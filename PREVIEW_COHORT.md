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

The cohort is proven only when Core reports at least five recently active,
distinct registered validators and shared groups receive independent votes
from unrelated operators. A successful install or heartbeat alone does not
prove quorum.

## Report Problems

Share the node version, platform, UTC timestamp, command that failed, and a
short redacted log excerpt. Remove secrets and the evidence fields listed
above. Report suspected security issues privately using the process in
[`SECURITY.md`](SECURITY.md), not in Discord or a public issue.

## Exit And Revocation

Stop the process or service to leave the cohort. If a signing key or validator
API key may have leaked, revoke the API key in the Console, rotate the signing
wallet, and ask an operator to revoke the validator registration. Deleting
local files does not revoke server-side credentials.
