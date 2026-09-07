# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Thin async client for the Grid's validator-only endpoints."""

import hashlib
import json
import logging

import httpx

from .config import Settings

logger = logging.getLogger("validator.grid")


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate response key")
        result[key] = value
    return result


def _receipt_matches(receipt: object, attestation: dict) -> bool:
    """A transport success is not a committed receipt for this envelope."""
    if not isinstance(receipt, dict):
        return False
    payload = attestation.get("payload")
    if not isinstance(payload, dict):
        return False
    signature = attestation.get("signature")
    if signature is not None and not isinstance(signature, str):
        return False
    if signature:
        signature = signature.strip()
        if not signature.startswith("0x"):
            signature = "0x" + signature
    canonical = json.dumps(
        {"payload": payload, "signature": signature or None},
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    authoritative = payload.get("assignment_source") == "grid" or bool(
        payload.get("grid_nonce")
    )
    if (
        receipt.get("status") not in ("accepted", "duplicate")
        or type(receipt.get("id")) is not int
        or receipt["id"] <= 0
        or receipt.get("attestation_hash")
        != hashlib.sha256(canonical.encode()).hexdigest()
        or receipt.get("authority") != ("authoritative" if authoritative else "preview")
    ):
        return False
    if authoritative:
        return (
            bool(payload.get("assignment_id"))
            and bool(payload.get("probe_group_id"))
            and receipt.get("assignment_id") == payload["assignment_id"]
            and receipt.get("probe_group_id") == payload["probe_group_id"]
            and receipt.get("signature_status") == "verified"
        )
    return (
        receipt.get("assignment_id") is None and receipt.get("probe_group_id") is None
    )


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
            fallback["targeted_probe_enabled"] = bool(
                data.get("targeted_probe_enabled")
            )
            fallback.setdefault("error", "")
            return fallback
        except httpx.HTTPError as e:
            logger.info(f"validator capabilities unavailable: {e}")
            return _default_capabilities(str(e))

    async def validator_scorecards(
        self, *, limit: int = 10, since_hours: int = 24
    ) -> dict:
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

    async def validator_assignments(
        self, *, limit: int = 5, modality: str = "text"
    ) -> list[dict]:
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
        """Return this key's active/suspended registration, or an unavailable status."""
        try:
            r = await self._http.get("/v1/validator/registration", timeout=10)
            if r.status_code in (403, 404):
                return {"available": False, "status": "unregistered", "error": r.text}
            r.raise_for_status()
            return {"available": True, **r.json()}
        except httpx.HTTPError as exc:
            return {"available": False, "status": "unavailable", "error": str(exc)}

    async def suspend_validator(self, envelope: dict) -> dict:
        """Self-suspend using the registered signing wallet."""
        r = await self._http.post("/v1/validator/suspend", json=envelope, timeout=10)
        r.raise_for_status()
        return r.json()

    async def rotate_validator(self, envelope: dict) -> dict:
        """Rotate to the configured wallet after it is linked to this Grid account."""
        r = await self._http.post("/v1/validator/rotate", json=envelope, timeout=10)
        r.raise_for_status()
        return r.json()

    async def heartbeat(self) -> dict:
        """Refresh the active validator's liveness and software metadata."""
        from . import __release_tag__
        from .attest import runtime_capabilities

        r = await self._http.post(
            "/v1/validator/heartbeat",
            json={
                "software_version": __release_tag__,
                "capabilities": runtime_capabilities(),
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
            data = r.json(object_pairs_hook=_unique_object)
            if (
                not isinstance(data, dict)
                or data.get("status") != "completed"
                or data.get("assignment_id") != assignment_id
            ):
                return None
            return data
        except (httpx.HTTPError, ValueError, RecursionError) as exc:
            logger.warning("probe response unavailable (%s)", type(exc).__name__)
            return None

    async def submit_attestation(self, attestation: dict) -> bool:
        """Return True only for a bound accepted/duplicate receipt from Core."""
        try:
            r = await self._http.post(
                "/v1/validator/attest", json=attestation, timeout=10
            )
            if r.status_code == 404:
                logger.warning(
                    "grid /v1/validator/attest not deployed yet - attestation remains queued"
                )
                return False
            r.raise_for_status()
            if r.status_code != 200 or not _receipt_matches(
                r.json(object_pairs_hook=_unique_object), attestation
            ):
                logger.warning(
                    "unverified attestation receipt; evidence remains queued"
                )
                return False
            return True
        except (httpx.HTTPError, ValueError, RecursionError) as exc:
            logger.warning("attestation delivery failed (%s)", type(exc).__name__)
            return False

    async def aclose(self):
        await self._http.aclose()
