# September Validator Rollout

Owner: the AIPG maintainer. Updated 2026-09-05. This is the execution record for
the controlled rollout, not a declaration of production quality authority.

## Pre-Rollout Snapshot

Read-only production checks at approximately 17:28 UTC on September 5:

- Core is `d348f0799f89cf8253b8341c5b3df59ef0151597`.
- Targeted, sealed text assignments and ordinary preview quorum are enabled.
- Text fidelity, image/video fidelity, rewards, stake, and epoch roots are off.
- Eight active registrations have a heartbeat within fifteen minutes: five
  preview.13 and three preview.9. Registration is not independence proof.
- No registration has a current completed independence review.
- The public worker inventory has nine online workers across modalities.
  Each advertised text model currently has only one online worker. There is
  no live same-model candidate plus two-reference cohort yet.
- The media reference table has zero active qualified rows.
- Text worker v0.3.8 includes native logprob relay. A released worker version
  does not prove a particular running worker has upgraded.
- Published validator binaries remain preview.13. Reviewed source contains
  text fidelity, decoder fairness, account-pairing UI, and onboarding fixes.

Individual operator identities, control reviews, credentials, and raw workload
evidence belong in protected operational storage, not this public report.

## Initial September 5 Rollout

- Core `6f12de6fdafa970caae6f5e380fdf72796a920ee` is production-live.
  A fresh production backup restored and migrated cleanly in an isolated
  scratch database; schema head remains `0034`. No live migration was needed.
- Validator preview.14 binds source `d5e7b3e2ef9ac8c5c905432ec5b5613f2f3c7444`.
  Binary workflow `33981849563` and Docker workflow `33981849520` succeeded.
  The published payload passed the exact-tag/commit asset verifier and GitHub
  provenance verification for all archives, installers, manifest, and SBOM.
- All three first-party Linux x64 nodes now run preview.14 with existing
  identities and state preserved. The first rolling canary submitted fresh
  accepted, signature-verified evidence at 17:57:09 UTC. Its failed code-task
  verdict was accepted evidence, not a claim of worker health.
- Core's exact preview.13/preview.14 overlap preserves qualification history.
  Fidelity issuance, media issuance, shadow authority, and rewards remain off.
- The public download page is deployed from website PR66 (`50778ff1`) and all
  eight website Playwright tests pass. Current installer/archive links and
  Docker instructions selected preview.14. Operator docs are merged in PR87.
- At 18:09 UTC eight nodes had fresh heartbeats: three first-party preview.14
  and five preview.13. All eight had verified assignment-bound reports in the
  preceding 24 hours; none had a current completed independence review.
- Four-platform packaging passed; this does not replace a preview.14 human
  Windows/macOS journey or the still-open real-model fidelity experiments.

### Fresh Setup Failure And Containment

Windows live run `33983090757` failed during fresh app enrollment before
registration. The canary revoked its one generated key; no registered node
or accepted report was left behind. The newer automatic-start path imported
Settings before writing its key and then reused that stale snapshot. Its old
unit test mocked Settings validation. Existing configured first-party runtime
proof is unaffected, but fresh enrollment is not qualified.

The public website deployment was rolled back to its proven preview.13
download path on September 5. Do not recommend a replacement until a fresh
published-binary canary passes. Preview.14 remains immutable; never replace
its archives. Operators who already installed it can preserve their config
and use Start after setup, but the replacement release should remove that
extra recovery step.

The fix in PR88 (`809b357c`) keeps Set up and start as one confirmed action while handing
off from the enrollment child to a fresh runtime child. Tests must use real
Settings parsing, prove stale values cannot carry across, and suppress the
handoff after stop, close or failure. The live harness must expect automatic
startup and report only allowlisted app errors rather than a generic timeout.

### Replacement Release Qualification

Preview.15 is published against `809b357cec6ca51a78cc8fe3f8013543b0522c02`.
Binary workflow `33984143672` and Docker workflow `33984143652` succeeded.
All four archives, both installers, the manifest and SBOM passed exact
tag/commit/checksum verification and GitHub provenance verification. The source
suite passed 332 tests with six optional skips; the fresh-settings regression
uses real separate child processes rather than mocking Settings validation.

Core now accepts preview.13 plus the exact preview.15 upgrade. The guarded
configuration change verified that this was the only changed setting and
checked the running Core commit after restart. All three owned Linux nodes
run preview.15 with their existing identities and state preserved.

