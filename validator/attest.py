# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Build and sign validator attestations.

An attestation is the validator's signed claim about one canary result. In V0,
the grid stores this as evidence only: no routing, reward, strike, slash, credit,
or ledger effects. Signing uses EIP-191 personal_sign over canonical JSON so the
same payload always yields the same digest.
"""

import json
import logging
import hashlib
from datetime import datetime, timezone

from .config import Settings
from . import __version__

logger = logging.getLogger("validator.attest")

VALID_VERDICTS = {"healthy", "slow", "failed"}
VERDICT_SCORE = {
    "healthy": 1.0,
    "slow": 0.75,
    "failed": 0.0,
}

TEXT_VALIDATOR_CAPABILITIES = [
    "text.instruction.v1",
    "text.reasoning.v1",
    "text.structured.v1",
    "text.context.4k.v1",
    "text.reasoning.multistep.v1",
    "text.tool_call.v1",
    "text.tool_chain.v1",
    "text.stop_sequence.v1",
]
# Backward-compatible text-only constant for callers that need the package's
# dependency-free baseline. Registration and heartbeat use
# ``runtime_capabilities`` so optional media support is never over-advertised.
VALIDATOR_CAPABILITIES = TEXT_VALIDATOR_CAPABILITIES


def runtime_capabilities() -> list[str]:
    """Return only scorers this process can execute safely right now."""
    capabilities = list(TEXT_VALIDATOR_CAPABILITIES)
    from .prober import token_limit_available

    if token_limit_available():
        capabilities.append("text.token_limit.v1")
    from .media_prober import media_dependencies_available

    if Settings.MEDIA_ALLOWED_ORIGINS and media_dependencies_available():
        capabilities.append("image.fidelity.v1")
    return capabilities


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _hash_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _hash_obj(obj: dict) -> str:
    return hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


def _epoch_from_ts(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y%m%d%H")


def build_registration(ts: int) -> dict:
    """Build the wallet-signed registration payload expected by Grid Core."""
    return {
        "registration_schema": "aipg.validator.registration.v1",
        "validator": Settings.VALIDATOR_WALLET,
        "software_version": __version__,
        "capabilities": runtime_capabilities(),
        "ts": ts,
    }


def _assignment_id(model: str, canary: dict, ts: int, explicit: str | None) -> str:
    if explicit:
        return explicit
    if canary.get("assignment_id"):
        return str(canary["assignment_id"])
    digest = _hash_obj({
        "model": model,
        "nonce": canary.get("nonce", ""),
        "ts": ts,
    })[:32]
    return f"validator-v0:{digest}"


def _evidence_fields(
    *,
    worker_id: str,
    model: str,
    modality: str,
    capability: str,
    canary: dict,
    response_text: str,
    verdict: str,
    latency_ms: int,
    ts: int,
) -> dict:
    """Build a compact evidence commitment without storing raw prompt/response."""
    prompt_hash = _hash_text(canary.get("prompt", ""))
    response_hash = _hash_text(response_text)
    evidence = {
        "schema": "aipg.validator.evidence.v0",
        "worker_id": worker_id,
        "model": model,
        "modality": modality,
        "capability": capability,
        "canary_kind": canary.get("kind"),
        "nonce": canary.get("nonce"),
        "prompt_hash": prompt_hash,
        "response_hash": response_hash,
        "verdict": verdict,
        "latency_ms": latency_ms,
        "ts": ts,
    }
    return {
        "evidence_schema": evidence["schema"],
        "prompt_hash": prompt_hash,
        "response_hash": response_hash,
        "evidence_hash": _hash_obj(evidence),
    }


def build(
    worker_id: str,
    model: str,
    canary: dict,
    verdict: str,
    latency_ms: int,
    ts: int,
    modality: str = "text",
    capability: str = "text.basic.v0",
    score: float | None = None,
    response_text: str = "",
    assignment_id: str | None = None,
    probe_group_id: str | None = None,
    epoch: str | None = None,
    grid_nonce: str | None = None,
) -> dict:
    """Assemble the unsigned attestation body."""
    if verdict not in VALID_VERDICTS:
        raise RuntimeError("verdict must be healthy, slow, or failed")
    assignment = _assignment_id(model, canary, ts, assignment_id)
    evidence = _evidence_fields(
        worker_id=worker_id,
        model=model,
        modality=modality,
        capability=capability,
        canary=canary,
        response_text=response_text,
        verdict=verdict,
        latency_ms=latency_ms,
        ts=ts,
    )
    return {
        "validator": Settings.VALIDATOR_WALLET,
        "attestation_schema": "aipg.validator.attestation.v0",
        "assignment_id": assignment,
        "probe_group_id": probe_group_id or "",
        "assignment_source": "grid" if grid_nonce else "validator_v0",
        "grid_nonce": grid_nonce or "",
        "epoch": epoch or _epoch_from_ts(ts),
        "worker_id": worker_id,
        "model": model,
        "modality": modality,
        "capability": capability,
        "canary_kind": canary["kind"],
        "nonce": canary["nonce"],
        **evidence,
        "verdict": verdict,  # healthy | slow | failed
        "score": VERDICT_SCORE[verdict] if score is None else score,
        "latency_ms": latency_ms,
        "ts": ts,
    }


def sign(attestation: dict) -> dict:
    """Return {payload, signature}. If no key is configured (dev), signature=None."""
    if not Settings.VALIDATOR_PRIVATE_KEY:
        return {"payload": attestation, "signature": None}
    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("eth-account is required to sign attestations.") from exc

    account = Account.from_key(Settings.VALIDATOR_PRIVATE_KEY)
    payload_wallet = (attestation.get("validator") or "").strip().lower()
    if not payload_wallet:
        raise RuntimeError("payload.validator is required when signing attestations.")
    if payload_wallet != account.address.lower():
        raise RuntimeError("payload.validator does not match VALIDATOR_PRIVATE_KEY.")

    body = _canonical(attestation)
    signed = Account.sign_message(
        encode_defunct(text=body),
        private_key=Settings.VALIDATOR_PRIVATE_KEY,
    )
    signature = signed.signature.hex()
    if not signature.startswith("0x"):
        signature = f"0x{signature}"
    return {"payload": attestation, "signature": signature}
