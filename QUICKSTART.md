# Validator Quickstart

Run a validator when you want to help measure Grid worker quality without
running a generation model yourself. V0 validators are CPU-only audit runners:
they send small canary jobs through the normal Grid API, score the result, and
submit signed evidence through Core's validator attestation endpoint.

V0 is evidence-only. It does not pay validator rewards, slash workers, change
routing, or prove exact model weights.

Rollout status: sealed shared-quorum text validation is live on production Core
commit `43156ffd` with migrations through `0028`. Three first-party pilot nodes
run the exact published `v0.1.0-preview.8` payload from commit `122f5565`.
On the earlier preview.5 payload they completed a healthy 3-of-5 16K-context
group and correctly disputed a token-limit group, all without credit,
reservation, den, or payout side effects. This proves the live protocol, not
independent operation: the pilot nodes share one operator and hypervisor.
Target, model, nonce, and challenge are disclosed only after worker execution
and are verified against the assignment seal before signing. Begin with
`check --no-probe` before
running an assignment probe.

## What You Need

- A machine that can stay online.
- Python 3.10+ for the source preview.
- A Grid account you can sign into at the Console.
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
Create it with `aipg-validator prepare-wallet`, link the printed address at
`https://console.aipowergrid.io/dashboard/validators`, create the scoped
validator key there, and then run `aipg-validator init`. The command reuses the
prepared identity without printing or re-requesting its private key. This
evidence identity is mandatory even while `VALIDATOR_REQUIRE_STAKE=false`.

## Source Preview

```bash
git clone https://github.com/AIPowerGrid/grid-validator
cd grid-validator

./install.sh
./.venv/bin/aipg-validator prepare-wallet
# Link the printed address and create a validator key in the Console.
./.venv/bin/aipg-validator init
./.venv/bin/aipg-validator check --no-probe
./.venv/bin/aipg-validator dashboard
```

`./install.sh` creates `.venv` and installs the package. It does not generate an
identity automatically. `prepare-wallet` writes the private identity locally
with mode `0600` and prints only the address needed by the Console. `init`
completes that same file after the wallet is linked and the scoped key exists.

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
| `init` | no | writes local `.env`; no network call |
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
curl -fsSLO https://github.com/AIPowerGrid/grid-validator/releases/download/v0.1.0-preview.8/install-validator.sh
gh attestation verify install-validator.sh --repo AIPowerGrid/grid-validator
bash install-validator.sh
cd ~/.aipg-validator
aipg-validator prepare-wallet
# Link the printed address and create a validator key in the Console.
aipg-validator init
aipg-validator check --no-probe
aipg-validator dashboard
aipg-validator run
```

Windows x64 PowerShell:

```powershell
Invoke-WebRequest https://github.com/AIPowerGrid/grid-validator/releases/download/v0.1.0-preview.8/install-validator.ps1 -OutFile install-validator.ps1
gh attestation verify install-validator.ps1 --repo AIPowerGrid/grid-validator
.\install-validator.ps1 -AcceptUnsignedPreview
```

The acknowledgement switch is mandatory because the preview executable is not
Authenticode signed. The installer verifies its SHA-256 checksum before the
binary is installed or executed.

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
GHCR access to `v0.1.0-preview.8` is verified for Linux x64 and ARM64. Keep the
version explicit: prereleases never publish or replace `latest`.

## Docker

```bash
docker pull ghcr.io/aipowergrid/validator:v0.1.0-preview.8
docker run --rm \
  --mount type=bind,source="$PWD/.env",target=/app/.env,readonly \
  ghcr.io/aipowergrid/validator:v0.1.0-preview.8 check --no-probe
```

Run the loop:

```bash
docker run -d --name aipg-validator --restart unless-stopped \
  --mount type=bind,source="$PWD/.env",target=/app/.env,readonly \
  ghcr.io/aipowergrid/validator:v0.1.0-preview.8
```

Run the dashboard:

```bash
docker run --rm -p 8790:8790 \
  --mount type=bind,source="$PWD/.env",target=/app/.env,readonly \
  ghcr.io/aipowergrid/validator:v0.1.0-preview.8 \
  dashboard --host 0.0.0.0
```

Build `aipowergrid/validator:local` from the reviewed checkout only when you
intend to test source changes instead of the immutable cohort release.

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
