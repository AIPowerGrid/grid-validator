#!/usr/bin/env bash
# AIPG Validator Node — source-checkout installer.
# Run from a cloned checkout:
#   ./install.sh
#
# Public binary installs use scripts/install-binary.sh or the hosted
# get.aipowergrid.io/validator installer once release artifacts exist.
set -euo pipefail

cd "$(dirname "$0")"
echo "▶ Setting up the AIPG validator node..."

command -v python3 >/dev/null || { echo "❌ python3 not found. Install Python 3.10+ and retry."; exit 1; }
python3 - <<'PY'
import sys

if sys.version_info < (3, 10):
    print("❌ Python 3.10+ is required. Found %s.%s." % sys.version_info[:2])
    raise SystemExit(1)
PY

python3 -m venv .venv
./.venv/bin/python -m pip -q install --upgrade pip
./.venv/bin/python -m pip -q install -e .
echo "✅ Dependencies installed."

if [ ! -f .env ]; then
  if [ -t 0 ]; then
    ./.venv/bin/aipg-validator init
  else
    echo "ℹ️  No .env found, and stdin is not interactive — skipping setup."
    echo "   Run this from a terminal when ready: ./.venv/bin/aipg-validator init"
  fi
else
  echo "ℹ️  .env already exists — skipping setup. Edit it or run: ./.venv/bin/aipg-validator init"
fi

echo
echo "Next steps:"
echo "  ./.venv/bin/aipg-validator check --no-probe  # verify install + API"
echo "  ./.venv/bin/aipg-validator dashboard         # local status page"
echo "  ./.venv/bin/aipg-validator run               # start validating"
echo "  (or install the systemd service — see OPERATORS.md)"
