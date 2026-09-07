# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Bounded synthetic Core transport; actual local payout signature recovery."""

import copy
import hashlib
import json
import secrets
import time
import unittest
from datetime import datetime, timezone
from unittest import mock
from uuid import uuid4

import httpx
from eth_account import Account
from eth_account.messages import encode_defunct

from tests.test_account_pairing import response
from validator import compensation as comp
from validator.account_pairing import Identity, PairingError


class FakeCompensation:
    def __init__(self):
        signer = Account.create()
        self.identity = Identity(
            signer.address.lower(),
            "grid_" + secrets.token_urlsafe(32),
            signer.key.hex(),
        )
        self.node_id = "val_" + uuid4().hex
        self.allocation = secrets.token_hex(32)
        self.request_id = "vpc_" + secrets.token_hex(32)
        self.recipient = Account.create().address.lower()
        self.status = "wallet_required"
        self.calls, self.signatures = [], []
        self.loss = False
        self.mutate = lambda path, data: data
        self.proof = {
            "schema": comp.CONSENT_SCHEMA,
            "audience": comp.GRID_URL,
            "campaign_id": "pilot-test",
            "contract_hash": secrets.token_hex(32),
            "allocation_hash": self.allocation,
            "operator_group_id": "opg_" + secrets.token_hex(12),
            "account_id": str(uuid4()),
            "validator_id": self.node_id,
            "signing_wallet": self.identity.wallet,
            "chain_id": 8453,
            "token_address": comp.TOKEN,
            "asset": "AIPG",
            "decimals": 18,
            "amount_atomic": "100000000000000000001",
            "recipient": self.recipient,
            "issued_at": datetime.fromtimestamp(
                time.time() - 1, timezone.utc
            ).isoformat(),
            "expires_at": datetime.fromtimestamp(
                time.time() + 3600, timezone.utc
            ).isoformat(),
        }

    def listing(self):
        return {
            "schema": comp.SCHEMA,
            "validator_id": self.node_id,
            "campaigns": [],
            "campaigns_has_more": False,
            "next_offset": None,
            "items": [
                {
                    "campaign_id": "pilot-test",
                    "allocation_hash": self.allocation,
                    "amount_atomic": self.proof["amount_atomic"],
                    "asset": "AIPG",
                    "decimals": 18,
                    "chain_id": 8453,
                    "reviewed_units": 14,
                    "status": self.status,
                    "recipient": None,
                    "request_id": None
                    if self.status == "wallet_required"
                    else self.request_id,
                    "transaction_hash": None,
                }
            ],
        }

    def view(self):
        raw = {
            "schema": comp.SCHEMA,
            "request_id": self.request_id,
            "allocation_hash": self.allocation,
            "status": self.status,
            "expires_at": self.proof["expires_at"],
            "approval_url": comp.CONSOLE + self.request_id,
            "payment_authorized": False,
        }
        if self.status in {"awaiting_node", "review_required"}:
            message, digest = comp.consent_message(
                self.proof, self.identity, self.node_id
            )
            raw.update(
                consent=copy.deepcopy(self.proof), message=message, review_hash=digest
            )
        return raw

    def handle(self, request):
        self.calls.append((request.method, request.url.path))
        assert (
            request.url.host == "api.aipowergrid.io" and request.url.scheme == "https"
        )
        assert request.headers["apikey"] == self.identity.api_key
        assert request.headers["Authorization"] == "Bearer " + self.identity.api_key
        path = request.url.path
        if path == "/v1/validator/registration":
            data = {
                "validator_id": self.node_id,
                "signing_wallet": self.identity.wallet,
                "status": "active",
            }
        elif path == "/v1/validator/compensation":
            data = self.listing()
        elif path.endswith("/requests"):
            self.status = (
                "awaiting_wallet" if self.status == "wallet_required" else self.status
            )
            data = self.view()
        elif path.endswith("/confirm"):
            form = json.loads(request.content)
            message, digest = comp.consent_message(
                self.proof, self.identity, self.node_id
            )
            assert form["review_hash"] == digest
            assert (
                Account.recover_message(
                    encode_defunct(text=message), signature=form["signature"]
                ).lower()
                == self.identity.wallet
            )
            self.signatures.append(form["signature"])
            self.status = "review_required"
            if self.loss:
                raise httpx.ReadTimeout("private fixture response loss")
            data = self.view()
        elif path.endswith("/cancel"):
            self.status = "cancelled"
            data = self.view()
        elif path.endswith(self.request_id):
            data = self.view()
        else:
            raise AssertionError("unexpected endpoint")
        return response(self.mutate(path, data))

    def controller(self):
        return comp.CompensationController(
            lambda: self.identity, httpx.MockTransport(self.handle)
        )


