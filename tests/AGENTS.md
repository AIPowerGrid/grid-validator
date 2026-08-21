# Validator Tests

## Purpose

Unit and contract coverage for configuration, dynamic probes, assignment-bound
attestations, fail-closed Grid capability handling, CLI/dashboard behavior, and systemd
installer generation.

## Ownership

- `test_prober.py`, `test_media_prober.py`, `test_attest.py`, `test_main.py` - challenge, evidence, and
  assignment loop.
- `test_outbox.py` - durable signed-evidence delivery and restart behavior.
- `test_grid_client.py` - endpoint/capability contracts and fail-closed behavior.
- `test_cli.py`, `test_dashboard.py`, `test_config.py` - operator surfaces.
- `test_systemd_installer.py` - generated service security and behavior.
- `test_release_tag.py` - binary/Docker release-tag and `latest` publication
  policy.
- `test_release_packaging.py` - frozen container/release dependencies, action
  pinning, SBOM/provenance contracts, reviewed-source binding, hostile archive
  rejection, and explicit publish gating.

## Local Contracts

- Tests use generated challenges and synthetic credentials; never commit live
  prompts, answer keys, pHashes, validator keys, or production API keys.
- Token-limit tests must prove early-stop, wrong-token, oversized, and hidden
  reasoning output fail closed, and that the signed response commitment binds
  visible text, reasoning text, and finish reason.
- Frozen-binary coverage must prove the dynamically packaged tokenizer is
  usable; registration must withhold the capability if it is unavailable.
- CLI checks must expose the local scorer set so release smokes can distinguish
  a usable frozen scorer from a silently withheld capability.
- Preserve the no-economic-effect boundary: assignment success/failure must not
  imply payout, routing, strike, or slash authority.
- Prove missing registration, assignments, and probe support do not fall back
  to public inference or locally invented targets.
- Media witness tests must prove exact HTTPS-origin enforcement, no redirects,
  bounded streaming, MIME/length/hash binding, and private-target rejection.
- Deterministic image tests must use generated local fixtures and prove two
  references agree before an outlier candidate can fail. Reference disagreement,
  missing decoders, unsafe transport, and oversized contracts are inconclusive.
- Video tests must generate local MP4 fixtures, exercise the real bounded PyAV
  decoder, reject inconsistent assignment timing and static/corrupt candidates,
  and prove reference agreement precedes candidate fidelity failure. They do
  not prove prompt relevance, production workflow calibration, or cross-GPU
  fidelity.
- Prove the node rejects mismatched assignment/result metadata and recomputes
  prompt, response, and canonical evidence hashes before signing. Core's
  returned verdict must not replace the node's local score.
- Image-loop tests must prove capability advertisement depends on local decoder
  and origin readiness, signed envelopes omit witness URLs, and inconclusive
  comparisons enqueue no attestation.
- A mocked unit test does not prove real multi-node independence or adversarial
  quorum; keep that limitation explicit in release docs.

## Work Guidance

- Add negative tests for missing/expired nonce, wrong worker, evidence-hash
  mismatch, duplicate attestation, endpoint failure, and self-validation.
- Keep CLI/installer tests isolated from the user's real home and services.
- Outbox tests must use temporary paths and prove evidence survives restart,
  retries idempotently, and never persists a validator private key.

## Verification

- Run `./.venv/bin/python -m unittest discover -s tests`.
- Run `./scripts/smoke-release.sh` for release or installer changes.

## Child DOX Index

No child guides are currently required; this file owns `tests/`.
