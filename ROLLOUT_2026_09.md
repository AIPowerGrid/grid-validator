# September Validator Rollout

Owner: the AIPG maintainer. Updated 2026-09-07. This is the execution record for
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

## September 7 Updater Rollout

Preview.17 is published from `aa35fa0a8ddea9087c25da4756bffe7e2e514458`.
Native workflow `34136400434` and Docker workflow `34136400313` passed.
The native matrix includes actual frozen fixture startup, same-session handoff,
cold restart, failed-commit rollback and interrupted-selection recovery on all
four platforms. These fixtures have synthetic state, not live Grid evidence.

Publication completed at 15:15:53 UTC. All nine downloaded assets pass the
tag/source/checksum/manifest/archive verifier. The manifest passes GitHub
attestation verification bound to the exact workflow, tag, source and signer
commit, and the updater's own Sigstore verifier through the unauthenticated
public API. The Linux x64 archive's attestation was separately verified before
execution. Windows is unsigned; macOS is unnotarized. Provenance does not change
those platform-signing limitations.

Core PR122 (`3714a927`) is deployed with Alembic `0035`. At 15:23:41 UTC only the
reviewed upgrade-version list expanded to .15/.16/.17, preserving baseline .13
and every other environment value. All 21 stored validator identity,
qualification-start and private-review records have the same digest before
and after. The API and existing payout/backup timers are healthy. Core PR123
records the deployment and admission checks. No independence review, rewards,
routing, slashing, media issuance or shadow observation was activated.

One owned Linux x64 systemd node upgraded from released preview.15 to released
preview.17 at 15:31:39 UTC. The executable was authenticated before staging and
execution. Service stop, atomic version selection, no-probe registration and
restart retained its config hash, entire durable journal and registered ID.
The old binary remains available for rollback. The first attempt rolled back
after an HTTP error in the harness's public-status request; rollback restored
the old service with no automatic restart failures. A corrected identified
request passed preflight before the successful second attempt.

The node was online on an accepted release afterward. Its journal contained
historical dead-letter assignments but no pending signed reports; none were
deleted or retried to manufacture a passing test. At 15:35:53 UTC one fresh
authoritative report was accepted after the confirmed service upgrade. A
separate read-only production audit recovered its signature against the current
registered signer and verified the assignment owner, target worker, nonce and
evidence hash. The complete identity/qualification/review digest remains
unchanged. There were ten new verified fleet reports since the Core cutover at
that follow-up. An initial audit query incorrectly expected a software-version
field in attestation payloads; that field belongs to registration. Its empty
result is not evidence of missing delivery. The corrected audit uses the
confirmed service cutover time and independently verified signed records.
Real pending-report replay remains an open check. This is an externally managed
service upgrade, not proof of the app's live one-click path.

The public `/validate` page was checked and currently selects preview.16.
Preview.17 publication is not website promotion or completion of the bounded
independent paid-beta pilot. The remaining steps are live pending-report replay,
operator reviews, public rollout, the frozen pilot and separately approved
compensation accounting. Do not extend those claims from native fixtures.

## Release And Upgrade (September 5)

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

The first real run is complete; see
[the September 5 experiment report](TEXT_FIDELITY_EXPERIMENT_2026_09_05.md).
It measured 100-prompt same-backend and different-backend comparisons, copied
logprob evasion and a live probe-aware router. This does not complete the
cross-engine/quant or independently qualified reference gates below. First-token
protocol formatting confounds the apparent separation; authority stays off.

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

## September 6 Local Qualification

These are isolated experiments and source tests, not a fresh fleet snapshot or
production deployment. The September 5 operational observations above remain
dated observations.

- [Native Responses transport](RESPONSES_QUALIFICATION.md): fresh local
  backend inference through the released worker, Core WebSocket/Redis and the
  independent validator reader preserves seven native probability positions.
  Missing first-word coverage stays missing; this is not the public signed
  assignment loop or proof of complete conditional-context alignment.
- [Same-artifact behavior](HONEST_BASELINE_2026_09_06.md): 48 LM Studio/Ollama
  requests on the identical 20B file retain wrong, truncated and correct
  outcomes separately. Historical reference timeouts did not reproduce; their
  original cause remains unknown.
  A pinned local 120B follow-up now scores real 20B tokens at matching raw
  contexts: all four word-level comparisons remain inside the unchanged
  scorer match band. This is calibration evidence of a limitation, not a
  qualified detector or a reason to tune thresholds on these same samples.
