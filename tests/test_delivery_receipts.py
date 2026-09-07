# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Real HTTPX parsing and durable local delivery; Core transport is simulated."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from validator import main
from validator.config import Settings
from validator.grid_client import GridClient
from validator.outbox import AttestationOutbox


def envelope():
    # This fixture tests delivery binding, not cryptographic signature validity.
    return {
        "payload": {
            "assignment_source": "grid",
            "assignment_id": "asg_delivery_fixture",
            "probe_group_id": "prg_delivery_fixture",
            "grid_nonce": "synthetic-nonce",
            "verdict": "healthy",
        },
        "signature": "0x" + "ab" * 65,
    }


def receipt(body, status="accepted"):
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {
        "status": status,
        "id": 12,
        "attestation_hash": hashlib.sha256(canonical.encode()).hexdigest(),
        "authority": "authoritative",
        "signature_status": "verified",
        "assignment_id": body["payload"]["assignment_id"],
        "probe_group_id": body["payload"]["probe_group_id"],
        "quorum_status": "pending",
        "economic_effect": "none",
    }


def client_for(handler):
    client = GridClient.__new__(GridClient)
    client._http = httpx.AsyncClient(
        base_url="https://grid.invalid",
        transport=httpx.MockTransport(handler),
        trust_env=False,
    )
    return client


