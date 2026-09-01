# Validator Preview Cohort

AI Power Grid is qualifying three independently operated nodes for the initial
authority-readiness review, then five for the broader pilot; ten remains the
recruitment target. With one candidate currently running, the immediate need is
two additional unrelated Linux/systemd operators. The purpose of this cohort is
to prove that the software, assignment lifecycle, and shared 3-of-5 evidence
flow work across unrelated operators and networks.

This is distributed testing, not decentralized economic validation. Preview
evidence does not change worker routing, strikes, payouts, or rewards. There is
no validator staking, slashing, or compensation in this cohort.

## Operating Decision

The preview is a useful production observability lane before independent
authority exists. Registered nodes may receive randomized assignments, submit
signed evidence, and contribute to aggregate reliability and disagreement
telemetry. That evidence helps maintainers find worker and protocol failures,
but it is not an independent vote unless the operator has completed the review
and qualification below.

The rest of AI Power Grid does not wait for this cohort to reach its
independence milestone. Worker onboarding, public inference, client
integrations, and demand-side products may continue while qualification runs in
parallel. Only validator-controlled routing, rewards, strikes, staking, and
slashing are gated on reviewed independent operators and a separate activation
decision. First-party nodes may keep the telemetry lane healthy, but they never
fill independent-operator seats.

Enrollment is open for the evidence-only cohort. As checked on 2026-09-01,
production Core runs commit
`4e0eb3f6b883218502b01d550c7cdeed7f9a0dd2` with migrations through `0031`.
New operators must use the immutable public
[`v0.1.0-preview.13`](https://github.com/AIPowerGrid/grid-validator/releases/tag/v0.1.0-preview.13),
which provides explicit automatic enrollment and a local operator app. Core
marks older versions `upgrade_required` and excludes them from independent
quorum. Legacy first-party registrations still reporting preview.9 are a
deployment snapshot, not the download recommendation.
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
   with **Create node account**, then choose **Start validator**. Published
   preview.13 keeps setup and start as separate actions. Existing operators
   should keep their protected configuration and use **Start validator**; do not
   delete keys or enroll a replacement identity just to upgrade. Wait for
   acknowledged registration and heartbeat, then copy the public `val_*`
   validator ID from the app.
3. Join the [AI Power Grid Discord](https://discord.gg/W9D8j6HCtC) and ask
   privately to join the **validator preview cohort**. Send only the `val_*`
   validator ID plus:
   - operating system and CPU architecture;
   - country or broad region;
   - expected online hours; and
   - whether the network is residential, datacenter, or cloud hosted.
4. Do not post API keys, private keys, signatures, account IDs, full wallet
   addresses, assignment payloads, prompts, or worker responses.
5. Before candidate status starts, complete a short live control check with the
   maintainer. Stop the local validator loop, run `aipg-validator suspend`, and
   wait for the maintainer to confirm that this exact `val_*` registration is
   suspended. Then run `aipg-validator check --no-probe` and confirm that the
   same validator ID returns active. Both requests are signed locally by the
   registered node identity; no key, signature, configuration file, or wallet
   address is shared. Knowing or copying somebody else's public validator ID is
   therefore not enough to enter qualification.
6. Ask the maintainer to begin independent-operator qualification. The signed
   control check proves possession of this node's credentials at review time;
   it does not prove separate ownership, hosting, funding, or operating
   decisions. Those facts remain part of the private common-control review.
   Running the preview and receiving assignments does not automatically start
   or complete that review. Never send a private key to the maintainer.
7. Check the public validator ID at <https://aipowergrid.io/validate>. This page
   requires no API key or private key and should agree with the local app's
   version, online state, aggregate activity, and qualification progress.

The maintainer can observe step 5 without handling credentials or private
metadata by running this from a reviewed `grid-validator` checkout:

```bash
python scripts/verify-validator-control.py val_0123456789abcdef0123456789abcdef
```

The helper requires the frozen supported cohort version and
`economic_effect=none`, then waits for the same public ID to transition from
active to signed-suspended and back to active. It is a bounded convenience for
the live review, not an independence oracle and not validator authority.

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

For headless operation, stop the app's worker first and install the pinned
systemd service from [QUICKSTART.md](QUICKSTART.md#systemd). Confirm it is
active and following the same preview.13 identity before starting the 72-hour
window:

```bash
sudo systemctl status aipg-validator --no-pager
sudo journalctl -u aipg-validator -f
```

After enrollment, the project maintainer places the registration into candidate
status only after the signed control check and common-control review above.
Perform the suspend/resume check before the 72-hour window so it cannot create a
qualification heartbeat gap. `aipg-validator check --no-probe` and the localhost
dashboard show only the authenticated operator's safe qualification status and
progress; they never show the internal common-control group or private review
reference. Core samples at most one qualifying heartbeat every five minutes.
Verification requires at least 72 hours, at least 80% sample coverage, a fresh
heartbeat, a project-maintainer review, at least one completed probe created
after the candidate window began, and at least one accepted authoritative
attestation created after that same boundary. Pre-window evidence cannot satisfy
the work gate. The maintainer follows Core's
[preview-first, digest-bound finalization runbook](https://github.com/AIPowerGrid/grid-core/blob/main/docs/VALIDATOR_SHADOW_RUNBOOK.md#0-finalize-and-recheck-the-independent-cohort);
the apply step remains fail-closed and grants no routing or economic effect. A
verified review expires after 30 days by default. A later review cycle starts a
fresh candidate window rather than extending trust in place. Operators cannot
self-certify through the node or API.

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

This milestone is an authority gate, not a network-launch gate. Failing to
recruit or retain three operators means independent validator authority remains
off; it does not erase the signed telemetry already produced or stop unrelated
Grid work.

After three recently participating independent operator groups complete this
gate, Core may begin one **seven-day shadow-authority run**. Shadow mode records
what a frozen validator advisory policy would have changed while the production
router remains authoritative and unchanged. It has no effect on user requests,
worker health, den, payouts, rewards, bonds, strikes, or slashing. At least 80
percent of the observation samples must retain three participating independent
groups, no continuous quorum gap may exceed one hour, and every hypothetical
change must be replayable from a policy and evidence commitment. A failed run is
repeated rather than weakening the gate.

The canonical design and review contract lives in Core's
[`VALIDATOR_SHADOW_AUTHORITY.md`](https://github.com/AIPowerGrid/grid-core/blob/main/docs/architecture/VALIDATOR_SHADOW_AUTHORITY.md).
Completing the run permits a separate routing review only; it does not activate
validator influence or rewards. Shadow collection uses the existing signed
evidence contract and does not require a new validator binary. Keep preview.13
as the cohort baseline while the current candidate qualifies; do not publish
preview.14 merely to start the observer.

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
