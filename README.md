# AIPG Validator Node

Validator nodes are the Grid's distributed audit runners. They send small canary
jobs through the normal Grid path, check whether workers follow the job contract,
and submit signed evidence back to the Grid.

V0 is intentionally humble: **observe, score, and attest first; route/reward/slash
later.** The node should be easy to run before it is allowed to carry economic
authority.

Random challenge values prevent answer replay, not template recognition. A
regex solver can legitimately pass some protocol checks, so current canaries do
not produce a quality score or prove an exact model. See
[ADVERSARIAL_VALIDATION.md](ADVERSARIAL_VALIDATION.md) for the attacker model
and economic gates.

Start with [QUICKSTART.md](QUICKSTART.md) if you just want to run a preview node.
Read [PREVIEW_COHORT.md](PREVIEW_COHORT.md) to join the first independent
operator cohort and complete the 72-hour qualification run.
Use [OPERATORS.md](OPERATORS.md) when you are installing it as an always-on
service, [RELEASE_V0.md](RELEASE_V0.md) for the cross-repo rollout order, and
[DESIGN.md](DESIGN.md) for the full validator story across text, image, video,
reference workers, and Base anchoring.

## V0 Scope

What is implemented and testable against production Core:

- CPU-only source install.
- Dockerfile and local Docker Compose.
- `init`, `check`, `dashboard`, and `run` CLI flow.
- Editable package install with the `aipg-validator` console command.
- Module entrypoint for `python -m validator`.
- Read-only local dashboard on `127.0.0.1:8790`.
- Assignment-bound text canaries through validator-only Core endpoints.
- Randomized text scoring: exact nonce echo, generated arithmetic, strict JSON,
  calibrated 4K, 16K, and 32K context retrieval, generated multistep logic, exact
  restricted-AST Python function synthesis against hidden inputs, function
  calls, a two-stage function-call chain, stop-sequence compliance, gross
  output-budget compliance, and latency classification.
- Mandatory signed registration, heartbeat, and attestations from a wallet
  linked to the validator's Grid account.
- Small default install: V0 text probing plus signing. Optional `media` and
  `stake` extras install heavier future-lane dependencies. From source, the
  media extra includes dark image and video scorers; release binaries remain
  text-only until media packaging is separately qualified.
- GitHub Actions release workflow scaffold for downloadable binaries.
- Grid-issued text assignments with short-lived nonces.
- Targeted probe execution at
  `POST /v1/validator/probe/{assignment_id}`; the core, not the validator,
  selects the worker.
- Compatible sealed-assignment execution: an updated Core may withhold the
  target, model, nonce, and challenge until the worker finishes. The node
  verifies their SHA-256 commitment before it scores or signs the result, while
  retaining staged compatibility with the current unsealed Core.
- Independent result binding and scoring: the node matches every returned
  assignment field, recomputes the prompt/response/evidence hashes, and applies
  its local scorer against an expected-answer hash before signing. Core does not
  return its private answer or verdict; a mismatch is skipped.
- Shared probe batches target five distinct registered validator accounts and
  require three matching votes. New Core v8 batches issue a unique randomized
  challenge per validator within one capability lane. This proves distinct
  evidence identities, not independently controlled operators or general model
  quality.
- Core admits a node to a probe group only when its registration advertises the
  matching local scorer. Legacy `text.basic.v1` nodes remain limited to
  echo/arithmetic instead of mis-scoring newer challenge families.
- All current validator evidence has `economic_effect: none`: it does not alter
  routing, rewards, strikes, payouts, or bonds.
- Production assignment polling is sealed: target, model, nonce, and challenge
  arrive only after worker execution, and the node verifies their SHA-256
  commitment before signing. This reduces advance collusion; it does not hide
  recognizable public prompt families from the worker during execution.
- Fail-closed behavior when registration, assignment, or targeted-probe support
  is unavailable; read-only dashboard metadata may degrade gracefully.

Production preview status:

- Production Core runs the sealed shared-quorum validator API at immutable
  commit `e18b38f9` with migrations through `0026`.
- Three first-party pilot nodes completed two fresh groups with three distinct
  verified signatures and evidence commitments per group on 2026-08-21.
