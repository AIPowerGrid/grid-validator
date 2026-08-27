# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Optional actual-Core service integration; only an in-memory SQLite database.

Use a Core dependency environment and set VALIDATOR_CORE_SOURCE to its reviewed
checkout. This does not replace fresh-account HTTP auth or native live proof.
"""

import asyncio
import json
import os
import secrets
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import httpx
from eth_account import Account

from validator.account_pairing import CONSOLE_URL, GRID_URL, Identity, PairingController

CORE_SOURCE = os.environ.get("VALIDATOR_CORE_SOURCE")


@unittest.skipUnless(
    CORE_SOURCE, "set VALIDATOR_CORE_SOURCE and use a Core dependency environment"
)
class ActualCorePairingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        sys.path.insert(0, str(Path(CORE_SOURCE).resolve()))
        import sqlalchemy as sa
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        from sqlalchemy.pool import StaticPool
        from grid_api.services import validator_pairing
        from grid_api.v2 import schema

        self.sa, self.core, self.db = sa, validator_pairing, schema
        self.engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)

        @sa.event.listens_for(self.engine.sync_engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        async with self.engine.begin() as conn:
            await conn.run_sync(schema.metadata.create_all)
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)

        async def new_session():
            return self.factory()

        self.patches = [
            patch.object(self.core, "new_session", new_session),
            patch.object(
                self.core,
                "get_settings",
                lambda: SimpleNamespace(
                    validator_pairing_audience=GRID_URL,
                    validator_pairing_console_url=CONSOLE_URL,
                ),
            ),
        ]
        for mocked in self.patches:
            mocked.start()
        signer = Account.create()
        self.identity = Identity(
            signer.address.lower(),
            "grid_" + secrets.token_urlsafe(32),
            signer.key.hex(),
        )
        self.account, self.human, self.other = uuid4(), uuid4(), uuid4()
        self.node = "val_" + uuid4().hex
        async with self.factory() as session:
            for aid in (self.account, self.human, self.other):
                await session.execute(
                    sa.insert(schema.accounts).values(
                        id=aid,
                        wallet=self.identity.wallet if aid == self.account else None,
                        payout_wallet=None,
                        flags={},
                    )
                )
                await session.execute(
                    sa.insert(schema.credits).values(
                        account_id=aid, balance_micro=12345
                    )
                )
            await session.execute(
                sa.insert(schema.validators).values(
                    id=self.node,
                    account_id=self.account,
                    signing_wallet=self.identity.wallet,
                    status="active",
                    registration_signature="synthetic-fixture",
                    software_version="integration-test",
                    capabilities=["text.basic.v1"],
                )
            )
            await session.commit()
        self.loop = asyncio.get_running_loop()
        self.lose_confirmation = False
        self.controller = self.new_controller()

    def new_controller(self):
        def transport(request):
            result = asyncio.run_coroutine_threadsafe(
                self.dispatch(request), self.loop
            ).result(timeout=5)
            if self.lose_confirmation and request.url.path.endswith("/confirm"):
                raise httpx.ReadError("synthetic response lost after real Core commit")
            return httpx.Response(
                200,
                headers={"Content-Type": "application/json"},
                stream=httpx.ByteStream(json.dumps(result).encode()),
            )

        return PairingController(lambda: self.identity, httpx.MockTransport(transport))

    async def dispatch(self, request):
        self.assertEqual(request.url.host, "api.aipowergrid.io")
        self.assertEqual(request.headers["apikey"], self.identity.api_key)
        path = request.url.path
        params = {"account_id": self.account, "wallet": self.identity.wallet}
        if path == "/v1/validator/registration":
            return {
                "validator_id": self.node,
                "signing_wallet": self.identity.wallet,
                "status": "active",
            }
        if path == "/v1/validator/account-link":
            return await self.core.node_link(**params)
        if path == "/v1/validator/account-pairing":
            return await self.core.poll(**params)
        if path == "/v1/validator/account-pairings":
            return await self.core.create(**params)
        if path.endswith("/confirm"):
            return await self.core.confirm(
                **params,
                pairing_id=path.split("/")[-2],
                signature=json.loads(request.content)["signature"],
            )
        if path.endswith("/cancel"):
            return await self.core.cancel(**params, pairing_id=path.split("/")[-2])
        if path == "/v1/validator/account-link/unlink":
            return await self.core.unlink_from_node(
                **params, **json.loads(request.content)
            )
        self.fail("Unexpected Core path")

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
                    dict(row)
                    for row in (await session.execute(self.sa.select(t))).mappings()
                ]
                for t in tables
            }

    async def asyncTearDown(self):
        self.controller.close()
        for mocked in reversed(self.patches):
            mocked.stop()
        await self.engine.dispose()
        sys.path.pop(0)

    async def test_actual_core_link_list_remove_preserves_non_pairing_state(self):
        before = await self.snapshot()
        start = await self.act("start")
        self.assertEqual(start["status"], "pending")
        await self.core.approve(
            pairing_id=start["pairing_id"], operator_account_id=self.human
        )
        approved = await self.act("refresh")
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(
            (await self.core.list_for_account(operator_account_id=self.human))["nodes"],
            [],
        )
        linked = await self.act(
            "confirm",
            **{
                k: approved[k] for k in ("pairing_id", "comparison_code", "review_hash")
            },
        )
        self.assertEqual(linked["status"], "linked")
        nodes = (await self.core.list_for_account(operator_account_id=self.human))[
            "nodes"
        ]
        self.assertEqual([node["validator_id"] for node in nodes], [self.node])
        self.assertEqual(
            (await self.core.list_for_account(operator_account_id=self.other))["nodes"],
            [],
        )
        self.assertEqual(before, await self.snapshot())
        self.assertEqual(
            (
                await self.act(
                    "unlink", **{k: linked[k] for k in ("pairing_id", "review_hash")}
                )
            )["status"],
            "none",
        )
        self.assertEqual(
            (await self.core.list_for_account(operator_account_id=self.human))["nodes"],
            [],
        )
        self.assertEqual(before, await self.snapshot())

    async def test_real_committed_link_recovers_after_lost_response_and_restart(self):
        start = await self.act("start")
        await self.core.approve(
            pairing_id=start["pairing_id"], operator_account_id=self.human
        )
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
        self.assertEqual(
            len(
                (await self.core.list_for_account(operator_account_id=self.human))[
                    "nodes"
                ]
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main()
