# Native-Context Candidate Answer Fidelity

Private exploratory study, 2026-09-06. This measures a proposed detector;
it does not ship a scoring policy or change production authority.

## Current Decision

Do not promote this final-answer likelihood rule into a model-identity policy.
The fresh quant/load follow-up below detects **0/88 scorable held-out 20B
observations** against the pinned 120B reference, with **0/13 scorable 120B
control flags**. Absence of false alarms does not rescue absence of detection.
This is a measured limitation of this particular rule and task set, not a
claim that all logprob-based methods are ineffective.

## Initial Result

The complete 96-generation run and 165 unique reference-scoring calls passed
the independent audit. **The proposed rule is not a qualified substitution
detector.** It missed most scorable smaller-model evaluation outputs, and its
few flags concern tiny likelihood differences on correct answers.

| Actual source | Generations | Correct final answers | Output-budget stops | Wrong/malformed/infrastructure |
| --- | ---: | ---: | ---: | ---: |
| Pinned 20B | 48 | 46 | 2 | 0 |
| Pinned 120B | 48 | 44 | 4 | 0 |

These are descriptive outcomes on these fixtures, not a model ranking. Every
completed answer was correct. All 48 within-model repeated token-sequence
pairs were identical, so repetitions do not provide independent evidence.

Held-out evaluation, using only the locally frozen calibration rule:

| Actual source | Evaluation runs | Scorable | Flagged | Unique scorable cases | Unique flagged cases |
| --- | ---: | ---: | ---: | ---: | ---: |
| 20B presented to the 120B reference | 24 | 22 | 4 | 11 | 2 |
| Same-artifact 120B controls | 24 | 20 | 0 | 10 | 0 |

The observed smaller-model flag rate is 4/22 scorable runs (18.2%), or 4/24
including the two unscorable runs (16.7%). Eighteen scorable runs were not
flagged. The four flags are both repeats of two paired extraction variants
from **one base fixture**, not four independent discoveries. The same-model
control observation is 0/20 scorable runs; it does not establish a low fleet
false-positive rate from ten distinct cases on one engine/artifact.

The frozen threshold is mean NLL `0.0000015497254021389634`, derived from 18
eligible calibration 120B runs. The two flagged case features are
`0.000011056906259909738` and `0.000002145774184706776`. These are tiny
differences in reference likelihood, not wrong answers or proof of dishonest
execution. No honest cross-engine/quant tolerance has been established at
this precision. Do not promote this threshold into a production policy.

Evaluation ineligibility was explicit: the 20B had one extraction case with
only one semantic token, repeated twice. The 120B had that same short-answer
case plus one budget-exhausted constraint case, each repeated twice. All 330
selected token positions had native reference scores: none was outside top 20.
Caching reduced those 330 bindings to 165 unique reference calls.

Measured summed HTTP time was 380.80 seconds for 20B generation, 641.36 seconds
for 120B generation, and 374.45 seconds for reference scoring. These exclude
model loading, hashing and other harness overhead; the shared host and cached
repeats make them descriptive run costs, not production throughput estimates.

Both owned model servers exited cleanly. The audit rehashed both model files,
verified every native witness and full-prefix binding, and checked the complete
schedule and decision rule. No production policy was changed.

## Why This Experiment

The earlier [single-token calibration](HONEST_BASELINE_2026_09_06.md)
could not separate four meaningful 20B/120B token distributions using the
unchanged public match band. This follow-up evaluates complete candidate
answers using only probabilities computed by the pinned 120B reference.
Candidate-supplied probabilities do not determine the feature.

## Retained Failed Attempt

The first raw-completion attempt stopped after nine 20B responses. Eight
exhausted a 32-token budget; one stopped on a newline. That stopped response
returned three token IDs but only two probability positions, violating the
harness's incorrect equal-length assumption. Raw few-shot text without the
trained chat template also produced unsuitable continuations.

The attempt remains frozen and has no completed detector result. These are
harness limitations, not evidence of worker dishonesty. A separate native
template control then returned correct structured output with reasoning and
108 complete token/probability positions, including the terminal token.

The replacement uses fresh inputs, not the old observed evaluation cases.

## Frozen Method

- Twenty-four independently checked synthetic cases: extraction, balance
  tracking, and binary-string constraints; twelve calibration, twelve evaluation.
  Each split has two paired base fixtures per family. Pairs change one input
  and require a changed answer. Both models repeat every case twice, giving
  96 generation slots, not 96 independent cases.
- Both GGUF files are the previously hash-checked publisher conversions in
  the baseline report. Both run on the same pinned llama.cpp b10826 engine
  and Apple Silicon host. No speculative draft, adapters or grammar constraint.
