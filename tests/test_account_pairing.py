# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Local consent and real signature recovery against a synthetic Core contract."""

import json
import os
import secrets
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import httpx
from eth_account import Account
from eth_account.messages import encode_defunct

from validator.account_pairing import (
    CONSOLE_URL,
    GRID_URL,
    Identity,
    PairingClient,
    PairingController,
    PairingError,
    canonical,
    review_hash,
    valid_form,
    validated_payload,
)
from validator.launcher import operator_config


def response(data, status=200):
    return httpx.Response(
        status,
        headers={"Content-Type": "application/json"},
        stream=httpx.ByteStream(json.dumps(data).encode()),
    )


class FakeCore:
    """Only a fixture, not evidence that Core enforces these transitions."""

    def __init__(self):
        signer = Account.create()
        self.identity = Identity(
            signer.address.lower(),
            "grid_" + secrets.token_urlsafe(32),
            signer.key.hex(),
        )
        self.node_id = "val_" + uuid4().hex
        self.pair_id = "vpa_" + secrets.token_hex(32)
        self.node_account = str(uuid4())
        self.operator_account = str(uuid4())
        self.expiry = int(time.time()) + 590
        self.code = secrets.token_hex(4).upper()
        self.status = "none"
        self.linked = False
        self.calls = []
        self.signatures = []
        self.lose_confirm_response = False
        self.mutate = lambda path, data: data

    def payload(self, unlink=False):
        data = {
            "purpose": "aipg.validator.account-link.v1",
            "audience": GRID_URL,
            "pairing_id": self.pair_id,
            "validator_id": self.node_id,
            "node_account_id": self.node_account,
            "operator_account_id": self.operator_account,
            "signing_wallet": self.identity.wallet,
        }
        if unlink:
            issued = int(time.time())
            data.update(
                purpose="aipg.validator.account-unlink.v1",
                issued_at=issued,
                expires_at=issued + 600,
            )
        else:
            data.update(
                comparison_code=self.code,
                expires_at=self.expiry,
                permissions=["validator.account_visibility"],
            )
        return data

    def view(self):
        data = {
            "status": self.status,
            "validator_id": self.node_id,
            "pairing_id": self.pair_id,
            "signing_wallet": self.identity.wallet,
            "expires_at": self.expiry,
            "economic_effect": "none",
        }
        if self.status == "approved":
            data.update(comparison_code=self.code, payload=self.payload())
        return data

    def verify(self, payload, signature):
        recovered = Account.recover_message(
            encode_defunct(text=canonical(payload)), signature=signature
        ).lower()
        if recovered != self.identity.wallet:
            raise AssertionError("wrong signer")
        self.signatures.append(payload)

    def handle(self, request):
        assert (
            request.url.scheme == "https" and request.url.host == "api.aipowergrid.io"
        )
        assert request.headers["apikey"] == self.identity.api_key
        assert request.headers["Authorization"] == "Bearer " + self.identity.api_key
        assert request.headers["Accept-Encoding"] == "identity"
        assert request.extensions["timeout"]["read"] <= 10
        path = request.url.path
        self.calls.append((request.method, path))
        data = None
        if path == "/v1/validator/registration":
            data = {
                "validator_id": self.node_id,
                "signing_wallet": self.identity.wallet,
                "status": "active",
            }
        elif path == "/v1/validator/account-link":
            data = (
                {
                    "status": "linked",
                    "validator_id": self.node_id,
                    "operator_account_id": self.operator_account,
                    "unlink_payload": self.payload(True),
                    "economic_effect": "none",
                }
                if self.linked
                else {"status": "none"}
            )
        elif path == "/v1/validator/account-pairings":
            self.status = "pending"
            data = {**self.view(), "approval_url": CONSOLE_URL + "/" + self.pair_id}
        elif path == "/v1/validator/account-pairing":
            data = self.view() if self.status != "none" else {"status": "none"}
        elif path == f"/v1/validator/account-pairings/{self.pair_id}/cancel":
            if self.linked:
                return response({}, 409)
            self.status = "cancelled"
            data = {"status": self.status}
        elif path == f"/v1/validator/account-pairings/{self.pair_id}/confirm":
            if self.status != "approved":
                return response({}, 409)
            self.verify(self.payload(), json.loads(request.content)["signature"])
            self.linked, self.status = True, "linked"
            if self.lose_confirm_response:
                raise httpx.ReadError("synthetic response loss after commit")
            data = self.view()
        elif path == "/v1/validator/account-link/unlink":
            body = json.loads(request.content)
            assert body["pairing_id"] == self.pair_id
            payload = self.payload(True)
            payload.update(
                issued_at=body["issued_at"], expires_at=body["issued_at"] + 600
            )
            self.verify(payload, body["signature"])
            self.linked, self.status = False, "cancelled"
            data = {"status": "unlinked", "validator_id": self.node_id}
        else:
            raise AssertionError("unexpected endpoint")
        return response(self.mutate(path, data))


