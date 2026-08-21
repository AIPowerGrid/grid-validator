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
import io
import logging
import math
import multiprocessing
import re
import secrets
import sys
from collections.abc import Collection, Mapping, Sequence
from dataclasses import asdict, dataclass
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
_MAX_VIDEO_DIMENSION = 4096
_MAX_VIDEO_PIXELS = 4096 * 4096
_MAX_VIDEO_FRAMES = 512
_MAX_VIDEO_FPS = 120.0
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


class VideoDecodeTimeout(MediaWitnessError):
    """The local bounded decoder exceeded its resource deadline."""


@dataclass(frozen=True)
class VerifiedMediaWitness:
    body: bytes
    sha256: str
    byte_count: int
    content_type: str


@dataclass(frozen=True)
class VideoProfile:
    width: int
    height: int
    frame_count: int
    fps: float
    duration_s: float
    frame_hashes: tuple[str, ...]
    motion_distances: tuple[int, ...]
    blank_frames: int


def media_dependencies_available() -> bool:
    try:
        import imagehash  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError:
        return False
    return True


def video_dependencies_available() -> bool:
    if not media_dependencies_available():
        return False
    try:
        import av  # noqa: F401
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


def _video_contract(
    challenge: Mapping[str, Any],
    witnesses: Sequence[Mapping[str, Any]],
    *,
    target_worker_id: str,
) -> tuple[dict[str, Any], list[Mapping[str, Any]], bool]:
    kind = str(challenge.get("kind") or "")
    policy = str(challenge.get("scoring_policy_id") or "")
    fidelity = kind == "video.fidelity" and policy == "video.fidelity.v1"
    if (
        challenge.get("schema") != "aipg.validator.media.challenge.v1"
        or challenge.get("modality") != "video"
        or not (
            (kind == "video.contract" and policy == "video.contract.v1")
            or fidelity
        )
    ):
        raise MediaWitnessError("unsupported video challenge")
    parameters = challenge.get("parameters")
    if not isinstance(parameters, Mapping):
        raise MediaWitnessError("video challenge is incomplete")

    width = parameters.get("width")
    height = parameters.get("height")
    frame_count = parameters.get("frame_count")
    fps = parameters.get("fps")
    duration_s = parameters.get("duration_s")
    motion_required = parameters.get("motion_required")
    if (
        isinstance(width, bool)
        or not isinstance(width, int)
        or isinstance(height, bool)
        or not isinstance(height, int)
        or isinstance(frame_count, bool)
        or not isinstance(frame_count, int)
        or isinstance(fps, bool)
        or not isinstance(fps, (int, float))
        or isinstance(duration_s, bool)
        or not isinstance(duration_s, (int, float))
        or not isinstance(motion_required, bool)
        or not 1 <= width <= _MAX_VIDEO_DIMENSION
        or not 1 <= height <= _MAX_VIDEO_DIMENSION
        or width * height > _MAX_VIDEO_PIXELS
        or not 2 <= frame_count <= _MAX_VIDEO_FRAMES
        or not 0 < float(fps) <= _MAX_VIDEO_FPS
        or not 0 < float(duration_s) <= _MAX_VIDEO_FRAMES
    ):
        raise MediaWitnessError("video parameters are invalid")
    expected_duration = frame_count / float(fps)
    duration_tolerance = max(0.15, 2.0 / float(fps))
    if abs(float(duration_s) - expected_duration) > duration_tolerance:
        raise MediaWitnessError("video timing parameters are inconsistent")

    references = challenge.get("reference_worker_ids") or []
    if not isinstance(references, list):
        raise MediaWitnessError("video reference set is invalid")
    reference_ids = [str(value) for value in references]
    if fidelity:
        if len(reference_ids) != 2 or any(not value for value in reference_ids):
            raise MediaWitnessError("video fidelity requires exactly two references")
        if len({target_worker_id, *reference_ids}) != 3 or len(witnesses) != 3:
            raise MediaWitnessError("video fidelity worker set is invalid")
    elif reference_ids or len(witnesses) != 1:
        raise MediaWitnessError("video contract requires one candidate witness")

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
        if str(witness.get("content_type") or "").lower() not in {"video/mp4", "video/webm"}:
            raise MediaWitnessError("video witness has a non-video content type")
        urls.add(url)
        by_identity[key] = witness

    ordered_keys = [("candidate", target_worker_id)]
    if fidelity:
        ordered_keys.extend(("reference", worker_id) for worker_id in reference_ids)
    try:
        ordered = [by_identity[key] for key in ordered_keys]
    except KeyError as exc:
        raise MediaWitnessError("video witnesses do not match committed workers") from exc
    if len(by_identity) != len(ordered_keys):
        raise MediaWitnessError("video witnesses contain an unexpected role")
    latency_ms = ordered[0].get("latency_ms")
    if isinstance(latency_ms, bool) or not isinstance(latency_ms, int) or latency_ms < 0:
        raise MediaWitnessError("candidate latency is invalid")
    return {
        "width": width,
        "height": height,
        "frame_count": frame_count,
        "fps": float(fps),
        "duration_s": float(duration_s),
        "motion_required": motion_required,
    }, ordered, fidelity


