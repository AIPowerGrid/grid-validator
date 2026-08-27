# Validator Tests

## Purpose

Unit and contract coverage for configuration, dynamic probes, assignment-bound
attestations, fail-closed Grid capability handling, CLI/dashboard behavior, and systemd
installer generation.

## Ownership

- `test_prober.py`, `test_media_prober.py`, `test_attest.py`, `test_main.py` - challenge, evidence, and
  assignment loop.
- `test_outbox.py` - durable assignment journaling, atomic signed-evidence
  promotion, delivery, dead-letter recovery, restart behavior, and deterministic
  connection closure after both commit and rollback.
- `test_grid_client.py` - endpoint/capability and lifecycle transport contracts.
- `test_enrollment.py` - real local signature recovery with mock Core transport,
  exact-purpose SIWE checks, consent/cancellation, private-key-free setup,
  signer preservation on retry, concurrent setup exclusion, scoped-key checks,
  response bounds, and refusal to replace existing identities/configuration.
  These tests run on every native binary build, including Windows file locks.
- `test_cli.py`, `test_launcher.py`, `test_dashboard.py`, `test_config.py` - operator surfaces,
  including POSIX mode-`0600` / Windows protected owner-only signing-wallet preparation without secret
  output, prepared-identity init, safe qualification progress without private
  control metadata, signed suspension, and account-bound signing-wallet
  rotation.
- `test_update_check.py` - bounded release selection and nonfatal update checks.
- `test_operator_app.py` - real loopback HTTP guards, allowlisted controls and
  diagnostics, invalid-credential child recovery, owned-process stop, OS lock
  exclusion, and runtime acknowledgement/cancellation contracts. No live Grid
  keys or operator home-directory writes.
  A real unavailable loopback connection covers HTTPX's exception cause chain,
  including the startup wrapper, without contacting an external service.
- `test_account_pairing.py` - synthetic Core responses with real EIP-191
  signature recovery, exact contract validation, prior-review/fresh-read consent,
  stale/replaced approvals, cancellation, expired attempts, response-loss/restart
  recovery, exact-association unlink, config preservation and transport limits.
  No mock result proves Core's transaction or authorization implementation.
  This suite runs on all four native binary targets. Synthetic credential files
  use the production protected atomic writer, including the Windows DACL path.
- `test_core_pairing_integration.py` - opt-in tests against actual Core HTTP
  handlers, signature verification, scoped-key authentication and transactions.
  Set `VALIDATOR_CORE_SOURCE` and use a Core dependency environment. Real SIWE
  challenge/verify and signed registration precede link, private list and exact
  unlink; reject replayed SIWE, stale proof, app tokens, wrong owners and revoked
  node keys. Prove response-loss recovery and unchanged non-pairing state except
  normal authentication telemetry. SQLite, ASGI transport and a single-process
  nonce store are fixtures; this does not prove Redis/PostgreSQL concurrency.
- `test_console_pairing_integration.py` - additionally set
  `VALIDATOR_CONSOLE_SOURCE` to a built, env-file-free Console checkout. Starts
  disposable loopback Core and Next servers and uses the real wallet-login
  callback, Core SIWE/service binding, Auth.js cookies and pairing proxies.
  Proves anonymous/cross-origin rejection, approval without automatic node
  consent, explicit confirmation, private listing, owner removal and state
  preservation. Subprocess env is allowlisted; keys are generated in-memory,
  logs are not printed, and servers/temp files are cleaned up on failure.
  No Google, wallet-extension UI, HTTPS, native live or production proof.
  Both optional modules skip explicitly when their source paths are absent;
  Core/Console dependencies never enter the validator binary.
- `pairing_app_fixture.py` - manual, loopback browser QA with temporary random
  credentials and stdin-controlled mock approval/expiry/outage; never contacts
  production or runs a validator. Remove its temporary state on shutdown.
  Local pairing HTTP tests also prove origin/token/body guards, cached-only
  reads, metadata exclusion from diagnostics and runtime-control isolation.
- `test_self_test.py` - offline, real-process image/video decoder qualification
  for source and packaged runtimes.
- `test_systemd_installer.py` - generated service security and behavior.
- `test_release_tag.py` - binary/Docker release-tag and `latest` publication
  policy plus deterministic source/build identity stamping.
- `test_release_packaging.py` - frozen container/release dependencies, action
  pinning, SBOM/provenance contracts, reviewed-source binding, hostile archive
  rejection, native Windows installation, four-platform clean-install CI,
  exact installer-tag stamping, explicit unsigned-preview disclosure, and
  strict stable signing gates.
