# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Validator node entrypoint: optional stake check, then probe in a loop.

Run:  python -m validator.main   (from the grid-validator/ dir, with a .env)
"""

import asyncio
import hashlib
import hmac
import json
import logging
import sys
import time

from . import attest, prober, staking
from .config import Settings
from .grid_client import GridClient
from .outbox import AttestationOutbox

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("validator.main")


def _canonical(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _response_commitment_text(assignment: dict, result: dict) -> str:
    text = str(result.get("output_text") or result.get("text") or "")
    kind = str(
        assignment.get("canary_kind")
        or (assignment.get("challenge") or {}).get("kind")
        or ""
    )
    if kind == "tool.call":
        return _canonical({"text": text, "tool_calls": result.get("tool_calls")})
    if kind == "tool.chain":
        return _canonical({"steps": result.get("tool_chain")})
    return text


def _prompt_commitment_text(assignment: dict) -> str:
    challenge = assignment.get("challenge") or {}
    prompt = str(challenge.get("prompt") or "")
    if str(challenge.get("kind") or "") == "tool.chain":
        return _canonical({"prompt": prompt, "steps": challenge.get("steps")})
    return prompt


def _verified_probe_evidence(
    assignment: dict,
    result: dict,
    response_text: str,
) -> dict[str, str] | None:
    """Recompute and verify Core's targeted-probe commitment.

    Core transports the workload, but the validator must not blindly sign the
    coordinator's identifiers or hashes. Any mismatch makes the probe
    unusable; it does not become a failed-worker attestation.
    """
    expected_result = {
        "assignment_id": str(assignment.get("assignment_id") or ""),
        "probe_group_id": str(assignment.get("probe_group_id") or ""),
        "grid_nonce": str(assignment.get("grid_nonce") or ""),
        "target_worker_id": str(assignment.get("target_worker_id") or ""),
        "model": str(assignment.get("model") or ""),
        "modality": str(assignment.get("modality") or ""),
        "capability": str(assignment.get("capability") or ""),
        "canary_kind": str(assignment.get("canary_kind") or ""),
    }
    if not all(expected_result.values()):
        logger.warning("assignment is missing evidence-binding metadata; skipping")
        return None
    for key, expected in expected_result.items():
        if str(result.get(key) or "") != expected:
            logger.warning("targeted probe %s mismatch; skipping", key)
            return None

    prompt_hash = _sha256_text(_prompt_commitment_text(assignment))
    response_hash = _sha256_text(response_text)
    evidence = {
        "assignment_id": expected_result["assignment_id"],
        "probe_group_id": expected_result["probe_group_id"],
        "grid_nonce": expected_result["grid_nonce"],
        "worker_id": expected_result["target_worker_id"],
        "model": expected_result["model"],
        "modality": expected_result["modality"],
        "capability": expected_result["capability"],
        "canary_kind": expected_result["canary_kind"],
        "prompt_hash": prompt_hash,
        "response_hash": response_hash,
    }
    evidence_hash = hashlib.sha256(_canonical(evidence).encode("utf-8")).hexdigest()
    commitments = {
        "prompt_hash": prompt_hash,
        "response_hash": response_hash,
        "evidence_hash": evidence_hash,
    }
    for key, expected in commitments.items():
        actual = str(result.get(key) or "")
        if not hmac.compare_digest(actual, expected):
            logger.warning("targeted probe %s does not verify; skipping", key)
            return None
    return commitments


def _assignment_canary(assignment: dict) -> dict | None:
    challenge = assignment.get("challenge") or {}
    prompt = challenge.get("prompt")
    expected_hash = challenge.get("expected_hash")
    kind = assignment.get("canary_kind") or challenge.get("kind")
    if not prompt or not expected_hash or not kind:
        return None
    return {
        "kind": str(kind),
        "nonce": str(assignment.get("grid_nonce") or ""),
        "prompt": str(prompt),
        "expected_hash": str(expected_hash),
        "steps": challenge.get("steps"),
    }


async def _submit_outbox_item(
    grid: GridClient,
    outbox: AttestationOutbox,
    item: dict,
) -> bool:
    submitted = await grid.submit_attestation(item["envelope"])
    if submitted:
        outbox.delivered(item["id"])
        return True
    dead = outbox.failed(
        item["id"],
        max_attempts=Settings.OUTBOX_MAX_ATTEMPTS,
        max_age_seconds=Settings.OUTBOX_MAX_AGE_S,
    )
    if dead:
        logger.error(
            "attestation %s exhausted delivery policy and was dead-lettered",
            item["id"][:12],
        )
    return False


async def _flush_outbox(grid: GridClient, outbox: AttestationOutbox) -> int:
    delivered = 0
    for item in outbox.pending():
        if await _submit_outbox_item(grid, outbox, item):
            delivered += 1
    return delivered


async def _probe_assignment(
    grid: GridClient,
    assignment: dict,
    outbox: AttestationOutbox,
) -> int:
    """Assignment-bound targeted probe.

    This is the first path whose evidence can be called authoritative by core:
    the Grid issued the assignment id + nonce, routed the probe to the specific
    worker, and returns the probe evidence hash that the signed attestation must
    echo back.
    """
    assignment_id = assignment.get("assignment_id")
    grid_nonce = assignment.get("grid_nonce")
    canary = _assignment_canary(assignment)
    if not assignment_id or not grid_nonce or not canary:
        logger.info("grid assignment missing id, nonce, or challenge; skipping")
        return 0

    model = assignment.get("model") or "unknown"
    worker_id = assignment.get("target_worker_id") or ""
    t0 = time.time()
    res = await grid.probe_assignment(str(assignment_id))
    latency = time.time() - t0
    if not res:
        logger.info(f"[{str(worker_id)[:8]} {model}] assignment probe unavailable; skipping")
        return 0

    text = str(res.get("output_text") or res.get("text") or "")
    tool_calls = res.get("tool_calls")
    tool_chain = res.get("tool_chain")
    probe_failed = bool((res.get("grid") or {}).get("probe_failed"))
    if not text and not tool_calls and not tool_chain and not probe_failed:
        logger.info(f"[{str(worker_id)[:8]} {model}] assignment probe returned no text; skipping")
        return 0

    response_commitment = _response_commitment_text(assignment, res)
    commitments = _verified_probe_evidence(assignment, res, response_commitment)
    if commitments is None:
        return 0

    try:
        verdict = prober.score_committed(
            {
                **canary,
                "tool_calls": tool_chain if canary["kind"] == "tool.chain" else tool_calls,
            },
            text,
            latency,
        )
    except ValueError:
        logger.warning("assignment has an invalid scoring commitment; skipping")
        return 0
    if verdict not in attest.VALID_VERDICTS:
        logger.info(
            f"[{str(worker_id)[:8]} {model}] local probe scorer returned invalid verdict; skipping"
        )
        return 0
    logger.info(
        f"[{str(worker_id)[:8]} {model}] assignment {canary['kind']} -> {verdict} "
        f"({latency:.1f}s)"
    )
    att = attest.build(
        worker_id=str(worker_id),
        model=str(model),
        canary=canary,
        verdict=verdict,
        latency_ms=int(latency * 1000),
        ts=int(time.time()),
        modality=str(assignment.get("modality") or "text"),
        capability=str(assignment.get("capability") or "text.basic.v1"),
        response_text=response_commitment,
        assignment_id=str(assignment_id),
        probe_group_id=str(assignment.get("probe_group_id") or ""),
        grid_nonce=str(grid_nonce),
    )
    # Echo only the commitment this node independently recomputed and matched
    # against Core's response.
    att.update(commitments)
    item_id = outbox.enqueue(attest.sign(att))
    item = outbox.get_pending(item_id)
    if item is None:
        # A duplicate envelope may already have been delivered or dead-lettered.
        return 0
    return 1 if await _submit_outbox_item(grid, outbox, item) else 0


async def probe_round(
    grid: GridClient,
    round_index: int,
    outbox: AttestationOutbox | None = None,
) -> int:
    """Run one probe round and return the number of attestations accepted by Core."""
    del round_index
    outbox = outbox or AttestationOutbox(Settings.STATE_DB_PATH)
    queued_assignments = outbox.pending_assignment_ids()
    accepted = await _flush_outbox(grid, outbox)
    assignments = await grid.validator_assignments(limit=5, modality="text")
    if not assignments:
        logger.info("no Grid-issued assignments available; fail-closed round performed no probe")
        return accepted
    fresh_assignments = [
        assignment
        for assignment in assignments
        if str(assignment.get("assignment_id") or "") not in queued_assignments
    ]
    results = await asyncio.gather(
        *(_probe_assignment(grid, assignment, outbox) for assignment in fresh_assignments)
    )
    return accepted + sum(results)


async def run() -> None:
    Settings.validate()
    # Stake gate — refuse to run unstaked (unless REQUIRE_STAKE=false for dev).
    try:
        staking.assert_eligible()
    except staking.NotDeployed:
        if Settings.REQUIRE_STAKE:
            raise RuntimeError(
                "Stake contract not deployed and REQUIRE_STAKE=true - exiting. "
                "Set VALIDATOR_REQUIRE_STAKE=false to run pre-launch."
            )

    grid = GridClient()
    registration = attest.sign(attest.build_registration(int(time.time())))
    try:
        registered = await grid.register_validator(registration)
    except Exception as exc:
        await grid.aclose()
        raise RuntimeError(f"validator registration failed: {exc}") from exc
    logger.info(
        f"Validator {registered.get('validator_id', 'unknown')} online -> {Settings.GRID_API_URL} "
        f"(probe every {Settings.PROBE_INTERVAL_S}s)"
    )
    outbox = AttestationOutbox(Settings.STATE_DB_PATH)
    round_index = 0
    try:
        while True:
            try:
                await grid.heartbeat()
                await probe_round(grid, round_index, outbox)
            except Exception as e:
                logger.error(f"probe round failed: {e}", exc_info=True)
            round_index += 1
            await asyncio.sleep(Settings.PROBE_INTERVAL_S)
    finally:
        await grid.aclose()


def _main() -> int:
    try:
        asyncio.run(run())
    except RuntimeError as exc:
        print(f"Startup: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
