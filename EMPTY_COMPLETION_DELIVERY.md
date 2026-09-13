# Committed Empty Completion Delivery

## Production Finding

During the September 13 owned preview.18-to-.19 canary, a read-only inspection
found 161 retained dead-lettered assignments in one owned node's journal.
Every record had reached the configured 20-attempt bound, and all IDs matched
Core assignments created between August 26 and September 13 at 02:47 UTC.
No matching signed attestation existed for any of the 161 assignments.

Core recorded 47 as probe failures without a verdict. These remain unavailable
transport evidence, not automatically failed workers. The other **114 had
completed empty outputs** and a failed local Core score: 97 stop-sequence,
13 context-retrieval and four arithmetic assignments. They had no visible text,
retained reasoning or tool calls. Their terminal reasons were stop or length.
Every local final retry occurred after the assignment expiry. Attempt counts
are local recovery counters, not proof of that many fresh worker executions.

The node skipped empty output unless the optional `grid.probe_failed` flag
was true, before verifying the returned commitment. The existing empty-output
test supplied that flag, leaving ordinary completed empty responses uncovered.
These records predate the .19 upgrade; they are not an upgrade regression.

## Correction

Completed replies with an explicit empty string now proceed through unchanged
disclosure and evidence verification, then the local scorer. Missing/null
output, non-completed replies, unavailable transport and mismatched hashes or
bindings remain skips. A worker-error flag is not evidence authority. No
scoring threshold, historical verdict, assignment or dead letter is rewritten.

New tests first reproduced the skip, then passed after the bounded correction:

- Sealed and unsealed empty stop/length completions produce a locally scored
  failed envelope, recoverable real signature and correlated empty hash.
- Wrong prompt/response/evidence hashes, wrong target/nonce/seal, non-completed
  status and null output never sign or submit.
- Delivery failure preserves the same signed envelope across journal reopening;
  retry neither reprobes nor signs again.

The full local source suite ran 427 tests: 420 passed and seven skipped. The
new transport is mocked; these tests do not prove a live empty-result delivery.

## Release Boundary

Preview.19 does not contain this correction. Its first owned canary delivered
fresh report `127676` at 03:20:23 UTC, a failed SmolLM instruction result, with
independently verified signature/bindings and zero economic rows. This is valid
failure reporting, not proof of fraud or live token-limit v2 execution.

The correction and token-limit update are now packaged together in immutable
preview.20, with verified four-platform builds, clean installs and source-bound
artifact provenance. Core admitted .20 and all three owned nodes upgraded;
see `PREVIEW20_ROLLOUT.md`. Ordinary and lane-specific fresh reports now passed
independent delivery audits; this is distinct from worker quality qualification.

Offline replay of the original sealed assignments and retained response bodies
verified, locally scored and signed all 114 completed-empty captures, while
leaving 47 unavailable captures unsigned. Delivery was mocked; no expired
assignment or historical production report was changed.

Fresh reports `127713` and `127714` at 04:56:51 UTC on September 13 exercised
this exact bug: completed empty stop-sequence results without reasoning, tool
calls or the optional worker-error flag. Two released .20 nodes delivered
signed failed evidence. Independent signature, assignment, disclosure-seal,
prompt/response/evidence hash and local-score checks passed, with no correlated
economic rows. These are real new assignments, not replayed historical work.
V2 delivery was separately checked at 04:48 UTC. Neither test establishes model
identity or determines why the backend returned empty output.

Keep .19 artifacts immutable. The live delivery gates for public promotion are
now satisfied. Do not automatically revive
expired historical work, backdate reports or manufacture compensation for it.
Operator review, payout consent and the total budget remain separate gates.
