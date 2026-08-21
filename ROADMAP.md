# Validator Node Roadmap

This is the practical build plan for turning validators from a preview audit
runner into a network primitive. Keep this document honest: mark a capability as
live only when the validator node, Grid core endpoint, operator docs, and tests
exist.

For the evidence-only rollout sequence, use [RELEASE_V0.md](RELEASE_V0.md).

## Product Story

Validators are independent audit nodes. They do not need GPUs. Their job is to
send small, unpredictable challenges through the Grid, score whether workers
followed the job contract, and submit signed evidence.

The point is not to prove every byte of a remote model stack. For most
generation work, the point is proof of usefulness and proof of honesty:

- did the worker solve the task it accepted?
- did it respect parameters such as max tokens, dimensions, seeds, duration, and
  output format?
- did it return usable output instead of unrelated cached output?
- did it perform within the claimed capability tier?

For deterministic workflows, especially image workflows with fixed model and
workflow hashes, validators can also provide proof of fidelity by comparing a
candidate worker against certified reference output.

## Design Principles

- Start with evidence, not punishment.
- Pay later for accepted useful attestations, never for mere uptime.
- Prefer objective checks over subjective judges.
- Treat bonded workers as more accountable, not automatically correct.
- Use trusted/reference workers to create baselines, but never one permanent
  oracle.
- Keep live challenge seeds, prompts, answer keys, pHashes, and thresholds out
  of the public repo.
- Raw prompts and outputs stay off-chain; Base gets compact commitments, roots,
  bonds, rewards, and dispute results.

## Phase 0: Preview Audit Runner

Status: evidence path implemented; production Core rollout and public binary
distribution are pending.

Goal: give operators something easy to run while the Grid learns from evidence
without economic side effects.

Live or scaffolded in this repo:

- source install
- local Docker build and Compose
- tag/manual GitHub Actions binary-release workflow
- frozen cross-platform release dependency lock
- release-binary installer script
- Linux systemd installer script
- `aipg-validator init`
- `aipg-validator check`
- `aipg-validator dashboard`
- `aipg-validator run`
- assignment-bound text canaries through validator-only endpoints
- nonce/generated-QA/latency scoring
- mandatory linked-wallet registration and signed attestations
- fail-closed behavior when required validator endpoints are missing

Candidate Grid-core support (merged, not yet production-live):

- `GET /v1/validator/capabilities` advertises safe validator feature flags
- `POST /v1/validator/attest` stores evidence only
- `GET /v1/validator/scorecards` returns aggregate evidence only
- `GET /v1/validator/workers` exposes targetable inventory to authenticated
  validator accounts
- `GET /v1/validator/assignments` issues short-lived text assignments
- `POST /v1/validator/probe/{assignment_id}` reaches the assigned worker
- assignment-bound attestations feed scorecards and a non-economic shared
  3-of-5 quorum lifecycle; independent operator proof remains rollout work

Hard no-go boundaries:

- no slashing
- no validator rewards
- no routing impact
- no false targeted failures
- no claim that exact model weights are proven

Definition of done:

- package installs cleanly from source
- local dashboard shows Grid reachability and mode
- unit tests pass
- docs say V0 is evidence-only
- deployed Grid Core can issue, probe, accept, and aggregate assignment-bound
  attestations without money or routing effects
- production rollout uses `RELEASE_V0.md` and requires explicit Alembic migration
  plus endpoint checks

## Phase 1: Public Distribution

Goal: make validators as easy to run as workers.

Deliverables:

- release binaries for Linux x64, Linux ARM64, macOS ARM64, Windows x64
- published Docker image
- checksum-covered install script in the exact GitHub release; stable hosted
  bootstrap only after its DNS and serving path are independently verified
- provenance-attested release artifacts and SPDX SBOM
- strict release tags; prereleases never publish Docker `latest`
- GitHub release workflow
- service install/update path
- operator health page that shows core capability flags

Operator shape:

```bash
curl -fsSLO https://github.com/AIPowerGrid/grid-validator/releases/download/v0.1.0-preview/install-validator.sh
gh attestation verify install-validator.sh --repo AIPowerGrid/grid-validator
AIPG_VALIDATOR_VERSION=v0.1.0-preview bash install-validator.sh
cd ~/.aipg-validator
aipg-validator init
aipg-validator check --no-probe
aipg-validator dashboard
aipg-validator run
```

Definition of done:

- release-binary workflow runs clean on a real tag/manual dispatch
- binary installer downloads and smoke-tests a release artifact
- systemd installer dry-run and Linux host install path are verified
- a non-developer can install, run `check --no-probe`, and see a healthy
  dashboard in under 10 minutes
- `.env` stays local and private
- Docker path does not expose secrets in process listings

## Phase 2: Targeted Assignments

Status: implemented for the evidence-only text lane. Media assignments,
economic effects, and adversarial multi-validator proving remain open.

Goal: move from "probe a model through the normal router" to "probe this worker
for this capability."

Grid-core endpoints:

- `GET /v1/validator/capabilities`
- `GET /v1/validator/assignments`
- `POST /v1/validator/probe/{assignment_id}`
- `POST /v1/validator/attest`
- worker scorecard APIs

Assignment fields:

