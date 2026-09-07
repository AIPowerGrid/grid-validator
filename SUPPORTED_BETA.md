# Supported Validator Beta

## Objective

An easy-to-operate validator with attributable, useful validation and a capped
compensation pilot. Model-identity research is not a prerequisite for releasing
supported operational validation. Failed detector experiments remain published
as limitations; no automatic worker penalties are authorized by this plan.

The owner is the sole AIPG maintainer. Do not invent another required maintainer
or make operators repeat information already supplied privately.

## Delivery Checklist

- Operator reviews: recover prior signed-control and common-control records;
  finish missing reviews using existing IDs. Diagnose interrupted participation
  before prescribing a remedy. Keep qualification timestamps and observations;
  do not use `--restart-qualification` to erase an inconvenient history.
- Upgrades: app-side release discovery is implemented in source, independent
  of a running node. Still required: explicit verified one-click installation,
  version/platform/source binding, provenance verification, atomic replacement,
  Windows running-executable handoff, health-checked restart and rollback. Test
  interrupted download, tampering, failed startup and unchanged signer/journal
  on every distributed platform. Preserve container/service ownership: an app
  must not kill or replace a separately managed service.
- Production pilot: use Core's existing shadow-run machinery, not a second
  timer. Start only with three reviewed independently controlled operators and
  the existing participation/group requirements. Freeze release, policy, cohort,
  acceptance thresholds, start and end in the run record before starting.
  Observe seven days. Publish pass/fail/inconclusive with denominators and outage
  explanations; do not extend the run indefinitely to manufacture a pass.
  Any rerun is a separately identified decision, not an overwritten result.
- Pilot evidence: report assignment completion, acknowledged evidence delivery,
  attributable signatures, duplicate/retry handling, outage recovery, heartbeat
  coverage, backlog and scorecard consistency. Separate host/coordinator failure
  from candidate-worker failure. Keep existing qualification history intact.
- Compensation: obtain owner approval of total budget and asset first. Existing
  Core `preview_validator_compensation.py` is an offline allocation preview,
  not a payment sender. Finish immutable allocations, per-operator caps,
  reviewed eligibility, duplicate protection and reconciliation before payment.
  Compensation is for reviewed useful participation, not majority agreement,
  a particular verdict, or number of accusations. No automatic slashing or
  routing privilege follows from payment. Never present simulated allocations
  as earned or paid balances.
- Operator view and release: show actual connection, completed assignments,
  accepted evidence, qualification, compensation state and actionable errors.
  Verify on native Windows/Linux/macOS and narrow/desktop browser layouts.
  Publish one reviewed release with an in-place upgrade guide and rollback
  evidence. Promote it only after artifact and production-pilot gates pass.

## Capability Boundary

Availability and task-specific correctness are supported evidence dimensions.
They do not prove exact weights, parameter count, hardware or model provenance.
Logprob substitution misses, forged matching probabilities, colluding signed
judgments and image-copy acceptance remain explicit limitations. Experimental
fidelity and media lanes stay non-punitive until separately qualified.

## Source Of Truth

- `QUALIFICATION_DECISIONS.md`: completed experiments and remaining gates.
- `PREVIEW_COHORT.md`: operator intake and independent-control qualification.
- `ROLLOUT_2026_09.md`: deployment/release evidence, not inferred fleet health.
- Core `scripts/review_validator_operator.py`: digest-bound review preview/apply.
- Core `scripts/manage_validator_shadow_run.py`: bounded shadow-run lifecycle.
- Core `scripts/preview_validator_compensation.py`: offline, non-sendable preview.

Live status, database review records, immutable CI artifacts and the finalized
pilot report are completion evidence. This checklist alone is not.
