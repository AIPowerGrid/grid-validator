# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Optional actual-Core HTTP integration; only an in-memory SQLite database.

Use a Core dependency environment and set VALIDATOR_CORE_SOURCE to its reviewed
checkout. SIWE/auth/router code is real; ASGI transport and the nonce store are
local fixtures. This is not a browser OAuth, live Redis or native live proof.
"""

import asyncio
import json
import os
import secrets
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import httpx
from eth_account import Account
from eth_account.messages import encode_defunct

from validator.account_pairing import CONSOLE_URL, GRID_URL, Identity, PairingController

CORE_SOURCE = os.environ.get("VALIDATOR_CORE_SOURCE")


class NonceStore:
    """Single-process expiring nonce fixture, never a production Redis claim."""

    def __init__(self):
        self.values = {}

    async def set(self, key, value, *, ex):
        self.values[key] = (value, time.monotonic() + ex)

    async def get(self, key):
        value, deadline = self.values.get(key, (None, 0))
        return value if time.monotonic() < deadline else None

    async def getdel(self, key):
        value = await self.get(key)
        self.values.pop(key, None)
        return value


@unittest.skipUnless(
    CORE_SOURCE, "set VALIDATOR_CORE_SOURCE and use a Core dependency environment"
)
class ActualCorePairingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        try:
            await self.set_up_core()
        except BaseException:
            await self.asyncTearDown()
            raise

    async def set_up_core(self):
        self.core_path = str(Path(CORE_SOURCE).resolve())
        sys.path.insert(0, self.core_path)
        import sqlalchemy as sa
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        from sqlalchemy.pool import StaticPool
        from fastapi import FastAPI
        from grid_api import auth, database, redis_client
        from grid_api.ratelimit import limiter
        from grid_api.routers import accounts as account_router
        from grid_api.routers import validator as validator_router
        from grid_api.routers import validator_pairing as pairing_router
        from grid_api.services import accounts, user_tokens
        from grid_api.services import validator_pairing
        from grid_api.v2 import schema

        self.sa, self.core, self.db = sa, validator_pairing, schema
        self.auth, self.accounts, self.user_tokens = auth, accounts, user_tokens
        self.engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)

        @sa.event.listens_for(self.engine.sync_engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        async with self.engine.begin() as conn:
            await conn.run_sync(schema.metadata.create_all)
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)

        async def new_session():
            return self.factory()

        self.settings = SimpleNamespace(
            validator_pairing_audience=GRID_URL,
            validator_pairing_console_url=CONSOLE_URL,
            validator_pairing_enabled=True,
        )
        self.patches = [
            patch.dict(
                os.environ,
                {
                    "GRID_USER_TOKEN_SIGNING_KEY": secrets.token_hex(32),
                    "GRID_SALT": secrets.token_hex(16),
                    "GRID_SIWE_ALLOWED_DOMAINS": "console.aipowergrid.io",
                    "GRID_LEGACY_SIWE_VERIFY_ENABLED": "0",
                    "GRID_LEGACY_SESSION_KEYS_ENABLED": "0",
                },
            ),
            patch.object(auth, "_API_KEY_SALT", None),
            patch.object(database, "_session_factory", self.factory),
            patch.object(redis_client, "get_redis", lambda: self.nonces),
            patch.object(limiter, "enabled", False),
            patch.object(self.core, "new_session", new_session),
            patch.object(self.core, "get_settings", lambda: self.settings),
            patch.object(pairing_router, "get_settings", lambda: self.settings),
        ]
        self.nonces = NonceStore()
        for mocked in self.patches:
            mocked.start()
        signer = Account.create()
        self.identity = Identity(
            signer.address.lower(),
            "grid_" + secrets.token_urlsafe(32),
            signer.key.hex(),
        )
        self.account, self.human, self.other = uuid4(), uuid4(), uuid4()
        self.human_signer, self.other_signer = Account.create(), Account.create()
        wallets = {
            self.account: self.identity.wallet,
            self.human: self.human_signer.address.lower(),
            self.other: self.other_signer.address.lower(),
        }
        async with self.factory() as session:
            for aid in (self.account, self.human, self.other):
                await session.execute(
                    sa.insert(schema.accounts).values(
                        id=aid,
                        wallet=wallets[aid],
                        payout_wallet=None,
                        flags={},
                    )
                )
                await session.execute(
                    sa.insert(schema.credits).values(
                        account_id=aid, balance_micro=12345
                    )
                )
            self.ordinary_key = accounts.generate_api_key()
            for key, aid, scopes in (
                (self.identity.api_key, self.account, accounts.VALIDATOR_SCOPES),
                (self.ordinary_key, self.human, accounts.INFERENCE_SCOPES),
            ):
                await session.execute(
                    sa.insert(schema.api_keys).values(
                        hash=auth.hash_api_key(key),
                        account_id=aid,
                        scopes=scopes,
                        is_session=False,
                        revoked=False,
                    )
                )
            await session.commit()
        app = FastAPI()
        for router in (
            account_router.router,
            validator_router.router,
            pairing_router.router,
        ):
            app.include_router(router)
        self.app = app
        self.http = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url=GRID_URL,
        )
        self.human_token = await self.sign_in(self.human_signer, self.human)
        self.other_token = await self.sign_in(self.other_signer, self.other)
        registration = {
            "registration_schema": "aipg.validator.registration.v1",
            "validator": self.identity.wallet,
            "software_version": "integration-test",
            "capabilities": ["text.basic.v1"],
            "ts": int(time.time()),
        }
        response = await self.http.post(
            "/v1/validator/register",
            headers={"apikey": self.identity.api_key},
            json={
                "payload": registration,
                "signature": signer.sign_message(
                    encode_defunct(
                        text=json.dumps(
                            registration, sort_keys=True, separators=(",", ":")
                        ),
                    )
                ).signature.hex(),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.node = response.json()["validator_id"]
        self.loop = asyncio.get_running_loop()
        self.lose_confirmation = False
        self.controller = self.new_controller()

    def new_controller(self):
        def transport(request):
            response = asyncio.run_coroutine_threadsafe(
                self.dispatch(request), self.loop
            ).result(timeout=5)
            if self.lose_confirmation and request.url.path.endswith("/confirm"):
                raise httpx.ReadError("synthetic response lost after real Core commit")
            return httpx.Response(
                response.status_code,
                headers=response.headers,
                stream=httpx.ByteStream(response.content),
            )

        return PairingController(lambda: self.identity, httpx.MockTransport(transport))

    async def dispatch(self, request):
        self.assertEqual(request.url.host, "api.aipowergrid.io")
        self.assertEqual(request.headers["apikey"], self.identity.api_key)
        return await self.http.request(
            request.method,
            request.url.path,
            headers=request.headers,
            content=request.content,
        )

    async def sign_in(self, signer, account_id):
        response = await self.http.post(
            "/v1/accounts/wallet/challenge",
            json={
                "address": signer.address,
                "domain": "console.aipowergrid.io",
                "uri": "https://console.aipowergrid.io",
                "chain_id": 8453,
            },
        )
        self.assertEqual(response.status_code, 200)
        message = response.json()["message"]
        form = {
            "message": message,
            "address": signer.address,
            "signature": signer.sign_message(
                encode_defunct(text=message)
            ).signature.hex(),
        }
        response = await self.http.post("/v1/accounts/wallet/verify", json=form)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["account_id"], str(account_id))
        self.assertIsNone(response.json()["api_key"])
        replay = await self.http.post("/v1/accounts/wallet/verify", json=form)
        self.assertEqual(replay.status_code, 401)
        return response.json()["access_token"]

    async def approve(self, pairing_id):
        response = await self.http.post(
            f"/v1/account/validator-pairings/{pairing_id}/approve",
            headers={"Authorization": f"Bearer {self.human_token}"},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    async def listed(self, token=None):
        response = await self.http.get(
            "/v1/account/validators",
            headers={"Authorization": f"Bearer {token or self.human_token}"},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["nodes"]

    async def act(self, action, **kwargs):
        status, view = await asyncio.to_thread(
            self.controller.perform, {"action": action, **kwargs}
        )
        self.assertEqual(status, 200)
        return view

    async def snapshot(self):
        tables = [
            self.db.accounts,
            self.db.account_aliases,
            self.db.account_identities,
            self.db.api_keys,
            self.db.credits,
            self.db.credit_ledger,
            self.db.ledger,
            self.db.validators,
        ]
        async with self.factory() as session:
            return {
                t.name: [
                    # Normal authentication stamps these two operational fields.
                    {
                        key: value
                        for key, value in row.items()
                        if (t.name, key)
                        not in {
                            ("grid_accounts", "last_active"),
                            ("grid_api_keys", "last_used"),
                        }
                    }
                    for row in (await session.execute(self.sa.select(t))).mappings()
                ]
                for t in tables
            }

    async def asyncTearDown(self):
        if hasattr(self, "controller"):
            self.controller.close()
        if hasattr(self, "http"):
            await self.http.aclose()
        for mocked in reversed(getattr(self, "patches", [])):
            mocked.stop()
        if hasattr(self, "engine"):
            await self.engine.dispose()
        if hasattr(self, "core_path") and self.core_path in sys.path:
            sys.path.remove(self.core_path)

    async def test_actual_core_link_list_remove_preserves_non_pairing_state(self):
        before = await self.snapshot()
        start = await self.act("start")
        self.assertEqual(start["status"], "pending")
        await self.approve(start["pairing_id"])
        approved = await self.act("refresh")
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(await self.listed(), [])
        linked = await self.act(
            "confirm",
            **{
                k: approved[k] for k in ("pairing_id", "comparison_code", "review_hash")
            },
        )
        self.assertEqual(linked["status"], "linked")
        nodes = await self.listed()
        self.assertEqual([node["validator_id"] for node in nodes], [self.node])
        self.assertEqual(await self.listed(self.other_token), [])
        self.assertEqual(before, await self.snapshot())
        self.assertEqual(
            (
                await self.act(
                    "unlink", **{k: linked[k] for k in ("pairing_id", "review_hash")}
                )
            )["status"],
            "none",
        )
        self.assertEqual(await self.listed(), [])
        self.assertEqual(before, await self.snapshot())

    async def test_real_committed_link_recovers_after_lost_response_and_restart(self):
        start = await self.act("start")
        await self.approve(start["pairing_id"])
        approved = await self.act("refresh")
        self.lose_confirmation = True
        result = await self.act(
            "confirm",
            **{
                k: approved[k] for k in ("pairing_id", "comparison_code", "review_hash")
            },
        )
        self.assertEqual(result["error"], "unavailable")
        self.controller.close()
        self.controller = self.new_controller()
        self.assertEqual((await self.act("refresh"))["status"], "linked")
        self.assertEqual(len(await self.listed()), 1)

    async def test_human_approval_requires_fresh_proof_not_node_or_app_keys(self):
        start = await self.act("start")
        path = f"/v1/account/validator-pairings/{start['pairing_id']}/approve"
        stale = self.user_tokens.issue(
            self.human,
            audience="direct",
            scopes=self.accounts.SESSION_SCOPES,
            auth_method="siwe",
            now=int(time.time()) - 601,
        )
        app_token = self.user_tokens.issue(
            self.human,
            audience="direct",
            scopes=self.accounts.SESSION_SCOPES,
            auth_method="app",
        )
        for token in (self.identity.api_key, self.ordinary_key, stale, app_token):
            response = await self.http.post(path, headers={"apikey": token})
            self.assertEqual(response.status_code, 403)
            self.assertEqual((await self.act("refresh"))["status"], "pending")
        await self.approve(start["pairing_id"])
        self.assertEqual((await self.act("refresh"))["status"], "approved")
        self.assertEqual(await self.listed(), [])

    async def test_revoked_node_key_fails_before_signed_confirmation(self):
        start = await self.act("start")
        await self.approve(start["pairing_id"])
        approved = await self.act("refresh")
        async with self.factory() as session:
            await session.execute(
                self.sa.update(self.db.api_keys)
                .where(
                    self.db.api_keys.c.hash
                    == self.auth.hash_api_key(self.identity.api_key),
                )
                .values(revoked=True)
            )
            await session.commit()
        with patch("validator.account_pairing.Account.sign_message") as signed:
            result = await self.act(
                "confirm",
                **{
                    key: approved[key]
                    for key in ("pairing_id", "comparison_code", "review_hash")
                },
            )
        self.assertEqual(result["error"], "credentials_rejected")
        signed.assert_not_called()
        self.assertEqual(await self.listed(), [])

    async def test_other_account_cannot_remove_link_and_owner_can(self):
        start = await self.act("start")
        await self.approve(start["pairing_id"])
        approved = await self.act("refresh")
        linked = await self.act(
            "confirm",
            **{
                key: approved[key]
                for key in ("pairing_id", "comparison_code", "review_hash")
            },
        )
        path = f"/v1/account/validators/{self.node}/unlink"
        response = await self.http.post(
            path,
            headers={"apikey": self.other_token},
            json={"pairing_id": linked["pairing_id"]},
        )
        self.assertEqual(response.status_code, 404)
        response = await self.http.post(
            path,
            headers={"apikey": self.human_token},
            json={"pairing_id": linked["pairing_id"]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual((await self.act("refresh"))["status"], "cancelled")
        self.assertEqual(await self.listed(), [])


if __name__ == "__main__":
    unittest.main()
