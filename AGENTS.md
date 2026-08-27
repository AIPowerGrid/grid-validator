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
`failed`), and submits signed attestations. Shared-quorum text validation is
production-live on Core commit `f51875ce` as checked on 2026-08-27, with migrations through `0030`.
Three first-party pilot nodes run the verified `v0.1.0-preview.9` payload from
validator commit `9d7b68f`; checksum-gated staging, offline media self-tests,
no-probe registration, rolling symlink rollout, immutable release reporting,
and clean service recovery were proven against production on 2026-08-27. After the one-hour preview
cooldown elapsed, the `preview.5` fleet completed a healthy 3-of-5 16K-context
group and a correctly disputed token-limit group. Both groups carried three
distinct nonces, evidence commitments, and verified signatures, with no credit,
reservation, den, or worker-ledger side effects. This proves the protocol and
deployment path, not independent operator control. Media assignments remain
disabled. Core `0029` also contains a dark atomic accounting terminal for future
compensated audits, but no scheduler, private corpus, or scoring integration is
enabled and existing preview probes remain unpaid. The live
`GET /v1/validator/assignments`, `POST /v1/validator/probe/{assignment_id}`, and
preview scorecards and distinct-validator 3-of-5 probe groups make evidence attributable, but still non-economic: no reward,
routing, strike, or slashing logic may read it as authority. Future phases harden adversarial
independent-operator proof, deterministic media workflow certification, rewards, staking, and
objective-fraud slashing. Do not describe future economic authority as live until the
Grid endpoints and contracts exist. Python package: `validator/`. Entry: `validator.main`.

Core's required anti-gaming CI owns the executable hostile-worker baseline:
regex/template solving, exact replay, public-probe classification, and
probe-aware model switching all reproduce the current fingerprinting risk while
proving generated probes remain ineligible for quality authority. This repo
documents and consumes that boundary; do not duplicate the Core challenge
generator here or imply that passing public templates proves model quality.

## Ownership

- **`validator/`** — the whole node (config, stake gate, grid client, canary probing +
  scoring, attestation signing, probe loop, CLI, read-only dashboard, and opt-in
  local operator app). Owned in its own AGENTS.md. Browser controls ship in
  the native-tested preview.12 release. Published preview.13 passed hosted Windows
  live runtime qualification; human desktop onboarding remains separate.
- **`README.md`** — V0 scope, quick start, and current public distribution shape.
- **`QUICKSTART.md`** — one-page operator path that mirrors the worker quickstart:
  source preview, verified binary install, versioned public Docker, systemd,
  health checks, and V0
  safety boundaries.
  Current downloads target preview.13 with confirmed local dedicated-account
  enrollment, the Windows menu, and opt-in operator app; preserve deployed-fleet snapshots
  separately. Do not direct first-time operators to paste private keys or claim
  existing-account pairing is shipped.
  Preview.13 preserves the network-error category through HTTPX's exception
  chain; its published Linux binary passed controlled live outage/recovery.
- **`OPERATORS.md`** — plain-language run guide (install, systemd, troubleshooting, FAQ).
  It owns the signed suspend/resume and account-bound signing-wallet/API-key
  rotation runbooks; do not describe local file deletion as credential revocation.
  It also owns hardened-Linux temporary-directory guidance: one-file binary
  libraries need executable mapping, without weakening the host's `/tmp` policy.
- **`ACCOUNT_PAIRING.md`** - existing-account visibility association contract,
  explicit two-sided consent, failure recovery, and cross-repo rollout gates.
  Local app support is merged and native-build tested but unreleased;
  preview.13 does not include it. Core (`f51875ce` / `0030`) and Console
  PR #21 (`db301013`) are deployed dark. Live Windows/Linux pairing qualification,
  a published client and supervised canary remain gates; the feature stays off.
  Core PR #60 adds an expiring account-scoped pilot for that qualification,
  deployed dark with an empty allowlist and no expiry configured. Keep private
  pilot membership out of diagnostics, docs and public capability responses.
- **`DESIGN.md`** — source of truth for validator phases, proof lanes, modality scoring,
  reference pool, future economics, Base anchoring, and Grid-side dependencies.
- **`ADVERSARIAL_VALIDATION.md`** — attacker model, evidence-dimension boundaries,
  probe-fingerprinting gaps, red-team acceptance tests, and economic gates.
- **`ROADMAP.md`** — dev-manager build order from V0 preview through targeted
  validation, text/image/video policy work, and Base-anchored economics.
  Its active ten-item milestone distinguishes published native runtime proof
  from human desktop use, staged restore proof from cutover, and registration
  from independently reviewed qualification. Keep those gates separate.
