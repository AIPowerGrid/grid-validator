# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import httpx
from dotenv import dotenv_values
from eth_account import Account
from eth_account.messages import encode_defunct

from validator import cli, enrollment


def challenge(wallet, now=None):
    now = (now or datetime.now(timezone.utc)).replace(microsecond=0)
    nonce = "a" * 32
    issued = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    expires = (now + timedelta(seconds=300)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "nonce": nonce, "chain_id": 8453, "expires_in": 300,
        "message": (
            f"{enrollment.DOMAIN} wants you to sign in with your Ethereum account:\n{wallet}\n\n"
            f"Sign in to AI Power Grid.\n\nURI: {enrollment.URI}\nVersion: 1\nChain ID: 8453\n"
            f"Nonce: {nonce}\nIssued At: {issued}\nExpiration Time: {expires}"
        ),
    }


class EnrollmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "private" / ".env"
        self.requests = []
        self.api_key = "grid_" + "synthetic_test_" * 3
        self.token = "synthetic_session." * 3
        self.mutate = lambda data: data
        self.session_mutate = lambda data: data

    def handler(self, request):
        self.requests.append(request)
        body = json.loads(request.content)
        self.assertEqual(request.url.host, "api.aipowergrid.io")
        if request.url.path.endswith("/challenge"):
            self.assertTrue(self.path.exists(), "Signer must survive network failure")
            self.wallet = body["address"]
            return httpx.Response(200, json=challenge(self.wallet))
        if request.url.path.endswith("/verify"):
            recovered = Account.recover_message(encode_defunct(text=body["message"]), signature=body["signature"])
            self.assertEqual(recovered.lower(), self.wallet)
            return httpx.Response(200, json=self.session_mutate({
                "wallet": self.wallet, "account_id": "12345678-1234-5678-1234-567812345678",
                "token_type": "Bearer", "access_token": self.token,
            }))
        self.assertEqual(request.url.path, "/v1/account/keys")
        self.assertEqual(body["purpose"], "validator")
        self.assertEqual(request.headers["Authorization"], f"Bearer {self.token}")
        return httpx.Response(200, json=self.mutate({
            "purpose": "validator", "api_key": self.api_key, "scopes": sorted(enrollment.SCOPES),
        }))

    def run_enroll(self, handler=None):
        client = httpx.Client(transport=httpx.MockTransport(handler or self.handler))
        with patch("validator.enrollment.httpx.Client", return_value=client) as factory, redirect_stdout(io.StringIO()) as output:
            result = enrollment.enroll(self.path)
        if self.requests:
            factory.assert_called_once_with(timeout=15, follow_redirects=False, trust_env=False)
        self.output = output.getvalue()
        return result

    def test_complete_wallet_signature_scoped_key_and_idempotent_rerun(self):
        self.assertTrue(self.run_enroll())
        values = dotenv_values(self.path)
        self.assertEqual(values["VALIDATOR_API_KEY"], self.api_key)
        self.assertEqual(values["VALIDATOR_REQUIRE_STAKE"], "false")
        self.assertNotIn(values["VALIDATOR_PRIVATE_KEY"], self.output)
        self.assertNotIn(self.api_key, self.output)
        self.assertNotIn(self.token, self.path.read_text())
        before = self.path.read_bytes()
        with patch("validator.enrollment.httpx.Client") as client:
            self.assertFalse(enrollment.enroll(self.path))
            client.assert_not_called()
        self.assertEqual(self.path.read_bytes(), before)

    def test_decline_does_not_generate_identity_or_contact_grid(self):
        with patch("builtins.input", return_value="n"), patch("validator.enrollment.enroll") as enroll, redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["enroll", "--env", str(self.path)]), 0)
        enroll.assert_not_called()
        self.assertFalse(self.path.parent.exists())

    def test_no_prompted_personal_key(self):
        with patch("builtins.input", return_value="y"), patch("getpass.getpass") as secret, patch("validator.enrollment.enroll", return_value=True), redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["enroll", "--env", str(self.path)]), 0)
        secret.assert_not_called()

    def test_legacy_init_directs_new_users_to_enrollment_without_any_key_prompt(self):
        with patch("validator.cli._env_path", return_value=self.path), patch("builtins.input") as prompt, patch("getpass.getpass") as secret, redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(["init"]), 1)
        prompt.assert_not_called()
        secret.assert_not_called()
        self.assertIn("aipg-validator enroll", output.getvalue())

    def test_encoded_response_is_rejected_before_decoding(self):
        def encoded(request):
            return httpx.Response(200, headers={"Content-Encoding": "gzip"}, stream=httpx.ByteStream(b"not-gzip"))
        with self.assertRaisesRegex(enrollment.EnrollmentError, "encoded"):
            self.run_enroll(encoded)

    def test_network_failure_resumes_with_same_signer(self):
        def unavailable(request):
            raise httpx.ConnectError("must not echo secrets", request=request)
        with self.assertRaises(enrollment.EnrollmentError):
            self.run_enroll(unavailable)
        before = dotenv_values(self.path)["VALIDATOR_PRIVATE_KEY"]
        self.assertTrue(self.run_enroll())
        self.assertEqual(dotenv_values(self.path)["VALIDATOR_PRIVATE_KEY"], before)

    def test_existing_identity_and_partial_manual_config_are_untouched(self):
        for lines in (
            ["VALIDATOR_WALLET=0x123"],
            ["VALIDATOR_PRIVATE_KEY=unknown"],
            ["GRID_API_URL=https://other.example"],
            ["GRID_API_URL="],
        ):
            with self.subTest(lines=lines):
                cli._write_private_env(self.path, lines)
                before = self.path.read_bytes()
                with patch("validator.enrollment.httpx.Client") as client, self.assertRaises(enrollment.EnrollmentError):
                    enrollment.enroll(self.path)
                client.assert_not_called()
                self.assertEqual(self.path.read_bytes(), before)

    def test_malicious_or_broad_key_is_never_written(self):
        for field, value in (("scopes", ["inference"]), ("scopes", [{}]), ("purpose", "inference"), ("api_key", "grid_" + "x" * 24 + "\nPRIVATE=oops")):
            with self.subTest(field=field):
                self.mutate = lambda data: {**data, field: value}
                with self.assertRaises(enrollment.EnrollmentError):
                    self.run_enroll()
                self.assertFalse(dotenv_values(self.path)["VALIDATOR_API_KEY"])

    def test_wrong_account_session_stops_before_requesting_api_key(self):
        self.session_mutate = lambda data: {**data, "wallet": "0x" + "0" * 40}
        with self.assertRaises(enrollment.EnrollmentError):
            self.run_enroll()
        self.assertEqual(len(self.requests), 2)

    def test_transport_rejects_redirect_and_large_or_invalid_responses(self):
        for response in (httpx.Response(302, headers={"location": "https://evil.example"}), httpx.Response(200, text="x" * 40000), httpx.Response(200, json=[]), httpx.Response(429, text=self.api_key)):
            with self.subTest(status=response.status_code):
                with self.assertRaises(enrollment.EnrollmentError) as exc:
                    self.run_enroll(lambda request: response)
                self.assertNotIn(self.api_key, str(exc.exception))

    def test_two_setup_processes_cannot_replace_signer(self):
        with enrollment.enrollment_lock(self.path):
            with self.assertRaises(enrollment.EnrollmentError):
                self.run_enroll()
        self.assertFalse(self.path.exists())
        self.assertTrue(self.run_enroll())

    def test_out_of_band_config_change_is_preserved(self):
        def mutate(data):
            cli._upsert_env(self.path, {"PROBE_INTERVAL_S": "121"}, fresh_lines=[])
            return data
        self.mutate = mutate
        with self.assertRaises(enrollment.EnrollmentError):
            self.run_enroll()
        self.assertEqual(dotenv_values(self.path)["PROBE_INTERVAL_S"], "121")
        self.assertFalse(dotenv_values(self.path)["VALIDATOR_API_KEY"])

    def test_failed_final_save_can_retry_with_original_identity(self):
        real_write = cli._upsert_env
        def write(path, updates, **kwargs):
            if updates.get("VALIDATOR_API_KEY"):
                raise OSError("disk full")
            return real_write(path, updates, **kwargs)
        with patch("validator.cli._upsert_env", side_effect=write), self.assertRaises(OSError):
            self.run_enroll()
        signer = dotenv_values(self.path)["VALIDATOR_PRIVATE_KEY"]
        self.assertTrue(self.run_enroll())
        self.assertEqual(dotenv_values(self.path)["VALIDATOR_PRIVATE_KEY"], signer)


class ChallengeTests(unittest.TestCase):
    def test_only_exact_login_purpose_address_domain_nonce_and_freshness(self):
        wallet = Account.create().address.lower()
        now = datetime.now(timezone.utc)
        valid = challenge(wallet, now)
        self.assertEqual(enrollment.validated_message(valid, wallet, now), valid["message"])
        for original, replacement in (
            (wallet, "0x" + "0" * 40),
            (enrollment.DOMAIN, "attacker.example"),
            ("Sign in to AI Power Grid.", "Authorize a transfer."),
            ("Chain ID: 8453", "Chain ID: 1"),
            ("Nonce: " + "a" * 32, "Nonce: " + "b" * 32),
            ("Version: 1", "Version: 1\nResources: arbitrary"),
        ):
            with self.subTest(original=original), self.assertRaises(enrollment.EnrollmentError):
                enrollment.validated_message({**valid, "message": valid["message"].replace(original, replacement)}, wallet, now)
        for delta in (-601, 61):
            with self.subTest(delta=delta), self.assertRaises(enrollment.EnrollmentError):
                enrollment.validated_message(challenge(wallet, now + timedelta(seconds=delta)), wallet, now)