- All three pilot nodes run the published `v0.1.0-preview.2` payload from commit
  `1472677d`; that exact Linux artifact passed production check and service
  rollout on Ubuntu 22.04. A live sealed tool-chain group reached healthy 3-of-5
  quorum with three verified signatures and no economic rows.
- Probe job IDs produced no credit, reservation, den, payout, or worker-ledger
  entries. Evidence remains economically inert.
- The three nodes share one operator and hypervisor. They do not prove an
  independent or decentralized validator cohort.

What is not production-live yet:

- Validator rewards.
- Validator staking/slashing.
- Core-issued media assignments and production media probe execution. The
  source node has dark image/video scoring paths, but Core withholds the work.
- Routing impact.
- On-chain epoch roots or dispute flow.
- Blind production-shaped quality audits and an ordinary paid audit-job rail;
  the current post-job zero-den acknowledgment remains a retrospective probe
  fingerprint.

Runtime Core capability flags are the source of truth. Operators should run
`check --no-probe` before their first assignment probe. The public preview is
evidence-only: it has no economic authority, and independent operator operation
is not yet proven.

## Download

The public V0 preview is published as
[`v0.1.0-preview.3`](https://github.com/AIPowerGrid/grid-validator/releases/tag/v0.1.0-preview.3).
It is an unsigned, non-economic operator preview, not a stable release.

Expected release assets:

| Platform | File |
|---|---|
| Windows x64 | `aipg-validator-windows-x64.zip` |
| macOS ARM64 | `aipg-validator-macos-arm64.zip` |
| Linux x64 | `aipg-validator-linux-x64.zip` |
| Linux ARM64 | `aipg-validator-linux-arm64.zip` |

Linux binaries target glibc 2.35 or newer (Ubuntu 22.04 or a comparable
distribution). Alpine/musl hosts should use Docker or the source install.

Every release also carries `install-validator.sh`, `install-validator.ps1`, `validator-release.json`,
`SHA256SUMS`, an SPDX JSON SBOM, and GitHub build provenance. The release
manifest binds the exact version, tag, source commit, asset sizes, and asset
hashes, plus the platform-signing state; `SHA256SUMS` covers the manifest
itself. The `v0.1.0-preview.3` macOS and Windows binaries are explicitly unsigned:
macOS is not Developer ID signed or notarized, and Windows is not Authenticode
signed. Verify `SHA256SUMS` and GitHub provenance before running them. Stable
releases remain blocked until both platform-signing gates are satisfied. The
installer verifies the platform archive checksum. GitHub immutable releases
prevent a published tag or asset from being silently replaced; a correction is
always a new version.
Operators can add provenance verification with:

```bash
gh attestation verify aipg-validator-linux-x64.zip \
  --repo AIPowerGrid/grid-validator
```

Once published, download the installer from the exact preview release, verify
its GitHub provenance, and run it:

```bash
curl -fsSLO https://github.com/AIPowerGrid/grid-validator/releases/download/v0.1.0-preview.3/install-validator.sh
gh attestation verify install-validator.sh --repo AIPowerGrid/grid-validator
AIPG_VALIDATOR_VERSION=v0.1.0-preview.3 bash install-validator.sh
cd ~/.aipg-validator
aipg-validator init
aipg-validator check --no-probe
aipg-validator dashboard
aipg-validator run
```

On Windows x64, use PowerShell. The required switch acknowledges that the
preview executable is not Authenticode signed; the installer verifies SHA-256
before installing or executing it:

```powershell
Invoke-WebRequest https://github.com/AIPowerGrid/grid-validator/releases/download/v0.1.0-preview.3/install-validator.ps1 -OutFile install-validator.ps1
gh attestation verify install-validator.ps1 --repo AIPowerGrid/grid-validator
$env:AIPG_VALIDATOR_VERSION = "v0.1.0-preview.3"
.\install-validator.ps1 -AcceptUnsignedPreview
```

Running nodes check the public GitHub release feed at most every six hours and
log a notice when a newer valid tag exists. They never download or install an
update. Set `VALIDATOR_UPDATE_CHECK=false` to disable the notification. Upgrade
by rerunning the exact-version installer and verifying checksum/provenance again.

Operators can stop new assignments with a signed `aipg-validator suspend` and
resume through `aipg-validator check --no-probe`. `aipg-validator rotate`
preserves the stable validator ID while binding a different signing wallet that
has already been linked to the same Grid account. Wallet rotation and API-key
rotation are separate: replace and revoke the old validator API key in the
Console as part of the same procedure. See [OPERATORS.md](OPERATORS.md).

## Quick Start

Requires Python 3.10+.

From source:

```bash
git clone https://github.com/AIPowerGrid/grid-validator
cd grid-validator

./install.sh
./.venv/bin/aipg-validator check --no-probe
./.venv/bin/aipg-validator dashboard
./.venv/bin/aipg-validator check
./.venv/bin/aipg-validator run
```

`install.sh` creates the virtualenv and installs the package. When it is run
from an interactive terminal and `.env` does not exist, it also launches
`aipg-validator init`. In non-interactive automation it skips config creation;
run `./.venv/bin/aipg-validator init` yourself, or create `.env` from
`.env.template`.

Required V0 identity config:

```ini
GRID_API_URL=https://api.aipowergrid.io
VALIDATOR_API_KEY=your-grid-api-key
VALIDATOR_WALLET=0xYourLinkedWallet
VALIDATOR_PRIVATE_KEY=0xYourLocalSigningKey
VALIDATOR_REQUIRE_STAKE=false
```

Assignments are persisted before probing in
`~/.aipg-validator/state.sqlite3`, then atomically replaced by their signed
attestations before delivery. If the node restarts after Core completes a probe,
it requests Core's committed result instead of running the worker again. Failed
attestation submissions are retried before new work. The database stores
short-lived synthetic assignments and public signed envelopes, never the
validator private key.

`check` validates config, registers the node, prints validator capability flags,
shows aggregate scorecard availability, runs one assigned probe round, and
prints the accepted attestation count. If no assignment is available, it fails
clearly instead of reporting a green no-op. Use
`check --no-probe` for an install/API smoke test that does not submit canary
traffic.

First-run command meanings:

| Command | Sends canary jobs? | Purpose |
|---|---:|---|
| `aipg-validator init` | no | write local `.env` with `chmod 600` |
| `aipg-validator check --no-probe` | no | config, Grid, capability, and scorecard smoke |
| `aipg-validator dashboard` | no | local read-only status page |
| `aipg-validator queue status` | no | inspect pending/dead assignments and attestations |
| `aipg-validator queue retry-dead` | no | explicitly retry dead letters after review |
| `aipg-validator check` | yes | register and run one assigned text probe round |
| `aipg-validator run` | yes | continuous V0 probe loop |

Optional dark-lane dependencies can be added from source when testing image or
video scoring and the future stake gate:

```bash
./.venv/bin/python -m pip install -e '.[media,stake]'
```

Once downloadable binaries are published, use the exact release installer
shown in the Download section, then:

```bash
cd ~/.aipg-validator
aipg-validator init
aipg-validator check --no-probe
aipg-validator dashboard
aipg-validator run
```

After a GitHub release exists, the same installer can be run from a checkout:

```bash
./scripts/install-binary.sh
```

`dashboard` starts a read-only local status page at
`http://127.0.0.1:8790/`. It shows config health, registration, Grid
reachability, validator-visible worker/model inventory, capability flags,
aggregate evidence scorecards, and stake mode. It never renders secrets.

During the V0 preview, use a dedicated validator signing wallet linked to the
same Grid account that issued the validator key. The private key stays local.
Answer `no` when setup asks whether on-chain stake is required. That writes:

```ini
VALIDATOR_REQUIRE_STAKE=false
```

Signing is required independently of the future stake gate. `init` derives the
wallet address from the required private key and refuses mismatched identity.

## Docker

Build locally:

```bash
docker build -t aipowergrid/validator:local .
```

Run a one-shot config/Grid check:

```bash
docker run --rm \
  --mount type=bind,source="$PWD/.env",target=/app/.env,readonly \
  aipowergrid/validator:local check --no-probe
```

Run the validator loop:

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

Or use Compose:

```bash
docker compose run --rm validator check --no-probe
docker compose up -d validator
docker compose --profile dashboard up -d validator-dashboard
```

## Service Install

On Linux hosts, install a systemd unit after `.env` is configured:

```bash
./scripts/install-systemd.sh --dry-run
sudo ./scripts/install-systemd.sh
journalctl -u aipg-validator -f
```

For a released binary installed on `PATH`, use the same helper:

```bash
sudo AIPG_VALIDATOR_EXEC="$(command -v aipg-validator)" \
  ./scripts/install-systemd.sh --workdir /var/lib/aipg-validator --user aipg
```

## Operator Guide

Read [OPERATORS.md](OPERATORS.md) for:

- detailed setup flow after the quickstart
- systemd service install
- local dashboard
- troubleshooting
- current reward/staking expectations
- what the node does and does not prove in V0

Read [DESIGN.md](DESIGN.md) for:

- validator phases
- text/image/video validation plan
- reference worker pool
- attestation model with V0 evidence hashes and future Grid-issued assignment
  requirements
- future Base anchoring, staking, and slashing

Read [ROADMAP.md](ROADMAP.md) for the concrete build order and go/no-go
boundaries from the V0 preview through targeted assignments, media validation,
and Base-anchored rewards.

Read [RELEASE_V0.md](RELEASE_V0.md) before publishing a validator release or
deploying the console scorecard surface. It is the operator-facing rollout
sequence across core, console, and grid-validator.

## Target Product Shape

The eventual hosted bootstrap should mirror the worker experience. It is not a
public install surface until DNS, hosting, and an exact-release test are live:

```bash
curl -fsSL https://get.aipowergrid.io/validator | bash
cd ~/.aipg-validator
aipg-validator init
aipg-validator check --no-probe
aipg-validator dashboard
aipg-validator run
```

And:

```bash
docker run \
  --mount type=bind,source="$PWD/.env",target=/app/.env,readonly \
  aipowergrid/validator:latest
```

Until that hosted bootstrap and a public image are published, use the
provenance-verified release installer, direct archive, local Docker build, or
source install above.

## Verification

```bash
./.venv/bin/python -m compileall validator
./.venv/bin/python -m unittest discover -s tests
./.venv/bin/aipg-validator --help
./.venv/bin/python -m validator --help
bash -n install.sh scripts/classify-release-tag.sh scripts/install-binary.sh \
  scripts/install-systemd.sh scripts/smoke-release.sh scripts/verify-release-assets.sh
./scripts/install-systemd.sh --dry-run --exec ./.venv/bin/aipg-validator
./scripts/smoke-release.sh
docker build -t aipowergrid/validator:local .
docker run --rm \
  --mount type=bind,source="$PWD/.env",target=/app/.env,readonly \
  aipowergrid/validator:local check --no-probe
```

Release-binary smoke test:

```bash
./.venv/bin/python -m pip install -e '.[release]'
./.venv/bin/pyinstaller --onefile --name aipg-validator-local \
  --specpath build/pyinstaller-local validator/__main__.py
./dist/aipg-validator-local --help
```

Also run at least one release-binary `check --no-probe` from a temp working
directory with only a local `.env`; that proves the binary does not depend on the
source checkout.

`./scripts/smoke-release.sh` bundles the operator-grade local smoke path. It uses
throwaway offline config and checks source, dashboard, Docker, release binary,
and installer behavior without touching your live `.env`.

## Security

- Report suspected vulnerabilities privately using [SECURITY.md](SECURITY.md).
- Keep `.env` private: `chmod 600 .env`.
- Prefer mounting `.env` read-only in Docker instead of passing secrets with
  `--env-file`.
- `VALIDATOR_PRIVATE_KEY` is required in V0 because registration and evidence
  are signed even though staking and rewards are disabled. `VALIDATOR_WALLET`
  must be the wallet derived from that key and a valid `0x` EVM address.
- Do not commit static challenge answers, golden pHashes, private prompts, live
  scoring secrets, or private policy thresholds into this public repo.
- One validator should not validate its own worker once targeted assignment
  exists.