- `test_native_live_canary.py` - offline checks for the optional live harness:
  exact release/archive binding, unsafe paths, credential-free child env,
  bounded transport, real synthetic SIWE recovery, owner-confusion rejection,
  suspension/revocation and a manual-only protected workflow. These tests never
  contact Core and do not count as live Windows evidence.

## Local Contracts

- Tests use generated challenges and synthetic credentials; never commit live
  prompts, answer keys, pHashes, validator keys, or production API keys.
- Token-limit tests must prove early-stop, wrong-token, oversized, and hidden
  reasoning output fail closed, and that the signed response commitment binds
  visible text, reasoning text, and finish reason.
- Frozen-binary coverage must prove the dynamically packaged tokenizer is
  usable; registration must withhold the capability if it is unavailable.
- Source checkouts must report `v<project-version>-dev`; packaging tests must
  prove binary and container workflows stamp and smoke-test the exact validated
  release tag before publication.
- CLI checks must expose the local scorer set so release smokes can distinguish
  a usable frozen scorer from a silently withheld capability.
- Every native binary build tests CLI and menu behavior. Windows clean-install
  must create and reuse a real identity through the packaged menu and verify
  its protected DACL, not stop at `--help`. Menu tests must cover no-argument
  terminal vs piped behavior, stable config paths, fresh command subprocesses,
  persistent error output, and no implicit key creation or network access.
- Every official binary and container must run the same bounded image/video
  decoder self-test, including after a clean installer extraction.
- Preserve the no-economic-effect boundary: assignment success/failure must not
  imply payout, routing, strike, or slash authority.
- Prove missing registration, assignments, and probe support do not fall back
  to public inference or locally invented targets.
- Media witness tests must prove exact HTTPS-origin enforcement, no redirects,
  bounded streaming, MIME/length/hash binding, and private-target rejection.
- Deterministic image tests must use generated local fixtures and prove two
  references agree before an outlier candidate can fail. Reference disagreement,
  missing decoders, unsafe transport, and oversized contracts are inconclusive.
  Exercise the real bounded image child process with truncated and
  decompression-bomb fixtures, prove local decoder timeout is inconclusive
  rather than a worker failure, and pin the exact versioned pHash boundary.
  Corrupt or blank candidates cannot override disagreement between references.
- Video tests must generate local MP4 fixtures, exercise the real bounded PyAV
  decoder, reject inconsistent assignment timing and static/corrupt candidates,
  prove corrupt references and local decoder/process failures are inconclusive,
  and prove reference agreement precedes candidate fidelity failure. They do
  not prove prompt relevance, production workflow calibration, or cross-GPU
  fidelity.
  Include PyAV allocation/missing-codec/permission/unknown errors, sanitized
  child messages, corrupt/static candidates with disagreeing references, and
  invalid reference contracts with corrupt candidates. The media suite runs
  on all four native binary build targets as well as source CI.
- Prove the node rejects mismatched assignment/result metadata and recomputes
  prompt, response, and canonical evidence hashes before signing. Core's
  returned verdict must not replace the node's local score.
- Image-loop tests must prove capability advertisement depends on local decoder
  and origin readiness, signed envelopes omit witness URLs, and inconclusive
  comparisons enqueue no attestation.
- A mocked unit test does not prove real multi-node independence or adversarial
  quorum; keep that limitation explicit in release docs.
- Adversarial coverage must include a template-specific solver that can pass an
  objective protocol check while remaining ineligible for quality authority.
  Core's required CI owns the network challenge generator and executable
  prompt-classification, replay, and model-switching worker harness. Validator
  tests must preserve local score-dimension and signed-envelope boundaries; do
  not fork Core's generator into this repo or treat its red baseline as proof of
  probe indistinguishability.

## Work Guidance

- Add negative tests for missing/expired nonce, wrong worker, evidence-hash
  mismatch, duplicate attestation, endpoint failure, and self-validation.
- Keep CLI/installer tests isolated from the user's real home and services.
- Outbox tests must use temporary paths and prove assignments are journaled
  before probing, completed work promotes atomically, evidence survives restart,
  retries idempotently, dead rows require explicit revival, and validator state
  never persists a private key.

## Verification

- Run `./.venv/bin/python -m unittest discover -s tests`.
- Run `./scripts/smoke-release.sh` for release or installer changes.

## Child DOX Index

No child guides are currently required; this file owns `tests/`.
