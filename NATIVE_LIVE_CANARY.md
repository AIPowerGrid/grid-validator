# Native Windows Live Canary

Preview.14 run `33983090757` failed fresh app setup with `app_state_timeout`;
its generated key was revoked and no validator was registered. The harness
now expects the intended automatic startup, reports only allowlisted app
errors, and records explicit upgrade versions. This is not a passing .14 proof.

Current status: preview.15 passed protected run
[33984877376](https://github.com/AIPowerGrid/grid-validator/actions/runs/33984877376)
on September 5 against Core `6f12de6f`: fresh automatic enrollment, one accepted
signature-verified report, preserved-identity upgrade, actual outage/recovery,
signed suspension and revocation of its one generated key. Independent database
checks confirmed suspension and zero payout/reservation rows for its probes.
Run `33984552555` overlapped a Core restart and is invalid qualification evidence;
see the rollout record. Freeze Core deployments during this live test.

Historical status: preview.13 passed the protected Windows live run
[33110290699](https://github.com/AIPowerGrid/grid-validator/actions/runs/33110290699)
on 2026-08-27, including two accepted signed reports, outage/recovery and full
test-identity retirement. See [PRODUCTION_BASELINE.md](PRODUCTION_BASELINE.md)
for exact revisions and read-only Core verification. This workflow tests the
actual published local app against the unpaid text preview; it does not publish
a release or enable any Core feature. Human desktop onboarding remains separate.

## Boundaries

- Only manual dispatch on reviewed `master`, with explicit unpaid-canary consent
  and the existing owner-approved `validator-release` environment. No pull
  request, push, schedule or public contribution can start live work.
- The hosted Windows x64 runner now targets verified immutable preview.13 and
  preview.15 archives; the earlier passing result tested preview.12 to .13.
  Both archives and manifests require GitHub provenance
  bound to the exact tag, source SHA, release workflow and hosted builder before
  extraction. The harness never builds a substitute binary.
- Enrollment creates one fresh, unfunded, first-party account and signer. The
  existing local app obtains explicit enrollment consent through its control
  API. No existing operator config, account, payout wallet, or identity is used.
- The binary does not receive the workflow token, environment credentials,
  Python injection paths or proxy settings. Harness Python is present on the
  runner; this is not a claim that the runner has no Python installed.
- Only ordinary unpaid Grid-issued text assignments may execute. No public
  inference request, custom target, private corpus, paid/blind audit, economic
  effect, media assignment, pairing activation or independence review is added.
- Results are first-party runtime evidence, not independent quorum. Windows
  Server on a hosted runner and HTTP-driven app controls do not prove a human's
  Windows 10/11 double-click, browser or wallet-extension experience.

## What It Tests

1. Exact published versions and protected local-app access.
2. Cancelled setup creates no identity; opening the app does not enroll.
3. Explicit app enrollment, owner-only Windows DACL and idempotent repeat setup.
4. Registration, acknowledged heartbeat and at least one Core-accepted signed
   report, with zero pending/dead entries. A healthy worker verdict is not
   required: accepting valid failure evidence is also correct protocol behavior.
5. Redacted diagnostics, stop/start and whole app restart with stable identity.
6. Invalid credentials fail without changing config.
7. Preview.13 to preview.15 existing-identity registration using both verified
   binaries; this is binary-switch proof, not an OS installer-upgrade UI test.
8. An outbound firewall block for only the tested executable produces
   `grid_unavailable`; removing it restores an acknowledged heartbeat on the
   same identity and completes a round with no pending/dead entries. The
   disposable runner's firewall profiles are temporarily
   enabled for this check, then restored exactly; only the uniquely named test
   rule is removed. No production or operator-host firewall is changed.
9. Signed suspension and fresh exact-purpose SIWE proof to revoke only the
   generated account's dedicated keys. Unexpected owners/keys fail closed.
   The revoked key must fail authentication. Cleanup must succeed for the
   complete run to pass.

## Running And Reviewing

Choose **Native Windows Live Canary** in GitHub Actions, select `master`, confirm
the unpaid first-party test, and choose a bounded 10, 30 or 75 minute assignment
window. Approve its protected environment only after checking the source SHA.
No credentials are supplied as workflow inputs or repository secrets.

The default is ten minutes. Core's per-worker/model cooldown can leave that
window without work; that is an incomplete proof, never a successful run. A
longer deliberate window can be used without changing assignment policy or
creating artificial work. Do not cancel after enrollment merely because the
node is waiting; allow its retirement path to finish.

Only `validator-canary-report.json` is uploaded. It includes version/source,
public validator ID, fixed check labels, accepted count and cleanup status.
Never upload the private config, journal, local app URL, raw stdout/stderr,
account tokens, challenges, responses or signatures. Failed cleanup requires
maintainer follow-up using the reported public node ID; do not describe the
run as fully retired until verified.

After a run, independently query Core for the reported node ID: verify stored
signatures/assignment authority, suspended status and no economic ledger or
reservation entries for its probe jobs. Record the exact release/workflow/Core
revisions and limitations in `PRODUCTION_BASELINE.md`. Human Windows onboarding,
live account pairing, independent operators and 72-hour qualification remain
separate requirements.