- [Attention quantization](QUANTIZATION_BASELINE_2026_09_06.md): per-tensor
  provenance, 24 behavioral requests and a separate 24-request exact-context
  probability run. Native word probabilities can move substantially even when
  the chosen token does not change. No acceptance threshold is qualified.
- [Tool capability and template attack](TOOL_CAPABILITY_PILOT_2026_09_06.md):
  eight successful model episodes, but a non-LLM solver also passes 400 fresh
  randomized-value episodes. This is useful capability testing, not model
  identity or a successful defense against probe-aware workers.
- [Native-context answer scoring](ANSWER_FIDELITY_2026_09_06.md): 96 fresh
  generations and 165 unique reference calls, with every completed answer
  correct. The frozen rule flags 4/22 scorable smaller-model evaluation runs
  and 0/20 same-model controls. Those flags are repeats of two paired cases,
  not independent discoveries; tiny likelihood gaps and missing honest
  cross-engine controls prevent promotion into a production trust policy.
  A separate 72-candidate scripted attack records both misses and catches:
  seven plain and six primed correct outputs are scorable/unflagged without
  candidate inference; all 24 primed wrong mutations are flagged. This tests a
  private proposed metric, not an authoritative production attestation path.
  The September 7 UTC follow-up evaluates all 256 captured quant/load 20B
  answers plus 32 fresh 120B controls against the unchanged cutoff. It flags
  0/88 scorable held-out smaller-model observations and 0/13 scorable controls.
  Do not promote this final-answer likelihood rule: zero false alarms with zero
  detections is not useful model-identity discrimination. See the linked report
  for complete denominators, unavailable cases and 276 native reference calls.
- [Fixed-context distributions](FIXED_CONTEXT_FIDELITY_2026_09_07.md): 384
  native calls without candidate reasoning, 64 fresh contexts and three pinned
  artifacts. No actual 20B/120B comparison reaches the current anomaly band;
  most remain in match, while some honest quant pairs are gray. Copying the
  reference distribution defeats the offline metric on all 256 cross-model
  observations. This is not public assignment/quorum or model-identity proof.

Core's local `48f772ef` includes 20 additional signed-evidence tests. The exact
committed suite plus four existing validator concurrency suites passed on a
fresh, isolated PostgreSQL 14.19 instance: **45 passed, zero skips**. Invalid
assignment/worker/model/nonce/hash bindings, signatures, expiry, unfinished
probes and finalized groups are rejected without inserting evidence. Twenty
concurrent identical deliveries produce one accepted row and nineteen
duplicates. Conflicting submissions by one validator cannot multiply votes;
different-validator disagreement stays disputed. Existing tests cover
common-control assignment-seat exclusion, reference-pool exclusion, audit
budget races and shadow-run idempotency.

The fixtures synthesize completed probes and call the storage service. They do
not establish HTTP authentication, live model execution, operator independence
or future compensation correctness. PostgreSQL 14 is supplementary: PostgreSQL
16 PR CI remains required before a release. The private run manifest hashes
every test file and records the exact commit; its server was stopped afterward.

Evidence SHA-256:

- PostgreSQL final-run manifest:
  `a39132f303f31a942cd89439f132817c1ff9945d15df67c95e55132846374603`.
- PostgreSQL JUnit results:
  `b056f49294d1fcd32fae0a361681f1f461c20ff678dd60ed1fe5df0064112652`.

The validator working branch also reran its full unit suite: 342 tests,
six skips, no failures. All qualification branches remain local and unpushed
at this checkpoint. No policy, routing, credit, payout or penalty setting was
changed by these experiments.

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

Read-only production preflight at 18:53 UTC on September 5 is **not ready**:
neither lane has fresh media-capable validators or configured bond verification,
and the local curated snapshot yields no governed deterministic recipe. The
stricter `--sync-recipes --require-ready` check also fails because the configured
RecipeVault returns no governed recipes. This does not mean ordinary image or
video generation is offline; governed validation readiness is a separate gate.
Do not enable issuance or treat a local-only preflight as chain-catalog proof.

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