class CompensationTests(unittest.TestCase):
    def setUp(self):
        self.core = FakeCompensation()
        self.controller = self.core.controller()

    def perform(self, action, **kwargs):
        status, value = self.controller.perform({"action": action, **kwargs})
        self.assertEqual(status, 200)
        return value

    def ready(self):
        self.perform("refresh", offset=0)
        self.perform("start", allocation_hash=self.core.allocation)
        self.core.status = "awaiting_node"
        return self.perform("inspect", request_id=self.core.request_id)["request"]

    def test_startup_cached_reads_and_all_nonconfirm_actions_never_sign(self):
        self.controller.snapshot()
        self.assertEqual(self.core.calls, [])
        self.perform("refresh", offset=0)
        self.perform("start", allocation_hash=self.core.allocation)
        self.perform("inspect", request_id=self.core.request_id)
        self.perform("cancel", request_id=self.core.request_id)
        self.assertEqual(self.core.signatures, [])

    def test_unreadable_configuration_clears_stale_payment_display(self):
        self.ready()
        with mock.patch.object(self.controller, "identity_loader", side_effect=OSError):
            result = self.perform("refresh", offset=0)
        self.assertEqual(result["error"], "configuration_invalid")
        self.assertEqual(result["items"], [])
        self.assertEqual(result["campaigns"], [])
        self.assertIsNone(result["request"])
        self.assertEqual(self.core.signatures, [])

    def test_explicit_review_signs_exact_message_and_does_not_expose_proofs(self):
        view = self.ready()
        result = self.perform(
            "confirm", request_id=view["request_id"], review_hash=view["review_hash"]
        )
        self.assertEqual(result["request"]["status"], "review_required")
        self.assertEqual(len(self.core.signatures), 1)
        serialized = json.dumps(self.controller.snapshot())
        for secret in (
            self.core.identity.api_key,
            self.core.identity.private_key,
            self.core.signatures[0],
            self.core.proof["account_id"],
            self.core.proof["operator_group_id"],
        ):
            self.assertNotIn(secret, serialized)
        self.assertEqual(result["items"][0]["status"], "review_required")
        self.assertEqual(
            comp.format_amount(self.core.proof["amount_atomic"]),
            "100.000000000000000001",
        )

    def test_changed_recipient_requires_a_new_displayed_review(self):
        view = self.ready()
        self.core.proof["recipient"] = Account.create().address.lower()
        result = self.perform(
            "confirm", request_id=view["request_id"], review_hash=view["review_hash"]
        )
        self.assertEqual(result["error"], "changed")
        self.assertEqual(self.core.signatures, [])

    def test_restart_cannot_sign_without_review_and_lost_ack_recovers_without_resigning(
        self,
    ):
        view = self.ready()
        self.controller = self.core.controller()
        result = self.perform(
            "confirm", request_id=view["request_id"], review_hash=view["review_hash"]
        )
        self.assertEqual(result["error"], "changed")
        self.perform("inspect", request_id=view["request_id"])
        self.core.loss = True
        self.assertEqual(
            self.perform(
                "confirm",
                request_id=view["request_id"],
                review_hash=view["review_hash"],
            )["error"],
            "unavailable",
        )
        self.controller = self.core.controller()
        self.perform("refresh", offset=0)
        self.assertEqual(
            self.perform("inspect", request_id=view["request_id"])["request"]["status"],
            "review_required",
        )
        self.assertEqual(len(self.core.signatures), 1)

    def test_domain_identity_asset_and_time_substitution_are_rejected(self):
        for field, value in {
            "audience": "https://evil.example",
            "chain_id": 1,
            "token_address": Account.create().address.lower(),
            "decimals": True,
            "asset": "ETH",
            "validator_id": "val_" + uuid4().hex,
            "signing_wallet": Account.create().address.lower(),
            "amount_atomic": "1.2",
            "recipient": self.core.identity.wallet,
            "account_id": "unknown",
            "operator_group_id": [],
            "issued_at": "2035-01-01T00:00:00+00:00",
            "expires_at": "2000-01-01T00:00:00+00:00",
        }.items():
            with self.subTest(field=field), self.assertRaises(PairingError):
                comp.consent_message(
                    {**self.core.proof, field: value},
                    self.core.identity,
                    self.core.node_id,
                )

    def test_server_signing_text_is_not_trusted(self):
        self.ready()
        self.core.mutate = lambda path, data: (
            {**data, "message": "Sign in to another site"}
            if path.endswith(self.core.request_id)
            else data
        )
        self.assertEqual(
            self.perform("inspect", request_id=self.core.request_id)["error"],
            "invalid_contract",
        )
        self.assertEqual(self.core.signatures, [])

    def test_message_contract_independent_encoding(self):
        message, digest = comp.consent_message(
            self.core.proof, self.core.identity, self.core.node_id
        )
        self.assertTrue(
            message.startswith(
                "AI Power Grid validator compensation payout consent\nReward: 100.000000000000000001 AIPG on Base (chain 8453)\n"
            )
        )
        self.assertEqual(
            message.split("\n\n", 1)[1],
            json.dumps(self.core.proof, sort_keys=True, indent=2),
        )
        self.assertEqual(
            digest,
            hashlib.sha256(
                json.dumps(
                    self.core.proof, sort_keys=True, separators=(",", ":")
                ).encode()
            ).hexdigest(),
        )

    def test_input_shapes_and_unbounded_pages_rejected(self):
        for form in (
            {"action": "sign", "message": "arbitrary"},
            {"action": "refresh", "offset": True},
            {"action": "refresh", "offset": 10025},
            {"action": "start", "allocation_hash": "../path"},
            {"action": "confirm", "request_id": self.core.request_id},
        ):
            self.assertEqual(self.controller.perform(form)[0], 400)
        self.assertEqual(self.core.calls, [])
        self.core.mutate = lambda path, data: (
            {**data, "items": data["items"] * 26}
            if path.endswith("/compensation")
            else data
        )
        self.assertEqual(self.perform("refresh", offset=0)["error"], "invalid_contract")

    def test_close_and_concurrent_actions_cannot_sign(self):
        self.controller.action_lock.acquire()
        self.assertEqual(
            self.controller.perform({"action": "refresh", "offset": 0})[0], 409
        )
        self.controller.action_lock.release()
        self.controller.close()
        self.assertEqual(
            self.controller.perform({"action": "refresh", "offset": 0})[0], 409
        )
        self.assertEqual(self.core.calls, [])

    def test_transport_is_bounded_and_remote_errors_are_not_returned(self):
        for result in (
            httpx.Response(503, content=b"sensitive server detail"),
            httpx.Response(302, headers={"location": "https://evil.example"}),
            httpx.Response(
                200,
                headers={"content-type": "application/json"},
                stream=httpx.ByteStream(b"x" * 65537),
            ),
            httpx.Response(
                200,
                headers={"content-type": "application/json"},
                stream=httpx.ByteStream(b'{"a":1,"a":2}'),
            ),
        ):
            controller = comp.CompensationController(
                lambda: self.core.identity,
                httpx.MockTransport(lambda request, result=result: result),
            )
            _, view = controller.perform({"action": "refresh", "offset": 0})
            self.assertEqual(view["status"], "error")
            self.assertNotIn("sensitive server detail", json.dumps(view))