- assignment id
- target worker id
- modality
- capability
- prompt/workflow reference
- nonce
- scoring policy id
- expiration
- validator signature domain

Rules:

- one validator must not validate its own worker
- assignments expire quickly
- probes must be unpredictable
- failed core endpoints must skip, not punish
- validators sign canonical attestation payloads

Definition of done:

- targeted endpoint reaches exactly the assigned worker
- retries cannot create duplicate economic effects
- missing or disabled targeted probes produce no false `failed` attestations
- scorecards can display evidence without routing impact first

## Phase 3: Text Validation

Goal: validate useful LLM behavior without pretending to know exact quantization.

Capability lanes:

- basic instruction following
- strict JSON/schema output
- code generation with hidden tests
- math and logic tasks with generated answers
- single-function calls, then multi-turn tool-call chains
- long-context retrieval
- max-token, stop-sequence, and streaming honesty

Implemented in the preview: exact instruction, generated arithmetic, strict
JSON object output, randomized context retrieval, generated multistep
integer logic, exact single-function calls, an exact two-stage tool-call chain,
stop-sequence compliance, and gross output-budget compliance. Code execution,
longer tool chains, larger context tiers, and exact native-tokenizer
equivalence remain future lanes.

Scoring:

- deterministic checks where possible
- hidden unit tests for code
- exact nonce and schema checks
- latency and timeout classification
- LLM-as-judge only as secondary evidence

Definition of done:

- each text capability has a scoring policy id
- validators can explain `healthy`, `slow`, and `failed`
- repeated objective failures affect routing caps before any slash design

## Phase 4: Image Validation

Implementation must follow
`grid-core/docs/architecture/MEDIA_VALIDATION_V1.md`: Core-computed object
digests, validator URL allowlisting, two agreeing references, distinct operator
controls, and inconclusive reference disagreement are release gates.

Implemented dark: exact public HTTPS-origin allowlisting, redirect/proxy/
encoding refusal, byte/time/MIME limits, SHA-256 witness recomputation, and the
independent `image.fidelity.v1` three-witness scorer. The scorer requires two
references to agree before comparing the candidate and classifies infrastructure
or reference ambiguity as inconclusive. Node-side assignment polling and
dependency-aware capability advertisement are implemented. Core assignment
issuance, immutable witness retention, deterministic recipe certification, and
the populated rotating reference pool remain release gates.

Goal: separate general image usefulness from deterministic workflow fidelity.

General image checks:

- output decodes
- dimensions match
- format matches
- image is not blank/noise
- explicit seed behavior is respected when claimed
- simple prompt constraints are plausibly followed

The local, non-authoritative scaffold now uses cryptographic prompt and seed
selection. The future authoritative lane must replace that helper with one
private Core-issued challenge shared only with the assigned validator group.

Deterministic workflow checks:

- workflow hash
- checkpoint/model hash
- LoRA/VAE/control model hashes where applicable
- sampler/scheduler/steps/CFG/dimensions
- explicit seed
- pHash/SSIM/LPIPS tolerance against reference output

Reference path:

- select bonded, highly validated workers as reference workers
- use more than one reference for important certification
- discard ambiguous reference disagreement
- rotate references

Definition of done:

- deterministic image workflow certificate format exists
- certificate evidence is reproducible by independent validators
- product layers can require certified deterministic workflow provenance
  without embedding minting policy in the validator node

## Phase 5: Video Validation

Goal: score basic video contract honesty first, then add semi-deterministic
workflow checks where the stack supports it.

General video checks:

- output decodes
- duration matches
- fps matches
- resolution matches
- frames are not a static still unless requested
- simple motion/key-event constraints are present where objectively checkable

Deterministic or semi-deterministic checks:

- workflow hash
- keyframe pHash
- frame count
- optical-flow/motion profile
- reference comparison for certified workflows

Definition of done:

- video evidence affects routing/caps first
- slashing is limited to objective fraud, not subjective quality

## Phase 6: Economics And Base Anchoring

Goal: validators become economically useful without making the hot path brittle.

On-chain surfaces:

- validator registry
- validator stake
- worker bond/slash events
- epoch attestation roots
- workflow certificate roots
- validator reward roots

Reward shape:

```text
reward =
  base_fee
  * difficulty_weight
  * modality_weight
  * agreement_score
  * timeliness
  * validator_reputation
```

Rules:

- pay for accepted useful attestations
- do not pay for duplicate spam
- going offline stops rewards but should not slash stake
- objective fraud may become slashable after quorum and dispute tooling exist
- subjective quality affects routing, not stake

Definition of done:

- epoch roots are published on Base
- reward claims are transparent
- slashing has a dispute path
- validators cannot profit by self-validating their own workers

## Immediate Next Build Order

1. Deploy migrations through `0024` and the immutable Core candidate; smoke every
   assignment-bound endpoint while keeping the path evidence-only.
2. Publish the already-scaffolded binaries and Docker image only after that gate.
3. Prove self-validation exclusion and adversarial multi-validator behavior.
4. Add text capability policies before media/video economic effects.
5. Add deterministic image workflow certification before any product-level
   minting or marketplace trust gate depends on validator evidence.
6. Add validator stake/rewards after evidence, scorecards, and references are
   proven operationally.
