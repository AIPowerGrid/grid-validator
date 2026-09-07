# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Authenticate an update manifest before downloading or executing its payload.

Run verification in the updater's killable child: Sigstore refreshes its pinned
TUF trust roots and may perform network I/O. This module never installs updates.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from .update_check import _version_key

REPOSITORY = "https://github.com/AIPowerGrid/grid-validator"
WORKFLOW = ".github/workflows/release-binaries.yml"
MANIFEST_LIMIT = 16 * 1024
ATTESTATION_LIMIT = 2 * 1024 * 1024
ARCHIVE_LIMIT = 512 * 1024 * 1024
PLATFORMS = {
    "linux-x64": "aipg-validator-linux-x64.zip",
    "linux-arm64": "aipg-validator-linux-arm64.zip",
    "macos-arm64": "aipg-validator-macos-arm64.zip",
    "windows-x64": "aipg-validator-windows-x64.zip",
}
PAYLOADS = set(PLATFORMS.values()) | {
    "aipg-validator-release.spdx.json",
    "install-validator.sh",
    "install-validator.ps1",
}
UNSIGNED_WARNING = (
    "UNSIGNED PREVIEW: macOS is not Developer ID signed or notarized; Windows is "
    "not Authenticode signed. Verify SHA256SUMS and GitHub provenance before running."
)


class ReleaseVerificationError(ValueError):
    """A fixed error code, safe to display without echoing untrusted input."""


@dataclass(frozen=True)
class VerifiedRelease:
    tag: str
    commit: str
    platform: str
    archive: str
    size: int
    sha256: str
    manifest_sha256: str
    unsigned_preview: bool


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReleaseVerificationError("ambiguous_release_metadata")
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise ReleaseVerificationError("invalid_release_metadata")


def _json(raw: bytes, limit: int) -> dict[str, Any]:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= limit:
        raise ReleaseVerificationError("release_metadata_size")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
        if not isinstance(value, dict):
            raise ReleaseVerificationError("invalid_release_metadata")
        pending = [(value, 0)]
        while pending:
            item, depth = pending.pop()
            if depth > 32:
                raise ReleaseVerificationError("release_metadata_depth")
            if isinstance(item, dict):
                pending.extend((child, depth + 1) for child in item.values())
            elif isinstance(item, list):
                pending.extend((child, depth + 1) for child in item)
        return value
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ReleaseVerificationError("invalid_release_metadata") from exc


def _platform_signing(manifest: dict[str, Any], preview: bool) -> None:
    signing = manifest.get("platform_signing")
    if not isinstance(signing, dict) or set(signing) != {"macos", "windows"}:
        raise ReleaseVerificationError("invalid_platform_signing")
    mac, win = signing["macos"], signing["windows"]
    if not isinstance(mac, dict) or not isinstance(win, dict):
        raise ReleaseVerificationError("invalid_platform_signing")
    if preview:
        valid = (
            mac
            == {
                "identity": "unsigned",
                "notarized": False,
                "team_id": None,
                "verified": False,
            }
            and win == {"identity": "unsigned", "subject": None, "verified": False}
            and manifest.get("unsigned_warning") == UNSIGNED_WARNING
            and mac.get("verified") is False
            and mac.get("notarized") is False
            and win.get("verified") is False
        )
    else:
        valid = (
            mac.get("identity") == "developer_id_application"
            and mac.get("verified") is True
            and mac.get("notarized") is True
            and isinstance(mac.get("team_id"), str)
            and bool(mac["team_id"])
            and win.get("identity") == "authenticode"
            and win.get("verified") is True
            and isinstance(win.get("subject"), str)
            and bool(win["subject"])
            and manifest.get("unsigned_warning") is None
        )
    if not valid:
        raise ReleaseVerificationError("platform_signing_policy")


def _verify_dsse(bundle: dict[str, Any], identity: str) -> dict[str, Any]:
    # Never accept decoded DSSE alone: verification checks the certificate,
    # workflow identity, signature and transparency-log inclusion first.
    try:
        from sigstore.models import Bundle
        from sigstore.verify import Verifier, policy

        content_type, payload = Verifier.production().verify_dsse(
            Bundle.from_json(json.dumps(bundle)),
            policy.Identity(
                identity=identity, issuer="https://token.actions.githubusercontent.com"
            ),
        )
        if content_type != "application/vnd.in-toto+json":
            raise ReleaseVerificationError("invalid_provenance_type")
        return _json(payload, ATTESTATION_LIMIT)
    except Exception as exc:
        # Third-party failures may contain URLs or certificate/response data.
        raise ReleaseVerificationError("provenance_verification_failed") from exc


