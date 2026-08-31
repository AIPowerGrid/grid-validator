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

Snapshot time: 2026-08-31 17:38 UTC.

| Gate | Current evidence | State |
| --- | --- | --- |
| Three independent verified operators | Zero verified independent groups | Open |
| Operator A qualification | Preview.13, online, candidate, 97.3% sampled heartbeat coverage; 164 completed / 152 authoritative attestations lifetime, including 28 completed / 26 authoritative after the qualification clock began; about 66.0 hours remain | Running |
| Operator B qualification | Preview.13, previously completed real work, currently offline and unreviewed | Open |
| Operator C qualification | Online with substantial real-work history, but still on preview.9 and unreviewed | Open |
| Public self-diagnosis | Public `val_*` lookup reports version, online state, activity, and redacted qualification progress | Passed |
| Windows self-service onboarding | One external operator enrolled, but required support after mixing the validator ID, API key, wallet, and private-key prompts | Not proven |
| Linux self-service onboarding | One external Ubuntu operator enrolled quickly without Google/GitHub login; upgrade-in-place to the cohort baseline remains required | Partial |
| Randomized workload coverage | Exact output, arithmetic, JSON, 4K/16K/32K retrieval, multistep logic, restricted code, tool calls, tool chains, stop sequences, and token limits observed | Passed with calibration work |
| Cohort operations monitor | One Redis-leased aggregate monitor is live across four Core processes; assignment, evidence, error, disagreement, freshness, version, candidate, and common-control warnings have no authority side effect | Passed |
| Independent quorum | Distinct-registration preview quorum operates; reviewed independent quorum remains zero | Open |
| Economic isolation | Public status reports `economic_effect: none`; no routing or reward authority enabled | Passed |

Operator labels are deliberately not linked to public validator IDs or human
identities in this repository. The protected review system owns the private
operator-to-control-group mapping.

## Network Evidence

At the snapshot, the public 24-hour network status reported:

- 10 active registrations, 7 fresh heartbeats, and 7 participating nodes;
- 738 completed assignments and 663 authoritative votes;
- 98.34 percent objective agreement and a 5.88 percent disputed-group rate;
- coverage across 10 workers and 9 models; and
- zero verified or participating independent operators.

The active candidate produced healthy post-enrollment evidence across JSON,
arithmetic, 4K/16K/32K retrieval, multistep logic, restricted code, and
two-stage tool calling. This is materially stronger than a static echo canary.
Each current generated assignment has a validator-specific randomized prompt
and answer commitment, Grid nonce, target worker, expiry, evidence commitment,
and authoritative signature path.

Production Core release `be6a976fc76443e3c927ff929cd88fb9fe876e5b`
also runs the aggregate cohort watchdog under a renewable Redis leader lease,
so four Uvicorn processes produce one database scan per interval. Its first
live pass reported the two expected operational warnings: three stale active
registrations and four fresh registrations outside preview.13. It reported no
stale candidate and no duplicate reviewed control group. The monitor is
read-only and public status continues to report `economic_effect: none`.

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
`max_tokens`.

A read-only production snapshot on 2026-08-31 established the first concrete
calibration baseline without exporting any prompt, answer, nonce, identity, or
evidence material:

- `stop.sequence` was not random noise. The `gpt-oss-120b` path completed 128
  probes but returned no visible answer in all 128; 95 reported a stop terminal
  and 33 did not report a finish reason. The
  `deepseek-v4-flash-nvfp4` path showed the same shape across 51 probes.
- Two observed `qwen38-flash-next-125b-nvfp4` aliases completed 40 stop probes:
  26 returned the exact committed prefix, while 14 returned a doubled prefix.
  This demonstrates that the lane distinguishes concrete adapter/backend
  behavior rather than merely rejecting every model family.
- `token.limit` remained strongly backend-sensitive. The `gpt-oss-120b` path
  had no healthy result in the observed window; most length terminals consumed
  hidden reasoning while returning no visible repeated marker. The
  `deepseek-v4-flash-nvfp4` path produced 15 healthy and 76 failed results,
  confirming that a blanket pass or blanket skip would both discard useful
  protocol evidence.
- The first 55 result envelopes carrying the new bounded reason code produced
  35 accepted results and 20 classified failures: malformed stop output,
  reasoning-only token-limit output, or malformed two-step tool calls. None of
  those codes contains expected-answer material.

The calibration decision is therefore to keep the lanes and keep their strict
API-level verdicts, while preserving `protocol_conformance`,
`quality_eligible: false`, and no economic or routing effect. Do not translate
these failures into claims that a model lacks intelligence or fidelity. Core
main commit `8f87bdf9472f4108d067dc8ec6de12bd5c9b21c2` adds a privacy-safe,
read-only aggregate calibration report so future snapshots are reproducible.
Backend-native comparisons remain open before any authority discussion.

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
