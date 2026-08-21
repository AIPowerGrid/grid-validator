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

import asyncio
import hashlib
import logging
import re
import secrets
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx

from .config import normalize_media_origins

# httpx's INFO line includes the full URL, including presigned object query
# credentials. Never emit those URLs into validator logs.
logging.getLogger("httpx").setLevel(logging.WARNING)

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_MAX_IMAGE_DIMENSION = 4096
_MAX_IMAGE_PIXELS = 4096 * 4096
_ALLOWED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
_ALLOWED_MEDIA_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "video/mp4",
        "video/webm",
    }
)


class MediaWitnessError(ValueError):
    """A media witness is unsafe, malformed, or does not match its commitment."""


@dataclass(frozen=True)
class VerifiedMediaWitness:
    body: bytes
    sha256: str
    byte_count: int
    content_type: str


def media_dependencies_available() -> bool:
    try:
        import imagehash  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError:
        return False
    return True


def _url_origin(url: str) -> str:
    parsed = urlsplit(url)
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise MediaWitnessError("media URL must be HTTPS without credentials or fragments")
    try:
        host = parsed.hostname.encode("idna").decode("ascii").lower()
        port = parsed.port
    except (UnicodeError, ValueError) as exc:
        raise MediaWitnessError("media URL host or port is invalid") from exc
    authority = f"[{host}]" if ":" in host else host
    return f"https://{authority}{f':{port}' if port is not None else ''}"


def _witness_fields(witness: Mapping[str, Any], *, max_bytes: int) -> tuple[str, str, int, str]:
    try:
        url = str(witness["url"])
        expected_hash = str(witness["sha256"]).lower()
        expected_bytes = witness["bytes"]
        expected_type = str(witness["content_type"]).lower()
    except (KeyError, TypeError) as exc:
        raise MediaWitnessError("media witness is missing required fields") from exc
    if not url or len(url) > 4096:
        raise MediaWitnessError("media witness URL is invalid")
    if not _SHA256_RE.fullmatch(expected_hash):
        raise MediaWitnessError("media witness SHA-256 is invalid")
    if isinstance(expected_bytes, bool) or not isinstance(expected_bytes, int):
        raise MediaWitnessError("media witness byte count must be an integer")
    if expected_bytes <= 0 or expected_bytes > max_bytes:
        raise MediaWitnessError("media witness byte count is outside the configured limit")
    if expected_type not in _ALLOWED_MEDIA_TYPES:
        raise MediaWitnessError("media witness content type is not allowed")
    return url, expected_hash, expected_bytes, expected_type


async def fetch_media_witness(
    witness: Mapping[str, Any],
    *,
    allowed_origins: Collection[str],
    max_bytes: int,
    timeout_s: float,
    transport: httpx.AsyncBaseTransport | None = None,
) -> VerifiedMediaWitness:
    """Fetch and verify one Core-issued media witness without SSRF fallbacks."""
    if max_bytes <= 0 or timeout_s <= 0:
        raise ValueError("media fetch limits must be positive")
    try:
        origins = frozenset(normalize_media_origins(allowed_origins))
    except RuntimeError as exc:
        raise MediaWitnessError(str(exc)) from exc
    if not origins:
        raise MediaWitnessError("media origin allowlist is empty")
    url, expected_hash, expected_bytes, expected_type = _witness_fields(
        witness,
        max_bytes=max_bytes,
    )
    if _url_origin(url) not in origins:
        raise MediaWitnessError("media URL origin is not allowlisted")

    timeout = httpx.Timeout(timeout_s)
    try:
        async with (
            httpx.AsyncClient(
                follow_redirects=False,
                trust_env=False,
                timeout=timeout,
                transport=transport,
            ) as client,
            client.stream(
                "GET",
                url,
                headers={"Accept-Encoding": "identity"},
            ) as response,
        ):
            if 300 <= response.status_code < 400:
                raise MediaWitnessError("media redirects are forbidden")
            response.raise_for_status()
            encoding = response.headers.get("content-encoding", "identity").lower()
            if encoding not in {"", "identity"}:
                raise MediaWitnessError("encoded media responses are forbidden")
            actual_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
            if actual_type != expected_type:
                raise MediaWitnessError("media response content type does not match witness")
            content_length = response.headers.get("content-length")
            if content_length is not None:
                try:
                    declared_length = int(content_length)
                except ValueError as exc:
                    raise MediaWitnessError("media response content length is invalid") from exc
                if declared_length != expected_bytes or declared_length > max_bytes:
                    raise MediaWitnessError("media response content length does not match witness")
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > expected_bytes or len(body) > max_bytes:
                    raise MediaWitnessError("media response exceeded its byte limit")
    except MediaWitnessError:
        raise
    except httpx.HTTPError as exc:
        raise MediaWitnessError("media fetch failed") from exc

    if len(body) != expected_bytes:
        raise MediaWitnessError("media response byte count does not match witness")
    actual_hash = hashlib.sha256(body).hexdigest()
    if not secrets.compare_digest(actual_hash, expected_hash):
        raise MediaWitnessError("media response SHA-256 does not match witness")
    return VerifiedMediaWitness(bytes(body), actual_hash, len(body), expected_type)