class PairingTests(unittest.TestCase):
    def setUp(self):
        self.core = FakeCore()
        self.controller = PairingController(
            lambda: self.core.identity, httpx.MockTransport(self.core.handle)
        )

    def tearDown(self):
        self.controller.close()

    def act(self, action, **values):
        code, data = self.controller.perform({"action": action, **values})
        self.assertEqual(code, 200)
        return data

    def approved(self):
        self.act("start")
        self.core.status = "approved"
        return self.act("refresh")

    @staticmethod
    def consent(view, action="confirm"):
        fields = ["pairing_id", "review_hash"]
        if action == "confirm":
            fields.append("comparison_code")
        return {key: view[key] for key in fields}

    def test_no_implicit_network_identity_or_signature(self):
        self.assertEqual(self.controller.snapshot(), {"status": "idle", "busy": False})
        self.assertEqual(self.core.calls, [])
        view = self.approved()
        self.assertEqual(view["status"], "approved")
        self.assertFalse(self.core.linked)
        self.assertEqual(self.core.signatures, [])
        self.act("cancel", pairing_id=view["pairing_id"])
        self.assertEqual(self.core.signatures, [])

    def test_real_signatures_link_and_remove_exact_association(self):
        approved = self.approved()
        linked = self.act("confirm", **self.consent(approved))
        self.assertEqual(linked["status"], "linked")
        self.assertEqual(self.core.signatures, [self.core.payload()])
        self.assertEqual(
            self.act("unlink", **self.consent(linked, "unlink"))["status"], "none"
        )
        self.assertEqual(len(self.core.signatures), 2)
        self.assertEqual(
            self.core.signatures[1]["purpose"], "aipg.validator.account-unlink.v1"
        )
        self.assertFalse(self.core.linked)

    def test_confirmation_requires_previous_local_review(self):
        self.core.status = "approved"
        values = {
            "pairing_id": self.core.pair_id,
            "comparison_code": self.core.code,
            "review_hash": review_hash(self.core.payload()),
        }
        self.assertEqual(self.act("confirm", **values)["error"], "changed")
        self.assertEqual(self.core.calls, [])
        self.assertEqual(self.core.signatures, [])

    def test_replaced_approval_cannot_reuse_review_even_with_same_code(self):
        approved = self.approved()
        self.core.operator_account = str(uuid4())
        self.assertEqual(
            self.act("confirm", **self.consent(approved))["error"], "changed"
        )
        self.assertEqual(self.core.signatures, [])

    def test_wrong_comparison_or_review_does_not_sign(self):
        for key, value in (
            ("comparison_code", "DEADBEEF"),
            ("review_hash", "0" * 64),
            ("pairing_id", "vpa_" + "0" * 64),
        ):
            approved = self.approved()
            consent = {**self.consent(approved), key: value}
            self.assertEqual(self.act("confirm", **consent)["error"], "changed")
        self.assertEqual(self.core.signatures, [])

    def test_expired_and_cancelled_approval_do_not_sign(self):
        for status in ("expired", "cancelled", "pending"):
            approved = self.approved()
            self.core.status = status
            self.assertEqual(
                self.act("confirm", **self.consent(approved))["error"], "changed"
            )
        approved = self.approved()
        self.core.expiry = int(time.time()) - 1
        self.assertEqual(
            self.act("confirm", **self.consent(approved))["error"], "changed"
        )
        self.assertEqual(self.core.signatures, [])

    def test_lost_commit_response_recovers_without_repeating_signature(self):
        approved = self.approved()
        self.core.lose_confirm_response = True
        self.assertEqual(
            self.act("confirm", **self.consent(approved))["error"], "unavailable"
        )
        self.assertTrue(self.core.linked)
        self.core.expiry = int(time.time()) - 1000
        self.controller.close()
        self.controller = PairingController(
            lambda: self.core.identity, httpx.MockTransport(self.core.handle)
        )
        self.assertEqual(self.act("refresh")["status"], "linked")
        self.assertEqual(len(self.core.signatures), 1)

    def test_stale_linked_slot_is_not_a_current_association(self):
        self.core.status = "linked"
        self.assertEqual(self.act("refresh")["status"], "cancelled")

    def test_unlink_new_timestamp_allowed_but_new_association_rejected(self):
        self.core.linked = True
        linked = self.act("refresh")
        clock = int(time.time())
        with patch("validator.account_pairing.time.time", return_value=clock + 10):
            self.assertEqual(
                self.act("unlink", **self.consent(linked, "unlink"))["status"], "none"
            )
        self.core.linked = True
        linked = self.act("refresh")
        self.core.pair_id = "vpa_" + secrets.token_hex(32)
        self.assertEqual(
            self.act("unlink", **self.consent(linked, "unlink"))["error"], "changed"
        )
        self.assertEqual(len(self.core.signatures), 1)

    def test_malformed_envelopes_fail_closed_without_traceback(self):
        self.core.status = "approved"
        for endpoint, field in (
            ("registration", "status"),
            ("account-pairing", "status"),
            ("account-pairing", "expires_at"),
            ("account-pairing", "payload"),
        ):
            for value in ([], {}, True, None, "unexpected"):
                with self.subTest(endpoint=endpoint, field=field, value=value):
                    self.core.mutate = (
                        lambda path, data: {**data, field: value}
                        if path.endswith("/" + endpoint)
                        else data
                    )
                    self.assertEqual(self.act("refresh")["status"], "error")
        self.assertEqual(self.core.signatures, [])

    def test_every_link_payload_field_is_checked_before_review(self):
        original = self.core.payload()
        mutations = {
            "purpose": "aipg.validator.rotate.v1",
            "audience": "https://attacker.example",
            "pairing_id": "other",
            "validator_id": "val_" + "0" * 32,
            "node_account_id": "not-uuid",
            "operator_account_id": self.core.node_account,
            "signing_wallet": Account.create().address.lower(),
            "comparison_code": "short",
            "expires_at": True,
            "permissions": ["account.manage"],
            "extra": "ignored?",
        }
        for field, value in mutations.items():
            with self.subTest(field=field), self.assertRaises(PairingError):
                validated_payload(
                    {**original, field: value}, self.core.identity, self.core.node_id
                )
        for field in original:
            without = {k: v for k, v in original.items() if k != field}
            with self.subTest(missing=field), self.assertRaises(PairingError):
                validated_payload(without, self.core.identity, self.core.node_id)
        for expires in (int(time.time()) - 1, int(time.time()) + 1000):
            with self.assertRaises(PairingError):
                validated_payload(
                    {**original, "expires_at": expires},
                    self.core.identity,
                    self.core.node_id,
                )

    def test_unlink_payload_has_distinct_purpose_and_bounded_freshness(self):
        payload = self.core.payload(True)
        for changes in (
            {"issued_at": True},
            {"issued_at": int(time.time()) + 31},
            {"issued_at": 1},
            {"expires_at": payload["expires_at"] - 2},
            {"permissions": []},
        ):
            with self.assertRaises(PairingError):
                validated_payload(
                    {**payload, **changes},
                    self.core.identity,
                    self.core.node_id,
                    unlink=True,
                )
        with self.assertRaises(PairingError):
            validated_payload(
                self.core.payload(), self.core.identity, self.core.node_id, unlink=True
            )

    def test_small_clock_skew_does_not_break_fresh_core_payload(self):
        payload = self.core.payload(True)
        clock = int(time.time())
        with patch("validator.account_pairing.time.time", return_value=clock - 10):
            self.assertEqual(
                validated_payload(
                    payload, self.core.identity, self.core.node_id, unlink=True
                ),
                payload,
            )
        with patch("validator.account_pairing.time.time", return_value=clock - 31):
            with self.assertRaises(PairingError):
                validated_payload(
                    payload, self.core.identity, self.core.node_id, unlink=True
                )

    def test_identity_is_reloaded_and_existing_config_untouched(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.dict(os.environ, {}, clear=True),
        ):
            path = Path(tmp) / "node.env"
            self.controller.identity_loader = lambda: Identity.from_values(
                operator_config(path)
            )
            self.assertEqual(self.act("refresh")["error"], "configuration_invalid")
            original = (
                f"GRID_API_URL={GRID_URL}\nVALIDATOR_API_KEY={self.core.identity.api_key}\n"
                f"VALIDATOR_PRIVATE_KEY={self.core.identity.private_key}\nVALIDATOR_WALLET={self.core.identity.wallet}\n"
            ).encode()
            path.write_bytes(original)
            self.assertEqual(self.act("refresh")["status"], "none")
            self.assertEqual(path.read_bytes(), original)
            with patch.dict(os.environ, {"VALIDATOR_API_KEY": ""}):
                self.assertEqual(self.act("refresh")["error"], "configuration_invalid")
            self.assertEqual(path.read_bytes(), original)

    def test_local_config_validation_never_returns_secrets(self):
        identity = self.core.identity
        values = {
            "VALIDATOR_API_KEY": identity.api_key,
            "VALIDATOR_PRIVATE_KEY": identity.private_key,
            "VALIDATOR_WALLET": identity.wallet,
            "GRID_API_URL": GRID_URL,
        }
        self.assertEqual(Identity.from_values(values), identity)
        for field, value in (
            ("GRID_API_URL", "https://other.example"),
            ("VALIDATOR_API_KEY", "bad"),
            ("VALIDATOR_PRIVATE_KEY", "0" * 64),
            ("VALIDATOR_WALLET", Account.create().address),
        ):
            with self.assertRaises(PairingError):
                Identity.from_values({**values, field: value})
        view = self.approved()
        for data in (
            repr(identity),
            json.dumps(view),
            json.dumps(self.controller.snapshot()),
        ):
            for secret in (
                identity.api_key,
                identity.private_key,
                self.core.node_account,
                self.core.operator_account,
            ):
                self.assertNotIn(secret, data)

    def test_arbitrary_fields_and_actions_never_reach_core(self):
        for form in (
            None,
            [],
            {},
            {"action": []},
            {"action": "sign", "payload": {}},
            {"action": "start", "private_key": "x"},
            {"action": "unlink"},
            {"action": "cancel", "pairing_id": "../../other"},
        ):
            self.assertFalse(valid_form(form))
            self.assertEqual(self.controller.perform(form)[0], 400)
        self.assertEqual(self.core.calls, [])

    def test_serialized_actions_cached_reads_and_close_before_sign(self):
        entered, release = threading.Event(), threading.Event()
        approved = self.approved()

        def handle(request):
            if request.url.path.endswith("/registration"):
                entered.set()
                self.assertTrue(release.wait(3))
            return self.core.handle(request)

        self.controller.transport = httpx.MockTransport(handle)
        results = []
        thread = threading.Thread(
            target=lambda: results.append(
                self.controller.perform({"action": "confirm", **self.consent(approved)})
            )
        )
        thread.start()
        try:
            self.assertTrue(entered.wait(3))
            self.assertTrue(self.controller.snapshot()["busy"])
            self.assertEqual(self.controller.perform({"action": "refresh"})[0], 409)
            self.controller.close()
        finally:
            release.set()
            thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(self.core.signatures, [])
        self.assertEqual(results[0][1]["status"], "error")
        self.assertFalse(self.controller.snapshot()["busy"])


