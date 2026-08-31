# Validator Preview Cohort Report - 2026 Q3

Status: **in progress**. This report is not evidence that the cohort exit gate
has passed. Refresh the dated observations from the public status contracts and
the private maintainer review before changing any gate below.

## Decision Boundary

The cohort tests independent operation, onboarding, assignment delivery, and
objective evidence handling. Validator evidence remains economically inert: it
does not affect routing, rewards, worker payouts, strikes, bonds, or slashing.
The current public baseline is immutable
[`v0.1.0-preview.13`](https://github.com/AIPowerGrid/grid-validator/releases/tag/v0.1.0-preview.13).

The initial exit gate requires three separately controlled operators to finish
one reviewed 72-hour run with at least 80 percent bounded heartbeat coverage, a
fresh terminal heartbeat, and accepted real-work evidence. Registration,
wallets, node count, or first-party validators do not satisfy independence.

## Current Gate Snapshot

Snapshot time: 2026-08-31 16:01 UTC.

| Gate | Current evidence | State |
| --- | --- | --- |
| Three independent verified operators | Zero verified independent groups | Open |
| Operator A qualification | Preview.13, online, candidate, 96.3% sampled heartbeat coverage; 158 assigned / 156 completed / 144 authoritative attestations | Running |
| Operator B qualification | Preview.13, previously completed real work, currently offline and unreviewed | Open |
| Operator C qualification | Online with substantial real-work history, but still on preview.9 and unreviewed | Open |
| Public self-diagnosis | Public `val_*` lookup reports version, online state, activity, and redacted qualification progress | Passed |
| Windows self-service onboarding | One external operator enrolled, but required support after mixing the validator ID, API key, wallet, and private-key prompts | Not proven |
| Linux self-service onboarding | One external Ubuntu operator enrolled quickly without Google/GitHub login; upgrade-in-place to the cohort baseline remains required | Partial |
| Randomized workload coverage | Exact output, arithmetic, JSON, 4K/16K/32K retrieval, multistep logic, restricted code, tool calls, tool chains, stop sequences, and token limits observed | Passed with calibration work |
| Independent quorum | Distinct-registration preview quorum operates; reviewed independent quorum remains zero | Open |
| Economic isolation | Public status reports `economic_effect: none`; no routing or reward authority enabled | Passed |

Operator labels are deliberately not linked to public validator IDs or human
identities in this repository. The protected review system owns the private
operator-to-control-group mapping.

## Network Evidence

At the snapshot, the public 24-hour network status reported:

- 10 active registrations, 7 fresh heartbeats, and 7 participating nodes;
- 733 completed assignments and 655 authoritative votes;
- 98.17 percent objective agreement and a 6.67 percent disputed-group rate;
- coverage across 10 workers and 9 models; and
- zero verified or participating independent operators.

The active candidate produced healthy post-enrollment evidence across JSON,
arithmetic, 4K/16K/32K retrieval, multistep logic, restricted code, and
two-stage tool calling. This is materially stronger than a static echo canary.
Each current generated assignment has a validator-specific randomized prompt
and answer commitment, Grid nonce, target worker, expiry, evidence commitment,
and authoritative signature path.

## Calibration Findings

Stop-sequence and token-limit probes are protocol-conformance evidence, not
general intelligence or model-fidelity scores. Their preview failure rates are
strongly backend-dependent. Reasoning-model backends frequently consume the
budget in hidden reasoning and return no visible answer, while several
non-reasoning backends return the expected visible output.

Core release `97efb358041ee00351e62e65b9b90f24fcf0d7e8` records a bounded private
`score_reason` in completed text-probe envelopes without changing verdicts or
exposing expected answers. The current text-worker main branch also has release-
gated tests proving that structured requests preserve Grid-issued `stop` and
`max_tokens`. Keep both lanes out of routing, rewards, strikes, and model-quality
claims until post-deploy reason distributions and backend-native comparisons
separate unsupported behavior from actual nonconformance.

## Onboarding Findings

- The dedicated-node enrollment model is correct: ordinary operators do not
  need funds, a browser wallet, Google/GitHub login, or an exported private key.
- Preview.13 setup and start are two separate local-app actions. Public guidance
  must not describe the unreleased combined setup/start behavior on `master` as
  part of the frozen binary.
- An upgrade must preserve the existing protected configuration and `val_*`
  identity. Re-enrollment would discard operational continuity and restart the
  review process under another registration.
- The public status checker removes most support guesswork, but the external
  Windows attempt shows that the current release does not yet prove unassisted
  onboarding for a non-technical operator.

## Remaining Actions

1. Keep Operator A online through the complete 72-hour gate, then preview the
   verify transition and inspect workload evidence before applying it.
2. Restore Operator B's existing preview.13 process and start candidate review
   only after a fresh heartbeat and control disclosure are confirmed.
3. Upgrade Operator C in place to preview.13, preserving its identity, then
   start the same reviewed candidate process.
4. Observe the deployed score-reason distribution and run bounded native-versus-
   Grid comparisons for stop-sequence and token-limit capable backends.
5. Record onboarding interventions, outages, disagreement, and final evidence
   totals for each operator without publishing identities or control groups.
6. Update this report only after all three verify previews are eligible and the
   private common-control review still supports three distinct groups.

## V1 Recommendation

Pending. Do not enable routing authority, validator rewards, staking, or
slashing from this draft. The final recommendation must be based on three
completed independent runs, shared-group evidence, calibrated failure reasons,
and the observed operator support burden.

## Refresh Sources

- Public aggregate: `GET https://api.aipowergrid.io/v1/status/network`
- Public node status: `GET https://api.aipowergrid.io/v1/validator/public/{validator_id}`
- Operator-local status: `aipg-validator check --no-probe`
- Maintainer qualification preview: `scripts/review_validator_operator.py`
- Public recruitment contract: [`PREVIEW_COHORT.md`](PREVIEW_COHORT.md)
- Private maintainer procedure: Core `deploy/VALIDATOR_COHORT_RUNBOOK.md`

