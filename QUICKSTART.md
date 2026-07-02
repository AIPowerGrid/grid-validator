# Validator Quickstart

Run a validator when you want to help measure Grid worker quality without
running a generation model yourself. V0 validators are CPU-only audit runners:
they send small canary jobs through the normal Grid API, score the result, and
submit signed evidence when core exposes the attestation endpoint.

V0 is evidence-only. It does not pay validator rewards, slash workers, change
routing, or prove exact model weights.

## What You Need

- A machine that can stay online.
- Python 3.10+ for the source preview.
- A Grid API key.
- No GPU.
- No Base stake requirement during the V0 preview.

Minimal V0 config:

```ini
GRID_API_URL=https://api.aipowergrid.io
VALIDATOR_API_KEY=your-grid-api-key
VALIDATOR_REQUIRE_STAKE=false
```

For preview installs, keep:

```ini
VALIDATOR_REQUIRE_STAKE=false
```

`VALIDATOR_PRIVATE_KEY` is optional in V0. If you set it, the node signs
attestations locally and sends only the signed payload to the Grid. The
configured `VALIDATOR_WALLET` must match the private key. `aipg-validator init`
can sign V0 attestations while `VALIDATOR_REQUIRE_STAKE=false`; it derives the
wallet from the key when no wallet is entered. If you enter a wallet manually,
it must be a valid `0x` EVM address.

## Source Preview

```bash
git clone https://github.com/AIPowerGrid/grid-validator
cd grid-validator

./install.sh
./.venv/bin/aipg-validator check --no-probe
./.venv/bin/aipg-validator dashboard
```

`./install.sh` creates `.venv` and installs the package. If it is run from a
terminal and `.env` is missing, it starts `aipg-validator init` for you. If it
is run by automation or another non-interactive shell, it skips setup; run
`./.venv/bin/aipg-validator init` yourself, or copy `.env.template` to `.env`
and set `chmod 600 .env`.

Open `http://127.0.0.1:8790/`.

When the smoke test and dashboard look healthy, run one canary probe:

```bash
./.venv/bin/aipg-validator check
```

Then start the loop:

```bash
./.venv/bin/aipg-validator run
```

Command safety:

| Command | Sends canary jobs? | Notes |
|---|---:|---|
| `init` | no | writes local `.env`; no network call |
| `check --no-probe` | no | validates config and Grid reachability |
| `dashboard` | no | read-only localhost view |
| `check` | yes | sends one small V0 text canary round |
| `run` | yes | keeps sending V0 canaries on the configured interval |

## Binary Install

This is the intended public path once release artifacts are published:

| Platform | Release asset |
|---|---|
| Windows x64 | `aipg-validator-windows-x64.zip` |
| macOS ARM64 | `aipg-validator-macos-arm64.zip` |
| Linux x64 | `aipg-validator-linux-x64.zip` |
| Linux ARM64 | `aipg-validator-linux-arm64.zip` |

```bash
curl -fsSL https://get.aipowergrid.io/validator | bash
cd ~/.aipg-validator
aipg-validator init
aipg-validator check --no-probe
aipg-validator dashboard
aipg-validator run
```

Until the first public release exists, use the source preview or local Docker
path.

## Docker

```bash
docker build -t aipowergrid/validator:local .
docker run --rm \
  --mount type=bind,source="$PWD/.env",target=/app/.env,readonly \
  aipowergrid/validator:local check --no-probe
```

Run the loop:

```bash
docker run -d --name aipg-validator --restart unless-stopped \
  --mount type=bind,source="$PWD/.env",target=/app/.env,readonly \
  aipowergrid/validator:local
```

Run the dashboard:

```bash
docker run --rm -p 8790:8790 \
  --mount type=bind,source="$PWD/.env",target=/app/.env,readonly \
  aipowergrid/validator:local dashboard --host 0.0.0.0
```

## Systemd

After `.env` is configured and `check --no-probe` passes:

```bash
./scripts/install-systemd.sh --dry-run
sudo ./scripts/install-systemd.sh
journalctl -u aipg-validator -f
```

The helper keeps secrets in `.env` and refuses to start the service when `.env`
is missing.

## Healthy Output

A healthy V0 node should show:

- config loaded
- Grid reachable
- validator capability flags visible, or safely reported as unavailable
- at least one text model visible for canary probes
- `check` reports at least one submitted canary job
- dashboard reachable on localhost
- scorecards visible when core exposes `/v1/validator/scorecards`

If `/v1/validator/attest`, `/v1/validator/workers`, or
`/v1/validator/scorecards` are missing, the node should keep running in safe V0
mode. Missing future validator endpoints are not worker failures.

If only image/video models are visible, `check` exits non-zero because it did not
submit a text canary. That is expected; use `check --no-probe` for a pure install
smoke, or wait until a compatible text model is online.

## Current Core Contract

V0 validator nodes rely on these Grid paths:

| Endpoint | Required | Effect |
|---|---:|---|
| `GET /v1/models` | yes | find text models for model-routed probes |
| `POST /v1/chat/completions` | yes | send V0 text canaries |
| `GET /v1/validator/capabilities` | no | discover safe validator features |
| `POST /v1/validator/attest` | no | store signed evidence only |
| `GET /v1/validator/workers` | no | inventory only until targeted probing is live |
| `GET /v1/validator/scorecards` | no | aggregate evidence only |

`GET /v1/validator/workers` must be treated as inventory unless core returns
`targeted_probe_enabled=true`. Do not create targeted failures from inventory.

## What V0 Does Not Prove

- It does not prove exact text model weights or quantization.
- It does not prove every worker is honest.
- It does not slash.
- It does not pay public validator rewards.
- It does not certify media workflows yet, and it does not decide NFT or
  marketplace minting policy.

For text, V0 measures usefulness and job-contract honesty. For future
deterministic image workflows, validators can compare against certified
reference outputs and provide proof of fidelity.

## Operator Safety

- Keep `.env` at `chmod 600`.
- Do not expose the dashboard publicly unless it is behind your own access
  controls.
- Do not commit live challenge seeds, answer keys, golden pHashes, private
  prompts, live scoring secrets, or private policy thresholds.
- Do not run slash/reward logic from validator evidence until assignment,
  quorum, dispute, and contract paths are live.

## Next Reading

- [README.md](README.md) - repo overview and install options.
- [OPERATORS.md](OPERATORS.md) - detailed runbook and troubleshooting.
- [DESIGN.md](DESIGN.md) - text, image, video, reference pool, and Base design.
- [ROADMAP.md](ROADMAP.md) - build order and go/no-go gates.
