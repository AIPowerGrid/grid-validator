# Honest Same-Artifact Baseline

Completed private exploratory run, 2026-09-06. No production policy change,
automatic penalties, public fake registrations, or compensation side effects.

## Result

The same GGUF produced different behavioral outcomes across two serving stacks.
Even repeated requests to one stack changed outcome despite requesting
temperature zero and a fixed seed. A mismatch with a reference answer is not
by itself evidence of substituted weights.

| Stack | Client scheduling | Correct | Wrong final JSON | Truncated | Infrastructure errors |
| --- | --- | ---: | ---: | ---: | ---: |
| LM Studio | Serial | 9 | 2 | 1 | 0 |
| LM Studio | Two overlapping requests | 9 | 1 | 2 | 0 |
| Ollama | Serial | 9 | 2 | 1 | 0 |
| Ollama | Two overlapping requests | 10 | 1 | 1 | 0 |

Each row contains 12 requests: six cases, repeated twice. The entire experiment
contains six distinct cases, not 48 independent samples. Do not rank engines or
estimate general model accuracy from these counts.

In the serial condition, LM Studio solved both constraint-counting repeats
but failed both string-transform repeats. Ollama showed the opposite pattern.
One LM Studio table repeat and one Ollama retrieval repeat truncated; their
other repeats were correct. All state-tracking and graph results were correct
in both scheduling conditions.

With two overlapping requests, one LM Studio string-transform response was
wrong and one truncated; its table repeats were correct/truncated. Ollama's
constraint repeats were wrong/truncated. These are observed API outcomes, not
proof of a particular numerical-nondeterminism cause or an engine defect.

Measured end-to-end request times, seconds:

| Stack | Scheduling | Minimum | Median | Maximum |
| --- | --- | ---: | ---: | ---: |
| LM Studio | Serial | 4.80 | 10.83 | 17.63 |
| LM Studio | Two overlapping | 5.95 | 16.61 | 40.57 |
| Ollama | Serial | 4.43 | 11.20 | 21.25 |
| Ollama | Two overlapping | 5.99 | 18.70 | 45.84 |

These are descriptive request timings including serving overhead and queuing,
not controlled throughput measurements or penalty thresholds.

## Reproduction Contract

- One Apple Silicon Mac, 128 GiB unified memory; shared with the public worker.
- LM Studio 0.4.4+1, runtime
  `llama.cpp-mac-arm64-apple-metal-advsimd@2.14.0`, loaded context 8192,
  one reported parallel slot.
- Ollama 0.33.2 imports the same local GGUF without re-quantization, context 8192.
- GGUF: community conversion of GPT-OSS-20B, native MXFP4 experts,
  12,109,565,632 bytes. SHA-256:
  `65d06d31a3977d553cb3af137b5c26b5f1e9297a6aaa29ae7caa98788cde53ab`.
  LM Studio's mapped file and Ollama's manifest model-blob reference matched
  this artifact. This is not an OpenAI-published GGUF or an independently
  established tensor-equivalence proof against upstream weights.
- Both use `/v1/chat/completions`, identical messages, temperature 0, top-p 1,
  seed 17, medium reasoning, 1536 output tokens, non-streaming. Server-side
  honoring of every requested parameter is not independently established.
- Fresh synthetic cases cover state transfers, table aggregation, directed
  reachability, constrained permutations, string transforms, and latest-record
  retrieval. An independent oracle reconstructed all six expected answers from
  prompt text before inference. Prompts and answer keys remain private.
- Freeze cases, metadata, settings, source hashes, schedule and stop rules
  before inference. Randomize within scheduling conditions; serial runs first.
- Preserve every raw response and terminal status with fsynced rows. Stop after
  three HTTP/transport/schema failures; never reinterpret those as wrong answers.
- An independent analysis script verified the complete 48-row schedule, no
  duplicate slots, unchanged source/case/metadata hashes, request settings and
  outcome classifications. All checks passed; no cases were discarded or tuned.

