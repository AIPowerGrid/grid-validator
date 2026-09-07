# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Private operator rewards and explicit, allocation-specific node consent."""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
import re
import threading
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

import httpx
from eth_account import Account
from eth_account.messages import encode_defunct

from .account_pairing import (
    GRID_URL,
    HASH,
    Identity,
    PairingClient,
    PairingError,
    _matches,
    _uuid,
)

SCHEMA = "aipg.validator.compensation.operator.v1"
CONSENT_SCHEMA = "aipg.validator.compensation.recipient.v1"
TOKEN = "0xa1c0decafe3e9bf06a5f29b7015cd373a9854608"
CONSOLE = "https://console.aipowergrid.io/dashboard/validator-payout/"
REQUEST_ID = re.compile(r"vpc_[a-f0-9]{64}")
CAMPAIGN_ID = re.compile(r"[a-z0-9][a-z0-9_-]{2,63}")
ADDRESS = re.compile(r"0x[a-f0-9]{40}")
CONSENT_FIELDS = {
    "schema",
    "audience",
    "campaign_id",
    "contract_hash",
    "allocation_hash",
    "operator_group_id",
    "account_id",
    "validator_id",
    "signing_wallet",
    "chain_id",
    "token_address",
    "asset",
    "decimals",
    "amount_atomic",
    "recipient",
    "issued_at",
    "expires_at",
}
REQUEST_STATES = {
    "awaiting_wallet",
    "awaiting_node",
    "review_required",
    "cancelled",
    "expired",
    "recipient_bound",
}
PAYMENT_STATES = REQUEST_STATES | {
    "wallet_required",
    "ready_for_payment",
    "no_payment_due",
    "pending",
    "sent",
    "manual_review",
}


def timestamp(value: object) -> float:
    if not isinstance(value, str) or len(value) > 40:
        raise PairingError("invalid_contract")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone required")
        return parsed.timestamp()
    except (ValueError, OverflowError):
        raise PairingError("invalid_contract") from None


def address(value: object) -> bool:
    return _matches(ADDRESS, value) and int(str(value), 16) != 0


def amount(value: object) -> bool:
    return (
        isinstance(value, str)
        and re.fullmatch(r"0|[1-9][0-9]{0,77}", value) is not None
        and int(value) < 2**256
    )


def format_amount(value: str) -> str:
    whole, fraction = divmod(int(value), 10**18)
    return f"{whole}.{fraction:018d}".rstrip("0").rstrip(".")


