# Native Responses Qualification

Unreleased local work, 2026-09-06. No capability advertisement, assignment-loop
change, production deployment or quality/economic authority.

## What Was Measured

Two fresh synthetic localhost requests traversed:

```text
LM Studio streaming /v1/responses
  -> unchanged released text worker v0.3.8
  -> real loopback WebSocket
  -> Core qualification collector and disposable Redis queue/replay
  -> independent validator.responses_observation reader
```

Each preserved seven native token probabilities and byte sequences exactly.
Each omitted the first visible word's probabilities, and the independent
checker retained one explicit missing delta and a `partial` observation.
Neither run established a complete first-token distribution.

The backend was LM Studio 0.4.4+1 using
`llama.cpp-mac-arm64-apple-metal-advsimd@2.14.0` and the same 20B MXFP4 GGUF
described in Core's `VALIDATOR_RESPONSES_QUALIFICATION.md`. The public worker
remained online on this machine, so these are not certified idle-load baselines.
No production request was registered or charged by this qualification.

Private evidence hashes:

- First fresh run:
  `de8d7380747a9a34a248ba0a15ca3ed9517c7b7f4677c515b0e58268fbd99e80`.
- Second fresh run, additionally proving diagnostic rejection by Core:
  `763886b028471dac96641ee23647216484157c7458000486d55c6da24186ef83`.

The harness used a fresh in-memory signing key with the existing EIP-191
signer to commit a domain-separated transport diagnostic. Signature recovery
matched the throwaway signer. Core's attestation normalizer rejected this
diagnostic because it is not a network verdict/attestation. No live key,
outbox entry, public evidence submission or payout was involved.

## What The Reader Checks

- Bounded JSON with duplicate-key rejection and bounded whole observations.
- Strict schema, no unexpected authority fields, and false quality/comparison
  flags.
- Ordered, unreplayed delta sequences for one message/content part.
- Recomputed visible-prefix SHA256 and exact assembled visible text.
- Bounded finite logprobs, token strings, optional byte arrays, and top-k lists.
- Explicit missing positions and independently checked complete/partial labels.

Malformed observations raise `ObservationError`, meaning unusable evidence,
not worker failure. Well-formed forged probabilities deliberately pass: this
reader is not an execution verifier. Visible-prefix hashes omit hidden
reasoning and cannot establish full context equality between engines.

## Tests And Remaining Gates

The full validator unit run passed 342 tests with six explicit integration
skips. Ten new test methods include negative subcases and the forgery baseline.
Default registration/scoring remains unchanged.

This proves real local component transport, not the public registration
handshake, authenticated assignment API, sealed disclosure, durable outbox or
attestation submission loop for a new Responses policy. Those must be tested
before a public capability/release. The current chat first-token scorer must
not consume this envelope by conversion or silent fallback.

### Unsupported Runtime Dispatch Guard

A subsequent local regression test found that the generic text dispatcher
would score a familiar arithmetic challenge even when its bound capability was
an unknown future policy. Four sealed/unsealed synthetic cases produced signed
healthy envelopes before the fix. This uses mocked Core transport; it does not
show that production issues or accepts such assignments.

The dispatcher now rejects unknown text capabilities before probing or signing.
Legacy basic/arithmetic controls still work, and retry/restart tests retain
unsupported work as local dead letters without worker verdicts. This prevents a
future Responses policy from silently borrowing a chat scorer; it does not
implement the missing Responses assignment, scoring or outbox contract. The
guard is source work, not part of the immutable preview.16 release.

Next: pin and compare the same model across serving engines/quantizations,
measure idle/loaded variation, establish meaningful context alignment, then
test held-out model substitutions and adversarial work. No public penalty or
trust threshold is justified by these component tests.

## Fault-Path Follow-Up

An 18-case synthetic SSE/HTTP -> released v0.3.8 worker -> real WebSocket ->
Core/isolated Redis -> this independent reader run exposed four discrepancies:
Core accepted duplicate JSON keys and incorrectly labeled invalid-Unicode or
over-byte-limit item IDs as available. The reader already rejected invalid
identifiers; duplicate keys had been collapsed before reaching it.

Core now rejects ambiguous JSON and enforces the same UTF-8 identifier limit.
All 18 cases pass against the final formatted source. Missing, empty, malformed,
oversized and replayed evidence remains unavailable. Valid controls pass before
and after the faults, using new test connections, not same-socket recovery.
The collector does not enter guarded economic or worker-health functions.
Final private fault-report SHA-256:
`5c5b74e29810779a193c039b15a02fc66077ba846d0a59a7c2d81959403ccf8a`.

A fresh LM Studio request after the logic fix again preserved seven native
probability positions, retained one missing first-word delta, and rejected the
local diagnostic as a network attestation. Evidence SHA-256:
`0d876097e861cdc858aa907b075eb7a681c8d78dc8ae59a579aa8cb4a9de7e03`.
Core's focused regression suite passed 122 tests with no skips, including the
private capture replay. No public Responses assignment policy, signed runtime
loop or production deployment is established by these tests.

## Second-Backend Preparation

The identical GGUF was imported without re-quantization into the existing local
Ollama 0.33.2 server. Its manifest references the same model-blob digest, and a
native-chat arithmetic preflight returned 323 with a normal stop in 2.66 seconds.
Verbose tokenizer metadata and the selected template were recorded privately.
The model was unloaded after the preflight; the public LM Studio worker stayed
running. No public Grid model registration was added.

This establishes availability for a same-artifact comparison, not a measured
range of honest differences. Reported templates do not prove identical rendered
prompts, and different serving stacks may share underlying engine components.
They are not independently operated validator references.

The subsequent frozen 48-request same-GGUF comparison is complete; see
[Honest Baseline](HONEST_BASELINE_2026_09_06.md) for measured correct, wrong and
truncated outcomes, shared-load limitations and the 120B timeout follow-up.
It does not establish logprob context alignment or cross-quantization tolerance.

That report's subsequent decoded-context follow-up records six identical
rendered LM Studio input/output controls and twelve same-GGUF standalone-engine
score calls. It measures chosen-token probability gaps up to 1.766401 percentage
points at six word positions. Native LM Studio token IDs and effective sampler
settings remain unavailable, so exact conditional-context equivalence and safe
thresholds are still unproven. This does not close the public assignment/outbox
integration gate or make partial Responses evidence a chat first-token witness.

The later SDK-native tokenization check in that baseline report queried the
same six captured prefixes twice through LM Studio. All twelve native token-ID
sequences match the saved llama.cpp reference inputs. This is current tokenizer
agreement on captured strings, not a historical prediction trace, effective
sampler proof or completion of the Responses assignment/outbox integration.
