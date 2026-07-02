import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from validator import main
from validator.config import Settings


def _echo_from_prompt(prompt: str) -> str:
    return prompt.rsplit(":", 1)[-1].strip()


class ProbeRoundTests(unittest.IsolatedAsyncioTestCase):
    async def test_assignment_probe_submits_grid_bound_attestation(self):
        class FakeGrid:
            def __init__(self):
                self.probed = []
                self.submitted = []

            async def validator_assignments(self, **_kwargs):
                return [{
                    "assignment_id": "asg_1",
                    "grid_nonce": "grid-nonce-1",
                    "target_worker_id": "worker-1",
                    "model": "qwen3-32b",
                    "modality": "text",
                    "capability": "text.basic.v1",
                    "canary_kind": "math.add",
                    "challenge": {
                        "kind": "math.add",
                        "prompt": "What is 19 + 23? Reply with only the number.",
                        "expected": "42",
                    },
                }]

            async def probe_assignment(self, assignment_id):
                self.probed.append(assignment_id)
                return {
                    "status": "completed",
                    "output_text": "42",
                    "probe_verdict": "slow",
                    "prompt_hash": "a" * 64,
                    "response_hash": "b" * 64,
                    "evidence_hash": "c" * 64,
                }

            async def submit_attestation(self, envelope):
                self.submitted.append(envelope)
                return True

            async def list_workers(self):
                raise AssertionError("assignments should be preferred over inventory")

        grid = FakeGrid()
        with (
            patch.object(Settings, "VALIDATOR_WALLET", ""),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", ""),
        ):
            attempted = await main.probe_round(grid, 0)

        self.assertEqual(attempted, 1)
        self.assertEqual(grid.probed, ["asg_1"])
        payload = grid.submitted[0]["payload"]
        self.assertEqual(payload["assignment_source"], "grid")
        self.assertEqual(payload["assignment_id"], "asg_1")
        self.assertEqual(payload["grid_nonce"], "grid-nonce-1")
        self.assertEqual(payload["worker_id"], "worker-1")
        self.assertEqual(payload["capability"], "text.basic.v1")
        self.assertEqual(payload["verdict"], "slow")
        self.assertEqual(payload["prompt_hash"], "a" * 64)
        self.assertEqual(payload["response_hash"], "b" * 64)
        self.assertEqual(payload["evidence_hash"], "c" * 64)
        self.assertIsNone(grid.submitted[0]["signature"])

    async def test_model_routed_probe_filters_media_models_and_attests_text(self):
        class FakeGrid:
            def __init__(self):
                self.chat_models = []
                self.submitted = []

            async def list_workers(self):
                return []

            async def list_models(self):
                return ["stable-diffusion-xl", "qwen3-32b"]

            async def chat(self, model, prompt):
                self.chat_models.append(model)
                return _echo_from_prompt(prompt), 0.1

            async def submit_attestation(self, envelope):
                self.submitted.append(envelope)
                return True

        grid = FakeGrid()
        with (
            patch.object(Settings, "VALIDATOR_WALLET", ""),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", ""),
        ):
            attempted = await main.probe_round(grid, 0)

        self.assertEqual(grid.chat_models, ["qwen3-32b"])
        self.assertEqual(attempted, 1)
        self.assertEqual(len(grid.submitted), 1)
        payload = grid.submitted[0]["payload"]
        self.assertEqual(payload["worker_id"], "")
        self.assertEqual(payload["model"], "qwen3-32b")
        self.assertEqual(payload["modality"], "text")
        self.assertEqual(payload["capability"], "text.basic.v0")
        self.assertEqual(payload["verdict"], "healthy")
        self.assertEqual(payload["assignment_source"], "validator_v0")
        self.assertRegex(payload["assignment_id"], r"^validator-v0:[0-9a-f]{32}$")
        self.assertRegex(payload["epoch"], r"^\d{10}$")
        self.assertRegex(payload["prompt_hash"], r"^[0-9a-f]{64}$")
        self.assertRegex(payload["response_hash"], r"^[0-9a-f]{64}$")
        self.assertRegex(payload["evidence_hash"], r"^[0-9a-f]{64}$")
        self.assertNotIn("prompt", payload)
        self.assertNotIn("response_text", payload)
        self.assertIsNone(grid.submitted[0]["signature"])

    async def test_targeted_probe_skips_media_workers(self):
        class FakeGrid:
            def __init__(self):
                self.probed = []
                self.submitted = []

            async def list_workers(self):
                return [
                    {
                        "worker_id": "image-worker",
                        "job_types": ["image"],
                        "api_formats": ["comfy"],
                        "models": ["stable-diffusion-xl"],
                    },
                    {
                        "worker_id": "text-worker",
                        "job_types": ["text"],
                        "api_formats": ["openai-chat"],
                        "models": ["qwen3-32b"],
                    },
                ]

            async def probe_worker(self, worker_id, payload):
                self.probed.append((worker_id, payload))
                return {"text": _echo_from_prompt(payload["prompt"])}

            async def submit_attestation(self, envelope):
                self.submitted.append(envelope)
                return True

        grid = FakeGrid()
        with (
            patch.object(Settings, "VALIDATOR_WALLET", ""),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", ""),
        ):
            attempted = await main.probe_round(grid, 0)

        self.assertEqual([worker_id for worker_id, _payload in grid.probed], ["text-worker"])
        self.assertEqual(attempted, 1)
        self.assertEqual(grid.probed[0][1]["max_tokens"], Settings.PROBE_MAX_TOKENS)
        self.assertFalse(grid.probed[0][1]["stream"])
        self.assertEqual(len(grid.submitted), 1)
        self.assertEqual(grid.submitted[0]["payload"]["worker_id"], "text-worker")

    async def test_targeted_inventory_with_no_text_workers_falls_back_to_models(self):
        class FakeGrid:
            def __init__(self):
                self.chat_models = []
                self.probed = []
                self.submitted = []

            async def list_workers(self):
                return [
                    {
                        "worker_id": "image-worker",
                        "job_types": ["image"],
                        "api_formats": ["comfy"],
                        "models": ["flux-dev"],
                    }
                ]

            async def list_models(self):
                return ["qwen3-32b"]

            async def chat(self, model, prompt):
                self.chat_models.append(model)
                return _echo_from_prompt(prompt), 0.1

            async def probe_worker(self, worker_id, payload):
                self.probed.append((worker_id, payload))
                return {"text": ""}

            async def submit_attestation(self, envelope):
                self.submitted.append(envelope)
                return True

        grid = FakeGrid()
        with (
            patch.object(Settings, "VALIDATOR_WALLET", ""),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", ""),
        ):
            attempted = await main.probe_round(grid, 0)

        self.assertEqual(grid.probed, [])
        self.assertEqual(grid.chat_models, ["qwen3-32b"])
        self.assertEqual(attempted, 1)
        self.assertEqual(len(grid.submitted), 1)

    async def test_targeted_probe_without_text_skips_attestation(self):
        class FakeGrid:
            def __init__(self):
                self.submitted = []

            async def probe_worker(self, _worker_id, _payload):
                return {"metadata": "no text"}

            async def submit_attestation(self, envelope):
                self.submitted.append(envelope)
                return True

        grid = FakeGrid()

        attempted = await main._probe_worker(
            grid,
            {
                "worker_id": "text-worker",
                "job_types": ["text"],
                "api_formats": ["openai-chat"],
                "models": ["qwen3-32b"],
            },
            0,
        )

        self.assertEqual(attempted, 0)
        self.assertEqual(grid.submitted, [])

    async def test_targeted_inventory_row_without_worker_id_is_skipped(self):
        class FakeGrid:
            def __init__(self):
                self.submitted = []

            async def probe_worker(self, _worker_id, _payload):
                raise AssertionError("missing worker_id should not be probed")

            async def submit_attestation(self, envelope):
                self.submitted.append(envelope)
                return True

        grid = FakeGrid()

        attempted = await main._probe_worker(
            grid,
            {"job_types": ["text"], "api_formats": ["openai-chat"], "models": ["qwen3-32b"]},
            0,
        )

        self.assertEqual(attempted, 0)
        self.assertEqual(grid.submitted, [])

    async def test_model_routed_probe_returns_zero_when_only_media_models_visible(self):
        class FakeGrid:
            async def list_workers(self):
                return []

            async def list_models(self):
                return ["stable-diffusion-xl", "flux-dev"]

            async def chat(self, _model, _prompt):
                raise AssertionError("media models should not receive text canaries")

            async def submit_attestation(self, _envelope):
                raise AssertionError("no canary means no attestation")

        self.assertEqual(await main.probe_round(FakeGrid(), 0), 0)


