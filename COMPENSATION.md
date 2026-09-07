# Operator Compensation

Status: node-app implementation in source, not yet released or production-live.
Core PR127 (`2d16a019`, migration `0039`) provides the default-off API. The
matching Console wallet page and full cross-repo rollout are still required.
No live campaign, budget or transfer is approved by this implementation.

## Operator Flow

1. Check compensation in the existing app. Approved pilot windows and finalized
   allocations come from Core. A campaign cap is not an earned balance.
2. For a positive allocation, select Set payout wallet. If no Console account
   is linked, use the existing account-link flow without replacing the node.
3. Open the fixed Console page and approve the exact destination with its wallet.
4. Back in the node app, review the amount and complete Base address, then
   explicitly confirm. The node signs only this earned allocation's consent.
5. Both signatures await independent maintainer destination review. Approved,
   pending, sent and manual-review payment states remain distinct.

Node participation does not require Google login. The optional account link
routes a private browser handoff; it is not payout ownership or independence
proof. Wallet setup requires separate wallet and node signatures. The node
signer is funds-less and is never silently selected as the payment recipient.

## Local Contract

`validator/compensation.py` reuses the official-Grid-only bounded transport and
existing configured identity. It does not enroll, rotate, start/stop a worker,
modify configuration, alter qualification or write an evidence journal.
Opening `/compensation.json` reads cached local state only. Explicit actions
query Core; pending wallet setup may be polled read-only every six seconds.
Restart recovers requests from Core after an explicit check. No signing text,
account/control-group identifiers, API keys, private keys, or signatures enter
the browser state or diagnostic download.

`/compensation` accepts only bounded refresh/start/inspect/cancel/confirm
commands under the same loopback Host, Origin and ephemeral-session guards as
existing controls. There is no arbitrary-message or transaction-signing API.
Actions serialize separately from normal validator execution. Outages and
unknown responses leave work/identity unchanged; stale or unavailable payment
data is not displayed as a current balance.

Confirmation requires an already displayed request/hash and a fresh matching
Core read. The client independently reconstructs the exact v1 EIP-191 message,
checks its canonical hash, node ID/local signer, Base chain, pinned AIPG token,
integer amount, account/campaign commitments and at-most-24-hour expiry.
Changing destination invalidates the old review. Reload, Escape, cancel and
polling never sign. A lost acknowledgement is recovered by reading the existing
request; a completed request does not cause another signature or transfer.

Amounts use integer base units and browser BigInt, never floating point.
External links are constructed only for the official Console request or a
validated BaseScan transaction hash. No server-supplied arbitrary URL is opened.

## Verification And Release

- `tests.test_compensation`: synthetic Core transport and actual EIP-191
  signatures, strict message checks, changed/expired consent, response loss,
  restart, bounds and non-signing actions. Not production or Core auth proof.
- `tests.test_operator_app`: real local HTTP authorization/origin/body guards
  and exclusion of private compensation data from diagnostics.
- `tests/compensation_browser.cjs`: Playwright with a temporary synthetic
  fixture at 320/390/1280px, exact decimal rendering, Escape/reload without
  signing, explicit confirmation, lost availability and no overflow. Set
  `VALIDATOR_TEST_PYTHON` to the repo environment; install Playwright externally.

Before public enablement, ship the matching Console page; run the complete
Core/PostgreSQL, Console login/wallet and native app journey; pass native package
and provenance checks; deploy migrations before code; and test a bounded canary.
Keep `VALIDATOR_COMPENSATION_OPERATOR_ENABLED=0` until that is complete. Payment
sending remains a separate approval and flag. Existing operators keep their
identities and qualification history throughout.
