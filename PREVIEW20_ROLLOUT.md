# Preview.20 Rollout

## Published And Verified

Immutable `v0.1.0-preview.20` was published at **2026-09-13T03:53:15Z** from
reviewed source `c73a284f155e86358f5348ab017747cd51d02e58`. It combines the
versioned token-limit correction with PR115's committed-empty evidence delivery
fix. The source suite ran 427 tests: 420 passed and seven skipped. The tested
source tree and merged release tree were compared with no differences.

Binary workflow `34736178270` passed four native builds, payload validation,
four clean installs and protected publication. Container workflow `34736178277`
passed qualification and protected publication. The sole maintainer approved
the protected environment; release protections were not disabled.

The downloaded nine-asset set passed exact archive layout, manifest, size and
checksum checks. All eight checksummed files passed GitHub provenance checks
pinned to the exact source, tag and release-binaries workflow, denying
self-hosted runners. These are build/provenance proofs, not model-fidelity
measurements or independent operator qualification.

| Artifact | SHA-256 |
| --- | --- |
| SHA256SUMS | `cd0b64d87e0a40508115c95c54a9a512bd640f28e69e71c2153ef18a49ab0391` |
| Release manifest | `5b62005f6e15d7c213129606de3e01b1f72d26a5b08ba013e70ff28c378a28f4` |
| Linux x64 archive | `a2dff51055a773521016f2303f8644220110418b43898031c58147bb98a76237` |
| Installed Linux x64 binary | `e94290ffa2134067fb1d532ce21c347262217560e788c55dc8d9547f269a34f4` |

Windows remains unsigned and macOS is not Developer ID signed or notarized.
This is an explicit preview, not a stable or platform-signed release.

## Production Admission And Owned Nodes

Core `d606e4d8` / Alembic `0042` admitted .20 at **03:57:06 UTC**. The drained,
compare-and-swap configuration update changed only the exact upgrade list,
preserving baseline .13 and upgrades .15-.19, qualification history, billing
and the worker-payout controls. Core/MCP recovered with eight workers and the
temporary generation/probe gate removed. No schema or runtime code changed.

All three first-party Linux nodes upgraded sequentially to the verified binary.
Each preflight checked the old release, archive/binary hashes and sizes, then
ran the exact version and offline decoder checks as the unprivileged service
user. Configuration, identities and stopped journal bytes were preserved.
Dead letters were neither erased nor revived. One pending assignment survived
the first switch. Active .20 registrations were confirmed at 03:58:46,
04:01:25 and 04:02:14 UTC.

Fresh signed reports independently verified after upgrade:

- `127694`: Qwen tool-chain, healthy, 03:58:50 UTC.
- `127695` and `127699`: DeepSeek 32K-context, healthy, 04:11:09 and 04:11:47 UTC,
  from two owned nodes.
- `127701`: SmolLM multistep reasoning, failed, 04:20:43 UTC, from the third
  owned node. The failure was preserved; it is not a cheating determination.

Independent recovery of signer addresses, canonical envelope hashes and
assignment/nonce/evidence/target bindings passed. No correlated credit,
reservation or worker-ledger rows existed. These ordinary reports prove live
delivery, not the outstanding v2 or committed-empty lane-specific canaries.

## Controlled Lane Selection

Normal random assignment and the per-worker/model cooldown can delay one
specific release test. A bounded first-party canary temporarily limits one
owned node's advertised capabilities to its supported `text.token_limit.v2`.
It uses the normal heartbeat and assignment APIs; it cannot choose the target,
create nonces, bypass cooldowns, execute a probe or submit evidence itself.

The helper restores the complete capability list and starts the exact released
binary to journal, execute, score and sign the issued assignment. It preserves
the stopped journal/configuration, polls at most once per minute for twelve
attempts, and has a separate service-restart cleanup hook. Seven local helper
tests cover selection, time bounds, existing work and recovery failures.
This is controlled release testing, not an unbiased workload sample.

The first bounded attempt did not obtain v2: another node created a different
capability group in the next eligible slot. It was deliberately interrupted
after seven minutes, and both API restoration and service cleanup succeeded.
The node was active again with all fourteen original capabilities. No selected
assignment, probe or report is claimed from that attempt. Lane-specific live
results remain pending. No result is declared healthy by the selector or
inferred from the published unit tests.

## Remaining Gates

- Verify fresh v2 and committed-empty reports end to end; preserve legitimate
  failures and unavailable results instead of making the canary pass.
- Promote the combined public upgrade once qualified; preserve each operator's
  identity, configuration and journal. Never overwrite .19 assets.
- Finalize practical operator-control reviews and obtain real payout consent.
  Uptime already observed does not need to restart merely because review is late.
- Approve the exact capped compensation campaign separately. Its backend stays
  disabled; worker payouts are a different rail.

Media, shadow observation, compensation collection/sending and worker penalty
authority remain off. No campaign was created by this rollout.
