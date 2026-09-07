# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import threading
import unittest
from unittest.mock import AsyncMock, patch

from validator.operator_updates import UpdateController
from validator.update_check import UpdateResult


class OperatorUpdateTests(unittest.TestCase):
    def test_cached_reads_no_startup_network_and_no_actions_after_close(self):
        with patch("validator.update_check.inspect_update", new_callable=AsyncMock) as check:
            controller = UpdateController()
            self.assertEqual(controller.snapshot()["status"], "not_checked")
            controller.close()
            self.assertFalse(controller.check())
            check.assert_not_called()

    def test_one_background_check_and_rate_limit(self):
        entered, release = threading.Event(), threading.Event()

        async def check(**kwargs):
            entered.set()
            while not release.is_set():
                await asyncio.sleep(.01)
            return UpdateResult("available", kwargs["current_tag"], "v0.1.0-preview.16")

        controller = UpdateController("v0.1.0-preview.13")
        try:
            with patch("validator.update_check.inspect_update", side_effect=check) as inspect:
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
            with patch("validator.update_check.inspect_update", side_effect=RuntimeError("private detail")):
                self.assertTrue(controller.check())
                controller.thread.join(2)
                state = controller.snapshot()
                self.assertEqual(state["status"], "unavailable")
                self.assertNotIn("private detail", str(state))
        finally:
            controller.close()
