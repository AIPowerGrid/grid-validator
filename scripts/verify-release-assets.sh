#!/usr/bin/env bash
# Verify the complete validator binary-release payload before publication.
set -euo pipefail

DIR="${1:-dist-artifacts}"

die() {
  echo "error: $*" >&2
  exit 1
}

[ -d "$DIR" ] || die "release directory not found: $DIR"

payloads=(
  aipg-validator-linux-x64.zip
  aipg-validator-linux-arm64.zip
  aipg-validator-macos-arm64.zip
  aipg-validator-windows-x64.zip
  aipg-validator-release.spdx.json
  install-validator.sh
  install-validator.ps1
)
checksummed=( "${payloads[@]}" validator-release.json )

for file in "${checksummed[@]}" SHA256SUMS; do
  [ -f "$DIR/$file" ] || die "missing release asset: $file"
done

python3 - "$DIR" "${payloads[@]}" <<'PY'
import hashlib
import json
import os
import pathlib
import re
import stat
import sys
import zipfile

root = pathlib.Path(sys.argv[1])
payloads = sys.argv[2:]
checksummed = [*payloads, "validator-release.json"]
expected_files = {*checksummed, "SHA256SUMS"}
actual_files = {path.name for path in root.iterdir()}
if actual_files != expected_files:
    missing = sorted(expected_files - actual_files)
    extra = sorted(actual_files - expected_files)
    raise SystemExit(f"release directory mismatch: missing={missing} extra={extra}")
if not all(
    (root / name).is_file() and not (root / name).is_symlink()
    for name in expected_files
):
    raise SystemExit("release payload entries must all be regular files")
entries = {}
for raw in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
    parts = raw.split(maxsplit=1)
    if len(parts) != 2:
        raise SystemExit(f"invalid SHA256SUMS line: {raw!r}")
    digest, name = parts
    name = name.lstrip("*")
    if name in entries:
        raise SystemExit(f"duplicate SHA256SUMS entry: {name}")
    entries[name] = digest.lower()

if set(entries) != set(checksummed):
    missing = sorted(set(checksummed) - set(entries))
    extra = sorted(set(entries) - set(checksummed))
    raise SystemExit(f"SHA256SUMS payload mismatch: missing={missing} extra={extra}")

for name in checksummed:
    actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
    if actual != entries[name]:
        raise SystemExit(f"checksum mismatch: {name}")

manifest = json.loads((root / "validator-release.json").read_text(encoding="utf-8"))
if manifest.get("schema") != "aipg-validator-release-v1":
    raise SystemExit("release manifest schema is invalid")
version = str(manifest.get("version") or "")
tag = str(manifest.get("tag") or "")
if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
    raise SystemExit("release version is invalid")
if tag and not re.fullmatch(
    rf"v{re.escape(version)}(?:-(?:preview|alpha|beta|rc)(?:\.[0-9]+)?)?",
    tag,
):
    raise SystemExit("release tag does not match version")
stable_tag = bool(tag and re.fullmatch(rf"v{re.escape(version)}", tag))
preview_tag = bool(tag and not stable_tag)
expected_release_class = "stable" if stable_tag else "preview" if preview_tag else "build"
if manifest.get("release_class") != expected_release_class:
    raise SystemExit("release manifest class does not match tag")
if not re.fullmatch(r"[0-9a-f]{40}", str(manifest.get("commit") or "")):
    raise SystemExit("release commit is invalid")
expected_tag = os.environ.get("EXPECTED_RELEASE_TAG")
if expected_tag is not None and tag != expected_tag:
    raise SystemExit("release tag does not match the workflow release tag")
expected_commit = os.environ.get("EXPECTED_RELEASE_COMMIT")
if expected_commit is not None and manifest.get("commit") != expected_commit:
    raise SystemExit("release commit does not match the workflow source commit")
signing = manifest.get("platform_signing")
if not isinstance(signing, dict) or set(signing) != {"macos", "windows"}:
    raise SystemExit("release platform-signing state is invalid")
macos = signing.get("macos")
windows = signing.get("windows")
if (
    not isinstance(macos, dict)
    or set(macos) != {"verified", "identity", "notarized", "team_id"}
    or not isinstance(macos.get("verified"), bool)
    or not isinstance(macos.get("notarized"), bool)
    or not isinstance(macos.get("identity"), str)
    or (macos.get("team_id") is not None and not isinstance(macos["team_id"], str))
):
    raise SystemExit("macOS signing state is invalid")
if (
    not isinstance(windows, dict)
    or set(windows) != {"verified", "identity", "subject"}
    or not isinstance(windows.get("verified"), bool)
    or not isinstance(windows.get("identity"), str)
    or (
        windows.get("subject") is not None
        and not isinstance(windows["subject"], str)
    )
):
    raise SystemExit("Windows signing state is invalid")
