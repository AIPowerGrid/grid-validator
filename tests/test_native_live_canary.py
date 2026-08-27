# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Offline safeguards for the explicitly approved live harness; no Core traffic."""

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import time
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import httpx
from eth_account import Account

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "native_canary", ROOT / "scripts/native-live-canary.py"
)
canary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(canary)


class NativeCanaryTests(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "POSIX owned-process-group cleanup")
    def test_timeout_stops_descendants_after_parent_has_exited(self):
        script = (
            "import subprocess,sys; "
            "subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
            "print('private child output',flush=True)"
        )
        started = time.monotonic()
        with self.assertRaisesRegex(canary.Failed, "command_timeout") as failure:
            canary.command([sys.executable, "-c", script], timeout=0.3)
        self.assertLess(time.monotonic() - started, 5)
        self.assertNotIn("private child output", str(failure.exception))

    def test_child_environment_excludes_tokens_keys_and_python_injection(self):
        with patch.dict(
            os.environ,
            {
                "GH_TOKEN": "do-not-copy",
                "GITHUB_TOKEN": "do-not-copy",
                "VALIDATOR_API_KEY": "do-not-copy",
                "GRID_SALT": "do-not-copy",
                "PYTHONPATH": "do-not-copy",
                "HTTP_PROXY": "do-not-copy",
            },
        ):
            result = canary.binary_env(Path("node.env"))
        self.assertNotIn("do-not-copy", result.values())
        self.assertEqual(result["VALIDATOR_UPDATE_CHECK"], "false")

    def test_identity_must_be_exact_public_id(self):
        with self.assertRaises(canary.Failed):
            canary.public_identity({"validator_id": "private material"})
        self.assertEqual(
            canary.public_identity({"validator_id": "val_" + "a" * 32}),
            "val_" + "a" * 32,
        )

    def make_archive(self, root, name=None, commit=None):
        path = root / canary.ASSET
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(name or canary.EXE, b"offline fixture; never executed")
        manifest = {
            "tag": canary.CURRENT,
            "commit": commit or canary.RELEASES[canary.CURRENT],
            "assets": [
                {
                    "name": canary.ASSET,
                    "bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            ],
        }
        (root / "validator-release.json").write_text(json.dumps(manifest))

    def test_verified_manifest_must_match_archive_and_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_archive(root, commit="0" * 40)
            with self.assertRaisesRegex(canary.Failed, "release_identity_mismatch"):
                canary.verify_archive(root, canary.CURRENT)
            self.assertFalse((root / canary.EXE).exists())
            self.make_archive(root)
            self.assertEqual(
                canary.verify_archive(root, canary.CURRENT)["tag"], canary.CURRENT
            )
            with self.assertRaisesRegex(canary.Failed, "binary_already_exists"):
                canary.verify_archive(root, canary.CURRENT)

    def test_archive_rejects_paths_before_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_archive(root, name="../" + canary.EXE)
            with self.assertRaisesRegex(canary.Failed, "unsafe_archive"):
                canary.verify_archive(root, canary.CURRENT)
            self.assertFalse((root / canary.EXE).exists())

    def test_core_transport_is_bounded_and_does_not_return_error_body(self):
        for size, status in ((65537, 200), (10, 403)):
            with httpx.Client(
                transport=httpx.MockTransport(
                    lambda request: httpx.Response(status, content=b"x" * size)
                )
            ) as client:
                with self.assertRaises(canary.Failed) as failure:
                    canary.core_json(client, "GET", "/health")
                self.assertNotIn("xxx", str(failure.exception))

    def test_cleanup_refuses_non_generated_config_before_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "node.env"
            config.write_text("VALIDATOR_IDENTITY_ORIGIN=existing-human\n")
            with patch("httpx.Client") as client:
                with self.assertRaisesRegex(
                    canary.Failed, "cleanup_identity_not_generated"
                ):
                    canary.cleanup(Path("binary"), config)
                client.assert_not_called()

    def test_cleanup_refuses_mismatched_signer_before_network(self):
        account = Account.create()
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "node.env"
            config.write_text(
                "VALIDATOR_IDENTITY_ORIGIN=dedicated-enrollment-v1\n"
                "GRID_API_URL=https://api.aipowergrid.io\n"
                "VALIDATOR_WALLET=0x" + "0" * 40 + "\n"
                "VALIDATOR_PRIVATE_KEY=0x" + bytes(account.key).hex() + "\n"
            )
            with patch("httpx.Client") as client:
                with self.assertRaisesRegex(canary.Failed, "cleanup_identity_mismatch"):
                    canary.cleanup(Path("binary"), config)
                client.assert_not_called()

    def retirement_case(self, *, wrong_owner=False, extra_key=False):
        account = Account.create()
        wallet = account.address.lower()
        state = {"suspended": False, "revoked": False, "deletes": 0}
        from validator.enrollment import DOMAIN, URI

        def handler(request):
            path = request.url.path
            if path == "/v1/validator/registration":
                if state["revoked"]:
                    return httpx.Response(401, json={"detail": "revoked"})
                return httpx.Response(
                    200,
                    json={"status": "suspended" if state["suspended"] else "active"},
                )
            if path == "/v1/accounts/wallet/challenge":
                now = datetime.now(timezone.utc).replace(microsecond=0)
                nonce = "a" * 32
                message = (
                    f"{DOMAIN} wants you to sign in with your Ethereum account:\n{wallet}\n\n"
                    f"Sign in to AI Power Grid.\n\nURI: {URI}\nVersion: 1\nChain ID: 8453\n"
                    f"Nonce: {nonce}\nIssued At: {now:%Y-%m-%dT%H:%M:%SZ}\n"
                    f"Expiration Time: {now + timedelta(minutes=5):%Y-%m-%dT%H:%M:%SZ}"
                )
                state["message"] = message
                return httpx.Response(
                    200, json={"message": message, "nonce": nonce, "chain_id": 8453}
                )
            if path == "/v1/accounts/wallet/verify":
                from eth_account.messages import encode_defunct

                body = json.loads(request.content)
                self.assertEqual(
                    Account.recover_message(
                        encode_defunct(text=state["message"]),
                        signature=body["signature"],
                    ).lower(),
                    wallet,
                )
                return httpx.Response(
                    200,
                    json={
                        "wallet": wallet,
                        "account_id": "fixture-owner",
                        "access_token": "fixture-session",
                    },
                )
            if path == "/v1/account":
                keys = [
                    {
                        "id": "a" * 12,
                        "label": "validator-dedicated-node",
                        "revoked": state["revoked"],
                    }
                ]
                if extra_key:
                    keys.append(
                        {"id": "b" * 12, "label": "unrelated-key", "revoked": False}
                    )
                return httpx.Response(
                    200,
                    json={
                        "wallet": wallet,
                        "keys": keys,
                        "account_id": "wrong-owner" if wrong_owner else "fixture-owner",
                    },
                )
            self.assertEqual(path, "/v1/account/keys/" + "a" * 12)
            self.assertEqual(request.method, "DELETE")
            state.update(revoked=True, deletes=state["deletes"] + 1)
            return httpx.Response(200, json={"count": 1})

        def suspend(args, **kwargs):
            self.assertEqual(args[-1], "suspend")
            state["suspended"] = True
            return ""

        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "node.env"
            config.write_text(
                "VALIDATOR_IDENTITY_ORIGIN=dedicated-enrollment-v1\n"
                "GRID_API_URL=https://api.aipowergrid.io\n"
                "VALIDATOR_WALLET=" + wallet + "\n"
                "VALIDATOR_PRIVATE_KEY=0x" + bytes(account.key).hex() + "\n"
                "VALIDATOR_API_KEY=fixture-key\n"
            )
            client = httpx.Client(transport=httpx.MockTransport(handler))
            with (
                patch("httpx.Client", return_value=client),
                patch.object(canary, "command", side_effect=suspend),
            ):
                if wrong_owner or extra_key:
                    with self.assertRaises(canary.Failed):
                        canary.cleanup(Path("binary"), config, wallet)
                    self.assertEqual(state["deletes"], 0)
                else:
                    self.assertEqual(
                        canary.cleanup(Path("binary"), config, wallet),
                        {"suspended": True, "keys_revoked": 1},
                    )
                    self.assertEqual(state["deletes"], 1)

    def test_retirement_requires_real_wallet_proof_and_verified_revocation(self):
        self.retirement_case()

    def test_retirement_never_revokes_on_owner_confusion_or_unexpected_keys(self):
        self.retirement_case(wrong_owner=True)
        self.retirement_case(extra_key=True)

    def test_workflow_is_owner_gated_manual_and_only_uploads_report(self):
        workflow = (ROOT / ".github/workflows/native-live-canary.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("pull_request:", workflow)
        self.assertNotIn("push:", workflow)
        self.assertIn("github.ref == 'refs/heads/master'", workflow)
        self.assertIn("inputs.approve_unpaid_canary", workflow)
        self.assertIn("environment: validator-release", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertIn("path: ${{ runner.temp }}/validator-canary-report.json", workflow)
        self.assertNotIn("path: ${{ runner.temp }}/validator-private", workflow)


if __name__ == "__main__":
    unittest.main()
