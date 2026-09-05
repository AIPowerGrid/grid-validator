# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Private child-process protocol. Never relay logs or raw exceptions to a browser."""

import asyncio
import contextlib
import json
import os
import sys
import threading
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from .file_lock import AlreadyRunning

_MAX_CLOCK_DRIFT_SECONDS = 300


async def clock_drift_seconds(grid_url: str) -> int | None:
    """Return bounded Grid clock drift when a valid HTTP Date is available."""
    try:
        async with httpx.AsyncClient(
            base_url=grid_url,
            timeout=5,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            response = await client.get("/health")
            response.raise_for_status()
        server_time = parsedate_to_datetime(response.headers.get("Date", ""))
        if server_time.tzinfo is None:
            server_time = server_time.replace(tzinfo=timezone.utc)
        drift = abs((datetime.now(timezone.utc) - server_time).total_seconds())
        return min(int(drift), 24 * 60 * 60)
    except (TypeError, ValueError, OverflowError, httpx.HTTPError):
        return None


def error_code(exc: BaseException) -> str:
    # HTTPX transport errors wrap httpcore errors; retain the public HTTPX type.
    for cause in (exc, exc.__cause__):
        if isinstance(cause, httpx.HTTPStatusError):
            return (
                "credentials_rejected"
                if cause.response.status_code in {401, 403}
                else "grid_unavailable"
            )
        if isinstance(cause, httpx.HTTPError):
            return "grid_unavailable"
        if isinstance(cause, AlreadyRunning):
            return "already_running"
    return "runtime_error"


async def _run_action(action: str, emit) -> int:
    if action == "enroll":
        from .enrollment import EnrollmentError, enroll
        from .launcher import config_path

        emit("enrolling")
        try:
            # The existing enrollment command prints progress, never the wire protocol.
            with open(os.devnull, "w") as sink, contextlib.redirect_stdout(sink):
                await asyncio.to_thread(enroll, config_path())
        except EnrollmentError:
            emit("error", error="enrollment_failed")
            return 1
        emit("enrolled")
        return 0

    from .config import Settings
    from .main import run

    try:
        Settings.validate()
    except RuntimeError:
        emit("error", error="configuration_invalid")
        return 1
    drift = await clock_drift_seconds(Settings.GRID_API_URL)
    if drift is not None and drift > _MAX_CLOCK_DRIFT_SECONDS:
        emit("error", error="clock_drift")
        return 1
    await run(observer=emit)
    return 0


def execute(action: str) -> int:
    stream = sys.stdout

    def emit(phase: str, **values: Any) -> None:
        print(
            json.dumps({"phase": phase, **values}, separators=(",", ":")),
            file=stream,
            flush=True,
        )

    async def managed() -> int:
        task = asyncio.create_task(_run_action(action, emit))
        loop = asyncio.get_running_loop()

        def watch_parent() -> None:
            # EOF also stops the child if the app crashes. No PID-based recovery/kill.
            sys.stdin.readline()
            with contextlib.suppress(RuntimeError):
                loop.call_soon_threadsafe(task.cancel)

        threading.Thread(target=watch_parent, daemon=True).start()
        try:
            return await task
        except asyncio.CancelledError:
            return 0
        except Exception as exc:
            emit("error", error=error_code(exc))
            return 1

    return asyncio.run(managed())
