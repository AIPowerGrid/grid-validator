import unittest
from unittest.mock import patch

from validator.config import Settings
from validator.dashboard import _grid_snapshot, _render_html, _short, collect_status


class DashboardTests(unittest.TestCase):
    def test_short_keeps_empty_values(self):
        self.assertEqual(_short(""), "")

    def test_short_keeps_short_values(self):
        self.assertEqual(_short("0x1234"), "0x1234")

    def test_short_redacts_long_values(self):
        self.assertEqual(_short("0x1234567890abcdef"), "0x1234...cdef")

    def test_render_html_includes_capabilities_panel(self):
        self.assertIn("Validator Capabilities", _render_html())

    def test_render_html_includes_scorecards_panel(self):
        html = _render_html()
        self.assertIn("Recent Evidence Scorecards", html)
        self.assertIn("scorecard-table", html)
        self.assertIn("function esc", html)

    def test_collect_status_does_not_call_grid_when_config_invalid(self):
        with (
            patch.object(Settings, "VALIDATOR_API_KEY", ""),
            patch("validator.dashboard.GridClient", side_effect=AssertionError("grid called")),
        ):
            data = collect_status()

        self.assertFalse(data["config"]["ok"])
        self.assertEqual(data["grid"]["error"], "config-invalid")


class DashboardGridSnapshotTests(unittest.IsolatedAsyncioTestCase):
    async def test_grid_snapshot_preserves_capabilities_on_model_error(self):
        class FakeGrid:
            async def validator_capabilities(self):
                return {"available": True, "mode": "evidence_only"}

            async def validator_scorecards(self, **_kwargs):
                return {"available": True, "items": [{"subject_id": "worker-1"}]}

            async def list_models(self):
                raise RuntimeError("models down")

            async def aclose(self):
                return None

        with patch("validator.dashboard.GridClient", return_value=FakeGrid()):
            data = await _grid_snapshot()

        self.assertFalse(data["ok"])
        self.assertEqual(data["capabilities"]["mode"], "evidence_only")
        self.assertTrue(data["scorecards"]["available"])
        self.assertIn("models down", data["error"])

    async def test_grid_snapshot_collects_scorecards(self):
        class FakeGrid:
            async def validator_capabilities(self):
                return {"available": True, "mode": "evidence_only"}

            async def validator_scorecards(self, **_kwargs):
                return {
                    "available": True,
                    "count": 1,
                    "items": [{"subject_id": "worker-1", "total": 2}],
                }

            async def list_models(self):
                return ["qwen3-27b"]

            async def list_workers(self):
                return []

            async def aclose(self):
                return None

        with patch("validator.dashboard.GridClient", return_value=FakeGrid()):
            data = await _grid_snapshot()

        self.assertTrue(data["ok"])
        self.assertEqual(data["scorecards"]["count"], 1)
        self.assertEqual(data["scorecards"]["items"][0]["subject_id"], "worker-1")


if __name__ == "__main__":
    unittest.main()
