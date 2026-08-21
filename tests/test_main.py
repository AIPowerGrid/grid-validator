import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from eth_account import Account

from validator import main
from validator.config import Settings
from validator.outbox import AttestationOutbox

TEST_ACCOUNT = Account.from_key("0x" + "11" * 32)


class ProbeRoundTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.outbox = AttestationOutbox(os.path.join(self.tmp.name, "state.sqlite3"))

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def _assignment():
        return {
            "assignment_id": "asg_1",
            "probe_group_id": "prg_1",
            "grid_nonce": "grid-nonce-1",
            "target_worker_id": "worker-1",
            "model": "qwen3-32b",
            "modality": "text",
            "capability": "text.basic.v1",
            "canary_kind": "math.add",
            "challenge": {
                "kind": "math.add",
                "prompt": "What is 19 + 23? Reply with only the number.",
                "expected_hash": hashlib.sha256(b"42").hexdigest(),
            },
        }

    @classmethod
    def _result(cls, **overrides):
        assignment = cls._assignment()
        prompt_hash = hashlib.sha256(
            assignment["challenge"]["prompt"].encode("utf-8")
        ).hexdigest()
        response_hash = hashlib.sha256(b"42").hexdigest()
        evidence = {
            "assignment_id": assignment["assignment_id"],
            "probe_group_id": assignment["probe_group_id"],
            "grid_nonce": assignment["grid_nonce"],
            "worker_id": assignment["target_worker_id"],
            "model": assignment["model"],
            "modality": assignment["modality"],
            "capability": assignment["capability"],
            "canary_kind": assignment["canary_kind"],
            "prompt_hash": prompt_hash,
            "response_hash": response_hash,
        }
        evidence_hash = hashlib.sha256(
            json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        result = {
            "status": "completed",
            "output_text": "42",
            "assignment_id": assignment["assignment_id"],
            "probe_group_id": assignment["probe_group_id"],
            "grid_nonce": assignment["grid_nonce"],
            "target_worker_id": assignment["target_worker_id"],
            "model": assignment["model"],
            "modality": assignment["modality"],
            "capability": assignment["capability"],
            "canary_kind": assignment["canary_kind"],
            "prompt_hash": prompt_hash,
            "response_hash": response_hash,
            "evidence_hash": evidence_hash,
        }
        result.update(overrides)
        return result

    async def test_assignment_probe_submits_grid_bound_attestation(self):
        class FakeGrid:
            def __init__(self):
                self.probed = []
                self.submitted = []

            async def validator_assignments(self, **_kwargs):
                return [ProbeRoundTests._assignment()]

            async def probe_assignment(self, assignment_id):
                self.probed.append(assignment_id)
                return ProbeRoundTests._result()

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
            attempted = await main.probe_round(grid, 0, self.outbox)

        self.assertEqual(attempted, 1)
        self.assertEqual(grid.probed, ["asg_1"])
        payload = grid.submitted[0]["payload"]
        self.assertEqual(payload["assignment_source"], "grid")
        self.assertEqual(payload["assignment_id"], "asg_1")
        self.assertEqual(payload["probe_group_id"], "prg_1")
        self.assertEqual(payload["grid_nonce"], "grid-nonce-1")
        self.assertEqual(payload["worker_id"], "worker-1")
        self.assertEqual(payload["capability"], "text.basic.v1")
        self.assertEqual(payload["verdict"], "healthy")
        self.assertEqual(payload["prompt_hash"], ProbeRoundTests._result()["prompt_hash"])
        self.assertEqual(payload["response_hash"], ProbeRoundTests._result()["response_hash"])
        self.assertEqual(payload["evidence_hash"], ProbeRoundTests._result()["evidence_hash"])
        self.assertIsNotNone(grid.submitted[0]["signature"])

    async def test_assignment_probe_rejects_mismatched_core_commitment(self):
        class FakeGrid:
            def __init__(self):
                self.submitted = []

            async def validator_assignments(self, **_kwargs):
                return [ProbeRoundTests._assignment()]

            async def probe_assignment(self, _assignment_id):
                return ProbeRoundTests._result(response_hash="f" * 64)

            async def submit_attestation(self, envelope):
                self.submitted.append(envelope)
                return True

        grid = FakeGrid()
        self.assertEqual(await main.probe_round(grid, 0, self.outbox), 0)
        self.assertEqual(grid.submitted, [])

    async def test_assignment_probe_rejects_wrong_target_binding(self):
        class FakeGrid:
            def __init__(self):
                self.submitted = []

            async def validator_assignments(self, **_kwargs):
                return [ProbeRoundTests._assignment()]

            async def probe_assignment(self, _assignment_id):
                return ProbeRoundTests._result(target_worker_id="worker-2")

            async def submit_attestation(self, envelope):
                self.submitted.append(envelope)
                return True

        grid = FakeGrid()
        self.assertEqual(await main.probe_round(grid, 0, self.outbox), 0)
        self.assertEqual(grid.submitted, [])

    async def test_no_assignment_fails_closed_without_inventory_or_model_fallback(self):
        class FakeGrid:
            async def validator_assignments(self, **_kwargs):
                return []

        self.assertEqual(await main.probe_round(FakeGrid(), 0, self.outbox), 0)

    async def test_failed_delivery_is_replayed_without_reprobing(self):
        class FakeGrid:
            def __init__(self):
                self.probes = 0
                self.submissions = 0

            async def validator_assignments(self, **_kwargs):
                return [ProbeRoundTests._assignment()] if self.probes == 0 else []

            async def probe_assignment(self, _assignment_id):
                self.probes += 1
                return ProbeRoundTests._result()

            async def submit_attestation(self, _envelope):
                self.submissions += 1
                return self.submissions > 1

        grid = FakeGrid()
        with (
            patch.object(Settings, "VALIDATOR_WALLET", TEST_ACCOUNT.address.lower()),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", TEST_ACCOUNT.key.hex()),
        ):
            self.assertEqual(await main.probe_round(grid, 0, self.outbox), 0)
            self.assertEqual(self.outbox.counts(), {"pending": 1, "dead": 0})
            self.assertEqual(await main.probe_round(grid, 1, self.outbox), 1)

        self.assertEqual(grid.probes, 1)
        self.assertEqual(grid.submissions, 2)
        self.assertEqual(self.outbox.counts(), {"pending": 0, "dead": 0})


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
