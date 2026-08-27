#!/usr/bin/env python3
"""Stamp packaged validator installers with their immutable release tag."""

from __future__ import annotations

import argparse
import pathlib
import re


PLACEHOLDER = "__AIPG_VALIDATOR_RELEASE_TAG__"
TAG_PATTERN = re.compile(
    r"v[0-9]+\.[0-9]+\.[0-9]+(?:-(?:preview|alpha|beta|rc)(?:\.[0-9]+)?)?"
)
INSTALLERS = ("install-validator.sh", "install-validator.ps1")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tag")
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path("dist-artifacts"))
    args = parser.parse_args()

    if not TAG_PATTERN.fullmatch(args.tag):
        raise SystemExit("release installer tag is invalid")

    for name in INSTALLERS:
        path = args.root / name
        body = path.read_text(encoding="utf-8")
        if body.count(PLACEHOLDER) != 1:
            raise SystemExit(f"{name} must contain the release-tag placeholder exactly once")
        path.write_text(body.replace(PLACEHOLDER, args.tag), encoding="utf-8")


if __name__ == "__main__":
    main()