- The 20B native `/apply-template` endpoint renders one user message per case.
  Both models receive the identical explicit token IDs, independently checked
  by tokenization/detokenization on each runtime. This is one canonical
  template, not a comparison of each engine's native chat defaults.
- Context 4096, output budget 1536 including reasoning, temperature zero,
  seed 17, pre-sampling top 20, native special-token output, no custom stop
  strings, one slot, prompt caching disabled in request/server settings.
  Actual response settings are checked; timings are not cold-cache benchmarks.
- Retain the full native reasoning and final-channel output. Select tokens
  covering alphanumeric characters in final JSON values, excluding keys and
  punctuation-only positions. This narrowly supports these ASCII fixtures,
  not arbitrary Unicode, tool-call or every Harmony conversation shape.
- For every selected token, pass its exact preceding token IDs, including all
  candidate reasoning, to the pinned 120B reference. Score the actual candidate
  token using the reference's native next-token top 20. Unknown tail tokens
  remain censored, not zero probability or an automatic accusation.
- Cache identical reference prefixes explicitly. Reused scores do not count
  as independent reference executions. Hashes bind each candidate position to
  the complete reference prefix and native response.
- The feature is mean reference negative log-likelihood over selected tokens.
  Eligibility requires at least two selected tokens and complete score coverage.
  The frozen threshold rule is the maximum eligible calibration 120B feature
  plus `1e-12`; flag an eligible evaluation observation only when above it.
- Keep wrong answers, malformed/unavailable evidence, output-budget stops and
  infrastructure errors separate. No ineligible row is labeled dishonest.
  Wrong but valid JSON can still be eligible for the likelihood experiment;
  correctness does not silently determine the model-identity label.

Six pre-inference regression tests cover native final selection, corrupted
token/byte witnesses, budget classification, top-k censoring, independence from
candidate probability values and agreement with the independent parser.
An independent oracle checked every expected answer and both data splits
before inference. Cases, schedule, sources and decision rule were frozen.

## Interpretation Limits

A candidate can write reasoning that makes its final answer easy for the
reference to predict. This experiment deliberately retains that conditioning;
it does not pretend final-answer likelihood measures the origin of the entire
reasoning trace. Successful evasion of recognizable probes, proxying and
collusion remain separate attack gates.

Same-artifact 120B controls are useful but are not honest cross-engine or
cross-quantization controls. Repeats and paired variants are correlated, the
two splits share task templates, and one machine does not represent a fleet.
The public LM Studio worker remains running, so do not interpret timings as
isolated throughput or latency thresholds.

Do not tighten a production threshold from these results. Detection strength,
honest false alarms, coverage and capability accuracy must be reported
separately, including any inability to distinguish the models.

## Evidence

Private failed-run manifest SHA-256:
`b7e14b36b681b95ee62fa98f964f99eef926b48b60c3c6070bd4aca2dccc2c5e`.
Private failed-run raw responses SHA-256:
`dec0f311c6f1fe1f814dde589dfff81edb359b4882b2d9452ae46655328603b0`.
Private native-template control response SHA-256:
`5908c7c9ac7aeb5c8e6eb90cdf3e37b326284dcde9d44b0d04d2ca6cb2a58e18`.
Replacement study manifest SHA-256:
`7667480e42823adb9291a196402a0dfc05f5bd9b398c5a22c0363798949f1763`.

Completed study evidence SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| All native generations | `1f5550a3be32fd029c048e785e93c3b6b0984c5d52afdafe65b7118d63998f7c` |
| Native reference calls | `c53fdc9414c4009afe796ffe3376c521c8cec5267be5095f92c7def4b5244197` |
| Candidate/reference bindings | `d59936e8e707df4eba68a7b8bad1288c94fb23a05d1ac35ffbdfdb35c013efc3` |
| Canonical contexts | `cb70e7759ae2cc945221da4dc81ef4ad6a253f8427bba67d6e39edf2555d9650` |
| Independently audited summary | `0ceddc188152047f03ef9c03e10ba281ac8e155bb9bd04f3451b9deb999ee42a` |
| Post-run descriptive metrics | `27e57d8f4a5e980bd288f2630665fe404ee1f5ca16c955a30dbbd3d20346a6f0` |

## Fixed Scripted-Reasoning Attack

A separate completed follow-up tested 72 **scripted candidates**, not model
generations, against the unchanged threshold above. A deterministic standard-
library solver received only visible prompt text. No candidate LLM, expected-
answer access or reference-feedback search was used. Native reference calls
provided the scores; its tokenizer provided token/byte alignment.

