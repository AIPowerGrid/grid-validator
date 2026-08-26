# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Validator node configuration (env-driven; secrets stay in a chmod-600 .env)."""

import os
import re
import ipaddress
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

ENV_FILE = Path(os.getenv("VALIDATOR_ENV", Path.cwd() / ".env"))
load_dotenv(ENV_FILE)

_ADDR_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
_CONFIG_ERRORS: list[str] = []


def _env_text(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_bool(name: str, default: bool) -> bool:
    raw = _env_text(name, "true" if default else "false").lower()
    if raw in {"1", "true", "yes", "y", "on"}:
        return True
    if raw in {"0", "false", "no", "n", "off"}:
        return False
    _CONFIG_ERRORS.append(f"{name} must be true or false.")
    return default


def _env_int(name: str, default: int, *, minimum: int | None = None) -> int:
    raw = _env_text(name, str(default))
    try:
        value = int(raw)
    except ValueError:
        _CONFIG_ERRORS.append(f"{name} must be an integer.")
        return default
    if minimum is not None and value < minimum:
        _CONFIG_ERRORS.append(f"{name} must be >= {minimum}.")
        return default
    return value


def _env_float(name: str, default: float, *, minimum: float | None = None) -> float:
    raw = _env_text(name, str(default))
    try:
        value = float(raw)
    except ValueError:
        _CONFIG_ERRORS.append(f"{name} must be a number.")
        return default
    if minimum is not None and value < minimum:
        _CONFIG_ERRORS.append(f"{name} must be >= {minimum:g}.")
        return default
    return value


def normalize_address(value: str, env_name: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if not _ADDR_RE.match(value):
        raise RuntimeError(f"{env_name} must be a 20-byte 0x hex address.")
    return value.lower()


def normalize_wallet(wallet: str) -> str:
    return normalize_address(wallet, "VALIDATOR_WALLET")


def normalize_grid_url(value: str) -> str:
    value = (value or "").strip().rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError(
            "GRID_API_URL must be an http(s) URL, e.g. https://api.aipowergrid.io."
        )
    return value


def normalize_media_origins(values) -> tuple[str, ...]:
    """Return exact public HTTPS origins permitted for media evidence."""
    normalized: list[str] = []
    for raw in values:
        value = str(raw or "").strip()
        if not value:
            continue
        parsed = urlsplit(value)
        if (
            parsed.scheme.lower() != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise RuntimeError(
                "VALIDATOR_MEDIA_ALLOWED_ORIGINS must contain exact HTTPS origins only."
            )
        try:
            host = parsed.hostname.encode("idna").decode("ascii").lower()
        except UnicodeError as exc:
            raise RuntimeError("VALIDATOR_MEDIA_ALLOWED_ORIGINS contains an invalid host.") from exc
        if host == "localhost" or host.endswith(".local"):
            raise RuntimeError("VALIDATOR_MEDIA_ALLOWED_ORIGINS cannot contain local hosts.")
        try:
            address = ipaddress.ip_address(host.strip("[]"))
        except ValueError:
            address = None
        if address and not address.is_global:
            raise RuntimeError("VALIDATOR_MEDIA_ALLOWED_ORIGINS cannot contain private IPs.")
        try:
            port = parsed.port
        except ValueError as exc:
            raise RuntimeError("VALIDATOR_MEDIA_ALLOWED_ORIGINS contains an invalid port.") from exc
        authority = f"[{host}]" if ":" in host else host
        origin = f"https://{authority}{f':{port}' if port is not None else ''}"
        if origin not in normalized:
            normalized.append(origin)
    return tuple(normalized)


def wallet_from_private_key(private_key: str) -> str:
    try:
        from eth_account import Account  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "eth-account is required when VALIDATOR_PRIVATE_KEY is set."
        ) from exc

    try:
        return Account.from_key(private_key).address.lower()
    except Exception as exc:
        raise RuntimeError("VALIDATOR_PRIVATE_KEY is invalid.") from exc


class Settings:
    ENV_FILE = ENV_FILE

    # ── Grid ──
    GRID_API_URL = _env_text("GRID_API_URL", "https://api.aipowergrid.io")
    # V2 Grid API key carrying the four dedicated validator scopes.
    VALIDATOR_API_KEY = _env_text("VALIDATOR_API_KEY", "")

    # ── Identity / on-chain ──
    # The validator's wallet signs attestations AND holds the stake. The private
    # key is required to sign; keep .env at chmod 600 and never commit it.
    VALIDATOR_WALLET = _env_text("VALIDATOR_WALLET", "").lower()
    VALIDATOR_PRIVATE_KEY = _env_text("VALIDATOR_PRIVATE_KEY", "")

    BASE_RPC_URL = _env_text("BASE_RPC_URL", "https://mainnet.base.org")
    AIPG_TOKEN_ADDR = _env_text("AIPG_TOKEN_ADDR", "0xa1c0deCaFE3E9Bf06A5F29B7015CD373a9854608")
    VALIDATOR_STAKING_ADDR = _env_text("VALIDATOR_STAKING_ADDR", "")  # set after deploy

    # Minimum stake (whole AIPG) required to run. Mirrors the on-chain MIN_STAKE.
    MIN_STAKE = _env_int("VALIDATOR_MIN_STAKE", 50000, minimum=0)
    # Preview skips the on-chain gate. Signing and registration are still mandatory.
    REQUIRE_STAKE = _env_bool("VALIDATOR_REQUIRE_STAKE", False)

    # ── Probing ──
    MEDIA_LATENCY_BUDGET_S = _env_float("MEDIA_LATENCY_BUDGET_S", 60, minimum=0)
    VIDEO_LATENCY_BUDGET_S = _env_float("VIDEO_LATENCY_BUDGET_S", 120, minimum=0)
    PHASH_TOLERANCE = _env_int("PHASH_TOLERANCE", 12, minimum=0)
    VIDEO_PHASH_TOLERANCE = _env_int("VIDEO_PHASH_TOLERANCE", 12, minimum=0)
    VIDEO_MOTION_TOLERANCE = _env_float("VIDEO_MOTION_TOLERANCE", 8, minimum=0)
    MEDIA_ALLOWED_ORIGINS = tuple(
        part.strip()
        for part in _env_text("VALIDATOR_MEDIA_ALLOWED_ORIGINS", "").split(",")
        if part.strip()
    )
    MEDIA_MAX_BYTES = _env_int("VALIDATOR_MEDIA_MAX_BYTES", 64 * 1024 * 1024, minimum=1)
    MEDIA_FETCH_TIMEOUT_S = _env_float("VALIDATOR_MEDIA_FETCH_TIMEOUT_S", 30, minimum=0.1)
    VIDEO_DECODE_TIMEOUT_S = _env_float("VALIDATOR_VIDEO_DECODE_TIMEOUT_S", 15, minimum=0.1)

    PROBE_INTERVAL_S = _env_int("PROBE_INTERVAL_S", 60, minimum=1)
    # Core permits a targeted text stage to run for 180 seconds. The node's
    # HTTP timeout must cover that full server-side window plus transport slack.
    PROBE_TIMEOUT_S = _env_int("PROBE_TIMEOUT_S", 180, minimum=1)
    PROBE_MAX_TOKENS = _env_int("PROBE_MAX_TOKENS", 256, minimum=1)
    # Latency budget: a correct-but-slower-than-this answer scores `slow`.
    LATENCY_BUDGET_S = _env_float("LATENCY_BUDGET_S", 30, minimum=0)

    # Durable signed-evidence delivery. The database contains public signed
    # envelopes, never the signing key.
    STATE_DB_PATH = _env_text(
        "VALIDATOR_STATE_DB",
        str(Path.home() / ".aipg-validator" / "state.sqlite3"),
    )
    OUTBOX_MAX_ATTEMPTS = _env_int("VALIDATOR_OUTBOX_MAX_ATTEMPTS", 20, minimum=1)
    OUTBOX_MAX_AGE_S = _env_int("VALIDATOR_OUTBOX_MAX_AGE_S", 1800, minimum=60)
    ASSIGNMENT_MAX_ATTEMPTS = _env_int(
        "VALIDATOR_ASSIGNMENT_MAX_ATTEMPTS", 20, minimum=1
    )
    ASSIGNMENT_MAX_AGE_S = _env_int(
        "VALIDATOR_ASSIGNMENT_MAX_AGE_S", 3600, minimum=60
    )
    UPDATE_CHECK_ENABLED = _env_bool("VALIDATOR_UPDATE_CHECK", True)
    UPDATE_CHECK_INTERVAL_S = _env_int(
        "VALIDATOR_UPDATE_CHECK_INTERVAL_S", 21600, minimum=3600
    )

    # ── Local dashboard ──
    DASHBOARD_HOST = _env_text("DASHBOARD_HOST", "127.0.0.1")
    DASHBOARD_PORT = _env_int("DASHBOARD_PORT", 8790, minimum=1)

    @classmethod
    def validate(cls):
        if _CONFIG_ERRORS:
            raise RuntimeError("; ".join(_CONFIG_ERRORS))
        cls.GRID_API_URL = normalize_grid_url(cls.GRID_API_URL)
        if not cls.VALIDATOR_API_KEY:
            raise RuntimeError("VALIDATOR_API_KEY is required.")
        wallet = normalize_wallet(cls.VALIDATOR_WALLET)
        cls.VALIDATOR_WALLET = wallet
        cls.AIPG_TOKEN_ADDR = normalize_address(cls.AIPG_TOKEN_ADDR, "AIPG_TOKEN_ADDR")
        cls.VALIDATOR_STAKING_ADDR = normalize_address(
            cls.VALIDATOR_STAKING_ADDR,
            "VALIDATOR_STAKING_ADDR",
        )
        if not cls.VALIDATOR_PRIVATE_KEY:
            raise RuntimeError(
                "VALIDATOR_PRIVATE_KEY is required to register and sign validator evidence."
            )
        if not wallet:
            raise RuntimeError(
                "VALIDATOR_WALLET is required and must be linked to the Grid account."
            )
        derived_wallet = cls._wallet_from_private_key()
        if derived_wallet != wallet:
            raise RuntimeError(
                "VALIDATOR_WALLET does not match VALIDATOR_PRIVATE_KEY."
            )
        if not 1 <= cls.DASHBOARD_PORT <= 65535:
            raise RuntimeError("DASHBOARD_PORT must be between 1 and 65535.")
        if not cls.STATE_DB_PATH:
            raise RuntimeError("VALIDATOR_STATE_DB must not be empty.")
        cls.MEDIA_ALLOWED_ORIGINS = normalize_media_origins(cls.MEDIA_ALLOWED_ORIGINS)

    @classmethod
    def _wallet_from_private_key(cls) -> str:
        return wallet_from_private_key(cls.VALIDATOR_PRIVATE_KEY)
