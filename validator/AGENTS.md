# validator — the node (config, stake, probing, attestation, loop, CLI)

## Purpose

The validator implementation: load config, register a linked signing identity,
optionally gate on on-chain stake, consume Grid-issued assignments, fire
unpredictable targeted canaries, score replies, sign attestations, and POST them
in a loop. V0 is CPU-only and assignment-bound for text. The assignment loop
can consume deterministic image-fidelity and video contract/fidelity work only
when the optional media dependencies and an explicit HTTPS witness-origin
allowlist are present. Core still issues no media work until its
independent-reference and rollout gates pass.

## Ownership

- **`config.py`** — env-driven `Settings` (grid URL + key, wallet/private key,
  Base RPC + contract addrs, `MIN_STAKE`/`REQUIRE_STAKE`, text probe intervals
  and latency budget, and exact public HTTPS media origins/byte/time limits).
  `Settings.validate()` enforces required fields, rejects malformed Grid URLs,
  rejects malformed EVM addresses for wallet/token/staking fields, validates the
  local dashboard port, and rejects a wallet/private-key mismatch.
  The default targeted-probe timeout covers Core's complete 180-second text
  probe window; do not shorten the client below the server-side deadline.
  All env reads live here. Malformed numeric/boolean/URL/address env values must be reported
  through `Settings.validate()` as operator-facing config errors, not import-time
  tracebacks or downstream Web3 exceptions.
- **`staking.py`** — on-chain stake gate (`stake_of`, `assert_eligible`). Raises `NotDeployed`
  until `VALIDATOR_STAKING_ADDR` is set; honors `REQUIRE_STAKE=false` for pre-launch/dev.
- **`grid_client.py`** — async httpx client for validator registration,
  suspension, signing-wallet rotation, heartbeat, capabilities, scorecards, assignments, assignment-bound targeted
  probes, worker inventory, and attestation submission.
  Each grid-only endpoint degrades gracefully (conservative capabilities,
  unavailable scorecards, empty list, `None`, or `False`) when not yet deployed.
  It sends both Grid-native `apikey` and OpenAI-compatible `Authorization:
  Bearer` headers with the same validator API key; keep that dual-header
  behavior unless core deliberately drops one auth style.
  Assignment and probe endpoints fail closed when absent. Worker inventory is
  dashboard-only and must never become an alternate targeting authority.
  Heartbeats advertise the immutable release tag, not only the base Python
  package version, so qualification can distinguish reviewed preview payloads.
- **`prober.py`** — independent text scoring for randomized exact-instruction,
  arithmetic, strict-JSON, exact 4K/16K/32K context-retrieval, multistep-logic,
  restricted-AST Python functions against assignment-only hidden inputs, exact
  single-function-call, two-stage tool-chain, and stop-sequence commitments. The
  code scorer parses and interprets one bounded integer expression; it must never
  `exec`, import, call, or otherwise run worker-supplied code;
  its token-limit scorer independently counts visible plus reasoning output
  with `o200k_base`, requires a length-style finish, and applies the same
  cross-tokenizer tolerance as Core. Runtime registration withholds that
  capability when the local encoding cannot be loaded;
  legacy local canary helpers remain for isolated tests. `is_text_model`
  heuristic skips media models in v0; `_strip_think` ignores reasoning-model
  chain-of-thought. Do not reintroduce static QA answer lists.
- **`media_prober.py`** — image/video canaries + scoring across structural,
  pHash-consensus, and video-motion axes. Its local preview generator uses
  cryptographic prompt/seed selection and is never an authority; shared media
  challenges must come from Core. Its dark `image.fidelity.v1` scorer requires
  one candidate plus two distinct committed references, verifies every witness,
  treats reference disagreement as inconclusive, and fails an outlier candidate
  only after the references agree. Image decoding and pHash computation run in
  a killable child process with host-supported resource limits; decoder timeout
  or local process failure is inconclusive, while a committed malformed
  candidate may fail. Its
  dark video scorers validate a bounded
  MP4/WebM decode, dimensions, frame count, frame rate, duration, blank/static
  frames, and latency. Video fidelity additionally compares every decoded frame
  and the motion profile against two references after those references agree.
  Native video decode runs in a killable child process and never makes prompt
  relevance an authoritative claim. The witness fetcher accepts only exact configured public HTTPS origins,
  does not follow redirects or environment proxies, rejects encoded/oversized/MIME-
  mismatched bodies, and recomputes Core's SHA-256 commitment before decoding.
  Heavy deps imported lazily; missing dep → skip, never crash.
- **`attest.py`** — build canonical registration, suspension, rotation, and attestation bodies + `sign()` (EIP-191 over sorted-key
  compact JSON). Text V0 attestations include `modality`, `capability`,
  `assignment_id`, `epoch`, prompt/response hashes, an `evidence_hash`, and a
  coarse score for scorecard aggregation. Runtime capability advertisement is
  dependency-aware: image fidelity is present only with Pillow/ImageHash and
  video capabilities only with Pillow/ImageHash/PyAV, plus a non-empty
  validated witness-origin allowlist. Runtime registration and
  evidence are always signed; low-level unsigned helpers exist only for isolated tests.
  Registration and rotation advertise the immutable release tag as
  `software_version`; the base package version is not a sufficient rollout
  identity when multiple previews share it.
