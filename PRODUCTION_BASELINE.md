# Validator Production Baseline

This is a dated rollout snapshot, not a live status page. Query
`GET https://api.aipowergrid.io/v1/status/network` and
`GET https://api.aipowergrid.io/v1/validator/capabilities` for current public
state.

## 2026-08-27 20:49 UTC - Cohort And Pairing Qualification Status

Read-only public health and production queries still report Core
`407f29841988fd253afe867a1f5a07e23349219e`. The expiring pairing-pilot change
in Core `f51875ce8fe550640008f1824625e2f5a071f88b` is merged, but the live
service has not switched to it. Pairing, media, rewards and staking remain
disabled; generated probes remain ineligible for quality authority.

Five active registrations now have fresh heartbeats: four on preview.9 and
one on preview.13. Three of the preview.9 nodes are the known first-party
pilots. The previously reported external registration has thirty verified
signed reports. The new preview.13 registration has no verified reports at
this snapshot, and its operator identity is not confirmed. Do not label it
as Donli based on its arrival time or version. All five registrations remain
unreviewed, with no qualification start or sampled qualification heartbeats;
verified independent operator count remains zero.

Validator PR [#63](https://github.com/AIPowerGrid/grid-validator/pull/63)
adds the manual [native pairing harness](NATIVE_PAIRING_CANARY.md). Its local
suite passed 307 tests with six explicitly skipped opt-in cross-repo fixtures.
This is test tooling, not a completed native live pairing run or a published
client. Public immutable downloads remain preview.13. The recruitment issue
and cohort guide point new users to explicit automatic enrollment and the
local app, without manual private-key entry.

The next operator evidence needed is a confirmed public validator ID, actual
accepted reports, a practical control-separation review and the 72-hour
qualification window. No independent review or association was created by this
read-only check, and no release, service configuration or production version
was changed.

## 2026-08-27 19:54 UTC - Published Windows Binary Live Proof

The protected manual
[Windows canary run 33110290699](https://github.com/AIPowerGrid/grid-validator/actions/runs/33110290699)
passed at 19:52:59 UTC using harness commit
`4502f0449c1848839cb7019831894faadd7e99a4`. It executed the immutable published
preview.13 Windows x64 binary, not a locally rebuilt candidate, against Core
`407f29841988fd253afe867a1f5a07e23349219e`. Both preview.12 and preview.13
archives and manifests passed exact-tag/source/workflow GitHub provenance and
checksum verification before execution. The preview.13 Windows archive SHA-256
is `56f59f39153f2c84de00a1dfc4aaccefcd7fa0c83616ed69492a1f10f36a0dad`.

The fresh first-party test demonstrated:

- Cancelled enrollment and merely opening the local app created no identity.
  Explicit enrollment generated a dedicated signer/key with an owner-only
  Windows DACL; repeated enrollment preserved the config.
- Registration, acknowledged heartbeat, real targeted text probes and two
  Core-accepted signed reports completed, with no pending/dead journal entries.
  Read-only production verification found two assignment-authoritative,
  signature-verified reports: one healthy and one failed worker result. A failed
  worker result is valid evidence, not failure of the validator test.
- Diagnostics excluded the config path, signing key, API key and local-app token.
  Stop/start, app restart, rejected credentials and switching the existing
  identity between verified preview.12 and preview.13 preserved the same config
  and validator ID.
- A real executable-specific outbound firewall block produced
  `grid_unavailable`. Removing it restored an acknowledged heartbeat and a
  completed polling round with no pending/dead entries. The runner's firewall
  profiles were restored to their original values.
- Signed suspension and revocation of the generated account's dedicated API key
  succeeded; the revoked key then received 401. Independent production queries
  confirmed the node suspended, no active keys, zero account credit entries and
  zero worker-ledger or reservation rows for its probe jobs.

The preceding ten-minute
[run 33109259349](https://github.com/AIPowerGrid/grid-validator/actions/runs/33109259349)
correctly failed with `no_accepted_evidence_in_window`: normal per-worker/model
cooldowns left it without assignments. Its generated node was also suspended
and its key revoked. The successful rerun used a thirty-minute maximum window
without changing assignment policy, cooldowns or worker targets.

This is hosted Windows Server runtime proof with HTTP-driven local-app controls,
not a human Windows 10/11 double-click/browser test or independent-operator
qualification. Neither temporary test node counts as Donli or another external
operator. Public status after cleanup again showed four fresh active preview.9
nodes: three first-party pilots and the previously observed external node,
whose independent-control review remains pending. Verified independence is zero.

No release, production deployment or feature activation occurred in these runs.
Pairing and compensated-audit tables remain empty; pairing, media issuance and
validator economics stay off. Public downloads remain preview.13; pairing and
decoder-fairness source remain unreleased. Human Windows onboarding, live pairing,
independent media references and the five-operator 72-hour cohort remain open.

## 2026-08-27 19:06 UTC - Pairing Dependencies Deployed Dark

Core `407f29841988fd253afe867a1f5a07e23349219e` is deployed with Alembic
`0030`. A 71,594,030-byte checksummed production backup passed restoration,
`0029` to `0030` upgrade and schema-drift checks in an isolated scratch database
before the production migration. A fresh Python 3.12 environment installed the
reviewed hash-locked wheels and passed dependency checks. Cutover completed at
19:00:27 UTC; environment contents and payout/backup timer configuration were
unchanged. No manual payout, validator economic activation or media activation
was performed.

Console `db3010132770385e454a0def9d96164808ce896f` is deployed as
`grid-frontend-mtg0r8qzx-ai-power-grids-projects.vercel.app` and aliased to the
public Console. Anonymous node-list access returns 401; the approval page
redirects to sign-in with its callback preserved and sends no-referrer/framing
protections. No authenticated human association was performed.

Public health reports the exact Core commit. Network status reports eight
connected workers, eleven model entries, and four fresh active validators on
preview.9. Three are first-party pilots; the external registration's control
review remains pending. Verified independent operator count is zero. Two
suspended canaries also contributed within the reporting window; they are not
active independent operators. All models remain below three-worker redundancy.

`account_pairing` remains false and its API returns 503. Both pairing tables
and both compensated-audit tables contain zero rows. The suspended Linux test
identity can still read registration; active-only scorecard/health requests
correctly return 403. Charging remains allowlisted, media issuance remains off,
and validator economic effect is `none`.

Merged node source `5de518b0a4bd67b6bcb0a05957c343433ec6cc66` passed all four
native builds and clean installs in
[33105488747](https://github.com/AIPowerGrid/grid-validator/actions/runs/33105488747).
The downloaded build-only payload passed manifest/checksum verification. It
includes pairing and decoder-fairness fixes, but is **not** a release and has
no release-provenance attestation. Public downloads remain immutable preview.13;
the active fleet was not upgraded. Core and Console exact-commit CI also passed.

Rollback targets are Core `6015eca3a5177c066048c3b6dc515ba86b257ee7` and Console
`grid-frontend-edh2yzth5-ai-power-grids-projects.vercel.app`. Keep pairing off,
retain the additive tables and node configurations, and revert application
versions if necessary; no database downgrade or identity replacement is needed.

Remaining gates: clean Windows double-click through accepted evidence,
Windows/Linux live account pairing, a qualified immutable client release,
supervised association/removal, and five independently controlled operators'
72-hour qualification. Native CI and dark deployment do not satisfy those gates.

## 2026-08-27 18:29 UTC - Preview.13 Network Recovery Release

Immutable unsigned `v0.1.0-preview.13` was published at 18:24:58 UTC from
reviewed master `5fa00bff24ce7749fa3316b68cecdb975155339d` (PR #57).
It corrects the HTTPX network-error label found in the preview.12 live test;
it does not change authentication, scoring, retry policy or economic authority.
Windows x64, macOS ARM64 and both Linux architectures passed native build,
packaged-app and clean-install checks in release run `33102892145`.

The complete downloaded payload passed manifest/checksum verification, and
all four archives, both installers, the SBOM and release manifest passed
GitHub provenance verification. The Linux ARM64 archive SHA-256 is
`df39ed403e25b5293f7340ed56492c6696e861048ce42def3adc168c3612896b`.
The existing first-party Linux canary upgraded with its private config intact.
An actual disconnected network produced `grid_unavailable`; reconnecting
restored an acknowledged heartbeat and a completed polling round with zero
accepted, pending or dead reports. This was a recovery test, not new evidence
generation: the earlier three verified reports were not duplicated. The node
then self-suspended and its temporary container was stopped and removed.

Container run `33102892171` published the versioned image with provenance:
`sha256:3b2d0fb0814e7e8a4ce9fa84a53a2830ab71c630ff00f1748c6aaf643bdc24ea`.
Anonymous manifest access passed for Linux x64 and ARM64; an anonymous ARM64
pull passed, and that exact image reported preview.13 and passed its offline
image/video decoder self-test with networking disabled. No `latest` tag changed.

No production Core deployment or validator-fleet upgrade was performed. Account
pairing, media issuance, independent-control verification and all validator
economic authority remain unchanged. Windows live onboarding through accepted
evidence and the five-independent-operator 72-hour cohort are still open.
For rollback, stop the local process, reinstall verified preview.12, and reuse
the existing private config/journal; do not enroll another identity. Preview.12
still recovers from outages but may display the older generic error label.

## 2026-08-27 18:11 UTC - Clean Linux Binary Live Proof

The published preview.12 Linux ARM64 archive and installer passed GitHub
provenance verification. The installer verified archive SHA-256
`4b2f084673d8d6f3e1cd8fd0f94db34540259168f6f03e70cdd9be34e0d377d8`,
bound by the release manifest to source
`7a084a674da3c8b09178faacdacd3257b829a023`. The binary ran without a source
checkout or Python installation in a fresh Ubuntu 22.04/glibc 2.35 ARM64
container on Docker Desktop's Linux VM. This is a real Linux runtime, not a
standalone Windows or Linux desktop qualification.

The bounded first-party test demonstrated:

- Cancelling enrollment created no identity. Explicit automatic enrollment
  created its own signer and a key with exactly the four validator scopes.
  The config was owner-only `0600`; repeating enrollment did not alter it.
- Signed registration, heartbeat, three real Grid-issued text assignments,
  local scoring and three Core-accepted signed reports completed. Read-only
  production queries confirmed all three signatures were verified and their
  authority was assignment-bound. One reported healthy and two reported failed
  worker results; accepted evidence does not mean all workers passed.
- The local journal had zero pending/dead work after delivery. Queries joining
  those probe job IDs found zero worker-ledger rows and zero reservations; the
  node account had zero credit-ledger writes.
- Invalid credentials failed without changing config. A full container restart
  preserved the same config and validator ID.
- Disconnecting the container network caused a retry event. Reconnecting it
  restored acknowledged heartbeats and a completed empty polling round, without
  changing identity or duplicating the three reports.
- The same existing identity registered using verified preview.11 and again
  after installation of verified preview.12. This proves the upgrade path for
  that config; the initial enrollment in this test was on preview.12.
- Signed suspension succeeded after testing. The temporary container was
  stopped; protected credentials were retained outside source control for
  deliberate recovery, not deleted as a substitute for server-side revocation.

Two practical issues were found. Docker's `noexec` `/tmp` prevented bundled
libraries from mapping; an owner-only executable `TMPDIR` fixed startup without
weakening `/tmp` (see [OPERATORS.md](OPERATORS.md#hardened-linux-temporary-directories)).
Preview.12 labelled the real HTTPX transport failure as `runtime_error` because
its classifier discarded HTTPX's type in favor of the underlying httpcore
cause. Recovery itself worked. A source fix and a real loopback connection
regression test now preserve `grid_unavailable`; that fix is not in the immutable
preview.12 artifact and still needs a subsequent qualified release.

No Core deployment, migration, validator economic authority, media issuance,
independence review or account pairing was enabled. This pilot is first-party
and does not count toward five independently controlled operators. Windows
double-click/live enrollment through accepted evidence, human account pairing,
media calibration and the 72-hour independent cohort remain separate gates.

## 2026-08-27 15:42 UTC - Local Operator App Release

Immutable unsigned preview `v0.1.0-preview.12` was published at 15:34 UTC from
reviewed master `7a084a674da3c8b09178faacdacd3257b829a023` (PR #52). Binary
workflow `33088049410` passed all four native builds, packaged operator-app
checks, payload verification, and clean installs before owner approval and
immutable publication. Container workflow `33088049466` passed its qualification
and protected publish jobs. The source suite passed 245 tests.

All nine downloaded assets passed exact-tag/source, manifest, and SHA-256
verification. The downloaded manifest, macOS archive, Windows archive, and OCI
index passed GitHub provenance checks bound to the repository, workflow, tag,
source digest, and hosted runners. The macOS binary passed offline decoder and
operator-app asset/authentication/child-restart/diagnostics/shutdown smoke tests.
The pulled container passed its offline decoder self-test. Anonymous release
and Linux AMD64/ARM64 manifest reads succeeded. The container index is
`sha256:1542b8c274586231048228711bd08a2360a80c269a5ed89b2a1ada89bbb6f9d8`.

The downloaded app ran the existing maintainer canary for five minutes against
production Core. Its stable validator ID and private config were preserved,
and Core acknowledged repeated preview.12 heartbeats. No assignment was issued
and no new evidence was accepted, so this is upgrade/heartbeat/lifecycle proof,
not a completed probe or clean Windows/Linux end-to-end qualification. Local
stop and app exit completed cleanly; the registration was then signed-suspended.

The three first-party pilots remain on preview.9. No Core deployment, schema
change, fleet rollout, media assignment activation, or economics activation was
part of this release. Existing-account pairing and five independent operators'
72-hour qualification remain open. To roll back, stop the app and use the
previous verified binary with the same private config and recovery journal;
never replace the identity to work around an upgrade failure.

## 2026-08-27 14:40 UTC - Enrollment Release

Immutable unsigned preview `v0.1.0-preview.11` was published from reviewed
master commit `55996c67bf9ee1e6ab13057a53a8249e472f9cae` (PR #50). The owner
approved the protected release jobs after four native builds and four clean
installs passed. All nine downloaded assets passed the exact-tag/source
manifest and checksum verifier. GitHub provenance verification bound the
downloaded manifest and macOS archive to that source, tag, hosted runner,
repository, and binary-release workflow. Anonymous release and GHCR reads
succeeded. Preview.10 remains an unpublished binary draft after GitHub upload
failures; preview.11 is the usable enrollment release, not a tag replacement.

The public Linux AMD64/ARM64 container index is
`sha256:950451a72fb101973bb5ad7c4aa8cb5655cd8c80313d069201b9b67fc94114b8`.
The pulled container and downloaded macOS binary passed the offline bounded
image/video decoder self-test. The downloaded binary reported preview.11 and
re-registered the existing maintainer canary without changing its validator
ID. A subsequent probe check correctly returned no assignment and nonzero
exit status: no new evidence was submitted. The canary was signed-suspended
again. This is upgrade/registration proof, not clean Windows/Linux live
enrollment through accepted evidence; that qualification remains open.

The three deployed first-party pilots remain on preview.9. No Core deployment,
schema change, fleet rollout, media assignment activation, or economic effect
was part of this release. Preserve the existing private configuration when
upgrading; the previous binary is the rollback target, not a new node identity.

## 2026-08-27 14:10 UTC - Dedicated Enrollment Canary

An unreleased source candidate completed the existing production wallet
challenge/verify and validator-purpose key flow with a newly generated,
dedicated local signer. No browser login, pasted private key, identity merge,
funding, or Core deployment was needed. Signed registration succeeded, followed
by one real stop-sequence assignment. A read-only production query confirmed
one stored attestation with `authority=authoritative`,
`signature_status=verified`, and `verdict=failed`: the worker failed the probe,
not the enrollment or evidence-delivery path. The canary was explicitly
suspended afterward; it is maintainer-controlled and is not an independent
qualification candidate. Credentials remain private and outside source control.

This proves source enrollment through accepted signed evidence on one host,
not clean Windows/Linux packaged enrollment, independent control, or a release.
Core still reports no validator economic effect. Public status before this
canary reported Core `6015eca3a5177c066048c3b6dc515ba86b257ee7`, four fresh and
participating preview.9 nodes, and zero independently verified operators.

## 2026-08-27 13:17 UTC

The public validator release advanced to immutable unsigned prerelease
`v0.1.0-preview.9` from commit
`9d7b68fd7cf549c7e245cdb07877486c9e59c962`. Its nine release assets matched
`SHA256SUMS`; anonymous release downloads and the Linux AMD64/ARM64 GHCR index
were reachable. The exact published container reported preview.9 and passed
the offline bounded image and video decoder self-test.

All three participating first-party Linux x64 validators rolled one at a time
from preview.8 using archive SHA-256
`4375a07e8ea1db722b8c09497237bc56271cac840ee9c7362018f951736cafb8`.
Each staged binary reported preview.9, passed the offline media self-test and
authenticated `check --no-probe`, then moved through an atomic `current`
symlink switch and clean systemd restart. All services remained active, every
private `.env` remained owner-only mode `0600`, no media origin allowlist was
configured, warning-or-higher deployment journals were empty, and preview.8
remained installed for rollback.

Post-rollout public status reported four active and heartbeat-fresh
registrations: the three participating first-party pilots on preview.9 and one
separate preview.8 registration. It reported zero independently verified
operators and validator economic effect `none`. Image and video assignments,
blind quality scoring, worker-terminal indistinguishability, validator rewards,
staking, routing influence, strikes, and slashing remained disabled. The
rollout qualifies the media-capable artifact and service recovery path; it does
not enable media evidence or prove independent operator control.

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
