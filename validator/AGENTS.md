# validator — the node (config, stake, probing, attestation, loop, CLI)

## Purpose

The validator implementation: load config, register a linked signing identity,
optionally gate on on-chain stake, consume Grid-issued assignments, fire
unpredictable targeted canaries, score replies, sign attestations, and POST them
in a loop. V0 is CPU-only and assignment-bound for text. The assignment loop
can consume deterministic image-fidelity work only when the optional media
dependencies and an explicit HTTPS witness-origin allowlist are present; Core
still issues no image work until its independent-reference rollout gates pass.
video scoring remains design/scaffold.

## Ownership

- **`config.py`** — env-driven `Settings` (grid URL + key, wallet/private key, Base RPC +
  contract addrs, `MIN_STAKE`/`REQUIRE_STAKE`, probe intervals + latency budgets,
  pHash tolerance, and exact public HTTPS media origins/byte/time limits).
  `Settings.validate()` enforces required fields, rejects malformed Grid URLs,
  rejects malformed EVM addresses for wallet/token/staking fields, validates the
  local dashboard port, and rejects a wallet/private-key mismatch.
  All env reads live here. Malformed numeric/boolean/URL/address env values must be reported
  through `Settings.validate()` as operator-facing config errors, not import-time
  tracebacks or downstream Web3 exceptions.
- **`staking.py`** — on-chain stake gate (`stake_of`, `assert_eligible`). Raises `NotDeployed`
  until `VALIDATOR_STAKING_ADDR` is set; honors `REQUIRE_STAKE=false` for pre-launch/dev.
- **`grid_client.py`** — async httpx client for validator registration,
  heartbeat, capabilities, scorecards, assignments, assignment-bound targeted
  probes, worker inventory, and attestation submission.
  Each grid-only endpoint degrades gracefully (conservative capabilities,
  unavailable scorecards, empty list, `None`, or `False`) when not yet deployed.
  It sends both Grid-native `apikey` and OpenAI-compatible `Authorization:
  Bearer` headers with the same validator API key; keep that dual-header
  behavior unless core deliberately drops one auth style.
  Assignment and probe endpoints fail closed when absent. Worker inventory is
  dashboard-only and must never become an alternate targeting authority.
- **`prober.py`** — independent text scoring for randomized exact-instruction,
  arithmetic, strict-JSON, context-retrieval, multistep-logic, and exact
  single-function-call, two-stage tool-chain, and stop-sequence commitments;
  legacy local canary helpers remain for isolated tests. `is_text_model`
  heuristic skips media models in v0; `_strip_think` ignores reasoning-model
  chain-of-thought. Do not reintroduce static QA answer lists.
- **`media_prober.py`** — image/video canaries + scoring across structural,
  pHash-consensus, and video-motion axes. Its local preview generator uses
  cryptographic prompt/seed selection and is never an authority; shared media
  challenges must come from Core. Its dark `image.fidelity.v1` scorer requires
  one candidate plus two distinct committed references, verifies every witness,
  treats reference disagreement as inconclusive, and fails an outlier candidate
  only after the references agree. The witness fetcher accepts only exact configured public HTTPS origins,
  does not follow redirects or environment proxies, rejects encoded/oversized/MIME-
  mismatched bodies, and recomputes Core's SHA-256 commitment before decoding.
  Heavy deps imported lazily; missing dep → skip, never crash.
- **`attest.py`** — build canonical registration/attestation bodies + `sign()` (EIP-191 over sorted-key
  compact JSON). Text V0 attestations include `modality`, `capability`,
  `assignment_id`, `epoch`, prompt/response hashes, an `evidence_hash`, and a
  coarse score for scorecard aggregation. Runtime capability advertisement is
  dependency-aware: image fidelity is present only with the media extra and a
  non-empty validated witness-origin allowlist. Runtime registration and
  evidence are always signed; low-level unsigned helpers exist only for isolated tests.
- **`main.py`** — entrypoint: `run()` (signed registration, optional stake gate,
  heartbeat, then assignment loop) and assignment-only `probe_round`. The loop
  polls text plus runtime-supported media modalities, independently verifies
  Core's challenge/witness commitment, and omits raw media URLs from signed evidence.
  Tool-chain assignments verify and commit both hard-targeted stages before
  signing. A target worker's accepted-but-empty completion is failed evidence,
  not a transport error; coordinator dispatch failures remain inconclusive.
  `probe_round` returns the number of canaries actually
  attempted; one-shot checks use this to reject green-looking no-op probes.
  If `VALIDATOR_REQUIRE_STAKE=true`, missing stake config/deployment must raise
  a startup error before the Grid client starts; do not silently return success.
  The direct `python -m validator.main` module path must also print clean
  startup errors and exit nonzero, not traceback.
