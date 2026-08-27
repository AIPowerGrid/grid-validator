import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReleasePackagingTests(unittest.TestCase):
    @staticmethod
    def _write_release_payload(root: Path, *, tag: str = "v0.1.0-preview.1") -> None:
        archives = {
            "aipg-validator-linux-x64.zip": "aipg-validator",
            "aipg-validator-linux-arm64.zip": "aipg-validator",
            "aipg-validator-macos-arm64.zip": "aipg-validator",
            "aipg-validator-windows-x64.zip": "aipg-validator.exe",
        }
        for archive, member in archives.items():
            info = zipfile.ZipInfo(member)
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o755) << 16
            with zipfile.ZipFile(root / archive, "w", zipfile.ZIP_DEFLATED) as bundle:
                bundle.writestr(info, b"test validator binary")

        (root / "aipg-validator-release.spdx.json").write_text(
            json.dumps({"spdxVersion": "SPDX-2.3"}), encoding="utf-8"
        )
        (root / "install-validator.sh").write_text(
            "#!/usr/bin/env bash\nset -euo pipefail\n"
            "echo prepare-wallet\necho ' init'\n",
            encoding="utf-8",
        )
        (root / "install-validator.ps1").write_text(
            "# SPDX-License-Identifier: AGPL-3.0-or-later\n"
            "param([switch]$AcceptUnsignedPreview)\n"
            "Write-Host prepare-wallet\nWrite-Host ' init'\n",
            encoding="utf-8",
        )
        payloads = [
            *archives,
            "aipg-validator-release.spdx.json",
            "install-validator.sh",
            "install-validator.ps1",
        ]
        assets = [
            {
                "name": name,
                "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest(),
                "bytes": (root / name).stat().st_size,
            }
            for name in payloads
        ]
        manifest = {
            "schema": "aipg-validator-release-v1",
            "tag": tag,
            "version": "0.1.0",
            "commit": "a" * 40,
            "release_class": "stable" if tag == "v0.1.0" else "preview",
            "unsigned_warning": (
                None
                if tag == "v0.1.0"
                else "UNSIGNED PREVIEW: macOS is not Developer ID signed or notarized; "
                "Windows is not Authenticode signed. Verify SHA256SUMS and GitHub "
                "provenance before running."
            ),
            "platform_signing": {
                "macos": {
                    "verified": False,
                    "identity": "unsigned",
                    "notarized": False,
                    "team_id": None,
                },
                "windows": {
                    "verified": False,
                    "identity": "unsigned",
                    "subject": None,
                },
            },
            "assets": assets,
        }
        (root / "validator-release.json").write_text(
            json.dumps(manifest, sort_keys=True), encoding="utf-8"
        )
        checksummed = [*payloads, "validator-release.json"]
        (root / "SHA256SUMS").write_text(
            "".join(
                f"{hashlib.sha256((root / name).read_bytes()).hexdigest()}  {name}\n"
                for name in checksummed
            ),
            encoding="ascii",
        )

    @staticmethod
    def _run_release_verifier(root: Path, **env_overrides: str) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env.update(env_overrides)
        return subprocess.run(
            [str(ROOT / "scripts" / "verify-release-assets.sh"), str(root)],
            check=False,
            capture_output=True,
            env=env,
            text=True,
        )

    def test_docker_image_uses_frozen_lock_and_non_root_runtime(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        from_lines = [line for line in dockerfile.splitlines() if line.startswith("FROM ")]

        self.assertEqual(len(from_lines), 2)
        for line in from_lines:
            self.assertRegex(line, r"@sha256:[0-9a-f]{64}")
        self.assertIn("COPY pyproject.toml uv.lock README.md ./", dockerfile)
        self.assertIn('ARG AIPG_VALIDATOR_RELEASE_TAG=""', dockerfile)
        self.assertIn("COPY scripts/stamp-release-tag.py", dockerfile)
        self.assertIn(
            'python scripts/stamp-release-tag.py "$AIPG_VALIDATOR_RELEASE_TAG"',
            dockerfile,
        )
        self.assertIn("uv sync --frozen --no-dev --no-editable", dockerfile)
        self.assertIn("COPY --from=builder /app /app", dockerfile)
        self.assertIn("USER validator", dockerfile)

    def test_all_workflow_actions_are_commit_sha_pinned(self):
        workflows = ROOT / ".github" / "workflows"
        uses_pattern = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)", re.MULTILINE)

        for path in workflows.glob("*.yml"):
            body = path.read_text(encoding="utf-8")
            for action in uses_pattern.findall(body):
                with self.subTest(workflow=path.name, action=action):
                    self.assertRegex(action, r"^[^@]+@[0-9a-f]{40}$")

    def test_release_workflows_enforce_locked_release_artifacts(self):
        binaries = (ROOT / ".github" / "workflows" / "release-binaries.yml").read_text(
            encoding="utf-8"
        )
        verifier = (ROOT / "scripts" / "verify-release-assets.sh").read_text(
            encoding="utf-8"
        )
        docker = (ROOT / ".github" / "workflows" / "docker.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("uv sync --frozen --extra release", binaries)
        self.assertIn("uv run --frozen --extra release pyinstaller", binaries)
        self.assertIn("python scripts/stamp-release-tag.py", binaries)
        self.assertIn('aipg-validator $EXPECTED_RELEASE_TAG', binaries)
        self.assertIn("pull_request:", binaries)
        self.assertIn("branches: [master]", binaries)
        self.assertIn("git merge-base --is-ancestor", binaries)
        self.assertIn("binary publication requires a protected v* tag push", binaries)
        self.assertNotIn("inputs.release_tag", binaries)
        self.assertIn("environment: validator-release", binaries)
        self.assertIn("name: Assemble verified release payload", binaries)
        self.assertIn("name: Clean install ${{ matrix.asset }}", binaries)
        self.assertIn("install-validator.ps1", binaries)
        self.assertIn("-AcceptUnsignedPreview", binaries)
        self.assertIn("PYTHONIOENCODING=cp1252", binaries)
        self.assertIn("subject-checksums: dist-artifacts/SHA256SUMS", binaries)
        self.assertIn("id: release_draft", binaries)
        self.assertIn("draft: true", binaries)
        self.assertIn("fail_on_unmatched_files: true", binaries)
        self.assertIn("Verify draft assets before immutable publication", binaries)
        self.assertIn("diff -u expected-assets.txt uploaded-assets.txt", binaries)
        self.assertIn("Publish verified immutable release", binaries)
        self.assertIn("gh api --method PATCH", binaries)
        self.assertLess(
            binaries.index("Create draft and upload GitHub release assets"),
            binaries.index("Verify draft assets before immutable publication"),
        )
        self.assertLess(
            binaries.index("Verify draft assets before immutable publication"),
            binaries.index("Publish verified immutable release"),
        )
        self.assertIn('"schema": "aipg-validator-release-v1"', binaries)
        self.assertIn('"commit": os.environ["RELEASE_COMMIT"]', binaries)
        self.assertIn('"platform_signing": {', binaries)
        self.assertIn('"release_class": release_class', binaries)
        self.assertIn('"unsigned_warning": unsigned_warning', binaries)
        self.assertIn("UNSIGNED PREVIEW:", binaries)
        self.assertLess(
            (ROOT / "scripts" / "install-binary.sh").read_text().index("prepare-wallet"),
            (ROOT / "scripts" / "install-binary.sh").read_text().index('"  $run_cmd init"'),
        )
        self.assertLess(
            (ROOT / "scripts" / "install-validator.ps1").read_text().index("prepare-wallet"),
            (ROOT / "scripts" / "install-validator.ps1").read_text().index(" init"),
        )
        self.assertIn("macOS Developer ID/notarization gate is not satisfied", verifier)
        self.assertIn("Windows Authenticode gate is not satisfied", verifier)
        self.assertIn('"validator-release.json"', binaries)
        self.assertIn("dist-artifacts/validator-release.json", binaries)
        self.assertIn("EXPECTED_RELEASE_COMMIT", binaries)
        self.assertIn("Reverify release identity and payload", binaries)
        self.assertIn("format: spdx-json", binaries)
        self.assertIn("provenance: mode=max", docker)
        self.assertIn("sbom: true", docker)
        self.assertIn("name: Qualify container image", docker)
        self.assertIn("name: Publish protected container image", docker)
        self.assertIn("container publication requires a protected v* tag push", docker)
        self.assertIn("environment: validator-release", docker)
        self.assertIn("push: false", docker)
        self.assertIn("push: true", docker)
        self.assertEqual(docker.count("packages: write"), 1)
        self.assertNotIn("inputs.publish_image", docker)
        self.assertNotIn("inputs.publish_latest", docker)
        self.assertIn("scripts/classify-release-tag.sh", binaries)
        self.assertIn("scripts/classify-release-tag.sh", docker)
        self.assertEqual(docker.count("AIPG_VALIDATOR_RELEASE_TAG="), 3)
        self.assertIn(
            'aipg-validator ${{ needs.validate.outputs.tag }}', docker
        )

    def test_release_asset_verifier_binds_workflow_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_release_payload(root)

            passed = self._run_release_verifier(
                root,
                EXPECTED_RELEASE_TAG="v0.1.0-preview.1",
                EXPECTED_RELEASE_COMMIT="a" * 40,
            )
            self.assertEqual(passed.returncode, 0, passed.stderr)

            failed = self._run_release_verifier(
                root,
                EXPECTED_RELEASE_TAG="v0.1.0-preview.1",
                EXPECTED_RELEASE_COMMIT="b" * 40,
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("workflow source commit", failed.stderr)

    def test_preview_release_accepts_explicit_unsigned_platforms(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_release_payload(root)

            result = self._run_release_verifier(root)

            self.assertEqual(result.returncode, 0, result.stderr)

    def test_preview_release_rejects_missing_unsigned_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_release_payload(root)
            manifest_path = root / "validator-release.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["unsigned_warning"] = None
            self._rewrite_manifest_and_checksums(root, manifest)

            result = self._run_release_verifier(root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("exact unsigned-platform warning", result.stderr)

    def test_preview_release_rejects_misleading_signed_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_release_payload(root)
            manifest_path = root / "validator-release.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["platform_signing"]["windows"] = {
                "verified": True,
                "identity": "authenticode",
                "subject": "CN=Unverified Example",
            }
            self._rewrite_manifest_and_checksums(root, manifest)

            result = self._run_release_verifier(root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must explicitly be unsigned", result.stderr)

    def test_stable_release_rejects_unsigned_platforms(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_release_payload(root, tag="v0.1.0")

            result = self._run_release_verifier(root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Developer ID/notarization gate", result.stderr)

    @staticmethod
    def _rewrite_manifest_and_checksums(root: Path, manifest: dict) -> None:
        manifest_path = root / "validator-release.json"
        manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        checksums_path = root / "SHA256SUMS"
        lines = []
        for line in checksums_path.read_text(encoding="ascii").splitlines():
            _, name = line.split(maxsplit=1)
            path = root / name
            lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {name}")
        checksums_path.write_text("\n".join(lines) + "\n", encoding="ascii")

    def test_release_asset_verifier_rejects_unexpected_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_release_payload(root)
            (root / "unattested.zip").write_bytes(b"not part of the release")

            failed = self._run_release_verifier(root)

            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("release directory mismatch", failed.stderr)

    def test_release_asset_verifier_rejects_symlink_archive_member(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_release_payload(root)
            archive = root / "aipg-validator-linux-x64.zip"
            info = zipfile.ZipInfo("aipg-validator")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr(info, "../../bin/sh")

            manifest_path = root / "validator-release.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for item in manifest["assets"]:
                if item["name"] == archive.name:
                    item["bytes"] = archive.stat().st_size
                    item["sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
            self._rewrite_manifest_and_checksums(root, manifest)

            failed = self._run_release_verifier(root)

            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("unsafe archive member", failed.stderr)


if __name__ == "__main__":
    unittest.main()
