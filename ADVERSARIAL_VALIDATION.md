# Adversarial Validator Contract

## Purpose

Define what Grid validator evidence proves, how a worker can game it, and the
gates that must close before evidence affects routing or economics.

The acceptance test is intentionally hostile:

> A worker using regexes, cached answers, template-specific programs, or a tiny
> specialist model may pass protocol checks, but must not earn a quality score.

## Attacker Model

Assume a worker operator:

- reads every public validator and worker source file
- controls the worker client, backend, model router, and local logs
- recognizes prompt families and records terminal acknowledgments
- routes suspected probes to a stronger backend
- caches prior prompts and outputs
- operates multiple accounts or colludes with a validator

Security cannot depend on hiding the scoring code. Short-lived challenge values
prevent exact answer replay; they do not prevent template recognition.

## Current Guarantees

- Core issues a short-lived assignment for one target worker and model.
- Core strips assignment, group, nonce, and `_validator_*` metadata before the
  job crosses the worker WebSocket.
- The validator independently scores the returned evidence commitment and signs
  its verdict.
- Core verifies assignment, nonce, target, evidence hash, signature, and one
  vote per registered validator/group.
- Preview quorum requires three matching votes from five registrations.
- Evidence has no routing, reward, strike, payout, bond, or slashing authority.

These guarantees prove attributable protocol execution. They do not prove an
exact model, parameter count, quantization, general intelligence, or independent
operator control.

## Evidence Dimensions

| Dimension | Examples | Current authority |
|---|---|---|
| Availability | accepted work, completed before deadline | evidence only |
| Protocol conformance | echo, strict JSON, stop, output limit, media contract | evidence only |
| Capability | reasoning, context, code, tool workflows | evidence only |
| Quality | blind production-shaped comparison | not implemented |
| Fidelity | deterministic governed workflow vs references | dark/default-off |

No generated public-template canary is quality-eligible.

## Known Fingerprints

- Prompt families remain recognizable even when their values are random.
- Production v7 text groups repeat one challenge across validators. Core v8
  changes the group into a capability batch with a unique challenge per member.
- An evidence-only validator probe ends with `den: 0`. Although this arrives
  after the answer, it labels examples that can train a future probe detector.
  Core candidate `0025` adds a default-off reviewed-wallet pilot whose text
  stages reserve from a durable daily den budget and settle through the
  ordinary worker ledger/ACK path. That closes the terminal label for the
  pilot, not prompt-template recognition.
- First-party pilot validators share one operator and hypervisor.

These are blockers for economic authority, not reasons to hide the source.

## Required Hardening

1. **Unique batch work:** issue a distinct challenge and commitment to every
   validator in a shared capability batch; aggregate the lane, not an identical
   exam prompt.
2. **Ordinary worker economics:** pay bounded audit work through a reviewed
   network audit budget so dispatch and terminal acknowledgment match ordinary
   jobs. Do not fake den in the worker UI without a committed ledger movement.
3. **Broad challenge packs:** combine generated code, hidden tests, stateful
   tools, long context, instruction hierarchy, extraction, reasoning, and
   multilingual surfaces. Public generators use unpredictable epoch inputs;
   secrecy is defense in depth, not the root control.
4. **Blind workload audits:** use consented or synthetic production-shaped jobs,
   compare anonymized results with rotating bonded references, and never reuse
   private user content without explicit consent.
5. **Adversarial CI:** run regex solvers, prompt classifiers, replay caches, and
   model-switching workers. A successful template solver must remain confined
   to protocol/capability evidence with no quality authority.
6. **Independent cohort:** prove independently controlled operators before any
   validator reward or routing influence.
7. **Conservative penalties:** subjective quality may affect scorecards and,
   later, routing. Only objective signed fraud may enter a dispute-backed
   slashing design.

## Economic Gate

Validator evidence must remain non-economic until all of the following are
measured in a production pilot:

- worker-visible probe classifier performs no materially better than chance
- audit compensation is bounded, ledgered, and abuse-tested
- unique challenge batches and evidence binding survive concurrency tests
- independent validator quorum and operator diversity are proven
- worker disputes and false-positive rollback are operational
- quality scoring uses blind workloads rather than public canary templates
