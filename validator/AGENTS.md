# validator — the node (config, stake, probing, attestation, loop, CLI)

## Purpose

The validator implementation: load config, optionally gate on on-chain stake, enumerate
available Grid targets, fire unpredictable canaries, score replies, sign attestations when
configured, and POST them in a loop when the Grid exposes the sink. V0 is CPU-only and
model-routed for text canaries; image/video scoring exists as design/scaffold until the Grid
adds targeted assignments and modality-aware probe jobs.

## Ownership

- **`config.py`** — env-driven `Settings` (grid URL + key, wallet/private key, Base RPC +
  contract addrs, `MIN_STAKE`/`REQUIRE_STAKE`, probe intervals + latency budgets, pHash tolerance).
  `Settings.validate()` enforces required fields, rejects malformed Grid URLs,
  rejects malformed EVM addresses for wallet/token/staking fields, validates the
  local dashboard port, and rejects a wallet/private-key mismatch.
  All env reads live here. Malformed numeric/boolean/URL/address env values must be reported
  through `Settings.validate()` as operator-facing config errors, not import-time
  tracebacks or downstream Web3 exceptions.
- **`staking.py`** — on-chain stake gate (`stake_of`, `assert_eligible`). Raises `NotDeployed`
  until `VALIDATOR_STAKING_ADDR` is set; honors `REQUIRE_STAKE=false` for pre-launch/dev.
- **`grid_client.py`** — async httpx client for grid endpoints: `list_models`,
  `validator_capabilities`, `validator_scorecards`, `validator_assignments`,
  `probe_assignment` (assignment-bound targeted), `list_workers`,
  `probe_worker` (legacy targeted), `chat` (v0 model-routed),
  `submit_attestation`.
  Each grid-only endpoint degrades gracefully (conservative capabilities,
  unavailable scorecards, empty list, `None`, or `False`) when not yet deployed.
  It sends both Grid-native `apikey` and OpenAI-compatible `Authorization:
  Bearer` headers with the same validator API key; keep that dual-header
  behavior unless core deliberately drops one auth style.
  `features.targeted_probe` is only a capability signal; only the explicit
  `targeted_probe_enabled=true` rollout flag may put the node or dashboard into
  targeted mode. Assignment-bound targeting is preferred over legacy
  worker-id targeting; if `/v1/validator/workers` advertises
  `/v1/validator/probe/{assignment_id}`, `list_workers` must return no legacy
  targets so `probe_round` uses `validator_assignments` instead.
- **`prober.py`** — text canaries (`echo` nonce + generated arithmetic `qa`) and `score()`;
  `is_text_model` heuristic skips media models in v0; `_strip_think` ignores
  reasoning-model chain-of-thought. Do not reintroduce static QA answer lists.
- **`media_prober.py`** — image/video canaries + scoring across structural, pHash-consensus, and
  video-motion axes. Heavy deps imported lazily; missing dep → skip, never crash.
- **`attest.py`** — `build()` the canonical attestation body + `sign()` (EIP-191 over sorted-key
  compact JSON). Text V0 attestations include `modality`, `capability`,
  `assignment_id`, `epoch`, prompt/response hashes, an `evidence_hash`, and a
  coarse score for scorecard aggregation. Unsigned (`signature=None`) only when
  no key is configured (dev). V0 assignment ids are validator-generated and
  marked `assignment_source=validator_v0`; V1 economic use must require
  Grid-issued assignment ids/nonces.
- **`main.py`** — entrypoint: `run()` (optional stake gate → probe loop), `probe_round`
  (Grid-issued assignments first, legacy targeted workers second, else v0
  model-routed), `_probe_assignment` / `_probe_worker` / `_probe_model`.
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
  nondeterminism).
- **A skipped check must not penalize a worker** — a missing optional dep returns ok/skip, not
  `failed`.
- **V0 fairness:** never send a text canary to a media model — gate model-routed probing
  through `prober.is_text_model` and targeted inventory through the worker's
  `job_types`, `api_formats`, and model-name hints. Missing targeted metadata is
  not text-capable by default. If targeted inventory has no text-capable workers,
  fall back to model-routed V0 probes instead of creating media-worker failures.
- **No false targeted failures:** if a targeted probe endpoint is missing, disabled, or
  returns no text, skip attestation instead of recording `failed`.
- **No green no-op checks:** `aipg-validator check` must fail clearly when no
  compatible text target exists and therefore no V0 canary was submitted.

## Work Guidance

—

## Verification

- `./.venv/bin/python -m compileall validator`
- `./.venv/bin/python -m unittest discover -s tests`
- `./.venv/bin/aipg-validator --help`
- `./.venv/bin/python -m validator --help`

## Child DOX Index

—
