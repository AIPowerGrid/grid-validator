#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Observe a validator's signed suspend/resume ownership check.

Core verifies both lifecycle signatures. This helper reads only the redacted
public status endpoint and never receives node credentials or private review
metadata. Passing proves control of the registered node credentials at that
moment; it does not prove independent operation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable


VALIDATOR_ID_RE = re.compile(r"^val_[0-9a-f]{32}$")
MIN_TIMEOUT_SECONDS = 30.0
MAX_TIMEOUT_SECONDS = 3600.0
MIN_INTERVAL_SECONDS = 0.5
MAX_INTERVAL_SECONDS = 30.0


class ControlCheckError(RuntimeError):
    """Raised when the public lifecycle evidence cannot prove control."""


class PublicStatusUnavailable(ControlCheckError):
    """Raised for bounded transient failures while reading public status."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _validated_api_url(value: str) -> str:
    raw = value.strip().rstrip("/")
    parsed = urllib.parse.urlparse(raw)
    local = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    if parsed.scheme != "https" and not (parsed.scheme == "http" and local):
        raise argparse.ArgumentTypeError(
            "API URL must use HTTPS (HTTP is allowed only for loopback tests)"
        )
    if not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise argparse.ArgumentTypeError(
            "API URL must be an origin without credentials, query, or fragment"
        )
    return raw


def _bounded_float(name: str, value: float, minimum: float, maximum: float) -> float:
    if not minimum <= value <= maximum:
        raise ControlCheckError(
            f"{name} must be between {minimum:g} and {maximum:g} seconds"
        )
    return value


def fetch_public_status(api_url: str, validator_id: str) -> dict[str, Any]:
    quoted_id = urllib.parse.quote(validator_id, safe="")
    request = urllib.request.Request(
        f"{api_url}/v1/validator/public/{quoted_id}",
        headers={
            "Accept": "application/json",
            "User-Agent": "aipg-validator-control-review/1",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status != 200:
                raise ControlCheckError(
                    f"public status returned HTTP {response.status}"
                )
            body = response.read(64 * 1024 + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise PublicStatusUnavailable(
            f"public status request failed: {type(exc).__name__}"
        ) from exc
    if len(body) > 64 * 1024:
        raise ControlCheckError("public status response exceeded 64 KiB")
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublicStatusUnavailable("public status returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ControlCheckError("public status must be a JSON object")
    return payload


def _validate_status(
    payload: dict[str, Any], validator_id: str
) -> tuple[str, bool, str]:
    if payload.get("schema") != "aipg.validator.public-status.v1":
        raise ControlCheckError("public status schema is unsupported")
    if payload.get("validator_id") != validator_id:
        raise ControlCheckError("public status returned a different validator ID")
    if payload.get("economic_effect") != "none":
        raise ControlCheckError("validator status no longer has economic_effect=none")
    if payload.get("software_version_supported") is not True:
        raise ControlCheckError(
            "validator is not on the frozen supported cohort version"
        )
    status = str(payload.get("registration_status") or "")
    if status not in {"active", "suspended"}:
        raise ControlCheckError(
            f"validator entered unexpected registration status {status or 'missing'}"
        )
    version = str(payload.get("software_version") or "")
    if not version:
        raise ControlCheckError("public status omitted the software version")
    return status, payload.get("online") is True, version


def verify_control(
    validator_id: str,
    *,
    api_url: str,
    timeout_seconds: float,
    interval_seconds: float,
    fetcher: Callable[[str, str], dict[str, Any]] = fetch_public_status,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    emit: Callable[[str], None] = print,
) -> None:
    if not VALIDATOR_ID_RE.fullmatch(validator_id):
        raise ControlCheckError(
            "validator ID must be val_ followed by 32 lowercase hex characters"
        )
    timeout_seconds = _bounded_float(
        "timeout", float(timeout_seconds), MIN_TIMEOUT_SECONDS, MAX_TIMEOUT_SECONDS
    )
    interval_seconds = _bounded_float(
        "interval",
        float(interval_seconds),
        MIN_INTERVAL_SECONDS,
        MAX_INTERVAL_SECONDS,
    )

    initial = fetcher(api_url, validator_id)
    status, online, version = _validate_status(initial, validator_id)
    if status != "active" or not online:
        raise ControlCheckError("validator must begin active and online")

    emit(f"READY {validator_id} active on {version} at {_utc_now()}")
    emit("Ask the operator to stop the local loop and run: aipg-validator suspend")
    deadline = monotonic() + timeout_seconds
    phase = "suspend"
    transient_errors = 0

    while monotonic() < deadline:
        sleep(interval_seconds)
        try:
            payload = fetcher(api_url, validator_id)
            status, online, current_version = _validate_status(payload, validator_id)
        except PublicStatusUnavailable:
            transient_errors += 1
            if transient_errors > 3:
                raise
            continue
        transient_errors = 0
        if current_version != version:
            raise ControlCheckError(
                "validator software version changed during the control check"
            )

        if phase == "suspend":
            if status == "suspended" and not online:
                emit(f"OBSERVED {validator_id} signed suspension at {_utc_now()}")
                emit("Ask the operator to run: aipg-validator check --no-probe")
                phase = "resume"
            continue

        if status == "active" and online:
            emit(f"PASS {validator_id} resumed the same identity at {_utc_now()}")
            emit(
                "This proves current node-key control, not independent operation or authority."
            )
            return

    waiting_for = "signed suspension" if phase == "suspend" else "signed resume"
    raise ControlCheckError(f"timed out waiting for {waiting_for}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Observe a preview validator's signed suspend/resume control check",
    )
    parser.add_argument("validator_id", help="public val_* identifier")
    parser.add_argument(
        "--api-url",
        default="https://api.aipowergrid.io",
        type=_validated_api_url,
        help="Grid API origin (default: production)",
    )
    parser.add_argument("--timeout-seconds", type=float, default=600.0)
    parser.add_argument("--interval-seconds", type=float, default=2.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        verify_control(
            args.validator_id,
            api_url=args.api_url,
            timeout_seconds=args.timeout_seconds,
            interval_seconds=args.interval_seconds,
        )
    except ControlCheckError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
