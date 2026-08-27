# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Opt-in real Console/HTTP/Core/node handoff with disposable local identities.

Set VALIDATOR_CORE_SOURCE and VALIDATOR_CONSOLE_SOURCE (built with pnpm build).
No Google login, wallet-extension UI, production service, or real funds are used.
"""

import asyncio
import os
import secrets
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import httpx
from eth_account.messages import encode_defunct

from tests import test_core_pairing_integration as core_fixture

CONSOLE_SOURCE = os.environ.get("VALIDATOR_CONSOLE_SOURCE")


@unittest.skipUnless(
    core_fixture.CORE_SOURCE and CONSOLE_SOURCE,
    "set VALIDATOR_CORE_SOURCE and VALIDATOR_CONSOLE_SOURCE for local HTTP proof",
)
class ConsolePairingIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        import uvicorn

        source = Path(CONSOLE_SOURCE).resolve()
        self.assertTrue(
            (source / ".next/BUILD_ID").is_file(), "Build the Console first"
        )
        for name in (".env", ".env.local", ".env.production", ".env.production.local"):
            self.assertFalse(
                (source / name).exists(), "Use an env-file-free test checkout"
            )
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node.js is required for this optional test")
        self.fixture = core_fixture.ActualCorePairingTests()
        await self.fixture.asyncSetUp()
        self.addAsyncCleanup(self.fixture.asyncTearDown)
        f = self.fixture
        self.requests = []

        async def record_paths(scope, receive, send):
            async def record_response(message):
                if message["type"] == "http.response.start":
                    self.requests.append(
                        (scope["method"], scope["path"], message["status"])
                    )
                await send(message)

            await f.app(scope, receive, record_response)

        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        self.addCleanup(listener.close)
        self.core_origin = f"http://127.0.0.1:{listener.getsockname()[1]}"
        self.server = uvicorn.Server(
            uvicorn.Config(
                record_paths,
                lifespan="off",
                access_log=False,
                log_level="critical",
                log_config=None,
                timeout_graceful_shutdown=5,
            )
        )
        self.server_task = asyncio.create_task(self.server.serve(sockets=[listener]))
        self.addAsyncCleanup(self.stop_core)
        for _ in range(100):
            if self.server.started:
                break
            if self.server_task.done():
                self.fail("Local Core server exited before startup")
            await asyncio.sleep(0.05)
        self.assertTrue(self.server.started)
        await f.http.aclose()
        f.http = httpx.AsyncClient(
            base_url=self.core_origin, trust_env=False, timeout=10
        )

        # Only this temporary SQLite database receives the synthetic service key.
        service_account = uuid4()
        service_key = f.accounts.generate_api_key()
        async with f.factory() as session:
            await session.execute(
                f.sa.insert(f.db.accounts).values(id=service_account, flags={})
            )
            await session.execute(
                f.sa.insert(f.db.service_clients).values(
                    id="pairing-console-test",
                    account_id=service_account,
                    name="Disposable pairing Console",
                    allowed_providers=["app"],
                )
            )
            await session.execute(
                f.sa.insert(f.db.api_keys).values(
                    hash=f.auth.hash_api_key(service_key),
                    account_id=service_account,
                    key_kind="service",
                    service_id="pairing-console-test",
                    scopes=f.accounts.SERVICE_SCOPES,
                    is_session=False,
                    revoked=False,
                )
            )
            await session.commit()

        with socket.socket() as port_probe:
            port_probe.bind(("127.0.0.1", 0))
            port = port_probe.getsockname()[1]
        # NextURL canonicalizes loopback hosts to localhost for auth redirects.
        self.origin = f"http://localhost:{port}"
        temp = tempfile.TemporaryDirectory(prefix="validator-console-http-")
        self.addCleanup(temp.cleanup)
        self.console_log = tempfile.TemporaryFile()
        self.addCleanup(self.console_log.close)
        self.console = subprocess.Popen(
            [
                node,
                str(source / "node_modules/next/dist/bin/next"),
                "start",
                "--hostname",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=source,
            env={
                "PATH": os.environ.get("PATH", ""),
                "HOME": temp.name,
                "NODE_ENV": "production",
                "NEXT_TELEMETRY_DISABLED": "1",
                "AUTH_URL": self.origin,
                "NEXTAUTH_URL": self.origin,
                "AUTH_TRUST_HOST": "true",
                "AUTH_SECRET": secrets.token_hex(32),
                "GRID_API_BASE": self.core_origin,
                "GRID_SERVICE_API_KEY": service_key,
            },
            stdin=subprocess.DEVNULL,
            stdout=self.console_log,
            stderr=subprocess.STDOUT,
        )
        self.addAsyncCleanup(self.stop_console)
        self.browser = httpx.AsyncClient(
            base_url=self.origin, trust_env=False, timeout=15
        )
        self.addAsyncCleanup(self.browser.aclose)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            self.assertIsNone(
                self.console.poll(), "Local Console exited before startup"
            )
            try:
                response = await self.browser.get("/api/auth/csrf")
                if response.status_code == 200:
                    break
            except httpx.TransportError:
                pass
            await asyncio.sleep(0.1)
        else:
            self.fail("Local Console did not become ready")
        self.headers = {"Origin": self.origin, "Sec-Fetch-Site": "same-origin"}

    async def stop_console(self):
        if self.console.poll() is None:
            self.console.terminate()
            try:
                await asyncio.to_thread(self.console.wait, timeout=10)
            except subprocess.TimeoutExpired:
                self.console.kill()
                await asyncio.to_thread(self.console.wait, timeout=5)

    async def stop_core(self):
        self.server.should_exit = True
        try:
            await asyncio.wait_for(self.server_task, timeout=10)
        except asyncio.TimeoutError:
            self.server_task.cancel()
            await asyncio.gather(self.server_task, return_exceptions=True)

    async def wallet_login(self):
        signer = self.fixture.human_signer
        response = await self.browser.post(
            "/api/auth/nonce",
            headers=self.headers,
            json={"address": signer.address},
        )
        self.assertEqual(response.status_code, 200)
        challenge = response.json()
        csrf = (await self.browser.get("/api/auth/csrf")).json()["csrfToken"]
        response = await self.browser.post(
            "/api/auth/callback/web3",
            headers=self.headers,
            data={
                "csrfToken": csrf,
                "callbackUrl": self.origin + "/dashboard",
                "address": signer.address,
                "nonce": challenge["nonce"],
                "message": challenge["message"],
                "signature": signer.sign_message(
                    encode_defunct(
                        text=challenge["message"],
                    )
                ).signature.hex(),
            },
        )
        self.assertEqual(response.status_code, 302)
        destination = urlsplit(response.headers.get("location", ""))
        self.assertEqual(
            destination.path,
            "/dashboard",
            f"Wallet callback failed: {parse_qs(destination.query).get('error', [])}; "
            f"Core HTTP statuses: {self.requests}",
        )
        session = await self.browser.get("/api/auth/session")
        self.assertEqual(session.status_code, 200)
        self.assertEqual(session.json()["user"]["id"], f"web3_{signer.address.lower()}")
        for forbidden in ("gridAccessToken", "gridApiKey", "private_key"):
            self.assertNotIn(forbidden, session.text)

    async def test_real_wallet_login_pairing_consent_and_owner_removal(self):
        f = self.fixture
        start = await f.act("start")
        path = f"/api/validator-pairings/{start['pairing_id']}"
        self.assertEqual((await self.browser.get(path)).status_code, 401)
        await self.wallet_login()
        before = await f.snapshot()
        response = await self.browser.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "pending")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertNotIn("payload", response.json())
        self.assertEqual((await f.act("refresh"))["status"], "pending")
        denied = await self.browser.post(
            path + "/approve",
            headers={"Origin": "https://attacker.example"},
            json={},
        )
        self.assertEqual(denied.status_code, 403)
        response = await self.browser.post(
            path + "/approve", headers=self.headers, json={}
        )
        self.assertEqual(response.status_code, 200)
        approved = await f.act("refresh")
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(
            approved["comparison_code"], response.json()["comparison_code"]
        )
        self.assertEqual(await f.listed(), [])
        linked = await f.act(
            "confirm",
            **{
                key: approved[key]
                for key in ("pairing_id", "comparison_code", "review_hash")
            },
        )
        self.assertEqual(linked["status"], "linked")
        nodes = await self.browser.get("/api/account/validators")
        self.assertEqual(nodes.status_code, 200)
        self.assertEqual(
            [row["validator_id"] for row in nodes.json()["nodes"]], [f.node]
        )
        self.assertEqual(before, await f.snapshot())
        removed = await self.browser.post(
            f"/api/account/validators/{f.node}/unlink",
            headers=self.headers,
            json={"pairing_id": linked["pairing_id"]},
        )
        self.assertEqual(removed.status_code, 200)
        self.assertEqual((await f.act("refresh"))["status"], "cancelled")
        self.assertEqual(await f.listed(), [])
        self.assertEqual(before, await f.snapshot())
        for expected in (
            ("POST", "/v1/accounts/wallet/challenge", 200),
            ("POST", "/v1/accounts/wallet/verify", 200),
            ("POST", "/v1/auth/service/bind", 200),
            (
                "POST",
                f"/v1/account/validator-pairings/{start['pairing_id']}/approve",
                200,
            ),
        ):
            self.assertIn(expected, self.requests)