def _limit_video_decoder(timeout_s: float) -> None:
    """Bound a native decoder process where the host supports rlimits."""
    if not sys.platform.startswith("linux"):
        return
    try:
        import resource

        cpu_soft = max(1, math.ceil(timeout_s))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_soft, max(2, cpu_soft + 1)))
        memory = 2 * 1024 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    except (ImportError, OSError, ValueError):
        return


def _decode_video_profile(body: bytes, content_type: str, max_frames: int) -> VideoProfile:
    import av
    import imagehash
    from PIL import ImageStat

    container_format = "mp4" if content_type == "video/mp4" else "webm"
    with av.open(io.BytesIO(body), mode="r", format=container_format) as container:
        streams = list(container.streams.video)
        if len(streams) != 1:
            raise MediaWitnessError("video must contain exactly one video stream")
        stream = streams[0]
        width = int(stream.codec_context.width or 0)
        height = int(stream.codec_context.height or 0)
        if (
            not 1 <= width <= _MAX_VIDEO_DIMENSION
            or not 1 <= height <= _MAX_VIDEO_DIMENSION
            or width * height > _MAX_VIDEO_PIXELS
        ):
            raise MediaWitnessError("video stream dimensions are invalid")
        rate = stream.average_rate or stream.guessed_rate
        fps = float(rate) if rate is not None else 0.0
        if not 0 < fps <= _MAX_VIDEO_FPS:
            raise MediaWitnessError("video frame rate is invalid")

        hashes: list[str] = []
        timestamps: list[float] = []
        blank_frames = 0
        for frame in container.decode(stream):
            if len(hashes) >= max_frames:
                raise MediaWitnessError("video exceeded the frame limit")
            if (int(frame.width), int(frame.height)) != (width, height):
                raise MediaWitnessError("video dimensions changed during decode")
            image = frame.to_image().convert("RGB")
            hashes.append(str(imagehash.phash(image)))
            grayscale = image.convert("L").resize((64, 64))
            if float(ImageStat.Stat(grayscale).stddev[0]) < 3:
                blank_frames += 1
            if frame.time is not None:
                timestamp = float(frame.time)
                if timestamps and timestamp <= timestamps[-1]:
                    raise MediaWitnessError("video timestamps are not strictly increasing")
                timestamps.append(timestamp)

    if len(hashes) < 2:
        raise MediaWitnessError("video decoded fewer than two frames")
    if timestamps and len(timestamps) != len(hashes):
        raise MediaWitnessError("video timestamps are incomplete")
    duration_s = (
        timestamps[-1] - timestamps[0] + (1.0 / fps)
        if timestamps
        else len(hashes) / fps
    )
    motion = tuple(phash_distance(a, b) for a, b in zip(hashes, hashes[1:]))
    return VideoProfile(
        width=width,
        height=height,
        frame_count=len(hashes),
        fps=fps,
        duration_s=duration_s,
        frame_hashes=tuple(hashes),
        motion_distances=motion,
        blank_frames=blank_frames,
    )


def _video_decode_worker(
    send_conn,
    body: bytes,
    content_type: str,
    max_frames: int,
    timeout_s: float,
) -> None:
    try:
        _limit_video_decoder(timeout_s)
        send_conn.send(("ok", asdict(_decode_video_profile(body, content_type, max_frames))))
    except Exception as exc:  # noqa: BLE001 - native decoders expose library-specific errors
        send_conn.send(("error", type(exc).__name__))
    finally:
        send_conn.close()


