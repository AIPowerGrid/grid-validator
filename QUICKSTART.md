# Validator Quickstart

Run a validator when you want to help measure Grid worker quality without
running a generation model yourself. V0 validators are CPU-only audit runners:
they send small canary jobs through the normal Grid API, score the result, and
submit signed evidence through Core's validator attestation endpoint.

V0 is evidence-only. It does not pay validator rewards, slash workers, change
routing, or prove exact model weights.

Rollout status: sealed shared-quorum text validation is live in production and
the immutable `v0.1.0-preview.13` release is the required cohort baseline.
Older preview.9 nodes are upgrade-required and cannot fill an independent
quorum seat. The evidence lane is unpaid and cannot change routing, rewards,
worker status, strikes, bonds, or slashing. See the public
[network status](https://console.aipowergrid.io/network) for current activity
and [PREVIEW_COHORT.md](PREVIEW_COHORT.md) for the 72-hour independent-operator
gate. Begin with `check --no-probe` before running an assignment probe.

## What You Need

**New setup (preview.13):** use the local operator app, or `aipg-validator enroll`, to create a dedicated node account
after confirmation. It saves an empty local signer, signs Core's short-lived
login challenge, and obtains a validator-only API key. No Google/GitHub login,
wallet extension, or pasted private key is needed. Upgrade older binaries to
preview.13 instead of exporting a personal wallet key.
Existing-account pairing is separate and not yet available. Keep existing
configured nodes on their current identities.

- A machine that can stay online.
- Python 3.10+ for the source preview.
- Permission to create a dedicated node account during setup.
- No GPU.
- No Base stake requirement during the V0 preview.

`enroll` writes the configuration automatically and keeps
`VALIDATOR_REQUIRE_STAKE=false`. The signing key stays on the node; Core
receives only signatures and the public wallet. Back up the private config
file, but never send it to support or post it in Discord.

## Source Preview

```bash
git clone https://github.com/AIPowerGrid/grid-validator
cd grid-validator

./install.sh
./.venv/bin/aipg-validator enroll
./.venv/bin/aipg-validator check --no-probe
./.venv/bin/aipg-validator dashboard
```

`./install.sh` creates `.venv` and installs the package. It does not generate an
identity automatically. `enroll` requires confirmation, writes a private local
identity (POSIX `0600` / Windows owner-only DACL), authenticates it with Core,
and saves its scoped API key. An interrupted attempt reuses the same signer;
an already configured node is not changed. It never enables stake or moves funds.

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
| `prepare-wallet` | no | creates the local signing identity and prints only its address |
| `enroll` | no | confirmed dedicated-account wallet authentication and scoped-key issuance |
| `init` | no | advanced API-key configuration for an already prepared signer |
| `check --no-probe` | no | validates config and Grid reachability |
| `dashboard` | no | read-only localhost view |
| `check` | yes | sends one small V0 text canary round |
| `run` | yes | keeps sending V0 canaries on the configured interval |

## Binary Install

Use the immutable preview release for the public binary path:

| Platform | Release asset |
|---|---|
| Windows x64 | `aipg-validator-windows-x64.zip` |
| macOS ARM64 | `aipg-validator-macos-arm64.zip` |
| Linux x64 | `aipg-validator-linux-x64.zip` |
| Linux ARM64 | `aipg-validator-linux-arm64.zip` |

The Linux binaries target glibc 2.35 or newer (Ubuntu 22.04 or a comparable
distribution). Use Docker or the source install on Alpine/musl.

The released installer verifies the downloaded archive against `SHA256SUMS`.
Download it from the exact preview release and verify its build provenance
before running it:

> **Unsigned preview:** the macOS binary is not Developer ID signed or
> notarized, and the Windows binary is not Authenticode signed. Your OS will
> warn before execution. Verify `SHA256SUMS` and GitHub provenance. Linux and
> Docker are the least-friction preview paths.

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

Windows x64: see the double-click steps below. Optional PowerShell installer:

```powershell
Invoke-WebRequest https://github.com/AIPowerGrid/grid-validator/releases/download/v0.1.0-preview.13/install-validator.ps1 -OutFile install-validator.ps1
gh attestation verify install-validator.ps1 --repo AIPowerGrid/grid-validator
.\install-validator.ps1 -AcceptUnsignedPreview
```

The acknowledgement switch is mandatory because the preview executable is not
Authenticode signed. The installer verifies its SHA-256 checksum before the
binary is installed or executed.

### Windows First Run

1. Download the preview.13 Windows x64 ZIP, verify its checksum/provenance,
   and extract it.
2. Double-click `aipg-validator.exe`. The menu stays open; PowerShell is not
   required. Opening the menu does not create credentials or start probes.
3. Choose **8. Open local operator app** to open its private local browser page.
4. Choose **Set up node**, confirm dedicated-account creation, then choose
   **Start validator**. Confirm acknowledged heartbeats and accepted evidence,
   not just registration. Waiting during assignment cooldown is normal.
5. Use **Stop** to stop the node without deleting its identity. **Exit app** also
   closes the local app. Closing only the browser tab leaves it running.

The displayed config path reuses `VALIDATOR_ENV`, an existing local `.env`, or
`$HOME/.aipg-validator/.env`. Preserve that file across upgrades. Existing
operators with working configuration should skip new enrollment and choose
**Start validator**. The older menu setup/check/run options still work.
If setup reports an existing identity, stop and keep it; do not delete it to
force a new account. Existing-account/browser pairing is not implemented yet.
The API key authorizes requests; the locally generated signer signs evidence.
Neither credential should be shared, and no personal wallet key should be pasted.

On macOS/Linux desktops, `aipg-validator app` opens the same controls. Keep its
private localhost URL private and never forward its port. **Download diagnostics**
provides redacted status for support, not keys or raw logs. See
[OPERATORS.md](OPERATORS.md#local-operator-app).

The running node checks for a newer public release at most every six hours and
prints a notification only. It never self-updates. To upgrade, rerun the
installer with the new exact `AIPG_VALIDATOR_VERSION`, then repeat
`aipg-validator check --no-probe`. Set `VALIDATOR_UPDATE_CHECK=false` to opt out.

For maintenance, `aipg-validator suspend` signs a request that stops new
assignments; `aipg-validator check --no-probe` resumes the same wallet. Signing
wallet recovery is a separate `aipg-validator rotate` workflow after the same
Grid account links a different replacement wallet and issues a replacement
validator API key. Follow [OPERATORS.md](OPERATORS.md) and revoke the old API
key after the replacement checks healthy.

The versioned GitHub binaries and exact preview container are public. Anonymous
GHCR access to `v0.1.0-preview.13` is verified for Linux x64 and ARM64. Keep the
version explicit: prereleases never publish or replace `latest`.

## Docker

```bash
docker pull ghcr.io/aipowergrid/validator:v0.1.0-preview.13
docker run --rm ghcr.io/aipowergrid/validator:v0.1.0-preview.13 self-test
docker run --rm \
  --mount type=bind,source="$PWD/.env",target=/app/.env,readonly \
  ghcr.io/aipowergrid/validator:v0.1.0-preview.13 check --no-probe
```

Run the loop:

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

Build `aipowergrid/validator:local` from the reviewed checkout only when you
intend to test source changes instead of the immutable cohort release.

## Systemd

After `.env` is configured and `check --no-probe` passes, run the helper from a
reviewed checkout. For a binary install in `~/.local/bin`, the lowest-friction
cohort path is:

```bash
git clone --depth 1 https://github.com/AIPowerGrid/grid-validator.git \
  /tmp/grid-validator-service-helper
cd /tmp/grid-validator-service-helper
sudo AIPG_VALIDATOR_EXEC="$HOME/.local/bin/aipg-validator" \
  AIPG_VALIDATOR_WORKDIR="$HOME/.aipg-validator" \
  ./scripts/install-systemd.sh --dry-run
sudo AIPG_VALIDATOR_EXEC="$HOME/.local/bin/aipg-validator" \
  AIPG_VALIDATOR_WORKDIR="$HOME/.aipg-validator" \
  ./scripts/install-systemd.sh
sudo systemctl status aipg-validator --no-pager
sudo journalctl -u aipg-validator -f
```

The helper keeps secrets in `.env`, keeps the durable journal writable only in
the private work directory, and refuses to start the service when `.env` is
missing. Do not run the local app's validator child at the same time as the
systemd service. The helper comes from reviewed `master`; the service still
runs the immutable preview.13 binary installed above.

## Healthy Output

A healthy V0 node should show:

- config loaded
- Grid reachable
- validator capability flags visible, or safely reported as unavailable
- registration is active for the configured wallet
- `check` reports at least one submitted assignment, or clearly says none are available
- `aipg-validator queue status` reports no unexplained dead letters
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
| `POST /v1/validator/suspend` | for `suspend` | stop new assignments with a current-wallet signature |
| `POST /v1/validator/rotate` | for `rotate` | preserve identity while binding a newly linked wallet |
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
multistep logic, restricted-AST Python function synthesis against hidden inputs,
one exact randomized function call, one two-stage tool-call chain, and one
randomized stop-sequence check. It also samples gross
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
