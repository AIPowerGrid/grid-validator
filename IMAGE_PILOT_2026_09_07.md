# First-Party Image Calibration

## Decision

The existing image scorer distinguishes the two actual model outputs tested
here, but it does not prove exact model, seed or quantization execution. It
accepts a grayscale mutation of a color-specific image at zero pHash distance,
and accepts the wrong FLUX seed at the current distance boundary. Preserve
these misses; do not lower the threshold after observing this one scene.

No production policy, media issuance, account, reward or penalty setting was
changed. The same-artifact Apple/NVIDIA follow-up below passes the tested
honest controls. Broader cross-hardware tolerance and independently controlled
reference qualification remain open. This is calibration, not launch approval.

## Frozen Workload

- One owned RTX 5090 running the existing image backend, verified online before
  testing. Two existing text-to-image recipes: Z-Image Turbo and FLUX.2 Klein.
- One private synthetic scene, two explicit seeds, three renders per
  model/seed combination: twelve 512x512 PNG outputs.
- Recipe-default sampling settings retained: Z-Image eight steps,
  `res_multistep`/`simple`, CFG 1; FLUX four steps, `euler`, its existing Flux2
  scheduler and CFG 1. Both recipes declare `deterministic: false`.
- Equivalent integer seed expressions change the cache ancestry without
  changing the effective seed. Every completed history reports its sampler
  uncached. Empty queue checks precede each request; only owned job histories
  and outputs are collected. No shared-cache clearing or service restart.
- ComfyUI 0.25.0 at `0a92ed161e6fa18eb169d96d64b4c279cf280dc5`, reported
  PyTorch `2.9.0.dev20250731+cu128`. Five referenced weight files and 1,527
  Python source files are privately hashed.
- Validator scorer source at `2580791`, with unchanged distance tolerance 12.

The two diffusion files' safetensors headers contain BF16 tensors: 453 tensors
for Z-Image and 149 for FLUX. The shared text encoder also stores BF16. The
FLUX recipe display name contains `FP8`, but that is not the file's stored dtype.
Headers and file sizes were inspected after capture; full file hashes were
recorded before capture. None of this proves runtime compute dtype, upstream
publisher authenticity or equivalence to another quantized artifact.

## Honest Repeats

All four model/seed groups have identical decoded RGB pixels across their
three uncached renders. All twelve within-group pair comparisons have pHash
distance zero, but different PNG file hashes. Use file SHA-256 to commit
specific evidence bytes, not as a rule requiring identical image containers.

The four local witness groups all return `healthy`. These are four correlated
first-party groups from one scene and backend, not a fleet false-positive bound.
The captured-byte scorer uses mocked HTTP, synthetic distinct role identities
and fixed 1000ms witness latency; its healthy label is not latency qualification.
Actual server execution intervals are retained separately: Z-Image 1.368-4.678
seconds and FLUX 0.529-3.262 seconds. These short sequential runs are not an SLA
or loaded-worker benchmark, and non-sampler caching remains permitted.

## Deliberate Mutations

| Comparison / input | Existing policy result |
| --- | --- |
| FLUX substituted for Z-Image, first seed | Failed; distance 28 to both agreeing references |
| Z-Image substituted for FLUX, first seed | Failed; distance 28 |
| FLUX substituted for Z-Image, second seed | Failed; distance 32 |
| Z-Image substituted for FLUX, second seed | Failed; distance 32 |
| Wrong Z-Image seed, either direction | Failed; distance 26 |
| Wrong FLUX seed, either direction | Healthy; distance 12 is accepted |
| Remove all color from one Z-Image output | Healthy; distance 0 |
| JPEG quality 90 or 40 re-encoding | Healthy; distance 0 |
| Wrong dimensions | Failed: candidate-wrong-dimensions |
| Blank output | Failed: candidate-blank-or-solid |
| Truncated PNG | Failed: candidate-undecodable |
| Disagreeing references, valid or corrupt candidate | Inconclusive: references-disagree |
| Corrupt reference | Inconclusive: reference structure unusable |

