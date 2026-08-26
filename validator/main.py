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

from . import attest, media_prober, prober, staking, update_check
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
    if kind == "token.limit":
        return _canonical({
            "text": text,
            "reasoning": str(result.get("reasoning_text") or ""),
            "finish_reason": result.get("finish_reason"),
        })
    return text


def _media_response_commitment(result: dict) -> str | None:
    """Commit immutable witness metadata without signing fetch credentials."""
    witnesses = result.get("witnesses")
    if not isinstance(witnesses, list) or len(witnesses) not in {1, 3}:
        return None
    committed = []
    for witness in witnesses:
        if not isinstance(witness, dict):
            return None
        try:
            item = {
                "role": str(witness["role"]),
                "worker_id": str(witness["worker_id"]),
                "sha256": str(witness["sha256"]).lower(),
                "bytes": int(witness["bytes"]),
                "content_type": str(witness["content_type"]).lower(),
                "latency_ms": int(witness["latency_ms"]),
            }
        except (KeyError, TypeError, ValueError):
            return None
        if not item["role"] or not item["worker_id"]:
            return None
        committed.append(item)
    return _canonical({"witnesses": committed})


def _prompt_commitment_text(assignment: dict) -> str:
    challenge = assignment.get("challenge") or {}
    if challenge.get("schema") == "aipg.validator.media.challenge.v1":
        return _canonical(challenge)
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
        "max_tokens": challenge.get("max_tokens"),
        "function_name": challenge.get("function_name"),
        "test_inputs": challenge.get("test_inputs"),
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


def _probe_latency_seconds(result: dict, fallback: float) -> float | None:
    """Use Core's original worker latency when a completed result is replayed."""
    value = result.get("probe_latency_ms")
    if not isinstance(value, bool) and isinstance(value, (int, float)):
        milliseconds = float(value)
        if 0 <= milliseconds <= 24 * 60 * 60 * 1000:
            return milliseconds / 1000
    if result.get("replayed"):
        return None
    return fallback


async def _promote_and_submit(
    grid: GridClient,
    outbox: AttestationOutbox,
    assignment_id: str,
    envelope: dict,
) -> int:
    item_id = outbox.promote_assignment(assignment_id, envelope)
    item = outbox.get_pending(item_id)
    if item is None:
        # A duplicate envelope may already have been delivered or dead-lettered.
        return 0
    return 1 if await _submit_outbox_item(grid, outbox, item) else 0


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
    if str(assignment.get("modality") or "") == "image":
        return await _probe_image_assignment(grid, assignment, outbox)
    if str(assignment.get("modality") or "") == "video":
        return await _probe_video_assignment(grid, assignment, outbox)
    if str(assignment.get("modality") or "text") != "text":
        logger.info("unsupported assignment modality; skipping")
        return 0

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
    reasoning_text = str(res.get("reasoning_text") or "")
    finish_reason = res.get("finish_reason")
    probe_failed = bool((res.get("grid") or {}).get("probe_failed"))
    if (
        not text
        and not reasoning_text
        and not tool_calls
        and not tool_chain
        and not probe_failed
    ):
        logger.info(
            f"[{str(worker_id)[:8]} {model}] assignment probe returned no committed output; skipping"
        )
        return 0
    latency = _probe_latency_seconds(res, latency)
    if latency is None:
        logger.warning("replayed assignment omitted its original probe latency; skipping")
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
            reasoning_text=reasoning_text,
            finish_reason=finish_reason,
        )
    except (ValueError, prober.ScorerUnavailable):
        logger.warning("assignment scorer is unavailable or invalid; skipping")
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
    return await _promote_and_submit(
        grid,
        outbox,
        str(assignment_id),
        attest.sign(att),
    )


