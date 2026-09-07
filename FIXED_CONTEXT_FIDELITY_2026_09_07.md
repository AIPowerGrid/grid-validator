# Fixed-Context Distribution Calibration

Private native-inference experiment, 2026-09-07 UTC. No public assignment,
registration, production configuration or economic authority changed.

## Decision

The existing distance bands do not reliably distinguish these actual 20B and
120B continuations. Removing candidate-generated reasoning did not by itself
solve the identification problem. Do not tighten the bands against these
already-observed evaluation inputs, or grant trust just for enabling logprobs.

This evaluates the unchanged bounded top-20 distance proxy, not every possible
fingerprinting method. It is distinct from the failed
[final-answer likelihood rule](ANSWER_FIDELITY_2026_09_06.md).

## Frozen Method

- Sixty-four new short English raw-text continuations: sixteen each in prose,
  science, software and operations. Eight per family enter calibration and
  eight evaluation, assigned before inference. None repeats a prompt from the
  earlier answer, quantization or scripted-reasoning studies.
- Every artifact runs each context twice: **384 actual native calls** across
  the pinned published 20B Q8/Q4 pair and the pinned 120B MXFP4 artifact.
  These are publisher conversions, not independently proven upstream tensor
  equivalence. The Q8/Q4 pair retains the same MXFP4 experts; see
  [the artifact audit](QUANTIZATION_BASELINE_2026_09_06.md).
- All three runtimes independently tokenize and detokenize every prefix and
  receive identical explicit token IDs. No chat-template insertion, sampled
  reasoning or candidate-authored continuation precedes the scored position.
- Pinned llama.cpp b10826, one 2048-token slot, F16 KV, all GPU layers,
  temperature zero, seed 17, one output token, pre-sampling top 20, no prompt
  caching, adapters, grammar or penalties. Runs are serialized on the shared
  Mac; this is not an exclusive-idle or cross-engine test.
- Eligibility requires ordinary decoded greedy output containing an
  alphanumeric character on both sides. Nonlexical, incomplete-UTF8,
  ambiguous-token or infrastructure outcomes remain unavailable. All 384
  observed calls are eligible; no case was silently discarded.
- Use the unchanged public `jensen_shannon` implementation, independently
  reconstructed and compared numerically. Match is at most `0.12`, anomaly is
  at least `0.30`, and the interval between is gray. No threshold is fitted on
  either split; calibration labels organize diagnostics only.

The proxy pools unreported probability mass and compares the reported token
categories. **It is not true full-vocabulary Jensen-Shannon divergence.** A
token missing from top 20 has unknown probability, not an established zero.
Do not interpret proxy distances as complete distribution measurements.

## Results

Each row below contains 32 distinct contexts, repeated twice. Related prose
and repeated cases are correlated, not 64 independent trials.

| Comparison | Split | Eligible | Match | Gray | Anomaly | Maximum distance |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Honest 20B Q8 vs Q4 | Calibration | 64 | 62 | 2 | 0 | 0.124395 |
| Honest 20B Q8 vs Q4 | Evaluation | 64 | 62 | 2 | 0 | 0.126936 |
| Actual 20B Q8 vs 120B | Calibration | 64 | 54 | 10 | 0 | 0.216075 |
| Actual 20B Q8 vs 120B | Evaluation | 64 | 62 | 2 | 0 | 0.180866 |
| Actual 20B Q4 vs 120B | Calibration | 64 | 56 | 8 | 0 | 0.294175 |
| Actual 20B Q4 vs 120B | Evaluation | 64 | 60 | 4 | 0 | 0.128139 |

On held-out inputs, 31/32 Q8 and 30/32 Q4 cross-model cases fall inside the
match band. Neither artifact produces an anomaly-band observation. One honest
quantization case per split is gray, not an accusation. The two models' exact
answers need not match for their distributions to fall inside a distance band.

All 64 within-artifact repeat pairs have exactly identical native top-20
distributions for each of the three artifacts. This is useful repeatability
evidence for these serialized short contexts, not a contradiction of the
earlier loaded full-answer variation or a guarantee of fleet determinism.

These are raw-context metric bands, **not authoritative validator verdicts**.
There is no Grid-issued challenge, signed assignment, independently operated
reference quorum or demonstrated application of public chat-policy semantics.
The honest quant controls concern 20B; they are not a measured honest
120B cross-quant/engine false-positive bound. Unfinished text continuations also
have no correctness oracle, so these results do not rank model quality.

## Copied-Report Attack

For all 256 cross-model pair observations, replacing the candidate-reported
distribution with the captured 120B reference distribution gives distance zero
under the unchanged scorer. The independent calculation agrees. This is an
offline fabricated-report experiment, not a forged signature, an accepted
production attestation or proof that an attacker can access a private reference.

It demonstrates the remaining trust assumption: native distributions can be
measured under controlled operation, but an arbitrary worker's reported values
are not authenticated proof of inference. Bindings establish who reported bytes,
not which model generated them. The reference-access/proxying threat remains
separate from intrinsic statistical discrimination.

## Verification And Evidence

Four pre-inference tests cover fresh fixture counts, independent metric
agreement, copied-distribution behavior, unavailable categories and correct
counting of repeated cases. The full audit checks the 384-call schedule,
native probability/settings witnesses, identical prefix token IDs, cross-model
token-byte consistency, model/binary/library hashes and server cleanup.
Its rerun reproduced the saved summary byte-for-byte without new inference.
The four regression tests and Ruff lint/format checks passed again afterward.

All three owned servers stopped with exit zero and their PIDs were absent.
The existing public LM Studio backend and worker remained running. Production
services, account balances, registrations, payouts and authority flags were
untouched. Raw prompts and captures remain private.

| Private artifact | SHA-256 |
| --- | --- |
| Frozen manifest | `af81ec90470a6d440fea4e0fb8c7c30732e622351c0136fcd257c57e4a316e0e` |
| Native requests/responses | `a6d090de99a3383f72ee605f6aa3ea44e258a53a37d6b7923367834ee7fe5e3b` |
| Reference tokenized contexts | `0d932ad887ed9a4e978d2213d8fb5bfa03495378a9aff974cab6ee392c8f4cfd` |
| Independently audited summary | `c41e0fbb15146956086c9578f1e908be8de26de5c82b210e5a3e3442f79aed0a` |

## Remaining Gates

Keep capability correctness separate from model identity. Honest engine/quant
controls, real media calibration, independent-operator review and shadow
scorecards remain open. Any revised or aggregate fingerprint method needs a
separate preregistered experiment and fresh held-out inputs; these observations
must not become their own tuning and validation set. Automatic penalties stay
outside the authority of these experiments.