The four directed wrong-model comparisons represent two underlying seed-paired
comparisons, not four independent workloads. Same numeric seeds do not mean
equivalent latent noise across these architectures. The experiment substitutes
actual captured outputs in the local scorer; it does not impersonate a worker
on the public Grid or test a dishonest live registration.

Grayscale acceptance is a real content blind spot: the policy's grayscale pHash
discards color information. JPEG acceptance demonstrates compression tolerance,
not proof that all visual detail or a requested encoding is preserved. The
scorer does not evaluate object counts or other semantic prompt requirements.

## Verification

- Twelve completed captures are bound to request graphs, prompt IDs, histories,
  output hashes and uncached-sampler events.
- Independent Pillow RGB decoding checks dimensions and pixel hashes alongside
  the existing killable image decoder.
- Twenty-one unchanged-policy scoring cases completed. Re-running the entire
  capture/scoring audit reproduced the same canonical summary bytes and control
  files; no new GPU work was performed for the repeat audit.
- Existing media suite: 37 tests passed, no skips. Private graph-invariant
  tests: two methods passed, including both recipes and repeated seed values.
- New image harness files pass Ruff checks and formatting. No public runtime
  code is changed by this report.
- Image backend and bridge remained active; final queue counts were zero.
  The temporary SSH control connection was closed. Credentials were not written
  to scripts, manifests, repository files or command-line arguments.

Private artifact SHA-256:

- Manifest: `f210a1dabe32af89d0a9b14ac6880a00926ac8b84d499554915f08b6735d3119`.
- Provenance: `679bc68b5d478566ed7124916b68fed56ab89ffebf8b7db3d6a25b9edcc2f08a`.
- Capture index: `d584ac82527582c4f39ec4cfa7981cf191278f18af947489e73a5d0c10f50734`.
- Reproduced summary: `d04eba433a8adc30e7edc468d7c0c995634e8a16a7a3a913b54a54185d09c018`.
- Stored-dtype supplement: `1f384e48721501a4c9cba25ccba724e92175ddbaafae614593c4891bcbd894f9`.

## Same-Artifact Apple/NVIDIA Follow-Up

Six additional uncached Z-Image renders on an owned Apple M3 Max are compared
with the six frozen RTX 5090 Z-Image outputs above. This is actual inference on
two hardware/runtime stacks, not a transformed-image stand-in. The same one
private scene and two seeds each have three executions per stack.

### Provenance And Controls

- The exact Z-Image, Qwen encoder and VAE files are copied read-only from the
  image host and SHA-256 verified before inference. No production model,
  service, recipe, registration or queue is changed.
- The isolated local ComfyUI checkout pins the same upstream commit as the
  CUDA capture. All 680 overlapping non-custom serving Python files match.
- Apple M3 Max, 128 GiB memory, macOS 26.2, Python 3.12.11 and Torch 2.9.0.
  The runtime reports MPS diffusion/VAE execution with BF16 weights/VAE and a
  CPU FP16 text encoder. Do not describe every stage as GPU execution or equate
  stored weight dtype with every intermediate operation's compute precision.
- The CUDA baseline uses a different OS, Python and development Torch build.
  Hardware, runtime and device placement differ together; this experiment does
  not isolate which one causes pixel differences.
- The numeric seed replaces only an equivalent seed-expression node, and an
  owned output prefix changes. Two graph-invariant tests verify that adapter.
  The local runtime disables custom/API nodes, uses offline model access and
  cache-none. All six histories prove successful, uncached sampler execution.
- The owned loopback runtime is stopped after capture. The existing production
  worker is not stopped or unloaded. No new remote inference was needed.

### Results With Unchanged V1

