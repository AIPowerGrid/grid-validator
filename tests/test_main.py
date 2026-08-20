import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from eth_account import Account

from validator import main
from validator.config import Settings

TEST_ACCOUNT = Account.from_key("0x" + "11" * 32)


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
            patch.object(Settings, "VALIDATOR_WALLET", TEST_ACCOUNT.address.lower()),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", TEST_ACCOUNT.key.hex()),
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
        self.assertIsNotNone(grid.submitted[0]["signature"])

    async def test_no_assignment_fails_closed_without_inventory_or_model_fallback(self):
        class FakeGrid:
            async def validator_assignments(self, **_kwargs):
                return []

        self.assertEqual(await main.probe_round(FakeGrid(), 0), 0)


class RunStartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_raises_when_required_stake_contract_is_missing(self):
        with (
            patch("validator.config.Settings.validate", return_value=None),
            patch.object(Settings, "VALIDATOR_WALLET", TEST_ACCOUNT.address.lower()),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", TEST_ACCOUNT.key.hex()),
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
            patch.object(Settings, "VALIDATOR_WALLET", TEST_ACCOUNT.address.lower()),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", TEST_ACCOUNT.key.hex()),
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