- **`main.py`** — entrypoint: `run()` (signed registration, optional stake gate,
  heartbeat, then assignment loop) and assignment-only `probe_round`. The loop
  polls text plus runtime-supported media modalities, independently verifies
  Core's challenge/witness commitment, and omits raw media URLs from signed evidence.
  It journals assignments before concurrent probing, isolates sibling failures,
  and uses Core's original `probe_latency_ms` for replayed completions.
  Tool-chain assignments verify and commit both hard-targeted stages before
  signing. A target worker's accepted-but-empty completion is failed evidence,
  not a transport error; coordinator dispatch failures remain inconclusive.
  `probe_round` returns the number of canaries actually
  attempted; one-shot checks use this to reject green-looking no-op probes.
  If `VALIDATOR_REQUIRE_STAKE=true`, missing stake config/deployment must raise
  a startup error before the Grid client starts; do not silently return success.
  The direct `python -m validator.main` module path must also print clean
  startup errors and exit nonzero, not traceback.
- **`cli.py`** — `aipg-validator prepare-wallet | init | check | dashboard | run | queue | suspend | rotate`.
  `prepare-wallet` uses the operating-system CSPRNG, writes a local signing
  identity atomically at mode `0600`, prints only the public address, and is
  idempotent. `init` reuses that prepared identity while adding the scoped API
  key. The remaining commands provide the capability/scorecard-aware health check with
  `--no-probe`; check reports the locally usable scorer set before registration
  and the authenticated operator's safe qualification progress afterward;
  stake-disabled preview check reports an explicit skip, while
  stake-required check fails closed on missing stake deps/config; startup
  config errors print one operator-facing line instead of tracebacks; the loop;
  local dashboard command; and explicit queue status/dead-letter recovery).
  `suspend` signs with the current registered wallet; `rotate` signs with the
  configured replacement wallet after Core reports the previous registration.
- **`__main__.py`** — module entrypoint for `python -m validator` and
  PyInstaller release binaries.
- **`update_check.py`** — bounded, notification-only GitHub release check. It
  validates tag syntax, ignores drafts, bypasses environment proxies, and
  constructs its own canonical release URL. It never downloads or executes an
  update; operators upgrade through the verified installer.
- **`dashboard.py`** — read-only localhost operator status page and
  `/status.json`. Uses the Python standard library only; shows Grid validator
  capability flags, the authenticated operator's safe qualification progress,
  and aggregate evidence scorecards; never render secrets, operator control
  groups, or private review references, and never bind beyond localhost by
  default. Invalid bind options must fail with a clean
  CLI error, not a Python traceback.

## Local Contracts

- **Canonical attestation form is load-bearing:** `attest._canonical` uses
  `json.dumps(..., sort_keys=True, separators=(",", ":"))` so the digest the grid recovers
  matches the one signed. Do not change the field set or serialization without the grid side.
  Never sign raw prompts, expected answers, or raw responses in V0; sign compact
  hashes so scorecards can stay private while evidence is still committed.
- **`outbox.py`** — private local SQLite state journal for Grid assignments and
  signed public envelopes. It records an assignment before the probe, atomically
  promotes it to a signed envelope, deduplicates by assignment, survives
  restarts, retries before new probes, and dead-letters after separate configured
  attempt/age bounds. `queue retry-dead` is the only automatic-state revival;
  ordinary polling must not silently revive reviewed dead work.
  Assignment-bound attestations must echo the Grid's returned probe
  `evidence_hash`; do not let the node invent a different hash after a targeted
  probe.
- **Signing identity must be coherent:** `Settings.validate()`, `prepare-wallet`, and `aipg-validator init`
  must reject malformed `VALIDATOR_WALLET` values and any
  `VALIDATOR_WALLET` / `VALIDATOR_PRIVATE_KEY` mismatch. If init receives a private key
  and no wallet, deriving the wallet is preferred to writing an unverifiable config.
  `attest.sign()` must also reject a payload whose `validator` field does not match
  the configured private key before sending it to core.
- **On-chain config must fail before Web3:** if `AIPG_TOKEN_ADDR` or
  `VALIDATOR_STAKING_ADDR` is set, `Settings.validate()` must reject malformed
  addresses as clean startup/config errors before `staking.py` constructs
  contracts or calls RPC.
- **Init must not write known-bad config:** required fields, currently the Grid API key,
  fail fast during `aipg-validator init` before `.env` is created.
- **Stake is in whole AIPG.** `stake_of` divides the raw 18-decimal balance by 10**18; compare
  against `Settings.MIN_STAKE` (also whole tokens). Staking is future economic authority; V0
  preview operation should run with `VALIDATOR_REQUIRE_STAKE=false`.
