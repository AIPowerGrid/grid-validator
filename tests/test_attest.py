import unittest
from unittest.mock import patch

from eth_account import Account
from eth_account.messages import encode_defunct

from validator import attest
from validator.config import Settings


class AttestationTests(unittest.TestCase):
    def test_registration_advertises_only_implemented_text_scorers(self):
        with patch.object(Settings, "VALIDATOR_WALLET", "0x" + "12" * 20):
            payload = attest.build_registration(123456)

        self.assertEqual(
            payload["capabilities"],
            [
                "text.instruction.v1",
                "text.reasoning.v1",
                "text.structured.v1",
                "text.context.4k.v1",
                "text.reasoning.multistep.v1",
                "text.tool_call.v1",
                "text.stop_sequence.v1",
            ],
        )

    def test_canonical_is_stable_for_key_order(self):
        left = {"b": 2, "a": {"z": 1, "m": 3}}
        right = {"a": {"m": 3, "z": 1}, "b": 2}

        self.assertEqual(attest._canonical(left), attest._canonical(right))

    def test_build_text_payload_has_scorecard_fields_without_prompt(self):
        with patch.object(Settings, "VALIDATOR_WALLET", "0x" + "12" * 20):
            payload = attest.build(
                worker_id="",
                model="qwen3-27b",
                canary={
                    "kind": "echo",
                    "nonce": "ABC123",
                    "prompt": "Reply with exactly this token: ABC123",
                    "expect": "ABC123",
                },
                verdict="healthy",
                latency_ms=321,
                ts=123456,
                response_text="ABC123",
            )

        self.assertEqual(payload["attestation_schema"], "aipg.validator.attestation.v0")
        self.assertEqual(payload["assignment_source"], "validator_v0")
        self.assertTrue(payload["assignment_id"].startswith("validator-v0:"))
        self.assertEqual(payload["epoch"], "1970010210")
        self.assertEqual(payload["evidence_schema"], "aipg.validator.evidence.v0")
        self.assertEqual(payload["modality"], "text")
        self.assertEqual(payload["capability"], "text.basic.v0")
        self.assertEqual(payload["score"], 1.0)
        self.assertEqual(payload["nonce"], "ABC123")
        self.assertRegex(payload["prompt_hash"], r"^[0-9a-f]{64}$")
        self.assertRegex(payload["response_hash"], r"^[0-9a-f]{64}$")
        self.assertRegex(payload["evidence_hash"], r"^[0-9a-f]{64}$")
        self.assertNotIn("prompt", payload)
        self.assertNotIn("expect", payload)
        self.assertNotIn("response_text", payload)

    def test_evidence_hash_binds_response_text(self):
        canary = {
            "kind": "echo",
            "nonce": "ABC123",
            "prompt": "Reply with exactly this token: ABC123",
            "expect": "ABC123",
        }
        with patch.object(Settings, "VALIDATOR_WALLET", "0x" + "12" * 20):
            left = attest.build(
                worker_id="",
                model="qwen3-27b",
                canary=canary,
                verdict="healthy",
                latency_ms=321,
                ts=123456,
                response_text="ABC123",
            )
            right = attest.build(
                worker_id="",
                model="qwen3-27b",
                canary=canary,
                verdict="healthy",
                latency_ms=321,
                ts=123456,
                response_text="different",
            )

        self.assertEqual(left["prompt_hash"], right["prompt_hash"])
        self.assertNotEqual(left["response_hash"], right["response_hash"])
        self.assertNotEqual(left["evidence_hash"], right["evidence_hash"])

    def test_build_honors_grid_assignment_fields(self):
        with patch.object(Settings, "VALIDATOR_WALLET", "0x" + "12" * 20):
            payload = attest.build(
                worker_id="worker-1",
                model="qwen3-27b",
                canary={"kind": "echo", "nonce": "ABC123", "prompt": "prompt"},
                verdict="slow",
                latency_ms=45000,
                ts=123456,
                response_text="ABC123",
                assignment_id="assign-1",
                epoch="epoch-7",
                grid_nonce="grid-nonce-1",
            )

        self.assertEqual(payload["assignment_id"], "assign-1")
        self.assertEqual(payload["assignment_source"], "grid")
        self.assertEqual(payload["grid_nonce"], "grid-nonce-1")
        self.assertEqual(payload["epoch"], "epoch-7")

    def test_build_rejects_unknown_verdict(self):
        with self.assertRaisesRegex(RuntimeError, "verdict"):
            attest.build(
                worker_id="",
                model="qwen3-27b",
                canary={"kind": "echo", "nonce": "ABC123"},
                verdict="maybe",
                latency_ms=1,
                ts=123456,
            )

    def test_sign_recovers_configured_validator_wallet(self):
        account = Account.create()
        with (
            patch.object(Settings, "VALIDATOR_WALLET", account.address.lower()),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", account.key.hex()),
        ):
            payload = attest.build(
                worker_id="worker-1",
                model="qwen3-27b",
                canary={"kind": "echo", "nonce": "ABC123"},
                verdict="slow",
                latency_ms=45000,
                ts=123456,
            )
            envelope = attest.sign(payload)

        recovered = Account.recover_message(
            encode_defunct(text=attest._canonical(envelope["payload"])),
            signature=envelope["signature"],
        )
        self.assertEqual(recovered.lower(), account.address.lower())
        self.assertEqual(envelope["payload"]["score"], 0.75)
        self.assertTrue(envelope["signature"].startswith("0x"))

    def test_sign_rejects_validator_wallet_mismatch(self):
        account = Account.create()
        other = Account.create()
        with (
            patch.object(Settings, "VALIDATOR_WALLET", other.address.lower()),
            patch.object(Settings, "VALIDATOR_PRIVATE_KEY", account.key.hex()),
        ):
            payload = attest.build(
                worker_id="worker-1",
                model="qwen3-27b",
                canary={"kind": "echo", "nonce": "ABC123"},
                verdict="healthy",
                latency_ms=100,
                ts=123456,
            )
            with self.assertRaisesRegex(RuntimeError, "does not match"):
                attest.sign(payload)

    def test_sign_allows_unsigned_preview_without_key(self):
        payload = {"validator": "", "verdict": "healthy"}
        with patch.object(Settings, "VALIDATOR_PRIVATE_KEY", ""):
            envelope = attest.sign(payload)

        self.assertEqual(envelope, {"payload": payload, "signature": None})


if __name__ == "__main__":
    unittest.main()
