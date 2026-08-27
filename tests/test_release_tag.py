import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "classify-release-tag.sh"
STAMP_SCRIPT = ROOT / "scripts" / "stamp-release-tag.py"


def classify(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=ROOT,
        env=os.environ.copy(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


class ReleaseTagTests(unittest.TestCase):
    def test_stable_tag_can_publish_latest(self):
        result = classify("--publish-latest", "v0.1.0")

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("stable=true", result.stdout)
        self.assertIn("prerelease=false", result.stdout)
        self.assertIn("latest=true", result.stdout)

    def test_preview_tag_is_prerelease(self):
        result = classify("v0.1.0-preview.1")

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("stable=false", result.stdout)
        self.assertIn("prerelease=true", result.stdout)
        self.assertIn("latest=false", result.stdout)

    def test_manual_stable_release_can_be_marked_prerelease(self):
        result = classify("--force-prerelease", "v0.1.0")

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("stable=true", result.stdout)
        self.assertIn("prerelease=true", result.stdout)

    def test_preview_tag_cannot_publish_latest(self):
        result = classify("--publish-latest", "v0.1.0-preview.1")

        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot be published as latest", result.stdout)

    def test_tag_event_policy_only_updates_latest_for_stable_tags(self):
        stable = classify("--publish-latest-if-stable", "v0.1.0")
        preview = classify("--publish-latest-if-stable", "v0.1.0-preview.1")

        self.assertEqual(stable.returncode, 0, stable.stdout)
        self.assertIn("latest=true", stable.stdout)
        self.assertEqual(preview.returncode, 0, preview.stdout)
        self.assertIn("latest=false", preview.stdout)

    def test_invalid_tag_is_rejected(self):
        result = classify("latest")

        self.assertEqual(result.returncode, 1)
        self.assertIn("must look like", result.stdout)

    def test_empty_tag_is_only_allowed_for_build_only_runs(self):
        rejected = classify("")
        allowed = classify("--allow-empty", "")

        self.assertEqual(rejected.returncode, 1)
        self.assertEqual(allowed.returncode, 0, allowed.stdout)
        self.assertIn("publish=false", allowed.stdout)


class ReleaseIdentityStampTests(unittest.TestCase):
    @staticmethod
    def _repo(root: Path, *, version: str = "0.1.0") -> Path:
        (root / "validator").mkdir()
        (root / "pyproject.toml").write_text(
            f'[project]\nname = "aipg-validator"\nversion = "{version}"\n',
            encoding="utf-8",
        )
        init_path = root / "validator" / "__init__.py"
        init_path.write_text(
            '__version__ = "0.1.0"\n__release_tag__ = "v0.1.0-dev"\n',
            encoding="utf-8",
        )
        return init_path

    @staticmethod
    def _stamp(root: Path, tag: str = "") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(STAMP_SCRIPT), "--root", str(root), tag],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

    def test_source_checkout_uses_development_identity(self):
        self.assertEqual(
            (ROOT / "validator" / "__init__.py")
            .read_text(encoding="utf-8")
            .count('__release_tag__ = "v0.1.0-dev"'),
            1,
        )

    def test_empty_tag_stamps_development_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_path = self._repo(root)
            init_path.write_text(
                init_path.read_text(encoding="utf-8").replace(
                    "v0.1.0-dev", "v0.1.0-preview.3"
                ),
                encoding="utf-8",
            )

            result = self._stamp(root)

            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(result.stdout.strip(), "v0.1.0-dev")
            self.assertIn(
                '__release_tag__ = "v0.1.0-dev"',
                init_path.read_text(encoding="utf-8"),
            )

    def test_matching_stable_and_preview_tags_are_stamped(self):
        for tag in ("v0.1.0", "v0.1.0-preview.5", "v0.1.0-rc.1"):
            with self.subTest(tag=tag), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                init_path = self._repo(root)

                result = self._stamp(root, tag)

                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertEqual(result.stdout.strip(), tag)
                self.assertIn(
                    f'__release_tag__ = "{tag}"',
                    init_path.read_text(encoding="utf-8"),
                )

    def test_malformed_or_wrong_version_tag_is_rejected_without_edit(self):
        for tag in ("latest", "v0.2.0-preview.1", "v0.1.0-dev"):
            with self.subTest(tag=tag), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                init_path = self._repo(root)
                before = init_path.read_text(encoding="utf-8")

                result = self._stamp(root, tag)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("does not match package version", result.stdout)
                self.assertEqual(init_path.read_text(encoding="utf-8"), before)

    def test_package_and_project_version_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_path = self._repo(root, version="0.2.0")
            before = init_path.read_text(encoding="utf-8")

            result = self._stamp(root, "v0.2.0-preview.1")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("validator.__version__ must occur once", result.stdout)
            self.assertEqual(init_path.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
