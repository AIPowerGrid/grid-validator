# Validator Qualification Decisions

Qualification and staged rollout checkpoint, 2026-09-07. This is an evidence
index and a preregistered gate for the next experiment. The deployment record
below is non-economic and does not activate new validation authority.
The full compatibility, baseline, substitution, capability, adversarial,
correctness, media and shadow-rollout objective remains open.

## Decisions From Completed Experiments

- Keep unsupported or partial logprobs unavailable for comparisons requiring
  complete observations. Seven preserved probabilities do not repair a missing
  first-word distribution. Do not convert native Responses evidence into the
  existing chat first-token policy.
- Do not promote the tested final-answer likelihood rule: its fresh evaluation
  flagged zero of 88 scorable smaller-model observations and zero of 13 controls.
  Zero false alarms is not useful discrimination when substitutions also pass.
- Do not promote the current fixed-context distance bands as model identity.
  Actual 20B/120B comparisons produced no anomaly-band observations, and copied
  reference distributions defeated the offline metric. Honest quantization
  differences also entered the gray band.
- Keep capability results separate from identity. A non-LLM solver passed the
  tested tool scenarios; that does not erase the capability result, but it does
  defeat a claim that passing proves a particular LLM was executed.
- Reference-based media comparison has caught real tested substitutions and
  temporal/source splices. Basic conformance and pHash alone have known misses.
  Do not turn same-host repeatability into a fleet tolerance or model/quant
  identity guarantee.

## Evidence And Unfinished Scope

The objective asks for an honest detection report, including failed methods,
not a guarantee that a successful model-identity detector can be built. Likewise,
an attack report must retain successful evasions; it need not claim they have
been prevented. Additional release/authority gates below are separate from
completion of the corresponding research experiment.

