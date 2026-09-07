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

## Still Outstanding

- Promote website downloads from .17 after reviewing this evidence.
- Retain the existing .15-to-.17 lost-response replay proof separately rather
  than relabeling it as a .18 upgrade-replay test.
- Exercise the production human wallet/node consent journey under a separately
  authorized narrow gate. The matching Console page is live at `28dbf5f3`.
- Complete three independent operator reviews and freeze one bounded seven-day
  pilot. No qualification reset or fabricated common-control proof.
- Obtain an explicit total compensation budget before creating a campaign.
  No payment, worker penalty, model-identity or fidelity authority is enabled.
