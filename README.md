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
- Public versioned multi-architecture container plus local Docker Compose.
- Consent-based `enroll`, `check`, `dashboard`, and `run` CLI flow.
- Editable package install with the `aipg-validator` console command.
- Module entrypoint for `python -m validator`.
- Read-only local dashboard on `127.0.0.1:8790`.
- Preview.13 includes opt-in `aipg-validator app` browser controls for
  explicit setup, start/stop, participation status, and redacted diagnostics.
  See the [local app runbook](OPERATORS.md#local-operator-app).
- Assignment-bound text canaries through validator-only Core endpoints.
- Randomized text scoring: exact nonce echo, generated arithmetic, strict JSON,
  calibrated 4K, 16K, and 32K context retrieval, generated multistep logic, exact
  restricted-AST Python function synthesis against hidden inputs, function
  calls, a two-stage function-call chain, stop-sequence compliance, gross
  output-budget compliance, and latency classification.
- Mandatory signed registration, heartbeat, and attestations from a wallet
  linked to the validator's Grid account.
- Small default source install: V0 text probing plus signing. Optional `media`
  and `stake` extras install heavier future-lane dependencies. Binary and
  container builds from current `master` include the locked `media` extra and must pass an
  offline bounded-decoder self-test on every supported platform. The scorers
  remain dark unless an operator configures an explicit HTTPS media origin and
  Core independently enables assignment issuance.
- GitHub Actions release workflow scaffold for downloadable binaries.
- Grid-issued text assignments with short-lived nonces.
- Targeted probe execution at
  `POST /v1/validator/probe/{assignment_id}`; the core, not the validator,
  selects the worker.
- Sealed-assignment execution: production Core withholds the target, model,
  nonce, and challenge until the worker finishes. The node verifies their
  SHA-256 commitment before it scores or signs the result. Compatibility code
  for a staged unsealed rollout remains, but production uses the sealed form.
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
  commit `4e0eb3f6b883218502b01d550c7cdeed7f9a0dd2` as checked on
  2026-09-01, with migrations through `0031`. Core requires
  `v0.1.0-preview.13` for candidate/verified qualification and excludes older
  releases from independent quorum.
- Core also contains a dark, atomic accounting terminal for future
  compensated quality audits. No scheduler, audit corpus, scoring policy, or
  operator configuration is enabled, and both production audit tables were
  empty after deployment. Existing assignment probes remain unpaid and
  economically inert.
- The 2026-09-01 public snapshot reported ten active registrations, seven fresh
  and participating nodes, 674 completed assignments, 641 authoritative
  evidence votes, eight covered workers, and seven covered models. Four nodes
  still reported preview.9 and three reported the required preview.13.
- One confirmed preview.13 candidate was online at 26.1 of 72 required hours
  with 97.45% heartbeat-sample coverage, 251 completed assignments, and 237
  attestations. No operator had completed independent qualification.
- On the earlier preview.5 payload, after the one-hour worker/model cooldown
  elapsed on 2026-08-27, the same nodes completed two fresh sealed groups. A
  16K-context group reached
  `accepted / healthy` with three authoritative votes. A token-limit group
  reached `disputed` after one healthy and two failed votes; disagreement is
  retained rather than forced into consensus.
- Each fresh group has three assignments, three distinct Grid nonces, three
  evidence commitments, and three verified signatures. Their six probe job IDs
  produced zero credit-ledger, reservation, den-event, or worker-ledger rows.
  Evidence remains economically inert.
- The three nodes share one operator and hypervisor. They do not prove an
  independent or decentralized validator cohort.

The evidence lane is useful production observability today, but it has no
economic or routing authority. The broader Grid roadmap continues while
independent operators qualify in parallel. Three recently active qualified
operators trigger an authority-readiness review; they do not automatically
activate validator control or economics.

What is not production-live yet:

- Validator rewards.
- Validator staking/slashing.
- Core-issued media assignments and production media probe execution. The
  source node has dark image/video scoring paths, but Core withholds the work.
- Routing impact.
- On-chain epoch roots or dispute flow.
- Scheduling and scoring for blind production-shaped quality audits. Their
  atomic accounting terminal is deployed dark, but it cannot originate work.
  The current assignment probes still use a post-job zero-den acknowledgment,
  which remains a retrospective probe fingerprint.

Runtime Core capability flags are the source of truth. Operators should run
`check --no-probe` before their first assignment probe. The public preview is
evidence-only: it has no economic authority, and independent operator operation
is not yet proven.

## Download

Preview.13 includes the local operator app (menu option 8) and explicit
`aipg-validator enroll` (menu option 1): enrollment
creates a dedicated local signer, authenticates a separate node account, and
saves a validator-only API key without private-key entry. Existing-account pairing remains separate;
do not export a personal wallet key or replace a running node's identity.

Source development adds an optional **Account link** flow in the local app.
It is **not in preview.13 or enabled in production**. See
[Account Pairing](ACCOUNT_PAIRING.md) for its consent, recovery and rollout gates.

The current public V0 preview is
[`v0.1.0-preview.13`](https://github.com/AIPowerGrid/grid-validator/releases/tag/v0.1.0-preview.13).
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
itself. The `v0.1.0-preview.13` macOS and Windows binaries are explicitly unsigned:
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

Download the installer from the exact preview release, verify
its GitHub provenance, and run it:

```bash
curl -fsSLO https://github.com/AIPowerGrid/grid-validator/releases/download/v0.1.0-preview.13/install-validator.sh
gh attestation verify install-validator.sh --repo AIPowerGrid/grid-validator
bash install-validator.sh
cd ~/.aipg-validator
aipg-validator enroll
aipg-validator self-test
aipg-validator check --no-probe
aipg-validator run
```

On Windows x64, extract the ZIP and double-click `aipg-validator.exe`. Choose
**8** to open the local app, **Set up node** and confirm, then **Start validator**.
Existing operators skip setup and start with their preserved configuration.
Watch for acknowledged heartbeats and accepted evidence, not just registration.
No PowerShell, Google/GitHub login, funded wallet,
or pasted private key is needed for enrollment. Keep existing configuration
when upgrading; do not create a replacement identity for a running node.

On macOS/Linux desktops, run `aipg-validator app` after installing. The page is
localhost-only. Closing its tab leaves the node running; **Exit app** stops its
owned process and closes the local server. The CLI below remains suitable for
headless hosts.

Alternatively, use the PowerShell installer. The required switch acknowledges that the
preview executable is not Authenticode signed; the installer verifies SHA-256
before installing or executing it:

```powershell
Invoke-WebRequest https://github.com/AIPowerGrid/grid-validator/releases/download/v0.1.0-preview.13/install-validator.ps1 -OutFile install-validator.ps1
gh attestation verify install-validator.ps1 --repo AIPowerGrid/grid-validator
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
./.venv/bin/aipg-validator enroll
./.venv/bin/aipg-validator check --no-probe
./.venv/bin/aipg-validator check
./.venv/bin/aipg-validator run
```

`install.sh` creates the virtualenv and installs the package, but never invents
account credentials. On a fresh checkout, confirm `enroll` to generate a
dedicated local signer, authenticate its node account, and save its scoped key.
Keep the private configuration backed up. Existing-account pairing is not part
of this flow; it does not merge accounts or change payout wallets.

Enrollment writes these V0 configuration fields automatically. The values below
are placeholders for reference, not instructions to paste a wallet key:

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

`check` validates config, registers the node, prints the authenticated
operator's qualification progress, prints validator capability flags, shows
aggregate scorecard availability, runs one assigned probe round, and
prints the accepted attestation count. If no assignment is available, it fails
clearly instead of reporting a green no-op. Use
`check --no-probe` for an install/API smoke test that does not submit canary
traffic.

First-run command meanings:

| Command | Sends canary jobs? | Purpose |
|---|---:|---|
| `aipg-validator enroll` | no | confirm dedicated-account creation; save its signer and validator-only key locally |
| `aipg-validator prepare-wallet` | no | generate a local signing identity in `.env` with `chmod 600`; print only its public address |
| `aipg-validator init` | no | advanced API-key configuration for an already prepared signer |
| `aipg-validator check --no-probe` | no | config, Grid, capability, and scorecard smoke |
| `aipg-validator self-test` | no | offline bounded image/video decoder qualification |
| `aipg-validator dashboard` | no | local read-only status page |
| `aipg-validator queue status` | no | inspect pending/dead assignments and attestations |
| `aipg-validator queue retry-dead` | no | explicitly retry dead letters after review |
| `aipg-validator check` | yes | register and run one assigned text probe round |
| `aipg-validator run` | yes | continuous V0 probe loop |

The default source install stays text-only. Add optional dark-lane dependencies
when testing image/video scoring or the future stake gate:

```bash
./.venv/bin/python -m pip install -e '.[media,stake]'
```

Use the exact release installer
shown in the Download section, then:

```bash
cd ~/.aipg-validator
aipg-validator enroll
aipg-validator self-test
aipg-validator check --no-probe
aipg-validator run
```

From a source checkout, select the exact version explicitly:

```bash
AIPG_VALIDATOR_VERSION=v0.1.0-preview.13 ./scripts/install-binary.sh
```

`dashboard` starts a read-only local status page at
`http://127.0.0.1:8790/`. It shows config health, registration, Grid
reachability, validator-visible worker/model inventory, capability flags,
aggregate evidence scorecards, and stake mode. It never renders secrets.

During the V0 preview, use a dedicated validator signing wallet linked to the
same Grid account that issued the validator key. The private key stays local.
Automatic enrollment keeps on-chain stake enforcement off:

```ini
VALIDATOR_REQUIRE_STAKE=false
```

Signing is required independently of the future stake gate. `enroll`
uses the operating system CSPRNG, stores the private key only in the local
mode-`0600` `.env` (owner-only DACL on Windows), and never prints that key.
Advanced `prepare-wallet` and `init` remain available for an already linked
dedicated identity; they are not the normal first-run path.

## Docker

Pull the exact public preview image. It is anonymously available for Linux x64
and ARM64; prereleases never publish or replace `latest`:

```bash
docker pull ghcr.io/aipowergrid/validator:v0.1.0-preview.13
```

The preview bundles the dark image/video decoders. Qualify the exact image
without contacting the Grid:

```bash
docker run --rm ghcr.io/aipowergrid/validator:v0.1.0-preview.13 self-test
```

Run a one-shot config/Grid check:

```bash
docker run --rm \
  --mount type=bind,source="$PWD/.env",target=/app/.env,readonly \
  ghcr.io/aipowergrid/validator:v0.1.0-preview.13 check --no-probe
```

Run the validator loop:

```bash
docker run -d --name aipg-validator --restart unless-stopped \
  --mount type=bind,source="$PWD/.env",target=/app/.env,readonly \
  ghcr.io/aipowergrid/validator:v0.1.0-preview.13
```

Run the dashboard:

```bash
docker run --rm -p 8790:8790 \
  --mount type=bind,source="$PWD/.env",target=/app/.env,readonly \
  ghcr.io/aipowergrid/validator:v0.1.0-preview.13 \
  dashboard --host 0.0.0.0
```

Build `aipowergrid/validator:local` from this checkout only when testing source
changes rather than the immutable cohort release.

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

For a released preview binary, use the commit- and checksum-pinned helper in
[QUICKSTART.md](QUICKSTART.md#systemd). Do not pipe a mutable remote script to a
shell. For a reviewed source checkout installed on `PATH`, the equivalent
command is:

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
aipg-validator enroll
aipg-validator check --no-probe
aipg-validator run
```

And:

```bash
docker run \
  --mount type=bind,source="$PWD/.env",target=/app/.env,readonly \
  aipowergrid/validator:latest
```

Until that hosted bootstrap and a stable `latest` image are published, use the
provenance-verified release installer, direct archive, exact versioned GHCR
image, local Docker build, or source install above.

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
