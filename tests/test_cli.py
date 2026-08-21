import argparse
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from eth_account import Account

from validator import cli
from validator.config import Settings


class _RegisteredFakeGrid:
    async def register_validator(self, _envelope):
        return {"validator_id": "val_test", "status": "active"}


class CliCapabilityTests(unittest.TestCase):
    def test_command_help_is_safe_for_default_windows_codepage(self):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "cp1252"

        for args in (
            ["--help"],
            ["init", "--help"],
            ["check", "--help"],
            ["dashboard", "--help"],
            ["run", "--help"],
        ):
            with self.subTest(args=args):
                result = subprocess.run(
                    [sys.executable, "-m", "validator", *args],
                    cwd=os.getcwd(),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout.decode("cp1252"))
                self.assertNotIn(b"Traceback", result.stdout)

    def test_capability_lines_are_conservative_when_targeting_disabled(self):
        lines = cli._capability_lines({
            "available": True,
            "validator_api_version": "v0",
            "mode": "evidence_only",
            "economic_effect": "none",
            "targeted_probe_enabled": False,
            "features": {
                "attest": True,
                "worker_inventory": True,
                "targeted_probe": False,
                "assignments": False,
                "validator_rewards": False,
                "staking_required": False,
            },
        })

        text = "\n".join(lines)
        self.assertIn("mode=evidence_only", text)
        self.assertIn("attest=yes", text)
        self.assertIn("targeted=no", text)
        self.assertIn("rewards=no", text)
        self.assertIn("no assignment means no probe", text)

    def test_scorecard_lines_are_explicitly_informational(self):
        lines = cli._scorecard_lines({
            "available": True,
            "count": 2,
            "window_hours": 24,
            "economic_effect": "none",
            "items": [
                {
                    "subject_id": "worker-1",
                    "model": "qwen3-27b",
                    "total": 4,
                    "healthy": 3,
                    "slow": 1,
                    "failed": 0,
                    "avg_latency_ms": 1250.7,
                }
            ],
        })

        text = "\n".join(lines)
        self.assertIn("economic_effect=none", text)
        self.assertIn("worker-1 / qwen3-27b", text)
        self.assertIn("healthy=3", text)
        self.assertIn("avg_latency=1250ms", text)

    def test_scorecard_lines_fall_back_when_unavailable(self):
        lines = cli._scorecard_lines({
            "available": False,
            "error": "scorecards endpoint not deployed",
        })

        self.assertIn("unavailable", lines[0])
        self.assertIn("not deployed", lines[0])


