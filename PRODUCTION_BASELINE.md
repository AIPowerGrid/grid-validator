# Validator Production Baseline

This is a dated rollout snapshot, not a live status page. Query
`GET https://api.aipowergrid.io/v1/status/network` and
`GET https://api.aipowergrid.io/v1/validator/capabilities` for current public
state.

## 2026-08-27 09:02 UTC

Production Core advanced without a schema change to immutable runtime commit
`df34ffd46e395798647f57a0ecdd026aa2d0152e` with Alembic `0029`. The exact
candidate used its reviewed hash-locked environment. Backup
`grid-postgres-20260827T085937Z.dump` restored into a guarded scratch database,
passed the candidate schema checks, and required no new upgrade operations.

This cutover added the privacy-safe maintainer cohort runbook and made the
existing digest-bound operator review dry run report current 72-hour progress
and blockers. Applying an incomplete verification still fails closed. It did
not add a validator scheduler, reward, routing effect, strike, stake, slashing,
media-validation gate, or paid-audit scheduler.

All seven workers reconnected. Public status reported three fresh,
participating `v0.1.0-preview.8` validators, zero independently verified
operators, and validator economic effect `none`. Charging remained
allowlist/global-off, payout and PostgreSQL-backup timers remained enabled and
active, public route smokes passed, and the post-cutover API journal contained
no warning-or-higher entries.

## 2026-08-27 08:37 UTC

Production Core advanced to immutable runtime commit
`d8a48f2af7109c199582b9f3305940ac4ae5dc0f` with Alembic `0029`. The migration
was applied before the runtime cutover because every ordinary worker terminal
now checks the compensated-audit hold table. A checksummed production backup
was restored into a guarded scratch database, migrated from `0028` to `0029`,
and passed `alembic check` before the production schema changed.

The new compensated-audit accounting and terminal path are dark. Production
contained zero `grid_validator_audit_jobs` rows and zero
`grid_validator_audit_budget_counters` rows before and after startup. No audit
scheduler, operator configuration, private corpus, challenge selection, or
quality scoring integration is deployed. Existing sealed assignment probes
remain unpaid, use the existing zero-den terminal acknowledgment, and have no
economic authority.

Post-cutover public health reported seven connected workers and the exact Core
runtime commit. Public validator status reported three heartbeat-fresh,
participating `v0.1.0-preview.8` validators, zero independently verified
operators, and validator economic effect `none`. Image and video validation,
validator rewards, staking, routing influence, strikes, and slashing remained
disabled. Payout and PostgreSQL-backup timers remained active, and the
deployment-window journal contained no warning-or-higher entries.

## 2026-08-27 07:20 UTC

Production Core advanced to immutable commit
`43156ffd11bc3baa311a589998df8ddd6594583a` with Alembic `0028` after a
checksummed backup, guarded scratch restore, migration, and schema-drift check.
The private media worker-control review table existed with zero rows after the
migration, so deployment backfilled no trust. Image validation, video
validation, media bond sync, validator rewards, routing effects, strikes, and
slashing remained disabled.

Public status reported seven connected workers, ten online model entries,
three active/heartbeat-fresh/participating preview.8 validators, zero verified
independent operators, and validator economic effect `none`. The three nodes
remain one first-party control domain. The public capability contract continued
to label generated text probes as not quality-eligible and exposed image/video
validation as disabled. The payout and PostgreSQL-backup timers remained active
through the Core switch; this deployment did not change the validator payload.

## 2026-08-27 06:01 UTC

Production Core ran immutable commit
`fabb767df593c0f8240ea75d764297a962a64042` with Alembic `0027`. The public
validator release advanced to immutable unsigned prerelease
`v0.1.0-preview.8` from commit
`122f5565fddddb17de1a28719bbe6e792e1b75a7`. Its nine-asset payload passed the
release verifier and GitHub provenance check. A real macOS ARM64 install with
no version or asset override selected preview.8, verified SHA-256, installed,
and reported the exact release identity. Anonymous GHCR inspection returned an
OCI index for Linux AMD64 and ARM64; `latest` remained absent.

All three first-party Linux x64 validators rolled one at a time using archive
SHA-256 `8960993a2174162b192b11dfe0b82b086f6bf19c4d441ae6350a5907d33b03f6`.
Each passed `check --no-probe` before an atomic symlink switch and systemd
restart. All services were active, every private `.env` remained mode `0600`,
warning-or-higher journals were empty, and preview.6 remained installed on
every host for rollback. Preview.7 was intentionally never deployed after a
pre-rollout installer-runtime defect was found; preview.8 includes the fix and
a no-version packaged-installer regression test.

Public status reported three registered, heartbeat-fresh, participating
validators, all on preview.8; zero verified independent operators; 288
completed assignments; 259 authoritative votes; two accepted, one disputed,
and 93 finalized groups. Validator economic effect remained `none`; charging
remained non-global allowlist mode; staking, rewards, routing influence,
slashing, image validation, video validation, and coordinator federation
remained disabled. No fresh assignment was issued for this packaging-only
rollout, so the latest workload proof remains the earlier preview.5 healthy
16K-context group and correctly disputed token-limit group.

## 2026-08-27 04:35 UTC

All three first-party validators rolled one at a time to the exact published
Linux x64 `v0.1.0-preview.5` payload from commit
`07190da899e3fe9eaa99b0f15efb15dc01d69e7b`. Each downloaded archive matched
SHA-256 `d74e66c69f3b2ebef5b1ca6b4bb1b69cc2f1c1400cfc36f4ae095afaed0be0b7`,
reported the expected immutable version, and passed `check --no-probe` before
an atomic `current` symlink switch and systemd restart. Every private `.env`
remained mode `0600`; all three services were active with no warning-or-higher
journal entries after rollout. The prior release remained present for rollback.