Windows run `33984552555` overlapped that Core restart and failed enrollment;
it is an invalid qualification attempt, not a product regression result. Its
cleanup did not complete during the outage. A read-only production check
found zero accounts created in its enrollment window (18:40:51-18:40:57 UTC).
Repeat run `33984877376` is against stable Core with further Core deployments
paused. It passed fresh enrollment, one accepted signature-verified tool-chain
report, identity-preserving upgrade/restart, actual network outage/recovery and
full retirement (suspended, one key revoked). Independent database checks
confirmed suspension and zero payout/reservation rows for its probes. Website
PR67 (`008d37df`) passes all eight browser tests and is deployed for preview.15.
After explicit promotion of the reviewed Vercel deployment, the public
`aipowergrid.io/validate` page was checked to contain only preview.15 release
links. The old preview.13 rollback deployment remains available.

At 18:45 UTC there were eight ongoing online nodes: three owned preview.15
and five other preview.13 registrations, all with verified assignment-bound
reports in the prior 24 hours. The additional disposable Windows canary is
excluded from this fleet count. No completed current independence review has
been established. Peteq's public record now satisfies elapsed time and coverage,
but that does not replace the separate signed-control/common-control review.

The existing read-only 24-hour text calibration report also shows non-fidelity
GPT-OSS failures with `empty_visible_output` on stop-sequence and token-limit
probes. Investigate reasoning budgets and backend behavior before attributing
these to worker misconduct. Report rows count assignments, not independent
operators or independent model experiments. No model-substitution accuracy or
false-positive rate has yet been measured.

The first Core cutover's verification mistakenly targeted the default API port
instead of the deployed service's port and rolled back automatically. The
corrected deployment verified the actual bind address and public health before
proceeding. Rollback release and environment backup remain available privately.

## Release And Upgrade

- [x] Isolate the release work from existing local branches and unfinished edits.
- [x] Check current source and four-platform build results for reviewed master.
- [x] Reproduce and fix malformed reference IDs escaping as TypeError.
- [x] Add scorer attack baselines for copied logprobs and probe-only correctness.
- [x] Merge validator PR86 (`d5e7b3e`) and Core PR112 (`6f12de6f`).
- [x] Deploy Core compatibility with preview.13 as baseline and preview.15 as
  the exact reviewed overlap. Preserve qualification timestamps and samples.
  Shadow observation stays off during the overlap.
- [x] Publish immutable v0.1.0-preview.15 with four native archives, manifest,
  checksums, SBOM, provenance, and versioned containers after CI passes.
- [x] Verify downloaded artifacts, run a first-party canary, and capture
  accepted signed evidence plus restart/outage recovery with the same identity.
- [x] Update the website, installers/docs, and operator instructions to the
  verified release. Existing operators reuse their private configuration.
- [x] Roll all three first-party nodes with private configuration preserved.
- [ ] Support independent operators upgrading.
  Record ordinary human Windows interaction separately from CI/runtime checks.

Qualification is operational history plus a separate review of operator
control. A software upgrade must not discard observation history. Accepting a
reviewed version never grants operator independence or enables scoring effects.

## Text Fidelity Experiment

Run on explicitly owned test workers. Keep public fidelity issuance off until
the isolated experiment has usable logprob evidence. Do not register a fake
model claim in the public production inventory to test substitution.

1. Inventory serving engine/version, tokenizer/chat template, model revision,
   quantization, GPU, and native logprob support on the owned machines.
2. Capture at least 100 fresh prompts per available configuration pair using
   the exact Core challenge generator and request parameters. Store prompt and
   response evidence privately with configuration hashes and timestamps.
3. Establish a repeated same-engine/same-model baseline, then test the same
   weights under another supported engine or quantization. Sequential repeats
   on one GPU are useful calibration, not independent references.
4. Replay the same prompts against a smaller/different model in the isolated
   runner. Compare both candidate/reference and reference/reference distances.
5. Report false failures on honest pairs, detected substitutions, inconclusive
   results, missing-logprob coverage, latency, and sample counts separately.
   No rate claim is valid when the relevant configuration has no measurements.
6. Use a separate held-out batch to assess any proposed threshold change.
   Versioned scorer constants must not be tuned silently in production.
7. Test copied/forged distributions and a proxy that invokes the correct model
   only for recognizable probes. Record evasion as failure of the detector.