class PairingTransportTests(unittest.TestCase):
    def check(self, handler):
        identity = FakeCore().identity
        client = PairingClient(
            identity, threading.Event(), httpx.MockTransport(handler)
        )
        self.addCleanup(client.http.close)
        return client

    def test_http_errors_are_sanitized_and_redirects_never_followed(self):
        for code, expected in (
            (401, "credentials_rejected"),
            (403, "registration_required"),
            (404, "not_found"),
            (409, "changed"),
            (429, "rate_limited"),
            (503, "unavailable"),
            (302, "unavailable"),
        ):
            calls = []

            def handle(request):
                calls.append(request.url.host)
                return httpx.Response(
                    code,
                    headers={"Location": "https://attacker.example"},
                    text="private remote error",
                )

            client = self.check(handle)
            with self.assertRaises(PairingError) as result:
                client.request("GET", "/v1/validator/registration")
            self.assertEqual(str(result.exception), expected)
            self.assertEqual(calls, ["api.aipowergrid.io"])

    def test_bounded_json_mime_encoding_duplicates_and_depth(self):
        cases = [
            (b"{}", {"Content-Type": "text/html"}),
            (b"{}", {"Content-Type": "application/json", "Content-Encoding": "gzip"}),
            (
                b'{"status":"none","status":"linked"}',
                {"Content-Type": "application/json"},
            ),
            (b"[]", {"Content-Type": "application/json"}),
            (b"[" * 2000 + b"]" * 2000, {"Content-Type": "application/json"}),
            (b'{"data":"' + b"x" * 17000 + b'"}', {"Content-Type": "application/json"}),
            (b"\xff", {"Content-Type": "application/json"}),
        ]
        for body, headers in cases:
            client = self.check(
                lambda request: httpx.Response(
                    200, headers=headers, stream=httpx.ByteStream(body)
                )
            )
            with self.assertRaises(PairingError):
                client.request("GET", "/v1/validator/registration")

    def test_deadline_and_network_timeout_are_safe(self):
        def fail(request):
            raise httpx.ReadTimeout("private network error")

        client = self.check(fail)
        with self.assertRaisesRegex(PairingError, "unavailable"):
            client.request("GET", "/v1/validator/registration")
        client.deadline = time.monotonic() - 1
        with self.assertRaisesRegex(PairingError, "unavailable"):
            client.request("GET", "/v1/validator/registration")

    def test_proxy_environment_is_not_used(self):
        with (
            patch.dict(
                os.environ,
                {
                    "HTTPS_PROXY": "http://127.0.0.1:1",
                    "ALL_PROXY": "http://127.0.0.1:1",
                },
            ),
            patch(
                "validator.account_pairing.httpx.Client", wraps=httpx.Client
            ) as constructor,
        ):
            client = self.check(lambda request: response({"status": "none"}))
            self.assertEqual(
                client.request("GET", "/v1/validator/account-link"), {"status": "none"}
            )
            self.assertFalse(constructor.call_args.kwargs["trust_env"])
            self.assertFalse(constructor.call_args.kwargs["follow_redirects"])


if __name__ == "__main__":
    unittest.main()
