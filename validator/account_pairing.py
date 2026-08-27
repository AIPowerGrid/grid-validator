# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Explicit account visibility consent; never transfer node credentials or funds."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import httpx
from eth_account import Account
from eth_account.messages import encode_defunct

GRID_URL = "https://api.aipowergrid.io"
CONSOLE_URL = "https://console.aipowergrid.io/dashboard/connect-validator"
PAIR_ID = re.compile(r"vpa_[a-f0-9]{64}")
NODE_ID = re.compile(r"val_[a-f0-9]{32}")
HASH = re.compile(r"[a-f0-9]{64}")
CODE = re.compile(r"[A-F0-9]{8}")
CLOCK_SKEW_SECONDS = 30
LINK_FIELDS = {
    "purpose",
    "audience",
    "pairing_id",
    "validator_id",
    "node_account_id",
    "operator_account_id",
    "signing_wallet",
    "comparison_code",
    "expires_at",
    "permissions",
}
UNLINK_FIELDS = LINK_FIELDS - {"comparison_code", "permissions"} | {"issued_at"}


class PairingError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _matches(pattern: re.Pattern[str], value: object) -> bool:
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def review_hash(payload: dict[str, Any], *, unlink: bool = False) -> str:
    # Unlink timestamps refresh on every read. Consent binds the immutable
    # association, while the actual signature includes Core's fresh timestamps.
    reviewed = {
        k: v
        for k, v in payload.items()
        if not unlink or k not in {"issued_at", "expires_at"}
    }
    return hashlib.sha256(canonical(reviewed).encode()).hexdigest()


@dataclass(frozen=True)
class Identity:
    wallet: str
    api_key: str = field(repr=False)
    private_key: str = field(repr=False)

    @classmethod
    def from_values(cls, values: Mapping[str, str | None]) -> Identity:
        if (values.get("GRID_API_URL") or GRID_URL).rstrip("/") != GRID_URL:
            raise PairingError("unsupported_grid")
        key = values.get("VALIDATOR_API_KEY")
        secret = values.get("VALIDATOR_PRIVATE_KEY")
        wallet = values.get("VALIDATOR_WALLET")
        if not isinstance(key, str) or not re.fullmatch(
            r"grid_[A-Za-z0-9_-]{20,200}", key
        ):
            raise PairingError("configuration_invalid")
        if not isinstance(secret, str) or not re.fullmatch(
            r"(?:0x)?[a-fA-F0-9]{64}", secret
        ):
            raise PairingError("configuration_invalid")
        try:
            derived = Account.from_key(secret).address.lower()
        except (TypeError, ValueError):
            raise PairingError("configuration_invalid") from None
        if not isinstance(wallet, str) or wallet.lower() != derived:
            raise PairingError("configuration_invalid")
        return cls(derived, key, secret)


def _uuid(value: object) -> bool:
    try:
        return isinstance(value, str) and str(UUID(value)) == value
    except ValueError:
        return False