def consent_message(raw: object, identity: Identity, node_id: str) -> tuple[str, str]:
    """Reconstruct the reviewed v1 message locally; never sign server text."""
    if not isinstance(raw, dict) or set(raw) != CONSENT_FIELDS:
        raise PairingError("invalid_contract")
    if (
        raw["schema"] != CONSENT_SCHEMA
        or raw["audience"] != GRID_URL
        or type(raw["chain_id"]) is not int
        or raw["chain_id"] != 8453
        or type(raw["decimals"]) is not int
        or raw["decimals"] != 18
        or raw["asset"] != "AIPG"
        or raw["token_address"] != TOKEN
        or raw["validator_id"] != node_id
        or raw["signing_wallet"] != identity.wallet
        or not _uuid(raw["account_id"])
        or not _matches(CAMPAIGN_ID, raw["campaign_id"])
        or not _matches(HASH, raw["contract_hash"])
        or not _matches(HASH, raw["allocation_hash"])
        or not isinstance(raw["operator_group_id"], str)
        or re.fullmatch(r"opg_[A-Za-z0-9_-]{8,88}", raw["operator_group_id"]) is None
        or not address(raw["recipient"])
        or raw["recipient"] in {TOKEN, identity.wallet}
        or not amount(raw["amount_atomic"])
        or raw["amount_atomic"] == "0"
    ):
        raise PairingError("invalid_contract")
    issued, expires = timestamp(raw["issued_at"]), timestamp(raw["expires_at"])
    now = time.time()
    if not 0 < expires - issued <= 86400 or issued > now + 30 or expires <= now:
        raise PairingError("expired")
    encoded = json.dumps(raw, sort_keys=True, indent=2, allow_nan=False)
    if len(encoded.encode()) > 4096:
        raise PairingError("invalid_contract")
    digest = hashlib.sha256(
        json.dumps(raw, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    message = (
        "AI Power Grid validator compensation payout consent\n"
        f"Reward: {format_amount(raw['amount_atomic'])} AIPG on Base (chain 8453)\n"
        f"Destination: {raw['recipient']}\n"
        "Authorize only the exact earned allocation below to this Base recipient.\n"
        "This is not a token approval, login, or authorization for other rewards.\n\n"
        + encoded
    )
    return message, digest


class CompensationClient(PairingClient):
    max_response_bytes = 65536

    def status(self, node_id: str, offset: int) -> dict[str, Any]:
        raw = self.request("GET", f"/v1/validator/compensation?offset={offset}")
        if raw.get("schema") != SCHEMA or raw.get("validator_id") != node_id:
            raise PairingError("invalid_contract")
        items, campaigns = raw.get("items"), raw.get("campaigns")
        next_offset = raw.get("next_offset")
        if (
            not isinstance(items, list)
            or len(items) > 25
            or not isinstance(campaigns, list)
            or len(campaigns) > 25
            or type(raw.get("campaigns_has_more")) is not bool
            or (
                next_offset is not None
                and (
                    type(next_offset) is not int
                    or next_offset != offset + 25
                    or next_offset > 10000
                )
            )
        ):
            raise PairingError("invalid_contract")
        safe_items, safe_campaigns = [], []
        for item in items:
            if (
                not isinstance(item, dict)
                or not _matches(HASH, item.get("allocation_hash"))
                or not _matches(CAMPAIGN_ID, item.get("campaign_id"))
                or not amount(item.get("amount_atomic"))
                or item.get("asset") != "AIPG"
                or type(item.get("decimals")) is not int
                or item["decimals"] != 18
                or type(item.get("chain_id")) is not int
                or item["chain_id"] != 8453
                or not isinstance(item.get("status"), str)
                or item["status"] not in PAYMENT_STATES
                or type(item.get("reviewed_units")) is not int
                or not 0 <= item["reviewed_units"] <= 1_000_000
                or (
                    item.get("recipient") is not None and not address(item["recipient"])
                )
                or (
                    item.get("request_id") is not None
                    and not _matches(REQUEST_ID, item["request_id"])
                )
                or (
                    item.get("transaction_hash") is not None
                    and not _matches(
                        re.compile(r"0x[a-f0-9]{64}"), item["transaction_hash"]
                    )
                )
            ):
                raise PairingError("invalid_contract")
            safe_items.append(
                {
                    k: item.get(k)
                    for k in (
                        "allocation_hash",
                        "campaign_id",
                        "amount_atomic",
                        "reviewed_units",
                        "status",
                        "recipient",
                        "request_id",
                        "transaction_hash",
                    )
                }
            )
        for campaign in campaigns:
            if (
                not isinstance(campaign, dict)
                or not _matches(CAMPAIGN_ID, campaign.get("campaign_id"))
                or not isinstance(campaign.get("status"), str)
                or campaign["status"]
                not in {"scheduled", "earning", "awaiting_finalization", "finalized"}
                or campaign.get("asset") != "AIPG"
                or type(campaign.get("decimals")) is not int
                or campaign["decimals"] != 18
                or not amount(campaign.get("operator_cap_atomic"))
                or type(campaign.get("identity_review_required")) is not bool
                or timestamp(campaign.get("ends_at"))
                <= timestamp(campaign.get("starts_at"))
            ):
                raise PairingError("invalid_contract")
            safe_campaigns.append(
                {
                    k: campaign[k]
                    for k in (
                        "campaign_id",
                        "status",
                        "starts_at",
                        "ends_at",
                        "operator_cap_atomic",
                        "identity_review_required",
                    )
                }
            )
        return {
            "status": "ready",
            "items": safe_items,
            "campaigns": safe_campaigns,
            "campaigns_has_more": raw["campaigns_has_more"],
            "offset": offset,
            "next_offset": next_offset,
        }

    def inspect_request(
        self, node_id: str, request_id: str
    ) -> tuple[dict[str, Any], str | None]:
        raw = self.request("GET", f"/v1/validator/compensation/requests/{request_id}")
        if (
            raw.get("schema") != SCHEMA
            or raw.get("request_id") != request_id
            or not _matches(HASH, raw.get("allocation_hash"))
            or raw.get("payment_authorized") is not False
            or not isinstance(raw.get("status"), str)
            or raw["status"] not in REQUEST_STATES
        ):
            raise PairingError("invalid_contract")
        view = {
            "request_id": request_id,
            "allocation_hash": raw["allocation_hash"],
            "status": raw["status"],
        }
        if raw["status"] == "recipient_bound":
            if not address(raw.get("recipient")):
                raise PairingError("invalid_contract")
            return {**view, "recipient": raw["recipient"]}, None
        expires = timestamp(raw.get("expires_at"))
        if (
            expires > time.time() + 86430
            or raw.get("approval_url") != CONSOLE + request_id
        ):
            raise PairingError("invalid_contract")
        view["expires_at"] = expires
        if raw["status"] in {"cancelled", "expired"} or expires <= time.time():
            return {
                **view,
                "status": "cancelled" if raw["status"] == "cancelled" else "expired",
            }, None
        view["approval_url"] = CONSOLE + request_id
        proof, message = raw.get("consent"), None
        if proof is not None:
            message, digest = consent_message(proof, self.identity, node_id)
            if (
                proof["allocation_hash"] != raw["allocation_hash"]
                or timestamp(proof["expires_at"]) != expires
                or raw.get("review_hash") != digest
                or raw.get("message") != message
            ):
                raise PairingError("invalid_contract")
            view.update(
                {k: proof[k] for k in ("campaign_id", "recipient", "amount_atomic")}
            )
            view["review_hash"] = digest
        elif raw["status"] != "awaiting_wallet":
            raise PairingError("invalid_contract")
        return view, message


def valid_form(form: object) -> bool:
    if not isinstance(form, dict) or not isinstance(form.get("action"), str):
        return False
    fields = {
        "refresh": {"action", "offset"},
        "start": {"action", "allocation_hash"},
        "inspect": {"action", "request_id"},
        "cancel": {"action", "request_id"},
        "confirm": {"action", "request_id", "review_hash"},
    }.get(form["action"])
    return set(form) == fields and all(
        (
            "offset" not in form
            or (
                type(form["offset"]) is int
                and 0 <= form["offset"] <= 10000
                and form["offset"] % 25 == 0
            ),
            "allocation_hash" not in form or _matches(HASH, form["allocation_hash"]),
            "request_id" not in form or _matches(REQUEST_ID, form["request_id"]),
            "review_hash" not in form or _matches(HASH, form["review_hash"]),
        )
    )


class CompensationController:
    def __init__(
        self,
        identity_loader: Callable[[], Identity],
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.identity_loader, self.transport = identity_loader, transport
        self.action_lock, self.state_lock = threading.Lock(), threading.Lock()
        self.closed = threading.Event()
        self.state: dict[str, Any] = {
            "status": "idle",
            "items": [],
            "campaigns": [],
            "request": None,
        }

    def snapshot(self) -> dict[str, Any]:
        with self.state_lock:
            return {**copy.deepcopy(self.state), "busy": self.action_lock.locked()}

    def perform(self, form: object) -> tuple[int, dict[str, Any]]:
        if not valid_form(form):
            return 400, {"error": "invalid_action"}
        assert isinstance(form, dict)
        if self.closed.is_set() or not self.action_lock.acquire(blocking=False):
            return 409, {"error": "compensation_busy"}
        client = None
        try:
            with self.state_lock:
                state = copy.deepcopy(self.state)
            try:
                client = CompensationClient(
                    self.identity_loader(), self.closed, self.transport
                )
                node_id = client.registration()
                if form["action"] == "refresh":
                    state = client.status(node_id, form["offset"])
                    state["request"] = None
                else:
                    request_id = form.get("request_id")
                    if form["action"] == "start":
                        started = client.request(
                            "POST",
                            f"/v1/validator/compensation/{form['allocation_hash']}/requests",
                        )
                        request_id = started.get("request_id")
                        if (
                            not _matches(REQUEST_ID, request_id)
                            or started.get("allocation_hash") != form["allocation_hash"]
                        ):
                            raise PairingError("invalid_contract")
                    assert isinstance(request_id, str)
                    view, message = client.inspect_request(node_id, request_id)
                    if form["action"] == "confirm":
                        previous = state.get("request") or {}
                        if (
                            previous.get("status") != "awaiting_node"
                            or view["status"] != "awaiting_node"
                            or not message
                            or previous.get("request_id") != request_id
                            or previous.get("review_hash") != form["review_hash"]
                            or not hmac.compare_digest(
                                view.get("review_hash", ""), form["review_hash"]
                            )
                        ):
                            raise PairingError("changed")
                        if self.closed.is_set():
                            raise PairingError("app_closed")
                        signature = Account.sign_message(
                            encode_defunct(text=message), client.identity.private_key
                        ).signature
                        client.request(
                            "POST",
                            f"/v1/validator/compensation/requests/{request_id}/confirm",
                            {
                                "review_hash": form["review_hash"],
                                "signature": "0x" + bytes(signature).hex(),
                            },
                        )
                        view, _ = client.inspect_request(node_id, request_id)
                        if view["status"] not in {"review_required", "recipient_bound"}:
                            raise PairingError("changed")
                    elif form["action"] == "cancel":
                        client.request(
                            "POST",
                            f"/v1/validator/compensation/requests/{request_id}/cancel",
                        )
                        view, _ = client.inspect_request(node_id, request_id)
                        if view["status"] != "cancelled":
                            raise PairingError("changed")
                    state.update(status="ready", request=view)
                    for item in state.get("items", []):
                        if item["allocation_hash"] == view["allocation_hash"]:
                            item.update(
                                status="ready_for_payment"
                                if view["status"] == "recipient_bound"
                                else view["status"],
                                request_id=request_id,
                            )
                    state.pop("error", None)
                state["validator_id"] = node_id
            except PairingError as exc:
                state = {
                    "status": "error",
                    "error": exc.code,
                    "items": [],
                    "campaigns": [],
                    "request": None,
                }
            except (OSError, UnicodeError):
                state = {
                    "status": "error",
                    "error": "configuration_invalid",
                    "items": [],
                    "campaigns": [],
                    "request": None,
                }
            with self.state_lock:
                self.state = state
                return 200, {**copy.deepcopy(state), "busy": False}
        finally:
            try:
                if client:
                    client.http.close()
            finally:
                self.action_lock.release()

    def close(self) -> None:
        self.closed.set()
