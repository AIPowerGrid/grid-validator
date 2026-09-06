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
