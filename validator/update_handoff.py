# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Owned app handoff with local readiness, durable selection and rollback."""

from __future__ import annotations

import contextlib
import http.client
import json
import os
import queue
import secrets
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Any

from . import __release_tag__
from .file_lock import exclusive_lock
from .release_verify import ReleaseVerificationError, _json
from .update_install import InstallStore
from .update_process import stop_owned


def _send(stream: Any, value: dict[str, Any]) -> None:
    stream.write(json.dumps(value).encode() + b"\n")
    stream.flush()


def _read(stream: Any) -> dict[str, Any]:
    result: dict[str, Any] = _json(stream.readline(4097), 4096)
    return result


def handoff(
    config: Path,
    entry: dict[str, Any],
    resume: bool,
    *,
    open_browser: bool = True,
    port: int = 0,
    token: str | None = None,
) -> bool:
    """Called only after the old app releases its lock and stops owned work."""
    store = InstallStore(config)
    try:
        previous = store.selected()
        executable = store.executable(entry)
    except (OSError, ValueError):
        return False
    nonce = secrets.token_hex(32)
    env = os.environ.copy()
    env["VALIDATOR_ENV"] = str(config)
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    options: dict[str, Any] = (
        {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW")}
        if os.name == "nt"
        else {"start_new_session": True}
    )
    try:
        child = subprocess.Popen(
            [str(executable), "_updated-app"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
            **options,
        )
    except OSError:
        return False
    assert child.stdin is not None and child.stdout is not None
    replies: queue.Queue[dict[str, Any] | None] = queue.Queue(maxsize=4)

    def read() -> None:
        try:
            for _ in range(2):
                replies.put_nowait(_read(child.stdout))
        except (ValueError, OSError, queue.Full):
            with contextlib.suppress(queue.Full):
                replies.put_nowait(None)

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    committed = False
    try:
        _send(
            child.stdin,
            {
                "config": str(config),
                "entry": entry,
                "previous": previous,
                "resume": resume,
                "nonce": nonce,
                "port": port,
                "token": token,
            },
        )
        ready = replies.get(timeout=40)
        if (
            not ready
            or set(ready) != {"phase", "nonce", "port", "token", "tag"}
            or ready["phase"] != "ready"
            or ready["nonce"] != nonce
            or ready["tag"] != entry["tag"]
        ):
            raise ReleaseVerificationError("update_start_failed")
        if (
            type(ready["port"]) is not int
            or not 0 < ready["port"] <= 65535
            or not isinstance(ready["token"], str)
            or len(ready["token"]) != 43
            or (port != 0 and ready["port"] != port)
            or (token is not None and ready["token"] != token)
        ):
            raise ReleaseVerificationError("update_start_failed")
        connection = http.client.HTTPConnection("127.0.0.1", ready["port"], timeout=5)
        try:
            connection.request(
                "GET",
                "/status.json",
                headers={"Authorization": "Bearer " + ready["token"]},
            )
            response = connection.getresponse()
            status = _json(response.read(65537), 65536)
            if (
                response.status != 200
                or status.get("version") != entry["tag"]
                or status.get("running") is not False
            ):
                raise ReleaseVerificationError("update_start_failed")
        finally:
            connection.close()
        store.write(entry, previous, pending=True)
        _send(child.stdin, {"action": "commit", "nonce": nonce})
        reply = replies.get(timeout=20)
        if reply != {"phase": "committed", "nonce": nonce} or child.poll() is not None:
            raise ReleaseVerificationError("update_start_failed")
        if store.selected() != entry:
            raise ReleaseVerificationError("update_start_failed")
        committed = True
        url = f"http://127.0.0.1:{ready['port']}/#{ready['token']}"
        # This is the newly owned loopback app, not a release-controlled URL.
        if open_browser and port == 0:
            with contextlib.suppress(webbrowser.Error, OSError):
                webbrowser.open(url)
        if port == 0:
            with contextlib.suppress(OSError):
                print("Updated local validator app: " + url, flush=True)
        threading.Thread(target=child.wait, daemon=True).start()
        return True
    except (OSError, ValueError, queue.Empty, http.client.HTTPException):
        return False
    finally:
        if not committed:
            stop_owned(child)
            store.write(previous, None)
        child.stdin.close()
        reader.join(timeout=5)
        child.stdout.close()


def updated_app() -> int:
    """Private startup protocol. EOF before commit leaves the old selection."""
    from .operator_app import OperatorServer, Supervisor

    request = _read(sys.stdin.buffer)
    if (
        set(request)
        != {"config", "entry", "previous", "resume", "nonce", "port", "token"}
        or type(request["resume"]) is not bool
        or not isinstance(request["config"], str)
        or not isinstance(request["nonce"], str)
        or len(request["nonce"]) != 64
        or type(request["port"]) is not int
        or not 0 <= request["port"] <= 65535
        or (
            request["token"] is not None
            and (
                not isinstance(request["token"], str)
                or len(request["token"]) != 43
                or any(
                    c
                    not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
                    for c in request["token"]
                )
            )
        )
    ):
        raise ReleaseVerificationError("invalid_update_handoff")
    config = Path(request["config"])
    if not config.is_absolute() or not getattr(sys, "frozen", False):
        raise ReleaseVerificationError("invalid_update_handoff")
    store = InstallStore(config)
    entry = request["entry"]
    if (
        store.executable(entry).resolve() != Path(sys.executable).resolve()
        or entry["tag"] != __release_tag__
    ):
        raise ReleaseVerificationError("invalid_update_handoff")
    with exclusive_lock(Path(str(config) + ".app.lock")):
        supervisor = Supervisor(config)
        server = OperatorServer(supervisor, request["port"])
        if request["token"] is not None:
            server.token = request["token"]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            _send(
                sys.stdout.buffer,
                {
                    "phase": "ready",
                    "nonce": request["nonce"],
                    "tag": __release_tag__,
                    "port": server.server_port,
                    "token": server.token,
                },
            )
            if (
                _read(sys.stdin.buffer)
                != {"action": "commit", "nonce": request["nonce"]}
                or store.selected() != request["previous"]
            ):
                raise ReleaseVerificationError("invalid_update_handoff")
            store.write(entry, request["previous"])
            if request["resume"] and not supervisor.start("run"):
                store.write(request["previous"], None)
                raise ReleaseVerificationError("update_start_failed")
            _send(sys.stdout.buffer, {"phase": "committed", "nonce": request["nonce"]})
            # The bootstrap closes its pipes after the ownership transfer.
            # Later app updates must not write a new URL into that closed pipe.
            sys.stdout = open(os.devnull, "w")
            # Commit transfers lifetime to the app's explicit Exit control.
            thread.join()
        finally:
            server.shutdown()
            server.server_close()
            stopped = supervisor.close()
            thread.join()
    # A later update may have been requested in the newly installed app.
    if server.restart is not None:
        if not stopped:
            return 1
        next_entry, resume = server.restart
        if not handoff(
            config, next_entry, resume, port=server.server_port, token=server.token
        ):
            from .operator_app import run_app

            run_app(resume=resume)
    return 0