| Comparison | Result |
| --- | --- |
| Same-seed repeats within Apple | Identical decoded RGB; all six pair distances 0 |
| Same-seed repeats within NVIDIA | Identical decoded RGB; all six pair distances 0 |
| Six paired Apple/NVIDIA outputs | Different decoded RGB; all pHash distances 0 |
| Apple candidate, NVIDIA references | 6/6 healthy, no observed false flags |
| NVIDIA candidate, Apple references | 6/6 healthy, no observed false flags |
| Held-out Apple repeat against other two same-seed repeats | 2/2 healthy |
| FLUX substituted for Apple Z-Image, or reverse | 4/4 failed; distances 28 and 32 |

There are only two underlying seed groups from one scene. Bidirectional
evaluations and repeated renders are correlated, not 12 independent honest
trials or four independent substitution trials. The FLUX outputs are reused
from the CUDA capture; this does not establish same-FLUX cross-hardware behavior.
The unchanged tolerance is 12. No threshold was fitted to these results.

Exact RGB matching would reject these honest cross-platform results. pHash
accepts them but still has the color and seed blind spots measured above; this
follow-up does not resolve those misses or establish model/quant identity.

Apple server execution intervals are 14.016-17.214 seconds. Cache policies,
device placement and runtime versions differ from the earlier CUDA runs, so
these numbers are not a controlled speed comparison or production latency SLA.
Scorer latency remains synthetic 1000ms with actual captured bytes delivered
through mocked HTTP; reference identities are synthetic and first-party.

### Audit And Reproduction

The capture manifest, graphs, histories, bytes, model/source hashes and cleanup
are verified before scoring. Independent Pillow decoding agrees with the
bounded decoder's pHashes. Eighteen scoring cases complete; two full offline
audits reproduce identical canonical summary bytes without new inference.

The frozen auditor had two reporting defects: it expected a dictionary instead
of the scorer's `(outcome, detail)` tuple, then could not serialize NumPy integer
distances. Separate hashed adapters preserve the original sources and map these
representations without changing verdicts, distances or policy. Failed audit
attempts are harness failures, not worker failures. Three adapter tests and two
graph tests pass. The unchanged media suite passes 37 tests with no skips.
The reused capture runner's cosmetic `/12` progress denominator is not the
schedule: the manifest and six successful receipts are authoritative.

Private artifact SHA-256:

- Manifest: `6ecc59be539725e4ef5bfc3920167feb2c2804b334fcd291ae8ff1054f458252`.
- Provenance: `de67e2fc1c7cf6ada9b6b9ca0bca6f8da04b7af87f617242d9cdc004fee97030`.
- Capture index: `5f98d0947e7569a37385d0fd2f21125e6e1d12c78ecbe24d5f82bf86369aa739`.
- Reproduced summary: `8f1b7a844a92288236843f8098d74f09d70fe9792b37ab15227b1b6c3da83d01`.
- Audit adapter provenance: `0937b466bd186e83a2063eb970271cd7a6ef8eabe60f513f485f99957e4a9273`.
- Runtime cleanup: `20a801a8631a8116801835503b6980298d70360a7e6fbf19977812c7050b5062`.

## Img2Img Sampler Follow-Up

Twelve additional uncached Z-Image img2img renders exercise two samplers
enumerated by the deployed recipe: `res_multistep` and `euler`. Each uses two
reused seeds and three repeats. The source is one owned synthetic image from
the first CUDA study, with its original scene description reused as the prompt.
This is a reconstruction-style calibration, not a held-out edit-instruction
test or a new independent scene population.

### Provenance And Controls

- The captured `z-image-turbo-i2i.json` bytes match deployed Core
  `c42dd8d12556267f2c0edda02c1336cfceef6fbc`. Recipe enumeration establishes
  supported parameter choices, not governed certification or determinism.
- The same isolated MPS stack and three SHA-256-pinned weight files from the
  Apple follow-up are reused. Settings are 512x512, eight steps, CFG 1,
  `simple` scheduler, denoise 0.7 and the recipe's sampling shift 3.
- The source PNG is hash-bound before upload and retrieved unchanged before
  inference. Captured graphs preserve source -> VAE encode -> sampler wiring.
  Only declared generation inputs and the owned output prefix change.
