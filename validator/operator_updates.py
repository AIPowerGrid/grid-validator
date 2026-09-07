# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Explicit, cached release discovery independent of the inference loop."""

from __future__ import annotations

import asyncio
import threading
import time
import sys
import shutil
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Any

from . import __release_tag__, update_check


class UpdateController:
    def __init__(self, current_tag: str = __release_tag__) -> None:
        self.current_tag = current_tag
        self.lock = threading.Lock()
        self.thread: threading.Thread | None = None
        self.closed = False
        self.next_check = 0.0
        self.state = asdict(update_check.UpdateResult("not_checked", current_tag))
        self.cancelled = threading.Event()
        self.config: Path | None = None
        self.on_ready: Callable[[dict[str, Any]], None] | None = None

    def configure_install(
        self, config: Path, on_ready: Callable[[dict[str, Any]], None]
    ) -> None:
        self.config, self.on_ready = config, on_ready

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                **self.state,
                "install_supported": bool(
                    getattr(sys, "frozen", False) and self.config is not None
                ),
            }

    def check(self) -> bool:
        with self.lock:
            if (
                self.closed
                or self.state["status"] in {"checking", "preparing", "restarting"}
                or time.monotonic() < self.next_check
            ):
                return False
            self.state = asdict(update_check.UpdateResult("checking", self.current_tag))
            self.next_check = time.monotonic() + 30
            self.thread = threading.Thread(target=self._check, daemon=True)
            self.thread.start()
            return True

    def _check(self) -> None:
        try:
            result = asyncio.run(
                update_check.inspect_update(current_tag=self.current_tag)
            )
        except Exception:
            result = update_check.UpdateResult("unavailable", self.current_tag)
        with self.lock:
            self.state = asdict(result)

    def install(self, tag: str, accept_unsigned: bool) -> bool:
        with self.lock:
            if (
                self.closed
                or not getattr(sys, "frozen", False)
                or self.config is None
                or self.on_ready is None
                or self.state["status"] not in {"available", "install_failed"}
                or tag != self.state.get("latest_tag")
            ):
                return False
            target = update_check._version_key(tag)
            if target is None or (not target[3] and accept_unsigned is not True):
                return False
            self.state["status"] = "preparing"
            self.cancelled.clear()
            self.thread = threading.Thread(
                target=self._install, args=(tag,), daemon=True
            )
            self.thread.start()
            return True

    def _install(self, tag: str) -> None:
        from .update_install import InstallStore
        from .update_download import _private_root
        from .update_process import run_worker

        assert self.config is not None and self.on_ready is not None
        store = InstallStore(self.config)
        attempt = store.root / ("attempt-" + uuid.uuid4().hex)
        ready = False
        try:
            _private_root(store.root)
            result = run_worker(
                "prepare", {"root": str(attempt), "tag": tag}, cancelled=self.cancelled
            )
            entry = store.from_preparation(result, tag)
            health = run_worker(
                "self-test",
                executable=store.executable(entry),
                timeout=40,
                cancelled=self.cancelled,
            )
            if health.get("tag") != tag:
                raise ValueError("candidate version mismatch")
            with self.lock:
                if self.closed or self.cancelled.is_set():
                    return
                self.state["status"] = "restarting"
                ready = True
            self.on_ready(entry)
        except Exception:
            with self.lock:
                self.state["status"] = "install_failed"
        finally:
            if not ready and attempt.exists():
                shutil.rmtree(attempt)

    def close(self) -> None:
        with self.lock:
            self.closed = True
            self.cancelled.set()
            thread = self.thread
        if thread:
            thread.join(timeout=45)
