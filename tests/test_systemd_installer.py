import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SystemdInstallerTests(unittest.TestCase):
    def test_dry_run_unit_keeps_env_private_and_hardened(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake_exec = tmp_path / "aipg-validator"
            workdir = tmp_path / "validator-state"
            fake_exec.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake_exec.chmod(fake_exec.stat().st_mode | stat.S_IXUSR)

            result = subprocess.run(
                [
                    str(ROOT / "scripts" / "install-systemd.sh"),
                    "--dry-run",
                    "--exec",
                    str(fake_exec),
                    "--workdir",
                    str(workdir),
                    "--user",
                    "aipg-test",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        unit = result.stdout
        self.assertIn(f"WorkingDirectory={workdir}", unit)
        self.assertIn(f"ExecStart={fake_exec} run", unit)
        self.assertIn(f"Environment=VALIDATOR_ENV={workdir / '.env'}", unit)
        self.assertIn("UMask=0077", unit)
        self.assertIn("NoNewPrivileges=true", unit)
        self.assertIn("PrivateTmp=true", unit)
        self.assertIn("ProtectSystem=full", unit)
        self.assertIn("ProtectHome=read-only", unit)
        self.assertIn(" init", unit)


if __name__ == "__main__":
    unittest.main()
