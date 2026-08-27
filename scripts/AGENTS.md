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
  child failure/restart, and checks diagnostics omit credentials and paths.

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
- Collect `validator` package data in PyInstaller. Every native release build
  runs the app smoke; importing source tests alone does not prove UI packaging.
- Windows installer output points to the interactive menu with an explicit
  config path. It never runs identity creation or requests credentials itself.
- Source and binary installers point new operators to explicit `enroll`, not
  private-key entry. Installation remains network-free with respect to Core
  authentication; enrollment requires a separate confirmed operator action.
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
