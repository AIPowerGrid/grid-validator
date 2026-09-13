# Stop-Sequence Reasoning Diagnosis

## Finding

On September 13, two first-party Qwen3-27B assignments produced empty visible
answers with `finish_reason=stop`. Both had a 1,024-token output budget and
reported only 51/58 completion tokens. This was not budget exhaustion.

The released validator correctly delivered signed failed evidence under the
existing policy. That delivery result does not identify the cause or prove
model substitution. A direct comparison now points to stop matching inside
reasoning, before the model can emit its final answer.

## Bounded Comparison

Six sequential calls used the same configured owned backend and its native
model alias, the two retained assignment prompts, temperature zero and the
original 1,024-token budget. No new Grid assignments or paid jobs were created.
Each call had a 45-second request timeout. These are two paired cases, not six
independent trials or a fleet-wide estimate.

| Variant | Cases | Visible characters | Reasoning characters | Completion tokens |
| --- | --- | --- | --- | --- |
| Original stop, streamed | 2 | 0 / 0 | 183 / 183 | 54 / 58 |
| Stop removed, streamed | 2 | 43 / 43 | 300 / 437 | 119 / 145 |
| Original stop, non-streamed | 2 | 0 / 0 | 169 / 183 | 51 / 58 |

All six returned HTTP 200 and finish stop. With stop removed, both outputs
contained the stop string inside reasoning and again inside the final answer.
After the released scorer's existing quote normalization, both visible prefixes
before the marker matched the original expected-answer hash. With stop present,
neither produced visible text; reasoning ended without including the stop string.

This paired behavior strongly supports termination when the model mentions the
marker in reasoning. Server-internal token traces were not captured, so do not
present the exact decoder path as independently witnessed. The non-streaming
control argues against a streaming-only transport defect. Removing stop was a
diagnostic control, not a proposed stop-compliance test or production fix.

The private response capture has SHA-256
`08c8b9bc0d9de33e315bfc40d074e0914fac8d8a58ed87bbab252b247603f1bf`.
An independent offline parser checked all six captured replies, marker presence,
and the two normalized prefix hashes. Raw prompts, markers, credentials and
responses remain private. Deployed worker source was `beeacbfaaa8e3116e3a16433aafbb17489b2d478`;
its configured default reasoning effort was unset.

## Correcting The Evidence Description

Core `d606e4d8` forwards worker reasoning through the internal probe collector,
but its public stored `reasoning_text` is populated only for token-limit v1/v2.
Stop-sequence evidence therefore contains null reasoning even when the backend
generated it. Reports `127713`/`127714` prove **completed empty visible evidence
was signed and delivered**, not that the backend generated zero reasoning.

This distinction also applies to the historical 114 completed-empty records:
absence of retained reasoning in a non-token-limit result cannot prove absence
of backend reasoning. Their old expired assignments remain closed. The .20
delivery fix and its live canary remain valid; the stronger backend-empty
interpretation is withdrawn. No historical scores or attestations were edited.

## Non-Reasoning Control

A second bounded experiment made four more direct calls using the same two
captured prompts and 1,024-token budgets. It used vLLM's documented
[`chat_template_kwargs.enable_thinking=false`](https://docs.vllm.ai/en/latest/features/reasoning_outputs/)
request control, with and without the original stop string. No server settings
were changed. HTTP success alone was not the acceptance criterion:

| Variant | Cases | Visible characters | Reasoning characters | Completion tokens |
| --- | --- | --- | --- | --- |
| Thinking disabled, stop present | 2 | 12 / 12 | 0 / 0 | 22 / 25 |
| Thinking disabled, stop removed | 2 | 41 / 41 | 0 / 0 | 32 / 33 |

All four returned HTTP 200 and finish stop. With stop present, both complete
visible answers matched the original expected hashes. Without stop, both
contained the marker and suffix, and only the prefix matched. Thus these two
cases demonstrate correct stopping on this backend in non-reasoning mode;
the model did not merely decide to omit the marker in every response.

Private capture SHA-256:
`d27a0edf9ac7b5d763317bc818951d416e485bdc648ba0e0cbe308b027c2b105`.
Together the experiments contain ten actual calls over two reused prompts,
not ten independent tests. The same-case controls narrow the cause but do not
qualify other engines, undisclosed model weights or a production-wide flag.
Do not send this provider-specific option blindly to the whole fleet. A worker
or backend may ignore it or reject it; either requires explicit handling.

## Next Implementation

1. Make reasoning presence and termination evidence explicit and bound to a
   versioned response commitment. Do not append uncommitted metadata and let it
   influence scoring. Preserve compatibility with existing signed evidence.
2. Qualify stop compliance separately from reasoning behavior. The owned Qwen
   control above passes; extend it to supported backend/mode combinations and
   retain the reasoning-enabled control. Unsupported controls must remain unavailable;
   never pretend that a backend honored a flag just because it returned 200.
3. If reasoning remains enabled, use a versioned paired policy that can report
   an inconclusive reasoning/stop interaction instead of equating an empty final
   answer with failed model fidelity. Neither longer budgets nor dropping stop
   from the actual test establishes stop compliance.
4. Before rollout, reproduce on owned backends and test ignored stop, malformed
   final output, missing reasoning metadata, transport failure, and both old/new
   commitment verification. Include at least one honest non-reasoning control.

These are implementation requirements, not shipped fixes. Existing results
remain preview evidence without payout, routing, strike or slashing authority.
Validator compensation is a separately approved participation pilot, not a
reward for healthy verdicts or a penalty for reporting this failure.
