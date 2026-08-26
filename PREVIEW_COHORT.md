# Validator Preview Cohort

AI Power Grid is recruiting 5-10 independently operated nodes for the first
validator preview. The purpose of this cohort is to prove that the software,
assignment lifecycle, and shared 3-of-5 evidence flow work across unrelated
operators and networks.

This is distributed testing, not decentralized economic validation. Preview
evidence does not change worker routing, strikes, payouts, or rewards. There is
no validator staking, slashing, or compensation in this cohort.

## Who Should Join

An operator should have:

- a Linux, macOS, or Windows machine that can stay online;
- a stable internet connection; no GPU is required;
- a Grid account with a dedicated validator API key;
- a dedicated signing wallet linked to that same Grid account; and
- enough familiarity with a terminal to run the health check and share logs
  with secrets removed.

One organization or person counts as one independent operator, regardless of
how many nodes they run. Multiple nodes controlled by the same operator do not
increase quorum weight.

Independence means separate practical control of the validator key, host, and
operating decisions. A second wallet, process, VM, cloud account, or family
member acting under the same operational control is not a second operator.
Operators must disclose common control privately to maintainers; Core records
only an opaque group, never the operator's name, email, IP, hostname, or review
notes.

## Join

1. Join the [AI Power Grid Discord](https://discord.gg/W9D8j6HCtC).
2. Ask to join the **validator preview cohort** and include only:
   - operating system and CPU architecture;
   - country or broad region;
   - expected online hours; and
   - whether the network is residential, datacenter, or cloud hosted.
3. Do not post API keys, private keys, signatures, account IDs, full wallet
   addresses, assignment payloads, prompts, or worker responses.
4. Wait for enrollment approval and a dedicated scoped validator key before
   running an assignment probe. Production Core supports shared quorum, but
   public binary distribution and open enrollment are still gated. Source
   installation checks may be performed with `aipg-validator check --no-probe`.

## Qualification Run

After the preview release and matching Core version are live:

```bash
aipg-validator init
aipg-validator check --no-probe
aipg-validator dashboard
aipg-validator check
```

The operator should then run the node continuously for at least 72 hours:

```bash
aipg-validator run
```

After enrollment, a maintainer places the registration into candidate status.
Core samples at most one qualifying heartbeat every five minutes. Verification
requires at least 72 hours, at least 80% sample coverage, a fresh heartbeat, and
a maintainer review. A verified review expires after 30 days by default and
must be renewed; operators cannot self-certify through the node or API.

The cohort is proven only when Core reports at least five recently active,
verified independent operator groups and real shared groups receive at least
three reviewed independent votes. The public status exposes aggregate verified
and participating counts but no group identifiers. A successful install,
registration, wallet, heartbeat, or ordinary 3-of-5 registration quorum alone
does not prove independence.

The 72-hour run qualifies basic operation and control separation. It does not
prove every model claim, authorize rewards, or make subjective evidence
slashable.

## Report Problems

Share the node version, platform, UTC timestamp, command that failed, and a
short redacted log excerpt. Remove secrets and the evidence fields listed
above. Report suspected security issues privately using the process in
[`SECURITY.md`](SECURITY.md), not in Discord or a public issue.

## Exit And Revocation

Run `aipg-validator suspend` before stopping the process or service to leave the
cohort cleanly. A later `aipg-validator check --no-probe` submits a fresh signed
registration and resumes the same wallet.

For planned signing-wallet rotation, stop the node, link a different replacement
wallet to the same canonical Grid account, issue a new validator API key, update
the local wallet/private-key/API-key settings, and run `aipg-validator rotate`.
After `aipg-validator check --no-probe` succeeds, revoke every previous validator
API key in the Console. The stable validator ID and historical evidence remain
unchanged; old in-flight assignments expire rather than moving to the new key.

If either key may have leaked, self-suspension is not sufficient: revoke the old
API key in the Console and ask a maintainer for hard registration revocation.
Deleting local files does not revoke server-side credentials.
