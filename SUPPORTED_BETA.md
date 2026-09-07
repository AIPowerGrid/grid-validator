# Supported Validator Beta

## Objective

Ship an easy-to-operate validator, useful attributable evidence and a capped
compensation pilot. Exact model identity is not a launch requirement. No
automatic worker penalties are authorized by this plan.

The owner is the sole AIPG maintainer. Do not invent another required maintainer
or make operators repeat information already supplied privately.

## Current Checkpoint

As checked September 7, 2026:

- Preview.17 is published from `aa35fa0a`, including the verified app updater.
  Release workflow `34136400434` passed four-platform native handoff, recovery
  and clean-install checks. Downloaded assets and pinned provenance passed
  verification. Old installed binaries do not gain the updater retroactively.
- Production Core `874f7407` / Alembic `0039` admits preview.13/.15/.16/.17 while preserving
  identity, qualification history and review records. Shadow observation and
  validator economics remain off.
- An owned Linux service upgraded from .15 to .17 with config and durable
  journal intact. Three fresh reports by 15:53:07 UTC have independently
  verified signatures and assignment bindings. A
  second owned node received no accepted report during a bounded 25-minute
  attempt ending 16:11:49 UTC; it was restored healthy to its original .15
  service with the temporary proxy removed. That attempt is inconclusive.
  Its repeat passed at 17:04:11 UTC: an accepted response was lost, the signed
  report survived .15-to-.17, and a same-record duplicate acknowledgment drained
  it. Independent Core signature/binding, zero-economic-row and cleanup checks
  passed. This is a service upgrade, not a human desktop one-click test.
- Website PR77 (`c23f9281`) promoted preview.17 after the recovery check.
  Its production deployment is Ready and `aipowergrid.io/validate` serves the
  new release links. The candidate passed 112 unit tests and nine local browser
  tests; production browser verification also passed. Website tests do not
  prove registered-node recovery or independent-operator qualification.
- Core PR124 (`f7c981c2`) merged the private, approved-campaign allocation ledger
  and migration `0036`, with PostgreSQL concurrency and restored-migration CI.
  PR125 adds reviewed dual-signed recipients (`0037`); PR126 adds a default-off
  nonce-bound sender (`0038`); PR127 (`2d16a019`) adds private operator status
  and wallet/node signature collection (`0039`). The node app now consumes that
  contract in unreleased source. Console PR27 (`28dbf5f3`) and node PR107/108
  are merged; Core PR128 (`874f7407`) passed real-PG/Core/Console/node handoff
  CI. PR108 and merged-master run `34157734708` passed all four native builds,
  frozen update handoffs and clean installs. The September 7 19:57 UTC dark
  Core deployment passed restored-backup migration/schema checks, preserved all
  21 validator identity/review records and environment bytes, and left all six
  compensation tables empty. Native publication, live consent and paid-pilot
  activation remain. No live campaign or total pilot budget has been approved.
  See `COMPENSATION.md` and Core's deployment record
  `deploy/VALIDATOR_COMPENSATION_DARK_2026_09_07.md`.
- The third first-party Linux service upgraded from .15 to published .17 at
  20:13:10 UTC with its existing identity, configuration and stopped-journal
  digest preserved. The authenticated no-probe check and public supported
  heartbeat passed. This check did not wait for a fresh post-upgrade signed
  report and does not count as an independent operator or desktop-app journey.
- The September 7 read-only candidate review found one candidate passing all
  technical gates, another blocked by an old heartbeat, and another blocked
  by coverage. Core's candidate review reference is not the underlying private
  control confirmation: finalization still requires that record. The new
  GitHub intake declaration is retained as a claim, not silently promoted to
  independence. Issue #5 now recommends .17 and preserves existing observation
  history instead of telling operators to restart after intake.
- An external .15 node remains active. Do not remove its supported version to
  make room for a successor release. The current four-version admission cap
  needs a separately reviewed compatibility transition before publishing an
  automatically discovered successor; native build success alone is not that
  admission decision.

See `UPDATES.md` and `ROLLOUT_2026_09.md` for release and failure evidence.

## Remaining Delivery Order

1. Help existing operators use the now-published preview.17 downloads and
   confirm fresh accepted evidence. Preserve configs, IDs and qualification clocks.
   App updates never replace externally managed services or containers.
2. Complete reviews for three independently controlled operators using existing
   records and IDs. Diagnose outages and missing coverage rather than restarting
   enrollment. Re-request only genuinely missing control information; do not
   infer independence from a public ID, IP address or Discord handle.
3. Freeze one seven-day production pilot in Core's existing shadow-run machinery:
   selected reviewed operators, exact compatible release policy, acceptance
   thresholds, start and end. Check the live start gate before activation.
   Publish pass/fail/inconclusive at the end; do not extend it to manufacture a
   pass. Any rerun is a separately recorded decision. Preserve prior observations.
4. Finish compensation in parallel: owner-approved asset and total budget,
   immutable eligible-work allocations, per-operator caps, durable duplicate
   protection, reviewed recipients and payment reconciliation. Reuse the audited
   payment rail where appropriate. Never send an offline preview as a payment
   manifest or show simulated allocations as earned balances.
5. Verify the complete operator journey and scorecard: actual connectivity,
   completed assignments, accepted evidence, pending retries, qualification,
   compensation status and actionable errors. Then publish the pilot result and
   supported-beta instructions with accurate capability limits.

## Pilot Acceptance

Freeze numerical thresholds in the run record before it starts. Evaluate
assignment completion and acknowledged evidence delivery with denominators;
signature and assignment binding; duplicate/retry safety; outage recovery;
heartbeat coverage; backlog; and scorecard consistency. Separate unavailable
coordinator/reference infrastructure from candidate-worker failures.

Preview release promotion and supported paid-beta activation are different
milestones. A tested updater can be recommended before the seven-day beta pilot
finishes. Publishing it grants no economic, routing or penalty authority.

## Capability And Payment Boundaries

Availability and task-specific correctness are useful evidence dimensions, not
proof of exact weights, parameter count, hardware or model provenance. Logprob
substitution misses, fabricated matching probabilities, colluding signed
judgments and image-copy acceptance remain limitations. Experimental fidelity
and media lanes remain non-punitive until separately qualified.

Compensate reviewed useful participation, not majority agreement, particular
verdicts or accusation counts. Payment does not authorize worker penalties.
First-party nodes do not fill independent-operator seats or eligible paid seats
under this pilot. No new staking contract is required to pay a reviewed pilot.

## Source Of Truth

- `QUALIFICATION_DECISIONS.md`: completed experiments and capability limits.
- `PREVIEW_COHORT.md`: operator intake and independent-control qualification.
- `ROLLOUT_2026_09.md`: dated deployment and release evidence.
- Core `scripts/review_validator_operator.py`: digest-bound review preview/apply.
- Core `scripts/manage_validator_shadow_run.py`: bounded shadow-run lifecycle.
- Core `scripts/preview_validator_compensation.py`: offline, non-sendable preview.
- Core `scripts/manage_validator_compensation.py`: approved durable allocations,
  not transaction execution or automatic economic activation.

Live status, protected review records, immutable CI artifacts and the finalized
pilot report are completion evidence. This checklist alone is not.
