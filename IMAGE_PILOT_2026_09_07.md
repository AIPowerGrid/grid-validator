# First-Party Image Calibration

## Decision

The existing image scorer distinguishes the two actual model outputs tested
here, but it does not prove exact model, seed or quantization execution. It
accepts a grayscale mutation of a color-specific image at zero pHash distance,
and accepts the wrong FLUX seed at the current distance boundary. Preserve
these misses; do not lower the threshold after observing this one scene.

No production policy, media issuance, account, reward or penalty setting was
changed. Cross-hardware and independently controlled reference gates remain
open. This is a first-party calibration, not a launch approval.

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

## Next Work

1. Evaluate color-sensitive comparison as a separate observational metric with
   legitimate color/codec variation controls. Do not silently change v1 consensus.
2. Freeze new evaluation scenes before testing proposed tolerances. Include
   supported samplers, image-to-image variants, quantizations and real hardware
   differences; the current one-scene result cannot qualify those cases.
3. Distinguish approximate visual agreement from exact workflow reproduction.
   pHash alone cannot certify a seed, model or quantization.
4. Complete source-frame adherence for video. Its separate preparation script
   was deferred, not executed, when image-backend access became available.
5. Complete governed recipes, immutable witness retention, independent reference
   qualification and real assignment-path testing before media rollout.
