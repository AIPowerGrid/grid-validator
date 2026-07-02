# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Thin async client for the grid's validator + OpenAI-compatible endpoints."""

import logging

import httpx

from .config import Settings

logger = logging.getLogger("validator.grid")


def _default_capabilities(error: str = "") -> dict:
    return {
        "available": False,
        "validator_api_version": "unknown",
        "mode": "model_routed_v0",
        "economic_effect": "none",
        "targeted_probe_enabled": False,
        "features": {
            "attest": False,
            "worker_inventory": False,
            "targeted_probe": False,
            "assignments": False,
            "worker_scorecards": False,
            "validator_rewards": False,
            "staking_required": False,
            "epoch_roots": False,
        },
        "endpoints": {},
        "notes": [],
        "error": error,
    }


def _default_scorecards(error: str = "") -> dict:
    return {
        "available": False,
        "items": [],
        "count": 0,
        "window_hours": 0,
        "economic_effect": "none",
        "error": error,
    }


def _default_assignments(error: str = "") -> dict:
    return {
        "available": False,
        "assignments": [],
        "count": 0,
        "economic_effect": "none",
        "error": error,
    }


class GridClient:
    def __init__(self):
        # Core accepts both Grid-native `apikey` and OpenAI-compatible bearer
        # auth. Send both so validator binaries work across the whole Grid
        # surface and match the operator docs/runbooks.
        headers = {
            "apikey": Settings.VALIDATOR_API_KEY,
            "Authorization": f"Bearer {Settings.VALIDATOR_API_KEY}",
        }
        self._http = httpx.AsyncClient(
            base_url=Settings.GRID_API_URL.rstrip("/"),
            headers=headers,
            timeout=Settings.PROBE_TIMEOUT_S + 5,
        )

    async def list_models(self) -> list[str]:
        r = await self._http.get("/v1/models", timeout=10)
        r.raise_for_status()
        return [m["id"] for m in r.json().get("data", [])]

    async def validator_capabilities(self) -> dict:
        """Return the grid's advertised validator feature flags.

        Older cores will not expose this endpoint. That is fine: the caller
        gets conservative defaults and remains in v0 model-routed mode.
        """
        try:
            r = await self._http.get("/v1/validator/capabilities", timeout=10)
            if r.status_code == 404:
                return _default_capabilities("capabilities endpoint not deployed")
            r.raise_for_status()
            data = r.json()
            fallback = _default_capabilities()
            fallback.update(data)
            fallback["available"] = True
            fallback["features"] = {
                **_default_capabilities()["features"],
                **(data.get("features") or {}),
            }
            # `features.targeted_probe` means the API surface may exist;
            # `targeted_probe_enabled` is the rollout/safety switch that says
            # targeting can actually affect per-worker evidence. Keep them
            # separate so half-deployed cores do not look targetable.
            fallback["targeted_probe_enabled"] = bool(data.get("targeted_probe_enabled"))
            fallback.setdefault("error", "")
            return fallback
        except httpx.HTTPError as e:
            logger.info(f"validator capabilities unavailable: {e}")
            return _default_capabilities(str(e))

    async def validator_scorecards(self, *, limit: int = 10, since_hours: int = 24) -> dict:
        """Return aggregate validator evidence if the grid exposes scorecards."""
        try:
            r = await self._http.get(
                "/v1/validator/scorecards",
                params={"limit": limit, "since_hours": since_hours},
                timeout=10,
            )
            if r.status_code == 404:
                return _default_scorecards("scorecards endpoint not deployed")
            if r.status_code == 403:
                return _default_scorecards("scorecards require a v2 validator API key")
            r.raise_for_status()
            data = r.json()
            fallback = _default_scorecards()
            fallback.update(data)
            fallback["available"] = True
            fallback.setdefault("items", [])
            fallback.setdefault("count", len(fallback["items"]))
            fallback.setdefault("economic_effect", "none")
            fallback.setdefault("error", "")
            return fallback
        except httpx.HTTPError as e:
            logger.info(f"validator scorecards unavailable: {e}")
            return _default_scorecards(str(e))

    async def validator_assignments(self, *, limit: int = 5, modality: str = "text") -> list[dict]:
        """Return Grid-issued assignments for authoritative evidence.

        Missing assignment endpoints are normal during rollout; callers fall
        back to preview/model-routed V0 canaries.
        """
        try:
            r = await self._http.get(
                "/v1/validator/assignments",
                params={"limit": limit, "modality": modality},
                timeout=10,
            )
            if r.status_code in (404, 403, 501):
                return []
            r.raise_for_status()
            data = r.json()
            return [a for a in data.get("assignments", []) if a.get("assignment_id")]
        except httpx.HTTPError as e:
            logger.info(f"validator assignments unavailable: {e}")
            return []

    async def list_workers(self) -> list[dict]:
        """Active (worker, models) pairs. Needs the grid validator endpoint;
        falls back to an empty list (v0 mode probes by model instead)."""
        try:
            r = await self._http.get("/v1/validator/workers", timeout=10)
            if r.status_code == 200:
                data = r.json()
                if not data.get("targeted_probe_enabled"):
                    logger.info(
                        "grid validator worker inventory is available but targeted probing is disabled; "
                        "using model-routed v0 probes"
                    )
                    return []
                if "{assignment_id}" in str(data.get("probe_endpoint") or ""):
                    logger.info(
                        "grid validator worker inventory uses assignment-bound probes; "
                        "using /v1/validator/assignments instead of legacy worker probes"
                    )
                    return []
                return [w for w in data.get("workers", []) if w.get("targetable", True)]
        except httpx.HTTPError:
            pass
        return []

    async def probe_assignment(self, assignment_id: str) -> dict | None:
        """Run one Grid-issued assignment through the targeted probe endpoint."""
        try:
            r = await self._http.post(
                f"/v1/validator/probe/{assignment_id}",
                timeout=max(Settings.PROBE_TIMEOUT_S + 15, 30),
            )
            if r.status_code in (404, 501, 503, 504):
                return None
            r.raise_for_status()
            data = r.json()
            if data.get("status") == "error":
                return None
            return data
        except httpx.HTTPError as e:
            logger.warning(f"probe_assignment failed for {assignment_id}: {e}")
            return None

    async def probe_worker(self, worker_id: str, payload: dict) -> dict | None:
        """Targeted probe of one worker (Layer 3b). Returns None if the grid
        doesn't yet expose the endpoint — caller falls back to model-routed."""
        try:
            r = await self._http.post(
                "/v1/validator/probe", json={"worker_id": worker_id, "payload": payload}
            )
            if r.status_code in (404, 501, 503):
                return None
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as e:
            logger.warning(f"probe_worker failed for {worker_id}: {e}")
            return None

    async def chat(self, model: str, prompt: str) -> tuple[str, float]:
        """v0 model-routed canary via the public chat endpoint. Returns
        (text, latency_seconds). Non-streaming so we get the whole answer."""
        import time
        t0 = time.time()
        r = await self._http.post(
            "/v1/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": Settings.PROBE_MAX_TOKENS,
                "stream": False,
            },
        )
        dt = time.time() - t0
        r.raise_for_status()
        text = r.json()["choices"][0]["message"].get("content") or ""
        return text, dt

    async def submit_attestation(self, attestation: dict) -> bool:
        """POST a signed attestation. Returns True on accept (200)."""
        try:
            r = await self._http.post("/v1/validator/attest", json=attestation, timeout=10)
            if r.status_code == 404:
                logger.warning("grid /v1/validator/attest not deployed yet — attestation dropped")
                return False
            r.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.warning(f"submit_attestation failed: {e}")
            return False

    async def aclose(self):
        await self._http.aclose()
