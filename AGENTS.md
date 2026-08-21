# DOX framework

- DOX is a hierarchy of AGENTS.md files that carry the durable contracts for this repo.
- Agents must follow the DOX chain on every edit.

## Core Contract

- AGENTS.md files are binding work contracts for their subtrees.
- Any work product must stay understandable from the nearest AGENTS.md plus every parent above it.

## Read Before Editing

1. Read this root AGENTS.md.
2. Identify every path you expect to touch.
3. Walk from repo root to each target, reading every AGENTS.md on the way.
4. The nearest AGENTS.md is the local contract; parents hold repo-wide rules.
5. If docs conflict, the closer doc controls local detail, but no child may weaken DOX.

Do not rely on memory — re-read the applicable chain in-session before editing.

## Update After Editing

Every meaningful change requires a DOX pass before the task is done. Update the closest
owning AGENTS.md when a change affects: purpose/scope/ownership; durable structure,
contracts, or workflows; inputs/outputs/permissions/side-effects; or the Child DOX Index.
Remove stale text immediately. Refresh affected parent and child indexes.

## Style

Concise, current, operational. Stable contracts, not diary entries. Broad rules in parents,
concrete detail in children. Delete stale notes instead of explaining history.

---

# grid-validator — distributed Grid validation node

## Purpose

The Grid's validator node. In V0 it is a CPU-only distributed audit runner: it sends
small canary jobs through the normal Grid path, scores replies (`healthy` / `slow` /
`failed`), and submits signed attestations when the Grid exposes the sink. The
shared-quorum Core implementation is merged but is not production-live until
migrations through `0022` and the matching immutable Core release are deployed. Once enabled,
`GET /v1/validator/assignments`, `POST /v1/validator/probe/{assignment_id}`, and
preview scorecards and distinct-validator 3-of-5 probe groups make evidence attributable, but still non-economic: no reward,
routing, strike, or slashing logic may read it as authority. Future phases harden adversarial
independent-operator proof, deterministic media workflow certification, rewards, staking, and
objective-fraud slashing. Do not describe future economic authority as live until the
Grid endpoints and contracts exist. Python package: `validator/`. Entry: `validator.main`.

## Ownership

- **`validator/`** — the whole node (config, stake gate, grid client, canary probing +
  scoring, attestation signing, probe loop, CLI, local dashboard). Owned in its own AGENTS.md.
- **`README.md`** — V0 scope, quick start, and target public distribution shape.
- **`QUICKSTART.md`** — one-page operator path that mirrors the worker quickstart:
  source preview, future binary install, Docker, systemd, health checks, and V0
  safety boundaries.
- **`OPERATORS.md`** — plain-language run guide (install, systemd, troubleshooting, FAQ).
- **`DESIGN.md`** — source of truth for validator phases, proof lanes, modality scoring,
  reference pool, future economics, Base anchoring, and Grid-side dependencies.
- **`ROADMAP.md`** — dev-manager build order from V0 preview through targeted
  validation, text/image/video policy work, and Base-anchored economics.
- **`RELEASE_V0.md`** — cross-repo evidence-only release runbook: core migration/API,
  console scorecards, validator packaging, canary operation, and rollback notes.
- **`pyproject.toml`** — package metadata and `aipg-validator` console script.
  Default dependencies cover V0 text probing plus signing; heavier future-lane
  dependencies live under `media` and `stake` extras. Do not reintroduce a
  parallel `requirements.txt`; it drifts from release builds.
- **`uv.lock`** — cross-platform dependency lock for release binaries. Release
  builds must use it with `uv sync --frozen`; update it deliberately with the
  pinned workflow uv version when package requirements change.
- **`Dockerfile` / `docker-compose.yml` / `.dockerignore`** — container packaging and
  local Compose run paths. The image uses a digest-pinned Python base and the
  same frozen `uv.lock` as release binaries; the final non-root stage does not
  carry the UV build tool.
- **`.github/workflows/`** — CI, checksum-verified secret scanning, image-release,
  and binary-release workflows.
  Tag pushes publish normal release artifacts. Manual binary releases must set
  `release_tag`; manual Docker publishes must set `image_tag`, with `latest`
  allowed only for stable tags. Preview/alpha/beta/RC images must never replace
  `latest`. A build-only binary dispatch still assembles and verifies the full
  payload, but skips provenance attestation, tag creation, and publication. A
  manual Docker dispatch defaults to multi-architecture build-only validation;
  `publish_image` must be explicit before login, push, or attestation.
  Third-party actions are commit-SHA pinned.
- **`scripts/install-binary.sh`** — GitHub Release binary installer intended to
  back the hosted `get.aipowergrid.io/validator` path. It installs the binary
  under `$HOME/.local/bin` by default and creates `$HOME/.aipg-validator` as
  the private config directory unless overridden.
  It verifies the selected archive against the release `SHA256SUMS`; signed
  GitHub provenance is verified separately with `gh attestation verify`.
- **`scripts/install-systemd.sh`** — Linux systemd service installer for source
  or released-binary validator nodes. Dry-run safe; generated unit must keep
  secrets in `.env`, not in the unit file.
- **`scripts/smoke-release.sh`** — full local release smoke: unit tests, CLI,
  dashboard, Docker, release binary, and binary installer using throwaway
  offline config. Use `SKIP_DOCKER=1` or `SKIP_BINARY=1` only when the local
  machine genuinely cannot run that lane.
