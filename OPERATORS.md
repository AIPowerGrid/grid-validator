# Run An AIPG Validator Node

A validator node helps measure whether Grid workers are useful, honest, and
available. In V0, it is a distributed audit runner: it sends small canary jobs,
scores the replies, and submits evidence to the Grid when `/v1/validator/attest`
is deployed.

V0 does **not** slash workers, pay public validator rewards, or prove exact model
identity. Those come later, after targeted assignments, staking, quorum rules, and
dispute tooling exist.

For the shortest install path, start with [QUICKSTART.md](QUICKSTART.md). This
file is the longer operator runbook.

## System Requirements

| Resource | Minimum | Recommended |
|---|---:|---:|
| CPU | 1 core | 2 cores |
| RAM | 1 GB | 2 GB |
| Disk | 1 GB | 2 GB |
| GPU | none | none |
| OS | Linux / macOS / Windows | Linux + systemd |
| Python | 3.10+ | 3.11+ |
| Network | stable broadband | stable always-on |

A small VPS, Raspberry Pi 4, or spare always-on machine is enough for V0 text
probing. Future media/video scorers are designed to stay CPU-only where possible,
but may need extra optional packages.

## Install

### Binary Install

Once downloadable binaries are published, this is the intended public path:

```bash
curl -fsSL https://get.aipowergrid.io/validator | bash
cd ~/.aipg-validator
aipg-validator init
aipg-validator check --no-probe
aipg-validator dashboard
```

The installer places the binary in `$HOME/.local/bin` and creates
`$HOME/.aipg-validator` for the private `.env` by default. Override with:

```bash
AIPG_VALIDATOR_INSTALL_DIR=/usr/local/bin \
  AIPG_VALIDATOR_CONFIG_DIR=/var/lib/aipg-validator \
  ./scripts/install-binary.sh
```

After a GitHub release exists, the same installer can be run from a checkout:

```bash
./scripts/install-binary.sh
```

### Source Install

```bash
git clone https://github.com/AIPowerGrid/grid-validator
cd grid-validator
./install.sh
```

The installer creates `.venv` and installs dependencies. If stdin is an
interactive terminal and `.env` is missing, it runs `aipg-validator init`. In
non-interactive automation it does not write config; run init yourself or create
`.env` from `.env.template`.

For the V0 preview:

- use your validator Grid API key
- set `VALIDATOR_REQUIRE_STAKE=false`
- leave `VALIDATOR_STAKING_ADDR` empty
- leave `VALIDATOR_PRIVATE_KEY` empty unless you are testing signed attestations;
  if you set it, `VALIDATOR_WALLET` must match the key. The init command derives
  the wallet when you leave the wallet prompt blank.
- if you set `VALIDATOR_WALLET`, use a valid `0x` EVM address even in unsigned
  preview mode
- if you set `AIPG_TOKEN_ADDR` or `VALIDATOR_STAKING_ADDR`, use valid 20-byte
  `0x` EVM addresses; malformed addresses fail startup before any RPC call

Minimal V0 `.env`:

```ini
GRID_API_URL=https://api.aipowergrid.io
VALIDATOR_API_KEY=your-grid-api-key
VALIDATOR_REQUIRE_STAKE=false
```

Then run:

```bash
./.venv/bin/aipg-validator check
```

The default source install keeps dependencies small: text probing and signed V0
attestations work out of the box. Future media scoring and on-chain stake-gate
experiments need optional extras:

```bash
./.venv/bin/python -m pip install -e '.[media,stake]'
```

What a first healthy preview run should prove:

- config loads from local `.env`
- core validator capability flags are visible, or safely reported as unavailable
- aggregate evidence scorecards are visible, or safely reported as unavailable
- the Grid is reachable
- visible text models can be listed
- one model-routed canary round completes
- optional stake/signature checks are either healthy or clearly skipped

Expected healthy output:

```text
Config OK
Grid reachable
Running one probe round
Probe round submitted 1 canary job(s)
check complete
```

For install validation without submitting a canary job:

```bash
./.venv/bin/aipg-validator check --no-probe
```

Use `check --no-probe` before enabling a long-running service. It still reaches
the Grid and reads capability/scorecard metadata, but it does not send canary
traffic or submit attestations.

The source checkout also supports:

```bash
./.venv/bin/python -m validator --help
```

Start the loop:

```bash
./.venv/bin/aipg-validator run
```

Start the local dashboard:

```bash
./.venv/bin/aipg-validator dashboard
```

Open `http://127.0.0.1:8790/`. The dashboard is read-only and localhost-bound by
default. It shows config health, Grid reachability, visible models, aggregate
evidence scorecards, and staking mode without printing API keys or private keys.

Override the bind address only when you know the machine/network boundary:

```bash
./.venv/bin/aipg-validator dashboard --host 127.0.0.1 --port 8790
```

### Docker Install

Docker is the easiest server path once `.env` exists.

```bash
docker build -t aipowergrid/validator:local .
docker run --rm \
  --mount type=bind,source="$PWD/.env",target=/app/.env,readonly \
  aipowergrid/validator:local check --no-probe
docker run -d --name aipg-validator --restart unless-stopped \
  --mount type=bind,source="$PWD/.env",target=/app/.env,readonly \
  aipowergrid/validator:local
```

Run the dashboard container when you want a local browser view:

```bash
docker run --rm -p 8790:8790 \
  --mount type=bind,source="$PWD/.env",target=/app/.env,readonly \
  aipowergrid/validator:local dashboard --host 0.0.0.0
```

Or use Compose:

