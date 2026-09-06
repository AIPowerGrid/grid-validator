# Native-Context Candidate Answer Fidelity

Private exploratory study, 2026-09-06. This measures a proposed detector;
it does not ship a scoring policy or change production authority.

## Result

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

## Next Gates

1. Establish honest cross-engine/quant scoring controls before interpreting
   tiny likelihood differences. Same-artifact control success is insufficient.
2. Test whether full reasoning makes the method easy to evade deliberately,
   including manufactured reasoning and correct-model-only probe service.
   Reference-side probabilities remove one self-report dependency, not proof
   that the candidate generated its own reasoning or used the claimed weights.
3. Freeze new evaluation inputs before testing a stronger method. Candidate
   answer likelihood under candidate-supplied reasoning must not be marketed
   as model identity. The two splits here share task templates.
4. Preserve capability scores independently. These tasks demonstrated useful
   responses from both models, not a reason to penalize the smaller one.

No production registration, credentials, routing, economic flags or penalties
were involved. The broader validator qualification goal remains incomplete.
