# First Real Text Fidelity Experiment

Status: **diagnostic evidence, not rollout qualification**. The September 5
experiment found both a separable backend pair and successful evasions. No
quality, routing, reward, strike or slashing authority was enabled.

## Method

The maintainer identified the owned worker bridge on the chat frontend VM.
Inference runs on separate configured backends. We used the current Core
`make_challenge` generator and validator `score_witnesses` implementation,
without changing their thresholds or registering a falsely labelled worker.

- Generate 100 fresh challenges with the public generator, temperature 0,
  top-p 1, 20 top logprobs, 32 output tokens, medium reasoning, and the same
  generated seed on each repeat.
- Request three sequential streaming generations per prompt from the configured
  GPT-OSS-120B/vLLM backend. Randomize their candidate/reference order.
- Request the same saved prompts from the configured Qwen backend (`q27fp8`,
  advertised by this operator as Qwen3-27B), using the worker's HTTPX transport.
- Score against the earlier GPT-OSS repeats. These are **one-server repeated
  references**, not independently controlled reference operators.
- Replace the captured Qwen distribution with the captured GPT-OSS distribution
  and rescore while retaining the Qwen output hash: a captured-evidence forgery
  replay, not a live malicious Grid worker.
- Run an isolated live routing harness that recognizes the public prompt prefix,
  routes 100 probes to GPT-OSS, and routes ten interleaved ordinary arithmetic
  requests to Qwen. Ordinary controls use a 256-token budget to permit visible
  answers. The router does not receive a hidden assignment-role flag.

Backend names are configuration and API claims. Model file hashes, exact weight
revisions, quantizations, tokenizer revisions and engine build versions were not
independently verified. This experiment cannot establish parameter counts or
same-model cross-quantization tolerance.

## Results

| Measurement | Observed result |
|---|---|
| Same-backend baseline | 300 successful requests over 100 fresh prompts |
| Missing native logprobs / HTTP errors | 0 / 0 in the baseline and 100-request Qwen run |
| Baseline candidate verdicts | 100 healthy, 0 failed, 0 inconclusive |
| Straight Qwen substitution verdicts | 100 failed, 0 healthy, 0 inconclusive |
| Qwen output with copied GPT-OSS logprobs | 100 healthy |
| Live probe-aware routing | 100 recognized probes, 100 healthy |
| Ordinary controls in live routing test | 10 routed to Qwen; all 10 returned visible answers |
| Live routing HTTP errors | 0 |

Baseline candidate Jensen-Shannon distance (nats): minimum `1.10e-12`, median
`1.70e-10`, maximum `1.36e-9`. Qwen candidate distances ranged from
`0.6931471791` to `0.6931471806`, essentially the metric's maximum.
Median candidate request latency was 732 ms for GPT-OSS and 486 ms for Qwen;
these are measurements under this load, not performance guarantees.

All 400 baseline/substitution responses exhausted the 32-token budget with
reasoning and no visible answer. More importantly, the highest-probability
first token was `<|message|>` for all 100 GPT-OSS candidates and `The` for all
100 Qwen candidates. The separation may largely identify backend response
formatting rather than semantic capability or exact weights. Do not advertise
the 100/100 result as a general model-substitution detection rate.

Zero observed false failures in this one configuration does not establish the
false-positive rate across engines, quantizations, model families or workload
types. Repeated samples from one backend do not qualify an independent quorum.

## Bridge Upgrade

The running bridge had local vision and cancellation changes. Source comparison
confirmed those changes are included in the published v0.3.8 source,
`afbb37595b61fa92a3b5bbd4dbba7320d31e008d`, matching the release manifest.

The upgrade uses a separate source release and virtual environment, installed
from the tag's hash-locked dependencies. The old checkout and environment remain
intact for rollback. The existing working directory, configuration and signer
are retained; before/after digest checks confirmed no changes to the config,
signer or original service unit. Only an additive systemd executable override
selects the reviewed release. It does not launch a new dashboard or restart chat.

VM verification: 95 tests passed, one skipped. All three configured workers
registered with Core after restart, and a DeepSeek completion was subsequently
recorded. A separate real-GPT-OSS bridge test exercised the released handler with
an in-memory Grid-side receiver: 29 native-logprob token frames, one completion,
zero errors. That proves backend-to-bridge relay, **not** a complete live
Core-to-validator fidelity assignment. The public chat login returned HTTP 200;
this is availability evidence, not an authenticated chat conversation test.

## Evidence And Failed Attempts

Raw generated prompts, streaming responses, configuration digests, timestamps
and experiment scripts are retained privately by the maintainer. No API keys,
operator mappings or private endpoints belong in this public report.

SHA-256 of the private JSONL records:

- Baseline: `710928c295c8204220c2bd3139b662da8792dc4848e3a9336ba13a911ee506cf`
- Substitution: `2a7ba67ac36dcdf84fa99791fe0c1048e93ddc3463f60865c87df9721005e505`
- Live probe switching: `5d2563d1f7da44ea23636581da9fca186f8d868de72a05e7bc4e41b8041d40fa`

Source hashes for the unmodified generator and scorer:

- Core: `24d942bdf98a732c17d97b49da6260f5b2ca5dd6b3cea214a8a3c0f3874940b3`
- Validator: `4cf3ed5266502ac0dcd1cf011347f173d528f3cf84c75e4624ba3d419570e470`

These hashes bind the retained records; they are not independent verification
of the experiment or model identity. Initial urllib requests to Qwen returned
HTTP 403; the worker's HTTPX request path succeeded. The first routing harness
attempt failed locally on an empty Bearer header before inference. The corrected
run omitted that header for the unauthenticated owned backend. Neither failed
preflight is included in the successful run's denominator.

## Rollout Decision

Keep text fidelity issuance and all economic/penalty effects off. Continue the
existing non-economic validator protocol and operator qualification separately.

Before considering a bounded fidelity canary:

1. Establish comparable content positions rather than assuming the first native
   logprob position represents visible semantic output. Calibrate a versioned
   policy against actual tokenizer/chat-template behavior.
2. Test the same model family across verified revisions, engines and quants,
   then substitute a smaller model in that same family. Keep a held-out batch;
   do not tune thresholds against only this observed pair.
3. Treat reported probabilities as forgeable. Hidden/private samples alone do
   not remove probe recognition or copied-distribution risk. Measure attacks
   against the full proposed dispatch and evidence path before claiming they
   are addressed.
4. Prove full Core/worker/validator fidelity delivery and zero economic effects
   with qualified references before expanding beyond isolated calibration.

Compensation may pay separately reviewed pilot contributions under a published
cap. It must not certify this detector, buy penalty authority, or turn a healthy
verdict into an automatically payable claim. Core PR115 is an offline allocation
simulation only; durable payment guards and explicit funding approval remain.
