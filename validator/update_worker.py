# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Private updater subprocess protocol. No credentials or runtime Settings."""

from __future__ import annotations

import asyncio
import json
import platform
import sys
from dataclasses import asdict
from importlib import resources
from pathlib import Path
from typing import Any

from . import __release_tag__
from .release_verify import ReleaseVerificationError, _json


def native_platform() -> str:
    machine = platform.machine().lower()
    arch = {"amd64": "x64", "x86_64": "x64", "aarch64": "arm64", "arm64": "arm64"}.get(
        machine
    )
    system = {"linux": "linux", "darwin": "macos", "win32": "windows"}.get(sys.platform)
    value = f"{system}-{arch}"
    if value not in {"linux-x64", "linux-arm64", "macos-arm64", "windows-x64"}:
        raise ReleaseVerificationError("unsupported_update_platform")
    return value


def self_test() -> dict[str, Any]:
    """Offline startup proof, including packaged trust roots and app assets."""
    try:
        from sigstore.models import TrustedRoot
        from sigstore.verify import Verifier
    except Exception as exc:
        raise ReleaseVerificationError("update_dependencies_missing") from exc
    try:
        # Test the shipped roots, never a previous install's mutable TUF cache.
        store = resources.files("sigstore._store").joinpath(
            "https%3A%2F%2Ftuf-repo-cdn.sigstore.dev"
        )
        for filename in ("root.json", "signing_config.v0.2.json"):
            if not isinstance(json.loads(store.joinpath(filename).read_bytes()), dict):
                raise ValueError("invalid embedded trust data")
        with resources.as_file(store.joinpath("trusted_root.json")) as root:
            Verifier(trusted_root=TrustedRoot.from_file(str(root)))
    except Exception as exc:
        raise ReleaseVerificationError("update_trust_resources_invalid") from exc
    assets = Path(__file__).parent / "ui"
    for filename in ("index.html", "app.js", "app.css", "logo.png"):
        if not (assets / filename).is_file() or (assets / filename).stat().st_size == 0:
            raise ReleaseVerificationError("update_resources_missing")
    return {
        "schema": "aipg.validator.update-health.v1",
        "tag": __release_tag__,
        "platform": native_platform(),
        "ready": True,
    }


def prepare_request(raw: bytes) -> dict[str, Any]:
    from .update_download import prepare_update

    request = _json(raw, 4096)
    if set(request) != {"tag", "root"} or not isinstance(request["root"], str):
        raise ReleaseVerificationError("invalid_update_request")
    root = Path(request["root"])
    if not root.is_absolute():
        raise ReleaseVerificationError("invalid_update_request")
    result = asyncio.run(
        prepare_update(
            root,
            tag=request["tag"],
            current_tag=__release_tag__,
            platform=native_platform(),
        )
    )
    return {
        "schema": "aipg.validator.update-stage.v1",
        "ready": True,
        "directory": str(result.directory),
        "executable": str(result.executable),
        "executable_sha256": result.executable_sha256,
        "release": asdict(result.release),
    }


def main(action: str) -> int:
    try:
        if action == "self-test":
            result = self_test()
        elif action == "prepare":
            result = prepare_request(sys.stdin.buffer.read(4097))
        else:
            raise ReleaseVerificationError("invalid_update_action")
        print(json.dumps(result), flush=True)
        return 0
    except Exception as exc:
        # Third-party errors can contain remote URLs or local paths. Only a
        # fixed failure escapes this process; the controller retains old state.
        code = "update_preparation_failed"
        if isinstance(exc, ReleaseVerificationError) and str(exc) in {
            "update_dependencies_missing",
            "update_trust_resources_invalid",
            "update_resources_missing",
            "unsupported_update_platform",
        }:
            code = str(exc)
        print(
            json.dumps({"ready": False, "error": code}),
            flush=True,
        )
        return 1
