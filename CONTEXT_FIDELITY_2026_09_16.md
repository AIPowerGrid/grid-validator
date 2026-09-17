# Context fidelity: measured limits and bounded follow-up

## Decision

The September 16 Qwen/Mac experiment does **not** establish a usable
model-substitution detector. Native probabilities were available, but the
candidate and reference did not expose probabilities at matching contexts.
Keep unavailable evidence separate from failed capability checks and from
model-substitution findings. No routing, worker penalty, reward adjustment or
model-verification claim follows from this study.

This extends, rather than replaces, the negative results in
[fixed-context fidelity](FIXED_CONTEXT_FIDELITY_2026_09_07.md) and the narrower
[batch experiment](BATCH_FIDELITY_2026_09_13.md). Customer reliability work takes
priority over this research. Compensation for approved participation is a
separate process, not payment for accusing workers or agreeing with a majority.

## Completed experiment

There were 54 direct native requests across six distinct cases and separately
frozen capability, raw-completion and visible-prefix follow-up plans. Repeated
Mac calls are correlated same-backend controls, not independent references.
Every request returned HTTP 200; that did not imply usable scoring evidence.

| Check | Measured outcome | What it establishes |
| --- | --- | --- |
| Qwen native probabilities | Present in Chat, Responses and raw Completions | Endpoint capability, not trustworthy worker reporting |
| Mac initial first-visible-token probabilities | Missing in all 18 repeated calls | First-token comparison unavailable on this configuration |
| Mac raw-completion probability preflight | Null in one request | Raw-prefix follow-up stopped rather than inventing probabilities |
| Mac aligned visible-prefix repeats | No flags in six cases | Same-machine repeatability only |
| Strict Qwen-as-120B comparison | Zero valid detections; six unavailable | Visible prefixes differed, so conditional distributions were not comparable |
| Unsafe first-available-token comparison | Six failed verdicts | Wrong-context comparisons can manufacture apparent success |
| Copied-reference-probability fixture | Six healthy verdicts | The isolated metric accepts copied vectors |
| Probe-only correct-model fixture | Six healthy verdicts | The isolated metric accepts a reference response selected for a recognized probe |

The last two rows are **offline comparator simulations**, not live attacks on
the signed assignment protocol. They assume reference-vector access or probe
recognition respectively; neither assumption's real-world success rate was
measured. No fabricated attestation was submitted to Core.

The maximum honest pairwise pooled-tail Jensen-Shannon proxy distance was
`1.9930238119738316e-9`. Existing reference-agreement, match and anomaly bands
remained `0.08`, `0.12` and `0.30`; no threshold was fitted to this experiment.
These six cases do not establish a population false-positive rate.

All six Qwen visible-prefix follow-up captures also contained an SSE event
over the Core observer's 65,536-byte limit. Capturing it directly is not proof
that the bounded production reader can admit it. Preserve reader safety limits
and investigate redundant or oversized payloads separately.

## Context and provenance requirements

Comparisons must bind the selected token bytes to the actual output delta,
channel and position. Missing first-token coverage must not silently become a
comparison of the second token. Equal visible prefixes alone do not establish
equal hidden reasoning, rendered templates, tokenizer semantics or effective
sampling settings. Temperature zero is not proof of deterministic execution.

This run projected native observations through the unchanged preview.20
comparator offline, excluding latency. It did not qualify Responses evidence
for the production Chat fidelity lane. The larger research output budget and
reasoning settings were not the production probe configuration.

Captured source and output hashes, native token/delta bindings and metric
calculations were independently reconstructed offline, including a read-only
recheck on September 17. Private captures and challenge material are retained
outside this public repository. The hashes below bind the retained artifacts;
they are not a public reproduction package or third-party audit certification.

- Scorecard SHA-256:
  `0f8d505fb230b412aead2b9b38d01490df14a7fa742ab8b0719628eda4939079`
- Independent verifier SHA-256:
  `5d3ad2e74a11367aa2f6878cbba9da34f148874195dcdb41458559ff9947c5de`

No service restart, model swap, production score change or economic action was
part of the completed experiment. Public challenge answer keys, operator
identities, endpoints and credentials are intentionally absent here.

## Prospective follow-up: one week, not an open-ended gate

The owner-authorized goal starts at **2026-09-17 01:10:09 UTC** and ends at
**2026-09-24 01:10:09 UTC**. Publish results and unresolved limitations by that
deadline, including a negative or incomplete result. Download time and customer
fixes do not silently reset the clock. This is separate from any Core shadow
observation window and does not change an approved compensation period.

1. Verify the staged second GPT-OSS-120B artifact against its pinned size and
   SHA-256 before an approved replacement of the owned Qwen backend. Preserve
   rollback and drain only that worker. The protected client GPT service is
   out of scope. A download in progress is not a working reference.
2. Freeze a private, hashed plan before new calls: backend/weight/runtime
   identity, actual rendered context, tokenizer and sampler settings, output
   channel, call and token budgets, scoring positions, and calibration versus
   held-out case split. Retain failures and exclusive-create captures.
3. First prove comparable native inputs and probability coverage. If that
   fails, report an adapter/capability limitation and stop the detector run.
   Do not strip whitespace or hidden reasoning after capture to manufacture
   matching contexts. Reference-side teacher forcing may be evaluated only
   where the endpoint actually exposes and binds the supplied prefix.
4. Run identical-artifact honest controls across the Mac and owned NVIDIA
   host, then deliberate substitution controls. The same GGUF using Metal and
   CUDA is cross-backend calibration within one engine family, **not vLLM
   qualification**, independent operator quorum or tolerance for every quant.
   Any additional engine/quant cell needs its own comparable-context proof.
5. Evaluate copied probabilities, replay and probe-only switching separately
   from honest drift. Label offline simulations versus live harness tests.
   Never send fabricated evidence into production or let research verdicts
   influence payments. A signature binds the reporter, not its computation.
6. Publish all scheduled, completed, comparable and unavailable denominators,
   honest flags, caught and missed substitutions, evasion results, latency and
   resource cost. Freeze candidate thresholds using calibration data only;
   do not adjust them after looking at held-out outcomes. With few correlated
   cases, report counts rather than a fleet-wide accuracy claim.

Initial bounds for this next study are at most **192 additional native calls**
including failed calls and preflights, with exact per-call token/time limits
frozen in the private plan. No unbounded retries or automatic resource purchases.
Plan 24 distinct cases split equally between calibration and held-out sets;
repeats do not increase the independent case count. Stop earlier when the
context gate fails, customer service is affected, or the time/call budget ends.

The deliverable is a decision: retain this as non-authoritative anomaly
research, propose a narrowly evidenced next method, or stop this approach.
Even a positive bounded result requires a separate review before any economic
or routing authority. Customer launch and useful capability monitoring do not
wait for a model-identity proof that this experiment may never provide.