unsigned_warning = manifest.get("unsigned_warning")
expected_unsigned_warning = (
    "UNSIGNED PREVIEW: macOS is not Developer ID signed or notarized; Windows is "
    "not Authenticode signed. Verify SHA256SUMS and GitHub provenance before running."
)
macos_signed = (
    macos.get("verified") is True
    and macos.get("identity") == "developer_id_application"
    and macos.get("notarized") is True
    and isinstance(macos.get("team_id"), str)
    and bool(macos["team_id"])
)
windows_signed = (
    windows.get("verified") is True
    and windows.get("identity") == "authenticode"
    and isinstance(windows.get("subject"), str)
    and bool(windows["subject"])
)
if stable_tag:
    if unsigned_warning is not None:
        raise SystemExit("stable release must not carry an unsigned-preview warning")
    if not macos_signed:
        raise SystemExit("macOS Developer ID/notarization gate is not satisfied")
    if not windows_signed:
        raise SystemExit("Windows Authenticode gate is not satisfied")
elif preview_tag:
    if unsigned_warning != expected_unsigned_warning:
        raise SystemExit("preview release must carry the exact unsigned-platform warning")
    if not (
        macos.get("verified") is False
        and macos.get("identity") == "unsigned"
        and macos.get("notarized") is False
        and macos.get("team_id") is None
    ):
        raise SystemExit("preview macOS signing state must explicitly be unsigned")
    if not (
        windows.get("verified") is False
        and windows.get("identity") == "unsigned"
        and windows.get("subject") is None
    ):
        raise SystemExit("preview Windows signing state must explicitly be unsigned")
assets = manifest.get("assets")
asset_names = [item.get("name") for item in assets] if isinstance(assets, list) else []
if (
    not isinstance(assets, list)
    or len(assets) != len(payloads)
    or not all(isinstance(item, dict) for item in assets)
    or len(asset_names) != len(set(asset_names))
    or set(asset_names) != set(payloads)
):
    raise SystemExit("release manifest asset list is invalid")
for item in assets:
    if set(item) != {"name", "sha256", "bytes"}:
        raise SystemExit("release manifest asset entry is invalid")
    if not isinstance(item["bytes"], int) or item["bytes"] <= 0:
        raise SystemExit(f"release manifest size is invalid: {item['name']}")
    if not re.fullmatch(r"[0-9a-f]{64}", str(item["sha256"])):
        raise SystemExit(f"release manifest checksum is invalid: {item['name']}")
    path = root / item["name"]
    if item.get("bytes") != path.stat().st_size:
        raise SystemExit(f"release manifest size mismatch: {path.name}")
    if item.get("sha256") != hashlib.sha256(path.read_bytes()).hexdigest():
        raise SystemExit(f"release manifest checksum mismatch: {path.name}")

archives = {
    "aipg-validator-linux-x64.zip": "aipg-validator",
    "aipg-validator-linux-arm64.zip": "aipg-validator",
    "aipg-validator-macos-arm64.zip": "aipg-validator",
    "aipg-validator-windows-x64.zip": "aipg-validator.exe",
}
for archive, expected in archives.items():
    with zipfile.ZipFile(root / archive) as bundle:
        members = bundle.infolist()
        names = [item.filename for item in members]
        if names != [expected]:
            raise SystemExit(f"unexpected archive payload for {archive}: {names}")
        member = members[0]
        mode = (member.external_attr >> 16) & 0xFFFF
        if member.is_dir() or stat.S_ISLNK(mode):
            raise SystemExit(f"unsafe archive member for {archive}: {member.filename}")
        if mode and not stat.S_ISREG(mode):
            raise SystemExit(f"non-regular archive member for {archive}: {member.filename}")
        if member.flag_bits & 0x1:
            raise SystemExit(f"encrypted archive member for {archive}: {member.filename}")
        if not 0 < member.file_size <= 512 * 1024 * 1024:
            raise SystemExit(f"archive member size is invalid for {archive}")
        if member.compress_size and member.file_size > member.compress_size * 100:
            raise SystemExit(f"archive compression ratio is unsafe for {archive}")

sbom = json.loads((root / "aipg-validator-release.spdx.json").read_text(encoding="utf-8"))
if not str(sbom.get("spdxVersion", "")).startswith("SPDX-"):
    raise SystemExit("release SBOM is not SPDX JSON")
power_shell = (root / "install-validator.ps1").read_text(encoding="utf-8")
if not power_shell.startswith("# SPDX-") or "AcceptUnsignedPreview" not in power_shell:
    raise SystemExit("PowerShell installer is missing its preview safety contract")
shell_installer = (root / "install-validator.sh").read_text(encoding="utf-8")
installer_placeholder = "__AIPG_VALIDATOR_RELEASE_TAG__"
for name, body in (
    ("shell", shell_installer),
    ("PowerShell", power_shell),
):
    if tag:
        if installer_placeholder in body or body.count(tag) != 1:
            raise SystemExit(f"{name} installer is not stamped with the release tag")
    elif body.count(installer_placeholder) != 1:
        raise SystemExit(f"build-only {name} installer must retain its tag placeholder")
for name, body in (("shell", shell_installer), ("PowerShell", power_shell)):
    prepare = body.find("prepare-wallet")
    initialize = body.find(" init")
    if prepare < 0 or initialize < 0 or prepare > initialize:
        raise SystemExit(
            f"{name} installer must direct operators to prepare-wallet before init"
        )
PY

bash -n "$DIR/install-validator.sh"
echo "Verified validator release payload in $DIR"
