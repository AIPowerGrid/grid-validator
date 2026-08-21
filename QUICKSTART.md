# Validator Quickstart

Run a validator when you want to help measure Grid worker quality without
running a generation model yourself. V0 validators are CPU-only audit runners:
they send small canary jobs through the normal Grid API, score the result, and
submit signed evidence when core exposes the attestation endpoint.

V0 is evidence-only. It does not pay validator rewards, slash workers, change
routing, or prove exact model weights.

Rollout status: the shared-quorum Core code is merged but migrations through `0024`
and the matching production release are still pending. `0022` carries quorum;
the later migrations are required by the current dark media schema. Use `check --no-probe`
for installation smoke until the public release page opens.

## What You Need

- A machine that can stay online.
- Python 3.10+ for the source preview.
- A Grid API key.
- A dedicated validator signing wallet linked to the same Grid account.
- No GPU.
- No Base stake requirement during the V0 preview.

Minimal V0 config:

```ini
GRID_API_URL=https://api.aipowergrid.io
VALIDATOR_API_KEY=your-grid-api-key
VALIDATOR_WALLET=0xYourLinkedWallet
VALIDATOR_PRIVATE_KEY=0xYourLocalSigningKey
VALIDATOR_REQUIRE_STAKE=false
```

For preview installs, keep:

```ini
VALIDATOR_REQUIRE_STAKE=false
```

`VALIDATOR_PRIVATE_KEY` is required and stays on the node. It signs registration
and attestations locally; Core receives only signatures and the public wallet.
The wallet must already be linked to the account that issued the dedicated
validator key. `aipg-validator init` derives `VALIDATOR_WALLET` from the key.
This evidence identity is mandatory even while `VALIDATOR_REQUIRE_STAKE=false`.

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

The released installer verifies the downloaded archive against `SHA256SUMS`.
Download it from the exact preview release and verify its build provenance
before running it:

```bash
curl -fsSLO https://github.com/AIPowerGrid/grid-validator/releases/download/v0.1.0-preview/install-validator.sh
gh attestation verify install-validator.sh --repo AIPowerGrid/grid-validator
AIPG_VALIDATOR_VERSION=v0.1.0-preview bash install-validator.sh
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
- registration is active for the configured wallet
- `check` reports at least one submitted assignment, or clearly says none are available
- dashboard reachable on localhost
- scorecards visible when core exposes `/v1/validator/scorecards`

Missing read-only scorecards are non-fatal. Missing registration, assignments,
targeted probing, or attestation support makes the validator unavailable; the
node must not substitute ordinary user inference or invent a worker target.

If only image/video models are visible, `check` exits non-zero because it did not
submit a text canary. That is expected; use `check --no-probe` for a pure install
smoke, or wait until a compatible text model is online.

## Current Core Contract

V0 validator nodes rely on these Grid paths:

| Endpoint | Required | Effect |
|---|---:|---|
| `GET /v1/validator/capabilities` | no | discover safe validator features |
| `POST /v1/validator/register` | yes | register the linked signing identity |
| `GET /v1/validator/registration` | yes | inspect registration state |
| `POST /v1/validator/heartbeat` | yes | refresh node liveness |
| `GET /v1/validator/assignments` | yes | receive Grid-issued text assignments |
| `POST /v1/validator/probe/{assignment_id}` | yes | execute an assignment against its bound worker |
| `POST /v1/validator/attest` | yes | store signed assignment evidence |
| `GET /v1/validator/workers` | no | discovery; targeting still requires an assignment |
| `GET /v1/validator/scorecards` | no | aggregate evidence workflow states only |

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

The current text preview samples exact instruction following, generated
arithmetic, strict JSON, calibrated 4K/16K/32K context retrieval, generated
multistep logic, one exact randomized function call, one two-stage tool-call
chain, and one randomized stop-sequence check. It also samples gross
output-budget compliance with an independent model-agnostic token counter and a cross-tokenizer
tolerance; it does not claim exact native tokenizer equivalence.
These checks are randomized and capability-gated, but they still do not prove
an exact model family, parameter count, or quantization.

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