```bash
docker compose run --rm validator check --no-probe
docker compose up -d validator
docker compose --profile dashboard up -d validator-dashboard
```

## Keep It Running

On Linux, install the systemd service after `check --no-probe` passes:

```bash
./scripts/install-systemd.sh --dry-run
sudo ./scripts/install-systemd.sh
journalctl -u aipg-validator -f
```

The helper writes `/etc/systemd/system/aipg-validator.service`, keeps the private
config in `.env`, and refuses to start the service until `.env` exists.

For released binaries, point the helper at the installed binary and a private
working directory:

```bash
sudo AIPG_VALIDATOR_EXEC="$(command -v aipg-validator)" \
  ./scripts/install-systemd.sh --workdir /var/lib/aipg-validator --user aipg
```

Useful service commands:

```bash
sudo systemctl status aipg-validator
sudo systemctl restart aipg-validator
sudo systemctl disable --now aipg-validator
```

## What The Node Checks In V0

The current node probes text models only when running through the public model
list. It avoids names that look like image/video models because V0 model metadata
does not reliably expose modality.

Checks:

- exact nonce echo: proves the response is prompt-derived and follows the
  instruction rather than echoing the whole prompt
- generated arithmetic QA: catches broken backends or wildly wrong model routing
- latency budget: classifies correct but slow responses as `slow`
- optional signature: signs the attestation payload, including prompt/response
  hashes and a compact evidence hash, when a private key is present

The result is one of:

```text
healthy
slow
failed
```

In V0, these are evidence signals. They should feed dashboards and internal
learning before they affect routing, payouts, or slashing.

## Current Core Compatibility

The node is intentionally defensive around new Grid endpoints:

| Core capability | Node behavior |
|---|---|
| `/v1/validator/capabilities` | reads feature flags; falls back to safe V0 defaults |
| `/v1/models` | required for model-routed V0 probing |
| `/v1/chat/completions` | required for model-routed text canaries |
| `/v1/validator/attest` | submits evidence when present; skips cleanly when unavailable |
| `/v1/validator/workers` | reads inventory only; ignores it unless `targeted_probe_enabled=true` |
| `/v1/validator/scorecards` | aggregate evidence view; no routing/reward/slash effect |
| `/v1/validator/probe` | not assumed live; missing/disabled endpoint must not create failures |

If every future validator endpoint is missing, the node should still run in V0
model-routed mode. That is deliberate.

## Future Validator Roles

The public product should grow into three operator-friendly roles:

| Role | Hardware | Purpose |
|---|---|---|
| Observer | CPU-only | Receipts, liveness, latency, format, parameter honesty |
| Scorer | CPU, optional media deps | Text/image/video challenge scoring |
| Reference | bonded, high-trust | Baseline outputs for deterministic workflow certification |

Do not present Reference or slash-capable operation as live until the Grid supports
targeted assignments and quorum validation.

## Staking And Rewards

Not live in V0.

Planned model:

- validators bond AIPG to participate in economic validation
- accepted attestations earn modest rewards
- rewards depend on agreement, timeliness, difficulty, and validator reputation
- objective fraud can eventually be slashable
- subjective quality should downgrade routing, not slash stake

Until the staking contract and reward path are deployed, validator operation is a
preview/testing role.

For the implementation sequence, see [ROADMAP.md](ROADMAP.md). The short version:
deploy evidence first, show informational scorecards next, then add targeted
assignments, then rewards/staking after the evidence loop is boring.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `VALIDATOR_API_KEY is required` | Run setup again or edit `.env` |
| `GRID_API_URL must be an http(s) URL` | Include the scheme, for example `https://api.aipowergrid.io`, not just the hostname |
| `Config: PROBE_INTERVAL_S must be an integer` | Fix the named value in `.env`; numeric env vars reject typos instead of guessing |
| `dashboard port must be between 1 and 65535` | Pick a valid free TCP port, usually `8790` |
| `Grid reachable - models: (none)` | No compatible models are online or visible |
| `no compatible text targets` | `check` found no text model to probe; use `check --no-probe` for install smoke |
| every model shows `failed` | Check API key, Grid URL, and local network |
| `VALIDATOR_PRIVATE_KEY is required` | Set `VALIDATOR_REQUIRE_STAKE=false` for V0 preview |
| `Interactive setup requires a terminal` | Run `aipg-validator init` from a shell, or create `.env` from `.env.template` |
| `web3 not installed` | Install stake extras with `./.venv/bin/python -m pip install -e '.[stake]'`, or keep `VALIDATOR_REQUIRE_STAKE=false` for V0 preview |
| `Stake contract not deployed and REQUIRE_STAKE=true` | Expected in V0; set `VALIDATOR_REQUIRE_STAKE=false` unless you are testing the future stake gate |
| service will not start | Run `scripts/install-systemd.sh --dry-run`; then check the journal |
| dashboard will not load | Confirm `DASHBOARD_PORT` is free and the command is still running |
| Docker exits immediately | Run `docker compose run --rm validator check --no-probe` |

## FAQ

**Do I need a GPU?**
No. Validators test workers; they do not run generation models locally.

**Can I run a worker and validator?**
For V0 testing, yes. Once targeted assignments exist, validators should not
validate workers controlled by the same account.

**Does the validator know exact model weights?**
Usually no. For text and general media, validators measure usefulness and honesty.
For deterministic image workflows, future validators can compare against certified
reference outputs using pHash/SSIM/LPIPS tolerances.

**Where is the private key stored?**
Only in local `.env`, if configured. Keep that file at `chmod 600`.
