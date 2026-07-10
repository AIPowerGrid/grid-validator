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
`failed`), and submits signed attestations when the Grid exposes the sink. The current
Production Grid core exposes assignment-bound text probes (`GET /v1/validator/assignments`,
`POST /v1/validator/probe/{assignment_id}`) plus preview scorecards. These assignments
make evidence attributable, but they are still non-economic: no reward, routing, strike,
or slashing logic may read them as authority yet. Future phases harden adversarial
multi-validator quorum, deterministic media workflow certification, rewards, staking, and
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
- **`Dockerfile` / `docker-compose.yml` / `.dockerignore`** — container packaging and
  local Compose run paths.
- **`.github/workflows/`** — CI, image-release, and binary-release workflows.
  Tag pushes publish normal release artifacts. Manual binary releases must set
  `release_tag`; manual Docker publishes must set `image_tag`, with `latest`
  opt-in only.
- **`scripts/install-binary.sh`** — GitHub Release binary installer intended to
  back the hosted `get.aipowergrid.io/validator` path. It installs the binary
  under `$HOME/.local/bin` by default and creates `$HOME/.aipg-validator` as
  the private config directory unless overridden.
- **`scripts/install-systemd.sh`** — Linux systemd service installer for source
  or released-binary validator nodes. Dry-run safe; generated unit must keep
  secrets in `.env`, not in the unit file.
- **`scripts/smoke-release.sh`** — full local release smoke: unit tests, CLI,
  dashboard, Docker, release binary, and binary installer using throwaway
  offline config. Use `SKIP_DOCKER=1` or `SKIP_BINARY=1` only when the local
  machine genuinely cannot run that lane.
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
- **Early-stage / v0:** current Grid core work has
  `GET /v1/validator/capabilities`, `GET /v1/validator/assignments`,
  `POST /v1/validator/probe/{assignment_id}`, `POST /v1/validator/attest`,
  `GET /v1/validator/scorecards`, and `GET /v1/validator/workers`. The node
  prefers Grid-issued assignments; missing/empty assignment endpoints fall back
  to **v0 model-routed probing**. Assignment-bound evidence must include the
  Grid assignment id, nonce, and probe evidence hash, but still must be treated
  as observation/scoring input, not as slash or reward authority.
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
- New grid-side endpoint dependencies must stay optional with a documented
  fallback (see Local Contracts).

## Verification

- `./.venv/bin/python -m compileall validator`
- `./.venv/bin/python -m unittest discover -s tests`
- `./.venv/bin/aipg-validator --help`
- `./.venv/bin/python -m validator --help`
- `docker build -t aipowergrid/validator:local .`
- `docker run --rm --mount type=bind,source="$PWD/.env",target=/app/.env,readonly aipowergrid/validator:local check --no-probe`
- `bash -n scripts/install-binary.sh scripts/install-systemd.sh`
- `./scripts/smoke-release.sh`
- `./scripts/install-systemd.sh --dry-run --exec ./.venv/bin/aipg-validator`
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
