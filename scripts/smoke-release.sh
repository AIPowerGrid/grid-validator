#!/usr/bin/env bash
# End-to-end local release smoke for the validator operator package.
#
# This intentionally uses throwaway config pointing at an offline Grid URL. The
# expected check result is a clean registration failure with no
# traceback/import errors.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -z "${PY:-}" ]; then
  if [ -x "$ROOT/.venv/bin/python" ]; then
    PY="$ROOT/.venv/bin/python"
  else
    PY="$(command -v python3 || command -v python || true)"
  fi
fi
if [ -z "${VALIDATOR:-}" ]; then
  if [ -x "$ROOT/.venv/bin/aipg-validator" ]; then
    VALIDATOR="$ROOT/.venv/bin/aipg-validator"
  else
    VALIDATOR="$(command -v aipg-validator || true)"
  fi
fi
PYINSTALLER="${PYINSTALLER:-}"
IMAGE="${AIPG_VALIDATOR_SMOKE_IMAGE:-aipowergrid/validator:local-smoke}"
SKIP_DOCKER="${SKIP_DOCKER:-0}"
SKIP_BINARY="${SKIP_BINARY:-0}"

die() {
  echo "error: $*" >&2
  exit 1
}

need_file() {
  [ -e "$1" ] || die "missing: $1"
}

status() {
  printf '\n==> %s\n' "$*"
}

write_offline_env() {
  local dest="$1" port="${2:-8791}"
  cat > "$dest" <<EOF
GRID_API_URL=http://127.0.0.1:1
VALIDATOR_API_KEY=grid-key
VALIDATOR_WALLET=0x19e7e376e7c213b7e7e7e46cc70a5dd086daff2a
VALIDATOR_PRIVATE_KEY=0x1111111111111111111111111111111111111111111111111111111111111111
VALIDATOR_REQUIRE_STAKE=false
VALIDATOR_MEDIA_ALLOWED_ORIGINS=https://media.example
PROBE_TIMEOUT_S=1
DASHBOARD_HOST=127.0.0.1
DASHBOARD_PORT=$port
EOF
}

assert_clean_offline_check() {
  local out="$1" code="$2" label="$3"
  if [ "$code" -ne 1 ]; then
    cat "$out" >&2 || true
    die "$label expected offline check to exit 1, got $code"
  fi
  if grep -Ei "Traceback|ModuleNotFoundError|ImportError" "$out"; then
    die "$label had import/traceback output"
  fi
  grep -F "Validator registration failed" "$out" >/dev/null || {
    cat "$out" >&2
    die "$label did not reach the expected Grid-model failure"
  }
  grep -F "text.token_limit.v1" "$out" >/dev/null || {
    cat "$out" >&2
    die "$label did not load the packaged token-limit scorer"
  }
  grep -F "image.fidelity.v1" "$out" >/dev/null || {
    cat "$out" >&2
    die "$label did not load the packaged image scorer"
  }
  grep -F "video.fidelity.v1" "$out" >/dev/null || {
    cat "$out" >&2
    die "$label did not load the packaged video scorer"
  }
}

stat_mode() {
  stat -f '%Lp' "$1" 2>/dev/null || stat -c '%a' "$1"
}

need_file "$PY"
need_file "$VALIDATOR"

cd "$ROOT"
tmp="$(mktemp -d)"
container=""
dashboard_pid=""
trap 'if [ -n "$dashboard_pid" ]; then kill "$dashboard_pid" 2>/dev/null || true; wait "$dashboard_pid" 2>/dev/null || true; fi; if [ -n "$container" ]; then docker rm -f "$container" >/dev/null 2>&1 || true; fi; rm -rf "$tmp"' EXIT

status "Python/package checks"
"$PY" -m compileall validator
"$PY" -m unittest discover -s tests
bash -n install.sh scripts/classify-release-tag.sh scripts/install-binary.sh \
  scripts/install-systemd.sh scripts/verify-release-assets.sh "$0"
"$VALIDATOR" --help >/dev/null
"$PY" -m validator --help >/dev/null
"$VALIDATOR" check --help >/dev/null
"$VALIDATOR" self-test
git diff --check

status "Local dashboard smoke"
mkdir -p "$tmp/local-dashboard"
write_offline_env "$tmp/local-dashboard/.env" 8791
(
  cd "$tmp/local-dashboard"
  VALIDATOR_ENV="$tmp/local-dashboard/.env" "$VALIDATOR" dashboard --host 127.0.0.1 --port 8791
) > "$tmp/local-dashboard/dashboard.out" 2>&1 &
dashboard_pid=$!
for _ in $(seq 1 40); do
  if curl -fsS http://127.0.0.1:8791/healthz >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done
curl -fsS http://127.0.0.1:8791/status.json > "$tmp/local-dashboard/status.json"
if grep -E "grid-key|VALIDATOR_API_KEY|VALIDATOR_PRIVATE_KEY" "$tmp/local-dashboard/status.json"; then
  die "local dashboard status leaked secret-ish content"
fi
curl -fsS http://127.0.0.1:8791/ > "$tmp/local-dashboard/index.html"
grep -F "AIPG Validator" "$tmp/local-dashboard/index.html" >/dev/null
kill "$dashboard_pid" 2>/dev/null || true
wait "$dashboard_pid" 2>/dev/null || true
dashboard_pid=""

