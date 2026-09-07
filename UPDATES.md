# App Updates

Implementation in progress, not a published operator release. Existing
preview.13/.16 downloads do not acquire this updater retroactively. Their first
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
