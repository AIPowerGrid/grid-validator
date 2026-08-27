# Run An AIPG Validator Node

A validator node helps measure whether Grid workers are useful, honest, and
available. In V0, it is a distributed audit runner: it sends small canary jobs,
scores the replies, and submits evidence to the Grid through
`/v1/validator/attest`.

V0 does **not** slash workers, pay public validator rewards, or prove exact model
identity. Those come later, after targeted assignments, staking, quorum rules, and
dispute tooling exist.

For the shortest install path, start with [QUICKSTART.md](QUICKSTART.md). This
file is the longer operator runbook.

Current rollout: sealed assignment-bound shared quorum is live on production
Core commit `df34ffd4` with migrations through `0029`. Three first-party pilot nodes
proved the signed 3-of-5 text flow without economic side effects and now run the
exact published `v0.1.0-preview.9` payload from commit `9d7b68f`. Core reports
that immutable release identity for all three nodes. Each node passed a staged
offline image/video decoder self-test, `check --no-probe`, atomic symlink
switch, and clean service restart. After the
earlier preview.5 cooldown, the fleet completed a healthy 3-of-5 16K-context
group and correctly disputed a token-limit group with no economic side effects.
Public enrollment remains a no-reward qualification cohort because those nodes
share one operator and hypervisor. Always run `check --no-probe` before operating
the loop.

Migration `0029` added a dark atomic accounting terminal for future compensated
audits. It did not enable a scheduler, private corpus, scoring policy, validator
rewards, or any new operator action. Current preview assignments remain unpaid
and have no routing, payout, strike, bond, or slashing effect.

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

Released Linux binaries target glibc 2.35 or newer (Ubuntu 22.04 or a
comparable distribution). Alpine/musl operators should use Docker or the source
install.

## Install

### Binary Install

Use the exact published preview release and verify the installer provenance
before running it:

> **Unsigned preview:** macOS is not Developer ID signed or notarized, and
> Windows is not Authenticode signed. Verify `SHA256SUMS` and GitHub provenance
> before accepting the OS warning. Prefer Linux or Docker for pilot nodes.

```bash
curl -fsSLO https://github.com/AIPowerGrid/grid-validator/releases/download/v0.1.0-preview.9/install-validator.sh
gh attestation verify install-validator.sh --repo AIPowerGrid/grid-validator
bash install-validator.sh
cd ~/.aipg-validator
aipg-validator prepare-wallet
# Link the printed address and create a validator key in the Console.
aipg-validator init
aipg-validator self-test
aipg-validator check --no-probe
aipg-validator dashboard
```

The installer places the binary in `$HOME/.local/bin` and creates
`$HOME/.aipg-validator` for the private `.env` by default. Override with:

```bash
AIPG_VALIDATOR_INSTALL_DIR=/usr/local/bin \
  AIPG_VALIDATOR_CONFIG_DIR=/var/lib/aipg-validator \
  AIPG_VALIDATOR_VERSION=v0.1.0-preview.9 \
  ./scripts/install-binary.sh
```

On Windows x64, use the native PowerShell installer:

```powershell
Invoke-WebRequest https://github.com/AIPowerGrid/grid-validator/releases/download/v0.1.0-preview.9/install-validator.ps1 -OutFile install-validator.ps1
gh attestation verify install-validator.ps1 --repo AIPowerGrid/grid-validator
.\install-validator.ps1 -AcceptUnsignedPreview
```

The acknowledgement is required because this preview is not Authenticode
signed. SHA-256 is verified before installation or execution. Stable releases
remain blocked on signing.

After a GitHub release exists, the same installer can be run from a checkout:

```bash
./scripts/install-binary.sh
```

Running nodes perform a notification-only release check at most every six
hours. They do not download or execute updates. When notified, set
`AIPG_VALIDATOR_VERSION` to that exact tag, rerun the verified installer, and
repeat `aipg-validator check --no-probe`. Disable the check with
`VALIDATOR_UPDATE_CHECK=false` when outbound GitHub access is not desired.