if [ "$SKIP_DOCKER" != "1" ]; then
  command -v docker >/dev/null 2>&1 || die "docker not found; set SKIP_DOCKER=1 to skip"

  status "Docker build and runtime smoke"
  write_offline_env "$tmp/docker.env" 8790
  docker build -t "$IMAGE" .
  set +e
  docker run --rm \
    --mount type=bind,source="$tmp/docker.env",target=/app/.env,readonly \
    "$IMAGE" check --no-probe > "$tmp/docker-check.out" 2>&1
  code=$?
  set -e
  assert_clean_offline_check "$tmp/docker-check.out" "$code" "docker"
  docker run --rm "$IMAGE" self-test
  docker run --rm "$IMAGE" --help >/dev/null

  status "Docker dashboard smoke"
  container="aipg-validator-dashboard-smoke-$$"
  docker run -d --name "$container" -p 127.0.0.1:8792:8790 \
    --mount type=bind,source="$tmp/docker.env",target=/app/.env,readonly \
    "$IMAGE" dashboard --host 0.0.0.0 --port 8790 >/dev/null
  for _ in $(seq 1 40); do
    if curl -fsS http://127.0.0.1:8792/healthz >/dev/null 2>&1; then
      break
    fi
    sleep 0.25
  done
  curl -fsS http://127.0.0.1:8792/status.json > "$tmp/docker-dashboard-status.json"
  if grep -E "grid-key|VALIDATOR_API_KEY|VALIDATOR_PRIVATE_KEY" "$tmp/docker-dashboard-status.json"; then
    die "docker dashboard status leaked secret-ish content"
  fi
  docker rm -f "$container" >/dev/null
  container=""
fi

if [ "$SKIP_BINARY" != "1" ]; then
  if [ -z "$PYINSTALLER" ]; then
    if [ -x "$ROOT/.venv/bin/pyinstaller" ]; then
      PYINSTALLER="$ROOT/.venv/bin/pyinstaller"
    else
      PYINSTALLER="$(command -v pyinstaller || true)"
    fi
  fi
  need_file "$PYINSTALLER"

  status "Release binary smoke"
  "$PYINSTALLER" --onefile --collect-data validator --name aipg-validator-smoke \
    --distpath "$tmp/dist" \
    --workpath "$tmp/build" \
    --specpath "$tmp/spec" \
    validator/__main__.py >/tmp/aipg-validator-pyinstaller.log 2>&1
  "$tmp/dist/aipg-validator-smoke" --help >/dev/null
  "$tmp/dist/aipg-validator-smoke" self-test
  "$PY" scripts/smoke-operator-app.py "$tmp/dist/aipg-validator-smoke"
  mkdir -p "$tmp/binary-run"
  write_offline_env "$tmp/binary-run/.env" 8793
  set +e
  (
    cd "$tmp/binary-run"
    "$tmp/dist/aipg-validator-smoke" check --no-probe
  ) > "$tmp/binary-check.out" 2>&1
  code=$?
  set -e
  assert_clean_offline_check "$tmp/binary-check.out" "$code" "binary"

  status "Binary installer smoke"
  mkdir -p "$tmp/pkg"
  cp "$tmp/dist/aipg-validator-smoke" "$tmp/pkg/aipg-validator"
  (
    cd "$tmp/pkg"
    "$PY" -m zipfile -c "$tmp/aipg-validator-install.zip" aipg-validator
  )
  checksum="$(shasum -a 256 "$tmp/aipg-validator-install.zip" | awk '{print $1}')"
  printf '%s  %s\n' "$checksum" "aipg-validator-$(uname -s | tr '[:upper:]' '[:lower:]' | sed 's/darwin/macos/')-$(uname -m | sed 's/x86_64/x64/; s/aarch64/arm64/').zip" > "$tmp/SHA256SUMS"
  config_dir="$tmp/config path"
  install_dir="$tmp/bin path"
  AIPG_VALIDATOR_URL="$tmp/aipg-validator-install.zip" \
    AIPG_VALIDATOR_CHECKSUMS_URL="$tmp/SHA256SUMS" \
    AIPG_VALIDATOR_INSTALL_DIR="$install_dir" \
    AIPG_VALIDATOR_CONFIG_DIR="$config_dir" \
    ./scripts/install-binary.sh > "$tmp/install.out"
  "$install_dir/aipg-validator" --help >/dev/null
  "$install_dir/aipg-validator" self-test
  [ "$(stat_mode "$config_dir")" = "700" ] || die "installer config dir is not mode 700"
  grep -F "cd '$config_dir'" "$tmp/install.out" >/dev/null
  enroll_line="$(grep -n -m1 -F " enroll" "$tmp/install.out" | cut -d: -f1)"
  check_line="$(grep -n -m1 -F " check --no-probe" "$tmp/install.out" | cut -d: -f1)"
  [ "$enroll_line" -lt "$check_line" ] || die "installer must print enroll before check"
  # Prove the packaged enrollment imports work, without creating a live account.
  printf 'n\n' | "$install_dir/aipg-validator" enroll --env "$config_dir/.env" > "$tmp/enroll.out"
  grep -F "Cancelled" "$tmp/enroll.out" >/dev/null
  [ ! -e "$config_dir/.env" ] || die "cancelled enrollment created an identity"
fi

status "Smoke release checks passed"
