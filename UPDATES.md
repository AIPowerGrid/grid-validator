# App Updates

Introduced in preview.17 from reviewed commit `aa35fa0a`; the public download
page now recommends preview.18 (`fef5e924`). Existing preview.13/.16 downloads do not acquire
this updater retroactively. Their first
upgrade must preserve the existing configuration and validator ID.

## Operator Flow

Check for updates, then confirm Update and restart for the displayed version.
Preview consent discloses missing Windows platform signing/macOS notarization.
Cancel, Escape, page load and cached polling do not start installation.
Source builds retain the external release link and package-manager workflow.

The app verifies GitHub workflow provenance, manifest/source/tag bindings,
archive digest and bounded safe extraction. A bounded credential-free child
does preparation; a separate candidate self-test checks its version, bundled
trust roots and UI assets. Preparation failure leaves the running app intact.

Only after preparation succeeds does the old app stop its own validator loop
and release its app lock. The candidate reuses the old loopback port and
ephemeral session token, passed only through its private startup pipe. The
bootstrap checks that server before committing the version choice. The existing
browser tab reconnects and reloads the new assets when the version changes;
`--no-browser` does not need a second private URL. A previously running app-owned
loop resumes; a stopped loop stays stopped. Tokens are never saved in version
selection files. A failed update may reopen the old app with a fresh local URL.
Unavailable Grid service is not mistaken for a failed local app installation.

## Storage And Recovery

Version slots live beside the selected config in `<config-name>.updates/`.
The original executable is retained, including on Windows where Explorer/menu
processes may still hold it open. Config and queued evidence are never copied,
replaced, re-enrolled or cleared. The same config path and working directory
follow the new app; runtime environment overrides remain effective.

`active.json` is owner-protected and atomically replaced. A pending transaction
selects the previous version after interruption. The new process validates its
own executable/tag and the nonce-bound pipe before committing. Startup failure
stops only the candidate process tree, restores the previous choice and reopens
the old app. A broken/digest-mismatched saved selection cannot execute; the
original installed app remains usable. Previous slots are retained for recovery.

Interactive app/menu launches follow a newer committed selection. Direct
`run`, systemd, container and other externally managed entrypoints do not change
binary or service state. This updater never adopts external PIDs. A newer
manually installed binary must not redirect into an older saved selection.

## Verification Boundary

Source tests cover private paths, interrupted atomic writes, pending fallback,
consent binding, failed preparation, owned child startup/commit/rollback and
unchanged synthetic config/journal bytes. The source process fixture simulates
frozen identity; it is not native or live-network evidence.

`scripts/smoke-update-handoff.py` builds disposable frozen preview.0 and
preview.17 fixtures. It tests loopback readiness, commit, same-session restart,
wrong-version and post-readiness write-failure rollback, reopening the original
bootstrap into the selected app, and interrupted-selection fallback on each
native CI platform. No fixture binary is published. A successful macOS
run does not establish Windows/Linux qualification or live registered-node
upgrade continuity. The separately tested real published-release provenance
download is preparation evidence, not the complete update journey.

Before preview download promotion: pass the current native matrix, admit the
exact release in Core's supported-version overlap without resetting
qualification, test an owned registered node through a real released-version
upgrade and preserved pending evidence, and confirm interrupted-startup
recovery. A merged implementation alone is not sufficient.

The seven-day production pilot and approved compensation are separate gates for
supported paid beta, not prerequisites for recommending a tested preview
updater. Preview promotion never resets qualification or activates economic or
worker-penalty authority. See `SUPPORTED_BETA.md` for the remaining delivery order.

## September 7 Release Checkpoint

Release workflow `34136400434` passed all four native build, frozen handoff and
clean-install lanes and published preview.17 at 15:15:53 UTC. All downloaded
assets pass the exact release verifier; the manifest passes both pinned GitHub
attestation verification and the updater's Sigstore verifier. Core `3714a927`
admits preview.17 alongside .13/.15/.16; identity/qualification/review digests
are unchanged. Shadow observation and validator economics remain off.

One owned Linux systemd node upgraded from the published preview.15 binary to
the published preview.17 binary at 15:31:39 UTC. Its config and complete durable
journal were preserved before restart, with the same registered ID afterward.
One fresh report at 15:35:53 UTC passed independent signature recovery and
assignment/nonce/evidence/worker binding checks against production records.
This is an externally managed service upgrade, not an app-controlled update.
There were no pending signed reports at cutover, so this does not prove their
live replay. A first attempt rolled back after the harness's public-status
request failed; the restored service stayed healthy. The corrected request
passed preflight before the successful repeat. Full evidence and remaining
gates are recorded in `ROLLOUT_2026_09.md`.

A second owned Linux node ran a bounded pending-report canary until 16:11:49
UTC. No accepted report arrived in 25 minutes, so no response-loss or upgrade
replay was exercised. Cleanup restored its original preview.15 service, removed
the temporary localhost proxy override and stopped the failsafe timer; all three
states were independently checked afterward. The result is inconclusive, not
a recovery pass or an observed updater failure. Re-run against available real
assignments without changing production cadence or resetting qualification.

A repeat on that same owned node passed at 17:04:11 UTC. It allowed one full
normal assignment cadence without changing Core policy. Core accepted a real
signed report, the local fault proxy discarded its HTTP response, and the old
node retained the pending envelope. The published .17 binary preserved the
same configuration/journal and retried while delivery was still held. After
release, Core returned `duplicate` for the same committed record and the node
drained the exact pending envelope. One blocked and one released retry were
observed. A separate read-only Core audit verified one record, its signature,
assignment/nonce/evidence/worker bindings and exact commitment; the probe had
zero worker-ledger, credit-ledger and reservation rows. The .17 service is
active, its original config hash is unchanged, and the temporary proxy and
rollback watchdog are removed. This is a first-party Linux service test, not
a live human desktop one-click test, fleet-wide reliability estimate or paid
pilot completion. The earlier inconclusive run remains part of the record.