class DeliveryReceiptTests(unittest.IsolatedAsyncioTestCase):
    async def test_unsigned_preview_and_normalized_signature_receipts(self):
        unsigned = {"payload": {"verdict": "healthy"}, "signature": None}
        ack = {
            **receipt(envelope()),
            "attestation_hash": hashlib.sha256(
                json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "authority": "preview",
            "signature_status": "unsigned",
            "assignment_id": None,
            "probe_group_id": None,
        }
        normalized = envelope()
        unprefixed = {**normalized, "signature": normalized["signature"][2:]}
        for body, response in ((unsigned, ack), (unprefixed, receipt(normalized))):
            client = client_for(
                lambda _, response=response: httpx.Response(200, json=response)
            )
            try:
                self.assertTrue(await client.submit_attestation(body))
            finally:
                await client.aclose()

    async def test_bound_accepted_and_duplicate_receipts_deliver(self):
        for status in ("accepted", "duplicate"):
            with self.subTest(status=status):
                body = envelope()
                response = receipt(body, status)
                client = client_for(
                    lambda _, response=response: httpx.Response(200, json=response)
                )
                try:
                    self.assertTrue(await client.submit_attestation(body))
                finally:
                    await client.aclose()

    async def test_ambiguous_or_unbound_success_does_not_deliver(self):
        body = envelope()
        valid = receipt(body)
        mutations = [
            {},
            [],
            None,
            {**valid, "status": "error"},
            {**valid, "status": "pending"},
            {**valid, "id": None},
            {**valid, "id": True},
            {**valid, "id": 0},
            {**valid, "id": "12"},
            {**valid, "attestation_hash": "0" * 64},
            {**valid, "assignment_id": "asg_other"},
            {**valid, "probe_group_id": "prg_other"},
            {**valid, "authority": "preview"},
            {**valid, "signature_status": "unverified"},
        ]
        for index, value in enumerate(mutations):
            with self.subTest(case=index):
                client = client_for(
                    lambda _, value=value: httpx.Response(
                        200, content=json.dumps(value)
                    )
                )
                try:
                    self.assertFalse(await client.submit_attestation(body))
                finally:
                    await client.aclose()

    async def test_non_json_duplicate_keys_and_uncommitted_status_do_not_deliver(self):
        body = envelope()
        raw = json.dumps(receipt(body))
        responses = [
            (200, "<html>Sign in</html>"),
            (200, "{"),
            (200, '{"status":"error",' + raw[1:]),
            (202, raw),
            (204, ""),
            (503, "temporarily unavailable"),
        ]
        for code, content in responses:
            with self.subTest(code=code, content_type=content[:1]):
                client = client_for(
                    lambda _, code=code, content=content: httpx.Response(
                        code, content=content
                    )
                )
                try:
                    self.assertFalse(await client.submit_attestation(body))
                finally:
                    await client.aclose()

    async def test_wrong_receipt_survives_restart_then_exact_duplicate_clears(self):
        body = envelope()
        attempts = []

        def handler(request):
            attempts.append(json.loads(request.content))
            result = receipt(body, "duplicate")
            if len(attempts) == 1:
                result["attestation_hash"] = "0" * 64
            return httpx.Response(200, json=result)

        client = client_for(handler)
        try:
            with tempfile.TemporaryDirectory() as directory:
                path = str(Path(directory) / "outbox.sqlite")
                outbox = AttestationOutbox(path)
                item_id = outbox.enqueue(body)
                self.assertEqual(await main._flush_outbox(client, outbox), 0)
                self.assertEqual(outbox.get_pending(item_id)["envelope"], body)
                reopened = AttestationOutbox(path)
                self.assertEqual(await main._flush_outbox(client, reopened), 1)
                self.assertEqual(reopened.counts(), {"pending": 0, "dead": 0})
                self.assertEqual(attempts, [body, body])
        finally:
            await client.aclose()

    async def test_response_loss_retries_identical_envelope(self):
        body = envelope()
        attempts = []

        def handler(request):
            attempts.append(json.loads(request.content))
            if len(attempts) == 1:
                raise httpx.ReadTimeout("synthetic response loss", request=request)
            return httpx.Response(200, json=receipt(body, "duplicate"))

        client = client_for(handler)
        try:
            with tempfile.TemporaryDirectory() as directory:
                outbox = AttestationOutbox(str(Path(directory) / "outbox.sqlite"))
                outbox.enqueue(body)
                self.assertEqual(await main._flush_outbox(client, outbox), 0)
                self.assertEqual(await main._flush_outbox(client, outbox), 1)
                self.assertEqual(attempts, [body, body])
        finally:
            await client.aclose()

    async def test_probe_requires_completed_status_and_requested_assignment(self):
        valid = {"status": "completed", "assignment_id": "asg_fixture"}
        for changed in (
            {**valid, "status": "pending"},
            {**valid, "status": "unavailable"},
            {**valid, "assignment_id": "asg_other"},
            {},
            [],
            None,
        ):
            client = client_for(
                lambda _, changed=changed: httpx.Response(
                    200, content=json.dumps(changed)
                )
            )
            try:
                self.assertIsNone(await client.probe_assignment("asg_fixture"))
            finally:
                await client.aclose()

    async def test_unavailable_probe_retries_then_dead_letters_without_signing(self):
        assignment = {
            "assignment_id": "asg_unavailable",
            "modality": "text",
            "capability": "text.fidelity.v1",
        }
        probes = []

        def handler(request):
            if request.url.path == "/v1/validator/assignments":
                return httpx.Response(
                    200,
                    json={
                        "assignments": [assignment]
                        if request.url.params.get("modality") == "text-fidelity"
                        else [],
                    },
                )
            if request.url.path == "/v1/validator/probe/asg_unavailable":
                probes.append(request.url.path)
                return httpx.Response(
                    422,
                    json={
                        "status": "error",
                        "probe_status": "failed",
                        "message": "text fidelity probe was inconclusive",
                        "economic_effect": "none",
                    },
                )
            raise AssertionError("unavailable work must not submit an attestation")

        client = client_for(handler)
        try:
            with (
                tempfile.TemporaryDirectory() as directory,
                patch.object(Settings, "ASSIGNMENT_MAX_ATTEMPTS", 2),
                patch.object(
                    main.attest,
                    "runtime_capabilities",
                    return_value=["text.fidelity.v1"],
                ),
                patch.object(
                    main.attest, "sign", side_effect=AssertionError("must not sign")
                ),
            ):
                path = str(Path(directory) / "outbox.sqlite")
                outbox = AttestationOutbox(path)
                self.assertEqual(await main.probe_round(client, 0, outbox), 0)
                self.assertEqual(outbox.assignment_counts(), {"pending": 1, "dead": 0})
                reopened = AttestationOutbox(path)
                self.assertEqual(await main.probe_round(client, 1, reopened), 0)
                self.assertEqual(
                    reopened.assignment_counts(), {"pending": 0, "dead": 1}
                )
                self.assertEqual(await main.probe_round(client, 2, reopened), 0)
                self.assertEqual(len(probes), 2)
                self.assertEqual(reopened.counts(), {"pending": 0, "dead": 0})
        finally:
            await client.aclose()


if __name__ == "__main__":
    unittest.main()