### Suspend, Resume, Or Rotate

Stop new assignments before planned maintenance:

```bash
aipg-validator suspend
```

The request is signed by the registered wallet. Resume the same identity with a
fresh registration and health check:

```bash
aipg-validator check --no-probe
```

To replace the signing wallet, first stop the node. In the Console, keep the
same Grid account, link a different replacement wallet, and issue a new
validator API key. Update `VALIDATOR_WALLET`, `VALIDATOR_PRIVATE_KEY`, and
`VALIDATOR_API_KEY` locally, keep `.env` mode `0600`, then run:

```bash
aipg-validator rotate
aipg-validator check --no-probe
```

Rotation preserves the validator ID and historical attribution. It does not
move old in-flight assignments; they expire. After the replacement checks
healthy, revoke every old validator API key in the Console. If compromise is
suspected, request maintainer revocation too: an attacker holding both old keys
can otherwise resume a merely self-suspended registration.

### Source Install

```bash
git clone https://github.com/AIPowerGrid/grid-validator
cd grid-validator
./install.sh
```

The installer creates `.venv` and installs dependencies. It does not create an
identity automatically. Run `aipg-validator prepare-wallet`; it writes the
private key only to the local mode-`0600` `.env` and prints the public address.
Link that address at `https://console.aipowergrid.io/dashboard/validators`,
create a validator-purpose API key there, and run `aipg-validator init` to
complete the same file.

For the V0 preview:

- use the validator-purpose Grid API key created after linking the signing wallet
- set `VALIDATOR_REQUIRE_STAKE=false`
- leave `VALIDATOR_STAKING_ADDR` empty
- use a dedicated `VALIDATOR_PRIVATE_KEY`; signing registration and evidence is
  required. The init command derives `VALIDATOR_WALLET` from it.
- link that wallet to the Grid account before issuing the validator-purpose API
  key; Core rejects a different or unlinked signing identity.
- if you set `AIPG_TOKEN_ADDR` or `VALIDATOR_STAKING_ADDR`, use valid 20-byte
  `0x` EVM addresses; malformed addresses fail startup before any RPC call

Minimal V0 `.env`:

```ini
GRID_API_URL=https://api.aipowergrid.io
VALIDATOR_API_KEY=your-grid-api-key
VALIDATOR_WALLET=0xYourLinkedWallet
VALIDATOR_PRIVATE_KEY=0xYourLocalSigningKey
VALIDATOR_REQUIRE_STAKE=false
```

Then run:

```bash
./.venv/bin/aipg-validator check
```

The default source install keeps dependencies small: text probing and signed V0
attestations work out of the box. Dark image/video scoring and on-chain
stake-gate experiments need optional extras:

```bash
./.venv/bin/python -m pip install -e '.[media,stake]'
```

What a first healthy preview run should prove:

- config loads from local `.env`
- core validator capability flags are visible, or safely reported as unavailable
- aggregate evidence scorecards are visible, or safely reported as unavailable
- the Grid is reachable
- signed registration succeeds
- one assignment-bound canary round completes, or the node clearly reports that
  no assignment is currently available
- the stake check is either healthy or explicitly skipped in preview mode

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
default. It shows config health, validator registration, Grid reachability,
registered worker inventory, aggregate evidence scorecards, and staking mode
without printing API keys or private keys.

Override the bind address only when you know the machine/network boundary:

```bash
./.venv/bin/aipg-validator dashboard --host 127.0.0.1 --port 8790
```

### Docker Install

Docker is the easiest server path once `.env` exists.