def decode_video_bounded(
    witness: VerifiedMediaWitness,
    *,
    max_frames: int,
    timeout_s: float,
) -> VideoProfile:
    """Decode untrusted video bytes in a killable child process."""
    if not 2 <= max_frames <= _MAX_VIDEO_FRAMES or timeout_s <= 0:
        raise ValueError("video decoder limits are invalid")
    context = multiprocessing.get_context("spawn")
    receive_conn, send_conn = context.Pipe(duplex=False)
    process = context.Process(
        target=_video_decode_worker,
        args=(send_conn, witness.body, witness.content_type, max_frames, timeout_s),
        daemon=True,
    )
    process.start()
    send_conn.close()
    try:
        if not receive_conn.poll(timeout_s):
            process.terminate()
            process.join(2)
            if process.is_alive():
                process.kill()
                process.join(2)
            raise VideoDecodeTimeout("video decoder timed out")
        status, payload = receive_conn.recv()
    except EOFError as exc:
        raise MediaWitnessError("video decoder exited without a result") from exc
    finally:
        receive_conn.close()
        if process.is_alive():
            process.join(2)
        if process.is_alive():
            process.terminate()
            process.join(2)
    if status != "ok" or not isinstance(payload, dict):
        raise MediaWitnessError("video decode failed")
    try:
        return VideoProfile(
            width=int(payload["width"]),
            height=int(payload["height"]),
            frame_count=int(payload["frame_count"]),
            fps=float(payload["fps"]),
            duration_s=float(payload["duration_s"]),
            frame_hashes=tuple(str(value) for value in payload["frame_hashes"]),
            motion_distances=tuple(int(value) for value in payload["motion_distances"]),
            blank_frames=int(payload["blank_frames"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise MediaWitnessError("video decoder returned an invalid profile") from exc


def _video_contract_failures(expected: Mapping[str, Any], profile: VideoProfile) -> list[str]:
    failures: list[str] = []
    if (profile.width, profile.height) != (expected["width"], expected["height"]):
        failures.append("dimensions")
    frame_tolerance = max(1, math.ceil(int(expected["frame_count"]) * 0.02))
    if abs(profile.frame_count - int(expected["frame_count"])) > frame_tolerance:
        failures.append("frame-count")
    fps_tolerance = max(0.25, float(expected["fps"]) * 0.02)
    if abs(profile.fps - float(expected["fps"])) > fps_tolerance:
        failures.append("fps")
    duration_tolerance = max(0.15, 2.0 / float(expected["fps"]))
    if abs(profile.duration_s - float(expected["duration_s"])) > duration_tolerance:
        failures.append("duration")
    if profile.blank_frames:
        failures.append("blank-frame")
    if bool(expected["motion_required"]):
        active = sum(distance >= 2 for distance in profile.motion_distances)
        active_ratio = active / max(1, len(profile.motion_distances))
        if max(profile.motion_distances, default=0) < 3 or active_ratio < 0.1:
            failures.append("repeated-still")
    return failures


def _profile_distances(left: VideoProfile, right: VideoProfile) -> tuple[float, int, float]:
    if len(left.frame_hashes) != len(right.frame_hashes):
        raise MediaWitnessError("video profiles have different frame counts")
    frame_distances = [
        phash_distance(a, b) for a, b in zip(left.frame_hashes, right.frame_hashes)
    ]
    motion_count = min(len(left.motion_distances), len(right.motion_distances))
    motion_delta = (
        sum(
            abs(left.motion_distances[index] - right.motion_distances[index])
            for index in range(motion_count)
        )
        / motion_count
        if motion_count
        else 0.0
    )
    return sum(frame_distances) / len(frame_distances), max(frame_distances), motion_delta


async def score_video_witnesses(
    challenge: Mapping[str, Any],
    witnesses: Sequence[Mapping[str, Any]],
    *,
    target_worker_id: str,
    allowed_origins: Collection[str],
    max_bytes: int,
    fetch_timeout_s: float,
    decode_timeout_s: float,
    phash_tolerance: int,
    motion_tolerance: float,
    latency_budget_s: float,
    transport: httpx.AsyncBaseTransport | None = None,
) -> tuple[str, dict[str, Any]]:
    """Verify and score a Core-issued video contract or fidelity witness set."""
    detail: dict[str, Any] = {"policy": str(challenge.get("scoring_policy_id") or "")}
    if (
        not 0 <= phash_tolerance <= 64
        or motion_tolerance < 0
        or latency_budget_s < 0
        or decode_timeout_s <= 0
    ):
        return "inconclusive", {**detail, "reason": "invalid-local-policy"}
    if not video_dependencies_available():
        return "inconclusive", {**detail, "reason": "video-dependencies-unavailable"}
    try:
        expected, ordered, fidelity = _video_contract(
            challenge,
            witnesses,
            target_worker_id=target_worker_id,
        )
    except MediaWitnessError:
        return "inconclusive", {**detail, "reason": "invalid-challenge-or-witness-set"}

    fetched = await asyncio.gather(
        *(
            fetch_media_witness(
                witness,
                allowed_origins=allowed_origins,
                max_bytes=max_bytes,
                timeout_s=fetch_timeout_s,
                transport=transport,
            )
            for witness in ordered
        ),
        return_exceptions=True,
    )
    if any(isinstance(result, Exception) for result in fetched):
        return "inconclusive", {**detail, "reason": "witness-fetch-or-commitment-failed"}
    verified = [result for result in fetched if isinstance(result, VerifiedMediaWitness)]
    if len(verified) != len(ordered):
        return "inconclusive", {**detail, "reason": "witness-fetch-or-commitment-failed"}

    expected_frames = int(expected["frame_count"])
    max_frames = min(
        _MAX_VIDEO_FRAMES,
        expected_frames + max(2, math.ceil(expected_frames * 0.02)),
    )
    decoded: list[VideoProfile | Exception] = []
    for witness in verified:
        try:
            decoded.append(await asyncio.to_thread(
                decode_video_bounded,
                witness,
                max_frames=max_frames,
                timeout_s=decode_timeout_s,
            ))
        except VideoDecodeTimeout:
            return "inconclusive", {**detail, "reason": "local-decoder-timeout"}
        except Exception as exc:  # decoder failures are classified by witness role below
            decoded.append(exc)
    if fidelity and any(isinstance(result, Exception) for result in decoded[1:]):
        return "inconclusive", {**detail, "reason": "reference-decode-failed"}
    if isinstance(decoded[0], Exception):
        return "failed", {**detail, "reason": "candidate-decode-failed"}
    profiles = [result for result in decoded if isinstance(result, VideoProfile)]
    if len(profiles) != len(ordered):
        return "inconclusive", {**detail, "reason": "video-decode-incomplete"}

    if fidelity:
        for label, profile in (("reference-a", profiles[1]), ("reference-b", profiles[2])):
            failures = _video_contract_failures(expected, profile)
            if failures:
                return "inconclusive", {**detail, "reason": f"{label}-contract-failed", "checks": failures}
    candidate_failures = _video_contract_failures(expected, profiles[0])
    if candidate_failures:
        return "failed", {**detail, "reason": "candidate-contract-failed", "checks": candidate_failures}

    detail.update({
        "frame_count": profiles[0].frame_count,
        "fps": round(profiles[0].fps, 3),
        "duration_s": round(profiles[0].duration_s, 3),
        "motion_active_ratio": round(
            sum(distance >= 2 for distance in profiles[0].motion_distances)
            / max(1, len(profiles[0].motion_distances)),
            4,
        ),
    })
    if fidelity:
        try:
            reference_mean, reference_max, reference_motion = _profile_distances(profiles[1], profiles[2])
            candidate_a = _profile_distances(profiles[0], profiles[1])
            candidate_b = _profile_distances(profiles[0], profiles[2])
        except MediaWitnessError:
            return "inconclusive", {**detail, "reason": "video-profile-shape-mismatch"}
        detail.update({
            "reference_frame_distance_mean": round(reference_mean, 3),
            "reference_frame_distance_max": reference_max,
            "reference_motion_delta": round(reference_motion, 3),
            "candidate_frame_distance_means": [round(candidate_a[0], 3), round(candidate_b[0], 3)],
            "candidate_frame_distance_maxes": [candidate_a[1], candidate_b[1]],
            "candidate_motion_deltas": [round(candidate_a[2], 3), round(candidate_b[2], 3)],
        })
        if reference_max > phash_tolerance or reference_motion > motion_tolerance:
            return "inconclusive", {**detail, "reason": "references-disagree"}
        if (
            candidate_a[1] > phash_tolerance
            or candidate_b[1] > phash_tolerance
            or candidate_a[2] > motion_tolerance
            or candidate_b[2] > motion_tolerance
        ):
            return "failed", {**detail, "reason": "candidate-outlier"}

    detail["latency_ms"] = int(ordered[0]["latency_ms"])
    return (
        "slow"
        if int(ordered[0]["latency_ms"]) / 1000 > latency_budget_s
        else "healthy"
    ), detail
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
