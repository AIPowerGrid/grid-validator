# Security Policy

## Reporting A Vulnerability

Email **security@aipowergrid.io** or open a private GitHub security advisory.
Do not open a public issue, post evidence in Discord, or send sensitive details
through a validator attestation.

- We acknowledge reports within 72 hours and aim to triage within 7 days.
- Give us a reasonable coordinated-disclosure window to investigate and ship a
  fix before publishing details.
- We credit reporters who follow this process.

## Scope

In scope:

- validator registration, API scopes, signing-wallet and Grid-account binding;
- assignment leases, nonces, replay handling, targeted probing, and evidence
  verification;
- attestation signatures, durable delivery, quorum isolation, and scorecards;
- private challenge or reference-data disclosure;
- release binaries, installers, checksums, SBOMs, containers, and provenance;
- any path that could fabricate evidence, count one operator more than once,
  expose validator secrets, target arbitrary workers, or influence future
  rewards, routing, disputes, or slashing incorrectly.

Third-party dependency vulnerabilities should normally be reported upstream.
Social engineering and volumetric denial of service are out of scope.

## What To Include

When available, include the affected validator version and platform, Core API
version, UTC timestamps, impact, reproduction steps, and a minimal proof of
concept. Redact API keys, private keys, full assignment payloads, prompts,
responses, and unrelated wallet or account data.

Preview validators currently provide non-economic evidence only. A report is
still high priority if it could become an economic or slashing vulnerability
when authority is enabled later.
