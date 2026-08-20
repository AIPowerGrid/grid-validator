# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Thin async client for the Grid's validator-only endpoints."""

import logging

import httpx

from .config import Settings

logger = logging.getLogger("validator.grid")


def _default_capabilities(error: str = "") -> dict:
    return {
        "available": False,
        "validator_api_version": "unknown",
        "mode": "unavailable",
        "economic_effect": "none",
        "targeted_probe_enabled": False,
        "features": {
            "attest": False,
            "registration": False,
            "heartbeat": False,
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
        # Core accepts both Grid-native `apikey` and bearer auth. Send both for
        # transport compatibility; the key itself has validator-only scopes.
        headers = {
            "apikey": Settings.VALIDATOR_API_KEY,
            "Authorization": f"Bearer {Settings.VALIDATOR_API_KEY}",
        }
        self._http = httpx.AsyncClient(
            base_url=Settings.GRID_API_URL.rstrip("/"),
            headers=headers,
            timeout=Settings.PROBE_TIMEOUT_S + 5,
        )

    async def validator_capabilities(self) -> dict:
        """Return the grid's advertised validator feature flags.

        Older cores will not expose this endpoint. The caller receives
        conservative defaults and must not probe without assignments.
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

        Missing assignment endpoints fail closed: callers perform no probe.
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

    async def register_validator(self, envelope: dict) -> dict:
        """Register this node's wallet and software capabilities with Core."""
        r = await self._http.post("/v1/validator/register", json=envelope, timeout=10)
        r.raise_for_status()
        return r.json()

    async def validator_registration(self) -> dict:
        """Return this key's active registration, or an unavailable status."""
        try:
            r = await self._http.get("/v1/validator/registration", timeout=10)
            if r.status_code in (403, 404):
                return {"available": False, "status": "unregistered", "error": r.text}
            r.raise_for_status()
            return {"available": True, **r.json()}
        except httpx.HTTPError as exc:
            return {"available": False, "status": "unavailable", "error": str(exc)}

    async def heartbeat(self) -> dict:
        """Refresh the active validator's liveness and software metadata."""
        from . import __version__
        from .attest import VALIDATOR_CAPABILITIES

        r = await self._http.post(
            "/v1/validator/heartbeat",
            json={
                "software_version": __version__,
                "capabilities": VALIDATOR_CAPABILITIES,
            },
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    async def list_workers(self) -> list[dict]:
        """Return active worker inventory for the local dashboard only."""
        try:
            r = await self._http.get("/v1/validator/workers", timeout=10)
            if r.status_code == 200:
                data = r.json()
                if not data.get("targeted_probe_enabled"):
                    logger.info("grid validator worker inventory is not targetable")
                    return []
                return list(data.get("workers", []))
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