Private evidence SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Frozen manifest | `a5562355c664c9e6625ac7d9157085d2b8793c691ec35bf3dfe57a9692a2c034` |
| Runtime metadata | `6a9775327df5eb172fafb57cee8d142986942bd10de8f2cb6522d265c73fdd3e` |
| Cases | `c8bf7e48a99fe738ef5e9e69a0ae2ce449141936e6ddf647d99b95c8b2c2a76d` |
| Complete raw results | `02cd840e1c332ae6c5a1857692c23e51c433edc1e987ee5a7eb8834fccc0a0c9` |
| Independently audited summary | `1222bb08f93af78ac77a4b4260dcf1e1945e839fb01b3adea0a556525d89bfc6` |

## Confounders And Unfinished Gates

The shared LM Studio worker remained running. Before each LM Studio batch it
reported idle with no queued requests. One public worker arrival overlapped
both state-request measurements in the overlapping condition; these rows
were retained and marked. No other arrivals were observed by the bounded log
counter. This does not certify an otherwise idle machine or exclude work
already running on other processes.

Two overlapping clients do not prove GPU batching. LM Studio reported one
parallel slot. The two stacks are on the same machine, may share underlying
implementation components, and are not independent operator references.

Native tokenizer/template metadata was captured, but rendered prompts, hidden
reasoning contexts, cache state and numerical settings were not proven equal.
This experiment establishes a same-artifact API baseline, not isolated engine
causality, logprob alignment, a cross-quantization tolerance or fraud detection.

Next gates remain: exact conditional-context alignment, supported
quantization comparisons, fresh held-out substitution tests with false-positive
measurement, and adversarial bypass evaluation. Do not promote a scoring
threshold or grant economic authority from this run.

## Reference Timeout Investigation

The earlier 20B-versus-120B pilot stopped after three 120-second reference-path
timeouts. A bounded follow-up replayed those exact synthetic requests directly
from the owned chat VM to the same 120B service, without the Mac's TCP forward.
It made no service changes and used no production account credentials.

- Arithmetic control: correct, normal stop, 1.34 seconds.
- First historical constraint timeout: length stop, 1536 output tokens,
  32.05 seconds.
- Second historical constraint timeout: length stop, 1536 output tokens,
  32.11 seconds.
- Historical state-tracking timeout: correct, normal stop, 722 output tokens,
  15.14 seconds.

Running/waiting metrics were zero before and after every replay. Completion
counters nevertheless showed four additional successful requests during the
latter two intervals, so this was demonstrably a shared service, not an
isolated latency experiment. The original run did not collect equivalent
metrics. No timeout reproduced; the historical root cause remains unknown.
Do not mark it fixed or infer that the larger model answered both constraint
cases correctly. The current 120B weight revision remains independently
unverified.

Replay manifest SHA-256:
`986f0d258cec98928d8aa80a8cef29c193245a5cd67f650cdf339e4a24f02a15`.
Replay raw results SHA-256:
`b792ed4e88a51ed7b45faa32ce9315b331eff9dfd6b0295be37fcf7f4fe60911`.

The temporary Ollama model was unloaded afterward; its server remained running.
LM Studio and the public worker were left running. All test processes exited.

## Reference-Side Prompt Scoring Preflight

The owned 120B service's live OpenAPI schema exposes `prompt_logprobs` and
`echo` on `/v1/completions`. Two bounded synthetic requests then verified real
prompt-token scores, rather than inferring support from the schema alone.

Both requests supply the same raw arithmetic prefix and a different one-number
continuation, one correct and one incorrect. Settings: `echo=true`,
`prompt_logprobs=5`, `logprobs=5`, `add_special_tokens=false`, temperature 0,
seed 17 and one generated token. Each prompt contained 12 tokens. This is a
raw-completion capability test, not a Harmony/chat-template experiment.

An independent checker verified exact ASCII prompt reconstruction, all decoded
token offsets, equality of decoded token prefixes before the number, and
agreement between native prompt-token dictionaries and echoed token scores.
The first prompt token's unavailable score is retained as null. The generated
thirteenth token is excluded: its length stop is expected and does not indicate
that the supplied 12-token prompt was incompletely scored.