```bash
docker pull ghcr.io/aipowergrid/validator:v0.1.0-preview.9
docker run --rm ghcr.io/aipowergrid/validator:v0.1.0-preview.9 self-test
docker run --rm \
  --mount type=bind,source="$PWD/.env",target=/app/.env,readonly \
  ghcr.io/aipowergrid/validator:v0.1.0-preview.9 check --no-probe
docker run -d --name aipg-validator --restart unless-stopped \
  --mount type=bind,source="$PWD/.env",target=/app/.env,readonly \
  ghcr.io/aipowergrid/validator:v0.1.0-preview.9
```

Run the dashboard container when you want a local browser view:

```bash
docker run --rm -p 8790:8790 \
  --mount type=bind,source="$PWD/.env",target=/app/.env,readonly \
  ghcr.io/aipowergrid/validator:v0.1.0-preview.9 \
  dashboard --host 0.0.0.0
```

The public preview image is anonymous and multi-architecture for Linux x64 and
ARM64. Keep the versioned tag explicit; `latest` is intentionally absent for a
prerelease. Build `aipowergrid/validator:local` only for source-development
testing.

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

The current node probes only text assignments issued by Core. It does not infer
targets from the public model list.

Checks:

- exact nonce echo: proves the response is prompt-derived and follows the
  instruction rather than echoing the whole prompt
- generated arithmetic QA: catches broken backends or wildly wrong model routing
- latency budget: classifies correct but slow responses as `slow`
- evidence binding: rejects a result whose assignment, target, model, nonce,
  capability, prompt hash, response hash, or canonical evidence hash does not
  match what the node independently recomputes
- local scoring: signs the node's own verdict; a disagreement with Core remains
  visible as disputed evidence
- mandatory signature: signs registration and the attestation payload,
  including prompt/response hashes and a compact evidence hash

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
| `/v1/validator/capabilities` | reads non-economic feature flags |
| `/v1/validator/register` | registers the linked signing wallet and capabilities |
| `/v1/validator/registration` | reports registration and the authenticated operator's safe qualification progress |
| `/v1/validator/suspend` | accepts signed self-suspension for maintenance or exit |
| `/v1/validator/rotate` | binds the stable validator ID to a linked replacement wallet |
| `/v1/validator/heartbeat` | refreshes node liveness |
| `/v1/validator/assignments` | supplies the only valid probe targets |
| `/v1/validator/probe/{assignment_id}` | targeted execution for an assignment |
| `/v1/validator/attest` | accepts signed assignment evidence |
| `/v1/validator/workers` | read-only inventory; never targeting authority |
| `/v1/validator/scorecards` | aggregate evidence view; no routing/reward/slash effect |

Missing read-only scorecards are non-fatal. Missing registration, assignments,
targeted probing, or attestation support makes the validator unavailable. It
must not substitute ordinary inference or invent a worker target.

## Durable Evidence Delivery

The node writes every assignment to the private local SQLite journal at
`VALIDATOR_STATE_DB` before probing. After local scoring, it atomically replaces
that row with the signed attestation before submission. A restart can therefore
request Core's committed completed result without dispatching the worker twice.
Failed submissions are replayed before new work, and the row is removed only
after Core accepts it.

Assignments and attestations have separate attempt/age bounds. Exhausted rows
remain as dead letters for operator review. Inspect them with
`aipg-validator queue status`; after resolving the cause, explicitly revive them
with `aipg-validator queue retry-dead --kind assignments`, `--kind attestations`,
or the default `--kind all`. The state database contains short-lived synthetic
assignments and signed public payloads, not `VALIDATOR_PRIVATE_KEY`.

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
| `No Grid assignment was available` | No eligible third-party text assignment is currently available; retry later |
| attestations remain pending | Check Core reachability; the node retries the durable local outbox automatically |
| outbox reports dead letters | Stop and inspect Core rejection logs before removing the local state database |
| registration fails with 403 | Confirm the key purpose is validator and the signing wallet is linked to the same Grid account |
| `VALIDATOR_PRIVATE_KEY is required` | Run `aipg-validator prepare-wallet`, link the printed address, then complete `init` |
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