- **`cli.py`** — `aipg-validator init | check | dashboard | run` (interactive
  `.env` at chmod 600; capability/scorecard-aware health check with
  `--no-probe`; stake-disabled preview check reports an explicit skip, while
  stake-required check fails closed on missing stake deps/config; startup
  config errors print one operator-facing line instead of tracebacks; the loop;
  local dashboard command).
- **`__main__.py`** — module entrypoint for `python -m validator` and
  PyInstaller release binaries.
- **`dashboard.py`** — read-only localhost operator status page and
  `/status.json`. Uses the Python standard library only; shows Grid validator
  capability flags and aggregate evidence scorecards; never render secrets or
  bind beyond localhost by default. Invalid bind options must fail with a clean
  CLI error, not a Python traceback.

## Local Contracts

- **Canonical attestation form is load-bearing:** `attest._canonical` uses
  `json.dumps(..., sort_keys=True, separators=(",", ":"))` so the digest the grid recovers
  matches the one signed. Do not change the field set or serialization without the grid side.
  Never sign raw prompts, expected answers, or raw responses in V0; sign compact
  hashes so scorecards can stay private while evidence is still committed.
- **`outbox.py`** — private local SQLite delivery queue for signed public
  envelopes. It deduplicates by assignment, survives restarts, retries before
  new probes, and dead-letters after the configured attempt/age bounds.
  Assignment-bound attestations must echo the Grid's returned probe
  `evidence_hash`; do not let the node invent a different hash after a targeted
  probe.
- **Signing identity must be coherent:** `Settings.validate()` and `aipg-validator init`
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
  numeric value, but not a larger number that merely contains it. pHash uses
  Hamming distance vs `PHASH_TOLERANCE`, never equality (absorbs cross-GPU
  nondeterminism). Assignment-bound JSON is parsed and canonicalized but must
  be the entire answer; retrieval requires exactly one token; numeric logic
  requires exactly one unambiguous integer.
- **A skipped check must not penalize a worker** — a missing optional dep returns ok/skip, not
  `failed`.
- **V0 fairness:** only execute the modality and capability in the Grid-issued
  assignment. Missing or unsupported assignment metadata is a skip, never a
  worker failure and never a reason to invent another target.
- **Media fetch is fail-closed:** an empty origin allowlist, non-HTTPS/private
  origin, redirect, content encoding, wrong MIME/length/hash, timeout, or byte
  overflow is inconclusive infrastructure evidence, never a worker verdict.
- **Image fidelity is dark and fail-closed:** `image.fidelity.v1` accepts only
  the versioned Core challenge contract and exactly three bound witnesses. Missing
  decoders, unsafe objects, malformed contracts, unusable references, and
  reference disagreement are inconclusive. Candidate decode/dimension/blank or
  pHash-outlier failures are worker failures only after all commitments verify.
  The scorer is not a live network capability until Core issuance and every
  media rollout gate are complete.
- **Independent evidence verification:** before signing, the node must match
  assignment ID, Grid nonce, worker, model, modality, capability, and canary
  kind plus shared probe group; recompute prompt/response hashes and the
  canonical probe evidence hash; and score the returned output locally against
  Core's one-way expected-answer commitment. A binding mismatch is a skip. Core
  does not return its private verdict.
- **No false targeted failures:** if a targeted probe endpoint is missing, disabled, or
  returns no text, skip attestation instead of recording `failed`.
- **No green no-op checks:** `aipg-validator check` must fail clearly when no
  compatible text target exists and therefore no V0 canary was submitted.
- **Persist before send:** an attestation must enter the outbox before the HTTP
  request. Core acceptance deletes it; delivery failure keeps it for replay.
  A queued assignment must not be probed again while its envelope is pending.

## Work Guidance

—

## Verification

- `./.venv/bin/python -m compileall validator`
- `./.venv/bin/python -m unittest discover -s tests`
- `./.venv/bin/aipg-validator --help`
- `./.venv/bin/python -m validator --help`

## Child DOX Index

—
