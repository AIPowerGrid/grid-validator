# First-Party Video Calibration

## Decision

Real LTX Director outputs exercise the existing bounded decoder and scorer.
Basic structural validation catches several defective outputs but accepts
reversed playback and a two-frame oscillation. Reference comparison rejects
those two mutations in this small pilot. Neither result establishes general
temporal understanding, model identity or a calibrated fleet false-positive
rate. Keep public media issuance and automatic economic authority gated.

## Scope And Provenance

- One owned RTX 5090, one synthetic text-to-video scene, two explicit seeds.
- LTX Director 2.0 recipe using LTX-2.3 distilled 1.1 Q4_K_M, with its existing
  two-stage sampler configuration. The recipe declares `deterministic: false`.
- Four accepted fresh executions, alternating the two seeds. Each output is
  512x512, 49 frames at 24 FPS, decoded duration 49/24 seconds.
- ComfyUI 0.25.0, commit `f026b01ba576d98442839861a0eb0046bc2250d3`, Python
  3.12.3, PyTorch 2.12.0+cu130. Seven referenced weight files and 825 Python
  source files are privately hashed. Their hashes are unchanged between the
  initial and revised preparation.
- Existing validator source at `8280fde`; bounded PyAV 17.1.0 decoder,
  Pillow 12.3.0 and ImageHash 4.3.2. Independent ffprobe frame counts, dimensions
  and FPS agree; per-frame decoded RGB hashes and timestamps are retained.

Generation used the existing first-party backend directly, only after empty
queue checks. No restarts, model replacement, shared-cache clearing, other-job
cancellation, production account edits or authority flags were needed. This
does not test the Grid submission, billing, signed assignment or quorum path.

## Cache Control

The initial attempt generated two fresh clips, then both samplers were cached
on the first same-seed repeat. Relabelled node IDs and output filenames did
not force inference: ComfyUI keys these outputs by input/ancestor signatures.
The harness stopped at the cache assertion, retained that history, and did not
submit its fourth request. That cached result is not a successful repeat.

A separate frozen revision inserts an existing integer calculator into the
seed input. Its different expressions evaluate to the same intended seed,
while changing the ancestor signature. Independent harness checks verify that
no other effective generation input changes. All four revised histories report
both samplers uncached. There are six uncached renders in total across the two
attempts, not seven independent generations.

## Repeat Measurements

| Comparison | Decoded RGB frames | Maximum frame pHash distance | Mean motion difference |
| --- | --- | ---: | ---: |
| First seed, two uncached repeats | Identical | 0 | 0 |
| Second seed, two uncached repeats | Identical | 0 | 0 |
| Different seeds, same scene/settings | Different | 34 | 5.917 |

Both same-seed pairs have different MP4 file hashes despite identical decoded
frames. Preserve file hashes as evidence commitments, but do not require equal
container bytes as a visual fidelity rule. Four server-reported execution
intervals are 47.290, 47.752, 47.739 and 47.992 seconds. These are not an SLA,
client-to-Grid latency measurements or independent timing attestations.

## Captured-Byte Scoring

The unchanged `score_video_witnesses` verifies commitments and decodes actual
captured/derived bytes through a mocked HTTP transport. Witness identities are
synthetic roles, not independent operators. Latency is fixed to 1000ms in this
scorer harness to isolate content decisions; `healthy` below is not measured
latency qualification. Existing pHash/motion thresholds were not tuned.

| Input / condition | Existing policy result |
| --- | --- |
| Four original clips, contract policy | All healthy |
| Repeated single frame | Failed: repeated-still |
| Shortened clip | Failed: frame-count and duration |
| Wrong dimensions | Failed: dimensions |
| Wrong FPS | Failed: FPS and duration |
| Truncated container | Failed: candidate-decode-failed |
| Reversed frames, contract policy | Healthy: missed semantic/order mutation |
| Alternating two frames, contract policy | Healthy: missed temporal-consistency mutation |
| Same-seed owned render with two agreeing owned references | Healthy |
| Wrong seed with agreeing references | Failed: candidate-outlier |
| Reversed frames with agreeing references | Failed: candidate-outlier |
| Alternating two frames with agreeing references | Failed: candidate-outlier |
| Corrupt candidate with agreeing references | Failed: candidate-decode-failed |
| Disagreeing references, valid or corrupt candidate | Inconclusive: references-disagree |
| Corrupt reference, valid or corrupt candidate | Inconclusive: reference-decode-failed |
| Commitment mismatch | Inconclusive: witness-fetch-or-commitment-failed |

The owned-reference comparison uses the initial attempt's uncached first clip
as candidate and two revised same-seed clips as references. All originate from
the same operator/hardware. No independent-reference qualification is implied.

Two harness mistakes are retained rather than hidden. The frozen capture
auditor initially used the decoder's wrong call signature; a separately hashed
adapter constructs `VerifiedMediaWitness` and calls the unchanged decoder.
One corrupt-reference case reused the candidate's URL and was correctly
rejected before decode. A two-case supplement uses distinct URLs and proves
reference-decode failure takes precedence for both valid and corrupt candidates.

## Verification And Evidence

- Existing media suite: 37 tests passed, no skips.
- Private harness checks: four tests passed, covering witness adaptation,
  failure-category preservation, seed-expression equivalence and provenance.
- Capture audit independently repeated with identical canonical summary bytes.
- Twenty captured-byte scoring cases repeated with identical summaries; two
  distinct-URL reference-failure cases also repeated identically.
- Raw prompts, clips, node identities, filesystem inventories and server
  addresses remain private. No new public challenge answer key is introduced.

Private artifact SHA-256:

- Revised manifest: `dfe9a8bd264db55e1fbdc82d80c449d37e44c6e7de9ab4f1b8c4cf4a8d24959d`.
- Provenance: `710e0a08eb1399e57df2a15fb2d43f38dfe4f2e87e2069642a035fd2bbe97221`.
- Completed capture index: `efea11efd2ceef4a76be9003e11cd4b6ab37c645334e6905fc9e76c293b55ca2`.
- Independent capture summary: `b43f81614742ba682622f1bad3e9312658a1f3ac2627fe8e5a47f7511c8c7c18`.
- Scorer summary: `807313e3b8af4c8a6f554c89b531a7c5bbf5e9b0719fddafaade29e16aeaa85f`.
- Reference-failure supplement: `7dc2891299bcda16703bf2d1f3dc7984e47469cf6a9646a13481b8c3e97a607f`.

## Next Gates

1. Test additional scenes and camera/motion types, source-image adherence,
   supported hardware and runtime variants before choosing tolerances.
2. Test actual wrong-model video substitutions; a wrong seed is not one.
3. Treat structural/motion checks as basic conformance, not semantic temporal
   consistency. Any proposed loop detector needs legitimate-loop controls.
4. Complete the image pilot and independently controlled reference enrollment.
5. Establish a governed recipe, immutable witness retention, real assignment
   delivery and fresh media-capable validators before public media issuance.

The full text compatibility, substitution, adversarial and shadow-rollout goal
remains open. This first-party video pilot does not supersede its gates.
