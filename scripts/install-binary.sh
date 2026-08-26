#!/usr/bin/env bash
# Install the pinned AIPG validator preview binary from GitHub Releases.
#
# Released installer form:
#   AIPG_VALIDATOR_VERSION=v0.1.0-preview.2 bash install-validator.sh
#
# Checkout/dev form:
#   ./scripts/install-binary.sh
set -euo pipefail

REPO="${AIPG_VALIDATOR_REPO:-AIPowerGrid/grid-validator}"
VERSION="${AIPG_VALIDATOR_VERSION:-v0.1.0-preview.2}"
INSTALL_DIR="${AIPG_VALIDATOR_INSTALL_DIR:-$HOME/.local/bin}"
BINARY_NAME="${AIPG_VALIDATOR_BINARY_NAME:-aipg-validator}"
ASSET_URL="${AIPG_VALIDATOR_URL:-}"
CHECKSUMS_URL="${AIPG_VALIDATOR_CHECKSUMS_URL:-}"
CONFIG_DIR="${AIPG_VALIDATOR_CONFIG_DIR:-$HOME/.aipg-validator}"

die() {
  echo "error: $*" >&2
  exit 1
}

need() {
  command -v "$1" >/dev/null 2>&1 || die "$1 is required"
}

shell_quote() {
  printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"
}

detect_platform() {
  local os arch
  case "$(uname -s)" in
    Linux) os="linux" ;;
    Darwin) os="macos" ;;
    MINGW*|MSYS*|CYGWIN*) os="windows" ;;
    *) die "unsupported OS: $(uname -s)" ;;
  esac

  case "$(uname -m)" in
    x86_64|amd64) arch="x64" ;;
    arm64|aarch64) arch="arm64" ;;
    *) die "unsupported architecture: $(uname -m)" ;;
  esac

  if [ "$os" = "windows" ] && [ "$arch" != "x64" ]; then
    die "windows arm64 binary is not published yet"
  fi

  printf '%s-%s' "$os" "$arch"
}

download() {
  local url="$1" out="$2"
  case "$url" in
    file://*)
      cp "${url#file://}" "$out"
      return
      ;;
    /*|./*|../*)
      cp "$url" "$out"
      return
      ;;
  esac
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$url" -o "$out"
    return
  fi
  if command -v wget >/dev/null 2>&1; then
    wget -qO "$out" "$url"
    return
  fi
  die "curl or wget is required"
}

extract_zip() {
  local zip="$1" dest="$2"
  if command -v unzip >/dev/null 2>&1; then
    unzip -q "$zip" -d "$dest"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 -m zipfile -e "$zip" "$dest"
    return
  fi
  die "unzip or python3 is required"
}

sha256_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
    return
  fi
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
    return
  fi
  die "sha256sum or shasum is required to verify the release"
}

platform="$(detect_platform)"
asset="aipg-validator-${platform}.zip"
if [ "$VERSION" = "latest" ]; then
  url="https://github.com/${REPO}/releases/latest/download/${asset}"
  checksums_url="https://github.com/${REPO}/releases/latest/download/SHA256SUMS"
else
  url="https://github.com/${REPO}/releases/download/${VERSION}/${asset}"
  checksums_url="https://github.com/${REPO}/releases/download/${VERSION}/SHA256SUMS"
fi
if [ -n "$ASSET_URL" ]; then
  url="$ASSET_URL"
fi
if [ -n "$CHECKSUMS_URL" ]; then
  checksums_url="$CHECKSUMS_URL"
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

echo "Installing AIPG validator (${platform}) from ${REPO} ${VERSION}..."
download "$url" "$tmp/$asset"
download "$checksums_url" "$tmp/SHA256SUMS"
expected="$(awk -v asset="$asset" '$2 == asset || $2 == "*" asset {print $1; exit}' "$tmp/SHA256SUMS")"
[ -n "$expected" ] || die "SHA256SUMS does not contain $asset"
actual="$(sha256_file "$tmp/$asset")"
[ "$actual" = "$expected" ] || die "checksum mismatch for $asset"
echo "Verified SHA-256: $actual"
extract_zip "$tmp/$asset" "$tmp/extract"

binary="$tmp/extract/aipg-validator"
if [ "$platform" = "windows-x64" ]; then
  binary="$tmp/extract/aipg-validator.exe"
fi
[ -f "$binary" ] || die "release archive did not contain $(basename "$binary")"

mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"
chmod 0700 "$CONFIG_DIR" 2>/dev/null || true
target="$INSTALL_DIR/$BINARY_NAME"
if [ "$platform" = "windows-x64" ] && [[ "$target" != *.exe ]]; then
  target="${target}.exe"
fi

cp "$binary" "$target"
chmod 0755 "$target" 2>/dev/null || true
"$target" --help >/dev/null

echo "Installed: $target"
run_cmd="$BINARY_NAME"
case ":$PATH:" in
  *":$INSTALL_DIR:"*) ;;
  *)
    echo "Note: $INSTALL_DIR is not on PATH."
    echo "Add it, or run the validator with: $target"
    run_cmd="$(shell_quote "$target")"
    ;;
esac
echo
echo "Next steps:"
echo "  cd $(shell_quote "$CONFIG_DIR")"
echo "  $run_cmd init"
echo "  $run_cmd check --no-probe"
echo "  $run_cmd dashboard"
echo "  $run_cmd run"
