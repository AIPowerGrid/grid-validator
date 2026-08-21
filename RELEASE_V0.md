# Validator V0 Release Runbook

This runbook coordinates the evidence-only validator launch across:

- Grid core (`grid-core` in this checkout) - validator evidence API and database migration
- `grid-frontend` - console scorecard view
- `grid-validator` - operator package, Docker image, and release binary

V0 is not an economic validator launch. It stores and displays evidence only.
It must not affect routing, worker strikes, rewards, slashing, credits, payouts,
or ledger rows.

## Release Principles

- Deploy the Grid API before the console and validator release.
- Apply Alembic migrations explicitly. Do not rely on `create_all(checkfirst=True)`
  as proof that an existing production database is migrated.
- Use targeted probing only through a Grid-issued assignment. The candidate
  `/v1/validator/probe/{assignment_id}` reaches exactly one assigned worker and
  is covered by Core and node tests; do not call it production-live before the
  deployment smoke proves that same behavior.
- Treat `GET /v1/validator/workers` as discovery, never as authority to invent
  an assignment locally.
- Require each validator signing wallet to be linked to its Grid account and
  registered before assignments are issued. This proves account-bound evidence
  identity, not stake or future economic authorization.
- Do not publish raw prompts, outputs, nonces, signatures, account IDs, or
  validator wallet addresses through public or console scorecard views.

## Phase 0 - Local Preflight

Run these before merging the V0 stack.

In the Grid core repo:

```bash
./.venv-test/bin/python -m pytest grid_api/routers/tests/test_validator_assignments.py -q
git diff --check
```

In `grid-frontend`:

```bash
pnpm lint:strict
pnpm format:check
pnpm build
```

In `grid-validator`:

```bash
./.venv/bin/python -m compileall validator
./.venv/bin/python -m unittest discover -s tests
bash -n install.sh scripts/classify-release-tag.sh scripts/install-binary.sh \
  scripts/install-systemd.sh scripts/smoke-release.sh scripts/verify-release-assets.sh
./scripts/install-systemd.sh --dry-run --exec ./.venv/bin/aipg-validator
./scripts/smoke-release.sh
docker build -t aipowergrid/validator:local .
docker run --rm aipowergrid/validator:local --help
docker run --rm \
  --mount type=bind,source="$PWD/.env",target=/app/.env,readonly \
  aipowergrid/validator:local check --no-probe
./.venv/bin/python -m pip install -e '.[release]'
./.venv/bin/pyinstaller --onefile --name aipg-validator-local \
  --specpath build/pyinstaller-local validator/__main__.py
./dist/aipg-validator-local --help
git diff --check
```

Documentation gate:

- `README.md`, `QUICKSTART.md`, and `OPERATORS.md` must all say V0 is
  evidence-only.
- They must describe `check --no-probe` as the no-canary install/API smoke.
- They must not imply that public binary releases, published Docker images,
  validator rewards, staking, media validation, routing impact, or slashing are
  live before the matching Core/contracts/release artifacts exist. Targeted
  text probes become live only after the Core rollout gate, and remain
  assignment-bound, non-economic evidence.

The V0 release binary intentionally includes the default dependency set:
assignment-bound text probing plus signed registration and attestations.
Optional `media` and `stake`
extras stay source/dev paths until those lanes are live.
At least one release-binary smoke should run from a separate temp working
directory with only a local `.env`, so the check proves the binary does not
depend on the source checkout.
The `scripts/smoke-release.sh` helper performs that binary smoke plus source,
Docker, dashboard, and installer checks against throwaway offline config.
CI/release smoke tests should assert that offline Grid checks fail cleanly with
`Validator registration failed`, not a Python traceback or import error.

## Phase 1 - Deploy Grid Core

Deploy the core before publishing validator nodes or the console scorecard
surface.

Required code:

- Alembic migrations through `0024_validator_group_witnesses`; `0022` adds
  shared quorum and `0023`-`0024` keep the current Core candidate schema-complete
  while media assignments remain disabled
- `grid_api/v2/schema.py` validator registration, assignment, and attestation tables
- `grid_api/services/validators.py`
- `grid_api/routers/validator.py`
- `grid_api/main.py` router include

Production migration gate:

```bash
alembic upgrade head
alembic current
```

Expected API checks:

```bash
curl -fsS https://api.aipowergrid.io/v1/validator/capabilities
```

Must show:

- `mode: "shared_quorum_preview"`
- `economic_effect: "none"`
- `features.assignments: true`
- `features.targeted_probe: true`
- `targeted_probe_enabled: true`
- `features.quorum: true`
- `quorum_policy.threshold: 3`
- `quorum_policy.target_validators: 5`
- `quorum_policy.operator_independence_proven: false`
- `features.validator_rewards: false`
- `features.staking_required: false`

With an authenticated Console session, create a validator-purpose API key. It
must contain exactly `validator.assignments`, `validator.probe`,
`validator.attest`, and `validator.read`. Then register the linked wallet before
reading assignments.

```bash
curl -fsS \
  -H "apikey: $GRID_API_KEY" \
  "https://api.aipowergrid.io/v1/validator/scorecards?limit=5&since_hours=24"

curl -fsS \
  -H "apikey: $GRID_API_KEY" \
  "https://api.aipowergrid.io/v1/validator/workers"
```