- **`scripts/verify-release-assets.sh`** — publication gate for the exact four
  platform archives, checksum-covered installer, SPDX JSON SBOM, and
  `SHA256SUMS`. It verifies archive contents and rejects missing, extra, or
  mismatched manifest entries before provenance is attested.
- **`scripts/classify-release-tag.sh`** — shared binary/Docker tag policy.
  Only stable `vX.Y.Z` tags may publish `latest`; bounded prerelease tags such
  as `v0.1.0-preview` remain explicitly versioned.
- **`install.sh` / `aipg-validator.service` / `.env.template`** — source-checkout
  install + run-as-service. `install.sh` may launch interactive setup only when
  stdin is a terminal; non-interactive runs must skip setup and point operators
  to `aipg-validator init`.
- **`tests/`** — lightweight unit tests for V0 scoring/operator surfaces.

## Local Contracts

- **Inherit org engineering standards:**
  `../aipg-documentation/engineering-standards/`
  (core + git + the matching language file). The rules below are
  grid-validator specializations.
- **Early-stage / v0:** the node must register a linked signing wallet, use a
  dedicated key with exactly the validator scopes, and consume only Grid-issued
  assignments. Missing registration, assignment, or targeted-probe support is
  unavailable, never permission to submit public inference as a probe.
  Core atomically leases each assignment and permits only a bounded retry
  budget; the node must reuse issued work rather than invent assignments.
  Assignment-bound evidence includes the Grid assignment id, nonce, and probe
  group id/evidence hash. The node scores against an expected-answer commitment
  and never trusts Core's private verdict. Evidence remains input with no slash, reward,
  payout, strike, or routing authority.
- V0 text scorer capabilities are exact instruction following, generated
  arithmetic, strict JSON, context retrieval, generated multistep logic, and
  one exact randomized function call, a two-stage randomized tool chain, and
  randomized stop-sequence compliance. Token-budget honesty remains future
  work.
  They are usefulness samples, not proof of a model family or parameter count.
- The media witness fetch/verifier and independent `image.fidelity.v1` scorer
  are wired to assignment polling but remain Core-gated: exact
  operator-configured HTTPS origins, redirects and encoded responses disabled,
  bounded bytes/time/MIME, SHA-256 recomputation, structural checks, and pHash
  comparison only after two references agree. A node advertises the capability
  only when its media dependencies and HTTPS origin allowlist are ready; Core
  must still withhold assignments until every media rollout gate is complete.
- **Evidence delivery is durable:** persist the signed public envelope before
  HTTP submission, replay pending evidence before new work, and remove it only
  after Core accepts it. Never persist the private key in validator state.
- **Secrets:** `.env` may hold `VALIDATOR_PRIVATE_KEY` (signs attestations and later controls
  stake) — always chmod 600, never commit. The key never leaves the box; the grid receives only
  signed payloads. If the private key is configured, `VALIDATOR_WALLET` must be the derived
  wallet address.
- **Pay for verified-correct work, never presence.** Any future reward/scoring logic added here
  must track accepted useful attestations and consensus agreement, not attestation count.
- **Canaries must stay unpredictable.** Do not commit static challenge answer keys, golden
  pHashes, private prompts, or live scoring secrets into the public repo.
- On-chain reads (stake gate) fail fast and gate startup only when `VALIDATOR_REQUIRE_STAKE=true`;
  they are not on the probe hot path.

## Work Guidance

- New env vars: add to `validator/config.py` `Settings` (typed, with a
  default), not ad-hoc `getenv`.
- Keep heavy deps (web3, Pillow, imagehash) lazily imported and in optional
  extras so default V0 text validators stay small. `eth-account` remains a
  default dependency because signed V0 attestations are part of the preview.
- New grid-side endpoint dependencies fail closed when they are required for
  attributable evidence. Read-only dashboard metadata may degrade gracefully.

## Verification

- `./.venv/bin/python -m compileall validator`
- `./.venv/bin/python -m unittest discover -s tests`
- `./.venv/bin/aipg-validator --help`
- `./.venv/bin/python -m validator --help`
- `docker build -t aipowergrid/validator:local .`
- `docker run --rm --mount type=bind,source="$PWD/.env",target=/app/.env,readonly aipowergrid/validator:local check --no-probe`
- `bash -n install.sh scripts/classify-release-tag.sh
  scripts/install-binary.sh scripts/install-systemd.sh scripts/smoke-release.sh
  scripts/verify-release-assets.sh`
- `./scripts/smoke-release.sh`
- `./scripts/install-systemd.sh --dry-run --exec ./.venv/bin/aipg-validator`
- `gitleaks detect --source . --no-git --config .gitleaks.toml --redact`
- Release-binary smoke:
  `./.venv/bin/python -m pip install -e '.[release]'` then
  `./.venv/bin/pyinstaller --onefile --name aipg-validator-local`
  `--specpath build/pyinstaller-local validator/__main__.py`
  then `./dist/aipg-validator-local --help`; also run at least one
  `check --no-probe` smoke from a temp working directory with only a local
  `.env` to prove the binary does not depend on the source checkout.

## Child DOX Index

- [validator/AGENTS.md](validator/AGENTS.md) — the node: config, stake,
  probing, attestation, loop, CLI.
- [tests/AGENTS.md](tests/AGENTS.md) — validator protocol and operator-surface
  unit tests.
