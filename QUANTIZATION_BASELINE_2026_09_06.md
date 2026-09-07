# Attention Quantization Baseline

Private exploratory qualification, 2026-09-06. No production model replacement,
public worker registration, policy change, payout or penalty side effects.

## Artifact Provenance

The source GGUF from the [same-artifact baseline](HONEST_BASELINE_2026_09_06.md)
contains 459 tensors: 98 Q8_0, 289 F32 and 72 MXFP4. Its 96 attention projection
weights are already Q8_0. The filename's MXFP4 label refers to its expert
weights; it is not a full per-tensor precision specification.

A private copy changes exactly those 96 attention projection tensors from
Q8_0 to Q4_0. The following were verified from parsed GGUF data:

- All 459 tensor names and shapes remain equal.
- Exactly the selected 96 attention weights change type and data hash.
- All 363 other tensors remain byte-identical, including every MXFP4 expert.
- All parsed model metadata, including tokenizer and chat template, is equal.
- Source size: 12,109,565,632 bytes; variant: 11,791,060,672 bytes.

This is additional Q8-to-Q4 requantization, not a fresh conversion from original
floating-point weights and not a suggested production model. The smaller file
saves only about 304 MiB: the large expert tensors are unchanged. Runtime
support and test results do not establish acceptable network quality.

