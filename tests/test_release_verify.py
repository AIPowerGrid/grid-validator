# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Hermetic policy tests; signature transport is explicitly mocked here."""

import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from validator import release_verify as rv


class ReleaseVerificationTests(unittest.TestCase):
    def setUp(self):
        self.tag = "v0.1.0-preview.17"
        self.commit = "a" * 40
        self.manifest = {
            "schema": "aipg-validator-release-v1",
            "tag": self.tag,
            "version": "0.1.0",
            "release_class": "preview",
            "commit": self.commit,
            "platform_signing": {
                "macos": {
                    "identity": "unsigned",
                    "verified": False,
                    "notarized": False,
                    "team_id": None,
                },
                "windows": {"identity": "unsigned", "verified": False, "subject": None},
            },
            "unsigned_warning": rv.UNSIGNED_WARNING,
            "assets": [
                {"name": name, "bytes": 12345, "sha256": "b" * 64}
                for name in sorted(rv.PAYLOADS)
            ],
        }
        self.attestations = json.dumps(
            {"attestations": [{"bundle": {"fixture": True}}]}
        ).encode()

    def raw(self):
        return json.dumps(self.manifest).encode()

    def statement(self):
        return {
            "_type": "https://in-toto.io/Statement/v1",
            "predicateType": "https://slsa.dev/provenance/v1",
            "subject": [
                {
                    "name": "validator-release.json",
                    "digest": {"sha256": hashlib.sha256(self.raw()).hexdigest()},
                }
            ],
            "predicate": {
                "buildDefinition": {
                    "buildType": "https://actions.github.io/buildtypes/workflow/v1",
                    "externalParameters": {
                        "workflow": {
                            "ref": f"refs/tags/{self.tag}",
                            "repository": rv.REPOSITORY,
                            "path": rv.WORKFLOW,
                        }
                    },
                    "internalParameters": {
                        "github": {
                            "event_name": "push",
                            "runner_environment": "github-hosted",
                            "repository_id": "1268894731",
                            "repository_owner_id": "150180242",
                        }
                    },
                    "resolvedDependencies": [
                        {
                            "uri": f"git+{rv.REPOSITORY}@refs/tags/{self.tag}",
                            "digest": {"gitCommit": self.commit},
                        }
                    ],
                },
                "runDetails": {
                    "builder": {
                        "id": f"{rv.REPOSITORY}/{rv.WORKFLOW}@refs/tags/{self.tag}"
                    }
                },
            },
        }

    def verify(self, **kwargs):
        return rv.verify_release(
            self.raw(),
            self.attestations,
            tag=self.tag,
            platform=kwargs.get("platform", "windows-x64"),
        )

    def test_all_platforms_bind_verified_manifest(self):
        for platform, archive in rv.PLATFORMS.items():
            with (
                self.subTest(platform=platform),
                patch.object(
                    rv, "_verify_dsse", return_value=self.statement()
                ) as verify,
            ):
                result = self.verify(platform=platform)
                self.assertEqual(result.archive, archive)
                self.assertEqual(result.commit, self.commit)
                self.assertEqual(result.size, 12345)
                self.assertTrue(result.unsigned_preview)
                self.assertEqual(
                    verify.call_args.args[1],
                    f"{rv.REPOSITORY}/{rv.WORKFLOW}@refs/tags/{self.tag}",
                )

    def test_checksum_without_signature_never_suffices(self):
        with patch.object(
            rv, "_verify_dsse", side_effect=rv.ReleaseVerificationError("bad_signature")
        ):
            with self.assertRaisesRegex(
                rv.ReleaseVerificationError, "release_provenance_not_verified"
            ):
                self.verify()

    def test_mutated_manifest_cannot_borrow_old_signature(self):
        statement = self.statement()
        self.manifest["assets"][0]["sha256"] = "c" * 64
        with patch.object(rv, "_verify_dsse", return_value=statement):
            with self.assertRaises(rv.ReleaseVerificationError):
                self.verify()

    def test_wrong_provenance_binding_is_rejected(self):
        edits = [
            (("_type",), "other"),
            (("predicateType",), "https://in-toto.io/attestation/release/v0.2"),
            (
                (
                    "predicate",
                    "buildDefinition",
                    "externalParameters",
                    "workflow",
                    "path",
                ),
                ".github/workflows/unreviewed.yml",
            ),
            (
                (
                    "predicate",
                    "buildDefinition",
                    "externalParameters",
                    "workflow",
                    "ref",
                ),
                "refs/heads/master",
            ),
            (
                (
                    "predicate",
                    "buildDefinition",
                    "externalParameters",
                    "workflow",
                    "repository",
                ),
                "https://github.com/other/fork",
            ),
            (
                (
                    "predicate",
                    "buildDefinition",
                    "internalParameters",
                    "github",
                    "event_name",
                ),
                "pull_request",
            ),
            (
                (
                    "predicate",
                    "buildDefinition",
                    "internalParameters",
                    "github",
                    "runner_environment",
                ),
                "self-hosted",
            ),
            (
                (
                    "predicate",
                    "buildDefinition",
                    "internalParameters",
                    "github",
                    "repository_id",
                ),
                "other",
            ),
            (("predicate", "buildDefinition", "resolvedDependencies"), []),
            (("predicate", "runDetails", "builder", "id"), "other"),
            (("subject",), []),
        ]
        for path, value in edits:
            statement = self.statement()
            cursor = statement
            for key in path[:-1]:
                cursor = cursor[key]
            cursor[path[-1]] = value
            with (
                self.subTest(path=path),
                patch.object(rv, "_verify_dsse", return_value=statement),
            ):
                with self.assertRaises(rv.ReleaseVerificationError):
                    self.verify()

    def test_wrong_source_commit_and_duplicate_subject_rejected(self):
        for duplicate in (False, True):
            statement = self.statement()
            if duplicate:
                statement["subject"] *= 2
            else:
                statement["predicate"]["buildDefinition"]["resolvedDependencies"][0][
                    "digest"
                ]["gitCommit"] = "c" * 40
            with patch.object(rv, "_verify_dsse", return_value=statement):
                with self.assertRaises(rv.ReleaseVerificationError):
                    self.verify()

    def test_unrelated_attestation_does_not_hide_good_provenance(self):
        self.attestations = json.dumps(
            {"attestations": [{"bundle": {}}, {"bundle": {}}]}
        ).encode()
        with patch.object(
            rv,
            "_verify_dsse",
            side_effect=[rv.ReleaseVerificationError("unrelated"), self.statement()],
        ):
            self.assertEqual(self.verify().tag, self.tag)

    def test_duplicate_json_keys_and_bounds_rejected(self):
        for raw in (
            b'{"tag":"one","tag":"two"}',
            b"{" * 1500,
            b" " * (rv.MANIFEST_LIMIT + 1),
            b"\xff",
            b"[]",
        ):
            with (
                self.subTest(raw=raw[:20]),
                self.assertRaises(rv.ReleaseVerificationError),
            ):
                rv.verify_release(
                    raw, self.attestations, tag=self.tag, platform="linux-x64"
                )
        for count in (0, 5):
            self.attestations = json.dumps(
                {"attestations": [{"bundle": {}}] * count}
            ).encode()
            with self.assertRaises(rv.ReleaseVerificationError):
                self.verify()

    def test_manifest_asset_identity_and_size_rejected(self):
        original = copy.deepcopy(self.manifest)
        for field, value in (
            ("name", "../../payload.zip"),
            ("bytes", True),
            ("bytes", 0),
            ("bytes", rv.ARCHIVE_LIMIT + 1),
            ("sha256", "invalid"),
        ):
            self.manifest = copy.deepcopy(original)
            self.manifest["assets"][0][field] = value
            with (
                self.subTest(field=field, value=value),
                self.assertRaises(rv.ReleaseVerificationError),
            ):
                self.verify()
        self.manifest = copy.deepcopy(original)
        self.manifest["assets"][0] = self.manifest["assets"][1]
        with self.assertRaises(rv.ReleaseVerificationError):
            self.verify()

    def test_unsigned_stable_or_hidden_preview_warning_rejected(self):
        self.tag = "v0.1.0"
        self.manifest.update(
            tag=self.tag, release_class="stable", unsigned_warning=None
        )
        with self.assertRaisesRegex(
            rv.ReleaseVerificationError, "platform_signing_policy"
        ):
            self.verify()
        self.tag = "v0.1.0-preview.17"
        self.manifest.update(
            tag=self.tag, release_class="preview", unsigned_warning=None
        )
        with self.assertRaisesRegex(
            rv.ReleaseVerificationError, "platform_signing_policy"
        ):
            self.verify()

    def test_source_build_and_unknown_platform_rejected(self):
        with self.assertRaises(rv.ReleaseVerificationError):
            self.verify(platform="macos-x64")
        self.tag = "v0.1.0-dev"
        with self.assertRaises(rv.ReleaseVerificationError):
            self.verify()

    def test_deep_and_nonfinite_metadata_rejected(self):
        for raw in (
            b'{"nested":' + b"[" * 34 + b"0" + b"]" * 34 + b"}",
            b'{"value":NaN}',
        ):
            with self.assertRaises(rv.ReleaseVerificationError):
                rv._json(raw, rv.MANIFEST_LIMIT)


if __name__ == "__main__":
    unittest.main()