class WorkerSupportTests(unittest.TestCase):
    def test_worker_supports_text_rejects_empty_preview_metadata(self):
        self.assertFalse(main._worker_supports_text({}))

    def test_worker_supports_text_rejects_media_job_type(self):
        self.assertFalse(main._worker_supports_text({"job_types": ["image"], "models": ["qwen3-32b"]}))

    def test_worker_supports_text_rejects_media_model_hint(self):
        self.assertFalse(main._worker_supports_text({"models": ["stable-diffusion-xl"]}))

    def test_worker_supports_text_accepts_text_job_type(self):
        self.assertTrue(main._worker_supports_text({"job_types": ["text"]}))


class RunStartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_raises_when_required_stake_contract_is_missing(self):
        with (
            patch("validator.config.Settings.validate", return_value=None),
            patch.object(Settings, "REQUIRE_STAKE", True),
            patch(
                "validator.staking.assert_eligible",
                side_effect=main.staking.NotDeployed("missing staking contract"),
            ),
            patch("validator.main.GridClient", side_effect=AssertionError("grid should not start")),
        ):
            with self.assertRaisesRegex(RuntimeError, "Stake contract not deployed"):
                await main.run()

    async def test_run_raises_required_stake_runtime_failures_before_grid_start(self):
        with (
            patch("validator.config.Settings.validate", return_value=None),
            patch.object(Settings, "REQUIRE_STAKE", True),
            patch(
                "validator.staking.assert_eligible",
                side_effect=RuntimeError("Insufficient stake"),
            ),
            patch("validator.main.GridClient", side_effect=AssertionError("grid should not start")),
        ):
            with self.assertRaisesRegex(RuntimeError, "Insufficient stake"):
                await main.run()


class MainModuleEntrypointTests(unittest.TestCase):
    def test_python_m_validator_main_reports_config_errors_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = os.path.join(tmp, ".env")
            with open(env_path, "w", encoding="utf-8") as fh:
                fh.write(
                    "GRID_API_URL=http://127.0.0.1:1\n"
                    "VALIDATOR_API_KEY=grid-key\n"
                    "VALIDATOR_REQUIRE_STAKE=false\n"
                    "PROBE_INTERVAL_S=abc\n"
                )
            env = os.environ.copy()
            env["VALIDATOR_ENV"] = env_path
            result = subprocess.run(
                [sys.executable, "-m", "validator.main"],
                cwd=os.getcwd(),
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Startup:", result.stdout)
        self.assertIn("PROBE_INTERVAL_S must be an integer", result.stdout)
        self.assertNotIn("Traceback", result.stdout)


if __name__ == "__main__":
    unittest.main()