- **`RELEASE_V0.md`** — cross-repo evidence-only release runbook: core migration/API,
  console scorecards, validator packaging, canary operation, and rollback notes.
- **`PREVIEW_COHORT.md`** — public recruitment and qualification contract for
  5-10 independent preview operators, including safe reporting and the
  distinction between node count and independently controlled quorum weight.
  Its new-operator path is preview.13 automatic dedicated-node enrollment and
  the local app, not manual wallet/key preparation. Keep independent-control
  review and advanced credential rotation separate from first-run setup.
  Qualification is 72 hours with bounded heartbeat sampling and an expiring
  external review; the node cannot self-certify operator independence. The
  authenticated CLI/dashboard may show that operator's progress and review
  expiry, but must never expose the opaque control group or private review ref.
- **`PRODUCTION_BASELINE.md`** — dated public capability, assignment, quorum,
  independence, and network-capacity snapshots. It is historical evidence, not
  a substitute for the live public status endpoints.
  Do not infer an operator's identity from a new registration's time or version;
  registration, accepted evidence and independent qualification are separate facts.
  It distinguishes published Linux ARM64 and hosted Windows x64 live
  enrollment/assignment/recovery proof from uncompleted human Windows UI and
  independent-operator qualification.
- **`NATIVE_LIVE_CANARY.md`** - owner-approved Windows runtime qualification
  against the unpaid production preview. The manual workflow uses published
  binaries and a disposable identity, tests app controls/recovery, and requires
  suspension plus key revocation. Preview.13 passed run `33110290699` with two
  verified signed reports and confirmed retirement. It is not human double-click
  or independent operator proof. Only its bounded public report may become an artifact.
- **`NATIVE_PAIRING_CANARY.md`** - manual Windows/Linux candidate pairing
  qualification with separate Console approval and local code consent. This is
  maintainer test tooling, not onboarding for ordinary operators. It has offline
  safety coverage but no completed native live pairing run; it neither deploys
  Core nor activates the pilot. Public downloads remain preview.13.
- **`SECURITY.md`** — private vulnerability disclosure process and the
  validator-specific evidence, identity, and release-supply-chain scope.
- **`pyproject.toml`** — package metadata and `aipg-validator` console script.
  Default dependencies cover V0 text probing plus signing; heavier future-lane
  dependencies live under `media` and `stake` extras. Python 3.10 installs the
  small `tomli` compatibility dependency used by release identity validation;
  Python 3.11+ uses the standard-library parser. Do not reintroduce a
  parallel `requirements.txt`; it drifts from release builds.
- **`uv.lock`** — cross-platform dependency lock for release binaries. Release
  builds must use it with `uv sync --frozen`; update it deliberately with the
  pinned workflow uv version when package requirements change.
- **`Dockerfile` / `docker-compose.yml` / `.dockerignore`** — container packaging and
  local Compose run paths. The image uses a digest-pinned Python base and the
  same frozen `uv.lock` as release binaries; official artifacts bundle the
  optional media extra and must pass the offline bounded-decoder self-test. The
  final non-root stage does not carry the UV build tool.
- **`.github/workflows/`**, `.gitleaks.toml`, and `.gitleaksignore` — CI,
  checksum-verified complete reachable-history scanning,
  image-release, and binary-release workflows. Historical scan exceptions are
  exact reviewed fingerprints only. Global placeholder words, lockfiles, and
  generated-directory names are not secret-scan exemptions; CI proves an
  `example_private_key` label cannot suppress a committed synthetic secret.
  Ordinary CI installs from the frozen `uv.lock`, executes the complete Python
  unit/adversarial suite on every supported Python version, and audits the
  complete locked graph, including every optional dependency lane; it must not
  resolve the broad `pyproject.toml` ranges independently with pip. A job named
  `test` that only compiles or smoke-tests the CLI is not a test gate.
  Pull requests and `master` pushes assemble, verify, and clean-install the exact
  four-platform binary payload without publishing it. Each target executes local
  account-pairing contract and consent tests before packaged-app smoke checks.
  Linux x64 and ARM64
  binaries are built and clean-installed on Ubuntu 22.04 runners, establishing
  a glibc 2.35 baseline instead of inheriting `ubuntu-latest` silently.
  Protected `v*` tag pushes are the only
  binary and container publication path; manual binary and Docker dispatches
  are build-only. `latest` is allowed only for stable tags.
  Preview/alpha/beta/RC images must never replace `latest`. A build-only binary
  dispatch still assembles and verifies the full payload, but skips provenance
  attestation, tag creation, and publication. A
  manual Docker dispatch performs multi-architecture build-only validation with
  read-only credentials. GHCR write and attestation permissions exist only in
  the protected tag-publish job.
  GitHub immutable releases must remain enabled. After a release is published,
  its tag and assets are permanent; corrections publish a new version instead
  of replacing an operator-visible artifact. Binary publication must create a
  draft, upload and remotely enumerate the complete verified payload, and only
  then publish the draft; publishing a prerelease before its assets exist is a
  release-blocking failure.
  Binary publication must use an owner-created protected `v*` tag on a commit
  reachable from reviewed `master`, pass the protected `validator-release`
  environment, and reverify the downloaded
  payload against the workflow tag and source commit. Packaged shell and
  PowerShell installers must be stamped with that exact tag; a released
  installer may never retain a source placeholder or silently target an older
  preview. Repository settings must
  restrict that environment to the `master` branch and `v*` tags with an
  explicit reviewer, and restrict creation, update, and deletion of `v*` tags
  to the release owner.
  Third-party actions are commit-SHA pinned.
