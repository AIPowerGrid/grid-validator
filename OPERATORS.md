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

Current rollout: sealed assignment-bound shared quorum is live in production
and the immutable `v0.1.0-preview.13` release is the required qualification
baseline. Older preview.9 registrations are upgrade-required and do not count
toward independent quorum. First-party nodes prove the signed workflow, not
independence. Public enrollment remains an unpaid evidence-only cohort: current
assignments have no routing, payout, reward, strike, bond, or slashing effect.
Always run `check --no-probe` before operating the loop and use the public
[network page](https://console.aipowergrid.io/network) for current status.

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

### Dedicated Account Setup

New installs can run `aipg-validator enroll` (menu option 1). Confirm
creation of a dedicated node account. The program generates and stores its
signer locally, authenticates by wallet signature, and saves a validator-only
API key. It never asks you to paste a private key. Then run
`check --no-probe`, followed by `run`; enrollment alone proves no completed work.

Keep the private config backed up. Retrying after a connection failure reuses
that signer. Existing keys and unrecognized identities are never replaced.
Advanced automation may use `enroll --env /private/path/node.env --yes` as
explicit consent. Only the official HTTPS Grid supports this automatic flow.
There is no account merging or existing Google-account pairing in this command.
If a key was issued but the local write failed, retrying may leave an unused
key on the dedicated account; revoke unused keys during account recovery.

Older binary users should not export a personal wallet key to complete setup.
Upgrade to preview.13, preserving existing configuration. New operators can
extract the Windows ZIP, double-click `aipg-validator.exe`, and choose 8 for the
local app described below. The menu's setup/check/run commands remain available.
PowerShell is optional.

### Local Operator App

Preview.13 includes `aipg-validator app` (menu option 8). Native packaged-app
and clean-install tests pass on Windows x64, macOS ARM64, and Linux x64/ARM64.
Published preview.13 also passed a hosted Windows Server runtime journey through
accepted signed evidence and recovery. That HTTP-driven test does not replace
ordinary-user double-click/browser qualification; see [PRODUCTION_BASELINE.md](PRODUCTION_BASELINE.md).

The app opens a private localhost page. On an empty configuration, choose
**Set up node** and confirm dedicated-account creation. Existing operators
retain their configuration and choose **Start validator**. Registration and
heartbeats reflect Core acknowledgements; accepted evidence counts successful
submissions during this app session, not completed quality audits or rewards.
Waiting without an assignment is normal during cooldown or limited capacity.

**Stop** stops only the process this app started and preserves the signing
identity and recovery journal. It does not revoke credentials or suspend the
registration. An interrupted enrollment may have already persisted a signer
or issued a key; retry the same configuration, never create another identity
to work around it. Closing the browser tab leaves the app/node running; choose
**Exit app** to stop its child and close the app. A separate systemd/CLI instance is not
controlled by this page; it must be stopped through its original launcher.

The app binds only `127.0.0.1`, chooses an available port, and uses a random
local session. Do not share the private URL or forward its port. Reopen through
the menu if the local session expires. **Download diagnostics** includes only
version, public validator ID, status, timestamps, counts, and bounded activity.
It omits credentials, config paths, raw logs, and challenge content. Missing or
invalid credentials and connection failures are shown without leaking server
responses. Existing-account pairing remains separate, unreleased work. Source
builds include optional account-link controls; they require the matching Core
and Console deployment and are not available in preview.13. See
[Account Pairing](ACCOUNT_PAIRING.md) before testing or enabling that flow.

### Binary Install

Use the exact published preview release and verify the installer provenance
before running it:

> **Unsigned preview:** macOS is not Developer ID signed or notarized, and
> Windows is not Authenticode signed. Verify `SHA256SUMS` and GitHub provenance
> before accepting the OS warning. Prefer Linux or Docker for pilot nodes.

```bash
curl -fsSLO https://github.com/AIPowerGrid/grid-validator/releases/download/v0.1.0-preview.13/install-validator.sh
gh attestation verify install-validator.sh --repo AIPowerGrid/grid-validator
bash install-validator.sh
cd ~/.aipg-validator
aipg-validator enroll
aipg-validator self-test
aipg-validator check --no-probe
aipg-validator dashboard
```

The installer places the binary in `$HOME/.local/bin` and creates
`$HOME/.aipg-validator` for the private `.env` by default. Override with:

```bash
AIPG_VALIDATOR_INSTALL_DIR=/usr/local/bin \
  AIPG_VALIDATOR_CONFIG_DIR=/var/lib/aipg-validator \
  AIPG_VALIDATOR_VERSION=v0.1.0-preview.13 \
  ./scripts/install-binary.sh
```

For scripted Windows x64 installs, use the native PowerShell installer:

```powershell
Invoke-WebRequest https://github.com/AIPowerGrid/grid-validator/releases/download/v0.1.0-preview.13/install-validator.ps1 -OutFile install-validator.ps1
gh attestation verify install-validator.ps1 --repo AIPowerGrid/grid-validator
.\install-validator.ps1 -AcceptUnsignedPreview
```

The acknowledgement is required because this preview is not Authenticode
signed. SHA-256 is verified before installation or execution. Stable releases
remain blocked on signing.

From a source checkout, select the exact release explicitly:

```bash
AIPG_VALIDATOR_VERSION=v0.1.0-preview.13 ./scripts/install-binary.sh
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
identity automatically. Run `./.venv/bin/aipg-validator enroll` and confirm.
It saves a dedicated signer locally, authenticates its node account, and stores
the scoped key. Existing-account pairing remains separate and unshipped.

For the V0 preview:

- use the validator-purpose Grid API key saved by `enroll`
- set `VALIDATOR_REQUIRE_STAKE=false`
- leave `VALIDATOR_STAKING_ADDR` empty
- keep the dedicated signer generated by `enroll`; signing registration and
  evidence is required. It authenticates the same wallet to obtain its key;
  Core rejects a different or unlinked signing identity.
- if you set `AIPG_TOKEN_ADDR` or `VALIDATOR_STAKING_ADDR`, use valid 20-byte
  `0x` EVM addresses; malformed addresses fail startup before any RPC call

V0 `.env` fields (written automatically by enrollment; placeholders for reference):

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

Docker is the easiest server path and can perform first-run enrollment without
a source checkout. Keep the exact preview tag and a private host directory:

```bash
IMAGE=ghcr.io/aipowergrid/validator:v0.1.0-preview.13
CONFIG_DIR="$HOME/.aipg-validator"
mkdir -p "$CONFIG_DIR/state"
chmod 700 "$CONFIG_DIR" "$CONFIG_DIR/state"
docker pull "$IMAGE"
docker run --rm "$IMAGE" self-test
docker run --rm -it \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e VALIDATOR_ENV=/config/.env \
  --mount type=bind,source="$CONFIG_DIR",target=/config \
  "$IMAGE" enroll
chmod 600 "$CONFIG_DIR/.env"
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e VALIDATOR_ENV=/config/.env \
  -e VALIDATOR_STATE_DB=/state/state.sqlite3 \
  --mount type=bind,source="$CONFIG_DIR/.env",target=/config/.env,readonly \
  --mount type=bind,source="$CONFIG_DIR/state",target=/state \
  "$IMAGE" check --no-probe
docker run -d --name aipg-validator --restart unless-stopped \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e VALIDATOR_ENV=/config/.env \
  -e VALIDATOR_STATE_DB=/state/state.sqlite3 \
  --mount type=bind,source="$CONFIG_DIR/.env",target=/config/.env,readonly \
  --mount type=bind,source="$CONFIG_DIR/state",target=/state \
  "$IMAGE"
docker logs -f aipg-validator
```

The config mount is read-only after enrollment. The separate writable state
mount preserves pending evidence and deduplication across container restarts.
Keep both directories and the existing `val_*` identity across upgrades.

Run the dashboard container when you want a local browser view:

```bash
docker run --rm -p 8790:8790 \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e VALIDATOR_ENV=/config/.env \
  -e VALIDATOR_STATE_DB=/state/state.sqlite3 \
  --mount type=bind,source="$CONFIG_DIR/.env",target=/config/.env,readonly \
  --mount type=bind,source="$CONFIG_DIR/state",target=/state \
  "$IMAGE" \
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
config in `.env`, pins the durable SQLite journal to the private working
directory, and grants that directory the only explicit write exception under
the read-only home/system sandbox. It refuses to start the service until `.env`
exists.

For released binaries, download the reviewed helper from its immutable source
commit and verify its SHA-256. This pins the service definition independently
from the installed preview.13 binary and avoids executing a moving `master`
branch:

```bash
cd ~/.aipg-validator
curl -fsSLo install-systemd.sh \
  https://raw.githubusercontent.com/AIPowerGrid/grid-validator/778e9a1f2263094918998954c62678dba6b90334/scripts/install-systemd.sh
printf '%s  %s\n' \
  32adb391ab0591a55b3cbefce851fb0b9965685dabfc26706d6458e488b5defd \
  install-systemd.sh | sha256sum -c -
chmod 700 install-systemd.sh
sudo AIPG_VALIDATOR_EXEC="$HOME/.local/bin/aipg-validator" \
  AIPG_VALIDATOR_WORKDIR="$HOME/.aipg-validator" \
  ./install-systemd.sh --dry-run
sudo AIPG_VALIDATOR_EXEC="$HOME/.local/bin/aipg-validator" \
  AIPG_VALIDATOR_WORKDIR="$HOME/.aipg-validator" \
  ./install-systemd.sh
```

Stop any validator child started by the local app before enabling systemd. The
run lock rejects a second process, but operators should not depend on that as a
normal launch method.

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
| Windows `.exe` closes immediately | Upgrade to preview.13, extract the ZIP, and double-click its executable. It opens a persistent menu. Keep existing configuration. |
| Windows setup mentions `fchmod` | Known identity-creation bug through preview.9, fixed in preview.11. Upgrade the executable; more API keys will not help. |
| Console shows a different wallet than `prepare-wallet` | Stop and request enrollment assistance; a public address alone is not proof of control. Never export a funded wallet key to get past registration. |
| `VALIDATOR_PRIVATE_KEY is required` | New operators: choose Set up node in the preview.13 app, or menu option 1. Existing operators: restore the correct private config; do not replace the identity or paste a personal wallet key. |
| Setup asks you to type a private key | You are using an older build. Stop and upgrade to preview.13; automatic enrollment creates its own local signer. |
| `Setup needs confirmation` | Confirm in the executable menu, or use explicit `enroll --yes` only for deliberate automation. Do not paste credentials into command arguments. |
| `web3 not installed` | Install stake extras with `./.venv/bin/python -m pip install -e '.[stake]'`, or keep `VALIDATOR_REQUIRE_STAKE=false` for V0 preview |
| `Stake contract not deployed and REQUIRE_STAKE=true` | Expected in V0; set `VALIDATOR_REQUIRE_STAKE=false` unless you are testing the future stake gate |
| service will not start | Run `scripts/install-systemd.sh --dry-run`; then check the journal |
| dashboard will not load | Confirm `DASHBOARD_PORT` is free and the command is still running |
| Docker exits immediately | Run `docker compose run --rm validator check --no-probe` |
| Linux binary reports `failed to map segment from shared object` | Check whether its temporary directory is mounted `noexec`; see the private runtime-directory instructions below. Do not create another node identity. |

### Hardened Linux Temporary Directories

The released one-file binary extracts bundled libraries before starting. A
`noexec` temporary filesystem can prevent those libraries from loading, even
when the archive checksum and executable permissions are correct. Keep the
host's `/tmp` policy intact; use a private directory on an executable filesystem:

```bash
install -d -m 700 "$HOME/.aipg-validator/runtime"
export TMPDIR="$HOME/.aipg-validator/runtime"
```

Set this environment for both the verified installer and subsequent validator
commands. A service needs the same explicit `TMPDIR` in its service environment;
an export in an interactive shell does not change systemd. If the home filesystem
is also `noexec`, ask the administrator for an owner-only executable runtime
directory. Do not make the directory world-writable or remount all of `/tmp`.

This was reproduced with the published preview.12 Linux ARM64 binary on Ubuntu
22.04. Its normal automatic enrollment and real assignment loop worked after
selecting the private runtime directory. This is separate from missing packages
or invalid credentials.

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