The 24 inputs are disjoint from both earlier inference studies. Three fixed
arms run on every input: a plain correct answer; the same correct answer
preceded by manufactured reasoning that repeats it; and a deliberately wrong
answer preceded by the same style of reasoning. Cases, recipe, source hashes,
schedule and prior threshold were frozen before any reference inference.
Duplicate-case rejection is explicit and occurs before inference; this final
random seed required no rejection. Task templates and paired variants remain
correlated, not a general adversarial benchmark.

| Scripted arm | Candidates | Correct | Scorable | Flagged | Scorable, not flagged |
| --- | ---: | ---: | ---: | ---: | ---: |
| Plain correct | 24 | 24 | 21 | 14 | 7 |
| Primed correct | 24 | 24 | 23 | 17 | 6 |
| Primed wrong | 24 | 0 | 24 | 24 | 0 |

**The intended wrong-answer priming attack did not evade this frozen rule.**
All 24 fixed wrong-answer mutations were flagged and also failed the separate
correctness oracle. That result must not be rewritten as a successful attack.
The mutations were limited: adding an out-of-domain extraction record,
shifting one unit between balances, or increasing the constraint count by one.
They do not establish general resistance to manufactured reasoning.

The rule nevertheless did not flag seven plain and six primed correct outputs
from a solver running no LLM. Among the 21 cases scorable in both correct arms,
priming rescued no previously flagged case and turned one previously unflagged
case into a flag. This particular priming recipe did not improve evasion.
An unflagged observation is still not proof that the claimed model executed.
These are attacks on the private proposed metric, not live Grid API exploits
or accepted authoritative validator attestations.

Two plain-answer token positions were outside reference top 20 and remained
censored; those two candidates were unscorable. One additional plain candidate
and one primed-correct candidate had only one semantic token. No unscorable
candidate is counted as an evasion or a cheating accusation.

All 316 native reference requests completed without HTTP failure. Independent
verification checked every candidate/reference prefix, native probability,
answer oracle, unchanged threshold, source/runtime/model hashes and server
cleanup. The owned server was loopback-only with restrictive CORS and stopped
cleanly. The public worker was left running; no production policy changed.

Six pre-inference tests include 480 generated case checks, candidate file/socket
denial, duplicate-fixture handling and five corrupted reference bindings.
These reviewed in-process tests are not an OS-sandbox isolation claim.
Manufactured transcripts are explicitly labeled in private evidence, never
misrepresented as native model-generation witnesses.

Private follow-up SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Frozen attack manifest | `d6c558ecbd885a6f43975527329d61f155572813c876c9f4c2f6b46b611befc2` |
| Fresh cases | `8d3643aff6825b36afc74ec3a2a45fcfaea366ff10f597e5ba51e56328edc1b6` |
| Scripted candidates | `cf8a29d9a812cd20750ae5ff5bb6f11779444a39921e9a1568ab848e548d1731` |
| Native reference calls | `72b6046ade901e0fe90faeabf1664c074ab2557d88d2ed2997a4b8dde163cd94` |
| Candidate/reference bindings | `3c5fbefefaf854f90529e6b74f32a888d189dd5ba9a3c32bba9d5e734d73a305` |
| Independently audited result | `dd04871a4cddf569dc5b62968faa6dc5a69f23b59e9258373c7822f070f2705a` |

## Fresh Quant/Load Answer Evaluation (2026-09-07 UTC)

The follow-up retains all 256 actual 20B generations from the
[published quant/load study](QUANTIZATION_BASELINE_2026_09_06.md) and generates
one fresh actual 120B control for each of its 32 cases. No outcome-based
selection, discarded budget stops, threshold search or production inference
request was involved. The same earlier cutoff, `1.5497254021389634e-6`, was
frozen before any new reference inference.

The 32 contexts are disjoint from the initial answer study and span extraction,
state tracking, constraints and 4,930-token retrieval. They retain the parent
study's sixteen calibration and sixteen evaluation labels. Here the former
are diagnostic inputs only: **neither subset refits the historical threshold**.
Shared task templates, pairs, repeats and quant variants remain correlated.

| Actual source | All generations | Correct | Budget stops | Scorable | Flagged |
| --- | ---: | ---: | ---: | ---: | ---: |
| Published 20B Q8 artifact | 128 | 108 | 20 | 96 | 0 |
| Published 20B Q4 artifact | 128 | 107 | 21 | 95 | 0 |
| Pinned 120B control | 32 | 30 | 2 | 27 | 0 |

Every completed answer is correct. The published Q4/Q8 pair changes selected
attention/embedding tensors, not the MXFP4 experts; these labels must not imply
full-model four/eight-bit quantization. Candidate outputs include two repeats
under serial and observed two-slot load. The 120B controls are one serial run
per case, not a matching loaded/cross-quant honest reference population.

Held-out evaluation, kept separate from diagnostic rows:

