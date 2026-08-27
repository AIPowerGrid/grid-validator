# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from validator import cli, launcher


class LauncherTests(unittest.TestCase):
    def test_no_arguments_in_terminal_opens_menu(self):
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("validator.launcher.run_menu", return_value=0) as menu,
        ):
            self.assertEqual(cli.main([]), 0)
        menu.assert_called_once()

    def test_noninteractive_no_args_prints_help_without_starting(self):
        with (
            patch("sys.stdin.isatty", return_value=False),
            patch("validator.launcher.run_menu") as menu,
            redirect_stdout(io.StringIO()) as output,
        ):
            self.assertEqual(cli.main([]), 0)
        menu.assert_not_called()
        self.assertIn("usage:", output.getvalue())

    def test_menu_preserves_failure_and_runs_commands_with_same_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            with (
                patch("validator.launcher.config_path", return_value=path),
                patch("builtins.input", side_effect=["1", "4", "0"]),
                patch("validator.launcher.subprocess.run", return_value=subprocess.CompletedProcess([], 1)) as run,
                redirect_stdout(io.StringIO()) as output,
            ):
                self.assertEqual(cli.main(["menu"]), 0)
            self.assertEqual(run.call_count, 2)
            self.assertEqual(run.call_args_list[0].args[0][-1], "prepare-wallet")
            self.assertEqual(run.call_args_list[1].args[0][-2:], ["check", "--no-probe"])
            for call in run.call_args_list:
                self.assertEqual(call.kwargs["env"]["VALIDATOR_ENV"], str(path))
                self.assertNotIn("shell", call.kwargs)
            self.assertIn("exited with code 1", output.getvalue())

    def test_menu_quit_does_not_create_identity_or_contact_grid(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "new" / ".env"
            with (
                patch("validator.launcher.config_path", return_value=path),
                patch("builtins.input", return_value="0"),
                patch("validator.launcher.subprocess.run") as run,
                patch("validator.launcher.webbrowser.open") as browser,
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(cli.main(["menu"]), 0)
            run.assert_not_called()
            browser.assert_not_called()
            self.assertFalse(path.parent.exists())

    def test_setup_without_identity_does_not_request_personal_private_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            with (
                patch("validator.launcher.config_path", return_value=Path(tmp) / ".env"),
                patch("builtins.input", side_effect=["3", "0"]),
                patch("validator.launcher.subprocess.run") as run,
                redirect_stdout(io.StringIO()) as output,
            ):
                self.assertEqual(cli.main(["menu"]), 0)
            run.assert_not_called()
            self.assertIn("option 1 first", output.getvalue())

    def test_config_resolution_keeps_existing_identity_and_explicit_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                patch.dict(os.environ, {}, clear=True),
                patch("validator.launcher.Path.cwd", return_value=root),
                patch("validator.launcher.Path.home", return_value=root / "home"),
                patch.object(sys, "frozen", False, create=True),
            ):
                self.assertEqual(launcher.config_path(), root / "home" / ".aipg-validator" / ".env")
                (root / ".env").touch()
                self.assertEqual(launcher.config_path(), root / ".env")
                with patch.dict(os.environ, {"VALIDATOR_ENV": str(root / "other.env")}):
                    self.assertEqual(launcher.config_path(), (root / "other.env").resolve())

    def test_frozen_actions_use_actual_executable_not_python_module(self):
        with patch.object(sys, "frozen", True, create=True):
            self.assertEqual(launcher.command_prefix(), [sys.executable])

    def test_menu_eof_exits_without_loop(self):
        with (
            patch("validator.launcher.config_path", return_value=Path("unused.env")),
            patch("builtins.input", side_effect=EOFError),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(cli.main(["menu"]), 0)
