# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Owned, bounded updater subprocesses without node credentials in their env."""

from __future__ import annotations

import contextlib
import json
import os
import signal
import subprocess
import threading
import time
from typing import Any

from .launcher import command_prefix
from .release_verify import ReleaseVerificationError, _json

ENV_KEYS = {
    "HOME",
    "PATH",
    "USERPROFILE",
    "LOCALAPPDATA",
    "APPDATA",
    "SYSTEMROOT",
    "WINDIR",
    "TEMP",
    "TMP",
    "TMPDIR",
    "LANG",
    "LC_ALL",
    "XDG_CACHE_HOME",
    "XDG_DATA_HOME",
}


def child_environment() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key.upper() in ENV_KEYS}
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def stop_owned(process: subprocess.Popen[bytes]) -> None:
    if os.name == "nt":
        if process.poll() is not None:
            return
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
            env=child_environment(),
        )
    else:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
    if process.poll() is None:
        process.kill()
    process.wait(timeout=10)


def run_worker(
    action: str,
    request: dict[str, Any] | None = None,
    *,
    timeout: float = 420,
    cancelled: threading.Event | None = None,
) -> dict[str, Any]:
    if action not in {"prepare", "self-test"} or not 0 < timeout <= 420:
        raise ReleaseVerificationError("invalid_update_action")
    if action == "prepare" and (
        not isinstance(request, dict) or set(request) != {"root", "tag"}
    ):
        raise ReleaseVerificationError("invalid_update_request")
    if action == "self-test" and request is not None:
        raise ReleaseVerificationError("invalid_update_request")
    payload = json.dumps(request or {}).encode()
    if len(payload) > 4096:
        raise ReleaseVerificationError("invalid_update_request")
    if cancelled is not None and cancelled.is_set():
        raise ReleaseVerificationError("update_cancelled")
    options: dict[str, Any] = (
        {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW")}
        if os.name == "nt"
        else {"start_new_session": True}
    )
    process = subprocess.Popen(
        command_prefix() + ["_update-worker", action],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=child_environment(),
        **options,
    )
    assert process.stdin is not None and process.stdout is not None
    stdout = process.stdout
    output: list[bytes] = []
    finished = threading.Event()

    def read() -> None:
        try:
            output.append(stdout.read(8193))
        except OSError:
            pass
        finally:
            finished.set()

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    deadline = time.monotonic() + timeout
    try:
        process.stdin.write(payload)
        process.stdin.close()
        while not finished.wait(0.05):
            if cancelled is not None and cancelled.is_set():
                raise ReleaseVerificationError("update_cancelled")
            if time.monotonic() >= deadline:
                raise ReleaseVerificationError("update_timed_out")
        if cancelled is not None and cancelled.is_set():
            raise ReleaseVerificationError("update_cancelled")
        if not output or len(output[0]) > 8192:
            raise ReleaseVerificationError("invalid_update_reply")
        process.wait(timeout=max(0.01, deadline - time.monotonic()))
        if process.returncode != 0:
            raise ReleaseVerificationError("update_worker_failed")
        result: dict[str, Any] = _json(output[0], 8192)
        schema = (
            "aipg.validator.update-stage.v1"
            if action == "prepare"
            else "aipg.validator.update-health.v1"
        )
        if result.get("schema") != schema or result.get("ready") is not True:
            raise ReleaseVerificationError("invalid_update_reply")
        return result
    except subprocess.TimeoutExpired as exc:
        raise ReleaseVerificationError("update_timed_out") from exc
    except OSError as exc:
        raise ReleaseVerificationError("update_process_error") from exc
    finally:
        stop_owned(process)
        reader.join(timeout=10)
        process.stdout.close()
        with contextlib.suppress(OSError):
            process.stdin.close()
