# Optional Account Pairing

Status: merged, native-build tested, unreleased client. **Not part of preview.13
and not enabled in production.** [Core PR #58](https://github.com/AIPowerGrid/grid-core/pull/58)
(`407f2984` / Alembic `0030`) and
[Console PR #21](https://github.com/AIPowerGrid/grid-frontend/pull/21) (`db301013`)
were deployed dark on 2026-08-27. The pairing tables now retain a completed,
unlinked disposable test record; no active association remains.
Keep `VALIDATOR_PAIRING_ENABLED=0` until the cross-repo rollout is verified.
Core's separate [scoped pilot change](https://github.com/AIPowerGrid/grid-core/pull/60)
adds a default-empty, expiring account allowlist for native qualification.
Its immutable `f51875ce` release passed the production-backup scratch-restore
and schema proof at 20:59 UTC, then deployed dark at 21:07 UTC on 2026-08-27.
An expiring two-account pilot subsequently passed the Linux ARM64 native
pairing lifecycle against production and was removed after cleanup. Its
allowlist is empty again; global pairing and economic features stayed off.
Windows pairing, human desktop proof and client release remain open; see
[PRODUCTION_BASELINE.md](PRODUCTION_BASELINE.md).

## What It Means

Running a validator does not require Google or GitHub. Automatic enrollment
already creates a dedicated node identity and validator-scoped API key locally.
Optional pairing lets an existing human account see that node's ID, signer,
version, status and heartbeat in its private Console list.

It does not merge accounts, change either wallet, move balances, grant login or
recovery rights, change node credentials, or establish independent control.
It does not grant rewards, stake, routing authority or slashing power. Those
features stay off. Losing a node key still requires the existing recovery path.

## Operator Flow

1. Set up and start the node once so Core has its signed registration. The
   node may keep running while pairing. Self-suspended registrations can pair;
   maintainer-revoked registrations cannot.
2. In the local app, select **Link account**, review the notice and explicitly
   create a ten-minute link request. No request or external page opens merely
   because the app starts.
3. Select **Open Console**. Sign in with the existing account using Google or
   a wallet and explicitly approve the displayed node. Recent account proof is
   required; a static API key cannot approve. No funded wallet key is requested.
4. Compare the Console code with the local app's code. Select **Compare code
   and confirm**, check the code again and explicitly confirm the match. The
   local node signs the exact verified account-visibility payload using its
   dedicated signer. Polling, reloading, Escape and Cancel do not sign.
5. The local app displays **Account linked** only after querying the current
   association. The human's Console lists the linked node privately.

The initial client supports the official `https://api.aipowergrid.io` Grid and
canonical Console approval origin. Other Grid configurations are not rewritten;
pairing reports unsupported while ordinary node operation remains unchanged.

## Cancel, Remove And Recover

- **Cancel request** cancels an unconfirmed attempt without signing. It cannot
  undo a committed association. If an attempt expired, start a new request.
- **Check link** queries Core. Pending attempts then use bounded read-only
  polling; polling stops on error, expiry or completion. App restart requires
  an explicit check; browser reload may resume its existing pending check.
- A timeout is not proof that a confirmation failed to commit. Check the link
  before starting again. A committed association survives the request's expiry.
- **Remove account link** has its own confirmation. The node signs only the
  current association, not a replacement created since the dialog opened.
  Removing it does not stop the validator or revoke keys. The human account
  can also remove the exact association after fresh authentication in Console.
- An expired/mismatched review requires a fresh check and confirmation. Correct
  an inaccurate system clock before retrying freshness errors.
- Exit prevents new pairing requests and signatures, but cannot retract an
  already submitted request. Reopen and check Core to learn its outcome.
- A missing/disabled API, revoked credentials or invalid response shows a fixed
  actionable error. Restore existing configuration; do not generate extra keys
  or replace the node identity to troubleshoot.

## Security Contract

The loopback server requires the existing private local session token and exact
Host/Origin checks. The token is never placed in an external URL. Local actions
accept exact bounded fields; they do not accept arbitrary payloads, destinations,
keys or account IDs. Pairing actions serialize separately from runtime controls.

The client checks the exact Core payload schema, purpose, audience, registered
validator ID, local signer, account UUID syntax, visibility-only permissions,
comparison code and expiry. The registered ID and signer are independently
matched locally; **account UUID ownership is verified by Core**, not inferred
from a public wallet address by this client.
Up to thirty seconds of local clock lag is tolerated when checking newly
issued Core timestamps; already expired payloads still fail and Core enforces
the original ten-minute deadline without extending it.

Confirmation requires a previously displayed local review and a fresh Core read
with the same payload hash/code/attempt. Unlink consent binds the immutable
association; its eventual signature also covers Core's fresh timestamps. Both
use EIP-191 over sorted-key compact JSON, matching Core's versioned contract.

Transport is HTTPS-only, ignores environment proxies, follows no redirects,
accepts unencoded JSON only, rejects duplicate keys and caps each reply at 16 KiB.
Requests use a maximum ten-second I/O timeout and a thirty-second overall action
budget checked between requests/chunks; an in-flight read may finish after that
budget. No response body or signing material is rendered as an error.

No configuration is written or identity generated by pairing. Fresh config
reads respect explicit environment overrides. The local UI receives only safe
display state, an opaque attempt ID and a review hash, never raw payloads,
account IDs, credentials or signatures. Pairing metadata is excluded from
downloadable diagnostics, public health and scorecards.

## Verification And Rollout

Local verification on 2026-08-27 includes real
EIP-191 recovery against synthetic Core transport, response-loss recovery,
stale/expired reviews, exact removal, malformed payloads, HTTP origin/body guards
and runtime isolation. A local macOS ARM64 frozen binary passes the packaged app
smoke. These are **not** proof of a Windows/Linux live account-pairing journey.

Five opt-in `tests.test_core_pairing_integration` tests pass against Core PR #58
commit `0e66da57`, using in-memory SQLite and actual HTTP handlers. Each fixture
authenticates generated wallets through Core's SIWE challenge/verify flow and
registers a node with a real signature and scoped API key. Approval requires
fresh proof; replayed SIWE, stale proof, app tokens, wrong owners and revoked
node keys are rejected. Link/removal preserves non-pairing tables except normal
authentication telemetry. A lost response after a real commit is recoverable
after client restart. The nonce store and ASGI transport remain local fixtures;
this does not prove Redis or PostgreSQL concurrency.

Run that lane from this repo with a Core dependency Python environment:

```sh
VALIDATOR_CORE_SOURCE=/path/to/reviewed/grid-core \
  /path/to/core-venv/bin/python -m unittest tests.test_core_pairing_integration -v
```

One additional `tests.test_console_pairing_integration` test passes against
Console PR #21 commit `8fca3356` and the same Core revision. It starts the built
Next server plus loopback Core, performs the actual Console wallet callback,
Core SIWE verification and service binding, and obtains real Auth.js session
cookies. It proves unauthenticated and cross-origin rejection, approval without
auto-confirmation, explicit local consent, private listing and owner removal.
All identities are disposable and no production endpoints or funds are used.
The Console checkout must have a current production build and no `.env*` files
loaded by Next in production mode; its subprocess receives only an allowlisted
test environment. Run both modules together:

```sh
VALIDATOR_CORE_SOURCE=/path/to/reviewed/grid-core \
VALIDATOR_CONSOLE_SOURCE=/path/to/built/grid-frontend \
  /path/to/core-venv/bin/python -m unittest \
  tests.test_core_pairing_integration tests.test_console_pairing_integration -v
```

Ordinary node CI explicitly skips these six cross-repo tests when the required
source paths are absent; it must not report them as executed. No Core or Console
dependency is added to the binary. Google OAuth, wallet-extension interaction,
HTTPS deployment and Windows/Linux live operation still require separate proof.

Browser QA uses `python -m tests.pairing_app_fixture`. It creates temporary
synthetic credentials, never calls production and accepts mock approval/expiry/
outage commands on stdin. Do not use that fixture to claim live Core enforcement.
The source UI was checked at 320/390/1280px: consent cancel, approval without
auto-signing, reload, explicit code confirmation, removal cancel/confirm,
outage recovery and expiry. No horizontal overflow was observed.

### Scoped Qualification

The maintainer-only [native pairing canary](NATIVE_PAIRING_CANARY.md) exercises
the actual Windows/Linux candidate through its loopback app and official HTTPS
Core. It requires explicit Console approval and local comparison-code entry,
not synthetic approval. Its offline safety tests are implemented; no native live
pairing run has passed yet. It does not deploy Core or configure the pilot.

After deploying the reviewed pilot-capable Core dark, the maintainer may keep
global pairing off and designate only unfunded test node and human accounts in
`VALIDATOR_PAIRING_CANARY_ACCOUNTS`, with an explicit timezone-aware
`VALIDATOR_PAIRING_CANARY_UNTIL`. Core caps the list at ten canonical accounts
and the deadline at 24 hours ahead on startup. Both accounts must qualify;
existing proofs, local consent and signatures are unchanged. No node-client
configuration or protocol change is needed. Public capabilities still advertise
pairing false, not the private pilot's membership or deadline.

Remove test links before expiry, verify unchanged credentials/balances/wallets
and ongoing evidence, then clear the pilot. Expiry blocks access without
deleting associations; deliberately renew the same scoped pilot if authenticated
cleanup must be retried. Never use a global activation or direct database edits
as a shortcut around an incomplete canary. Pilot availability is not a public
release or human desktop proof.

### Before Release/Activation

1. Review the node, Console and Core changes together; verify the real Core
   signature/transaction path and account-bound approval with both clients.
2. Pass all native build/clean-install checks and complete Windows/Linux live
   registration, heartbeat, assignment, probe and accepted-evidence journeys.
   Include linking, cancellation, restart, upgrade and response-loss recovery.
3. Apply migration `0030` and deploy Core dark. Deploy the matching Console and
   publish reviewed immutable node artifacts before enabling the feature.
4. Run a scoped supervised association/removal canary with non-funded test identities.
   Check unchanged credentials, balances, wallets, independence reviews and
   ongoing evidence submission. Only then enable optional pairing publicly.
5. Roll back by disabling the pairing flag and clearing the pilot allowlist. Preserve tables and node config;
   revert application versions if needed. Do not delete keys or association
   tables as a routine rollback.

Deployment progress at 19:06 UTC on 2026-08-27: cross-repo review/merge,
four-platform build/clean-install checks, Core backup/restore/migration and dark
Console deployment have passed. Build-only source `5de518b0` passed run
[33105488747](https://github.com/AIPowerGrid/grid-validator/actions/runs/33105488747)
and downloaded payload verification; it is not a new public release. The
deployed API advertises pairing disabled and returns 503. Console rejects
anonymous node-list access and sends login, framing and referrer protections.
These checks do not replace the live platform pairing and supervised canary
requirements above. See [PRODUCTION_BASELINE.md](PRODUCTION_BASELINE.md) for
exact deployment and rollback references.

Five independently controlled operators and 72-hour qualification remain
separate required work. Account linking does not certify either condition.
