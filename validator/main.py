# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Validator node entrypoint: optional stake check, then probe in a loop.

Run:  python -m validator.main   (from the grid-validator/ dir, with a .env)
"""

import asyncio
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


def _worker_supports_text(worker: dict) -> bool:
    """Conservative text capability check for targeted V0 probes."""
    text_signal = False

    job_types = [str(j).lower() for j in (worker.get("job_types") or [])]
    if job_types:
        if not any(j in {"text", "llm", "chat"} for j in job_types):
            return False
        text_signal = True

    api_formats = [str(f).lower() for f in (worker.get("api_formats") or [])]
    if api_formats:
        if not any("chat" in f or "text" in f or "openai" in f for f in api_formats):
            return False
        text_signal = True

    models = [str(m) for m in (worker.get("models") or [])]
    if models:
        if not any(prober.is_text_model(m) for m in models):
            return False
        text_signal = True

    return text_signal


async def _probe_model(grid: GridClient, model: str, round_index: int) -> int:
    """V0 model-routed canary.

    This cannot attribute evidence to a single worker. Failed V0 canaries are
    observations only and must not create strikes or slashing.
    """
    canary = prober.make_canary(round_index)
    try:
        text, latency = await grid.chat(model, canary["prompt"])
    except Exception as e:
        logger.warning(f"[{model}] canary errored: {e}")
        text, latency = "", Settings.PROBE_TIMEOUT_S
    verdict = prober.score(canary, text, latency)
    logger.info(f"[{model}] {canary['kind']} canary → {verdict} ({latency:.1f}s)")

    att = attest.build(
        worker_id="",  # unknown in v0 (no targeted probe yet)
        model=model,
        canary=canary,
        verdict=verdict,
        latency_ms=int(latency * 1000),
        ts=int(time.time()),
        response_text=text,
    )
    await grid.submit_attestation(attest.sign(att))
    return 1


async def _probe_worker(grid: GridClient, worker: dict, round_index: int) -> int:
    """Layer 3b: targeted probe of a specific worker (when the grid exposes it)."""
    canary = prober.make_canary(round_index)
    wid = worker.get("worker_id")
    if not wid:
        logger.info("targeted worker inventory row missing worker_id; skipping")
        return 0
    model = (worker.get("models") or ["unknown"])[0]
    payload = {
        "prompt": canary["prompt"],
        "max_tokens": Settings.PROBE_MAX_TOKENS,
        "stream": False,
    }
    t0 = time.time()
    res = await grid.probe_worker(wid, payload)
    latency = time.time() - t0
    if not res or "text" not in res:
        logger.info(f"[{wid[:8]} {model}] targeted probe unavailable; skipping attestation")
        return 0
    text = (res or {}).get("text", "") if res else ""
    verdict = prober.score(canary, text, latency)
    logger.info(f"[{wid[:8]} {model}] {canary['kind']} → {verdict} ({latency:.1f}s)")
    att = attest.build(
        wid,
        model,
        canary,
        verdict,
        int(latency * 1000),
        int(time.time()),
        response_text=text,
    )
    await grid.submit_attestation(attest.sign(att))
    return 1


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

    verdict = str(res.get("probe_verdict") or prober.score(canary, text, latency))
    if verdict not in attest.VALID_VERDICTS:
        logger.info(
            f"[{str(worker_id)[:8]} {model}] assignment probe returned invalid verdict; skipping"
        )
        return 0
    logger.info(
        f"[{str(worker_id)[:8]} {model}] assignment {canary['kind']} → {verdict} "
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
    # Core stores the probe evidence hash when the hard-targeted worker reply
    # arrives. Echo it exactly so authoritative attestation storage can verify
    # this claim is bound to that probe, not just to a nonce.
    for key in ("prompt_hash", "response_hash", "evidence_hash"):
        if res.get(key):
            att[key] = res[key]
    await grid.submit_attestation(attest.sign(att))
    return 1


async def probe_round(grid: GridClient, round_index: int) -> int:
    """Run one full probe round and return the number of canaries attempted."""
    validator_assignments = getattr(grid, "validator_assignments", None)
    if validator_assignments:
        assignments = await validator_assignments(limit=5, modality="text")
        if assignments:
            results = await asyncio.gather(*(_probe_assignment(grid, a) for a in assignments))
            return sum(results)

    workers = await grid.list_workers()
    text_workers = [w for w in workers if _worker_supports_text(w)]
    if text_workers:  # Layer 3b: targeted, per-worker
        results = await asyncio.gather(
            *(_probe_worker(grid, w, round_index + i) for i, w in enumerate(text_workers))
        )
        return sum(results)
    else:  # v0: model-routed (text models only — see prober)
        if workers:
            logger.info("targeted inventory had no text-capable workers; using model-routed v0 probes")
        models = [m for m in await grid.list_models() if prober.is_text_model(m)]
        if not models:
            logger.warning("no text-compatible models visible; no V0 canary submitted")
            return 0
        results = await asyncio.gather(
            *(_probe_model(grid, m, round_index + i) for i, m in enumerate(models))
        )
        return sum(results)


async def run() -> None:
    Settings.validate()
    # Stake gate — refuse to run unstaked (unless REQUIRE_STAKE=false for dev).
    try:
        staking.assert_eligible()
    except staking.NotDeployed:
        if Settings.REQUIRE_STAKE:
            raise RuntimeError(
                "Stake contract not deployed and REQUIRE_STAKE=true — exiting. "
                "Set VALIDATOR_REQUIRE_STAKE=false to run pre-launch."
            )

    grid = GridClient()
    logger.info(
        f"Validator online → {Settings.GRID_API_URL} "
        f"(probe every {Settings.PROBE_INTERVAL_S}s)"
    )
    round_index = 0
    try:
        while True:
            try:
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
