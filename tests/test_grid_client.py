import unittest

import httpx

from validator.config import Settings
from validator.grid_client import GridClient


class _Response:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data or {}

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://api.aipowergrid.io")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("boom", request=request, response=response)


class _HTTP:
    def __init__(self, response):
        self.response = response

    async def get(self, *_args, **_kwargs):
        return self.response

    async def post(self, *_args, **_kwargs):
        return self.response


class GridClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_client_sends_grid_native_and_bearer_auth_headers(self):
        old_key = Settings.VALIDATOR_API_KEY
        old_url = Settings.GRID_API_URL
        old_timeout = Settings.PROBE_TIMEOUT_S
        try:
            Settings.VALIDATOR_API_KEY = "grid-key"
            Settings.GRID_API_URL = "https://api.aipowergrid.io/"
            Settings.PROBE_TIMEOUT_S = 7
            client = GridClient()
            try:
                self.assertEqual(client._http.headers["apikey"], "grid-key")
                self.assertEqual(client._http.headers["authorization"], "Bearer grid-key")
                self.assertEqual(client._http.base_url.host, "api.aipowergrid.io")
            finally:
                await client.aclose()
        finally:
            Settings.VALIDATOR_API_KEY = old_key
            Settings.GRID_API_URL = old_url
            Settings.PROBE_TIMEOUT_S = old_timeout

    async def test_validator_capabilities_merges_safe_defaults(self):
        client = GridClient.__new__(GridClient)
        client._http = _HTTP(_Response(data={
            "validator_api_version": "v0",
            "mode": "evidence_only",
            "features": {
                "attest": True,
                "worker_inventory": True,
                "targeted_probe": False,
            },
            "targeted_probe_enabled": False,
        }))

        caps = await client.validator_capabilities()

        self.assertTrue(caps["available"])
        self.assertEqual(caps["mode"], "evidence_only")
        self.assertTrue(caps["features"]["attest"])
        self.assertTrue(caps["features"]["worker_inventory"])
        self.assertFalse(caps["features"]["assignments"])
        self.assertFalse(caps["targeted_probe_enabled"])

    async def test_validator_capabilities_requires_explicit_targeting_enable(self):
        client = GridClient.__new__(GridClient)
        client._http = _HTTP(_Response(data={
            "features": {
                "targeted_probe": True,
            },
            "targeted_probe_enabled": False,
        }))

        caps = await client.validator_capabilities()

        self.assertTrue(caps["features"]["targeted_probe"])
        self.assertFalse(caps["targeted_probe_enabled"])

    async def test_validator_capabilities_honors_explicit_targeting_enable(self):
        client = GridClient.__new__(GridClient)
        client._http = _HTTP(_Response(data={
            "features": {
                "targeted_probe": True,
            },
            "targeted_probe_enabled": True,
        }))

        caps = await client.validator_capabilities()

        self.assertTrue(caps["features"]["targeted_probe"])
        self.assertTrue(caps["targeted_probe_enabled"])

    async def test_validator_capabilities_falls_back_when_missing(self):
        client = GridClient.__new__(GridClient)
        client._http = _HTTP(_Response(status_code=404, data={"detail": "missing"}))

        caps = await client.validator_capabilities()

        self.assertFalse(caps["available"])
        self.assertEqual(caps["mode"], "unavailable")
        self.assertFalse(caps["features"]["targeted_probe"])
        self.assertFalse(caps["targeted_probe_enabled"])

    async def test_validator_scorecards_merges_success(self):
        client = GridClient.__new__(GridClient)
        client._http = _HTTP(_Response(data={
            "items": [{"subject_id": "worker-1", "total": 2}],
            "count": 1,
            "window_hours": 24,
            "economic_effect": "none",
        }))

        scorecards = await client.validator_scorecards(limit=10, since_hours=24)

        self.assertTrue(scorecards["available"])
        self.assertEqual(scorecards["count"], 1)
        self.assertEqual(scorecards["items"][0]["subject_id"], "worker-1")
        self.assertEqual(scorecards["economic_effect"], "none")

    async def test_validator_scorecards_falls_back_when_missing(self):
        client = GridClient.__new__(GridClient)
        client._http = _HTTP(_Response(status_code=404, data={"detail": "missing"}))

        scorecards = await client.validator_scorecards()

        self.assertFalse(scorecards["available"])
        self.assertEqual(scorecards["items"], [])
        self.assertIn("not deployed", scorecards["error"])

    async def test_list_workers_ignores_inventory_until_targeted_probe_enabled(self):
        client = GridClient.__new__(GridClient)
        client._http = _HTTP(_Response(data={
            "targeted_probe_enabled": False,
            "workers": [{"worker_id": "w1", "models": ["qwen3-27b"], "targetable": False}],
        }))

        self.assertEqual(await client.list_workers(), [])

    async def test_list_workers_returns_inventory_when_assignment_targeting_enabled(self):
        client = GridClient.__new__(GridClient)
        client._http = _HTTP(_Response(data={
            "targeted_probe_enabled": True,
            "workers": [
                {"worker_id": "w1", "models": ["qwen3-27b"], "direct_targetable": False},
                {"worker_id": "w2", "models": ["qwen3-27b"], "direct_targetable": False},
            ],
        }))

        self.assertEqual(
            await client.list_workers(),
            [
                {"worker_id": "w1", "models": ["qwen3-27b"], "direct_targetable": False},
                {"worker_id": "w2", "models": ["qwen3-27b"], "direct_targetable": False},
            ],
        )

    async def test_list_workers_is_dashboard_inventory_only(self):
        client = GridClient.__new__(GridClient)
        client._http = _HTTP(_Response(data={
            "targeted_probe_enabled": True,
            "probe_endpoint": "/v1/validator/probe/{assignment_id}",
            "workers": [{"worker_id": "w1", "models": ["qwen3-27b"], "direct_targetable": False}],
        }))

        self.assertEqual(
            await client.list_workers(),
            [{"worker_id": "w1", "models": ["qwen3-27b"], "direct_targetable": False}],
        )

    async def test_validator_assignments_returns_grid_issued_assignments(self):
        client = GridClient.__new__(GridClient)
        client._http = _HTTP(_Response(data={
            "assignments": [
                {"assignment_id": "asg_1", "grid_nonce": "nonce"},
                {"grid_nonce": "missing-id"},
            ],
            "count": 2,
        }))

        self.assertEqual(
            await client.validator_assignments(limit=5),
            [{"assignment_id": "asg_1", "grid_nonce": "nonce"}],
        )

    async def test_probe_assignment_returns_none_for_unavailable_endpoint(self):
        client = GridClient.__new__(GridClient)
        client._http = _HTTP(_Response(status_code=504, data={"detail": "timeout"}))

        self.assertIsNone(await client.probe_assignment("asg_1"))

if __name__ == "__main__":
    unittest.main()
