# Validator Preview Cohort

AI Power Grid is recruiting 5-10 independently operated nodes for the first
validator preview. The purpose of this cohort is to prove that the software,
assignment lifecycle, and shared 3-of-5 evidence flow work across unrelated
operators and networks.

This is distributed testing, not decentralized economic validation. Preview
evidence does not change worker routing, strikes, payouts, or rewards. There is
no validator staking, slashing, or compensation in this cohort.

Enrollment is open for the evidence-only cohort. As checked on 2026-08-27,
production Core runs commit `f51875ce` with migrations through `0030`. New
operators should use the immutable public
[`v0.1.0-preview.13`](https://github.com/AIPowerGrid/grid-validator/releases/tag/v0.1.0-preview.13),
which provides explicit automatic enrollment and a local operator app. The
first-party fleet still runs preview.9; that is a deployment snapshot, not the
download recommendation.
The three first-party nodes share one operator and hypervisor, so they do not
count toward the five independent-operator exit gate.
See [PRODUCTION_BASELINE.md](PRODUCTION_BASELINE.md) for dated runtime evidence;
fresh registrations alone are not accepted-evidence or independence proof.

Core's new compensated-audit accounting is deployed dark: it has no scheduler,
quality workload, or effect on this cohort. Preview qualification remains
unpaid and evidence-only.

## Who Should Join

An operator should have:

- a Linux, macOS, or Windows machine that can stay online;
- a stable internet connection; no GPU is required;
- permission to install and run the preview; and
- willingness to report their public validator ID and basic operating details.

New enrollment creates a dedicated local signer and obtains a scoped validator
key for its own node account, only after confirmation. No pre-existing wallet,
funds, Google/GitHub login, or exported private key is required. Do not paste a
funded wallet's key into the validator. Optional association with an existing
human account is separate, unreleased work; preview.13 does not include it.

One organization or person counts as one independent operator, regardless of
how many nodes they run. Multiple nodes controlled by the same operator do not
increase quorum weight.

Independence means separate practical control of the validator key, host, and
operating decisions. A second wallet, process, VM, cloud account, or family
member acting under the same operational control is not a second operator.
Operators must disclose common control privately to the project maintainer;
Core records only an opaque group, never the operator's name, email, IP,
hostname, or review notes.

## Join

1. Install the verified preview.13 release using [QUICKSTART.md](QUICKSTART.md).
   On Windows, extract the ZIP and double-click `aipg-validator.exe`; choose
   menu option **8: Open local operator app**. No PowerShell is needed for the
   menu/app flow. Follow the unsigned-preview and verification guidance before
   running the download.
2. In the local app, choose **Set up node** on a new installation and confirm
   with **Set up and start**. The app continues into the validator loop after
   enrollment; a second Start click is not required. Existing operators should
   keep their protected configuration and use **Start validator**; do not delete
   keys or enroll a replacement identity just to upgrade. Wait for the setup
   checklist to confirm registration, heartbeat, assignment, and accepted
   evidence, then copy the public `val_*` validator ID from the app.
3. Join the [AI Power Grid Discord](https://discord.gg/W9D8j6HCtC) and ask
   privately to join the **validator preview cohort**. Send only the `val_*`
   validator ID plus:
   - operating system and CPU architecture;
   - country or broad region;
   - expected online hours; and
   - whether the network is residential, datacenter, or cloud hosted.
4. Do not post API keys, private keys, signatures, account IDs, full wallet
   addresses, assignment payloads, prompts, or worker responses.
5. Ask the maintainer to begin independent-operator qualification. Running the
   preview and receiving assignments does not automatically start or complete
   that review. Never send a private key to the maintainer.
6. Check the public validator ID at <https://aipowergrid.io/validate>. This page
   requires no API key or private key and should agree with the local app's
   version, online state, aggregate activity, and qualification progress.

Linux x64 and ARM64 binaries target glibc 2.35 or newer. macOS and Windows
preview binaries are explicitly unsigned; Linux is the lowest-friction public
pilot path. The exact `ghcr.io/aipowergrid/validator:v0.1.0-preview.13`
container is anonymously pullable on Linux x64 and ARM64; the prerelease does
not publish `latest`.

```bash
curl -fsSLO https://github.com/AIPowerGrid/grid-validator/releases/download/v0.1.0-preview.13/install-validator.sh
gh attestation verify install-validator.sh --repo AIPowerGrid/grid-validator
bash install-validator.sh
cd ~/.aipg-validator
aipg-validator enroll
aipg-validator check --no-probe
aipg-validator app
```

## Qualification Run

Use Start validator in the local app and keep it running. A heartbeat alone is not a
passing end-to-end test: the node must receive an assignment, finish its probe,
and have its signed evidence accepted. Assignment availability is not guaranteed
immediately. Do not run a second copy while the app's worker is running.

For headless operation, stop the app's worker first and run the node
continuously for at least 72 hours:

```bash
aipg-validator run
```

After enrollment, the project maintainer places the registration into candidate
status. `aipg-validator check --no-probe` and the localhost dashboard show only
the authenticated operator's safe qualification status and progress; they never
show the internal common-control group or private review reference. Core samples
at most one qualifying heartbeat every five minutes.
Verification requires at least 72 hours, at least 80% sample coverage, a fresh
heartbeat, and a project-maintainer review. A verified review expires after 30
days by default and must be renewed; operators cannot self-certify through the
node or API.

Three recently active, verified independent operator groups is the initial
production-cohort milestone for assessing onboarding and shared evidence. The
broader pilot is proven only when Core reports at least five recently active,
verified independent operator groups and real shared groups receive at least
three reviewed independent votes. Neither milestone enables validator rewards,
slashing, or routing authority. The public
[network status](https://console.aipowergrid.io/network) exposes aggregate
verified and participating counts but no group identifiers. A successful install,
registration, wallet, heartbeat, or ordinary 3-of-5 registration quorum alone
does not prove independence. Until both conditions hold, validator evidence
remains preview-only and economically inert.

The 72-hour run qualifies basic operation and control separation. It does not
prove every model claim, authorize rewards, or make subjective evidence
slashable.

## Report Problems

Share the node version, platform, UTC timestamp, command that failed, and a
short redacted log excerpt. Remove secrets and the evidence fields listed
above. Report suspected security issues privately using the process in
[`SECURITY.md`](SECURITY.md), not in Discord or a public issue.

## Exit And Revocation

Stop in the local app stops its managed process; it does not revoke keys or
unlink an account. For a signed self-suspension, stop the local loop first and
run `aipg-validator suspend`. A later Start validator or `aipg-validator check --no-probe`
submits a fresh signed registration and resumes the same wallet.

Planned key rotation is an advanced, account-bound procedure documented in
[OPERATORS.md](OPERATORS.md). Ask the maintainer for help before changing a
dedicated node identity. Do not assume the human Console session controls an
automatically enrolled node account, or that deleting local files rotates it.

If either key may have leaked, self-suspension is not sufficient: revoke the old
API key through an authenticated session for its owning account, or ask the
project maintainer for server-side key and registration revocation. This is
especially important for dedicated node accounts without a human login.
Deleting local files does not revoke server-side credentials.