- Every own history reports successful uncached sampler execution, with empty
  queues before and after. No public Grid jobs, shared service restarts, worker
  changes or new model downloads are involved. The owned loopback runtime
  stopped; postflight weight/source hashes match preflight.

### Results With Unchanged V1

| Comparison | Result |
| --- | --- |
| Within-setting repeats | All 12 pair comparisons have identical RGB and pHash distance 0 |
| Candidate and two references with matching source/seed/sampler | 4/4 healthy, distance 0 |
| Same source/seed, deliberately wrong sampler for both references | 4/4 healthy; distances 0 or 2 |
| Return the untouched source PNG instead of running img2img | 4/4 healthy; distances 4 or 6 |

The four matching groups have no observed false flags. Cross-sampler decoded
pixels differ, but pHash does not reliably distinguish these workflow choices.
The deliberately mismatched references are a configuration control, not evidence
of dishonest workers. A real comparison must bind the complete requested recipe
and parameters before interpreting output disagreement.

Source-copy acceptance demonstrates that this similarity rule cannot establish
img2img execution. It does not show that a required semantic edit was omitted:
the prompt described the existing scene, and the scorer has no edit evaluator.
Blindly rejecting every unchanged source would also need legitimate no-op and
low-denoise controls. Keep source-copy detection and requested-edit adherence
separate from model-identity claims.

These twelve scorer cases use actual bytes with mocked witness HTTP, synthetic
role identities and 1000ms latency. There are only four correlated setting/seed
groups, two seed values and one source scene, not twelve independent trials.
Recorded execution intervals are 14.203-15.083 seconds on the shared Mac;
this is not an exclusive-idle or loaded-fleet benchmark. Tolerance remains 12,
with no post-hoc tuning or authority change.

### Verification

Two complete offline audits reproduce identical canonical summary bytes. They
bind the frozen harness, validator sources, recipe, graphs, submission receipts,
histories, outputs and runtime cleanup; independent Pillow decoding agrees with
the bounded decoder. Four private graph/input tests and 37 existing media tests
pass with no skips. New private harness files pass Ruff lint and formatting.

Private artifact SHA-256:

- Manifest: `8976ec580b84cfca4d6202256196cd63827671ce709d04eff0d3ec28a89e7d62`.
- Provenance: `591aa2f5261875b333d24f7bb172a321d8fde2badec538549b59cc1d7799f859`.
- Capture index: `3288e2ea16c4d236fb4ce4fe83cffe4501335dcee2b8b699965b0bce3ba7edf8`.
- Reproduced summary: `189a9d9bb12df9f7e0ad11d99ebdb6e8f5c7f7d1edced589d8f296255a1d2353`.
- Auditor: `54b2d269824cfaa01fa19342a60faeed89436e1fdee3a1fa22d5aac766ca44f1`.
- Runtime cleanup: `c02342668f27f19752cb8f244279aaae82cd4ce6eb22e58294734b62eee49b90`.
- Postflight: `7b60478ba1efe1f76267ee6fb8859df375f7df27044e44d501bb05b047630502`.

## Next Work

1. Evaluate color-sensitive comparison as a separate observational metric with
   legitimate color/codec variation controls. Do not silently change v1 consensus.
2. Freeze new evaluation scenes before testing proposed tolerances. Include
   additional supported samplers, edit instructions, denoise levels,
   quantizations and real hardware differences. The two img2img sampler choices
   above narrow the workflow gap but cannot qualify these broader cases.
3. Distinguish approximate visual agreement from exact workflow reproduction.
   pHash alone cannot certify a seed, model or quantization.
4. Review the completed [video source-adherence and splice experiments](VIDEO_PILOT_2026_09_07.md).
   First-frame-only checking is insufficient; measured source distances do not
   themselves implement a source-binding policy.
5. Complete governed recipes, immutable witness retention, independent reference
   qualification and real assignment-path testing before media rollout.