The conversion used the official
[llama.cpp b10826 release](https://github.com/ggml-org/llama.cpp/releases/tag/b10826),
source commit `73a43d1f69345aee8bb186ef4b3172cef892f2e5`. Its macOS ARM64 archive
was checked against GitHub's asset SHA-256 before execution. No platform-signing
claim is made. GGUF inspection used `gguf==0.19.0` in an isolated local venv.

Both artifacts load into Ollama 0.33.2. A small arithmetic preflight on the
variant returned the correct integer with a normal stop. Ollama's details
report **the same `MXFP4_MOE` label and parameter size for both artifacts**.
An API-level quantization label is therefore insufficient even to describe
this controlled change, let alone prove weights used for a remote job.

## Frozen Comparison

The test schedules 24 serial requests: six previously frozen cases, two
repeats per artifact, shuffled before inference. No case is removed or tuned
after observing the new variant. This reuses calibration cases; it is not a
fresh held-out model-substitution evaluation.

Both variants use the same Ollama server, identical templates and parameter
strings, 8192 context and identical messages. Requests specify temperature 0,
top-p 1, seed 17, medium reasoning and 1536 output tokens. Runtime source hashes,
metadata, case hashes, artifact audit and schedule are frozen in the manifest.
Expected answers were independently reconstructed from all six prompts again
before inference.

Wrong final answers, output-budget exhaustion and infrastructure errors are
separate outcomes. Three infrastructure errors stop the run; raw partial
results are retained. The machine remains shared with the public LM Studio
worker; bounded log-arrival counters record visible public-worker overlap.
This is not certified idle hardware or a throughput benchmark.

## Measured Results

All 24 requests completed. An independent analysis verified source/input hashes,
the full schedule without duplicate or missing slots, unchanged settings and
every outcome classification. No HTTP, transport or schema failures occurred.
Post-run API metadata matched the frozen snapshots. Local Ollama manifests
resolved to the expected model blobs, and both blobs were independently hashed
again to confirm those bindings, not merely their declared digest strings.

| Artifact | Correct | Wrong final JSON | Budget exhausted |
| --- | ---: | ---: | ---: |
| Original Q8 attention | 9 | 2 | 1 |
| Experimental Q4 attention | 4 | 2 | 6 |

There are six distinct cases, not 24 independent samples. Per-case outcomes
over two repeats:

| Capability | Original Q8 | Experimental Q4 |
| --- | --- | --- |
| State tracking | Both correct | Both budget-exhausted |
| Table aggregation | Both correct | Both wrong |
| Graph reachability | Both correct | Both correct |
| Constraint counting | Both wrong | Both correct |
| String transformation | Both correct | Both budget-exhausted |
| Latest-record retrieval | One correct, one budget-exhausted | Both budget-exhausted |

Every budget-exhausted response reported a length stop at exactly 1536 output
tokens. This measures usefulness under that budget, not proof the task could
never be solved. No longer-budget rerun was mixed into these results.

Observed request times were 4.89-23.60 seconds (median 12.23) for original Q8
and 6.00-22.84 seconds (median 15.93) for attention Q4. No public-worker arrival
was detected during these requests; that counter does not prove exclusive
machine use. Timings include load/cache/serving effects.

The attention change coincided with substantially more budget exhaustion on
this small test set. It was not uniformly worse: Q4 solved the constraint case
that Q8 failed. Neither a single reference mismatch nor this aggregate result
establishes worker dishonesty or model substitution. Quantization affects the
behavior we need to calibrate, and cannot be reduced to a coarse model label.

The original Q8 outcomes also reproduce its earlier serial baseline counts,
including the inconsistent retrieval repeats. That is repeated evidence of
API-level variability under requested temperature zero, not a proven diagnosis
of the serving engine's numerical behavior.

## Evidence Hashes

| Artifact | SHA-256 |
| --- | --- |
| Original GGUF | `65d06d31a3977d553cb3af137b5c26b5f1e9297a6aaa29ae7caa98788cde53ab` |
| Attention-Q4 GGUF | `3c1d0dc9951f2b061899466bf083583ace6b736e1c2bdb6f5f619b706e597c8b` |
| Quantizer archive | `15c1b2f460331d9a20709ebde21240d7e60fdb5cf15e1f8db0309af3a5bbc6d2` |
| Conversion manifest | `aee5accb5beff29538df85eb49422ea4ad9ac865c8a7c0663a043604c5bd8709` |
| Per-tensor artifact audit | `a45de2f0b9f0929353356ba04c01e431be073c84fa7fbe72d4f32ab00e53d775` |
| Benchmark manifest | `1c5086754075022800977699a927c68858ca96aae9adca037a64782217a7a0c5` |
| Complete benchmark responses | `a6850c61189f9f8aba6d784ad553584e84c7a5fd8b2640a345f28f315d7eefba` |
| Independently audited summary | `52e7ced2a841fcc2877d229ef519bb15dd8a6305fd2790ee522279f32b60e9d1` |
| Post-run runtime/artifact bindings | `435b9895fa29e015c94b1456bd114c250372521c009b49d7ebea69478e882e70` |

Prompts, raw replies, local paths and the synthetic variant stay in private
operator storage. No credentials were used for local inference.

After the run, only the two private Ollama models were unloaded; its model-list
endpoint confirmed no loaded models. The Ollama daemon, LM Studio and public
worker were left running. No raw benchmark prompts or variant artifacts were
published to operators.

## Exact Raw-Context Probability Follow-Up

A separate frozen 24-request run compares the same two files through the
official llama.cpp b10826 server on the same Mac. This removes the previous
experiment's uncertainty about rendered conversational contexts, but does not
test ordinary chat behavior or different serving engines.

Six short raw few-shot contexts, two repeats per file, and all settings were
frozen before inference. Each model ran in its own temporary loopback process,
with one slot, 2048 context, four CPU threads, Metal offload, flash attention
enabled, and f16 KV caches. The runner and independent audit hashed both model
files, the server binary and real dynamic libraries. Saved process commands
and `/props` agree on the model paths and build identity.

Each input was tokenized without automatic special tokens and detokenized
back to its original text. Both files returned exactly the same token IDs and
pieces. `/completion` received those explicit token arrays, with no chat
template, generated reasoning history, grammar, logit bias or LoRA. It requested
one token, temperature zero, seed 17, only the temperature sampler, no repetition
penalty, and native pre-sampling top-20 logprobs. Prompt caching was disabled
in both launch flags and requests. The backend's `tokens_cached` response is
retained but is not used as proof of how many tokens were reused.

The API contract is pinned to
[llama.cpp's source revision](https://github.com/ggml-org/llama.cpp/blob/73a43d1f69345aee8bb186ef4b3172cef892f2e5/tools/server/README.md).
The saved responses confirm the requested sampler and pre-sampling settings;
probabilities are not reconstructed from chosen text or replaced with a
temperature-zero one-hot distribution.

All 24 requests returned one native probability position without context
truncation. Their intentional one-token `limit` stop is an observation boundary,
not failure to finish a user task. The independent audit verified token IDs,
decoded bytes, complete prompt echoes, evaluated-token counts, settings,
finite logprobs, unique top-20 IDs, sorted probabilities and retained probability
mass. It checked every schedule slot and rehashed the runtime/artifacts.

| Raw context family | Original chosen-token probability | Q4 chosen-token probability | Common top-20 IDs |
| --- | ---: | ---: | ---: |
| Antonym completion | 66.45% | 49.94% | 19 |
| Attribute completion | 82.99% | 80.90% | 19 |
| Boolean completion | 99.19% | 94.75% | 17 |
| Translation completion | 93.31% | 88.89% | 16 |
| Updated-record completion | 80.45% | 72.24% | 19 |
| Arithmetic prefix, whitespace only | 99.65% | 99.60% | 18 |

All six emitted token IDs agree across the two files, and all 12 within-file
repeat pairs have identical native top-20 observations. Five contexts produce
ordinary word tokens; the arithmetic context produces only a space. All four
arithmetic observations are retained and excluded from semantic interpretation.
No after-the-fact extra generation was mixed into the frozen run.

For the five word-producing contexts, chosen-token probability changes range
from 2.09 to 16.51 percentage points despite matching token choices. Only 16-19
top-20 alternatives are shared. Missing alternatives have unknown probabilities,
not zero; this report does not calculate full-distribution KL/JSD by filling
missing entries or renormalizing a truncated vocabulary.

This is useful same-engine quantization calibration, not a safe tolerance or
proof of dishonesty. The private Q4 stress artifact is not an approved network
quant, five lexical positions are not population accuracy, and exact repeat
agreement on this run does not prove determinism across hosts, engines, load,
or longer contexts. No 120B model or candidate-answer likelihood detector was
tested here. Request times (median 0.080 seconds) concern short one-token raw
requests only, not chat throughput.

Private evidence directory: `text-worker-20b/raw-context-quant-20260906/`.
`audit_raw_context_quant.py` checks stored native evidence without calling the
backend. Its unit tests accept the original observation and reject eight
controlled mutations, including missing/empty/oversized probability lists,
nonfinite or positive logprobs, changed context/token IDs and post-sampling
substitution. Rejected observations are not assigned fraud authority.

| Artifact | SHA-256 |
| --- | --- |
| Frozen raw-context manifest | `a3f2809617bac961c73f97fc5271edd27c77ef0042c7fa5d8bf008f14cacfd79` |
| All raw-context responses | `561e99265f208941a1c0fb4f73150062ffc1c02139d0529bfa75cf686e21e3a6` |
| Independent raw-context audit | `87d2b58e2610c75aea4703c7c999915a75867ee591cb8dd1915f4b976bac5a81` |

Both temporary server processes exited cleanly and their PIDs were absent at
post-run inspection. The existing LM Studio model remained loaded and idle,
and the public worker process remained running. No production services or
Grid authority settings were modified.

## Reference Provenance Gate

The owned 120B service reports vLLM 0.10.2 and supports the prompt-scoring
preflight recorded in the prior report. That remains API behavior, not verified
weights. Host SSH was rejected with both the configured identities and the
existing AIPG infrastructure key. Working host access has been requested to
inspect actual artifacts and runtime settings. Do not replace that gate with
the API's advertised model name or claim a verified 120B substitution result.

## Published Quantization Follow-Up (2026-09-07 UTC)

This follow-up uses published artifacts, not the hand-made attention stress
variant above. Both files come from `unsloth/gpt-oss-20b-GGUF`, pinned to revision
`d449b42d93e1c2c7bda5312f5c25c8fb91dfa9b4`. Public metadata was checked before
download, and full-file SHA-256 matched the publisher's LFS checksums:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `gpt-oss-20b-Q8_0.gguf` | 12109567168 | `bcd455d4034ec02f71a875b46cb17df44a97911d7258291973be4d21f98329f3` |
| `gpt-oss-20b-Q4_K_M.gguf` | 11624759488 | `c27536640e410032865dc68781d80a08b98f8db5e93575919af8ccc0568aeb4f` |

The tensor audit found 459 tensors in each artifact. The published Q8 file has
98 Q8_0, 289 F32 and 72 MXFP4 tensors. Its Q4 counterpart has 13 Q8_0, 61 Q5_0,
24 Q4_K, 289 F32 and 72 MXFP4 tensors. Exactly 85 tensor payloads change:
84 attention tensors and the token embedding. All shapes, the 72 expert
payloads and tokenizer/chat-template metadata match between this publisher's
pair; only `general.file_type` changes in metadata. This is not full-model
four-bit versus eight-bit precision, nor a Grid-certified quantization tier.

Compared with the original LM Studio-community artifact, the published Q8
file has 387 byte-identical tensors and 72 differing packed MXFP4 expert
payloads, with unchanged tensor types and shapes. Chat-template and padding
token metadata also differ. Packed-byte differences alone do not establish
different numerical weights. Neither conversion's publisher checksum proves
correspondence with an independently verified upstream OpenAI tensor snapshot.

A follow-up decoded all 72 differing expert tensors in bounded chunks with
the installed GGUF MXFP4 decoder: 19,110,297,600 values compared, zero numerical
differences and zero nonfinite values. All 72 decoded tensor digests match.
Together with the other 387 byte-identical tensors, this establishes numerical
tensor equivalence under that decoder despite different file/payload hashes.
It does not remove the chat-template/padding metadata differences or prove
upstream OpenAI provenance. File-hash inequality alone is not a substitution
verdict. The decoder source digest is
`db403c3b2292d3f2c5cfef4109d4b5745f437b5599c7afc94d4b97feca7e9247`.

### Frozen Native Comparison

Before inference, the private runner froze 24 fresh contexts, comprising 12
changed-answer pairs across lookup, ordered updates and minimum selection.
A separately implemented oracle checked every expected answer and pair;
an additional generator check covered 4,800 cases and 2,400 pairs. These are
predictable capability templates, not unrecognizable anti-cheat probes.

Each of the three artifacts received the same 48-slot shuffled schedule
(24 contexts, two repeats) on the pinned standalone llama.cpp b10826 runtime.
All models received identical explicit token-ID contexts, verified by native
tokenization, detokenization and all 144 actual prompt echoes. This avoids
chat-template differences for this raw-completion experiment; it does not
establish equivalent conversational behavior under the files' own templates.
Settings used greedy temperature zero, seed 17, one intentional output token,
pre-sampling top-20 logprobs, F16 KV cache and no prompt caching or penalties.

| Artifact | Correct first-word calls / 48 | Unique contexts with identical repeat distributions / 24 | Pairs with both variants correct, first repeat / 12 |
| --- | ---: | ---: | ---: |
| Original LM Studio-community MXFP4 | 30 | 24 | 5 |
| Published Q8 | 30 | 24 | 5 |
| Published Q4 | 32 | 24 | 5 |

All 144 requests returned valid native witnesses. Every preregistered expected
color encoded as one token and appeared in the native top 20; no absent
alternative was filled with zero. The independent verifier checked the full
schedule, request parameters, native settings, token IDs/bytes, finite sorted
probabilities, context sizes, artifact hashes and owned-process cleanup.

Original versus published Q8 yielded identical full top-20 observations on
all 24 unique contexts. Published Q8 versus Q4 chose the same token on 18/24
contexts. Their expected-color probability gaps ranged from 1.605316 to
48.526740 percentage points (median 17.769532), using first repeats only.
These are chosen-context probability differences, not full-distribution
distances or population false-positive rates.

One-token limits intentionally prevent reasoning and complete chat answers.
The correctness counts above must not be presented as a model ranking or
normal chat capability. Runs were serialized on a shared Mac, not verified
exclusive-idle or loaded hardware. No 120B reference, new detection threshold,
production registration, authority, compensation or penalties were involved.
All three owned server processes exited and their PIDs were absent afterward;
the existing LM Studio backend and public worker were not reconfigured.

The practical consequence is to calibrate genuine within-family variations
before assigning outlier meaning. A tight absolute probability threshold can
reject a published quantization even at an identical semantic context.
This run does not determine how tolerant a useful substitution detector can
be while still catching adversaries. Full-answer cross-quantization and
held-out substitution/false-flag studies remain required.

Private evidence is under `text-worker-20b/published-quants-20260907/` and
`text-worker-20b/published-quant-baseline-20260907/`. Raw prompts stay private.

| Artifact | SHA-256 |
| --- | --- |
| Tensor and metadata audit | `bcbc5871390724f0c1e2d95cc32cecf6f97285424277573275761925ef5f4f23` |
| Cross-publisher expert-value audit | `0673b6e31bf02c6b87f0a5e5e6ddc9a8f2fb82ec76923bbc2bb44a144295a7b6` |
| Frozen native manifest | `b8a310492de085ba9b018455b9b215a140cf493c89f4646b77d6cd85f971578c` |
| All 144 native responses | `cdf6e6fa49e99ecc2e8691e7ba8bd04481925f219c53719c4a9aa1bbdfdfbbda` |
| Independent summary | `3e4a5369a215a0c6591c8d8f0e93890885c27482774420b2a5c2605da9e089b9` |

## Full Answers And Observed Load (2026-09-07 UTC)

The next private study uses the same published Q8/Q4 pair, with 32 fresh
full-answer cases: eight each for exact extraction, ordered state updates,
binary constraints and retrieval with superseding records. Sixteen pairs
change one input and require a changed answer. Calibration/evaluation inputs
are disjoint, but this is capability calibration, not a fitted detector or a
fresh held-out detection result. The task templates remain predictable.

Before any generation, a preflight rejected the original retrieval contexts
because they contained 2,830 native tokens, below the frozen 3,000-token minimum.
Its generation file is empty and its owned server exited. A read-only context
preflight measured all lengths; the corrected study appended 140 non-target
distractor records without changing expected answers, short cases, generation
settings or schedule. The eight revised retrieval contexts are exactly 4,930
native tokens. The original attempt remains preserved, not overwritten.

An independent oracle verified all 32 expected answers and 16 changed-answer
pairs. A separate 100-seed generator exercise verified 3,104 cases across 97
valid seeds; three other seeds were rejected before inference for duplicate
prompts. They were not substituted based on model performance. The actual
frozen study has no duplicate prompts or discarded generated outcomes.

Each model received two repeats under each of two conditions, for 128 calls
per model and 256 total. Both independently rendered identical chat prompts
and tokenized/detokenized them to identical IDs. The pinned llama.cpp b10826
server used two 8,192-token slots, F16 KV cache, greedy temperature zero,
seed 17, pre-sampling top-20 probabilities, no prompt caching and a fixed
1,536-token output budget including reasoning. No selective budget increase,
retry or truncation-based prompt replacement was performed.

The serial condition sends one owned request at a time. The overlap condition
starts the two variants of a pair together. Slot telemetry, bounded by the
actual overlapping request intervals, verified two processing slots for
every one of the 64 overlap batches across both models. All 128 serial batches
had observed single-slot processing without a competing owned request.
This is measured modest backend load on a shared Mac, not globally idle
hardware, simultaneous GPU-kernel proof or a production fleet load test.

### Outcomes

| Artifact / condition | Correct complete / 64 | Output-budget exhaustion / 64 | Median request seconds | Maximum seconds |
| --- | ---: | ---: | ---: | ---: |
| Q8 serial | 54 | 10 | 7.36 | 40.22 |
| Q8 overlap | 54 | 10 | 12.78 | 50.21 |
| Q4 serial | 54 | 10 | 7.12 | 30.30 |
| Q4 overlap | 53 | 11 | 11.96 | 57.11 |

All 256 native witnesses passed the independent context, token, probability,
settings and schedule audit. There were 215 correct completed answers and
41 output-budget exhaustions, with zero wrong completed answers, invalid
JSON outputs, context truncations or infrastructure errors. A supplemental
canonical-JSON guard found no bool/integer or float/integer equality ambiguity
in the reported classifications. The guard's controlled checks reject such
coercions while accepting reordered object keys.

| Family | Q8 serial correct / 16 | Q8 overlap correct / 16 | Q4 serial correct / 16 | Q4 overlap correct / 16 |
| --- | ---: | ---: | ---: | ---: |
| Extraction | 16 | 16 | 16 | 16 |
| State updates | 16 | 16 | 16 | 16 |
| Constraints | 8 | 8 | 6 | 6 |
| Updated-record retrieval | 14 | 14 | 16 | 15 |

Every non-completion in this table exhausted the fixed output budget. The
results are not proof that a task is unsolvable, nor permission to label an
honest worker fraudulent. Q4 was not uniformly worse: the family results
differ, and a single overall ranking would hide that distinction. Eight
distinct inputs per family, their paired variants and repeats do not support
population accuracy or independent-sample confidence claims.

### Repeatability And Paired Changes

Within the serial condition, both artifacts repeated all 32 token sequences
exactly. Under overlap, each repeated only 29/32 sequences exactly. Matching
repeat indices across serial/overlap gave 48/64 identical sequences for Q8
and 59/64 for Q4. These counts include reasoning and budget-limited outputs,
not just final answers. Temperature zero therefore did not guarantee identical
full output under these observed conditions.

All 54 Q8 comparisons that completed correctly in both conditions preserved
their final answer; the remaining ten exhausted the budget in both. For Q4,
53 preserved correct final answers, ten exhausted the budget in both, and one
retrieval call changed from correct completion to budget exhaustion under
overlap. The shared host and schedule do not isolate an exclusive causal
effect of load, but this is an observed honest-worker difference to retain.

Of 32 paired trials per artifact/condition (16 pairs, two repeats), both
variants were correct and changed as required in 24 Q8 serial, 24 Q8 overlap,
26 Q4 serial and 25 Q4 overlap trials. Every remaining pair had at least one
budget exhaustion, not a wrong completed answer. Pair completion and single
request completion are different denominators; do not interchange them.

The full-answer summary reproduced byte-for-byte. The paired supplement's
first replay exposed unstable dictionary-key ordering in its JSON serializer,
not different results. A separate canonical re-verifier recomputed every
paired/cross-load count and matched the original report without changing any
inference record or the original report. The failed preflight,
context-inspection and two generation servers exited, and all four owned PIDs
were absent afterward. The public LM Studio backend and worker stayed running;
no production service, registration, authority, credit or payout setting changed.

This advances honest full-answer/load calibration and capability reporting.
It does not test another engine under the same load matrix, establish a model
substitution threshold, refresh the production fleet, or authorize penalties.
Fresh reference-scored substitution and honest false-flag evaluation remain
required before any fidelity method can gain authority.

Private evidence: `text-worker-20b/quant-answer-study-20260907-v2/`, with the
original failed preflight and separate context inspection retained alongside.
Raw synthetic prompts and outputs remain private.

| Artifact | SHA-256 |
| --- | --- |
| Corrected frozen manifest | `4e4a133232171d8ff0034120a70b0cdf1e7e41b1dd8fbda3e7ce447d8dda5839` |
| All 256 generation records | `f9bdf919f20d968076274566eebdfbd19e65edd41fd6b601c2dbfdf87066f995` |
| Native slot telemetry | `b6b1fa87e82ddb23dafddbea91a08c7239f94707f948f9415553e809235661b7` |
| Independent full-answer summary | `4e19942c646ce9f07f559756e5353835e645568a0c1ebe34c402457980eed02e` |
| Paired/cross-load analysis | `ed7dc27bb67e820803c692a61d24f6c6b8f0925e6783f0fac0a92638d6044f94` |
| Canonical paired re-verification | `9ef2b4fc0feb4d5a5818f0799338661d01fc7b797c731b68c08b76a557f558bb` |