def _image_fidelity_contract(
    challenge: Mapping[str, Any],
    witnesses: Sequence[Mapping[str, Any]],
    *,
    target_worker_id: str,
) -> tuple[dict[str, Any], list[Mapping[str, Any]]]:
    if (
        challenge.get("schema") != "aipg.validator.media.challenge.v1"
        or challenge.get("kind") != "image.fidelity"
        or challenge.get("modality") != "image"
        or challenge.get("scoring_policy_id") != "image.fidelity.v1"
    ):
        raise MediaWitnessError("unsupported image fidelity challenge")
    parameters = challenge.get("parameters")
    references = challenge.get("reference_worker_ids")
    if not isinstance(parameters, Mapping) or not isinstance(references, list):
        raise MediaWitnessError("image fidelity challenge is incomplete")
    width = parameters.get("width")
    height = parameters.get("height")
    if (
        isinstance(width, bool)
        or not isinstance(width, int)
        or isinstance(height, bool)
        or not isinstance(height, int)
        or not 1 <= width <= _MAX_IMAGE_DIMENSION
        or not 1 <= height <= _MAX_IMAGE_DIMENSION
        or width * height > _MAX_IMAGE_PIXELS
    ):
        raise MediaWitnessError("image fidelity dimensions are invalid")
    reference_ids = [str(value) for value in references]
    if len(reference_ids) != 2 or any(not value for value in reference_ids):
        raise MediaWitnessError("image fidelity requires exactly two references")
    if len({target_worker_id, *reference_ids}) != 3:
        raise MediaWitnessError("candidate and reference workers must be distinct")
    if len(witnesses) != 3:
        raise MediaWitnessError("image fidelity requires exactly three witnesses")

    by_identity: dict[tuple[str, str], Mapping[str, Any]] = {}
    urls: set[str] = set()
    for witness in witnesses:
        if not isinstance(witness, Mapping):
            raise MediaWitnessError("media witness entry is invalid")
        role = str(witness.get("role") or "")
        worker_id = str(witness.get("worker_id") or "")
        key = (role, worker_id)
        if role not in {"candidate", "reference"} or not worker_id or key in by_identity:
            raise MediaWitnessError("media witness role or worker identity is invalid")
        url = str(witness.get("url") or "")
        if not url or url in urls:
            raise MediaWitnessError("media witness objects must be distinct")
        if str(witness.get("content_type") or "").lower() not in _ALLOWED_IMAGE_TYPES:
            raise MediaWitnessError("image fidelity witness has a non-image content type")
        urls.add(url)
        by_identity[key] = witness

    ordered_keys = [
        ("candidate", target_worker_id),
        ("reference", reference_ids[0]),
        ("reference", reference_ids[1]),
    ]
    try:
        ordered = [by_identity[key] for key in ordered_keys]
    except KeyError as exc:
        raise MediaWitnessError("media witnesses do not match committed workers") from exc
    if len(by_identity) != len(ordered_keys):
        raise MediaWitnessError("media witnesses contain an unexpected role")

    latency_ms = ordered[0].get("latency_ms")
    if isinstance(latency_ms, bool) or not isinstance(latency_ms, int) or latency_ms < 0:
        raise MediaWitnessError("candidate latency is invalid")
    return {"expect_w": width, "expect_h": height}, ordered