8. Only then populate explicit references/model allowlists for a bounded
   evidence-only production canary and verify zero economic side effects.

The current scorer looks at a worker-reported first-token distribution. Output
hashes bind the reported bytes but cannot prove which weights produced them or
that the logprobs correspond to those bytes. Reference agreement does not fix
that trust gap. Synthetic regression tests already show copied distributions
and correct-model-only probe responses can score healthy. These are executable
limitations; they are not live attacker trials or model-substitution benchmarks.

## Compensation Pilot Proposal

Proposed budget: 10,000 AIPG total for seven days, at most 2,000 AIPG per reviewed
independent operator. This is a proposal, not an enabled payout or approved
transfer manifest. First-party nodes are excluded. Unallocated funds remain in
treasury; budgets are never increased automatically.

- Freeze a campaign ID, UTC start/end, operator eligibility, source commits,
  and accepted-work criteria before earning starts. Publish the terms.
- Count at most one timely, signature-valid, assignment-bound contribution per
  operator and probe group. Duplicate delivery/retry creates no extra units.
- Cap eligible units at 100 per operator per UTC day. Inspect a random sample
  by independently recomputing verdicts from committed evidence. Disputed or
  unreproducible evidence is held for review; agreement alone is not correctness.
- Split the fixed pool pro rata over reviewed units, apply the per-operator cap,
  floor to token base units, and leave any remainder undistributed. Multiple
  nodes owned by the same person share one cap.
- Produce a dry-run manifest binding campaign, recipient proof, units, amount,
  evidence digest, and total. Resolve payout wallets through account ownership;
  do not send to ephemeral validator signing keys by assumption.
- Before any payment, prove budget and duplicate guards on PostgreSQL and use
  the existing receipt-verified payout rail only after reviewing its campaign
  support. A campaign plus operator must have one durable payout identity.
- Require explicit approval of the budget and exact transfer manifest before
  sending. Compensation does not confer routing, stake, or slashing authority.

This rewards audited pilot contributions. It does not claim that synthetic
canary agreement proves general model quality, nor that accounts are Sybil-proof.

### Implementation Gates Before Funding

Core's existing `validator_audit_budgets` funds **worker execution of audits**;
it is not a validator reward ledger. Likewise, the current custodial payout CLI
splits worker den for a time period. Neither can be relabelled as this pilot or
fed invented worker completions to pay validators.

1. Add a separate immutable campaign and reviewed contribution ledger. Enforce
   unique `(campaign_id, operator_control_group, probe_group_id)` units and
   unique `(campaign_id, operator_control_group)` payout manifests in PostgreSQL.
   Private control groups must not appear in public receipts or manifests.
2. Require a current control review at contribution time and at manifest
   approval, plus explicit recipient ownership proof. A generated validator
   signer is not automatically the operator's desired payout wallet.
3. Freeze recipient, evidence digest, integer token amount and campaign end
   before sending. Changed review, recipient or evidence requires a new reviewed
   manifest, not a mutation of an in-flight payment. Replaying a campaign under
   a different display name cannot create a second entitlement.
4. Reuse verified transfer/receipt mechanics only through an explicit campaign
   adapter sharing the treasury nonce lock with existing payout rails. Prove
   duplicate manifest, concurrent runners, crash before/after broadcast, pending
   receipt, partial batch retry and budget-cap cases on real PostgreSQL.
5. Test a dry manifest first, then obtain explicit approval for one bounded
   transfer. Publish the approved terms before the earning window; no retroactive
   promise is implied by this proposed seven-day campaign.

## Image And Video

- [ ] Start with one active image model/workflow and explicit seed. Capture
  same-hardware repeats, cross-hardware agreement, and deliberate wrong-model,
  wrong-seed, corrupt-file, dimension, and blank-image cases.
- [ ] Pin workflow, model, VAE, sampler, scheduler, steps, guidance, resolution,
  and relevant runtime revisions. A seed or pHash alone does not identify a quant.
- [ ] Qualify two independently controlled reference operators before public
  media assignment issuance. Owned replicas count only as calibration.
- [ ] Verify immutable witness retention and local decoder-failure fairness.
- [ ] Repeat for one governed video recipe, including frame timing, duration,
  static-frame substitution, decode bounds, and reference disagreement.
- [ ] Record canary results and zero economic side effects before wider rollout.

Do not waive the absent reference pool by labelling owned replicas independent.
Unfinished empirical work and unavailable hardware remain explicit open items.
