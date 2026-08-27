# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Offline harness checks, not evidence of a native or production pairing run."""

import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
import zipfile
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "pairing_canary", ROOT / "scripts/native-pairing-canary.py"
)
canary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(canary)
COMMIT = "a" * 40
PAIR = "vpa_" + "b" * 64
NODE = "val_" + "c" * 32


class NativePairingCanaryTests(unittest.TestCase):
    def candidate(
        self, root, *, entry="aipg-validator", commit=COMMIT, release_class="build"
    ):
        path = root / "aipg-validator-linux-x64.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(entry, b"offline fixture, never executable")
        manifest = {
            "schema": "aipg-validator-release-v1",
            "tag": "",
            "version": "0.1.0",
            "commit": commit,
            "release_class": release_class,
            "assets": [
                {
                    "name": path.name,
                    "bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            ],
        }
        (root / "validator-release.json").write_text(json.dumps(manifest))

    def test_only_exact_source_build_can_be_extracted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.candidate(root, commit="d" * 40)
            with self.assertRaisesRegex(
                canary.native.Failed, "candidate_identity_mismatch"
            ):
                canary.verify_candidate(root, COMMIT, "linux-x64")
            self.candidate(root, release_class="preview")
            with self.assertRaisesRegex(
                canary.native.Failed, "candidate_identity_mismatch"
            ):
                canary.verify_candidate(root, COMMIT, "linux-x64")
            self.candidate(root)
            binary, meta = canary.verify_candidate(root, COMMIT, "linux-x64")
            self.assertTrue(binary.is_file())
            self.assertFalse(meta["release_provenance"])
            self.assertEqual(meta["artifact_kind"], "reviewed_ci_build_only")
            self.assertEqual(meta["binary_version"], "v0.1.0-dev")

    def test_hash_and_unsafe_paths_fail_before_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.candidate(root, entry="../aipg-validator")
            with self.assertRaisesRegex(
                canary.native.Failed, "unsafe_candidate_archive"
            ):
                canary.verify_candidate(root, COMMIT, "linux-x64")
            self.assertFalse((root / "aipg-validator").exists())
            self.candidate(root)
            with (root / "aipg-validator-linux-x64.zip").open("ab") as output:
                output.write(b"changed")
            with self.assertRaisesRegex(
                canary.native.Failed, "candidate_archive_mismatch"
            ):
                canary.verify_candidate(root, COMMIT, "linux-x64")

    def test_wrong_workflow_source_or_unfinished_run_never_downloads(self):
        valid = {
            "head_sha": COMMIT,
            "head_branch": "master",
            "event": "push",
            "path": ".github/workflows/release-binaries.yml",
            "conclusion": "success",
            "head_repository": {"full_name": canary.native.REPO},
        }
        for field, value in (
            ("head_sha", "d" * 40),
            ("head_branch", "unreviewed"),
            ("event", "pull_request"),
            ("conclusion", None),
            ("head_repository", {"full_name": "somebody/fork"}),
            ("path", ".github/workflows/other.yml"),
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                with patch.object(
                    canary.native,
                    "command",
                    return_value=json.dumps({**valid, field: value}),
                ) as command:
                    with self.assertRaisesRegex(
                        canary.native.Failed, "candidate_run_not_qualified"
                    ):
                        canary.fetch_candidate(
                            Path(tmp) / "artifacts", "123", COMMIT, "linux-x64"
                        )
                    command.assert_called_once()
                    self.assertFalse((Path(tmp) / "artifacts").exists())

    def test_review_binds_ticket_pairing_and_external_console_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pending = {
                "validator_id": NODE,
                "pairing_id": PAIR,
                "approval_url": canary.CONSOLE_URL + "/" + PAIR,
            }
            ticket = canary.request_review(root, pending, "node-removal")
            approved = {**pending, "comparison_code": "A1B2C3D4"}
            self.assertFalse(canary.confirmed_review(root, approved, ticket))
            response = {
                "ticket": "d" * 32,
                "pairing_id": PAIR,
                "comparison_code": "A1B2C3D4",
            }
            canary.private_json(root / "review-response.json", response)
            self.assertFalse(canary.confirmed_review(root, approved, ticket))
            canary.private_json(
                root / "review-response.json",
                {**response, "ticket": ticket, "comparison_code": "00000000"},
            )
            with self.assertRaisesRegex(
                canary.native.Failed, "console_code_does_not_match"
            ):
                canary.confirmed_review(root, approved, ticket)
            with (
                patch("getpass.getpass", return_value="a1b2c3d4"),
                patch.object(canary.sys.stdin, "isatty", return_value=True),
            ):
                self.assertEqual(canary.review(root), 0)
            self.assertTrue(canary.confirmed_review(root, approved, ticket))
            if os.name != "nt":
                self.assertEqual(
                    (root / "review-request.json").stat().st_mode & 0o777, 0o600
                )
                (root / "review-response.json").chmod(0o644)
                with self.assertRaisesRegex(
                    canary.native.Failed, "review_file_not_private"
                ):
                    canary.confirmed_review(root, approved, ticket)

    def test_review_destination_cannot_be_redirected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(
                canary.native.Failed, "invalid_review_destination"
            ):
                canary.request_review(
                    root,
                    {"pairing_id": PAIR, "approval_url": "https://attacker.example/"},
                    "node-removal",
                )
            self.assertFalse((root / "review-request.json").exists())

    def test_review_never_falls_back_to_echoing_input(self):
        with (
            patch.object(canary.sys.stdin, "isatty", return_value=False),
            patch("getpass.getpass") as prompt,
        ):
            with self.assertRaisesRegex(
                canary.native.Failed, "interactive_review_required"
            ):
                canary.review(Path("not-opened"))
            prompt.assert_not_called()

    def test_review_rejects_duplicate_fields_and_oversized_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "review.json"
            path.write_text('{"ticket":"one","ticket":"two"}')
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                canary.read_json(path)
            path.write_bytes(b"x" * 16385)
            with self.assertRaisesRegex(canary.native.Failed, "unsafe_json_file"):
                canary.read_json(path)

    def test_missing_approval_timeout_is_failure_not_success(self):
        with patch.object(canary, "pairing", return_value={"status": "pending"}):
            with (
                patch.object(canary.time, "monotonic", side_effect=[1, 2, 4]),
                patch.object(canary.time, "sleep"),
            ):
                with self.assertRaisesRegex(
                    canary.native.Failed, "pairing_wait_timed_out"
                ):
                    canary.poll(
                        None, lambda value: value.get("status") == "approved", 3
                    )

    def test_pairing_cleanup_refuses_replaced_config_before_starting_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "node.env"
            config.write_text("original isolated identity")
            expected = canary.native.fingerprint(config)
            config.write_text("an unrelated identity")
            with patch.object(canary.native, "opened_app") as app:
                with self.assertRaisesRegex(
                    canary.native.Failed, "cleanup_config_changed"
                ):
                    canary.clean_pairing(Path("binary"), config, expected)
                app.assert_not_called()

    def exercise(self, *, cleanup_failure=False, lost_start=False):
        """Drive orchestration using a fake app; it is deliberately not native proof."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = SimpleNamespace(
                workspace=root / "private",
                report=root / "report.json",
                run_id="123",
                commit=COMMIT,
                core_commit=COMMIT,
                minutes=30,
            )
            state = {"status": "none", "running": False, "phase": "", "starts": 0}
            control = {"confirmed": 0, "unlinked": 0}

            class App:
                def __init__(self, binary, config):
                    self.config, self.token, self.reviewed = (
                        config,
                        "private-local-token",
                        False,
                    )
                    self.link_reads = 0

                def request(self, path="/status.json", action=None, auth=True):
                    if not auth:
                        return 401, b"{}"
                    return 200, json.dumps({"status": "idle"}).encode()

                def action(self, action):
                    if action == "enroll":
                        self.config.write_text(
                            "VALIDATOR_PRIVATE_KEY=synthetic-private-secret\nVALIDATOR_API_KEY=synthetic-api-secret\n"
                            "VALIDATOR_WALLET=0x" + "e" * 40 + "\n"
                        )
                    state["running"] = action == "run"

                def wait(self, predicate, seconds=90):
                    value = {
                        "phase": "enrolled",
                        "running": state["running"],
                        "validator_id": NODE,
                        "heartbeat_at": "fixture",
                        "accepted": 1,
                        "pending": 0,
                        "dead": 0,
                    }
                    if not predicate(value):
                        raise AssertionError("fake app predicate not satisfied")
                    return value

            @contextmanager
            def opened(binary, config):
                yield App(binary, config)

            def action(app, operation, **fields):
                if operation == "start":
                    state.update(status="pending", starts=state["starts"] + 1)
                    if lost_start:
                        raise TimeoutError(
                            "private response content must not be printed"
                        )
                elif operation == "cancel":
                    state["status"] = "cancelled"
                elif operation == "confirm":
                    self.assertFalse(app.reviewed)
                    return {"status": "error", "error": "changed"}
                elif operation == "unlink":
                    control["unlinked"] += 1
                    state["status"] = "none"
                elif operation == "refresh":
                    app.reviewed = True
                    if (
                        state["status"] == "linked"
                        and state["phase"] == "owner-removal"
                    ):
                        app.link_reads += 1
                        if app.link_reads == 2:
                            state["status"] = (
                                "cancelled"  # Simulated external owner removal.
                            )
                return {
                    "status": state["status"],
                    "validator_id": NODE,
                    "pairing_id": PAIR,
                    "review_hash": "d" * 64,
                    "comparison_code": "A1B2C3D4",
                    "approval_url": canary.CONSOLE_URL + "/" + PAIR,
                }

            original_review = canary.request_review

            def approve(workspace, value, phase):
                state.update(status="approved", phase=phase)
                ticket = original_review(workspace, value, phase)
                canary.private_json(
                    workspace / "review-response.json",
                    {
                        "ticket": ticket,
                        "pairing_id": PAIR,
                        "comparison_code": "A1B2C3D4",
                    },
                )
                return ticket

            def commit(app, value):
                self.assertTrue(app.reviewed)
                state["status"] = "linked"
                control["confirmed"] += 1

            def core(client, method, path):
                if path == "/health":
                    return {"build_commit": COMMIT}
                return {
                    "economic_effect": "none",
                    "probe_policy": {"quality_eligible": False},
                    "features": {
                        key: False
                        for key in (
                            "account_pairing",
                            "validator_rewards",
                            "staking_required",
                            "image_fidelity",
                            "video_validation",
                        )
                    },
                }

            with (
                patch.object(canary, "platform_name", return_value="linux-x64"),
                patch.object(
                    canary,
                    "fetch_candidate",
                    return_value=(root / "binary", {"binary_version": "v0.1.0-dev"}),
                ),
                patch.object(
                    canary.native, "command", return_value="aipg-validator v0.1.0-dev"
                ),
                patch.object(canary.native, "core_json", side_effect=core),
                patch.object(canary.native, "opened_app", side_effect=opened),
                patch.object(canary, "pairing", side_effect=action),
                patch.object(canary, "request_review", side_effect=approve),
                patch.object(
                    canary, "discard_confirmation_response", side_effect=commit
                ),
                patch.object(
                    canary,
                    "clean_pairing",
                    side_effect=RuntimeError("private cleanup data")
                    if cleanup_failure
                    else None,
                ) as clean_pairing,
                patch.object(
                    canary.native,
                    "cleanup",
                    return_value={"suspended": True, "keys_revoked": 1},
                ) as retire,
            ):
                result = canary.run(args)
                report = json.loads(args.report.read_text())
                retire.assert_called_once()
                self.assertEqual(retire.call_args.args[-1], "0x" + "e" * 40)
                clean_pairing.assert_called_once()
            self.assertNotIn("private response", args.report.read_text())
            self.assertNotIn("private cleanup data", args.report.read_text())
            self.assertNotIn(PAIR, args.report.read_text())
            self.assertNotIn("A1B2C3D4", args.report.read_text())
            if cleanup_failure or lost_start:
                self.assertEqual(result, 1)
                self.assertFalse(report["passed"])
            else:
                self.assertEqual(result, 0, report)
                self.assertTrue(report["passed"])
                self.assertEqual(control, {"confirmed": 2, "unlinked": 1})
                self.assertEqual(report["accepted_reports_after_pairing"], 1)
                self.assertTrue(report["pairing_cleanup_verified"])

    def test_journey_requires_two_consents_removal_recovery_and_fresh_evidence(self):
        self.exercise()

    def test_cleanup_failure_prevents_pass_but_still_retires_node(self):
        self.exercise(cleanup_failure=True)

    def test_lost_start_response_still_attempts_pairing_cleanup(self):
        self.exercise(lost_start=True)


if __name__ == "__main__":
    unittest.main()
