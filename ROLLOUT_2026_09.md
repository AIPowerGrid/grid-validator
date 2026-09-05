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

## Completed September 5 Rollout

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

The pending fix keeps Set up and start as one confirmed action while handing
off from the enrollment child to a fresh runtime child. Tests must use real
Settings parsing, prove stale values cannot carry across, and suppress the
handoff after stop, close or failure. The live harness must expect automatic
startup and report only allowlisted app errors rather than a generic timeout.

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
- [x] Deploy Core compatibility with preview.13 as baseline and preview.14 as
  the exact reviewed overlap. Preserve qualification timestamps and samples.
  Shadow observation stays off during the overlap.
- [x] Publish immutable v0.1.0-preview.14 with four native archives, manifest,
  checksums, SBOM, provenance, and versioned containers after CI passes.
- [ ] Verify downloaded artifacts, run a first-party canary, and capture
  accepted signed evidence plus restart/outage recovery with the same identity.
- [x] Update the website, installers/docs, and operator instructions to the
  verified release. Existing operators reuse their private configuration.
- [ ] Roll first-party nodes, then support independent operators upgrading.
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