At the meaningful number position, the correct token received probability
0.87697 (logprob -0.13128), and the incorrect token received 0.003584
(logprob -5.63119). The latter was rank six and still had its actual-token score
returned alongside the top five. Request durations were 0.134 and 0.042 seconds,
excluding SSH setup. These two samples do not establish throughput or a
generally reliable correctness test.

This establishes a useful measurement primitive: a reference can score supplied
text without using candidate-reported probabilities. It does not establish
model identity, calibrated answer quality, cross-engine context equivalence or
substitution detection. The full raw prompt is controlled in this preflight;
mapping real chat answers and hidden reasoning into that context remains work.
The reference's weight revision is still unverified, and these were synthetic
supplied continuations, not captured smaller-model answers.

Private evidence SHA-256:

- Manifest:
  `cf225a4b1430128c2af6f23444cf359b572ec37f2c2894ca192e26a1e2a5c0ed`.
- Raw results:
  `9a74dfa26114c4c275748326cab3b579ea66ea11897b829a26d943c8ae2ef0f7`.
- Independently verified summary:
  `0abc398400b32bea8f012433ff75f78df53404bd15b94c00d1b83996a2ee161c`.

No public assignment API, validator policy, worker capability advertisement or
production setting changed. The next experiment must use pinned reference
artifacts and controlled context construction on real candidate continuations,
with honest baselines and held-out evaluation before drawing detection claims.

The subsequent [attention-quantization baseline](QUANTIZATION_BASELINE_2026_09_06.md)
adds a controlled 24-request comparison with per-tensor provenance. It verifies
that the original GGUF's attention is already Q8_0 while experts are MXFP4, and
records behavior after attention-only requantization. Neither result qualifies
a model-substitution detector or resolves the 120B provenance gate.

## Pinned Local 120B Token Calibration

A subsequent local run replaces the unverified remote reference with a
hash-checked publisher conversion for this experiment. It does not retroactively
verify the remote service's weights or explain the historical timeouts.

Reference provenance:

