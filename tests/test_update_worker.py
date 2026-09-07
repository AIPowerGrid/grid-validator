# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

import contextlib
import io
import json
import os
import sys
import threading
import time
import unittest
from unittest.mock import patch

from validator import update_process as up
from validator import update_worker as uw
from validator.release_verify import ReleaseVerificationError


class UpdateWorkerTests(unittest.TestCase):
    def test_platform_mapping(self):
        for system, machine, result in (
            ("win32", "AMD64", "windows-x64"),
            ("darwin", "arm64", "macos-arm64"),
            ("linux", "aarch64", "linux-arm64"),
            ("linux", "x86_64", "linux-x64"),
        ):
            with (
                self.subTest(system=system),
                patch.object(uw.sys, "platform", system),
                patch.object(uw.platform, "machine", return_value=machine),
            ):
                self.assertEqual(uw.native_platform(), result)
        with (
            patch.object(uw.platform, "machine", return_value="unknown"),
            self.assertRaises(ReleaseVerificationError),
        ):
            uw.native_platform()

    def test_invalid_request_never_starts_preparation(self):
        with patch("validator.update_download.prepare_update") as prepare:
            for raw in (
                b"[]",
                b'{"root":"relative","tag":"v0.1.0-preview.17"}',
                b'{"root":"/tmp","tag":"one","tag":"two"}',
                b'{"root":"/tmp","tag":"x","command":"bad"}',
            ):
                with self.subTest(raw=raw), self.assertRaises(ReleaseVerificationError):
                    uw.prepare_request(raw)
            prepare.assert_not_called()

    def test_child_error_is_fixed_and_redacted(self):
        output = io.StringIO()
        with (
            contextlib.redirect_stdout(output),
            patch.object(
                uw,
                "self_test",
                side_effect=RuntimeError("private path and secret response"),
            ),
        ):
            self.assertEqual(uw.main("self-test"), 1)
        self.assertEqual(
            json.loads(output.getvalue()),
            {"ready": False, "error": "update_preparation_failed"},
        )

    def test_child_environment_excludes_credentials_and_proxies(self):
        with patch.dict(
            os.environ,
            {
                "VALIDATOR_PRIVATE_KEY": "private-fixture",
                "VALIDATOR_API_KEY": "api-fixture",
                "HTTPS_PROXY": "https://proxy.invalid",
                "PYTHONPATH": "/untrusted",
                "HOME": "/home-fixture",
            },
        ):
            env = up.child_environment()
        self.assertEqual(env["HOME"], "/home-fixture")
        self.assertEqual(env["PYINSTALLER_RESET_ENVIRONMENT"], "1")
        for key in (
            "VALIDATOR_PRIVATE_KEY",
            "VALIDATOR_API_KEY",
            "HTTPS_PROXY",
            "PYTHONPATH",
        ):
            self.assertNotIn(key, env)


class UpdateProcessTests(unittest.TestCase):
    def command(self, program):
        return patch.object(
            up, "command_prefix", return_value=[sys.executable, "-c", program]
        )

    def test_real_child_valid_reply(self):
        program = 'import json; print(json.dumps({"schema":"aipg.validator.update-health.v1","ready":True}))'
        with self.command(program):
            self.assertTrue(up.run_worker("self-test", timeout=5)["ready"])

    def test_real_child_timeout_and_oversized_reply(self):
        for program in (
            "import time; time.sleep(60)",
            'import sys,time; sys.stdout.write("x"*9000); sys.stdout.flush(); time.sleep(60)',
        ):
            start = time.monotonic()
            with self.command(program), self.assertRaises(ReleaseVerificationError):
                up.run_worker("self-test", timeout=0.4)
            self.assertLess(time.monotonic() - start, 15)

    def test_cancelled_child_and_no_start_after_cancel(self):
        cancel = threading.Event()
        timer = threading.Timer(0.15, cancel.set)
        timer.start()
        try:
            with (
                self.command("import time; time.sleep(60)"),
                self.assertRaisesRegex(ReleaseVerificationError, "update_cancelled"),
            ):
                up.run_worker("self-test", timeout=5, cancelled=cancel)
        finally:
            timer.cancel()
            timer.join()
        with (
            patch.object(up.subprocess, "Popen") as start,
            self.assertRaises(ReleaseVerificationError),
        ):
            up.run_worker("self-test", cancelled=cancel)
        start.assert_not_called()

    def test_malformed_nonzero_or_false_success_rejected(self):
        for program in (
            'print("not json")',
            'print("{}")',
            'import sys; print("{}"); sys.exit(1)',
            'print(\'{"schema":"aipg.validator.update-health.v1","ready":false}\')',
        ):
            with (
                self.subTest(program=program),
                self.command(program),
                self.assertRaises(ReleaseVerificationError),
            ):
                up.run_worker("self-test", timeout=5)


if __name__ == "__main__":
    unittest.main()
