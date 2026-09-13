# Preview.18 Release And Owned-Service Canary

## Published Release

- Tag: `v0.1.0-preview.18`.
- Reviewed source: `fef5e92470257733c9719c368fbfda2df86394b1`.
- Published: September 7, 2026, 20:48:03 UTC; immutable prerelease, not draft.
- Native workflow: `34160189029`; Docker workflow: `34160188973`. Both passed.
- All four native builds, frozen-app/update checks, assembled-payload validation
  and four clean installs passed before protected publication approval.
- Complete downloaded release verified against the exact tag and source SHA.
  GitHub/Sigstore verification pinned the repository, release workflow, source
  ref and commit for the manifest and Linux x64 archive. The attested manifest
  and checksums bind all assets; SBOM and version-pinned installers are present.
- Manifest SHA-256: `8abc7aebee9abe20be57c98b6152fb59651035cd638e371daa9ae1c53aa4bad1`.
- Linux x64 archive SHA-256: `405be1b35a75e81d5331470112bb071a17cdf8bbdb0f120752cb1303d3fa3c21`.
- Extracted Linux binary SHA-256: `5c53b2b24ea9c747f1e3458feddde8a505f369e859f0d675a75c268d71e34d8d`.

Windows remains unsigned and macOS unnotarized under the approved preview
policy, explicitly disclosed in the immutable manifest/release page. Do not
call these stable-platform signing proofs. Versioned Docker publication does
not promote `latest`.

## Core Admission And Upgrade

Production Core `84fe0fd6202c2744c970dfeebd5103f1ad13f883` / Alembic `0039`
admitted .18 at 20:53:03 UTC. Baseline .13 and upgrades .15/.16/.17 remain
supported; no operator must reenroll. The configuration update changed only
the exact upgrade list, retained a private rollback copy and passed candidate
validation and post-restart health. No shadow, compensation or pairing gate
was enabled. Private read-only checks preserved all 21 existing
identity/account/signer/review/qualification bindings and found zero rows in
all six compensation tables.

One owned Linux service upgraded from released .17 to the verified .18 binary
at 20:55:06 UTC. The same validator ID, configuration checksum and stopped
pending-journal digest were preserved. Candidate version, authenticated
`check --no-probe`, supported public .18 heartbeat and active service checks
passed. Core activity was 1,546 assigned, 1,531 completed and 1,431 attested;
these are cumulative counts, not newly submitted .18 evidence.

The service still runs under its existing dedicated user and private config.
Rollback selects its prior immutable .17 release without resetting state.
Fresh accepted report `123657`, created at 21:03:21.714220 UTC after the
upgrade, passed independent EIP-191 signer recovery, canonical envelope
SHA-256, assignment wallet/nonce/worker/evidence binding, and accepted-authority
checks. Its job has zero worker-ledger, reservation and credit-ledger rows.
This is an owned service upgrade and fresh signed-report canary, not an
independent operator, desktop one-click journey or real payout-consent test.

## Public Download Promotion

Website PR78 merged as `f236575a66945c83e45074ec20c281b400d9f7f4` after 112
unit tests and all 45 CI browser tests passed. Production Vercel deployment
`dpl_3XffNbUUW25QTzCJmvdxaEW9peCd`, created at 21:11:41 UTC and verified Ready
by 21:14 UTC, serves `aipowergrid.io`. All four archive links, installer and
checksum/SBOM links target .18. Desktop/mobile production browser checks pass,
including the separate app-update and managed-service guidance. These checks
mock only the public lookup fixture; they do not test operator wallet consent.
Rollback is the prior `dpl_8gms6bvTKebnZePkEDmdxoG9Vdno` website deployment.
No website environment or Core configuration was changed during promotion.
Cohort issue #5 was updated in place after checking its unchanged prior body.

The 21:14 UTC public network snapshot showed seven fresh heartbeats and zero
verified-independent operators. FoggyFinder and h0me1ca75 pass time/coverage
checks but remain unreviewed; Donli and peteq are offline. Do not replace their
identities or reinterpret technical readiness as operator-control proof.

## September 13 Owned-Service Rollout

The two remaining owned Linux services moved from the immutable preview.17
payload to the existing preview.18 release at 02:34:38 and 02:35:42 UTC.
Manifest and Linux archive provenance were reverified against the exact tag,
source commit and GitHub-hosted release workflow. The archive and extracted
binary hashes match the published values above. No new release was published.

Both candidates passed their version check and offline media-decoder self-test
under the existing unprivileged service user. Each service was stopped
separately; its configuration hash and entire stopped journal were unchanged
when the versioned binary symlink switched. Read-only authenticated registration
then confirmed the same validator ID, active status and preview.18. Running
process executable paths independently matched the intended release. Existing
service hardening, credentials and prior binaries were retained.

The first preflight failed because the rollout harness's restrictive umask
made its newly staged release directories inaccessible to the service user.
This happened before stopping or switching the old service. The corrected
harness explicitly sets traversal permissions on the non-secret binary
directories and verifies any existing candidate against the pinned archive
before reuse. The failure remains part of this rollout record.

At each cutover the journal contained 160 already-dead assignments and no
pending assignments or signed reports. Dead letters were preserved, not
silently retried or deleted. This is not a pending-report replay test; retain
the separately recorded September 7 lost-response experiment as its own proof.
An initial post-upgrade database check found no new reports from these nodes
yet. Fresh signed-report/assignment-binding checks remain outstanding for this
particular rollout; a heartbeat is not sufficient evidence of delivery.

The subsequent production snapshot showed nine active registrations with a
heartbeat in the preceding five minutes: four preview.18, four preview.13 and
one preview.15. These are version/heartbeat counts, not independently controlled
operators or qualified compensation participants. No Core deployment, payment
activation, media activation, qualification reset or public threshold change
was made by this service rollout. The versioned token-limit correction merged
in validator PR112 is newer than preview.18 and is not in these binaries.

## Still Outstanding

- Help external operators upgrade and confirm their fresh evidence.
- Verify fresh accepted reports from both September 13 owned-service upgrades.
- Retain the existing .15-to-.17 lost-response replay proof separately rather
  than relabeling it as a .18 upgrade-replay test.
- Exercise the production human wallet/node consent journey under a separately
  authorized narrow gate. The matching Console page is live at `28dbf5f3`.
- Complete three independent operator reviews and freeze one bounded seven-day
  pilot. No qualification reset or fabricated common-control proof.
- Obtain an explicit total compensation budget before creating a campaign.
  No payment, worker penalty, model-identity or fidelity authority is enabled.
