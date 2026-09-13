# Preview.19 Rollout

## Published Artifact

`v0.1.0-preview.19` was published as a prerelease at
**2026-09-13T03:05:44Z**, from reviewed master commit
`7bbda88970e3eba304d97715a7f7a911e5ea439a`. Runtime changes since .18 are the
versioned token-limit correction in PR112; PR110, PR111 and PR113 are docs.
This release does not ship the private multi-context fidelity experiment.

Binary run `34734035168` passed four native builds, release payload assembly,
four native clean installs and protected publication. Container run
`34734035201` passed qualification and protected publication. Both used the
same source commit and exact protected tag. The sole maintainer's environment
review approved publication only after all native clean-install checks passed.
The tag push used the configured release-owner exception; no branch protection
or environment review settings were changed.

The downloaded payload passed complete-file-set, archive-layout, checksums and
exact tag/commit manifest validation. All eight checksummed artifacts separately
passed `gh attestation verify`, pinned to this repository, the release-binaries
workflow, exact tag and source SHA, with self-hosted runners denied. This is
downloaded binary provenance, not independent runtime container qualification.

| Artifact | SHA-256 |
| --- | --- |
| SHA256SUMS | `101a33e42b9211fd3253a58aae5bdeaf250820f2f4ad120e223aa16b60252397` |
| Release manifest | `2331926d6243ec37b661ad4dab3411407e12dd057acce4e8c9b8795375df9944` |
| Linux x64 archive | `92de1b32db53a6091a25d92d14395109cca94bf1b5746558ece9b457419e2a7c` |
| Linux arm64 archive | `cb09e1de1351b2209a1d89d613a96c57c99efb120a085d182f14aa0164dd26dd` |
| macOS arm64 archive | `6b9c2bee2b39c93c3cc00ecf6b6bb02088b3e7c6279aacaf72d0597ecd56c7af` |
| Windows x64 archive | `6f8adf1916a8fd0f150d0d2f2201bebff6b3152860b58b4b61348c143d3b2204` |

Windows remains unsigned; macOS is not Developer ID signed or notarized.
Preserve the explicit unsigned-preview warning. Publication is not a stable
release, economic activation or proof that existing operators upgraded.

## Core And Operator Gate

Core `d606e4d8` / Alembic `0042` is already live with `text.token_limit.v2`.
The live retained-response audit corrected 35 terminal-fragment false failures
across nine groups without changing stored v1 evidence or other real failures.
That counterfactual is separate from fresh v2 execution.

At publication Core still admitted .13 and .15/.16/.17/.18. At 03:16:03 UTC
the exact .19 tag joined that overlap through a drained, compare-and-swap
configuration restart. All earlier versions, billing controls and the payout
timer were preserved; the running process environment independently matched
the new list. Core remained `d606e4d8` / `0042` with eight connected workers.

One owned service upgraded to the verified .19 Linux binary with its same
identity, configuration hash and entire stopped journal. Its 161 existing dead
assignments and empty pending-report queue were retained. Registration became
active on .19 at 03:18:20.966431 UTC. Fresh report `127676` at 03:20:23 UTC
passed independent signature recovery, canonical hash and assignment binding,
with no credit/reservation/worker-ledger rows. It reported a failed SmolLM
instruction result, not token-limit v2. The other two owned services and the
website recommendation remain on .18.

The retained journal exposed the separate completed-empty delivery bug in
`EMPTY_COMPLETION_DELIVERY.md`. Qualify that correction before public promotion
so operators receive one recommended upgrade. Do not claim that this canary
proves fresh v2 scoring or that .19 contains the empty-completion fix.

For the corrected release, preserve every admitted version and qualification
record while extending the bounded upgrade list. Stage the verified candidate,
preserve each node's configuration, signing identity and durable journal, then
upgrade one owned service. Independently verify a new v2 assignment, signed
report, commitment and zero credit/reservation/worker-ledger side effects.
Retain old binaries and original v1 semantics for any outstanding work.

After the canary passes, finish the owned rollout and promote public download
guidance once. Do not reset operator identities, qualification history or dead
letters. External operator control reviews and human payout consent remain
separate gates. Validator compensation, media, shadow and penalty authority
remain off; no campaign was created by this release.
