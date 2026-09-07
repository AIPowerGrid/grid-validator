# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Explicit, cached release discovery independent of the inference loop."""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import asdict

from . import __release_tag__, update_check


class UpdateController:
    def __init__(self, current_tag: str = __release_tag__) -> None:
        self.current_tag = current_tag
        self.lock = threading.Lock()
        self.thread: threading.Thread | None = None
        self.closed = False
        self.next_check = 0.0
        self.state = asdict(update_check.UpdateResult("not_checked", current_tag))

    def snapshot(self) -> dict:
        with self.lock:
            return dict(self.state)

    def check(self) -> bool:
        with self.lock:
            if self.closed or self.state["status"] == "checking" or time.monotonic() < self.next_check:
                return False
            self.state = asdict(update_check.UpdateResult("checking", self.current_tag))
            self.next_check = time.monotonic() + 30
            self.thread = threading.Thread(target=self._check, daemon=True)
            self.thread.start()
            return True

    def _check(self) -> None:
        try:
            result = asyncio.run(update_check.inspect_update(current_tag=self.current_tag))
        except Exception:
            result = update_check.UpdateResult("unavailable", self.current_tag)
        with self.lock:
            self.state = asdict(result)

    def close(self) -> None:
        with self.lock:
            self.closed = True
            thread = self.thread
        if thread:
            thread.join(timeout=10)
