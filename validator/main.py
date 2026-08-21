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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("validator.main")


def _canonical(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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

    challenge = assignment.get("challenge") or {}
    prompt_hash = _sha256_text(str(challenge.get("prompt") or ""))
    response_hash = _sha256_text(response_text)
    evidence = {
        "assignment_id": expected_result["assignment_id"],
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
    expect = challenge.get("expected") or challenge.get("expect")
    kind = assignment.get("canary_kind") or challenge.get("kind")
    if not prompt or not expect or not kind:
        return None
    return {
        "kind": str(kind),
        "nonce": str(assignment.get("grid_nonce") or ""),
        "prompt": str(prompt),
        "expect": str(expect),
    }


async def _probe_assignment(grid: GridClient, assignment: dict) -> int:
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

    text = res.get("output_text") or res.get("text") or ""
    if not text:
        logger.info(f"[{str(worker_id)[:8]} {model}] assignment probe returned no text; skipping")
        return 0

    commitments = _verified_probe_evidence(assignment, res, text)
    if commitments is None:
        return 0

    verdict = prober.score(canary, text, latency)
    if verdict not in attest.VALID_VERDICTS:
        logger.info(
            f"[{str(worker_id)[:8]} {model}] local probe scorer returned invalid verdict; skipping"
        )
        return 0
    core_verdict = str(res.get("probe_verdict") or "")
    if core_verdict and core_verdict != verdict:
        logger.warning(
            "[%s %s] local verdict %s disagrees with Core verdict %s",
            str(worker_id)[:8],
            model,
            verdict,
            core_verdict,
        )
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
        response_text=text,
        assignment_id=str(assignment_id),
        grid_nonce=str(grid_nonce),
    )
    # Echo only the commitment this node independently recomputed and matched
    # against Core's response.
    att.update(commitments)
    submitted = await grid.submit_attestation(attest.sign(att))
    return 1 if submitted else 0


async def probe_round(grid: GridClient, round_index: int) -> int:
    """Run one probe round and return the number of attestations accepted by Core."""
    assignments = await grid.validator_assignments(limit=5, modality="text")
    if not assignments:
        logger.info("no Grid-issued assignments available; fail-closed round performed no probe")
        return 0
    results = await asyncio.gather(*(_probe_assignment(grid, a) for a in assignments))
    return sum(results)


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
    round_index = 0
    try:
        while True:
            try:
                await grid.heartbeat()
                await probe_round(grid, round_index)
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