| Actual source | Runs | Scorable | Distinct scorable cases | Flagged |
| --- | ---: | ---: | ---: | ---: |
| 20B Q8 evaluated as 120B | 64 | 44 | 11 | 0 |
| 20B Q4 evaluated as 120B | 64 | 44 | 11 | 0 |
| Same-artifact 120B control | 16 | 13 | 13 | 0 |

Both diagnostic and evaluation subsets produce zero flags. Evaluation
ineligibility is twelve budget stops and eight too-short answers per 20B
artifact; the 120B has one budget stop and two too-short answers. Across the
whole study, 43 budget stops and 27 answers with fewer than two semantic tokens
remain unavailable, never a detected substitution or evidence of honesty.

The complete native-prefix check preserves all candidate reasoning and verifies
every selected token ID against reference-decoded token bytes. It excludes
JSON keys and formatting-only positions and derives the feature solely from
reference probabilities, not the candidate's reported probabilities. All 678
selected positions have native top-20 coverage; explicit prefix caching reduces
them to 276 unique reference calls. There are no reference HTTP failures.

All eligible Q8 evaluation features are exactly zero as returned/computed from
the captured finite-precision scores. The maximum Q4 evaluation feature is
`1.5156690226701488e-6`; the maximum 120B evaluation feature is
`5.960464477539063e-8`. These are observed numeric values, not mathematical
certainty. They do not separate the actual model sources under the fixed rule.
Do not lower the cutoff after seeing these evaluation answers.

This is consistent with the already documented conditioning weakness: the
candidate's reasoning can make the final answer highly predictable to the
reference. It does not by itself prove that mechanism caused every miss.
The earlier four flags therefore do not establish generalization. Unflagged
answer likelihood cannot substantiate which weights produced an answer.

Both models use pinned llama.cpp b10826 and canonical explicit prompt IDs;
the 120B tokenizer independently reproduced every prompt and token prefix.
The current context allocation is 8192 versus the original threshold study's
4096, with the same 1536-token generation budget. This expanded workload tests
generalization, not an isolated experiment attributing differences to one
factor. Engine/quant/hardware false-positive bounds remain unqualified.

Independent verification checks all 288 source rows, complete schedules,
correctness oracles, semantic selection, context/token bindings and the unchanged
rule. The runtime/model/binary/library hashes and owned-server cleanup are
checked separately from the result counts. Independent audit and descriptive
analysis each reproduce their saved report byte-for-byte on rerun.
The six native-parser/scorer regressions also pass. Summed reference HTTP time is
1041.35 seconds; new control generation time is 385.19 seconds. These exclude
loading/hashing overhead and are not a production throughput estimate.
The owned 120B server stopped; the existing public LM Studio worker was left
running. No account, registration, authority, penalty or economic setting changed.

Private evidence SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Frozen follow-up manifest | `0040fa72ec1093e1339d7cfe6c3fc4783190cc67c180795d66bd50a016039154` |
| Fresh native 120B controls | `e86456dcc0a39606b8c3cd7a0d86acef26745381d3d1f08261d60570b5415333` |
| Native reference calls | `dc3eedba11278d3733f8a268d08e1aab07867a0957e1206e8a5cd190cec080bd` |
| Candidate/reference bindings | `b6357af848fb04dbaa3a0dae13a33bb5fe1c033d200544b893a93465a02a40fd` |
| Reference token-byte witnesses | `d64b0c701f7e666e1e6de677393c18b6b7736cfffb3fb6343abe59aa51615bc2` |
| Independently audited summary | `014a247517d69452ba1c35aac2a314a3d575c62085dd2902e7e089dac72b02a5` |
| Post-run descriptive metrics | `e7b8bc0881c9bfc45729104e823be3c325a69a39dce60f08b81af96aa0d3a9a2` |

## Next Gates

1. Reject promotion of the tested final-answer likelihood rule. Establish
   honest cross-engine/quant scoring controls before interpreting tiny
   likelihood differences in any replacement method. Zero control flags
   alongside zero detections is insufficient.
2. Broaden the fixed manufactured-reasoning test to production-shaped inputs,
   adaptive strategies with fresh held-out evaluation, and correct-model-only
   probe service. The one recipe above is measured, not an exhaustive defense.
   Reference-side probabilities remove one self-report dependency, not proof
   that the candidate generated its own reasoning or used the claimed weights.
3. Freeze new evaluation inputs before testing a stronger method. Candidate
   answer likelihood under candidate-supplied reasoning must not be marketed
   as model identity. The two splits here share task templates.
4. Preserve capability scores independently. These tasks demonstrated useful
   responses from both models, not a reason to penalize the smaller one.

No production registration, credentials, routing, economic flags or penalties
were involved. The broader validator qualification goal remains incomplete.