| Objective | Evidence | Scope still unproven |
| --- | --- | --- |
| 1. Backend compatibility | [Responses qualification](RESPONSES_QUALIFICATION.md): real LM Studio -> released worker -> local Core/Redis -> independent reader; 18 fault cases | Public Responses assignment/signing/outbox policy; first-word probabilities missing in measured native responses |
| 2. Honest baselines | [Engine baseline](HONEST_BASELINE_2026_09_06.md), [quant/load baseline](QUANTIZATION_BASELINE_2026_09_06.md) | Exclusive idle conditions, exact native LM Studio conditioning/settings, honest 120B cross-engine/quant range; historical timeout root cause remains unresolved despite bounded replay |
| 3. Substitution | [Answer scoring](ANSWER_FIDELITY_2026_09_06.md), [fixed contexts](FIXED_CONTEXT_FIDELITY_2026_09_07.md): real 20B/120B comparisons, reference-side scoring, fresh evaluation and honest controls; tested methods fail to reliably distinguish models | These reports do not qualify a detector for authority. Any new candidate method needs separate matched controls and fresh evaluation; retain the current negative results |
| 4. Useful work | [Tool pilot](TOOL_CAPABILITY_PILOT_2026_09_06.md), [full-answer/load study](QUANTIZATION_BASELINE_2026_09_06.md) | Broader independent workload coverage and public per-capability reporting; existing template tests do not certify intelligence |
| 5. Attacks | [Adversarial report](ADVERSARIAL_VALIDATION.md), including six real-PG copied-envelope/judgment and common-control cases; [initial live fidelity study](TEXT_FIDELITY_EXPERIMENT_2026_09_05.md), fixed-context and answer-scoring reports above | Probe-aware switching/proxying, fabricated probabilities and concealed collusion remain trust limitations. Three individually signed false judgments can form an accepted non-economic preview quorum; known-control exclusion does not discover hidden coordination |
| 6. Correctness | [Rollout evidence and delivery tests](ROLLOUT_2026_09.md): 55 real PostgreSQL 16 binding/race/retry/terminal tests, plus seven PG scorecard tests; Linux release CI and production backup/restore proof passed | Complete authenticated production validator/Console integration remains separate; worker-ledger atomicity is not a validator compensation send |
| 7. Media | [Image pilot](IMAGE_PILOT_2026_09_07.md): six same-artifact Apple/NVIDIA renders and twelve img2img renders across two recipe-enumerated samplers; [video pilot](VIDEO_PILOT_2026_09_07.md) | Broader scenes, edit instructions, workflow/quant variants and qualified references; one image scene/two seeds do not establish fleet tolerance. Untouched source copies pass all four img2img groups; source-binding and execution-proof limits remain |
| 8. Shadow rollout | [Core PR #117](https://github.com/AIPowerGrid/grid-core/pull/117) and [Console PR #25](https://github.com/AIPowerGrid/grid-frontend/pull/25) merged and deployed; dated verification below | Authenticated end-user scorecard render and an observed shadow run; zero reviewed independent operators in the pre-rollout snapshot. Deployment is not independent shadow authority |

## Scorecard Release Candidate

Core candidate `b843b8dd3e8ce69cfd7f3cbc286f2561419d27cc` was tested in
PR #117 before the merged deployment recorded below. Seven added
real-PostgreSQL scorecard cases cover signed
shared-group votes, missing/future/incomplete probe times, receipt-window
filtering, real foreign-key pruning and a read-only evidence snapshot. Three
registered validators remain one probe group, never three independent samples.

The exact clean commit passed 106 tests with no skips/failures on an isolated
PostgreSQL 16.15 runtime: 62 real-PG cases, 14 SQLite/utility terminal cases and
30 offline compensation cases. All captured sources remained unchanged and
the owned database stopped. This is synthetic evidence/storage qualification,
not live inference, production HTTP auth or a payment send. New tests pass
configured Ruff/Black; branch-history and staged secret scans pass. Console's
six metadata tests also pass without any frontend changes in this pass.

Private result commitments:

- Manifest: `bed5cf9ad36ba4c4909352c099e17b0044b12fb000abd1b5e2b9739cd23fb60c`.
- JUnit: `26c09515dfcf4cbc4523f49cd30567f8f6ca971bc9d47df29de6991ec24bbc9f`.
- Summary: `a954ed0690433b9c7b43041756c5dd3a7c4d800312dc5b4986bb5c5ce1602982`.

GitHub Linux/Python 3.12 [run 34087354680](https://github.com/AIPowerGrid/grid-core/actions/runs/34087354680)
passed the production dependency lock/audit, anti-gaming contract (15 tests),
backup/restore through Alembic `0034`, schema parity and full Grid suite:
1,143 passed, eight skipped, two warnings. The quiet CI report does not identify
skip reasons; do not describe this as zero skipped coverage. CodeQL and
secret/infra-string checks also pass. These checks qualify the candidate, not
live model identity, independent operators or deployed behavior.

Console PR #25 tested `005a1a849628fd370b5ae208ddc1a1cf38be1575` and adds the
six evidence-metadata tests to required CI. [Run 34087765631](https://github.com/AIPowerGrid/grid-frontend/actions/runs/34087765631)
passed the pinned pnpm frozen install, formatting, strict lint, six metadata
tests, production build and account/key-management/OAuth/pairing smoke tests.
The existing default-branch Faker and selector-parser advisories remain open:
Faker has no app/script imports in this checkout; selector-parser is transitive
CSS build tooling. No vulnerable API use was found in this scorecard diff;
this is scoped triage, not remediation or a general dependency security claim.

### Controlled Deployment

All three PRs merged through their required checks without an admin bypass:

- Core #117: `8e1b65f2ebbe6bf1b796933fbdd5800b31f1ec95`, deployed to the
  production API. Its tree equals the tested candidate. Main-branch
  [run 34088430917](https://github.com/AIPowerGrid/grid-core/actions/runs/34088430917)
  also passed. A fresh production backup restored into a disposable database,
  the candidate passed schema parity at Alembic `0034`, and the scratch database
  was removed. No production migration was needed.
- Console #25: `bfdee8eb55eb0315232c0651d843a0153848d811`, deployed on Vercel
  and assigned to `console.aipowergrid.io`. Its tree equals the tested candidate.
  The public sign-in page returns 200; anonymous dashboard access redirects to
  sign-in, and the scorecard proxy retains its 404 no-account response.
- Validator [#92](https://github.com/AIPowerGrid/grid-validator/pull/92):
  `95b593f19d1d7e98ef68150694fe495fb2f1df43`, merged source only.
  [CI 34088187721](https://github.com/AIPowerGrid/grid-validator/actions/runs/34088187721)
  passed the supported Python matrix and dependency audit: 344 tests passed and
  six opt-in pairing integrations skipped per matrix entry. Those six passed
  separately against the exact local Core/Console candidates.
  [Native run 34088187606](https://github.com/AIPowerGrid/grid-validator/actions/runs/34088187606)
  passed four-platform builds and clean installs: Linux x64/ARM64, macOS ARM64
  and Windows x64. Publication was intentionally skipped on this PR build.
  No new release tag, downloadable binary or cohort version was activated.

After Core cutover, public health reported the exact merged SHA, healthy Redis
and all nine workers reconnected. An authenticated account read returned 200;
anonymous assignments returned 401 and the retired heartbeat route returned
410. A read-only production service query at
`2026-09-07T06:02:43.202544+00:00` returned 69 scorecard groups with sampling,
probe freshness and uncertainty. All independent sample counts remained null.
This query was not an authenticated scorecard HTTP or browser test. The
Console view still depends on an account permitted to read validator data;
ordinary account access and the complete live browser flow are not established
by the deployment smoke checks.

Configuration remained byte-identical, payout and backup timers retained their
states, and the prior releases remain available for rollback. No paid inference
was submitted. Fidelity, media, rewards and independent shadow authority remain
off. The next validator binary still needs protected publication, staged live
delivery/recovery checks and a compatible operator upgrade plan.

### Account Access And Preview Publication Follow-Up

On September 7, Core PR #118 deployed `3f0b966a438177b5c695adec4f3e6132a1c237c1`
and Console PR #26 deployed `f060841828125f4cf5b2a110d53f820f5aa100f2`.
Both protected merges retain the exact tested candidate trees. Core CI run
`34090386886` passed 1,152 tests with eight explicit skips, plus anti-gaming
and PostgreSQL restore/parity checks. Console CI run `34090442269` passed.

`GET /v1/account/validator-scorecards` requires `account.read`, but no linked
wallet or node registration. It exposes only the existing bounded redacted
aggregates. The old validator-specific route and private assignment, probe,
attestation and health permissions are unchanged. Console forwards its current
user token and treats unavailable private health as optional, not zero counts
or a reason to discard readable reports. Local tests cover Google/SIWE/refreshed
account tokens, wrong scope, expiry, private-route denial and optional health
failures; those fixtures are not live Google or wallet-provider proof.

Production HTTP verification returned 200 for an existing account-read key,
401 for anonymous reports and assignments, and retained Console's login gate.
Core reports the new SHA, healthy Redis and nine reconnected workers. Vercel
reports the new deployment Ready under the public Console alias. Local rendered
checks passed at 1440, 768, 375 and 320 pixels, including private-health 403/503
and invalid JSON. A logged-in production browser journey remains unverified.
Configuration remained unchanged; no paid inference or economic activation.

Immutable prerelease `v0.1.0-preview.16` published at `2026-09-07T06:33:23Z`
from reviewed validator commit `323e0104a8a6a5886b6b58e14bf953dab5b93544`.
Release run `34090594246` passed all four native builds and clean installs;
container run `34090594219` also passed. The downloaded nine-file binary payload
passed the release verifier with exact tag/source binding. Each of the eight
checksummed assets independently passed GitHub provenance verification bound to
the release workflow, tag, source and hosted builder. Windows and macOS remain
explicitly unsigned previews; this is not a stable-platform-signing claim.

The preview.15-to-.16 Windows canary passed protected run `34092210339`.
The independent post-run audit verified its stored signature and assignment
bindings, one vote, suspension, revoked key and no economic rows; see
[Production baseline](PRODUCTION_BASELINE.md). This is one first-party runtime
sample, not an independent shadow run or a Responses assignment-policy test.
Public website recommendations and accepted cohort versions remain unchanged.
No model-identity claim, independent shadow authority or compensation follows
from this package release.

### Pre-Rollout Fleet Snapshot

The public network endpoint generated this snapshot at
`2026-09-07T05:44:14.282163+00:00`, Core
`c0cda681dc0f24aed4123f356b6ef115a3a30887`:

- 14 active registrations, eight fresh heartbeats, 11 participants in 24 hours.
- 690 completed assignments, 666 authoritative votes, six workers/six models
  covered. Votes and completed assignments are not independent workload counts.
- Fresh software split: four preview.13 and four preview.15 nodes.
- Zero verified/participating independent operators; independence not proven.
- Economic effect: none. Observability is active, but this snapshot does not
  qualify independent shadow authority or prove the new scorecards are deployed.

Captured public-response SHA-256:
`ab4ed179eed3b18e81882d69517570ed49fb9a8795cb412735a06d6d55f73275`.
This is a dated aggregate snapshot, not continuous monitoring or an identity
claim about any individual operator.

## Next Text Experiment: Frozen Acceptance

These criteria apply to a new, explicitly versioned candidate method. They do
not retrospectively qualify any completed study. Freeze the method, thresholds,
artifact/runtime matrix, context construction, case-family split and manifest
before the first held-out inference. Raw prompts and reference material stay
private. Calibration cases and all prior evaluation cases are ineligible as
fresh evaluation inputs. Any revision requires a new manifest and new holdout.

1. **Matched controls first.** Each claimed model has a pinned reference and
   honest candidate controls of that same model. Include each engine and quant
   variant the proposed claim covers. A 20B quant baseline cannot substitute
   for honest 120B controls. Unavailable artifacts narrow the reported scope,
   not the acceptance criteria of the missing comparison.
2. **Meaningful conditioning.** Compare identical independently tokenized
   contexts at lexical positions, or reference-score the candidate's actual
   answer with its full conditioning recorded. Distinguish top-k proxies from
   full distributions. Candidate-supplied probabilities cannot be the sole
   evidence for an affirmative model-execution claim.
3. **Case units.** For each claimed comparison, reserve 100 fresh case groups
   spanning at least four task families with at least 20 groups per family.
   Pair honest and substituted executions on the same cases. Repeat under
   observed idle and controlled load; repetitions, token positions and multiple
   validators do not increase the count of distinct case groups.
4. **No cherry-picking.** A case group is available only when all required
   runs for that comparison have usable evidence. Retain every unavailable
   group and reason. Any anomalous repeat of an honest group counts as one
   false flag, even if another repeat is unavailable; those two counts may
   overlap. A substitution group counts as detected only when every required
   eligible repeat is flagged; inconsistent outcomes are misses for this gate.
5. **Exploratory usefulness gate.** Require at most one falsely flagged honest
   group per 100 scheduled groups, at least 80 detected substitution groups per
   100 scheduled groups, and at most ten unavailable groups on either side.
   Require at least 70% detected among scheduled substitution groups in each
   family. Report eligible-only rates too, but they cannot replace scheduled
   denominators. These are pragmatic gates for another non-economic shadow
   evaluation, not a claim of a 1% population false-positive bound.
6. **Separate outcomes.** Report correct, wrong, budget-exhausted, unsupported,
   malformed evidence, reference failure and infrastructure error separately.
   Unsupported logprobs, reference disagreement or transport failure must not
   produce an accusation. Wrong output is capability evidence, not automatic
   proof of a substituted model.
7. **Adversarial qualification.** Repeat fabricated/copy-reported probabilities,
   replay, recognizable-probe switching, proxying and common-control cases.
   Record caught and missed attacks independently of statistical sensitivity.
   A method that matches honest output but can be satisfied by proxying may
   measure output fidelity; it still cannot prove local model possession.

Missing a gate means report the method as unqualified, with its useful and
failed observations intact. Do not tune on its holdout, silently relax a
criterion, or collect more repeats until the denominator looks favorable.
Confidence claims require a justified sampling design; correlated task families
and repetitions do not warrant an IID confidence interval by default.

## Preview Publication Gate

- Freeze and review the exact Core/Console/validator commit set, compatibility
  checks and rollback before deployment. No public capability advertisement
  until its complete authenticated runtime path is qualified.
- Show passing/failed/unavailable counts, retained assignment/group counts,
  registered validators, real probe freshness and explicit uncertainty.
  Unknown operator independence remains unknown; fresh receipt time cannot
  substitute for old probe time.
- Keep protocol/capability, experimental fidelity and operator independence
  visibly separate. A matching result must not become a verified-model badge.
- Keep automatic penalties and economic authority off. A shadow observation
  needs its own dated live record; rendered local mock data is not that record.
- Compensation remains a separately approved capped campaign with durable
  campaign/operator deduplication and verified transfers. Passing this research
  gate creates neither entitlement to payment nor permission to penalize.
