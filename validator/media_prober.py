# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Image/video canaries + scoring.

Generative media can't be exact-matched, so we score on two CPU-light axes
(see DESIGN.md) — no GPU, no ML model:
  1. structural/liveness — decode, dimensions, not-blank, latency
  2. pHash consensus     — perceptual agreement across workers on one Core-issued seed
Video adds a motion check (sampled frames must perceptually differ).

Pillow + imagehash are imported lazily so a missing dep degrades a check to
"skip" rather than crashing the node.
"""

import secrets

# This generator is local preview scaffolding only. Authoritative media prompts
# and seeds must be issued privately by Core to a shared probe group. The large
# randomized combination space prevents this public helper from becoming a
# small enumerable answer set while that Core lane is being built.
_OBJS = (
    "elephant", "teapot", "bicycle", "lighthouse", "cactus", "violin",
    "dragon", "umbrella", "airship", "hourglass", "origami fox", "telescope",
)
_COLORS = (
    "crimson", "turquoise", "golden", "violet", "emerald", "obsidian",
    "cobalt", "coral", "silver", "amber", "indigo", "ivory",
)
_SETTINGS = (
    "underwater", "on the moon", "in a snowy forest", "in a neon city",
    "in a desert at dusk", "inside a glass observatory", "on a stormy coast",
    "in an overgrown library", "above a field of clouds", "beside a frozen lake",
)
_COMPOSITIONS = (
    "wide establishing view", "low-angle close view", "symmetrical composition",
    "overhead composition", "shallow depth of field", "layered foreground and background",
)
_LIGHTING = (
    "soft morning light", "hard rim lighting", "moonlit haze", "warm lantern light",
    "diffuse overcast light", "high-contrast studio lighting",
)
_VIDEO_ACTIONS = (
    "moving steadily from left to right", "turning slowly toward the camera",
    "rising through drifting mist", "circling a stationary landmark",
    "approaching while the camera pulls back", "crossing the frame as shadows move",
)


def make_media_canary(round_index: int, kind: str = "image") -> dict:
    del round_index
    obj = secrets.choice(_OBJS)
    color = secrets.choice(_COLORS)
    setting = secrets.choice(_SETTINGS)
    composition = secrets.choice(_COMPOSITIONS)
    lighting = secrets.choice(_LIGHTING)
    nonce = secrets.token_hex(3)
    action = f", {secrets.choice(_VIDEO_ACTIONS)}" if kind == "video" else ""
    prompt = f"a {color} {obj} {setting}{action}, {composition}, {lighting}, highly detailed"
    payload = {
        "prompt": prompt, "seed": secrets.randbits(63) or 1,
        "width": 512, "height": 512, "steps": 12, "n": 1,
    }
    if kind == "video":
        payload.update({"frames": 16, "fps": 8})
    return {"kind": kind, "nonce": nonce, "prompt": prompt, "payload": payload,
            "expect_w": 512, "expect_h": 512}


# ── Axis 1: structural ──────────────────────────────────────────────────────

def check_structure(canary: dict, image_bytes: bytes) -> tuple[bool, str]:
    """Decodes? right size? not blank/noise? Returns (ok, reason)."""
    try:
        import io
        from PIL import Image
    except ImportError:
        return True, "pillow-missing-skip"  # can't check; don't penalize the worker
    try:
        img = Image.open(io.BytesIO(image_bytes)); img.load()
    except Exception as e:
        return False, f"undecodable:{type(e).__name__}"
    if (img.width, img.height) != (canary["expect_w"], canary["expect_h"]):
        return False, f"wrong-dims:{img.width}x{img.height}"
    # Blank/solid or pure-noise detection via grayscale std-dev.
    import statistics
    px = list(img.convert("L").getdata())
    sample = px[:: max(1, len(px) // 4096)]
    sd = statistics.pstdev(sample) if len(sample) > 1 else 0
    if sd < 3:
        return False, "blank-or-solid"
    return True, "ok"


# ── Axis 2: perceptual-hash consensus ───────────────────────────────────────

def phash(image_bytes: bytes) -> str | None:
    try:
        import io
        import imagehash
        from PIL import Image
        return str(imagehash.phash(Image.open(io.BytesIO(image_bytes))))
    except ImportError:
        return None
    except Exception:
        return None


def phash_distance(a: str, b: str) -> int:
    """Hamming distance between two hex pHash strings."""
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def consensus_ok(my_hash: str, peer_hashes: list[str], tolerance: int = 12) -> bool:
    """True if my output perceptually agrees with the majority of peers.

    tolerance ~12/64 bits absorbs cross-GPU/library nondeterminism while still
    catching a different model or a cached/unrelated image (distance >> 12)."""
    if not peer_hashes:
        return True  # no peers this round → can't disagree; defer to other axes
    agree = sum(1 for h in peer_hashes if phash_distance(my_hash, h) <= tolerance)
    return agree >= (len(peer_hashes) + 1) // 2


# ── Scoring ─────────────────────────────────────────────────────────────────

def score_image(canary: dict, image_bytes: bytes, latency_s: float,
                peer_hashes: list[str] | None = None,
                latency_budget_s: float = 60) -> tuple[str, dict]:
    """Combine the axes into healthy|slow|failed plus a detail dict for attestation."""
    detail: dict = {}
    ok, reason = check_structure(canary, image_bytes)
    detail["structure"] = reason
    if not ok:
        return "failed", detail

    h = phash(image_bytes)
    if h is not None:
        detail["phash"] = h
        if peer_hashes is not None and not consensus_ok(h, peer_hashes):
            detail["consensus"] = "outlier"
            return "failed", detail

    return ("slow" if latency_s > latency_budget_s else "healthy"), detail


def score_video(canary: dict, frames: list[bytes], latency_s: float,
                latency_budget_s: float = 120) -> tuple[str, dict]:
    """Video = structural per-keyframe + a motion check (frames must differ)."""
    detail: dict = {"frame_count": len(frames)}
    if len(frames) < 2:
        return "failed", detail
    # Per-keyframe structural on first/last.
    for label, fb in (("first", frames[0]), ("last", frames[-1])):
        ok, reason = check_structure(canary, fb)
        detail[f"{label}_frame"] = reason
        if not ok:
            return "failed", detail
    # Motion: first vs last must perceptually differ (else it's a looped still).
    a, b = phash(frames[0]), phash(frames[-1])
    if a and b:
        detail["motion_dist"] = phash_distance(a, b)
        if detail["motion_dist"] < 2:
            detail["motion"] = "static-loop"
            return "failed", detail
    return ("slow" if latency_s > latency_budget_s else "healthy"), detail
