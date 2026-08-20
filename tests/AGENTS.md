# Validator Tests

## Purpose

Unit and contract coverage for configuration, dynamic probes, assignment-bound
attestations, fail-closed Grid capability handling, CLI/dashboard behavior, and systemd
installer generation.

## Ownership

- `test_prober.py`, `test_attest.py`, `test_main.py` - challenge, evidence, and
  assignment loop.
- `test_grid_client.py` - endpoint/capability contracts and fail-closed behavior.
- `test_cli.py`, `test_dashboard.py`, `test_config.py` - operator surfaces.
- `test_systemd_installer.py` - generated service security and behavior.

## Local Contracts

- Tests use generated challenges and synthetic credentials; never commit live
  prompts, answer keys, pHashes, validator keys, or production API keys.
- Preserve the no-economic-effect boundary: assignment success/failure must not
  imply payout, routing, strike, or slash authority.
- Prove missing registration, assignments, and probe support do not fall back
  to public inference or locally invented targets.
- A mocked unit test does not prove real multi-node independence or adversarial
  quorum; keep that limitation explicit in release docs.

## Work Guidance

- Add negative tests for missing/expired nonce, wrong worker, evidence-hash
  mismatch, duplicate attestation, endpoint failure, and self-validation.
- Keep CLI/installer tests isolated from the user's real home and services.

## Verification

- Run `./.venv/bin/python -m unittest discover -s tests`.
- Run `./scripts/smoke-release.sh` for release or installer changes.

## Child DOX Index

No child guides are currently required; this file owns `tests/`.
