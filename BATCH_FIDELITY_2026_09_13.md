# Fresh Multi-Context Fidelity Experiment

## Scope And Frozen Rule

This is private research, not a deployed scorer or an identity guarantee. The
earlier fixed-context study detected zero substitutions under its existing
distance bands. Those negative results remain in
`FIXED_CONTEXT_FIDELITY_2026_09_07.md`; this follow-up does not replace them.

Before new inference, the runner froze 32 new raw-text prefixes: eight each in
prose, science, software and operations. Random assignment formed four batches
of eight, with two contexts from each family. Each context was evaluated twice
on published GPT-OSS-20B Q8 and Q4 artifacts and the retained GPT-OSS-120B
artifact, for 192 native calls. Repeats are averaged within each context, not
counted as independent trials. All three backends received identical verified
token IDs and decoded raw prefixes; this is not chat-template calibration.

The decision rule uses only the preceding study's calibration Q8/Q4 controls:
four disjoint balanced batch means, taking the largest and multiplying by 1.25.
That fixed the threshold at **0.05834650517568059** before these new responses
existed. The new result did not tune the threshold. The metric is the existing
coarsened top-20 probability distance, not full-vocabulary Jensen-Shannon
divergence. An incomplete eight-context batch is unavailable, never a match.

## Observed Results

All 192 requests returned HTTP 200. There were 188 eligible observations and
four nonlexical observations, belonging to two repeated model/context slots
in the operations family. These made batch 1 unavailable for all three pairs.
It remains in the scheduled denominator; no replacement prompts were drawn.

| Pair | Batch 0 | Batch 1 | Batch 2 | Batch 3 |
| --- | --- | --- | --- | --- |
| 20B Q8 / 20B Q4 | 0.023643, no flag | Unavailable | 0.030358, no flag | 0.014541, no flag |
| 20B Q8 / 120B | 0.059201, flagged | Unavailable | 0.077566, flagged | 0.079602, flagged |
| 20B Q4 / 120B | 0.062435, flagged | Unavailable | 0.092372, flagged | 0.082452, flagged |

Each cross-model pair was flagged in **3/4 scheduled batches**, with one
unavailable. Honest 20B Q8/Q4 was flagged in **0/4**, also with one unavailable.
The two cross-model comparisons share contexts, models and reference evidence;
do not report six independent detections or a population accuracy percentage.
The first Q8/120B margin is only about 0.000855 above the frozen threshold.

An offline copied-distribution check returns exactly zero distance for all
188 eligible observations. This is a successful arithmetic evasion control,
not 188 live cheating workers. A worker that fabricates reference probabilities
or routes recognizable probes to the real model is still not caught by this
comparison alone.

## Verification And Limits

The auditor checked the complete schedule, unchanged sources and settings,
native token observations, model/library/binary hashes, identical contexts and
owned-server cleanup. Four rule tests passed, covering calibration-only
threshold selection, incomplete schedules, unavailable batches and boundaries.
All three experiment server PIDs exited; the existing public LM Studio and
worker processes remained alive. No Grid job, charge, registration, reward,
production threshold or economic-authority setting changed.

Private evidence commitments:

- Frozen manifest: `029d46c38ab5095616c1b614eb4939004401971bf88f7a26359d24729e82989b`.
- Finished capture index: `1331ae9b991ed9bdf36780086c8604b16f36c13b89bf854b53fb191292bf1dde`.
- Reproduced summary: `be6a7dc4e944dacafe4a5bc998f50a11d64fcd37b1a8d8f5e1a8764433267520`.

One pinned llama.cpp engine and four batches provide a useful development
signal, not fleet qualification. The honest precision control covers 20B,
not alternative 120B quants or engines. Prompt generation, batch size and the
1.25 factor are engineering choices, not a proven statistical confidence bound.
Model possession, workload quality and validator independence remain separate.

## Next Evidence Required

Freeze a new replication before inference; retain the current threshold and
the unavailable outcomes. Include honest 120B precision controls, matched
contexts on supported engines, and smaller-model substitutions in the actual
claimed-model direction. Then exercise the same comparison through assigned
probes and verified reports, including copied probabilities and probe-aware
switching. Do not enable routing, worker rewards or penalties from this result.
