# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Stamp a validated release tag into a validator build checkout."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised by the Python 3.10 CI lane
    import tomli as tomllib


RELEASE_ASSIGNMENT = re.compile(r'^__release_tag__ = "[^"]+"$', re.MULTILINE)
VERSION_ASSIGNMENT = re.compile(r'^__version__ = "([^"]+)"$', re.MULTILINE)


def release_tag(version: str, requested: str) -> str:
    if not requested:
        return f"v{version}-dev"
    pattern = re.compile(
        rf"v{re.escape(version)}(?:-(?:preview|alpha|beta|rc)(?:\.[0-9]+)?)?"
    )
    if not pattern.fullmatch(requested):
        raise ValueError(f"release tag {requested!r} does not match package version {version}")
    return requested


def stamp(root: Path, requested: str) -> str:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    version = str(project["version"])
    tag = release_tag(version, requested)
    init_path = root / "validator" / "__init__.py"
    source = init_path.read_text(encoding="utf-8")
    package_versions = VERSION_ASSIGNMENT.findall(source)
    if package_versions != [version]:
        raise ValueError(
            f"validator.__version__ must occur once and equal project version {version}"
        )
    updated, replacements = RELEASE_ASSIGNMENT.subn(
        f'__release_tag__ = "{tag}"', source
    )
    if replacements != 1:
        raise ValueError(
            f"expected exactly one __release_tag__ assignment in {init_path}"
        )
    init_path.write_text(updated, encoding="utf-8")
    return tag


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stamp a validated Git release tag into validator/__init__.py."
    )
    parser.add_argument(
        "tag",
        nargs="?",
        default="",
        help="validated vX.Y.Z release tag; empty stamps the development identity",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (used by tests and release automation)",
    )
    args = parser.parse_args()
    try:
        tag = stamp(args.root.resolve(), args.tag.strip())
    except (KeyError, OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        parser.error(str(exc))
    print(tag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
