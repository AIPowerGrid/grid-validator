# App Updates

Published in preview.17 from reviewed commit `aa35fa0a`; public download
promotion remains separate. Existing preview.13/.16 downloads do not acquire
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

Before promotion: pass the current native matrix, admit the exact release in
Core's supported-version overlap without resetting qualification, test an owned registered
node through a real released-version upgrade and preserved pending evidence,
confirm recovery after interrupted startup, and run the bounded production pilot.
Do not change public download recommendations or operator qualification clocks
merely because this implementation is merged.

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