- **`scripts/install-binary.sh`** — GitHub Release binary installer intended to
  back the hosted `get.aipowergrid.io/validator` path. It installs the binary
  under `$HOME/.local/bin` by default and creates `$HOME/.aipg-validator` as
  the private config directory unless overridden.
  It verifies the selected archive against the release `SHA256SUMS`; signed
  GitHub provenance is verified separately with `gh attestation verify`.
- **`scripts/install-validator.ps1`** — native Windows x64 installer. It
  requires explicit acknowledgement of the unsigned preview and verifies the
  archive checksum before installation or execution. It prints the interactive
  menu invocation. Native clean-install CI must exercise identity creation,
  repeated preparation, and the protected Windows DACL, not just help/decoders.
- **`scripts/install-systemd.sh`** — Linux systemd service installer for source
  or released-binary validator nodes. Dry-run safe; generated unit must keep
  secrets in `.env`, not in the unit file.
- **`scripts/smoke-release.sh`** — full local release smoke: unit tests, CLI,
  dashboard, Docker, release binary, and binary installer using throwaway
  offline config. The Docker and frozen-binary checks must both prove the
  packaged token-limit scorer loads. Use `SKIP_DOCKER=1` or `SKIP_BINARY=1`
  only when the local machine genuinely cannot run that lane.
- **`scripts/smoke-operator-app.py`** — offline native binary proof that UI assets,
  session authentication, managed child errors/restarts, and safe diagnostics
  work after freezing. Runs in every native binary build; no live credentials.
- **`scripts/verify-release-assets.sh`** — publication gate for the exact four
  platform archives, checksum-covered shell and PowerShell installers, SPDX JSON SBOM, and
  `validator-release.json` plus `SHA256SUMS`. The manifest binds version, tag,
  source commit, exact asset names, sizes, hashes, and platform-signing state;
  the aggregate checksum covers the manifest. The verifier checks archive
  contents and rejects missing, extra, mismatched, non-regular, encrypted, or
  path-bearing archive entries before provenance is attested. Tagged previews
  may publish only when the manifest and release page explicitly disclose that
  macOS lacks Developer ID signing/notarization and Windows lacks Authenticode;
  checksums and GitHub provenance remain mandatory. Stable publication must
  fail unless both platform-signing identities are verified.
- **`scripts/classify-release-tag.sh`** — shared binary/Docker tag policy.
  Only stable `vX.Y.Z` tags may publish `latest`; bounded prerelease tags such
  as `v0.1.0-preview.9` remain explicitly versioned.
- **`scripts/stamp-release-tag.py`** — deterministic build identity stamping.
  Moving source and branch builds identify as `v<project-version>-dev`; only a
  release workflow may stamp its already validated tag, and packaged binary and
  container smoke tests must require that exact identity.
- **`install.sh` / `aipg-validator.service` / `.env.template`** — source-checkout
  install + run-as-service. Installation never generates a signing identity as
  a side effect. New operators explicitly run `aipg-validator enroll` to create
  a dedicated local signer and authenticate a separate node account using
  Core's existing SIWE and validator-purpose key endpoints. This is not
  existing-account pairing and never merges identities or changes payout wallets.
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
  arithmetic, strict JSON, calibrated 4K/16K/32K context retrieval, generated
  multistep logic, restricted-AST Python function synthesis against
  assignment-only hidden inputs, one exact randomized function call, a two-stage
  randomized tool chain, randomized stop-sequence compliance, and gross
  output-budget compliance. The code lane interprets a bounded arithmetic AST;
  it never executes worker-supplied code.
  The token-limit lane independently counts visible and reasoning output with
  `o200k_base` and a cross-tokenizer tolerance; it does not claim exact native
  tokenizer equivalence.
  They are usefulness samples, not proof of a model family or parameter count.
