# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Offline runtime checks for packaged validator scorers."""

import hashlib
import io
import struct
import zlib

from .media_prober import (
    VerifiedMediaWitness,
    decode_image_bounded,
    decode_video_bounded,
    media_dependencies_available,
    video_dependencies_available,
)


def _png_fixture() -> bytes:
    width = height = 64
    raw = b"".join(
        b"\x00"
        + b"".join(
            bytes(((x * 4) % 256, (y * 4) % 256, ((x + y) * 2) % 256))
            for x in range(width)
        )
        for y in range(height)
    )

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def _video_fixture() -> bytes:
    import av
    from PIL import Image, ImageDraw

    output = io.BytesIO()
    with av.open(output, "w", format="mp4") as container:
        stream = container.add_stream("mpeg4", rate=4)
        stream.width = 64
        stream.height = 64
        stream.pix_fmt = "yuv420p"
        for index in range(4):
            image = Image.new("RGB", (64, 64), (24, 36, 52))
            draw = ImageDraw.Draw(image)
            draw.rectangle((5 + index * 12, 20, 17 + index * 12, 34), fill=(240, 180, 40))
            for packet in stream.encode(av.VideoFrame.from_image(image)):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    return output.getvalue()


def _witness(body: bytes, content_type: str) -> VerifiedMediaWitness:
    return VerifiedMediaWitness(
        body=body,
        sha256=hashlib.sha256(body).hexdigest(),
        byte_count=len(body),
        content_type=content_type,
    )


def run_media_decoder_self_test() -> dict[str, str]:
    """Exercise the real bounded decoder subprocesses without network access."""
    if not media_dependencies_available():
        raise RuntimeError("image scorer dependencies are unavailable")
    if not video_dependencies_available():
        raise RuntimeError("video scorer dependencies are unavailable")

    image = decode_image_bounded(_witness(_png_fixture(), "image/png"), timeout_s=10)
    if (image.width, image.height) != (64, 64) or image.grayscale_stddev < 3:
        raise RuntimeError("image decoder returned an invalid self-test profile")

    video = decode_video_bounded(
        _witness(_video_fixture(), "video/mp4"),
        max_frames=8,
        timeout_s=15,
    )
    if (
        (video.width, video.height) != (64, 64)
        or video.frame_count != 4
        or max(video.motion_distances, default=0) < 3
    ):
        raise RuntimeError("video decoder returned an invalid self-test profile")

    return {
        "image": f"{image.width}x{image.height} png/phash",
        "video": f"{video.width}x{video.height} mp4/{video.frame_count} frames",
    }