- [ggml-org/gpt-oss-120b-GGUF, pinned revision](https://huggingface.co/ggml-org/gpt-oss-120b-GGUF/tree/238abdd290bb874b90a5da1b4549881b7d05c091).
- `gpt-oss-120b-MXFP4.gguf`, 63,387,346,208 bytes, SHA-256
  `582bd40f6886200101f4c4ed9f25f3fe80cc14c86e9e2b37746cd8904a0c622d`.
- Publisher conversion metadata identifies primary OpenAI source revision
  `b5c939de8f754692c1647ca79fbf85e8c1e70f8a`. That revision was verified to
  exist; tensor equivalence to upstream safetensors was not independently proven.
- Static inspection found 116,829,156,672 parameter elements, 36 blocks,
  128 experts, and 687 tensors: 146 Q8_0, 433 F32, 108 MXFP4. This is neither
  a fully FP16 model nor an OpenAI-published GGUF. No draft model was loaded.
- Tokenizer metadata matched the original 20B conversion except for the chat
  template. The experiment bypasses both templates with explicit raw token-ID
  prompts, not chat messages or hidden reasoning.

The same pinned official llama.cpp b10826 engine, libraries and settings from
the raw-context quantization baseline ran the reference in a private loopback
process. Six reused contexts, two repeats each, temperature zero, seed 17,
one predicted token, native pre-sampling top 20. Every tokenization round-trip
and candidate/reference input token ID matched. Both reference repeats were
identical in all six contexts. The independent audit rehashed the model after
inference and checked the exact complete schedule, settings, native scores,
runner summary and process cleanup.

All twelve reference calls returned the probability of the token actually
emitted by the earlier 20B run. That reference-side score does not use the
candidate's reported probability. Comparing the two probabilities does use
the candidate's report and therefore still assumes honest reporting.

Two contexts are excluded from word-level interpretation: one emitted only
whitespace in both models; another emitted a word in the 20B but a formatting
token in the 120B. Both remain in the raw evidence. The four remaining contexts
chose the same word token in both models:

| Context family | 20B token probability | 120B probability of that token | Absolute model gap (percentage points) | 20B attention-quant gap (percentage points) |
| --- | ---: | ---: | ---: | ---: |
| Boolean | 0.99186 | 0.98095 | 1.09 | 4.44 |
| Translation | 0.93306 | 0.91773 | 1.53 | 4.42 |
| Attribute | 0.82990 | 0.85381 | 2.39 | 2.09 |
| Updated record | 0.80452 | 0.73350 | 7.10 | 8.21 |

On three of these four contexts, the model-size gap is smaller than the earlier
attention-only quantization gap. This contradicts an assumption that model
substitution must always produce a larger chosen-token probability change
than honest quantization. It does not estimate a detection rate or establish
that every quantization should be accepted.

### Unchanged Scorer Replay

An offline replay then applied the existing `text_fidelity.jensen_shannon`
function, without changing its constants, to these audited native top-20
captures. This calls the metric, not the public assignment/scoring workflow;
there is no Grid-issued challenge or independently operated reference cohort.

| Word-level context | 20B vs 120B metric | 20B vs attention variant metric |
| --- | ---: | ---: |
| Boolean | 0.003283 | 0.010039 |
| Translation | 0.011661 | 0.005175 |
| Attribute | 0.020748 | 0.003905 |
| Updated record | 0.028820 | 0.006703 |

**All four cross-model word-level observations fall inside the unchanged
0.12 match band.** The only context outside that band was the mixed
word/formatting position (0.125665), not evidence of a substantive wrong answer.
The metric pools unobserved tail mass; these are its bounded-input distances,
not measurements of full-distribution Jensen-Shannon divergence.

Do not fix this by fitting a tighter threshold to four reused contexts. The
next experiment needs complete candidate continuations, aligned reference-side
scoring, more varied honest configurations and a separate held-out evaluation.
This run establishes a pinned measurement path and a concrete limitation of
the current first-position comparison, not a qualified substitution detector.

Private artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Reference static audit | `585e63bee80ed7395c50b103dbf3741bfcd097e0004611983d215f811296c23e` |
| Frozen calibration manifest | `ffe02514d4f817e705f77b6abea8e434fc09f9fa966b94a5921c1c8cfd5df706` |
| Complete reference results | `4f3059f3b1892f17a579345b33f5d4d7465286b5e92824fae8f6f13d99ce7bb8` |
| Independently audited comparison | `3812b2eb9d86d146974e36e47b37da521f775d44a1a46366f2b4570441ead4d5` |
| Unchanged metric replay | `25347a083856cc41173328ccb453bb867b914cfaad3f715d0e0c64de5a0e8ef6` |

The private reference process exited cleanly. The public 20B worker was not
stopped or reconfigured. No public registration, policy or economic setting
changed. Six reused contexts remain six correlated calibration contexts, not
twelve independent samples or a held-out normal-chat benchmark.

The completed [native-context answer follow-up](ANSWER_FIDELITY_2026_09_06.md)
uses fresh paired calibration/evaluation inputs and scores actual complete
answers while preserving their full reasoning context. It records weak
substitution separation and explicit coverage limits; neither its tiny fitted
threshold nor this first-token baseline qualifies a production trust score.

## Decoded-Context Cross-Engine Follow-Up

A separate completed run on September 7 UTC narrows the prompt-construction
uncertainty for one new synthetic answer. It does not retroactively establish
context equality in the earlier LM Studio/Ollama experiment.

Three alternating pairs of LM Studio Responses and Chat streaming requests
used identical messages, temperature 0, top-p 1, seed 17, low reasoning and a
256-token output budget. An owned model-log reader retained only records
containing this experiment's synthetic marker, not other users' traffic.
All six logged rendered inputs were identical, including injected system text
and Harmony channel markers. All six logged outputs, reasoning and final
answers were identical. Every response ended normally.

| Endpoint | Completed requests | Native final-text probability positions per request | Missing final-text deltas per request |
| --- | ---: | ---: | ---: |
| Responses | 3 | 21 | 1 |
| Chat completions | 3 | 0 | Not applicable: no probability coverage |

The Responses coverage is partial, not a complete sequence likelihood. One
selected token per Responses run ranked below an alternative in the reported
distribution despite requested temperature zero. It repeated identically;
this is not evidence of random sampling, a dishonest worker or a specific
backend defect. Native versus effective sampling distributions, penalties and
other hidden settings remain possible confounders. The API request is not
proof of the effective sampler configuration.

### Same File, Second Engine

Standalone llama.cpp b10826 loaded the exact original 20B GGUF described above.
The capture and independent audit rehashed the file. An OS mapped-file check
also identified that artifact in LM Studio's running backend; the catalogue's
model alias and displayed size are not substitutes for loaded-file provenance.

Six available single-token alphabetic final-text positions were selected in
order before querying the second engine. Each native request included the
complete decoded LM Studio input, captured reasoning, channel markers and
preceding final text. Native tokenization/detokenization round-tripped that
prefix exactly. Each position was scored twice with native pre-sampling top 20,
temperature zero, seed 17, one output token and no repetition/frequency/presence
penalty. All twelve calls completed; every selected token was in the top 20.
Both native repeats agreed exactly. Each of the six selected LM Studio token
probabilities also agreed across its three Responses repeats.

| Selected position | LM Studio probability | Native probability of the same token bytes | Absolute gap (percentage points) |
| --- | ---: | ---: | ---: |
| 1 | 0.983095 | 0.983060 | 0.003433 |
| 2 | 0.959495 | 0.959875 | 0.038046 |
| 3 | 0.265655 | 0.247991 | 1.766401 |
| 4 | 0.822086 | 0.830539 | 0.845373 |
| 5 | 0.127839 | 0.131854 | 0.401497 |
| 6 | 0.993478 | 0.994579 | 0.110126 |

These are six correlated positions in one answer, not independent challenges,
full-distribution distances or a calibrated normal-variation bound. The maximum
observed gap is 1.766401 percentage points, not a proposed acceptance threshold.
No 120B substitution, supported-quant comparison or loaded-condition probability
experiment was conducted in this follow-up.

**Decoded context is not native token-ID equality.** LM Studio's input retokenizes
to 95 tokens, matching its reported prompt count. Its logged output retokenizes
to 68 while the reported prediction count is 69; an omitted terminal token is
compatible with this difference, but does not prove its cause or segmentation.
LM Studio does not expose the native input/output token-ID trace or effective
sampler settings in these captured logs. Numerical engine causality and exact
conditional-context equivalence therefore remain unproven. Do not use these
measurements to excuse arbitrary mismatches or punish workers.

The first native scoring runner failed on its own incorrect response-field
assumption after one inference response. That attempt is retained as failed,
not a backend error or part of the twelve-call result. A separately frozen
corrected runner saves raw responses before parsing and uses the actual
`top_logprobs`/`logprob` schema. The independent audit reproduced its saved
summary, verified source/model/binary/library hashes, token-byte and context
bindings, complete repeats, native settings and owned-process cleanup.

Private evidence SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Endpoint-control manifest | `688357ae42e7bc1d708181503482877f79a32450440cace452c92dbb591abd69` |
| Corrected cross-engine scoring manifest | `7f4faae6beb0830a23ad9b8e0eae2bfb7d64e1cf595c2ebffeac2623de3209e8` |
| Independently audited summary | `fbc52c9623d33a2a3414fae468842502abf2d93e27e9258a7fb0ad5ea5e627a7` |
| Independent auditor source | `99d565d668e06841ef7b82bc7d018995fa30e4f57c8f4b2e3c0dc919877472ae` |

The owned log readers and standalone model processes stopped. The existing
public worker was not reconfigured or restarted. No assignments, capabilities,
production policies, compensation or automatic penalties changed.
