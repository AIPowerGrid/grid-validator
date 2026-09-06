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

## Reference Provenance Gate

The owned 120B service reports vLLM 0.10.2 and supports the prompt-scoring
preflight recorded in the prior report. That remains API behavior, not verified
weights. Host SSH was rejected with both the configured identities and the
existing AIPG infrastructure key. Working host access has been requested to
inspect actual artifacts and runtime settings. Do not replace that gate with
the API's advertised model name or claim a verified 120B substitution result.