async def score_image_fidelity_witnesses(
    challenge: Mapping[str, Any],
    witnesses: Sequence[Mapping[str, Any]],
    *,
    target_worker_id: str,
    allowed_origins: Collection[str],
    max_bytes: int,
    timeout_s: float,
    phash_tolerance: int,
    latency_budget_s: float,
    transport: httpx.AsyncBaseTransport | None = None,
) -> tuple[str, dict[str, Any]]:
    """Verify three witnesses and independently score deterministic image fidelity."""
    detail: dict[str, Any] = {"policy": "image.fidelity.v1"}
    if not 0 <= phash_tolerance <= 64 or latency_budget_s < 0:
        return "inconclusive", {**detail, "reason": "invalid-local-policy"}
    if not media_dependencies_available():
        return "inconclusive", {**detail, "reason": "media-dependencies-unavailable"}
    try:
        canary, ordered = _image_fidelity_contract(
            challenge,
            witnesses,
            target_worker_id=target_worker_id,
        )
    except MediaWitnessError:
        return "inconclusive", {**detail, "reason": "invalid-challenge-or-witness-set"}

    results = await asyncio.gather(
        *(
            fetch_media_witness(
                witness,
                allowed_origins=allowed_origins,
                max_bytes=max_bytes,
                timeout_s=timeout_s,
                transport=transport,
            )
            for witness in ordered
        ),
        return_exceptions=True,
    )
    if any(isinstance(result, Exception) for result in results):
        return "inconclusive", {**detail, "reason": "witness-fetch-or-commitment-failed"}
    verified = [result for result in results if isinstance(result, VerifiedMediaWitness)]
    if len(verified) != 3:
        return "inconclusive", {**detail, "reason": "witness-fetch-or-commitment-failed"}

    candidate, reference_a, reference_b = verified
    for label, reference in (("reference_a", reference_a), ("reference_b", reference_b)):
        ok, reason = check_structure(canary, reference.body)
        if not ok or reason != "ok":
            return "inconclusive", {**detail, "reason": f"{label}-structure-unusable"}
    candidate_ok, candidate_reason = check_structure(canary, candidate.body)
    if not candidate_ok:
        return "failed", {**detail, "reason": f"candidate-{candidate_reason}"}
    if candidate_reason != "ok":
        return "inconclusive", {**detail, "reason": "candidate-decoder-unavailable"}

    candidate_hash = phash(candidate.body)
    reference_hash_a = phash(reference_a.body)
    reference_hash_b = phash(reference_b.body)
    if not candidate_hash or not reference_hash_a or not reference_hash_b:
        return "inconclusive", {**detail, "reason": "phash-unavailable"}
    reference_distance = phash_distance(reference_hash_a, reference_hash_b)
    detail["reference_distance"] = reference_distance
    if reference_distance > phash_tolerance:
        return "inconclusive", {**detail, "reason": "references-disagree"}

    candidate_distances = [
        phash_distance(candidate_hash, reference_hash_a),
        phash_distance(candidate_hash, reference_hash_b),
    ]
    detail["candidate_distances"] = candidate_distances
    if any(distance > phash_tolerance for distance in candidate_distances):
        return "failed", {**detail, "reason": "candidate-outlier"}
    latency_s = int(ordered[0]["latency_ms"]) / 1000
    detail["latency_ms"] = int(ordered[0]["latency_ms"])
    return ("slow" if latency_s > latency_budget_s else "healthy"), detail

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
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:  # noqa: BLE001 - untrusted decoders can raise plugin-specific errors
        return False, f"undecodable:{type(e).__name__}"
    if (img.width, img.height) != (canary["expect_w"], canary["expect_h"]):
        return False, f"wrong-dims:{img.width}x{img.height}"
    try:
        img.load()
    except Exception as e:  # noqa: BLE001 - untrusted decoders can raise plugin-specific errors
        return False, f"undecodable:{type(e).__name__}"
    # Blank/solid or pure-noise detection via grayscale std-dev.
    import statistics
    grayscale = img.convert("L")
    if hasattr(grayscale, "get_flattened_data"):
        px = list(grayscale.get_flattened_data())
    else:  # Pillow < 12
        px = list(grayscale.getdata())
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
    except Exception:  # noqa: BLE001 - a malformed image must not crash the validator loop
        return None


def phash_distance(a: str, b: str) -> int:
    """Hamming distance between two hex pHash strings."""
    return (int(a, 16) ^ int(b, 16)).bit_count()


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