async def _probe_image_assignment(
    grid: GridClient,
    assignment: dict,
    outbox: AttestationOutbox,
) -> int:
    """Fetch, verify, and score one Core-issued three-worker image witness set."""
    assignment_id = str(assignment.get("assignment_id") or "")
    grid_nonce = str(assignment.get("grid_nonce") or "")
    worker_id = str(assignment.get("target_worker_id") or "")
    model = str(assignment.get("model") or "")
    challenge = assignment.get("challenge") or {}
    if (
        not assignment_id
        or not grid_nonce
        or not worker_id
        or not model
        or assignment.get("capability") != "image.fidelity.v1"
        or assignment.get("canary_kind") != "image.fidelity"
        or not isinstance(challenge, dict)
        or challenge.get("schema") != "aipg.validator.media.challenge.v1"
        or not Settings.MEDIA_ALLOWED_ORIGINS
    ):
        logger.info("image assignment is unsupported or incomplete; skipping")
        return 0

    result = await grid.probe_assignment(assignment_id)
    if not result:
        logger.info("[%s %s] image assignment probe unavailable; skipping", worker_id[:8], model)
        return 0
    response_commitment = _media_response_commitment(result)
    if response_commitment is None:
        logger.info("[%s %s] image assignment has invalid witnesses; skipping", worker_id[:8], model)
        return 0
    commitments = _verified_probe_evidence(assignment, result, response_commitment)
    if commitments is None:
        return 0

    verdict, detail = await media_prober.score_image_fidelity_witnesses(
        challenge,
        result.get("witnesses") or [],
        target_worker_id=worker_id,
        allowed_origins=Settings.MEDIA_ALLOWED_ORIGINS,
        max_bytes=Settings.MEDIA_MAX_BYTES,
        timeout_s=Settings.MEDIA_FETCH_TIMEOUT_S,
        phash_tolerance=Settings.PHASH_TOLERANCE,
        latency_budget_s=Settings.MEDIA_LATENCY_BUDGET_S,
    )
    if verdict == "inconclusive":
        logger.info(
            "[%s %s] image assignment inconclusive (%s); skipping",
            worker_id[:8],
            model,
            detail.get("reason", "unknown"),
        )
        return 0
    if verdict not in attest.VALID_VERDICTS:
        logger.warning("image scorer returned an invalid verdict; skipping")
        return 0

    candidate = next(
        (
            witness
            for witness in result.get("witnesses", [])
            if witness.get("role") == "candidate"
            and str(witness.get("worker_id") or "") == worker_id
        ),
        None,
    )
    if not candidate:
        return 0
    latency_ms = int(candidate["latency_ms"])
    canary = {
        "kind": "image.fidelity",
        "nonce": grid_nonce,
        "prompt": _prompt_commitment_text(assignment),
    }
    body = attest.build(
        worker_id=worker_id,
        model=model,
        canary=canary,
        verdict=verdict,
        latency_ms=latency_ms,
        ts=int(time.time()),
        modality="image",
        capability="image.fidelity.v1",
        response_text=response_commitment,
        assignment_id=assignment_id,
        probe_group_id=str(assignment.get("probe_group_id") or ""),
        grid_nonce=grid_nonce,
    )
    body.update(commitments)
    logger.info(
        "[%s %s] image assignment -> %s (%dms)",
        worker_id[:8],
        model,
        verdict,
        latency_ms,
    )
    return await _promote_and_submit(
        grid,
        outbox,
        assignment_id,
        attest.sign(body),
    )


async def _probe_video_assignment(
    grid: GridClient,
    assignment: dict,
    outbox: AttestationOutbox,
) -> int:
    """Fetch, verify, and score one Core-issued video witness set."""
    assignment_id = str(assignment.get("assignment_id") or "")
    grid_nonce = str(assignment.get("grid_nonce") or "")
    worker_id = str(assignment.get("target_worker_id") or "")
    model = str(assignment.get("model") or "")
    capability = str(assignment.get("capability") or "")
    canary_kind = str(assignment.get("canary_kind") or "")
    challenge = assignment.get("challenge") or {}
    expected = {
        "video.contract.v1": "video.contract",
        "video.fidelity.v1": "video.fidelity",
    }
    if (
        not assignment_id
        or not grid_nonce
        or not worker_id
        or not model
        or capability not in expected
        or canary_kind != expected[capability]
        or not isinstance(challenge, dict)
        or challenge.get("schema") != "aipg.validator.media.challenge.v1"
        or challenge.get("kind") != canary_kind
        or challenge.get("scoring_policy_id") != capability
        or not Settings.MEDIA_ALLOWED_ORIGINS
    ):
        logger.info("video assignment is unsupported or incomplete; skipping")
        return 0

    result = await grid.probe_assignment(assignment_id)
    if not result:
        logger.info("[%s %s] video assignment probe unavailable; skipping", worker_id[:8], model)
        return 0
    response_commitment = _media_response_commitment(result)
    if response_commitment is None:
        logger.info("[%s %s] video assignment has invalid witnesses; skipping", worker_id[:8], model)
        return 0
    commitments = _verified_probe_evidence(assignment, result, response_commitment)
    if commitments is None:
        return 0

    verdict, detail = await media_prober.score_video_witnesses(
        challenge,
        result.get("witnesses") or [],
        target_worker_id=worker_id,
        allowed_origins=Settings.MEDIA_ALLOWED_ORIGINS,
        max_bytes=Settings.MEDIA_MAX_BYTES,
        fetch_timeout_s=Settings.MEDIA_FETCH_TIMEOUT_S,
        decode_timeout_s=Settings.VIDEO_DECODE_TIMEOUT_S,
        phash_tolerance=Settings.VIDEO_PHASH_TOLERANCE,
        motion_tolerance=Settings.VIDEO_MOTION_TOLERANCE,
        latency_budget_s=Settings.VIDEO_LATENCY_BUDGET_S,
    )
    if verdict == "inconclusive":
        logger.info(
            "[%s %s] video assignment inconclusive (%s); skipping",
            worker_id[:8],
            model,
            detail.get("reason", "unknown"),
        )
        return 0
    if verdict not in attest.VALID_VERDICTS:
        logger.warning("video scorer returned an invalid verdict; skipping")
        return 0

    candidate = next(
        (
            witness
            for witness in result.get("witnesses", [])
            if witness.get("role") == "candidate"
            and str(witness.get("worker_id") or "") == worker_id
        ),
        None,
    )
    if not candidate:
        return 0
    latency_ms = int(candidate["latency_ms"])
    canary = {
        "kind": canary_kind,
        "nonce": grid_nonce,
        "prompt": _prompt_commitment_text(assignment),
    }
    body = attest.build(
        worker_id=worker_id,
        model=model,
        canary=canary,
        verdict=verdict,
        latency_ms=latency_ms,
        ts=int(time.time()),
        modality="video",
        capability=capability,
        response_text=response_commitment,
        assignment_id=assignment_id,
        probe_group_id=str(assignment.get("probe_group_id") or ""),
        grid_nonce=grid_nonce,
    )
    body.update(commitments)
    logger.info(
        "[%s %s] video assignment -> %s (%dms)",
        worker_id[:8],
        model,
        verdict,
        latency_ms,
    )
    return await _promote_and_submit(
        grid,
        outbox,
        assignment_id,
        attest.sign(body),
    )


