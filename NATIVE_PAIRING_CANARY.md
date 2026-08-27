# Native Pairing Qualification

Status: **Linux ARM64 live candidate run passed; Windows pairing remains open**.
On 2026-08-27, the actual unpublished `35b4e045` Linux binary completed the
procedure against production Core and Console, with three verified reports and
complete node/key retirement. The separate Console account used real wallet
authentication; an automated test driver entered its code through the real
hidden TTY review. This proves neither human desktop interaction nor independent
control. Public release and activation remain separate gates; see
[PRODUCTION_BASELINE.md](PRODUCTION_BASELINE.md). This is a maintainer procedure, not instructions for
Donli or other ordinary operators. They should use [QUICKSTART.md](QUICKSTART.md).

`scripts/native-pairing-canary.py` exercises an actual candidate binary through
its authenticated local app and the official HTTPS Core. It does not replace
Core, mock approval in a live run, weaken TLS, write production configuration,
or deploy anything. Existing [published Windows proof](NATIVE_LIVE_CANARY.md)
covers bad credentials, network faults and binary upgrades; this additional
run focuses on account pairing and continued useful participation.

## Prerequisites

- A controlled Windows x64 or Linux x64/ARM64 test host with Python, the frozen
  repo dependencies, and authenticated read-only GitHub CLI access. Windows
  and Linux are separate runs; the host has a Python harness, while the app
  under test is the frozen executable, not a source substitute.
- A successful `Release Binaries` workflow run from reviewed `master`, with
  its exact 40-character source SHA. Pull-request/fork builds, wrong workflows,
  incomplete runs and mismatched archives are rejected before execution.
- Reviewed pilot-capable Core deployed dark, its exact SHA, and an unfunded
  test human account accessible in Console. Global pairing and all validator
  economics must remain off. Follow [ACCOUNT_PAIRING.md](ACCOUNT_PAIRING.md)
  for the separately controlled, expiring pilot; this script cannot enable it.
- A fresh private workspace outside any public artifact directory. No existing
  node configuration or identity may be reused by this destructive test.

The script downloads `aipg-validator-release-payload` from the specified run,
checks GitHub workflow/source/result metadata, and verifies the manifest and
archive before extraction. These are **build-only CI artifacts, not signed
release artifacts**. The report records `release_provenance: false`; a green
candidate run does not publish or attest a public release.

## Run

From the reviewed validator checkout, install the locked dependencies:

```sh
uv sync --frozen
```

Run with concrete reviewed values, not the placeholders below:

```sh
uv run --frozen python scripts/native-pairing-canary.py run \
  --run-id BUILD_RUN_ID --commit EXACT_NODE_SOURCE_SHA \
  --core-commit EXACT_DEPLOYED_CORE_SHA \
  --workspace /private/path/new-pairing-run \
  --report /separate/path/pairing-report.json \
  --minutes 75 --approve-live-canary
```

Use the equivalent Windows paths in PowerShell. This command is for the
maintainer's test host only; it is not a new operator requirement.

Opening/cancelling setup must create no identity. Explicit test consent then
enrolls a fresh dedicated node and starts its ordinary unpaid assignment loop.
The report emits only its public `val_*` ID. Within ten minutes, the maintainer
must privately resolve that exact registration and admit its account plus the
unfunded test human through the scoped pilot. Do not infer identity from a
timestamp, admit unrelated operators, print account UUIDs, or enable global
pairing as a shortcut. Admission waiting is not a passing test.

After cancellation and an accepted-evidence round, the harness stops its node
while testing account visibility. It performs two separate pairings:

1. **Node removal:** approve in Console, explicitly compare the code locally,
   recover the committed link after restarting the app and discarding its
   confirmation response, then remove that exact association from the node.
2. **Owner removal:** repeat with fresh request-specific consent; once the
   harness reports `waiting_for_console_owner_removal`, remove the exact node
   association from the test human's Console account. The harness only polls
   during that step; it must observe the removal before continuing.

For each phase the private workspace contains `review-request.json`, written
with POSIX mode `0600` or the existing protected Windows owner-only DACL. It
contains the exact official Console approval URL and public node ID. Open that
URL privately, authenticate as the admitted unfunded test human, inspect the
node and approve. Do not post this file or its URL. Then on the same test host:

```sh
uv run --frozen python scripts/native-pairing-canary.py review \
  --workspace /private/path/new-pairing-run
```

Enter the comparison code shown by Console at the hidden TTY prompt. Never pass
it as a command-line argument or public workflow input. This writes an
owner-only response bound to this phase's random ticket and pairing ID.
Polling alone cannot confirm; a stale phase, different request or wrong code
cannot authorize a signature. A restarted app must first obtain a fresh local
review. Each approval/removal has a nine-minute maximum; the overall workflow
uses the selected 30/75-minute budget plus bounded setup and cleanup I/O.

This version is deliberately a supervised local-host harness, not an unattended
GitHub Actions live workflow. Do not upload its private workspace to bridge
approval to a hosted runner. The normal native-build CI runs only its offline
tests, with no production enrollment or account linking.

## Passing Evidence And Cleanup

A passing runtime report requires accepted signed evidence before and after
pairing, unchanged node ID/config bytes, explicit consent for both requests,
restart/recovery and both removal paths, and redacted diagnostics. No assignment
within the time budget is a failure/incomplete proof, not a reason to change
cooldowns or fabricate work.

Finally, the harness attempts to cancel/remove any remaining test pairing,
self-suspend the generated registration, and revoke only that account's
dedicated API keys using fresh wallet proof. It verifies revoked-key rejection.
Cleanup runs after ordinary failures, including a lost request-creation response.
Failed cleanup makes the run fail; retain the private test state for recovery
and follow up using the public node ID. Do not interrupt or kill a live run
after enrollment merely because it is waiting. Forced process/host termination
cannot guarantee cleanup.

Upload **only the explicit report file**, never a wildcard over the workspace.
It contains fixed checks, version/source/build metadata, public node ID,
accepted counts and cleanup status. It omits keys, account IDs, approval URLs,
pairing IDs, codes, local session tokens and raw child output.

Before calling the platform qualified, independently verify Core's stored
signatures, exact associations/removal, suspended status, key revocation and
unchanged balances, identities, payout wallets, independence reviews and
economic ledgers. Record exact candidate, Core and Console versions and the
limitations in [PRODUCTION_BASELINE.md](PRODUCTION_BASELINE.md). The harness's
`passed` flag alone does not prove those database invariants, a human desktop
journey, published release provenance or independent control.

Remove test links before the pilot expires, then clear the pilot separately.
Expiry blocks access without deleting links; if cleanup is interrupted, renew
only the same scoped test identities for reviewed cleanup. Do not delete
production tables or merge accounts to recover a canary.
