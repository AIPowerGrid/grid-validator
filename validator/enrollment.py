# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Explicit dedicated-account enrollment, without exporting a signing key."""

import os
import re
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from uuid import UUID

import httpx
from dotenv import dotenv_values
from eth_account import Account
from eth_account.messages import encode_defunct

GRID_URL = "https://api.aipowergrid.io"
DOMAIN = "console.aipowergrid.io"
URI = "https://console.aipowergrid.io/dashboard/validators"
IDENTITY_ORIGIN = "dedicated-enrollment-v1"
SCOPES = {"validator.assignments", "validator.probe", "validator.attest", "validator.read"}


class EnrollmentError(RuntimeError):
    """Safe operator-facing error; never include response bodies or credentials."""


@contextmanager
def enrollment_lock(path: Path) -> Iterator[None]:
    """OS-released lock prevents two setup windows replacing the same identity."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path) + ".enrollment.lock", os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, "r+b") as handle:
        if os.name == "nt":
            import msvcrt

            if os.fstat(handle.fileno()).st_size == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise EnrollmentError("Setup is already open for this identity. Close the other setup window.") from None
        else:
            import fcntl

            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise EnrollmentError("Setup is already open for this identity. Close the other setup window.") from None
        yield


def _post(client: httpx.Client, path: str, body: dict, token: str = "") -> dict:
    headers = {"Accept": "application/json", "Accept-Encoding": "identity"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    started = time.monotonic()
    try:
        with client.stream("POST", GRID_URL + path, json=body, headers=headers) as response:
            if response.status_code != 200:
                hint = {
                    401: "Authentication expired or was rejected. Run setup again.",
                    403: "This account cannot enroll a validator. Contact support.",
                    429: "Too many setup attempts. Wait a minute before retrying.",
                }.get(response.status_code, "Grid setup is unavailable. Retry later with the same identity.")
                raise EnrollmentError(hint)
            if response.headers.get("content-encoding", "identity").lower() != "identity":
                raise EnrollmentError("Grid returned an encoded setup response. Setup stopped.")
            data = bytearray()
            for chunk in response.iter_bytes(chunk_size=4096):
                data.extend(chunk)
                if len(data) > 32768 or time.monotonic() - started > 30:
                    raise EnrollmentError("Grid returned an oversized or slow setup response.")
            import json

            result = json.loads(data)
            if not isinstance(result, dict):
                raise ValueError
            return result
    except httpx.HTTPError:
        raise EnrollmentError("Could not reach the Grid securely. Check your connection and retry.") from None
    except (ValueError, RecursionError):
        raise EnrollmentError("Grid returned an invalid setup response. No credentials were printed.") from None


def validated_message(challenge: dict, wallet: str, now: datetime) -> str:
    """Sign only the exact short-lived Core login contract, never arbitrary text."""
    message = challenge.get("message")
    nonce = challenge.get("nonce")
    if (
        not isinstance(message, str)
        or len(message) > 2048
        or not isinstance(nonce, str)
        or not re.fullmatch(r"[0-9a-f]{32}", nonce)
        or challenge.get("chain_id") != 8453
    ):
        raise EnrollmentError("Grid returned an unexpected login challenge; nothing was signed.")
    lines = message.split("\n")
    try:
        if len(lines) != 11:
            raise ValueError
        issued = datetime.strptime(lines[9], "Issued At: %Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        expires = datetime.strptime(lines[10], "Expiration Time: %Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        expected = (
            f"{DOMAIN} wants you to sign in with your Ethereum account:\n{wallet}\n\n"
            f"Sign in to AI Power Grid.\n\nURI: {URI}\nVersion: 1\nChain ID: 8453\n"
            f"Nonce: {nonce}\n{lines[9]}\n{lines[10]}"
        )
        if message != expected or not (-60 <= (now - issued).total_seconds() <= 300):
            raise ValueError
        if not (0 < (expires - now).total_seconds() <= 600 and 0 < (expires - issued).total_seconds() <= 600):
            raise ValueError
    except ValueError:
        raise EnrollmentError("Login challenge identity, purpose, or expiry did not match. Check your clock and retry.") from None
    return message


def enroll(path: Path) -> bool:
    """Enroll only our own generated identity; return False for existing credentials.

    Caller obtains explicit operator consent before invoking. The signer is
    persisted before network activity so interrupted enrollment can resume.
    """
    from .cli import _upsert_env
    from .config import wallet_from_private_key

    with enrollment_lock(path):
        existing = dotenv_values(path) if path.exists() else {}
        if existing.get("VALIDATOR_API_KEY"):
            return False
        if str(existing.get("GRID_API_URL", GRID_URL) or "").rstrip("/") != GRID_URL:
            raise EnrollmentError("Automatic setup supports the official Grid only. Existing settings were kept.")
        if existing.get("VALIDATOR_PRIVATE_KEY") or existing.get("VALIDATOR_WALLET"):
            if existing.get("VALIDATOR_IDENTITY_ORIGIN") != IDENTITY_ORIGIN:
                raise EnrollmentError("Existing identity kept. Use manual setup or a new config file; automatic setup never imports an existing wallet.")
            private_key = str(existing.get("VALIDATOR_PRIVATE_KEY") or "")
            try:
                wallet = wallet_from_private_key(private_key)
            except RuntimeError:
                raise EnrollmentError("Existing signing identity is invalid. Restore its backup; do not generate a replacement.") from None
            if existing.get("VALIDATOR_WALLET") != wallet:
                raise EnrollmentError("Existing wallet and signer do not match. Configuration was not changed.")
        else:
            if existing:
                raise EnrollmentError("Existing configuration kept. Choose a new config file for dedicated-account setup.")
            account = Account.create()
            wallet = account.address.lower()
            private_key = "0x" + bytes(account.key).hex()
            _upsert_env(path, {
                "GRID_API_URL": GRID_URL,
                "VALIDATOR_API_KEY": "",
                "VALIDATOR_WALLET": wallet,
                "VALIDATOR_PRIVATE_KEY": private_key,
                "VALIDATOR_IDENTITY_ORIGIN": IDENTITY_ORIGIN,
                "VALIDATOR_REQUIRE_STAKE": "false",
            }, fresh_lines=[])
        snapshot = path.read_bytes()
        print("Signing identity saved locally. Authenticating with the Grid...")
        with httpx.Client(timeout=15, follow_redirects=False, trust_env=False) as client:
            challenge = _post(client, "/v1/accounts/wallet/challenge", {
                "address": wallet, "domain": DOMAIN, "uri": URI, "chain_id": 8453,
            })
            message = validated_message(challenge, wallet, datetime.now(timezone.utc))
            signature = "0x" + Account.sign_message(encode_defunct(text=message), private_key).signature.hex().removeprefix("0x")
            session = _post(client, "/v1/accounts/wallet/verify", {
                "address": wallet, "message": message, "signature": signature,
            })
            token = session.get("access_token")
            try:
                UUID(session.get("account_id", ""))
                if session.get("wallet") != wallet or session.get("token_type") != "Bearer":
                    raise ValueError
                if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{20,8192}", token):
                    raise ValueError
            except (ValueError, TypeError, AttributeError):
                raise EnrollmentError("Grid returned an unexpected account session. Setup stopped.") from None
            print("Wallet authentication accepted. Requesting a validator-only API key...")
            key_result = _post(client, "/v1/account/keys", {
                "purpose": "validator", "label": "validator-dedicated-node",
            }, token)
            key = key_result.get("api_key")
            scopes = key_result.get("scopes")
            if (
                key_result.get("purpose") != "validator"
                or not isinstance(scopes, list)
                or not all(isinstance(scope, str) for scope in scopes)
                or set(scopes) != SCOPES
                or not isinstance(key, str)
                or not re.fullmatch(r"grid_[A-Za-z0-9_-]{20,200}", key)
            ):
                raise EnrollmentError("Grid did not return a validator-only key. Setup stopped without saving it.")
            if path.read_bytes() != snapshot:
                raise EnrollmentError("Configuration changed during setup. It was not overwritten; review before retrying.")
            _upsert_env(path, {"VALIDATOR_API_KEY": key}, fresh_lines=[])
        return True
