import os
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "classify-release-tag.sh"


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


if __name__ == "__main__":
    unittest.main()
