#!/usr/bin/env bash
# Install an AIPG validator systemd service for Linux hosts.
#
# Source checkout:
#   ./scripts/install-systemd.sh --dry-run
#   sudo ./scripts/install-systemd.sh
#
# Released binary:
#   sudo AIPG_VALIDATOR_EXEC="$(command -v aipg-validator)" \
#     ./scripts/install-systemd.sh --workdir /var/lib/aipg-validator --user aipg
set -euo pipefail

SERVICE_NAME="${AIPG_VALIDATOR_SERVICE_NAME:-aipg-validator}"
RUN_USER="${AIPG_VALIDATOR_RUN_USER:-${SUDO_USER:-${USER:-}}}"
EXEC_PATH="${AIPG_VALIDATOR_EXEC:-}"
WORKDIR="${AIPG_VALIDATOR_WORKDIR:-}"
DRY_RUN=0
NO_START=0

die() {
  echo "error: $*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: install-systemd.sh [options]

Options:
  --dry-run          Print the unit without writing or starting anything.
  --no-start         Install the unit but do not enable/start it.
  --name NAME        Service name (default: aipg-validator).
  --user USER        Linux user to run as (default: sudo user/current user).
  --workdir DIR      Directory containing .env (default: checkout or ~/.aipg-validator).
  --exec PATH        aipg-validator executable (default: ./.venv/bin/aipg-validator or PATH).
  -h, --help         Show this help.

Environment alternatives:
  AIPG_VALIDATOR_SERVICE_NAME, AIPG_VALIDATOR_RUN_USER, AIPG_VALIDATOR_WORKDIR,
  AIPG_VALIDATOR_EXEC
EOF
}

abs_path() {
  case "$1" in
    /*) printf '%s\n' "$1" ;;
    *) printf '%s/%s\n' "$PWD" "$1" ;;
  esac
}

shell_quote() {
  printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"
}

user_home() {
  local user="$1"
  if command -v getent >/dev/null 2>&1; then
    getent passwd "$user" | cut -d: -f6
    return
  fi
  printf '%s\n' "${HOME:-}"
}

find_exec() {
  if [ -n "$EXEC_PATH" ]; then
    abs_path "$EXEC_PATH"
    return
  fi
  if [ -x "./.venv/bin/aipg-validator" ]; then
    abs_path "./.venv/bin/aipg-validator"
    return
  fi
  if command -v aipg-validator >/dev/null 2>&1; then
    command -v aipg-validator
    return
  fi
  die "could not find aipg-validator; pass --exec /path/to/aipg-validator"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --no-start) NO_START=1; shift ;;
    --name) SERVICE_NAME="${2:-}"; shift 2 ;;
    --user) RUN_USER="${2:-}"; shift 2 ;;
    --workdir) WORKDIR="${2:-}"; shift 2 ;;
    --exec) EXEC_PATH="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
done

[ -n "$SERVICE_NAME" ] || die "service name is required"
[ -n "$RUN_USER" ] || die "run user is required"

EXEC_PATH="$(find_exec)"
[ -x "$EXEC_PATH" ] || die "executable is not runnable: $EXEC_PATH"

if [ -z "$WORKDIR" ]; then
  if [ -f ".env" ]; then
    WORKDIR="$PWD"
  else
    home="$(user_home "$RUN_USER")"
    [ -n "$home" ] || die "could not determine home for $RUN_USER; pass --workdir"
    WORKDIR="$home/.aipg-validator"
  fi
fi
WORKDIR="$(abs_path "$WORKDIR")"

unit_path="/etc/systemd/system/${SERVICE_NAME}.service"
env_path="$WORKDIR/.env"

unit="$(cat <<EOF
[Unit]
Description=AIPG Validator Node
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$WORKDIR
ExecStart=$EXEC_PATH run
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1
Environment=VALIDATOR_ENV=$env_path
Environment=VALIDATOR_STATE_DB=$WORKDIR/state.sqlite3
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=read-only
ReadWritePaths=$WORKDIR

[Install]
WantedBy=multi-user.target
EOF
)"

if [ "$DRY_RUN" -eq 1 ]; then
  echo "# Would write: $unit_path"
  printf '%s\n' "$unit"
  if [ ! -f "$env_path" ]; then
    echo
    echo "# Note: $env_path does not exist yet."
    echo "# Run: cd $(shell_quote "$WORKDIR") && $(shell_quote "$EXEC_PATH") enroll"
  fi
  exit 0
fi

[ "$(id -u)" -eq 0 ] || die "run with sudo/root to write $unit_path"
command -v systemctl >/dev/null 2>&1 || die "systemctl not found"
id "$RUN_USER" >/dev/null 2>&1 || die "user does not exist: $RUN_USER"

mkdir -p "$WORKDIR"
chown "$RUN_USER:" "$WORKDIR"
chmod 0700 "$WORKDIR"

if [ ! -f "$env_path" ]; then
  echo "No $env_path found."
  echo "Run this before starting the service:"
  echo "  cd $(shell_quote "$WORKDIR") && $(shell_quote "$EXEC_PATH") enroll"
  NO_START=1
else
  chown "$RUN_USER:" "$env_path"
  chmod 0600 "$env_path"
fi

printf '%s\n' "$unit" > "$unit_path"
chmod 0644 "$unit_path"
systemctl daemon-reload

if [ "$NO_START" -eq 1 ]; then
  echo "Installed $unit_path. Service not started."
  echo "After .env exists: sudo systemctl enable --now $SERVICE_NAME"
else
  systemctl enable --now "$SERVICE_NAME"
  echo "Installed and started $SERVICE_NAME."
fi
echo "Logs: journalctl -u $SERVICE_NAME -f"
