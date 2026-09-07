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

## Updater Implementation Evidence

Release discovery is merged; installation is not yet wired. The in-progress
`release_verify.py` authenticates the manifest using Sigstore 4.5.0, the exact
GitHub release workflow identity and signed SLSA source/tag/platform bindings.
On 2026-09-07 it verified the published preview.16 manifest without a GitHub
login and rejected altered manifest bytes and an altered source commit against
the real published attestation. Manifest SHA-256:
`904c279ca6c381c1de75b216d160e9676aa7307ee7f979946e027683233500d0`.

Hermetic policy tests mock the cryptographic transport explicitly. Neither
those tests nor the live manifest check proves archive extraction, packaged
trust-root resources, anti-downgrade selection, running-binary replacement,
identity preservation or successful restart/rollback. Those remain required
for the one-click updater, which must isolate verification in a killable child
and must never replace an externally managed service or container.

Local source verification: 372 unittest cases, 366 passed and six optional
Core/Console integration cases skipped; all 11 new verifier-policy cases pass.
Ruff, strict mypy on the verifier, frozen-lock resolution with CI's uv 0.12.5,
staged secret scanning and the all-extras dependency audit pass. These are local
source checks, not native packaged updater qualification.

The next implementation step adds bounded, credential-free child preparation,
HTTPS download and private archive staging. The real preview.16 macOS archive
was downloaded (61,383,946 bytes), signature/digest checked and extracted
(61,845,216 executable bytes), without execution or activation. Executable
SHA-256: `c096d116b03cc23e991b3f40cecc787883d7834891d85a4af44126368d23699a`.
The temporary stage was removed. Fixture tests reject path/symlink/device
entries, CRC corruption, compression bombs, untrusted redirects, interrupted
downloads and attempts to overwrite an existing executable. Source child tests
cover cancellation, oversized replies, timeouts and a credential-free environment.

Native build CI now collects Sigstore data and invokes offline packaged
`_update-worker self-test`, which loads trust roots and app assets. Passing the
earlier manifest-only build does not prove this newer gate. Installation still
needs explicit app activation, restart/rollback and cross-platform persistence
tests. Frozen restart/handoff must use independent PyInstaller state as required
by the [PyInstaller restart guidance](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#using-sys-executable-to-spawn-subprocesses-that-outlive-the-application-process-implementing-application-restart).
The staging/process source suite passes 394 cases (388 passed, six optional
Core/Console integration skips), including 14 download/archive and eight process
tests. Strict type checks pass for the three new modules. Native build results
for this step must be checked on its own commit, not the earlier verifier-only
commit.

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