def validated_payload(
    raw: object, identity: Identity, node_id: str, *, unlink: bool = False
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PairingError("invalid_contract")
    expected = UNLINK_FIELDS if unlink else LINK_FIELDS
    purpose = (
        "aipg.validator.account-unlink.v1"
        if unlink
        else "aipg.validator.account-link.v1"
    )
    if (
        set(raw) != expected
        or raw.get("purpose") != purpose
        or raw.get("audience") != GRID_URL
        or raw.get("validator_id") != node_id
        or raw.get("signing_wallet") != identity.wallet
        or not _matches(PAIR_ID, raw.get("pairing_id"))
        or not _uuid(raw.get("node_account_id"))
        or not _uuid(raw.get("operator_account_id"))
        or raw["node_account_id"] == raw["operator_account_id"]
        or type(raw.get("expires_at")) is not int
    ):
        raise PairingError("invalid_contract")
    clock = int(time.time())
    if not 0 < raw["expires_at"] - clock <= 600 + CLOCK_SKEW_SECONDS:
        raise PairingError("expired")
    if unlink:
        issued = raw.get("issued_at")
        if (
            type(issued) is not int
            or not -CLOCK_SKEW_SECONDS <= clock - issued < 600
            or raw["expires_at"] != issued + 600
        ):
            raise PairingError("invalid_contract")
    elif raw.get("permissions") != ["validator.account_visibility"] or not _matches(
        CODE, raw.get("comparison_code")
    ):
        raise PairingError("invalid_contract")
    return dict(raw)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


class PairingClient:
    def __init__(
        self,
        identity: Identity,
        closed: threading.Event,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.identity = identity
        self.closed = closed
        self.deadline = time.monotonic() + 30
        self.http = httpx.Client(
            timeout=10, trust_env=False, follow_redirects=False, transport=transport
        )

    def request(
        self, method: str, path: str, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if self.closed.is_set():
            raise PairingError("app_closed")
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise PairingError("unavailable")
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "apikey": self.identity.api_key,
            "Authorization": "Bearer " + self.identity.api_key,
        }
        try:
            with self.http.stream(
                method,
                GRID_URL + path,
                json=body,
                headers=headers,
                timeout=min(10, remaining),
            ) as response:
                if response.status_code != 200:
                    code = {
                        401: "credentials_rejected",
                        403: "registration_required",
                        404: "not_found",
                        409: "changed",
                        429: "rate_limited",
                    }.get(response.status_code, "unavailable")
                    raise PairingError(code)
                if (
                    response.headers.get("content-encoding", "identity").lower()
                    != "identity"
                    or response.headers.get("content-type", "").split(";")[0]
                    != "application/json"
                ):
                    raise PairingError("invalid_contract")
                data = bytearray()
                for chunk in response.iter_raw():
                    if (
                        len(data) + len(chunk) > 16384
                        or time.monotonic() > self.deadline
                        or self.closed.is_set()
                    ):
                        raise PairingError("unavailable")
                    data.extend(chunk)
                value = json.loads(data, object_pairs_hook=_unique_object)
                if not isinstance(value, dict):
                    raise PairingError("invalid_contract")
                return value
        except httpx.HTTPError:
            raise PairingError("unavailable") from None
        except (ValueError, RecursionError):
            raise PairingError("invalid_contract") from None

    def registration(self) -> str:
        data = self.request("GET", "/v1/validator/registration")
        node_id = data.get("validator_id")
        if (
            not _matches(NODE_ID, node_id)
            or data.get("signing_wallet") != self.identity.wallet
            or data.get("status") not in ("active", "suspended")
        ):
            raise PairingError("registration_required")
        return str(node_id)

    def link(self, node_id: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
        raw = self.request("GET", "/v1/validator/account-link")
        if raw.get("status") == "none":
            return {"status": "none", "validator_id": node_id}, None
        payload = validated_payload(
            raw.get("unlink_payload"), self.identity, node_id, unlink=True
        )
        if (
            raw.get("status") != "linked"
            or raw.get("validator_id") != node_id
            or raw.get("operator_account_id") != payload["operator_account_id"]
            or raw.get("economic_effect") != "none"
        ):
            raise PairingError("invalid_contract")
        return {
            "status": "linked",
            "validator_id": node_id,
            "signing_wallet": self.identity.wallet,
            "pairing_id": payload["pairing_id"],
            "review_hash": review_hash(payload, unlink=True),
        }, payload

    def poll(self, node_id: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
        raw = self.request("GET", "/v1/validator/account-pairing")
        if raw.get("status") == "none":
            return {"status": "none", "validator_id": node_id}, None
        pair_id, expires = raw.get("pairing_id"), raw.get("expires_at")
        if (
            raw.get("validator_id") != node_id
            or raw.get("signing_wallet") != self.identity.wallet
            or not _matches(PAIR_ID, pair_id)
            or type(expires) is not int
            or raw.get("economic_effect") != "none"
            or raw.get("status")
            not in ("pending", "approved", "expired", "cancelled", "linked")
        ):
            raise PairingError("invalid_contract")
        status = raw["status"]
        # A completed slot is not proof that its association still exists.
        if status == "linked":
            return {"status": "cancelled", "validator_id": node_id}, None
        if status in {"pending", "approved"} and expires <= int(time.time()):
            status = "expired"
        if expires > int(time.time()) + 600 + CLOCK_SKEW_SECONDS:
            raise PairingError("invalid_contract")
        view: dict[str, Any] = {
            "status": status,
            "validator_id": node_id,
            "pairing_id": pair_id,
            "signing_wallet": self.identity.wallet,
            "expires_at": expires,
        }
        payload = None
        if status in {"pending", "approved"}:
            view["approval_url"] = CONSOLE_URL + "/" + str(pair_id)
        if status == "approved":
            payload = validated_payload(raw.get("payload"), self.identity, node_id)
            if (
                payload["pairing_id"] != pair_id
                or payload["expires_at"] != expires
                or payload["comparison_code"] != raw.get("comparison_code")
            ):
                raise PairingError("invalid_contract")
            view.update(
                comparison_code=payload["comparison_code"],
                review_hash=review_hash(payload),
            )
        return view, payload

    def sign(self, payload: dict[str, Any]) -> str:
        if self.closed.is_set():
            raise PairingError("app_closed")
        signature = Account.sign_message(
            encode_defunct(text=canonical(payload)), self.identity.private_key
        ).signature
        return "0x" + bytes(signature).hex()

    def perform(self, form: dict[str, Any]) -> dict[str, Any]:
        node_id = self.registration()
        action = form["action"]
        if action == "cancel":
            result = self.request(
                "POST", f"/v1/validator/account-pairings/{form['pairing_id']}/cancel"
            )
            if result.get("status") != "cancelled":
                raise PairingError("invalid_contract")
            return {"status": "cancelled", "validator_id": node_id}
        linked, unlink_payload = self.link(node_id)
        if action == "unlink":
            if (
                not unlink_payload
                or form["pairing_id"] != linked["pairing_id"]
                or not hmac.compare_digest(form["review_hash"], linked["review_hash"])
            ):
                raise PairingError("changed")
            result = self.request(
                "POST",
                "/v1/validator/account-link/unlink",
                {
                    "pairing_id": unlink_payload["pairing_id"],
                    "issued_at": unlink_payload["issued_at"],
                    "signature": self.sign(unlink_payload),
                },
            )
            if (
                result.get("status") != "unlinked"
                or result.get("validator_id") != node_id
            ):
                raise PairingError("invalid_contract")
            return {"status": "none", "validator_id": node_id}
        if unlink_payload:
            return linked
        if action == "start":
            created = self.request("POST", "/v1/validator/account-pairings")
            pair_id = created.get("pairing_id")
            if not _matches(PAIR_ID, pair_id) or created.get(
                "approval_url"
            ) != CONSOLE_URL + "/" + str(pair_id):
                raise PairingError("invalid_contract")
        view, payload = self.poll(node_id)
        if action != "confirm":
            return view
        if (
            not payload
            or view["status"] != "approved"
            or form["pairing_id"] != view["pairing_id"]
            or form["comparison_code"] != view["comparison_code"]
            or not hmac.compare_digest(form["review_hash"], view["review_hash"])
        ):
            raise PairingError("changed")
        result = self.request(
            "POST",
            f"/v1/validator/account-pairings/{form['pairing_id']}/confirm",
            {"signature": self.sign(payload)},
        )
        if (
            result.get("status") != "linked"
            or result.get("pairing_id") != form["pairing_id"]
            or result.get("validator_id") != node_id
            or result.get("signing_wallet") != self.identity.wallet
            or result.get("economic_effect") != "none"
        ):
            raise PairingError("invalid_contract")
        linked, _ = self.link(node_id)
        if linked.get("pairing_id") != form["pairing_id"]:
            raise PairingError("changed")
        return linked


def valid_form(form: object) -> bool:
    if not isinstance(form, dict) or not isinstance(form.get("action"), str):
        return False
    action = form["action"]
    fields = {
        "start": {"action"},
        "refresh": {"action"},
        "cancel": {"action", "pairing_id"},
        "confirm": {"action", "pairing_id", "review_hash", "comparison_code"},
        "unlink": {"action", "pairing_id", "review_hash"},
    }.get(action)
    if set(form) != fields:
        return False
    return (
        ("pairing_id" not in form or _matches(PAIR_ID, form["pairing_id"]))
        and ("review_hash" not in form or _matches(HASH, form["review_hash"]))
        and ("comparison_code" not in form or _matches(CODE, form["comparison_code"]))
    )


class PairingController:
    def __init__(
        self,
        identity_loader: Callable[[], Identity],
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.identity_loader = identity_loader
        self.transport = transport
        self.action_lock = threading.Lock()
        self.state_lock = threading.Lock()
        self.closed = threading.Event()
        self.state: dict[str, Any] = {"status": "idle"}

    def snapshot(self) -> dict[str, Any]:
        with self.state_lock:
            return {**self.state, "busy": self.action_lock.locked()}

    def perform(self, form: object) -> tuple[int, dict[str, Any]]:
        if not valid_form(form):
            return 400, {"error": "invalid_action"}
        assert isinstance(form, dict)
        if self.closed.is_set() or not self.action_lock.acquire(blocking=False):
            return 409, {"error": "pairing_busy"}
        client = None
        try:
            try:
                # Signing needs a displayed review and a fresh matching Core read.
                if form["action"] in {"confirm", "unlink"}:
                    with self.state_lock:
                        expected = (
                            "approved" if form["action"] == "confirm" else "linked"
                        )
                        if self.state.get("status") != expected or any(
                            self.state.get(key) != value
                            for key, value in form.items()
                            if key != "action"
                        ):
                            raise PairingError("changed")
                client = PairingClient(
                    self.identity_loader(), self.closed, self.transport
                )
                state = client.perform(form)
            except PairingError as exc:
                state = {"status": "error", "error": exc.code}
            except (OSError, UnicodeError):
                state = {"status": "error", "error": "configuration_invalid"}
            # Publish before releasing the operation lock, so concurrent local
            # requests cannot overwrite newer state with an older result.
            with self.state_lock:
                self.state = state
                return 200, {**state, "busy": False}
        finally:
            try:
                if client:
                    client.http.close()
            finally:
                self.action_lock.release()

    def close(self) -> None:
        self.closed.set()