async def probe_round(
    grid: GridClient,
    round_index: int,
    outbox: AttestationOutbox | None = None,
) -> int:
    """Run one probe round and return the number of attestations accepted by Core."""
    del round_index
    outbox = outbox or AttestationOutbox(Settings.STATE_DB_PATH)
    accepted = await _flush_outbox(grid, outbox)
    assignments = await grid.validator_assignments(limit=5, modality="text")
    if "image.fidelity.v1" in attest.runtime_capabilities():
        assignments.extend(await grid.validator_assignments(limit=2, modality="image"))
    if "video.contract.v1" in attest.runtime_capabilities():
        assignments.extend(await grid.validator_assignments(limit=2, modality="video"))
    tracked_attestations = outbox.tracked_attestation_assignment_ids()
    for assignment in assignments:
        assignment_id = str(assignment.get("assignment_id") or "")
        if not assignment_id or assignment_id in tracked_attestations:
            continue
        try:
            outbox.journal_assignment(assignment)
        except (TypeError, ValueError) as exc:
            logger.error("refusing invalid assignment journal entry: %s", exc)

    pending_assignments = outbox.pending_assignments()
    if not pending_assignments:
        logger.info("no Grid-issued assignments available; fail-closed round performed no probe")
        return accepted
    results = await asyncio.gather(
        *(_probe_assignment(grid, assignment, outbox) for assignment in pending_assignments),
        return_exceptions=True,
    )
    completed = 0
    still_journaled = outbox.journaled_assignment_ids()
    for assignment, result in zip(pending_assignments, results, strict=True):
        assignment_id = str(assignment.get("assignment_id") or "")
        if isinstance(result, BaseException):
            logger.error(
                "assignment %s probe raised %s",
                assignment_id[:12],
                type(result).__name__,
            )
        else:
            completed += int(result)
        if assignment_id in still_journaled and (isinstance(result, BaseException) or result == 0):
            dead = outbox.assignment_failed(
                assignment_id,
                max_attempts=Settings.ASSIGNMENT_MAX_ATTEMPTS,
                max_age_seconds=Settings.ASSIGNMENT_MAX_AGE_S,
            )
            if dead:
                logger.error(
                    "assignment %s exhausted recovery policy and was dead-lettered",
                    assignment_id[:12],
                )
    return accepted + completed


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
    next_update_check = 0.0
    try:
        while True:
            try:
                await grid.heartbeat()
                await probe_round(grid, round_index, outbox)
            except Exception as e:
                logger.error(f"probe round failed: {e}", exc_info=True)
            if Settings.UPDATE_CHECK_ENABLED and time.monotonic() >= next_update_check:
                notice = await update_check.check_for_update()
                if notice is not None:
                    logger.warning(
                        "Validator update available: %s -> %s (%s). Upgrade with the "
                        "checksum-verifying installer; updates are never installed automatically.",
                        notice.current_tag,
                        notice.latest_tag,
                        notice.url,
                    )
                next_update_check = time.monotonic() + Settings.UPDATE_CHECK_INTERVAL_S
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
