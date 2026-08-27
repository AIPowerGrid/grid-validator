#!/usr/bin/env bash
# AIPG Validator Node - source-checkout installer.
# Run from a cloned checkout:
#   ./install.sh
#
# Public binary installs use scripts/install-binary.sh or the hosted
# get.aipowergrid.io/validator installer once release artifacts exist.
set -euo pipefail

cd "$(dirname "$0")"
echo "Setting up the AIPG validator node..."

command -v python3 >/dev/null || { echo "ERROR python3 not found. Install Python 3.10+ and retry."; exit 1; }
python3 - <<'PY'
import sys

if sys.version_info < (3, 10):
    print("ERROR Python 3.10+ is required. Found %s.%s." % sys.version_info[:2])
    raise SystemExit(1)
PY

python3 -m venv .venv
./.venv/bin/python -m pip -q install --upgrade pip
./.venv/bin/python -m pip -q install -e .
echo "OK Dependencies installed."

if [ ! -f .env ]; then
  echo "INFO No validator identity found. Prepare one locally before Console enrollment:"
  echo "   ./.venv/bin/aipg-validator prepare-wallet"
else
  echo "INFO .env already exists - preserving it."
fi

echo
echo "Next steps:"
echo "  ./.venv/bin/aipg-validator prepare-wallet    # local signing identity"
echo "  Link the printed address and create a validator key in the Console"
echo "  ./.venv/bin/aipg-validator init              # add the scoped API key"
echo "  ./.venv/bin/aipg-validator check --no-probe  # verify install + API"
echo "  ./.venv/bin/aipg-validator dashboard         # local status page"
echo "  ./.venv/bin/aipg-validator run               # start validating"
echo "  (or install the systemd service - see OPERATORS.md)"
