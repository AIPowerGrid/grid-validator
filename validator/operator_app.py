# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Explicit loopback-only UI controlling only its own validator subprocess."""

from __future__ import annotations

import contextlib
import hmac
import json
import os
import re
import secrets
import subprocess
import threading
import webbrowser
from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from . import __release_tag__
from .account_pairing import Identity, PairingController, _unique_object
from .file_lock import exclusive_lock
from .launcher import command_prefix, config_path, operator_config

PHASES = {
    "starting",
    "registering",
    "registered",
    "heartbeat",
    "probing",
    "waiting",
    "retrying",
    "error",
    "enrolling",
    "enrolled",
    "stopping",
    "stopped",
}
ERRORS = {
    "configuration_invalid",
    "credentials_rejected",
    "grid_unavailable",
    "already_running",
    "enrollment_failed",
    "runtime_error",
    "process_exited",
    "local_access",
    "clock_drift",
}
ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/logo.png": ("logo.png", "image/png"),
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Supervisor:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.RLock()
        self.process: subprocess.Popen[bytes] | None = None
        self.reader: threading.Thread | None = None
        self.action: str | None = None
        self.closed = False
        self.pairing = PairingController(
            lambda: Identity.from_values(operator_config(self.path))
        )
        self.events: deque[dict[str, Any]] = deque(maxlen=40)
        self.state: dict[str, Any] = {
            "phase": "stopped",
            "error": "",
            "validator_id": "",
            "heartbeat_at": None,
            "assignment_at": None,
            "evidence_at": None,
            "accepted": 0,
            "assignments": 0,
            "pending": None,
            "dead": None,
            "latest_version": "",
        }

    def event(self, raw: dict[str, Any]) -> None:
        phase = raw.get("phase")
        if not isinstance(phase, str) or phase not in PHASES:
            return
        event: dict[str, Any] = {"phase": phase, "at": now()}
        for key in ("assignments", "pending", "dead", "accepted"):
            value = raw.get(key)
            if type(value) is int and 0 <= value <= 1_000_000:
                event[key] = value
        if isinstance(raw.get("error"), str) and raw["error"] in ERRORS:
            event["error"] = raw["error"]
        identity = raw.get("validator_id")
        if isinstance(identity, str) and re.fullmatch(r"val_[a-f0-9]{32}", identity):
            event["validator_id"] = identity
        latest_version = raw.get("latest_version")
        if isinstance(latest_version, str) and re.fullmatch(
            r"v[0-9]+\.[0-9]+\.[0-9]+(?:-(?:preview|alpha|beta|rc)(?:\.[0-9]+)?)?",
            latest_version,
        ):
            event["latest_version"] = latest_version
        with self.lock:
            self.events.append(event)
            if self.state["phase"] != "stopping":
                self.state["phase"] = phase
            self.state["error"] = event.get("error", "")
            for key in (
                "assignments",
                "pending",
                "dead",
                "validator_id",
                "latest_version",
            ):
                if key in event:
                    self.state[key] = event[key]
            if phase == "heartbeat":
                self.state["heartbeat_at"] = event["at"]
            if event.get("assignments", 0):
                self.state["assignment_at"] = event["at"]
            if event.get("accepted", 0):
                self.state["accepted"] += event["accepted"]
                self.state["evidence_at"] = event["at"]

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            try:
                values = operator_config(self.path)
                configured = all(
                    values.get(k)
                    for k in (
                        "VALIDATOR_API_KEY",
                        "VALIDATOR_PRIVATE_KEY",
                        "VALIDATOR_WALLET",
                    )
                )
            except (OSError, UnicodeError):
                configured = False
            checks = {
                "configured": configured,
                "registered": bool(self.state["validator_id"]),
                "heartbeat": self.state["heartbeat_at"] is not None,
                "assignment": self.state["assignment_at"] is not None,
                "evidence": self.state["evidence_at"] is not None,
            }
            return {
                "schema": "aipg.validator.operator.v1",
                "version": __release_tag__,
                "checked_at": now(),
                "configured": configured,
                "running": self.process is not None and self.process.poll() is None,
                "action": self.action,
                "checks": checks,
                **self.state,
                "events": list(self.events),
            }

    def start(self, action: str) -> bool:
        if action not in {"run", "enroll"}:
            raise ValueError("Unknown operation")
        with self.lock:
            if (
                self.closed
                or self.process is not None
                or (self.reader and self.reader.is_alive())
            ):
                return False
            env = os.environ.copy()
            env["VALIDATOR_ENV"] = str(self.path)
            options = (
                {"creationflags": subprocess.CREATE_NO_WINDOW}
                if os.name == "nt"
                else {}
            )
            try:
                process = subprocess.Popen(
                    command_prefix() + ["_operator-worker", action],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    env=env,
                    **options,
                )
            except OSError:
                self.event({"phase": "error", "error": "local_access"})
                return False
            self.process = process
            self.action = action
            self.state.update(
                phase="starting",
                error="",
                validator_id="",
                heartbeat_at=None,
                assignment_at=None,
                evidence_at=None,
                accepted=0,
                assignments=0,
            )
            self.reader = threading.Thread(
                target=self._read, args=(process,), daemon=True
            )
            self.reader.start()
            return True

    def _read(self, process: subprocess.Popen[bytes]) -> None:
        assert process.stdout is not None and process.stdin is not None
        try:
            with process.stdout:
                while line := process.stdout.readline(4097):
                    if len(line) > 4096:
                        process.kill()
                        self.event({"phase": "error", "error": "runtime_error"})
                        break
                    try:
                        data = json.loads(line)
                    except (ValueError, UnicodeError):
                        continue
                    if isinstance(data, dict):
                        self.event(data)
            code = process.wait()
            with self.lock:
                if self.state["phase"] == "stopping":
                    self.state.update(phase="stopped", error="")
                elif code != 0:
                    self.state.update(
                        phase="error", error=self.state["error"] or "process_exited"
                    )
                elif self.state["phase"] != "enrolled":
                    self.state["phase"] = "stopped"
        finally:
            with contextlib.suppress(OSError):
                process.stdin.close()
            with self.lock:
                self.process = None
                self.action = None

    def stop(self) -> None:
        with self.lock:
            process = self.process
            if process is None or self.state["phase"] == "stopping":
                return
            self.state["phase"] = "stopping"
            assert process.stdin is not None
            with contextlib.suppress(OSError):
                process.stdin.close()
            threading.Thread(
                target=self._stop_deadline, args=(process,), daemon=True
            ).start()

    @staticmethod
    def _stop_deadline(process: subprocess.Popen[bytes]) -> None:
        try:
            process.wait(timeout=25)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                # A frozen Windows executable has a bootloader plus an app child.
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=10,
                )
            else:
                process.kill()
            process.wait(timeout=5)

    def close(self) -> bool:
        with self.lock:
            self.closed = True
        self.pairing.close()
        self.stop()
        if self.reader:
            self.reader.join(timeout=45)
        return self.reader is None or not self.reader.is_alive()


class OperatorServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, supervisor: Supervisor, port: int = 0) -> None:
        super().__init__(("127.0.0.1", port), OperatorHandler)
        self.supervisor = supervisor
        self.token = secrets.token_urlsafe(32)
        self.origin = f"http://127.0.0.1:{self.server_port}"

    def get_request(self):
        sock, address = super().get_request()
        sock.settimeout(3)
        return sock, address


class OperatorHandler(BaseHTTPRequestHandler):
    server_version = "AIPGValidatorOperator"
    server: OperatorServer

    def log_message(self, *_args: object) -> None:
        pass

    def _allowed(self, write: bool = False) -> bool:
        expected_host = self.server.origin.removeprefix("http://")
        if self.headers.get_all("Host") != [expected_host]:
            return False
        origin = self.headers.get_all("Origin", [])
        if origin and origin != [self.server.origin]:
            return False
        if write and origin != [self.server.origin]:
            return False
        return self.headers.get("Sec-Fetch-Site", "same-origin") != "cross-site"

    def _authorized(self) -> bool:
        values = self.headers.get_all("Authorization", [])
        return len(values) == 1 and hmac.compare_digest(
            values[0].encode("utf-8"), ("Bearer " + self.server.token).encode("ascii")
        )

    def _send(
        self, status: int, data: bytes | dict[str, Any], kind: str = "application/json"
    ) -> None:
        body = data if isinstance(data, bytes) else json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
        )
        self.end_headers()
        with contextlib.suppress(BrokenPipeError, ConnectionResetError):
            self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if not self._allowed():
            self._send(403, {"error": "local_origin_required"})
        elif self.path in ASSETS:
            name, kind = ASSETS[self.path]
            self._send(200, (Path(__file__).parent / "ui" / name).read_bytes(), kind)
        elif self.path in {"/status.json", "/diagnostics.json", "/pairing.json"}:
            if not self._authorized():
                self._send(401, {"error": "local_session_required"})
                return
            # Account association metadata never enters shareable diagnostics.
            data = (
                self.server.supervisor.pairing.snapshot()
                if self.path == "/pairing.json"
                else self.server.supervisor.snapshot()
            )
            self._send(200, data)
        else:
            self._send(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if not self._allowed(write=True) or not self._authorized():
            self._send(403, {"error": "local_session_required"})
            return
        if self.path not in {"/control", "/pairing"}:
            self._send(404, {"error": "not_found"})
            return
        lengths = self.headers.get_all("Content-Length", [])
        if (
            self.headers.get("Transfer-Encoding")
            or len(lengths) != 1
            or len(lengths[0]) > 3
            or not lengths[0].isdigit()
            or not 0 < int(lengths[0]) <= (256 if self.path == "/pairing" else 128)
            or self.headers.get_all("Content-Type") != ["application/json"]
        ):
            self._send(400, {"error": "invalid_request"})
            return
        try:
            body = json.loads(
                self.rfile.read(int(lengths[0])), object_pairs_hook=_unique_object
            )
        except (ValueError, TimeoutError):
            self._send(400, {"error": "invalid_request"})
            return
        if self.path == "/pairing":
            status, result = self.server.supervisor.pairing.perform(body)
            self._send(status, result)
            return
        if (
            not isinstance(body, dict)
            or set(body) != {"action"}
            or not isinstance(body["action"], str)
            or body["action"] not in {"run", "stop", "enroll", "quit"}
        ):
            self._send(400, {"error": "invalid_action"})
            return
        if body["action"] == "quit":
            if not self.server.supervisor.close():
                self._send(409, {"ok": False})
                return
            self._send(202, {"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        elif body["action"] == "stop":
            self.server.supervisor.stop()
            self._send(202, {"ok": True})
        else:
            started = self.server.supervisor.start(body["action"])
            self._send(202 if started else 409, {"ok": started})


def run_app(port: int = 0, open_browser: bool = True) -> None:
    if not 0 <= port <= 65535:
        raise RuntimeError("App port must be between 0 and 65535.")
    path = config_path()
    with exclusive_lock(Path(str(path) + ".app.lock")):
        supervisor = Supervisor(path)
        server = OperatorServer(supervisor, port)
        url = server.origin + "/#" + server.token
        print("Local validator app: " + url, flush=True)
        print("Keep this app process open. Do not share its private local URL.")
        try:
            if open_browser:
                webbrowser.open(url)
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
            supervisor.close()
