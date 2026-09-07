# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import threading
import unittest
import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, patch

from validator.operator_updates import UpdateController
from validator.update_check import UpdateResult
from tests.test_update_install import InstallFixture
from validator.update_download import _private_file, _private_root


class OperatorUpdateTests(unittest.TestCase):
    def test_cached_reads_no_startup_network_and_no_actions_after_close(self):
        with patch(
            "validator.update_check.inspect_update", new_callable=AsyncMock
        ) as check:
            controller = UpdateController()
            self.assertEqual(controller.snapshot()["status"], "not_checked")
            controller.close()
            self.assertFalse(controller.check())
            check.assert_not_called()


class OperatorInstallTests(InstallFixture, unittest.TestCase):
    def test_close_cancels_preparation_without_handoff(self):
        controller = self.controller()
        entered = threading.Event()

        def worker(action, request, *, cancelled):
            _private_root(Path(request["root"]))
            entered.set()
            if not cancelled.wait(5):
                raise AssertionError("preparation was not cancelled")
            raise ValueError("cancelled fixture")

        with (
            patch("validator.operator_updates.sys.frozen", True, create=True),
            patch("validator.update_process.run_worker", side_effect=worker),
        ):
            self.assertTrue(controller.install("v0.1.0-preview.17", True))
            self.assertTrue(entered.wait(2))
            controller.close()
        self.assertFalse(controller.thread.is_alive())
        self.assertEqual(self.ready, [])
        self.assertIsNone(self.store.selected())
        self.assertEqual(list(self.store.root.glob("attempt-*")), [])

    def controller(self):
        controller = UpdateController("v0.1.0-preview.16")
        controller.state.update(status="available", latest_tag="v0.1.0-preview.17")
        self.ready = []
        controller.configure_install(self.config, self.ready.append)
        return controller

    def worker(self, action, request=None, **kwargs):
        if action == "self-test":
            return {"ready": True, "tag": "v0.1.0-preview.17"}
        root = Path(request["root"])
        _private_root(root)
        directory = root / "stage-fixture"
        _private_root(directory)
        path = directory / "aipg-validator"
        with _private_file(path) as output:
            output.write(b"fixture")
        return {
            "release": {"tag": request["tag"]},
            "executable": str(path),
            "executable_sha256": hashlib.sha256(b"fixture").hexdigest(),
        }

    def test_explicit_matching_tag_and_preview_consent_before_preparation(self):
        controller = self.controller()
        try:
            with (
                patch("validator.operator_updates.sys.frozen", True, create=True),
                patch(
                    "validator.update_process.run_worker", side_effect=self.worker
                ) as worker,
            ):
                self.assertFalse(controller.install("v0.1.0-preview.18", True))
                self.assertFalse(controller.install("v0.1.0-preview.17", False))
                worker.assert_not_called()
                self.assertTrue(controller.install("v0.1.0-preview.17", True))
                controller.thread.join(5)
                self.assertFalse(controller.thread.is_alive())
                self.assertEqual(controller.snapshot()["status"], "restarting")
                self.assertEqual(len(self.ready), 1)
                self.assertIsNone(self.store.selected())
                self.assertEqual(worker.call_count, 2)
        finally:
            controller.close()

    def test_failed_health_cleans_only_attempt_and_does_not_activate(self):
        controller = self.controller()
        old = self.entry(16)
        self.store.write(old, None)

        def worker(action, request=None, **kwargs):
            if action == "self-test":
                raise ValueError("private fixture error")
            return self.worker(action, request, **kwargs)

        try:
            with (
                patch("validator.operator_updates.sys.frozen", True, create=True),
                patch("validator.update_process.run_worker", side_effect=worker),
            ):
                self.assertTrue(controller.install("v0.1.0-preview.17", True))
                controller.thread.join(5)
            self.assertEqual(controller.snapshot()["status"], "install_failed")
            self.assertEqual(self.ready, [])
            self.assertEqual(self.store.selected(), old)
            self.assertEqual(len(list(self.store.root.glob("attempt-*"))), 1)
            self.assertNotIn("private fixture", str(controller.snapshot()))
        finally:
            controller.close()

    def test_one_background_check_and_rate_limit(self):
        entered, release = threading.Event(), threading.Event()

        async def check(**kwargs):
            entered.set()
            while not release.is_set():
                await asyncio.sleep(0.01)
            return UpdateResult("available", kwargs["current_tag"], "v0.1.0-preview.16")

        controller = UpdateController("v0.1.0-preview.13")
        try:
            with patch(
                "validator.update_check.inspect_update", side_effect=check
            ) as inspect:
                self.assertTrue(controller.check())
                self.assertTrue(entered.wait(2))
                self.assertEqual(controller.snapshot()["status"], "checking")
                self.assertFalse(controller.check())
                release.set()
                controller.thread.join(2)
                self.assertFalse(controller.thread.is_alive())
                self.assertEqual(controller.snapshot()["status"], "available")
                self.assertFalse(controller.check())
                inspect.assert_called_once()
        finally:
            release.set()
            controller.close()

    def test_failure_is_sanitized(self):
        controller = UpdateController("v0.1.0-preview.13")
        try:
            with patch(
                "validator.update_check.inspect_update",
                side_effect=RuntimeError("private detail"),
            ):
                self.assertTrue(controller.check())
                controller.thread.join(2)
                state = controller.snapshot()
                self.assertEqual(state["status"], "unavailable")
                self.assertNotIn("private detail", str(state))
        finally:
            controller.close()