Scorecards may be empty. Worker inventory may be targetable only through the
assignment endpoint; validators must not turn arbitrary worker IDs into
authoritative probes.

Rollback:

- The validator endpoints are evidence-only, so disabling the route or rolling
  back the service should not affect money movement.
- Do not downgrade the database until you confirm no code still reads
  `grid_validator_attestations`.

## Phase 2 - Deploy `grid-frontend`

Deploy the console after the core endpoints are reachable.

Required surface:

- `/api/validator/scorecards` BFF route
- `/dashboard/validators` page
- sidebar item labelled `Validator Evidence`

Verification:

```bash
pnpm lint:strict
pnpm format:check
pnpm build
```

Browser checks:

- signed-out users are redirected or shown the normal account requirement
- signed-in users with a v2 Grid session key can load scorecards
- empty evidence renders as an empty state, not an error
- the page says evidence is informational only
- no raw payloads, nonces, signatures, account IDs, or validator identities are
  rendered

Rollback:

- Removing the console route is safe. It is read-only and does not change core
  behavior.

## Phase 3 - Publish `grid-validator`

Publish the operator package after core and console are deployed.

Source/Docker preview is usable immediately:

```bash
git clone https://github.com/AIPowerGrid/grid-validator
cd grid-validator
./install.sh
./.venv/bin/aipg-validator check --no-probe
./.venv/bin/aipg-validator dashboard
```

Public release path:

1. Push the repo with CI green. Confirm GitHub immutable releases are enabled
   for `AIPowerGrid/grid-validator`; never disable the setting to repair a
   published release. The public release remains blocked until
   [issue #1](https://github.com/AIPowerGrid/grid-validator/issues/1) closes:
   the macOS binary must carry a verified Developer ID identity and notarization,
   and the Windows binary must carry a verified Authenticode identity. The
   workflow records those facts in `validator-release.json` and fails closed
   before publication while either is absent.
2. Create a release tag, or run the binary and Docker workflows manually with
   explicit publish tags:
   - binary workflow: set `release_tag` to the release name, for example
     `v0.1.0-preview`
   - Docker workflow: set `image_tag` to the matching image tag, and enable
     `publish_image` only after a build-only qualification succeeds. Enable
     `publish_latest` only for a stable release that should become the default
     public image. Preview/alpha/beta/RC tags are rejected if `publish_latest`
     is enabled, and `publish_latest` is rejected unless `publish_image` is on.
3. Confirm release assets exist:
   - `aipg-validator-linux-x64.zip`
   - `aipg-validator-linux-arm64.zip`
   - `aipg-validator-macos-arm64.zip`
   - `aipg-validator-windows-x64.zip`
   - `validator-release.json`
   - `SHA256SUMS`
   - `aipg-validator-release.spdx.json`
   - `install-validator.sh`
   Then run `./scripts/verify-release-assets.sh <download-directory>` against a
   clean download of the complete release.
4. Confirm GitHub build provenance attestations exist and verify each binary
   archive from a clean download directory:

```bash
gh attestation verify aipg-validator-linux-x64.zip \
  --repo AIPowerGrid/grid-validator
```

   Repeat for the other platform archives, installer, and release SBOM. The
   installer verifies `SHA256SUMS`; the release manifest binds the exact tag,
   version, source commit, asset sizes, and asset hashes; and the attestation
   check proves the artifacts were produced by this repository's GitHub Actions
   workflow.
5. Confirm the container image exists at `ghcr.io/aipowergrid/validator` with
   registry SBOM and provenance metadata.
6. Test the checksum-verifying installer against the release asset:

```bash
AIPG_VALIDATOR_VERSION=<tag> bash install-validator.sh
cd ~/.aipg-validator
aipg-validator --help
aipg-validator init
aipg-validator check --no-probe
```

After publication, the release tag and assets are immutable. If any asset,
manifest, signature, or note is wrong, publish a new version and leave the
original release available for audit.

Operator config:

- keep `VALIDATOR_REQUIRE_STAKE=false` for V0
- leave `VALIDATOR_STAKING_ADDR` empty
- signing is mandatory; `VALIDATOR_WALLET` is derived from
  `VALIDATOR_PRIVATE_KEY` and must already be linked to the key's Grid account
- `AIPG_TOKEN_ADDR` and `VALIDATOR_STAKING_ADDR`, when set, must also be valid
  20-byte `0x` EVM addresses and fail as clean startup errors before Web3/RPC

Rollback:

- Stop the validator service or container.
- Evidence rows already submitted can remain in core; they are non-economic.

## Phase 4 - Canary Operation

Start with a small internal validator set.

Recommended first checks:

```bash
aipg-validator check --no-probe
aipg-validator check
aipg-validator dashboard
```

Watch for:

- capability endpoint available
- scorecards available or clearly empty
- active registration and assignment-bound text probing
- no arbitrary worker targeting outside a Grid-issued assignment
- no repeated 401/403 due to key type
- no route, payout, strike, or slash side effects

Only after internal canaries are quiet should the release be announced to
external operators.

## Still Not V0

These require a separate design, tests, and release gate:

- validator role/stake authorization
- self-validation exclusion
- adversarially proven multi-validator quorum and operator dispute tooling
- routing impact
- validator rewards
- worker slashing from validator evidence
- on-chain epoch roots
- deterministic media workflow certificates used by product policy
