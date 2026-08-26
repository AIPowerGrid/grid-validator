# Validator Production Baseline

This is a dated rollout snapshot, not a live status page. Query
`GET https://api.aipowergrid.io/v1/status/network` and
`GET https://api.aipowergrid.io/v1/validator/capabilities` for current public
state.

## 2026-08-26 18:07 UTC

Core reported build `0d850e7341c365787bf2b0dd7011342ef33f09cf` and an
operational API/Redis pair.

| Validator signal | Value |
|---|---:|
| Registered active | 3 |
| Fresh heartbeat | 3 |
| Participating (24h) | 3 |
| Independently verified operators | 0 |
| Pending groups | 1 |
| Accepted groups | 3 |
| Disputed groups | 0 |
| Finalized groups | 92 |
| Completed assignments | 286 |
| Authoritative votes | 263 |
| Worker coverage | 4 |
| Model coverage | 3 |
| Reported software version | `0.1.0` (3 validators) |

The 23-count difference between completed assignments and authoritative votes
is an operational delivery signal, not proof of fraud. Core completed-result
replay and the node assignment journal are pending review in Core PRs #26/#27
and validator PR #10; none of that recovery code was deployed in this snapshot.

## Authority Flags

- Mode: `shared_quorum_preview`
- Validator economic effect: `none`
- Validator rewards: disabled
- Validator staking requirement: disabled
- Image fidelity assignments: disabled
- Video validation assignments: disabled
- Epoch roots: disabled
- Operator independence proven: false
- Quorum policy: 3 matching votes from 5 distinct registered validators
- Charging: allowlist mode, global charging disabled

Registration and distinct wallets do not establish independent control. These
three nodes remain first-party preview infrastructure until operators are
externally qualified under `PREVIEW_COHORT.md`.

## Network Context

Production reported 7 online workers and 10 online models. Every model was below
the target of three serving workers, so limited model redundancy remained an
active public advisory. Validator coverage was narrower than serving capacity
(4 workers and 3 models), which is why fair multi-model assignment rotation is
an explicit protocol gate rather than a cosmetic metric.