Public status then reported three registered, heartbeat-fresh, participating
validators, all on `v0.1.0-preview.5`; zero independently verified operators;
288 completed assignments; 256 authoritative votes; and quorum state of zero
pending, two accepted, zero disputed, and 94 finalized groups. Validator
economic effect remained `none`, staking remained disabled, and charging
remained a non-global allowlist canary.

No new assignment or authoritative vote appeared during the 90-second
post-rollout observation window. Core finalized two existing groups, but that is
not a fresh workload proof. This snapshot therefore proves the public artifact,
upgrade, registration, heartbeat, service recovery, and rollback path. The most
recent fresh 3-of-5 workload proof remains the earlier `preview.3` echo group.

## 2026-08-27 00:09 UTC

Production Core ran immutable commit
`e18b38f95f08e168dbef458d934cd2360c6a2d50` with Alembic `0026`. A fresh
checksummed PostgreSQL backup restored into a guarded scratch database, upgraded
to the candidate head, passed `alembic check`, and was removed before cutover.
All three first-party validators then moved to the published, provenance-verified
Linux x64 `v0.1.0-preview.2` payload from commit
`1472677d01ceb67770bf59bd3a2cd48239e17aac`.

Core enabled sealed assignment polling only after all three compatible nodes
passed registration and no-probe checks. A supervised production poll returned
one opaque assignment id, public lifecycle/capability metadata, and a
64-character hexadecimal SHA-256 seal. It contained no target worker, worker
name, model, Grid nonce, canary kind, probe group, or challenge. After worker
execution, all three nodes
verified the terminal disclosure against their stored seal and submitted three
verified authoritative signatures. The tool-chain group reached `accepted /
healthy` 3-of-5 quorum.

The three probe job ids joined to zero `grid_ledger`, `grid_den_events`,
`grid_reservations`, and `grid_credit_ledger` rows. Core continued to report
`economic_effect: none`; rewards, stake, strikes, routing influence, slashing,
image assignments, and video assignments remained disabled. Public health
reported three active/fresh/participating validators and zero independently
verified operators. Sealing prevents advance assignment disclosure to a
validator; it does not make a public prompt grammar indistinguishable to the
worker during execution.

## 2026-08-26 21:17 UTC

Core reported immutable build
`49a6eb00707eec7e1b9bd9e3ab98039253c8518d`, Alembic `0026`, and an operational
API/Redis pair. The restored production backup upgraded through `0026` with no
schema drift before cutover. All three first-party validators were then moved,
one at a time with rollback guards, to the verified `v0.1.0-preview` payload
from commit `3a505d624b928c1b1fea4f23dffb972a50ae9905`.

| Validator signal | Value |
|---|---:|
| Registered active | 3 |
| Fresh heartbeat | 3 |
| Participating (24h) | 3 |
| Independently verified operators | 0 |
| Pending groups | 1 |
| Accepted groups | 3 |
| Disputed groups | 0 |
| Finalized groups | 92 |
| Completed assignments | 288 |
| Authoritative votes | 259 |
| Worker coverage | 4 |
| Model coverage | 3 |
| Reported software version | `0.1.0` (3 validators) |

The exact Linux x64 artifact ran on Ubuntu 22.04/glibc 2.35 and passed
`check --no-probe`, signed suspension, immediate re-registration, and normal
service startup. Core continued to report `economic_effect: none`, validator
rewards and staking disabled, media assignments disabled, and operator
independence unproven. The network reported 7 workers and 10 models; every model
remained below the three-worker redundancy target.

## 2026-08-26 18:07 UTC

Core reported build `0d850e7341c365787bf2b0dd7011342ef33f09cf` and an
operational API/Redis pair.

| Validator signal | Value |
|---|---:|
| Registered active | 3 |
| Fresh heartbeat | 3 |
| Participating (24h) | 3 |
| Independently verified operators | 0 |
| Pending groups | 1 |
| Accepted groups | 3 |
| Disputed groups | 0 |
| Finalized groups | 92 |
| Completed assignments | 286 |
| Authoritative votes | 263 |
| Worker coverage | 4 |
| Model coverage | 3 |
| Reported software version | `0.1.0` (3 validators) |

The 23-count difference between completed assignments and authoritative votes
is an operational delivery signal, not proof of fraud. Core completed-result
replay and the node assignment journal are pending review in Core PRs #26/#27
and validator PR #10; none of that recovery code was deployed in this snapshot.

## Authority Flags

- Mode: `shared_quorum_preview`
- Validator economic effect: `none`
- Validator rewards: disabled
- Validator staking requirement: disabled
- Image fidelity assignments: disabled
- Video validation assignments: disabled
- Epoch roots: disabled
- Operator independence proven: false
- Quorum policy: 3 matching votes from 5 distinct registered validators
- Charging: allowlist mode, global charging disabled

Registration and distinct wallets do not establish independent control. These
three nodes remain first-party preview infrastructure until operators are
externally qualified under `PREVIEW_COHORT.md`.

## Network Context

Production reported 7 online workers and 10 online models. Every model was below
the target of three serving workers, so limited model redundancy remained an
active public advisory. Validator coverage was narrower than serving capacity
(4 workers and 3 models), which is why fair multi-model assignment rotation is
an explicit protocol gate rather than a cosmetic metric.
