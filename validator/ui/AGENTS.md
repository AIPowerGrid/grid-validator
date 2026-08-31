# Local Operator UI

## Purpose And Ownership

`index.html`, `app.css`, and `app.js` implement the optional `aipg-validator app`
browser view. `logo.png` is the official worker logo. Assets ship in the Python
package and frozen binary; no CDN, remote font, or third-party script is loaded.

## Contracts

- Only the local app's fragment token authorizes controls and diagnostics. Store
  it in per-tab session storage, remove the fragment, and never place it in a
  request URL, diagnostic download, or external navigation.
- Enrollment requires the confirmation dialog. Confirmed setup creates the
  dedicated identity and starts the normal validator loop so the five-step
  setup check can observe registration, heartbeat, assignments, and accepted
  evidence. Dismissal, Escape, reload, and simply opening the page must never
  create an identity or start Grid traffic.
- Render structured state with textContent, not HTML interpolation. Do not
  display raw logs, server errors, private keys, API keys, or challenge material.
- Heartbeats mean Grid acknowledgement. Accepted evidence counts only actual
  submissions acknowledged during this app session, not assignments or verdicts.
  Zero assignments is not a worker failure or evidence of completed validation.
- Stop affects the owned local process only. It does not unlink a wallet, revoke
  a key, suspend registration, or delete durable assignments/evidence.
  Exit app additionally closes the local server after stopping its child.
- Keep unavailable/error states actionable. Disable controls when the app
  session is unavailable; keep status and controls usable at mobile widths.
  Surface a newer verified release, gross clock drift, and a non-empty dead
  evidence queue without exposing server text or recovery contents.
- Preserve the separate read-only dashboard. This UI ships in preview.12;
  native offline package checks do not replace live end-to-end qualification.
- Existing-account linking is newer, unreleased work. Require explicit start,
  separate Console approval, a displayed comparison code, and a second local
  confirmation. Polls, reload, dialog opening, Escape and cancellation never
  sign. Capture the reviewed pairing ID/hash/code when opening confirmation;
  never replace them with later poll results at submit time.
- Opening the app reads cached local pairing state only. Core reads begin on
  explicit Check link/start; pending/approved attempts may resume read-only
  polling no faster than every six seconds. Stop polling on expiry/error/linked,
  and while a consent dialog is open. Never automatically open external pages.
  Only the canonical HTTPS Console approval URL may be rendered as a link.
- Removal requires its own confirmation and affects only the exact account
  association, not runtime, credentials, evidence, payout wallets or trust.
  Retry/restart queries Core's current association before attempting another
  confirmation. Do not interpret a failed HTTP reply as proof of no commit.

## Verification

Run `tests.test_operator_app`, the packaged `scripts/smoke-operator-app.py`, and
browser QA at desktop and narrow mobile widths. Exercise consent cancel/Escape,
repeat start/stop, invalid credentials, expired local session, error rendering,
diagnostic download, and no horizontal overflow.
For linking, run `python -m tests.pairing_app_fixture` with synthetic credentials;
its stdin controls mock approval/expiry/outage. Test explicit confirmation,
cancel, reload, removal and recovery at 320/390/1280px. This does not replace
real Core/Console/native-host integration or live operator qualification.

## Child DOX Index

No child guides.
