import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReleasePackagingTests(unittest.TestCase):
    def test_docker_image_uses_frozen_lock_and_non_root_runtime(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        from_lines = [line for line in dockerfile.splitlines() if line.startswith("FROM ")]

        self.assertEqual(len(from_lines), 2)
        for line in from_lines:
            self.assertRegex(line, r"@sha256:[0-9a-f]{64}")
        self.assertIn("COPY pyproject.toml uv.lock README.md ./", dockerfile)
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

    def test_release_workflows_enforce_locked_signed_artifacts(self):
        binaries = (ROOT / ".github" / "workflows" / "release-binaries.yml").read_text(
            encoding="utf-8"
        )
        docker = (ROOT / ".github" / "workflows" / "docker.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("uv sync --frozen --extra release", binaries)
        self.assertIn("uv run --frozen --extra release pyinstaller", binaries)
        self.assertIn("PYTHONIOENCODING=cp1252", binaries)
        self.assertIn("subject-checksums: dist-artifacts/SHA256SUMS", binaries)
        self.assertIn("format: spdx-json", binaries)
        self.assertIn("provenance: mode=max", docker)
        self.assertIn("sbom: true", docker)
        self.assertIn("scripts/classify-release-tag.sh", binaries)
        self.assertIn("scripts/classify-release-tag.sh", docker)


if __name__ == "__main__":
    unittest.main()
