# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import http.client
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx

from validator.file_lock import AlreadyRunning, exclusive_lock
from validator.operator_app import OperatorServer, Supervisor
from validator import operator_worker
from validator.operator_worker import error_code
from validator.account_pairing import PairingController
from tests.test_account_pairing import FakeCore


class OperatorHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.supervisor = Supervisor(Path(self.tmp.name) / ".env")
        self.server = OperatorServer(self.supervisor)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.supervisor.close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=5
        )
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def credentials(self):
        return {
            "Authorization": "Bearer " + self.server.token,
            "Origin": self.server.origin,
            "Content-Type": "application/json",
        }

    def test_static_ui_contains_no_session_token_and_has_csp(self):
        code, headers, body = self.request("GET", "/")
        self.assertEqual(code, 200)
        self.assertNotIn(self.server.token.encode(), body)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        self.assertEqual(headers["Referrer-Policy"], "no-referrer")
        self.assertIn(b"Set up and start", body)
        self.assertIn(b"Automatic setup check", body)
        for path in ("/app.js", "/app.css", "/logo.png"):
            self.assertEqual(self.request("GET", path)[0], 200)
        self.assertFalse(self.supervisor.path.exists())

    def test_private_status_and_diagnostics_require_session(self):
        for path in ("/status.json", "/diagnostics.json"):
            self.assertEqual(self.request("GET", path)[0], 401)
            status, _, body = self.request("GET", path, headers=self.credentials())
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)["phase"], "stopped")
            self.assertNotIn(str(self.supervisor.path).encode(), body)
            self.assertNotIn(self.server.token.encode(), body)

    def test_pairing_reads_are_cached_and_private_not_diagnostics(self):
        core = FakeCore()
        self.supervisor.pairing = PairingController(
            lambda: core.identity, httpx.MockTransport(core.handle)
        )
        self.assertEqual(self.request("GET", "/pairing.json")[0], 401)
        code, _, body = self.request("GET", "/pairing.json", headers=self.credentials())
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body), {"status": "idle", "busy": False})
        self.assertEqual(core.calls, [])
        self.assertEqual(
            self.request("POST", "/pairing", '{"action":"start"}', self.credentials())[
                0
            ],
            200,
        )
        core.status = "approved"
        code, _, body = self.request(
            "POST", "/pairing", '{"action":"refresh"}', self.credentials()
        )
        view = json.loads(body)
        self.assertEqual(view["status"], "approved")
        self.assertEqual(core.signatures, [])
        fields = {k: view[k] for k in ("pairing_id", "review_hash", "comparison_code")}
        form = json.dumps({"action": "confirm", **fields})
        self.assertLessEqual(len(form), 256)
        code, _, body = self.request("POST", "/pairing", form, self.credentials())
        self.assertEqual(json.loads(body)["status"], "linked")
        self.assertEqual(len(core.signatures), 1)
        for path in ("/diagnostics.json", "/status.json"):
            code, _, body = self.request("GET", path, headers=self.credentials())
            for private in (
                core.identity.api_key,
                core.identity.private_key,
                core.pair_id,
                core.code,
                core.operator_account,
            ):
                self.assertNotIn(private.encode(), body)

    def test_pairing_guards_reject_cross_site_and_unbounded_writes(self):
        core = FakeCore()
        self.supervisor.pairing = PairingController(
            lambda: core.identity, httpx.MockTransport(core.handle)
        )
        for override in (
            {"Host": "evil.example"},
            {"Origin": "https://evil.example"},
            {"Sec-Fetch-Site": "cross-site"},
            {"Authorization": "Bearer wrong"},
        ):
            headers = {**self.credentials(), **override}
            self.assertIn(
                self.request("GET", "/pairing.json", headers=headers)[0], (401, 403)
            )
            self.assertEqual(
                self.request("POST", "/pairing", '{"action":"start"}', headers)[0], 403
            )
        for body in (
            '{"action":"start","action":"refresh"}',
            '{"action":"start","private_key":"x"}',
            '{"action":"sign","payload":{}}',
            "x" * 257,
        ):
            self.assertEqual(
                self.request("POST", "/pairing", body, self.credentials())[0], 400
            )
        for override in (
            {"Transfer-Encoding": "chunked"},
            {"Content-Type": "text/plain"},
        ):
            self.assertEqual(
                self.request(
                    "POST",
                    "/pairing",
                    '{"action":"refresh"}',
                    {**self.credentials(), **override},
                )[0],
                400,
            )
        self.assertEqual(core.calls, [])
        self.assertFalse(self.supervisor.path.exists())

    def test_pairing_does_not_block_owned_run_stop_or_cached_status(self):
        entered, release = threading.Event(), threading.Event()
        core = FakeCore()

        def handle(request):
            entered.set()
            self.assertTrue(release.wait(4))
            return core.handle(request)

        self.supervisor.pairing = PairingController(
            lambda: core.identity, httpx.MockTransport(handle)
        )
        thread = threading.Thread(
            target=lambda: self.request(
                "POST", "/pairing", '{"action":"refresh"}', self.credentials()
            )
        )
        thread.start()
        try:
            self.assertTrue(entered.wait(3))
            self.assertTrue(
                json.loads(
                    self.request("GET", "/pairing.json", headers=self.credentials())[2]
                )["busy"]
            )
            with patch.object(self.supervisor, "stop") as stop:
                self.assertEqual(
                    self.request(
                        "POST", "/control", '{"action":"stop"}', self.credentials()
                    )[0],
                    202,
                )
                stop.assert_called_once()
            self.assertEqual(
                self.request("GET", "/status.json", headers=self.credentials())[0], 200
            )
        finally:
            release.set()
            thread.join(5)
        self.assertFalse(thread.is_alive())

    def test_host_and_foreign_origin_block_reads_and_writes(self):
        for override in (
            {"Host": "attacker.example"},
            {"Origin": "https://attacker.example"},
            {"Origin": "null"},
            {"Sec-Fetch-Site": "cross-site"},
        ):
            headers = {**self.credentials(), **override}
            self.assertEqual(
                self.request("GET", "/status.json", headers=headers)[0], 403
            )
            self.assertEqual(
                self.request("POST", "/control", '{"action":"run"}', headers)[0], 403
            )

    def test_write_requires_origin_and_token(self):
        for headers in (
            {},
            {"Origin": self.server.origin},
            {"Authorization": "Bearer " + self.server.token},
            {**self.credentials(), "Authorization": "Bearer wrong"},
            {**self.credentials(), "Authorization": "Bearer \xe9"},
        ):
            self.assertEqual(
                self.request("POST", "/control", '{"action":"run"}', headers)[0], 403
            )

    def test_actions_are_allowlisted_and_bounded(self):
        for body in (
            "{}",
            "[]",
            '{"action":[]}',
            '{"action":"shell"}',
            '{"action":"run","command":"other"}',
            "x" * 129,
        ):
            self.assertEqual(
                self.request("POST", "/control", body, self.credentials())[0], 400
            )
        self.assertEqual(
            self.request(
                "POST",
                "/control",
                '{"action":"run"}',
                {**self.credentials(), "Content-Type": "text/plain"},
            )[0],
            400,
        )
        self.assertFalse(self.supervisor.path.exists())

    def test_authorized_explicit_action_and_conflict(self):
        with patch.object(self.supervisor, "start", return_value=True) as start:
            self.assertEqual(
                self.request(
                    "POST", "/control", '{"action":"enroll"}', self.credentials()
                )[0],
                202,
            )
            start.assert_called_once_with("enroll")
        with patch.object(self.supervisor, "start", return_value=False):
            self.assertEqual(
                self.request(
                    "POST", "/control", '{"action":"run"}', self.credentials()
                )[0],
                409,
            )
        with patch.object(self.supervisor, "stop") as stop:
            self.assertEqual(
                self.request(
                    "POST", "/control", '{"action":"stop"}', self.credentials()
                )[0],
                202,
            )
            stop.assert_called_once()

    def test_unknown_paths_cannot_read_files(self):
        for path in ("/../.env", "/logo.png?token=secret", "/healthz", "/ui/AGENTS.md"):
            self.assertEqual(self.request("GET", path)[0], 404)

    def test_explicit_quit_closes_only_owned_supervisor_and_server(self):
        self.assertEqual(
            self.request("POST", "/control", '{"action":"quit"}', self.credentials())[
                0
            ],
            202,
        )
        self.thread.join(timeout=5)
        self.assertFalse(self.thread.is_alive())
        self.assertTrue(self.supervisor.closed)
        self.assertFalse(self.supervisor.start("run"))


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.supervisor = Supervisor(Path(self.tmp.name) / "node.env")

    def tearDown(self):
        self.supervisor.close()
        self.tmp.cleanup()

    def test_private_child_protocol_is_not_an_operator_command(self):
        from validator.cli import main

        output = io.StringIO()
        with (
            contextlib.redirect_stdout(output),
            self.assertRaises(SystemExit) as stopped,
        ):
            main(["--help"])
        self.assertEqual(stopped.exception.code, 0)
        self.assertIn("app", output.getvalue())
        self.assertNotIn("_operator-worker", output.getvalue())
        with patch("validator.cli._cmd_operator_worker", return_value=0) as child:
            self.assertEqual(main(["_operator-worker", "run"]), 0)
            self.assertEqual(child.call_args.args[0].action, "run")

    def test_events_are_allowlisted_not_a_log_relay(self):
        node_id = "val_" + "a" * 32
        self.supervisor.event(
            {
                "phase": "registered",
                "validator_id": node_id,
                "private_key": "secret",
                "message": "raw response",
            }
        )
        self.supervisor.event({"phase": "heartbeat"})
        self.supervisor.event(
            {
                "phase": "waiting",
                "accepted": 2,
                "assignments": 1,
                "pending": 1,
                "dead": 0,
                "latest_version": "v0.1.0-preview.14",
            }
        )
        self.supervisor.event({"phase": [], "error": []})
        self.supervisor.event(
            {"phase": "waiting", "accepted": True, "dead": -1, "message": "secret"}
        )
        data = self.supervisor.snapshot()
        self.assertEqual(data["accepted"], 2)
        self.assertEqual(data["validator_id"], node_id)
        self.assertTrue(data["heartbeat_at"])
        self.assertTrue(data["evidence_at"])
        self.assertTrue(data["assignment_at"])
        self.assertEqual(data["latest_version"], "v0.1.0-preview.14")
        self.assertEqual(
            data["checks"],
            {
                "configured": False,
                "registered": True,
                "heartbeat": True,
                "assignment": True,
                "evidence": True,
            },
        )
        self.assertNotIn("secret", json.dumps(data))
        self.assertNotIn("raw response", json.dumps(data))
        self.assertNotIn("private_key", json.dumps(data))

    def test_event_history_is_bounded(self):
        for _ in range(100):
            self.supervisor.event({"phase": "heartbeat"})
        self.assertEqual(len(self.supervisor.snapshot()["events"]), 40)

    def test_actual_child_rejects_invalid_config_and_can_restart(self):
        self.supervisor.path.write_text("VALIDATOR_PRIVATE_KEY=\nVALIDATOR_API_KEY=\n")
        with patch.dict(
            os.environ, {"VALIDATOR_API_KEY": "", "VALIDATOR_PRIVATE_KEY": ""}
        ):
            for _ in range(2):
                self.assertTrue(self.supervisor.start("run"))
                self.supervisor.reader.join(timeout=20)
                self.assertFalse(self.supervisor.reader.is_alive())
                state = self.supervisor.snapshot()
                self.assertEqual(state["error"], "configuration_invalid")
                self.assertFalse(state["running"])

    def test_stop_only_owns_created_process_and_preserves_config(self):
        self.supervisor.path.write_text("# preserved\n")
        # A real local child waits for parent EOF; no Grid or signing involved.
        with patch(
            "validator.operator_app.command_prefix",
            return_value=[
                sys.executable,
                "-c",
                'import json,sys; print(json.dumps({"phase":"heartbeat"}),flush=True); sys.stdin.read()',
            ],
        ):
            self.assertTrue(self.supervisor.start("run"))
            self.assertFalse(self.supervisor.start("run"))
            self.supervisor.stop()
            self.supervisor.reader.join(timeout=10)
        self.assertFalse(self.supervisor.snapshot()["running"])
        self.assertEqual(self.supervisor.snapshot()["phase"], "stopped")
        self.assertEqual(self.supervisor.path.read_text(), "# preserved\n")

    def test_parent_close_reaps_child(self):
        with patch(
            "validator.operator_app.command_prefix",
            return_value=[sys.executable, "-c", "import sys; sys.stdin.read()"],
        ):
            self.assertTrue(self.supervisor.start("run"))
            process = self.supervisor.process
            self.supervisor.close()
        self.assertIsNotNone(process.poll())
        self.assertFalse(self.supervisor.start("run"))

    def test_windows_force_stop_targets_the_owned_frozen_process_tree(self):
        process = Mock(pid=12345)
        process.wait.side_effect = [subprocess.TimeoutExpired("owned-child", 25), 0]
        with (
            patch("validator.operator_app.os.name", "nt"),
            patch("validator.operator_app.subprocess.run") as stop_tree,
        ):
            Supervisor._stop_deadline(process)
        self.assertEqual(
            stop_tree.call_args.args[0], ["taskkill", "/PID", "12345", "/T", "/F"]
        )
        process.kill.assert_not_called()

    def test_same_state_lock_rejects_concurrent_process_then_releases(self):
        path = Path(self.tmp.name) / "runtime.lock"
        command = [
            sys.executable,
            "-c",
            'import sys; from pathlib import Path; from validator.file_lock import exclusive_lock;\nwith exclusive_lock(Path(sys.argv[1])): print("acquired")',
            str(path),
        ]
        with exclusive_lock(path):
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("AlreadyRunning", result.stderr)
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)

    def test_error_classification_never_contains_response(self):
        response = httpx.Response(
            401,
            request=httpx.Request("POST", "https://grid.example"),
            text="private material",
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            self.assertEqual(error_code(exc), "credentials_rejected")
        self.assertEqual(error_code(AlreadyRunning()), "already_running")
        self.assertEqual(error_code(ValueError("secret")), "runtime_error")


class RuntimeStatusTests(unittest.IsolatedAsyncioTestCase):
    async def test_clock_drift_uses_bounded_grid_date(self):
        class Client:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def get(self, path):
                self.path = path
                return httpx.Response(
                    200,
                    headers={
                        "Date": format_datetime(
                            datetime.now(timezone.utc) - timedelta(minutes=10),
                            usegmt=True,
                        )
                    },
                    request=httpx.Request("GET", "https://grid.example/health"),
                )

        client = Client()
        with patch.object(operator_worker.httpx, "AsyncClient", return_value=client):
            drift = await operator_worker.clock_drift_seconds("https://grid.example")
        self.assertEqual(client.path, "/health")
        self.assertGreaterEqual(drift, 599)

    async def test_confirmed_enrollment_continues_into_validator_loop(self):
        events = []
        run = AsyncMock(return_value=None)
        with (
            patch("validator.enrollment.enroll") as enroll,
            patch("validator.launcher.config_path", return_value=Path("node.env")),
            patch.object(operator_worker, "clock_drift_seconds", new=AsyncMock(return_value=0)),
            patch("validator.config.Settings.validate"),
            patch("validator.main.run", new=run),
        ):
            result = await operator_worker._run_action(
                "enroll", lambda phase, **values: events.append({"phase": phase, **values})
            )
        self.assertEqual(result, 0)
        enroll.assert_called_once_with(Path("node.env"))
        self.assertEqual(events[:2], [{"phase": "enrolling"}, {"phase": "enrolled"}])
        run.assert_awaited_once()

    async def test_clock_drift_blocks_signed_runtime(self):
        events = []
        run = AsyncMock(return_value=None)
        with (
            patch.object(operator_worker, "clock_drift_seconds", new=AsyncMock(return_value=301)),
            patch("validator.config.Settings.validate"),
            patch("validator.main.run", new=run),
        ):
            result = await operator_worker._run_action(
                "run", lambda phase, **values: events.append({"phase": phase, **values})
            )
        self.assertEqual(result, 1)
        self.assertEqual(events, [{"phase": "error", "error": "clock_drift"}])
        run.assert_not_awaited()

    async def test_real_connection_failure_keeps_network_error_category(self):
        import socket

        # Reserve a port without listening, so no other service can take it.
        with socket.socket() as unavailable:
            unavailable.bind(("127.0.0.1", 0))
            port = unavailable.getsockname()[1]
            async with httpx.AsyncClient(trust_env=False, timeout=2) as client:
                with self.assertRaises(
                    (httpx.ConnectError, httpx.ConnectTimeout)
                ) as caught:
                    await client.get(f"http://127.0.0.1:{port}/")
        failure = caught.exception
        self.assertIsNotNone(failure.__cause__)
        self.assertEqual(error_code(failure), "grid_unavailable")
        wrapped = RuntimeError("private startup detail")
        wrapped.__cause__ = failure
        self.assertEqual(error_code(wrapped), "grid_unavailable")

    async def test_cancel_during_registration_closes_client(self):
        from validator import main

        grid = AsyncMock()
        grid.register_validator.side_effect = asyncio.CancelledError
        with (
            patch.object(main, "GridClient", return_value=grid),
            patch.object(main.attest, "build_registration", return_value={}),
            patch.object(main.attest, "sign", return_value={}),
        ):
            with self.assertRaises(asyncio.CancelledError):
                await main._run_registered()
        grid.aclose.assert_awaited_once()

    async def test_runtime_reports_actual_acknowledgements_and_counts(self):
        from validator import main

        events = []
        grid = AsyncMock()
        grid.register_validator.return_value = {"validator_id": "val_" + "b" * 32}
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(
                main.Settings, "STATE_DB_PATH", str(Path(tmp) / "state.sqlite3")
            ),
            patch.object(main.Settings, "UPDATE_CHECK_ENABLED", False),
            patch.object(main, "GridClient", return_value=grid),
            patch.object(main.attest, "build_registration", return_value={}),
            patch.object(main.attest, "sign", return_value={}),
            patch.object(main, "probe_round", new=AsyncMock(return_value=2)),
            patch.object(main.asyncio, "sleep", side_effect=asyncio.CancelledError),
        ):
            with self.assertRaises(asyncio.CancelledError):
                await main._run_registered(
                    lambda phase, **values: events.append({"phase": phase, **values})
                )
        self.assertIn({"phase": "heartbeat"}, events)
        self.assertIn(
            {"phase": "waiting", "accepted": 2, "pending": 0, "dead": 0}, events
        )
        grid.aclose.assert_awaited_once()

    async def test_failed_heartbeat_is_not_reported_healthy(self):
        from validator import main

        events = []
        grid = AsyncMock()
        grid.register_validator.return_value = {"validator_id": "val_" + "b" * 32}
        grid.heartbeat.side_effect = httpx.ConnectError("secret server detail")
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(
                main.Settings, "STATE_DB_PATH", str(Path(tmp) / "state.sqlite3")
            ),
            patch.object(main.Settings, "UPDATE_CHECK_ENABLED", False),
            patch.object(main, "GridClient", return_value=grid),
            patch.object(main.attest, "build_registration", return_value={}),
            patch.object(main.attest, "sign", return_value={}),
            patch.object(main.asyncio, "sleep", side_effect=asyncio.CancelledError),
        ):
            with self.assertRaises(asyncio.CancelledError):
                await main._run_registered(
                    lambda phase, **values: events.append({"phase": phase, **values})
                )
        self.assertNotIn({"phase": "heartbeat"}, events)
        self.assertIn({"phase": "retrying", "error": "grid_unavailable"}, events)
        self.assertNotIn("secret", json.dumps(events))
