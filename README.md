# AIPG Validator Node

Validator nodes are the Grid's distributed audit runners. They send small canary
jobs through the normal Grid path, check whether workers follow the job contract,
and submit signed evidence back to the Grid.

V0 is intentionally humble: **observe, score, and attest first; route/reward/slash
later.** The node should be easy to run before it is allowed to carry economic
authority.

Start with [QUICKSTART.md](QUICKSTART.md) if you just want to run a preview node.
Read [PREVIEW_COHORT.md](PREVIEW_COHORT.md) to join the first independent
operator cohort and complete the 72-hour qualification run.
Use [OPERATORS.md](OPERATORS.md) when you are installing it as an always-on
service, [RELEASE_V0.md](RELEASE_V0.md) for the cross-repo rollout order, and
[DESIGN.md](DESIGN.md) for the full validator story across text, image, video,
reference workers, and Base anchoring.

## V0 Scope

What is implemented and testable against the candidate Core:

- CPU-only source install.
- Dockerfile and local Docker Compose.
- `init`, `check`, `dashboard`, and `run` CLI flow.
- Editable package install with the `aipg-validator` console command.
- Module entrypoint for `python -m validator`.
- Read-only local dashboard on `127.0.0.1:8790`.
- Assignment-bound text canaries through validator-only Core endpoints.
- Randomized text scoring: exact nonce echo, generated arithmetic, strict JSON,
  context retrieval, generated multistep logic, exact function calls, a
  two-stage function-call chain, stop-sequence compliance, and latency
  classification.
- Mandatory signed registration, heartbeat, and attestations from a wallet
  linked to the validator's Grid account.
- Small default install: V0 text probing plus signing. Optional `media` and
  `stake` extras install heavier future-lane dependencies.
- GitHub Actions release workflow scaffold for downloadable binaries.
- Grid-issued text assignments with short-lived nonces.
- Targeted probe execution at
  `POST /v1/validator/probe/{assignment_id}`; the core, not the validator,
  selects the worker.
- Independent result binding and scoring: the node matches every returned
  assignment field, recomputes the prompt/response/evidence hashes, and applies
  its local scorer against an expected-answer hash before signing. Core does not
  return its private answer or verdict; a mismatch is skipped.
- Shared probe groups target five distinct registered validator accounts and
  require three matching votes. This proves distinct evidence identities, not
  independently controlled operators.
- Core admits a node to a probe group only when its registration advertises the
  matching local scorer. Legacy `text.basic.v1` nodes remain limited to
  echo/arithmetic instead of mis-scoring newer challenge families.
- All current validator evidence has `economic_effect: none`: it does not alter
  routing, rewards, strikes, payouts, or bonds.
- Fail-closed behavior when registration, assignment, or targeted-probe support
  is unavailable; read-only dashboard metadata may degrade gracefully.

What is not production-live yet:

- Core migrations through `0024` and the shared-quorum validator API rollout.
  Quorum lands in `0022`; the later dark media schema must still match the
  deployed Core candidate even though media assignments stay disabled.
- Public downloadable binary releases.
- Published Docker image release.
- Validator rewards.
- Validator staking/slashing.
- Media/video probe loop integration.
- Routing impact.
- On-chain epoch roots or dispute flow.

Runtime Core capability flags are the source of truth. Until the migration and
endpoint smoke tests pass in production, operators should use `check --no-probe`
only; the public release remains closed. Current evidence has no economic
authority; independent operator operation is not yet proven.

## Download

Public binary releases are planned for the V0 canary. Until the first release
exists, use the source or local Docker paths below.

Expected release assets:

| Platform | File |
|---|---|
| Windows x64 | `aipg-validator-windows-x64.zip` |
| macOS ARM64 | `aipg-validator-macos-arm64.zip` |
| Linux x64 | `aipg-validator-linux-x64.zip` |
| Linux ARM64 | `aipg-validator-linux-arm64.zip` |

Every release also carries `install-validator.sh`, `SHA256SUMS`, an SPDX JSON
SBOM, and GitHub build provenance. The installer verifies the platform archive
checksum. Operators can add provenance verification with:

```bash
gh attestation verify aipg-validator-linux-x64.zip \
  --repo AIPowerGrid/grid-validator
```

Once published, download the installer from the exact preview release, verify
its GitHub provenance, and run it:

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

Signed attestations are persisted before delivery in
`~/.aipg-validator/state.sqlite3`. A temporary Core or network failure is
retried on later rounds without re-running the assignment. The database stores
only public signed envelopes, never the validator private key.

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
| `aipg-validator check` | yes | register and run one assigned text probe round |
| `aipg-validator run` | yes | continuous V0 probe loop |

Optional future-lane dependencies can be added from source when you are testing
them:

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
