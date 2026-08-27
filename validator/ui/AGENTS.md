# Local Operator UI

## Purpose And Ownership

`index.html`, `app.css`, and `app.js` implement the optional `aipg-validator app`
browser view. `logo.png` is the official worker logo. Assets ship in the Python
package and frozen binary; no CDN, remote font, or third-party script is loaded.

## Contracts

- Only the local app's fragment token authorizes controls and diagnostics. Store
  it in per-tab session storage, remove the fragment, and never place it in a
  request URL, diagnostic download, or external navigation.
- Enrollment requires the confirmation dialog. Dismissal, Escape, reload, and
  simply opening the page must never create an identity or start Grid traffic.
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
- Preserve the separate read-only dashboard. This UI ships in preview.12;
  native offline package checks do not replace live end-to-end qualification.

## Verification

Run `tests.test_operator_app`, the packaged `scripts/smoke-operator-app.py`, and
browser QA at desktop and narrow mobile widths. Exercise consent cancel/Escape,
repeat start/stop, invalid credentials, expired local session, error rendering,
diagnostic download, and no horizontal overflow.

## Child DOX Index

No child guides.
