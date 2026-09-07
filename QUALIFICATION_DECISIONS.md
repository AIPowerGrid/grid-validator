# Validator Qualification Decisions

Local qualification checkpoint, 2026-09-07. This is an evidence index and a
preregistered gate for the next experiment, not a deployment or activation.
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
| 5. Attacks | [Adversarial design](ADVERSARIAL_VALIDATION.md), [initial live fidelity study](TEXT_FIDELITY_EXPERIMENT_2026_09_05.md), fixed-context and answer-scoring reports above | Probe-aware switching/proxying and fabricated probabilities remain trust limitations, not solved problems. Cross-check copied/common-control evidence tests before declaring the complete attack matrix covered |
| 6. Correctness | [Rollout evidence and delivery tests](ROLLOUT_2026_09.md): 55 real PostgreSQL 16 binding/race/retry/terminal tests, including killed transaction backends and strict matching receipts | Linux release CI, migrated-database and authenticated production integration; worker-ledger atomicity is not a validator compensation send |
| 7. Media | [Image pilot](IMAGE_PILOT_2026_09_07.md), including six actual same-artifact Apple/NVIDIA renders; [video pilot](VIDEO_PILOT_2026_09_07.md) | Broader scenes, workflow/quant variants and qualified references; one image scene/two seeds do not establish fleet tolerance; measured misses and source-binding limits remain |
| 8. Shadow rollout | Core sampling metadata is under review in [Core PR #117](https://github.com/AIPowerGrid/grid-core/pull/117); Console preview context remains a local candidate | Reviewed release/deployment, fresh live operator qualification and an observed shadow run; local UI tests and a draft PR are not publication |

## Scorecard Release Candidate

Core `b843b8dd3e8ce69cfd7f3cbc286f2561419d27cc` is pushed to draft PR #117,
not merged or deployed. Seven added real-PostgreSQL scorecard cases cover signed
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

GitHub Linux/Python 3.12 CI must independently pass the production dependency
lock/audit, full Grid suite and PostgreSQL migration/restore gates before this
draft can be considered merge-ready. Do not infer success from local tests or
the existence of a workflow run. No automatic merge, deployment, new public
Responses assignment policy, compensation or penalty activation is enabled.

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
