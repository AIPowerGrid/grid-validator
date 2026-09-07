#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Build an isolated version fixture and test the real frozen app handoff."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def build(fixture: Path, number: int) -> Path:
    from validator.update_process import stop_owned

    tag = f"v0.1.0-preview.{number}"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/stamp-release-tag.py"),
            tag,
            "--root",
            str(fixture),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        timeout=20,
    )
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--collect-data",
        "validator",
        "--collect-data",
        "sigstore",
        "--hidden-import",
        "sigstore._store",
        "--paths",
        str(fixture),
        "--name",
        "aipg-validator",
        "--distpath",
        str(fixture / f"dist-{number}"),
        "--workpath",
        str(fixture / "build"),
        "--specpath",
        str(fixture),
        str(fixture / "validator/__main__.py"),
    ]
    options = (
        {"creationflags": subprocess.CREATE_NO_WINDOW}
        if os.name == "nt"
        else {"start_new_session": True}
    )
    with (fixture / f"build-{number}.log").open("wb") as output:
        process = subprocess.Popen(
            command, cwd=fixture, stdout=output, stderr=subprocess.STDOUT, **options
        )
        try:
            if process.wait(timeout=300) != 0:
                raise RuntimeError("Native handoff fixture build failed")
        finally:
            stop_owned(process)
    binary = (
        fixture
        / f"dist-{number}"
        / ("aipg-validator.exe" if os.name == "nt" else "aipg-validator")
    )
    result = subprocess.run(
        [str(binary), "--version"],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    if result.stdout.strip() != "aipg-validator " + tag:
        raise RuntimeError("Fixture build did not retain its exact version")
    return binary


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="aipg-update-handoff-") as temporary:
        fixture = Path(temporary)
        shutil.copytree(
            ROOT / "validator",
            fixture / "validator",
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        shutil.copyfile(ROOT / "pyproject.toml", fixture / "pyproject.toml")
        env = os.environ.copy()
        env["TEST_VALIDATOR_BOOTSTRAP_BINARY"] = str(build(fixture, 0))
        env["TEST_VALIDATOR_UPDATE_BINARY"] = str(build(fixture, 17))
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "tests.test_update_handoff_native"],
            cwd=ROOT,
            env=env,
            timeout=180,
        )
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
