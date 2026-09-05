# Validator Release And Install Scripts

## Purpose

Operational scripts for release classification and identity stamping, artifact
verification, binary installation, systemd installation, and release smoke tests.

## Ownership

- `classify-release-tag.sh` validates release classes and controls whether a tag
  may publish `latest`.
- `stamp-release-tag.py` converts a validated workflow tag into the immutable
  identity embedded in a binary or container. Empty input stamps the package's
  `vX.Y.Z-dev` identity.
- `stamp-release-installers.py` replaces the one release-tag placeholder in
  each packaged installer. Source installers require an explicit version;
  published installers must default to their own immutable tag.
- `verify-release-assets.sh` verifies the complete binary release payload.
- `install-binary.sh`, `install-validator.ps1`, and `install-systemd.sh` own
  operator installation paths.
- `smoke-release.sh` exercises source, container, binary, and installer paths.
- `smoke-operator-app.py` starts an actual frozen binary against invalid offline
  config, verifies packaged assets and local HTTP authentication, exercises
  child failure/restart and explicit app exit, and checks diagnostics omit
  credentials and paths. Windows fallback cleanup must stop the owned onefile
  process tree; killing only its bootloader can leave a child holding stdout.
  It also checks the private cached pairing endpoint and invalid-config recovery
  without Core traffic. This is package qualification, not live pairing proof.
- `native-live-canary.py` verifies fixed published archives/provenance and runs
  an explicitly approved first-party Windows local-app journey against the
  unpaid production Grid. It creates fresh isolated state, checks accepted
  evidence and recovery, then suspends/revokes the disposable node credentials.
  Never print captured child output or upload private state. This is a manual
  protected workflow, not ordinary CI or independent/operator-UI proof.
  Current pins exercise published preview.13 to preview.14. Updating the pins
  prepares a test; only a successful live report establishes runtime proof.
- `native-pairing-canary.py` is a separate, manual Windows/Linux candidate
  qualification harness. It binds a successful reviewed-master binary workflow
  to its exact source and archive hash, explicitly labels build-only artifacts
  as lacking release provenance, and requires an exact dark Core revision.
  It creates only a fresh disposable node; a maintainer separately admits that
  node and an unfunded test human through the expiring pilot. Console approval
  and hidden code entry are separate from polling. Private review files never
  enter the bounded public report. Cancellation, two removals, app restart,
  discarded-response recovery, fresh evidence before/after and retirement must
  all pass. This harness has not yet passed a native live pairing run; its
  offline fixtures are not that proof. See `../NATIVE_PAIRING_CANARY.md`.
- `verify-validator-control.py` is a credential-free maintainer helper for the
  preview cohort's live ownership check. It observes only the redacted public
  status transition from active to signed-suspended and back to active. Passing
  proves current node-key control, never operator independence or authority.

## Local Contracts

- Moving source never claims an immutable published tag. The committed
  `validator.__release_tag__` must be `v<project-version>-dev`.
- Only protected release workflows may call `stamp-release-tag.py` with a
  non-development tag. The tag must match `pyproject.toml` exactly and use an
  allowed stable or bounded prerelease form.
- Release workflows must run the packaged CLI with `--version` and require the
  exact stamped identity before publication.
- The release verifier must reject published installers that are unstamped or
  point at any tag other than the manifest tag. Build-only payloads retain the
  placeholder and may install only from explicit local asset/checksum paths.
- Keep scripts deterministic and non-interactive unless their installer purpose
  explicitly requires operator input. Never print secrets.
- Validator-control review polling must be bounded, require the frozen supported
  cohort version and `economic_effect=none`, and reject ID/version changes. It
  may consume only the public validator status endpoint.
- The manual pairing harness's `review` command deliberately requires a TTY for
  hidden comparison-code input. No code, approval URL, local session token or
  private state may be passed through public CI logs/artifacts. Shared native
  subprocess helpers own POSIX process groups and kill descendants on timeout,
  even when the parent exited first; Windows cleanup remains tree-scoped.
- Collect `validator` package data in PyInstaller. Every native release build
  runs the app smoke; importing source tests alone does not prove UI packaging.
- Windows installer output points to the interactive menu with an explicit
  config path. It never runs identity creation or requests credentials itself.
- Source and binary installers point new operators to explicit `enroll`, not
  private-key entry. Installation remains network-free with respect to Core
  authentication; enrollment requires a separate confirmed operator action.
- The systemd unit keeps `ProtectHome=read-only` and `ProtectSystem=full`, grants
  `ReadWritePaths` only to its private work directory, and pins
  `VALIDATOR_STATE_DB` inside that directory so assignment/evidence recovery is
  actually durable. A missing `.env` must direct a new operator to `enroll`, not
  the advanced `init` path.
- The release verifier requires enrollment before the registration check in
  both installers. Its payload tests must use the real installer sources,
  not synthetic instructions that can drift while still passing their own gate.

## Verification

- `./.venv/bin/python -m unittest tests.test_release_tag tests.test_release_packaging`
- `bash -n classify-release-tag.sh install-binary.sh install-systemd.sh smoke-release.sh verify-release-assets.sh`
- `python stamp-release-tag.py --root <throwaway-repo-root> <tag>` only against a
  throwaway checkout; do not stamp a release tag into the working tree manually.

## Child DOX Index

No child guides are required; this file owns `scripts/`.