- **Scoring contract:** verdicts are exactly `healthy | slow | failed`. `failed` = empty/wrong/
  undecodable/wrong-dims/blank/pHash-outlier/static-loop; `slow` = correct but over the latency
  budget; `healthy` otherwise. Text echo canaries require the answer to be
  exactly the nonce after harmless quote/backtick wrappers are stripped; generated
  arithmetic QA canaries may accept a short answer phrase containing the expected
  numeric value, but not a larger number that merely contains it. Media pHash,
  motion, and latency thresholds are immutable constants of each versioned
  scoring policy, never operator configuration; changing one requires a new
  policy id. pHash uses Hamming distance, not equality, to absorb bounded
  cross-GPU nondeterminism. Assignment-bound JSON is parsed and canonicalized but must
  be the entire answer; retrieval requires exactly one token; numeric logic
  requires exactly one unambiguous integer.
- **A skipped check must not penalize a worker** — a missing optional dep returns ok/skip, not
  `failed`.
- **V0 fairness:** only execute the modality and capability in the Grid-issued
  assignment. Missing or unsupported assignment metadata is a skip, never a
  worker failure and never a reason to invent another target.
- **Media fetch and decode are fail-closed:** an empty origin allowlist, non-HTTPS/private
  origin, redirect, content encoding, wrong MIME/length/hash, timeout, or byte
  overflow is inconclusive infrastructure evidence, never a worker verdict.
  Authoritative image and video decoders run out of process with deadlines and
  resource bounds; a local decoder/process failure cannot become worker-failed
  evidence.
- **Image fidelity is dark and fail-closed:** `image.fidelity.v1` accepts only
  the versioned Core challenge contract and exactly three bound witnesses. Missing
  decoders, unsafe objects, malformed contracts, unusable references, and
  reference disagreement are inconclusive. Candidate decode/dimension/blank or
  pHash-outlier failures are worker failures only after all commitments verify.
  The scorer is not a live network capability until Core issuance and every
  media rollout gate are complete.
- **Video scoring is dark and fail-closed:** `video.contract.v1` accepts one
  committed candidate witness; `video.fidelity.v1` additionally requires two
  distinct reference workers and three committed witnesses. Unsafe transport,
  malformed or inconsistent timing contracts, missing PyAV, reference decode
  failure/disagreement, and local decoder timeout are inconclusive. Candidate
  malformed decode, contract, blank/static, or reference-outlier failures may
  produce failed evidence only after all commitments verify. Core has a
  separately gated, default-off `video.contract.v1` assignment/witness path;
  governed timing metadata and a real-workload canary are still required before
  operators enable it. Public preview binaries do not bundle the media extra.
- **Independent evidence verification:** before signing, the node must match
  assignment ID, Grid nonce, worker, model, modality, capability, and canary
  kind plus shared probe group; recompute prompt/response hashes and the
  canonical probe evidence hash; and score the returned output locally against
  Core's one-way expected-answer commitment. A binding mismatch is a skip. Core
  does not return its private verdict.
- **Sealed assignment compatibility:** a sealed assignment journal entry may
  contain only its opaque id, modality/capability metadata, and SHA-256 seal.
  Request the probe before requiring target, model, nonce, or challenge; accept
  those fields only from the terminal Core disclosure after recomputing and
  constant-time comparing the seal. A missing, mismatched, or mutated
  disclosure is a skip and must never produce signed evidence. Continue to
  accept an older unsealed Core response during the staged rollout.
- **No false targeted failures:** if a targeted probe endpoint is missing,
  disabled, or returns no committed output at all, skip attestation instead of
  recording `failed`. A verified token-limit result containing reasoning but no
  required visible output is still independently scorable failed evidence.
- **No green no-op checks:** `aipg-validator check` must fail clearly when no
  compatible text target exists and therefore no V0 canary was submitted.
- **Persist before send:** an assignment must enter the journal before the
  targeted request, then its attestation must atomically replace it before HTTP
  submission. Core acceptance deletes the envelope; delivery failure keeps it
  for replay. A queued assignment must not be probed again while its envelope is
  pending or dead-lettered.
- **Updates are notification-only:** a release-feed response may select a newer
  syntactically valid tag, but it is never execution authority. Installation
  remains an explicit operator action through checksums and GitHub provenance.
- **Lifecycle controls are not magic recovery:** suspension requires the current
  signing key and ordinary registration resumes it. Rotation requires a
  different configured key whose wallet has already been linked to the same
  Grid account. Operators must replace and revoke the previous scoped API key
  separately; a suspected compromise requires server-side revocation.

## Work Guidance

—

## Verification

- `./.venv/bin/python -m compileall validator`
- `./.venv/bin/python -m unittest discover -s tests`
- `./.venv/bin/aipg-validator --help`
- `./.venv/bin/python -m validator --help`

## Child DOX Index

—