def _bind_statement(
    statement: dict[str, Any], tag: str, commit: str, digest: str
) -> bool:
    try:
        definition = statement["predicate"]["buildDefinition"]
        workflow = definition["externalParameters"]["workflow"]
        github = definition["internalParameters"]["github"]
        expected_identity = f"{REPOSITORY}/{WORKFLOW}@refs/tags/{tag}"
        subjects = statement["subject"]
        matches = [
            item for item in subjects if item.get("name") == "validator-release.json"
        ]
        return bool(
            statement["_type"] == "https://in-toto.io/Statement/v1"
            and statement["predicateType"] == "https://slsa.dev/provenance/v1"
            and len(matches) == 1
            and matches[0]["digest"] == {"sha256": digest}
            and definition["buildType"]
            == "https://actions.github.io/buildtypes/workflow/v1"
            and workflow
            == {"ref": f"refs/tags/{tag}", "repository": REPOSITORY, "path": WORKFLOW}
            and github["event_name"] == "push"
            and github["runner_environment"] == "github-hosted"
            and github["repository_id"] == "1268894731"
            and github["repository_owner_id"] == "150180242"
            and definition["resolvedDependencies"]
            == [
                {
                    "uri": f"git+{REPOSITORY}@refs/tags/{tag}",
                    "digest": {"gitCommit": commit},
                }
            ]
            and statement["predicate"]["runDetails"]["builder"]["id"]
            == expected_identity
        )
    except (KeyError, TypeError, AttributeError):
        return False


def verify_release(
    manifest_bytes: bytes, attestations_bytes: bytes, *, tag: str, platform: str
) -> VerifiedRelease:
    """Verify a pinned target. Selection/anti-downgrade and install are separate."""
    key = _version_key(tag)
    if key is None or not isinstance(platform, str) or platform not in PLATFORMS:
        raise ReleaseVerificationError("invalid_update_target")
    manifest = _json(manifest_bytes, MANIFEST_LIMIT)
    preview = not bool(key[3])
    commit = manifest.get("commit")
    if (
        manifest.get("schema") != "aipg-validator-release-v1"
        or manifest.get("tag") != tag
        or manifest.get("version") != tag[1:].split("-", 1)[0]
        or manifest.get("release_class") != ("preview" if preview else "stable")
        or not isinstance(commit, str)
        or re.fullmatch(r"[0-9a-f]{40}", commit) is None
    ):
        raise ReleaseVerificationError("manifest_identity_mismatch")
    _platform_signing(manifest, preview)
    assets = manifest.get("assets")
    if not isinstance(assets, list) or len(assets) != len(PAYLOADS):
        raise ReleaseVerificationError("invalid_release_assets")
    by_name: dict[str, dict[str, Any]] = {}
    for item in assets:
        if not isinstance(item, dict) or set(item) != {"name", "bytes", "sha256"}:
            raise ReleaseVerificationError("invalid_release_assets")
        name, size, digest = item["name"], item["bytes"], item["sha256"]
        if (
            not isinstance(name, str)
            or name not in PAYLOADS
            or name in by_name
            or type(size) is not int
            or not 0 < size <= ARCHIVE_LIMIT
            or not isinstance(digest, str)
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
        ):
            raise ReleaseVerificationError("invalid_release_assets")
        by_name[name] = item
    digest = hashlib.sha256(manifest_bytes).hexdigest()
    attestations = _json(attestations_bytes, ATTESTATION_LIMIT).get("attestations")
    if not isinstance(attestations, list) or not 0 < len(attestations) <= 4:
        raise ReleaseVerificationError("invalid_attestation_list")
    identity = f"{REPOSITORY}/{WORKFLOW}@refs/tags/{tag}"
    for attestation in attestations:
        if not isinstance(attestation, dict) or not isinstance(
            attestation.get("bundle"), dict
        ):
            continue
        try:
            statement = _verify_dsse(attestation["bundle"], identity)
        except ReleaseVerificationError:
            continue
        if _bind_statement(statement, tag, commit, digest):
            asset = by_name[PLATFORMS[platform]]
            return VerifiedRelease(
                tag,
                commit,
                platform,
                asset["name"],
                asset["bytes"],
                asset["sha256"],
                digest,
                preview,
            )
    raise ReleaseVerificationError("release_provenance_not_verified")