September 7 first-party follow-up: [VIDEO_PILOT_2026_09_07.md](VIDEO_PILOT_2026_09_07.md)
records four uncached LTX Director executions on one owned GPU, two same-seed
repeat pairs with identical decoded pixels, and actual-byte defect scoring.
Basic structural checks miss reversed playback and a two-frame oscillation;
the existing reference comparison rejects both in this pilot. Disagreement and
reference decode failures remain inconclusive. The initial cached repeat and
two harness corrections are retained. This completes a bounded calibration,
not the governed video, cross-hardware, image or independent-reference gates
above. No production issuance or economic authority was enabled.

The subsequent [IMAGE_PILOT_2026_09_07.md](IMAGE_PILOT_2026_09_07.md) records
twelve uncached Z-Image/FLUX renders across two seeds, using the owner's active
image backend. Honest repeats have equal decoded pixels; two cross-model
pairs are outliers in both directions. Grayscale removal and the wrong FLUX
seed remain accepted by v1. Keep those misses explicit and do not tune the
threshold to this scene. Cross-hardware, workflow variants and independent
references remain open; issuance stays gated.

The video report's image-to-video follow-up adds five uncached executions:
two source images, their repeats and one deliberately bypassed conditioning
run. Honest repeats match in decoded pixels. First-frame pHash distances to
the intended source are zero for the conditioned outputs and 32 for the
bypassed output, yet all five pass the existing structural contract. A
source-binding policy is not implemented or calibrated by these measurements.
The subsequent nine-clip offline study covers first-frame/prefix splices and
codec/resize controls. First-frame-only comparison is defeated; full-clip v1
rejects the tested splices and accepts all three reconstruction controls.
Broader scene/crop/hardware and legitimate temporal controls remain required;
this does not enable public media assignments or penalties.

## Attestation Delivery Follow-Up

Local unreleased hardening, September 7 UTC. A client defect treated any
successful HTTP response from attestation submission as delivery and removed
the durable envelope. Regression fixtures reproduced deletion after a wrong
receipt and acceptance of HTTP-200 error/HTML/empty responses. This is a
delivery-loss risk, not evidence of observed production loss.

The client now requires HTTP 200 and an `accepted` or `duplicate` receipt with
a positive integer stored ID, the exact canonical payload/signature hash and
matching authority. Assignment-bound evidence also requires matching assignment
and probe-group IDs and verified signature status. Unsigned preview helpers
remain preview-only; signature-prefix normalization matches Core. Duplicate
JSON keys, malformed bodies and uncommitted HTTP 202 responses cannot clear
the local queue. Failed checks use existing retry/dead-letter limits.

The probe client separately requires a completed object for the requested
assignment. A full local round/restart/retry test feeds Core-shaped inconclusive
responses through HTTPX and proves no signing, no attestation submission and
no silent revival after the assignment becomes a dead letter. Operational
probe failure is not a worker-failed verdict.

Eight unit methods cover these paths and negative subcases. The full validator
run completed 350 tests with six explicit optional-integration skips and no
failures, using the validator dependency environment. Earlier invocations with
the Core-only environment or a forced `VALIDATOR_ENV` override were unsuitable
for the complete suite; they are not passing runs.

Four additional cross-repo tests use Core's real signature/assignment checks
and disposable PostgreSQL persistence with simulated HTTP delivery. Each first
commits an attestation, then loses the reply or corrupts its hash, assignment ID
or authority. The client retains the exact envelope across reopening SQLite;
replay receives Core's matching duplicate receipt and clears the queue. The
database contains one vote throughout recovery. The matching envelope hash is
checked against Core's implementation, not just a duplicated unit-test formula.

The final formatted source passed all 49 PostgreSQL 14.19 tests (four new plus
45 existing evidence/concurrency tests), with zero skips or failures. Core was
`ebe97a61`; the owned database stopped. Private evidence SHA-256:

- Final summary: `28d0bf893c461dff1bb38251847f8a2fb69e35b09b846c1a0dcbd524a53175b2`.
- Source-bound invocation: `145e0c44447e64c12387804bbbbde06e331a6d055291a745a25c945c04cc478c`.
- JUnit: `4c3da491a5a2f2c08c3547f58a69c967d415c23f7e4d6e0de68aa9e36d033264`.

