# Tool Capability Pilot And Template-Solver Control

## Decision

Keep recognizable tool workflows as capability samples, not model-identity or
general-quality evidence. The tested 20B completed every local episode, but a
non-LLM script also completed them and 400 fresh randomized-value episodes.
Random tool-name suffixes, quantities, inventory, and revision strings did not
make this workflow resistant to a specialized solver.

No production policy, assignment schema, worker registration, routing weight,
penalty, reward, or account balance changed. This is a private backend pilot and
offline negative control, not a live exploit of signed Grid assignments.

## Frozen Model Experiment

The local LM Studio GPT-OSS-20B used the same GGUF as
[the honest baseline](HONEST_BASELINE_2026_09_06.md): SHA-256
`65d06d31a3977d553cb3af137b5c26b5f1e9297a6aaa29ae7caa98788cde53ab`.
LM Studio 0.4.4+1 used its selected
`llama.cpp-mac-arm64-apple-metal-advsimd@2.14.0` runtime, 8192 loaded context,
one parallel slot. The aggregate API model label is not artifact provenance;
the earlier local file/runtime inspection owns that binding.

Two generated base fixtures each have normal and stockout variants, with two
repeats: eight episodes, not eight independent task families. The private
manifest froze cases, schedule, source hashes, settings and acceptance rules
before inference. This is calibration, not held-out model-substitution testing.

- Non-streaming `/v1/chat/completions`; temperature 0, top_p 1, seed 17,
  medium reasoning, max_tokens 1024 per call.
- Three tools visible each turn, `tool_choice=auto`, parallel calls disabled.
  No forced function selector; the initial instruction specifies a lookup.
- After lookup, the user changes the requested quantity. The change makes the
  previously eligible cheapest item insufficient.
- Stockout variants return an error and replacement inventory/revision after
  the first otherwise-correct reservation. The next action must select again.
- Successful reservation requires a confirmation with the correct total, then
  exact structured final output matching the completed transaction state.
- Native assistant messages, including reasoning and tool calls, remain in
  subsequent request history. No invented assistant reasoning is substituted.
- All tools are local synthetic fixtures. No model-generated code executes and
  no real purchase, reservation, or external tool request occurs.
- Stop at the first bad or budget-limited turn; infrastructure/unavailable
  results remain separate. No result-driven retry or fixture replacement.

## Observed Results

| Condition | Episodes | Correct | Median episode time |
| --- | ---: | ---: | ---: |
| Quantity correction, normal completion | 4 | 4 | 9.09 s |
| Quantity correction, stockout recovery | 4 | 4 | 12.00 s |

The 36 model calls produced 28 correct tool calls and eight correct final
objects. All eight quantity corrections were honored; all four stockouts were
recovered. Per-call completion tokens ranged from 64 to 340, median 147.
There were no observed transport failures or budget exhaustion in this run.
The independent transcript audit verified 28 native reasoning messages were
preserved in subsequent requests.

The public worker remained running on the same backend. No public job arrivals
were observed in its log during these episodes; that is not exclusive-host or
numerical-determinism proof. These observations do not establish population
accuracy, long-context robustness, a minimum viable output budget, or exact
model identity. The direct-backend pilot does not exercise Core's deployed
two-stage tool-chain assignment policy.

## Specialized Solver Attack

A frozen, non-LLM solver recognizes the workflow and parses only the visible
messages and tool definitions. It filters inventory, tracks the latest quantity
and revision, and calculates the confirmation total. Its strategy receives no
fixture seed or expected-answer object. The original driver supplies simulated
tool results from the fixture oracle; this is not a hostile process sandbox.

It passed the original eight episodes without inference. A separate stateful
environment then rechecked every stored trace without using the original
oracle or turn scorers. The independent checker rejected three intentional
corruptions: old quantity, stale revision after stockout, and incorrect total.

With the solver unchanged and its source hash checked, 100 fresh random seeds
produced 400 episodes (200 base inventories, each normal/stockout). The script
passed all 400 with zero model calls and zero network calls. The cases contain
new values within the known template, not new task semantics. Paired cases and
the shared template are correlated; 400/400 is not a general attack-success
estimate for the deployed network.

**Attack outcome:** this local capability family fails to distinguish a model
from a purpose-built script. Assignment signatures and fresh nonces can bind
who reported evidence and when; they cannot make such a result prove inference.
This experiment did not test bypassing Core authentication, assignment binding,
signatures, quorum, or a live worker's evidence submission.

## Evidence And Reproduction

Private operator directory: `text-worker-20b/tool-behavior-20260906/`.
Prompts, seeds, expected answers, transcripts, and attack code remain private;
the hashes below commit to the measured artifacts. Hashes alone are not a
publicly reproducible benchmark. An authorized reviewer needs the private
bundle; this report intentionally does not publish a reusable challenge key.

| Artifact | SHA-256 |
| --- | --- |
| Frozen model-run manifest | `9c47509d53c5fc3cec037e6777df4364cdeb2317e5f3f3dc56d03f1d4eb675e0` |
| Raw model transcripts | `dc7a8a15b4bdc56f237c0158a6c3284d2f3ca4bb2a2866d492537a3d2a720cf4` |
| Independently audited model summary | `f9af68b9cab6ef8116d166a7c5c910b3d4868fadb705bcb911e81631a48af10e` |
| Original script attack | `0c426bd5dc7b54778b1ac109c671e883e7d9461c5aaae9de0919ca1ab68f2607` |
| Fresh-case independent attack audit | `0ed2e09d93241bf50abae0ff85b1b809d2068ac807be1004bc3662abfc4d9a97` |

Verification: eight private scorer unit tests pass; `audit_tool_success.py`
reconstructs all requests and expected results from the recorded native
transcripts. `audit_tool_template_attack.py` independently checks recorded
script traces, rejects corrupted controls, and replays all fresh cases. Repeat
audit runs verify existing artifacts byte-for-byte, without rerunning inference
or overwriting results. Neither audit converts an unavailable result into fraud.

## Next Gates

1. Separate structured-output, tool recovery, state tracking and context scores;
   no composite intelligence score or model badge from this fixture family.
2. Freeze any candidate detector and acceptance criteria before fresh evaluation
   with verified reference weights and actual candidate answers. Do not train
   thresholds on the old behavioral calibration cases.
3. Include specialized solvers, fabricated probabilities, probe-aware switching
   and proxying as negative controls. More randomized values in an unchanged
   template are not sufficient anti-cheating hardening.
4. Qualify any expanded multi-step policy through Core and the independent
   validator, including bounded histories, failure categories, replay and
   assignment binding. This report does not claim that integration is shipped.
5. Continue shadow-only evidence until honest variation and held-out false
   positives are measured. Compensation remains separate from penalty authority.