- The media witness fetch/verifier and independent image/video scorers are wired
  to assignment polling but remain Core-gated: exact
  operator-configured HTTPS origins, redirects and encoded responses disabled,
  bounded bytes/time/MIME, SHA-256 recomputation, structural checks, and
  reference comparison only after two references agree. Video decoding runs in
  a killable child process with time, frame, dimension, and Linux resource
  bounds. Local FFmpeg allocation/missing-codec failures are inconclusive;
  reference disagreement takes precedence even over malformed candidates.
  Consensus-affecting pHash, motion, and latency thresholds are fixed
  by the versioned policy; only local limits that yield inconclusive evidence
  are operator configurable. A node advertises each capability only when its media dependencies
  and HTTPS origin allowlist are ready; Core must still withhold assignments
  until every media rollout gate is complete.
- **Evidence delivery is durable:** persist each Grid assignment before probing,
  atomically replace it with the signed public envelope after local scoring,
  replay pending evidence before new work, and remove evidence only after Core
  accepts it. Core-completed replay responses must retain the original measured
  latency. Never persist the private key in validator state. Exhausted rows stay
  as dead letters until an operator explicitly retries them.
- **Lifecycle controls preserve identity:** self-suspension is signed by the
  current registered wallet; rotation is signed by a different replacement
  wallet already linked to the same canonical Grid account and preserves the
  validator ID. Wallet rotation never substitutes for revoking the previous
  validator API key.
- **Secrets:** `.env` may hold `VALIDATOR_PRIVATE_KEY` (signs attestations and later controls
  stake) — always chmod 600, never commit. The key never leaves the box; the grid receives only
  signed payloads. If the private key is configured, `VALIDATOR_WALLET` must be the derived
  wallet address.
- **Pay for verified-correct work, never presence.** Any future reward/scoring logic added here
  must track accepted useful attestations and consensus agreement, not attestation count.
- **Canaries must stay unpredictable.** Do not commit static challenge answer keys, golden
  pHashes, private prompts, or live scoring secrets into the public repo.
- Unpredictable values are not indistinguishable workloads. Public-template
  canaries may produce protocol or capability evidence, never quality evidence.
  Follow `ADVERSARIAL_VALIDATION.md` before adding routing or economic authority.
- On-chain reads (stake gate) fail fast and gate startup only when `VALIDATOR_REQUIRE_STAKE=true`;
  they are not on the probe hot path.

## Work Guidance

- New env vars: add to `validator/config.py` `Settings` (typed, with a
  default), not ad-hoc `getenv`.
- Keep heavy deps (web3, Pillow, imagehash, PyAV) lazily imported and in optional
  extras so the default source install stays small. Official binary/container
  builds intentionally install the `media` extra; runtime advertisement still
  requires the explicit media-origin gate. `eth-account` remains a default
  dependency because signed V0 attestations are part of the preview.
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
- `gitleaks git . --log-opts=HEAD --config .gitleaks.toml --redact` from a full
  clone. This covers the current committed tree and all reachable history
  without scanning ignored local environments or generated caches.
- `uv export --frozen --all-extras --no-dev --no-emit-project
  --format requirements-txt --output-file /tmp/validator-all-deps.txt` then
  `uvx --from pip-audit==2.9.0 pip-audit -r /tmp/validator-all-deps.txt
  --require-hashes --disable-pip`
- Release-binary smoke:
  `./.venv/bin/python -m pip install -e '.[release]'` then
  `./.venv/bin/pyinstaller --onefile --collect-data validator --name aipg-validator-local`
  `--specpath build/pyinstaller-local validator/__main__.py`
  then `./dist/aipg-validator-local --help` and
  `./.venv/bin/python scripts/smoke-operator-app.py ./dist/aipg-validator-local`; also run at least one
  `check --no-probe` smoke from a temp working directory with only a local
  `.env` to prove the binary does not depend on the source checkout.

## Child DOX Index

- [validator/AGENTS.md](validator/AGENTS.md) — the node: config, stake,
  probing, attestation, loop, CLI.
- [tests/AGENTS.md](tests/AGENTS.md) — validator protocol and operator-surface
  unit tests.
- [scripts/AGENTS.md](scripts/AGENTS.md) - release, installation, and packaged smoke contracts.