These are delivery/persistence checks with synthesized completed probes. They
do not prove native inference, HTTP authentication, operator independence,
future compensation or PostgreSQL 16 release qualification. Receipt matching
does not make a dishonest coordinator trustworthy. No public Responses
assignment policy, capability advertisement, automatic penalty or deployment
is introduced by this change.

## PostgreSQL 16 Terminal Qualification

Local Core `2cc536dd34900a44f1c0c6dfba0fadf6b51e116e` passed a fresh
PostgreSQL 16.15 qualification run with **99 tests, zero failures or skips**.
The final manifest records a clean Core worktree and unchanged Core/validator
Python source hashes. A preceding source-bound working-tree run also passed.
The database was built in a private prefix from the checksum-verified
[official PostgreSQL source archive](https://ftp.postgresql.org/pub/source/v16.15/).
Neither an existing database nor a production service was changed.

The count is deliberately split by what it proves:

- 49 real-PostgreSQL evidence, signature/binding, common-control, budget,
  shadow-run and cross-repo receipt-recovery tests, previously run on PG14.
- Six new real-PostgreSQL worker-ledger/audit-terminal cases. Three modality
  cases each race twenty completions after observing at least two genuinely
  blocked database backends: one settles and nineteen return duplicate, with
  one ledger row and one charge against each of four budget scopes.
- One of those six cases races release against success and checks that the
  resulting state is either charged/paid or released/unpaid, never both. It
  does not claim to enumerate every possible database interleaving.
- The other two cases terminate the actual transaction backend after the
  ledger insert, either before or after budget writes but before commit. Both
  return an error, retain the original hold, and leave no ledger row or spent
  budget. A subsequent retry settles once; the following retry is duplicate.
- 14 existing terminal/utility tests using SQLite or no database, plus 30
  pure/offline compensation-preview tests. These 44 are not PG concurrency
  proofs. The 99-test total must not be described as 99 PostgreSQL tests.

The new fixture creates and drops only its generated schema. The harness
starts a new loopback-only cluster with production environment stripped,
records immutable sources/results, and stops that cluster in cleanup. Tests
use synthetic completed probes and worker outputs. Killing a database backend
tests transaction rollback, not every possible whole-Core crash or network
partition. The worker completion ledger is not a sent on-chain payment or a
validator compensation entitlement.

Private final-run SHA-256:

- Manifest: `5ebb0d0c54192a22afe359ef2f75059010ebc579673c4106be9f71ea334be32f`.
- JUnit: `6940a79a09d11f83a906833b38e201ff3e1ce8dd930aef4a54ba671cb9730d02`.
- Summary: `7b1404458e40e47af34dfc43c10ee938fb196d7442cc088f41f1cb93bbc04786`.
- Stopped-server record: `2ed7d5ebca33929df5b21f41d1b710aef81e6f4992a848b9e471f3c2179281eb`.

This closes the local PostgreSQL-major-version evidence gap for these cases,
not the required Linux/Python-3.12 PR CI, migration/restore proof, authenticated
HTTP integration, public shadow deployment or compensation sends. The local
runtime is macOS/Python 3.13 and disables ICU/readline/zlib at PG build time.
No feature flag, scheduler, policy, routing or economic authority was enabled.

The changed-source secret scan and the tested Core branch's complete reachable
history passed. A broader all-local-refs scan flagged 14 entries outside that
history, including archived/remotely tracked branches. Their redacted metadata
is retained for separate review; this is not an all-refs secret-clean claim.
No history or scan exclusions were rewritten to suppress findings.

## Immediate Operator Follow-Up

- Ask existing operators to install preview.15 while preserving configuration
  and their `val_*` ID. Confirm fresh accepted evidence after each upgrade.
- Obtain the owned text-serving host and a non-disruptive test allocation. Its
  bridge was located on the chat frontend VM and upgraded to v0.3.8 while
  preserving the config and signer. Direct backend calibration is now recorded
  above. Rack-level configuration access is still needed for verified
  same-family engine/quant comparisons; do not evict production media workloads.
- Complete Peteq's existing qualification review rather than restart the
  72-hour observation. Core PR113 corrected the mature candidate's next-action
  copy; the fix is included in the separate `8380dfdf` production release.
  Correcting that copy does not bypass signed-control or common-control
  review, and a public validator ID alone is not authority to approve someone.
