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
)
checksummed=( "${payloads[@]}" validator-release.json )

for file in "${checksummed[@]}" SHA256SUMS; do
  [ -f "$DIR/$file" ] || die "missing release asset: $file"
done

python3 - "$DIR" "${payloads[@]}" <<'PY'
import hashlib
import json
import pathlib
import re
import sys
import zipfile

root = pathlib.Path(sys.argv[1])
payloads = sys.argv[2:]
checksummed = [*payloads, "validator-release.json"]
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
if not re.fullmatch(r"[0-9a-f]{40}", str(manifest.get("commit") or "")):
    raise SystemExit("release commit is invalid")
assets = manifest.get("assets")
if (
    not isinstance(assets, list)
    or not all(isinstance(item, dict) for item in assets)
    or {item.get("name") for item in assets} != set(payloads)
):
    raise SystemExit("release manifest asset list is invalid")
for item in assets:
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
        members = [item.filename for item in bundle.infolist() if not item.is_dir()]
    if members != [expected]:
        raise SystemExit(f"unexpected archive payload for {archive}: {members}")

sbom = json.loads((root / "aipg-validator-release.spdx.json").read_text(encoding="utf-8"))
if not str(sbom.get("spdxVersion", "")).startswith("SPDX-"):
    raise SystemExit("release SBOM is not SPDX JSON")
PY

bash -n "$DIR/install-validator.sh"
echo "Verified validator release payload in $DIR"