class CliCheckTests(unittest.TestCase):
    def test_check_no_probe_reports_capabilities_without_probe_round(self):
        calls = {"probe": 0}

        class FakeGrid(_RegisteredFakeGrid):
            async def validator_capabilities(self):
                return {
                    "available": True,
                    "validator_api_version": "v0",
                    "mode": "evidence_only",
                    "targeted_probe_enabled": False,
                    "features": {"attest": True},
                    "economic_effect": "none",
                }

            async def list_models(self):
                return ["qwen3-27b"]

            async def validator_scorecards(self, *, limit=10, since_hours=24):
                return {
                    "available": True,
                    "count": 1,
                    "window_hours": since_hours,
                    "economic_effect": "none",
                    "items": [{"subject_id": "worker-1", "model": "qwen3-27b", "total": 1}],
                }

            async def aclose(self):
                return None

        async def fake_probe_round(_grid, _round_index):
            calls["probe"] += 1

        with (
            patch("validator.config.Settings.validate", return_value=None),
            patch.object(Settings, "REQUIRE_STAKE", False),
            patch("validator.staking.assert_eligible", return_value=None),
            patch(
                "validator.attest.runtime_capabilities",
                return_value=["text.instruction.v1", "text.token_limit.v1"],
            ),
            patch("validator.main.probe_round", fake_probe_round),
            patch("validator.grid_client.GridClient", FakeGrid),
        ):
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = cli._cmd_check(argparse.Namespace(no_probe=True))

        self.assertEqual(code, 0)
        self.assertEqual(calls["probe"], 0)
        out = buf.getvalue()
        self.assertIn("Validator API: available", out)
        self.assertIn("Stake: gate disabled", out)
        self.assertIn("Local scorers: text.instruction.v1, text.token_limit.v1", out)
        self.assertIn("Scorecards: 1 subject", out)
        self.assertIn("economic_effect=none", out)
        self.assertIn("Probe skipped", out)
        self.assertIn("qwen3-27b", out)

    def test_check_no_probe_does_not_require_public_model_scope(self):
        class FakeGrid(_RegisteredFakeGrid):
            async def validator_capabilities(self):
                return {
                    "available": False,
                    "features": {},
                    "economic_effect": "none",
                    "targeted_probe_enabled": False,
                }

            async def validator_scorecards(self, *, limit=10, since_hours=24):
                return {"available": False, "error": "not deployed"}

            async def list_models(self):
                raise AssertionError("validator health must not call the public model API")

            async def aclose(self):
                return None

        with (
            patch("validator.config.Settings.validate", return_value=None),
            patch.object(Settings, "REQUIRE_STAKE", False),
            patch("validator.staking.assert_eligible", return_value=None),
            patch("validator.grid_client.GridClient", FakeGrid),
        ):
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = cli._cmd_check(argparse.Namespace(no_probe=True))

        self.assertEqual(code, 0)
        out = buf.getvalue()
        self.assertIn("validator registration and API available", out)
        self.assertNotIn("Traceback", out)

    def test_check_reports_invalid_numeric_env_without_import_traceback(self):
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
                [sys.executable, "-m", "validator", "check", "--no-probe"],
                cwd=os.getcwd(),
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Config:", result.stdout)
        self.assertIn("PROBE_INTERVAL_S must be an integer", result.stdout)
        self.assertNotIn("Traceback", result.stdout)

    def test_check_rejects_malformed_grid_url_before_http_client(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = os.path.join(tmp, ".env")
            with open(env_path, "w", encoding="utf-8") as fh:
                fh.write(
                    "GRID_API_URL=api.aipowergrid.io\n"
                    "VALIDATOR_API_KEY=grid-key\n"
                    "VALIDATOR_REQUIRE_STAKE=false\n"
                )
            env = os.environ.copy()
            env["VALIDATOR_ENV"] = env_path
            result = subprocess.run(
                [sys.executable, "-m", "validator", "check", "--no-probe"],
                cwd=os.getcwd(),
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Config:", result.stdout)
        self.assertIn("GRID_API_URL must be an http(s) URL", result.stdout)
        self.assertNotIn("Grid models unavailable", result.stdout)
        self.assertNotIn("Traceback", result.stdout)

    def test_run_reports_invalid_numeric_env_without_traceback(self):
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
                [sys.executable, "-m", "validator", "run"],
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

    def test_run_requires_staking_contract_when_stake_gate_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = os.path.join(tmp, ".env")
            with open(env_path, "w", encoding="utf-8") as fh:
                fh.write(
                    "GRID_API_URL=http://127.0.0.1:1\n"
                    "VALIDATOR_API_KEY=grid-key\n"
                    "VALIDATOR_REQUIRE_STAKE=true\n"
                    "VALIDATOR_WALLET=0x19e7e376e7c213b7e7e7e46cc70a5dd086daff2a\n"
                    f"VALIDATOR_PRIVATE_KEY=0x{'11' * 32}\n"
                )
            env = os.environ.copy()
            env["VALIDATOR_ENV"] = env_path
            result = subprocess.run(
                [sys.executable, "-m", "validator", "run"],
                cwd=os.getcwd(),
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Startup:", result.stdout)
        self.assertIn("Stake contract not deployed", result.stdout)
        self.assertNotIn("Traceback", result.stdout)

    def test_run_rejects_malformed_staking_address_before_web3(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = os.path.join(tmp, ".env")
            with open(env_path, "w", encoding="utf-8") as fh:
                fh.write(
                    "GRID_API_URL=http://127.0.0.1:1\n"
                    "VALIDATOR_API_KEY=grid-key\n"
                    "VALIDATOR_REQUIRE_STAKE=true\n"
                    "VALIDATOR_WALLET=0x19e7e376e7c213b7e7e7e46cc70a5dd086daff2a\n"
                    f"VALIDATOR_PRIVATE_KEY=0x{'11' * 32}\n"
                    "VALIDATOR_STAKING_ADDR=bad\n"
                )
            env = os.environ.copy()
            env["VALIDATOR_ENV"] = env_path
            result = subprocess.run(
                [sys.executable, "-m", "validator", "run"],
                cwd=os.getcwd(),
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Startup:", result.stdout)
        self.assertIn("VALIDATOR_STAKING_ADDR must be a 20-byte 0x hex address", result.stdout)
        self.assertNotIn("Traceback", result.stdout)

    def test_dashboard_rejects_invalid_port_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = os.path.join(tmp, ".env")
            with open(env_path, "w", encoding="utf-8") as fh:
                fh.write(
                    "GRID_API_URL=http://127.0.0.1:1\n"
                    "VALIDATOR_API_KEY=grid-key\n"
                    "VALIDATOR_REQUIRE_STAKE=false\n"
                )
            env = os.environ.copy()
            env["VALIDATOR_ENV"] = env_path
            result = subprocess.run(
                [sys.executable, "-m", "validator", "dashboard", "--port", "99999"],
                cwd=os.getcwd(),
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Dashboard:", result.stdout)
        self.assertIn("port must be between 1 and 65535", result.stdout)
        self.assertNotIn("Traceback", result.stdout)

    def test_check_probe_fails_when_no_canary_was_submitted(self):
        class FakeGrid(_RegisteredFakeGrid):
            async def validator_capabilities(self):
                return {
                    "available": True,
                    "features": {},
                    "economic_effect": "none",
                    "targeted_probe_enabled": False,
                }

            async def validator_scorecards(self, *, limit=10, since_hours=24):
                return {"available": False, "error": "not deployed"}

            async def list_models(self):
                return ["stable-diffusion-xl"]

            async def aclose(self):
                return None

        async def fake_probe_round(_grid, _round_index):
            return 0

        with (
            patch("validator.config.Settings.validate", return_value=None),
            patch.object(Settings, "REQUIRE_STAKE", False),
            patch("validator.staking.assert_eligible", return_value=None),
            patch("validator.main.probe_round", fake_probe_round),
            patch("validator.grid_client.GridClient", FakeGrid),
        ):
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = cli._cmd_check(argparse.Namespace(no_probe=False))

        self.assertEqual(code, 1)
        out = buf.getvalue()
        self.assertIn("No Grid assignment was available", out)
        self.assertNotIn("Traceback", out)

    def test_check_probe_reports_canary_count(self):
        class FakeGrid(_RegisteredFakeGrid):
            async def validator_capabilities(self):
                return {
                    "available": True,
                    "features": {},
                    "economic_effect": "none",
                    "targeted_probe_enabled": False,
                }

            async def validator_scorecards(self, *, limit=10, since_hours=24):
                return {"available": False, "error": "not deployed"}

            async def list_models(self):
                return ["qwen3-32b"]

            async def aclose(self):
                return None

        async def fake_probe_round(_grid, _round_index):
            return 1

        with (
            patch("validator.config.Settings.validate", return_value=None),
            patch.object(Settings, "REQUIRE_STAKE", False),
            patch("validator.staking.assert_eligible", return_value=None),
            patch("validator.main.probe_round", fake_probe_round),
            patch("validator.grid_client.GridClient", FakeGrid),
        ):
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = cli._cmd_check(argparse.Namespace(no_probe=False))

        self.assertEqual(code, 0)
        self.assertIn("submitted 1 canary", buf.getvalue())

    def test_check_fails_closed_when_required_stake_is_unavailable(self):
        class UnexpectedGrid:
            def __init__(self):
                raise AssertionError("grid should not be contacted after stake failure")

        with (
            patch("validator.config.Settings.validate", return_value=None),
            patch.object(Settings, "REQUIRE_STAKE", True),
            patch(
                "validator.staking.assert_eligible",
                side_effect=RuntimeError(
                    "web3 not installed; install the validator `stake` extra to use the stake gate."
                ),
            ),
            patch("validator.grid_client.GridClient", UnexpectedGrid),
        ):
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = cli._cmd_check(argparse.Namespace(no_probe=True))

        self.assertEqual(code, 1)
        out = buf.getvalue()
        self.assertIn("Stake:", out)
        self.assertIn("stake` extra", out)
        self.assertNotIn("Traceback", out)


class CliInitTests(unittest.TestCase):
    def test_init_reports_non_interactive_setup_without_traceback(self):
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                with patch("builtins.input", side_effect=EOFError):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = cli._cmd_init(argparse.Namespace())
            finally:
                os.chdir(old_cwd)

            self.assertEqual(code, 1)
            out = buf.getvalue()
            self.assertIn("Interactive setup requires a terminal", out)
            self.assertNotIn("Traceback", out)
            self.assertFalse(os.path.exists(os.path.join(tmp, ".env")))

    def test_init_rejects_missing_api_key(self):
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                with patch("builtins.input", side_effect=["", ""]):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = cli._cmd_init(argparse.Namespace())
            finally:
                os.chdir(old_cwd)

            self.assertEqual(code, 1)
            self.assertIn("API key is required", buf.getvalue())
            self.assertFalse(os.path.exists(os.path.join(tmp, ".env")))

    def test_init_can_sign_v0_without_requiring_stake(self):
        account = Account.create()
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                with (
                    patch("builtins.input", side_effect=["", "grid-key", "", "n", "y"]),
                    patch("getpass.getpass", return_value=account.key.hex()),
                ):
                    with redirect_stdout(io.StringIO()):
                        code = cli._cmd_init(argparse.Namespace())
            finally:
                os.chdir(old_cwd)

            self.assertEqual(code, 0)
            env = (os.path.join(tmp, ".env"))
            with open(env, encoding="utf-8") as fh:
                body = fh.read()
            self.assertIn("VALIDATOR_REQUIRE_STAKE=false", body)
            self.assertIn(f"VALIDATOR_WALLET={account.address.lower()}", body)
            self.assertIn(f"VALIDATOR_PRIVATE_KEY={account.key.hex()}", body)

    def test_init_rejects_mismatched_wallet_private_key(self):
        account = Account.create()
        other = Account.create()
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                with (
                    patch("builtins.input", side_effect=["", "grid-key", other.address, "n", "y"]),
                    patch("getpass.getpass", return_value=account.key.hex()),
                ):
                    with redirect_stdout(io.StringIO()):
                        code = cli._cmd_init(argparse.Namespace())
            finally:
                os.chdir(old_cwd)

            self.assertEqual(code, 1)
            self.assertFalse(os.path.exists(os.path.join(tmp, ".env")))

    def test_init_rejects_malformed_optional_wallet(self):
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                with patch("builtins.input", side_effect=["", "grid-key", "0xnot-a-wallet"]):
                    with redirect_stdout(io.StringIO()):
                        code = cli._cmd_init(argparse.Namespace())
            finally:
                os.chdir(old_cwd)

            self.assertEqual(code, 1)
            self.assertFalse(os.path.exists(os.path.join(tmp, ".env")))


if __name__ == "__main__":
    unittest.main()
