import gzip
import hashlib
import io
import logging
import struct
import unittest
import zlib
from unittest.mock import patch

import httpx

from validator import media_prober


def _png(width, height, pixel):
    raw = b"".join(
        b"\x00" + b"".join(bytes(pixel(x, y)) for x in range(width))
        for y in range(height)
    )
    def chunk(kind, data):
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


def _png_declared_dimensions(source, width, height):
    """Rewrite only IHDR dimensions; useful for tiny decompression-bomb fixtures."""
    value = bytearray(source)
    value[16:24] = struct.pack(">II", width, height)
    value[29:33] = struct.pack(">I", zlib.crc32(value[12:29]) & 0xFFFFFFFF)
    return bytes(value)


def _mp4(*, frames=8, fps=8, variant=0, static=False):
    import av
    from PIL import Image, ImageDraw

    output = io.BytesIO()
    with av.open(output, "w", format="mp4") as container:
        stream = container.add_stream("mpeg4", rate=fps)
        stream.width = 64
        stream.height = 64
        stream.pix_fmt = "yuv420p"
        for index in range(frames):
            image = Image.new("RGB", (64, 64))
            pixels = image.load()
            for y in range(64):
                for x in range(64):
                    pixels[x, y] = (
                        (x * 4 + variant * 47) % 256,
                        (y * 4 + variant * 83) % 256,
                        ((x + y) * 2 + variant * 29) % 256,
                    )
            draw = ImageDraw.Draw(image)
            offset = 4 if static else 4 + index * 5
            draw.rectangle((offset % 48, 20, offset % 48 + 15, 35), fill=(255, 255, 255))
            frame = av.VideoFrame.from_image(image)
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    return output.getvalue()


class MediaChallengeTests(unittest.TestCase):
    def test_preview_canary_uses_cryptographic_seed_and_not_round_index(self):
        choices = iter([
            "dragon", "cobalt", "on the moon", "wide establishing view",
            "moonlit haze", "moving steadily from left to right",
        ])
        with (
            patch.object(media_prober.secrets, "choice", side_effect=choices),
            patch.object(media_prober.secrets, "token_hex", return_value="a1b2c3"),
            patch.object(media_prober.secrets, "randbits", return_value=987654321),
        ):
            canary = media_prober.make_media_canary(0, kind="video")

        self.assertEqual(canary["payload"]["seed"], 987654321)
        self.assertIn("dragon", canary["prompt"])
        self.assertIn("moving steadily from left to right", canary["prompt"])
        self.assertEqual(canary["payload"]["frames"], 16)

    def test_no_public_fixed_seed_constant_exists(self):
        self.assertFalse(hasattr(media_prober, "CANARY_SEED"))


class MediaWitnessTests(unittest.IsolatedAsyncioTestCase):
    ORIGIN = "https://media.example.test"
    BODY = b"verified-media-bytes"

    def _witness(self, **overrides):
        witness = {
            "url": f"{self.ORIGIN}/validator/object?signature=opaque",
            "sha256": hashlib.sha256(self.BODY).hexdigest(),
            "bytes": len(self.BODY),
            "content_type": "image/webp",
        }
        witness.update(overrides)
        return witness

    def test_http_client_does_not_log_presigned_urls_at_info(self):
        self.assertGreaterEqual(
            logging.getLogger("httpx").getEffectiveLevel(),
            logging.WARNING,
        )

    async def _fetch(self, handler, witness=None):
        return await media_prober.fetch_media_witness(
            witness or self._witness(),
            allowed_origins=[self.ORIGIN],
            max_bytes=1024,
            timeout_s=2,
            transport=httpx.MockTransport(handler),
        )

    async def test_fetch_recomputes_hash_and_binds_size_and_mime(self):
        def handler(request):
            self.assertEqual(request.headers["accept-encoding"], "identity")
            return httpx.Response(
                200,
                headers={
                    "content-type": "image/webp",
                    "content-length": str(len(self.BODY)),
                },
                content=self.BODY,
            )

        result = await self._fetch(handler)
        self.assertEqual(result.body, self.BODY)
        self.assertEqual(result.sha256, hashlib.sha256(self.BODY).hexdigest())

    async def test_cross_origin_url_is_rejected_before_network(self):
        called = False

        def handler(request):
            nonlocal called
            called = True
            return httpx.Response(200, content=self.BODY)

        with self.assertRaisesRegex(media_prober.MediaWitnessError, "not allowlisted"):
            await self._fetch(
                handler,
                self._witness(url="https://attacker.example/object"),
            )
        self.assertFalse(called)

    async def test_redirect_is_not_followed(self):
        requests = []

        def handler(request):
            requests.append(str(request.url))
            return httpx.Response(302, headers={"location": f"{self.ORIGIN}/other"})

        with self.assertRaisesRegex(media_prober.MediaWitnessError, "redirects"):
            await self._fetch(handler)
        self.assertEqual(len(requests), 1)

    async def test_hash_mismatch_is_rejected(self):
        def handler(request):
            return httpx.Response(
                200,
                headers={"content-type": "image/webp"},
                content=self.BODY,
            )

        with self.assertRaisesRegex(media_prober.MediaWitnessError, "SHA-256"):
            await self._fetch(handler, self._witness(sha256="0" * 64))

    async def test_size_mime_and_encoding_mismatches_are_rejected(self):
        cases = (
            (
                {"content-type": "image/png", "content-length": str(len(self.BODY))},
                "content type",
            ),
            (
                {"content-type": "image/webp", "content-length": str(len(self.BODY) + 1)},
                "content length",
            ),
            (
                {"content-type": "image/webp", "content-encoding": "gzip"},
                "encoded",
            ),
        )
        for headers, error in cases:
            with self.subTest(error=error):
                def handler(request, headers=headers):
                    content = (
                        gzip.compress(self.BODY)
                        if headers.get("content-encoding") == "gzip"
                        else self.BODY
                    )
                    return httpx.Response(200, headers=headers, content=content)

                with self.assertRaisesRegex(media_prober.MediaWitnessError, error):
                    await self._fetch(handler)

    async def test_empty_allowlist_and_oversized_commitment_fail_closed(self):
        transport = httpx.MockTransport(lambda request: httpx.Response(500))
        with self.assertRaisesRegex(media_prober.MediaWitnessError, "allowlist is empty"):
            await media_prober.fetch_media_witness(
                self._witness(),
                allowed_origins=[],
                max_bytes=1024,
                timeout_s=2,
                transport=transport,
            )
        with self.assertRaisesRegex(media_prober.MediaWitnessError, "configured limit"):
            await media_prober.fetch_media_witness(
                self._witness(bytes=1025),
                allowed_origins=[self.ORIGIN],
                max_bytes=1024,
                timeout_s=2,
                transport=transport,
            )


class ImageFidelityTests(unittest.IsolatedAsyncioTestCase):
    ORIGIN = "https://media.example.test"
    TARGET = "worker-candidate"
    REFERENCES = ("worker-reference-a", "worker-reference-b")

    @classmethod
    def setUpClass(cls):
        cls.reference = _png(
            64,
            64,
            lambda x, y: ((x * 4) % 256, (y * 4) % 256, ((x + y) * 2) % 256),
        )
        cls.outlier = _png(
            64,
            64,
            lambda x, y: (255, 255, 255) if (x // 8 + y // 8) % 2 else (0, 0, 0),
        )
        cls.blank = _png(64, 64, lambda x, y: (128, 128, 128))

    def _challenge(self, **overrides):
        challenge = {
            "schema": "aipg.validator.media.challenge.v1",
            "kind": "image.fidelity",
            "modality": "image",
            "scoring_policy_id": "image.fidelity.v1",
            "parameters": {"width": 64, "height": 64},
            "reference_worker_ids": list(self.REFERENCES),
        }
        challenge.update(overrides)
        return challenge

    def _witness(self, role, worker_id, name, body, latency_ms=1000):
        return {
            "role": role,
            "worker_id": worker_id,
            "url": f"{self.ORIGIN}/{name}?signature=opaque",
            "sha256": hashlib.sha256(body).hexdigest(),
            "bytes": len(body),
            "content_type": "image/png",
            "latency_ms": latency_ms,
        }

    def _witnesses(self, candidate=None, reference_a=None, reference_b=None, latency_ms=1000):
        return [
            self._witness(
                "candidate",
                self.TARGET,
                "candidate",
                candidate or self.reference,
                latency_ms,
            ),
            self._witness(
                "reference",
                self.REFERENCES[0],
                "reference-a",
                reference_a or self.reference,
            ),
            self._witness(
                "reference",
                self.REFERENCES[1],
                "reference-b",
                reference_b or self.reference,
            ),
        ]

    async def _score(self, witnesses, *, handler_bodies=None):
        bodies = handler_bodies or {
            "candidate": self.reference,
            "reference-a": self.reference,
            "reference-b": self.reference,
        }

        def handler(request):
            name = request.url.path.rsplit("/", 1)[-1]
            body = bodies[name]
            return httpx.Response(200, headers={"content-type": "image/png"}, content=body)

        return await media_prober.score_image_fidelity_witnesses(
            self._challenge(),
            witnesses,
            target_worker_id=self.TARGET,
            allowed_origins=[self.ORIGIN],
            max_bytes=1024 * 1024,
            timeout_s=2,
            decode_timeout_s=10,
            transport=httpx.MockTransport(handler),
        )

    async def test_agreeing_references_and_candidate_are_healthy_or_slow(self):
        witnesses = self._witnesses()
        outcome, detail = await self._score(witnesses)
        self.assertEqual(outcome, "healthy")
        self.assertEqual(detail["reference_distance"], 0)
        self.assertEqual(detail["candidate_distances"], [0, 0])
        self.assertEqual(detail["phash_tolerance"], 12)
        self.assertEqual(detail["latency_budget_ms"], 60_000)

        slow = self._witnesses(latency_ms=61_000)
        outcome, _ = await self._score(slow)
        self.assertEqual(outcome, "slow")

    def test_bounded_image_decoder_reports_profile(self):
        witness = media_prober.VerifiedMediaWitness(
            self.reference,
            hashlib.sha256(self.reference).hexdigest(),
            len(self.reference),
            "image/png",
        )
        profile = media_prober.decode_image_bounded(witness, timeout_s=5)
        self.assertEqual((profile.width, profile.height), (64, 64))
        self.assertTrue(profile.phash)
        self.assertGreaterEqual(profile.grayscale_stddev, 3)

        wrong_mime = media_prober.VerifiedMediaWitness(
            self.reference,
            hashlib.sha256(self.reference).hexdigest(),
            len(self.reference),
            "image/jpeg",
        )
        with self.assertRaisesRegex(media_prober.ImageWitnessInvalid, "mime-mismatch"):
            media_prober.decode_image_bounded(wrong_mime, timeout_s=5)

    def test_bounded_image_decoder_rejects_truncation_and_bomb_dimensions(self):
        for body, reason in (
            (self.reference[:40], "undecodable"),
            (_png_declared_dimensions(self.reference, 8192, 8192), "unsafe-dimensions"),
        ):
            with self.subTest(reason=reason):
                witness = media_prober.VerifiedMediaWitness(
                    body,
                    hashlib.sha256(body).hexdigest(),
                    len(body),
                    "image/png",
                )
                with self.assertRaisesRegex(media_prober.ImageWitnessInvalid, reason):
                    media_prober.decode_image_bounded(witness, timeout_s=5)

    async def test_image_policy_has_one_network_wide_phash_boundary(self):
        reference = media_prober.ImageProfile(64, 64, "0" * 16, 10.0)
        at_limit = media_prober.ImageProfile(64, 64, "0000000000000fff", 10.0)
        over_limit = media_prober.ImageProfile(64, 64, "0000000000001fff", 10.0)
        with patch.object(
            media_prober,
            "decode_image_bounded",
            side_effect=[at_limit, reference, reference],
        ):
            outcome, detail = await self._score(self._witnesses())
        self.assertEqual(outcome, "healthy")
        self.assertEqual(detail["candidate_distances"], [12, 12])

        with patch.object(
            media_prober,
            "decode_image_bounded",
            side_effect=[over_limit, reference, reference],
        ):
            outcome, detail = await self._score(self._witnesses())
        self.assertEqual(outcome, "failed")
        self.assertEqual(detail["candidate_distances"], [13, 13])

    async def test_local_image_decoder_failure_is_inconclusive(self):
        with patch.object(
            media_prober,
            "decode_image_bounded",
            side_effect=media_prober.ImageDecodeTimeout("deadline"),
        ):
            outcome, detail = await self._score(self._witnesses())
        self.assertEqual(outcome, "inconclusive")
        self.assertEqual(detail["reason"], "local-image-decoder-timeout")

    async def test_reference_disagreement_is_inconclusive(self):
        witnesses = self._witnesses(reference_b=self.outlier)
        outcome, detail = await self._score(
            witnesses,
            handler_bodies={
                "candidate": self.reference,
                "reference-a": self.reference,
                "reference-b": self.outlier,
            },
        )
        self.assertEqual(outcome, "inconclusive")
        self.assertEqual(detail["reason"], "references-disagree")

    async def test_candidate_outlier_is_failed_only_after_references_agree(self):
        witnesses = self._witnesses(candidate=self.outlier)
        outcome, detail = await self._score(
            witnesses,
            handler_bodies={
                "candidate": self.outlier,
                "reference-a": self.reference,
                "reference-b": self.reference,
            },
        )
        self.assertEqual(outcome, "failed")
        self.assertEqual(detail["reason"], "candidate-outlier")

    async def test_reference_structure_failure_is_inconclusive_but_candidate_is_failed(self):
        reference_witnesses = self._witnesses(reference_a=self.blank)
        outcome, detail = await self._score(
            reference_witnesses,
            handler_bodies={
                "candidate": self.reference,
                "reference-a": self.blank,
                "reference-b": self.reference,
            },
        )
        self.assertEqual(outcome, "inconclusive")
        self.assertEqual(detail["reason"], "reference_a-structure-unusable")

        candidate_witnesses = self._witnesses(candidate=self.blank)
        outcome, detail = await self._score(
            candidate_witnesses,
            handler_bodies={
                "candidate": self.blank,
                "reference-a": self.reference,
                "reference-b": self.reference,
            },
        )
        self.assertEqual(outcome, "failed")
        self.assertEqual(detail["reason"], "candidate-blank-or-solid")

    async def test_fetch_or_commitment_failure_is_inconclusive(self):
        witnesses = self._witnesses()
        witnesses[0]["sha256"] = "0" * 64
        outcome, detail = await self._score(witnesses)
        self.assertEqual(outcome, "inconclusive")
        self.assertEqual(detail["reason"], "witness-fetch-or-commitment-failed")

    async def test_worker_binding_and_dependency_failures_are_inconclusive(self):
        witnesses = self._witnesses()
        witnesses[1]["worker_id"] = self.TARGET
        outcome, detail = await self._score(witnesses)
        self.assertEqual(outcome, "inconclusive")
        self.assertEqual(detail["reason"], "invalid-challenge-or-witness-set")

        with patch.object(media_prober, "media_dependencies_available", return_value=False):
            outcome, detail = await self._score(self._witnesses())
        self.assertEqual(outcome, "inconclusive")
        self.assertEqual(detail["reason"], "media-dependencies-unavailable")

    async def test_oversized_dimensions_fail_before_fetch(self):
        witnesses = self._witnesses()
        with patch.object(
            media_prober,
            "fetch_media_witness",
            side_effect=AssertionError("fetch must not run"),
        ):
            outcome, detail = await media_prober.score_image_fidelity_witnesses(
                self._challenge(parameters={"width": 4097, "height": 64}),
                witnesses,
                target_worker_id=self.TARGET,
                allowed_origins=[self.ORIGIN],
                max_bytes=1024 * 1024,
                timeout_s=2,
                decode_timeout_s=5,
            )
        self.assertEqual(outcome, "inconclusive")
        self.assertEqual(detail["reason"], "invalid-challenge-or-witness-set")

    async def test_non_image_witness_contract_is_inconclusive_before_fetch(self):
        witnesses = self._witnesses()
        witnesses[0]["content_type"] = "video/mp4"
        with patch.object(
            media_prober,
            "fetch_media_witness",
            side_effect=AssertionError("fetch must not run"),
        ):
            outcome, detail = await self._score(witnesses)
        self.assertEqual(outcome, "inconclusive")
        self.assertEqual(detail["reason"], "invalid-challenge-or-witness-set")


class VideoScoringTests(unittest.IsolatedAsyncioTestCase):
    ORIGIN = "https://media.example.test"
    TARGET = "worker-candidate"
    REFERENCES = ("worker-reference-a", "worker-reference-b")

    @classmethod
    def setUpClass(cls):
        cls.reference = _mp4()
        cls.outlier = _mp4(variant=3)
        cls.static = _mp4(static=True)

    def _challenge(self, *, fidelity=False, **parameter_overrides):
        parameters = {
            "width": 64,
            "height": 64,
            "frame_count": 8,
            "fps": 8.0,
            "duration_s": 1.0,
            "motion_required": True,
        }
        parameters.update(parameter_overrides)
        return {
            "schema": "aipg.validator.media.challenge.v1",
            "kind": "video.fidelity" if fidelity else "video.contract",
            "modality": "video",
            "scoring_policy_id": "video.fidelity.v1" if fidelity else "video.contract.v1",
            "parameters": parameters,
            "reference_worker_ids": list(self.REFERENCES) if fidelity else [],
        }

    def _witness(self, role, worker_id, name, body, latency_ms=1000):
        return {
            "role": role,
            "worker_id": worker_id,
            "url": f"{self.ORIGIN}/{name}?signature=opaque",
            "sha256": hashlib.sha256(body).hexdigest(),
            "bytes": len(body),
            "content_type": "video/mp4",
            "latency_ms": latency_ms,
        }

    def _witnesses(self, *, fidelity=False, candidate=None, reference_a=None, reference_b=None):
        values = [
            self._witness("candidate", self.TARGET, "candidate", candidate or self.reference),
        ]
        if fidelity:
            values.extend((
                self._witness(
                    "reference",
                    self.REFERENCES[0],
                    "reference-a",
                    reference_a or self.reference,
                ),
                self._witness(
                    "reference",
                    self.REFERENCES[1],
                    "reference-b",
                    reference_b or self.reference,
                ),
            ))
        return values

    async def _score(self, witnesses, *, fidelity=False, bodies=None, challenge=None):
        response_bodies = bodies or {
            "candidate": self.reference,
            "reference-a": self.reference,
            "reference-b": self.reference,
        }

        def handler(request):
            name = request.url.path.rsplit("/", 1)[-1]
            body = response_bodies[name]
            return httpx.Response(200, headers={"content-type": "video/mp4"}, content=body)

        return await media_prober.score_video_witnesses(
            challenge or self._challenge(fidelity=fidelity),
            witnesses,
            target_worker_id=self.TARGET,
            allowed_origins=[self.ORIGIN],
            max_bytes=1024 * 1024,
            fetch_timeout_s=2,
            decode_timeout_s=15,
            transport=httpx.MockTransport(handler),
        )

    def test_bounded_decoder_reports_real_container_timing(self):
        witness = media_prober.VerifiedMediaWitness(
            self.reference,
            hashlib.sha256(self.reference).hexdigest(),
            len(self.reference),
            "video/mp4",
        )
        profile = media_prober.decode_video_bounded(witness, max_frames=10, timeout_s=5)
        self.assertEqual((profile.width, profile.height), (64, 64))
        self.assertEqual(profile.frame_count, 8)
        self.assertAlmostEqual(profile.fps, 8.0)
        self.assertAlmostEqual(profile.duration_s, 1.0)
        self.assertTrue(any(distance >= 2 for distance in profile.motion_distances))

    async def test_contract_accepts_valid_video_and_rejects_repeated_still(self):
        outcome, detail = await self._score(self._witnesses())
        self.assertEqual(outcome, "healthy")
        self.assertEqual(detail["frame_count"], 8)
        self.assertEqual(detail["latency_budget_ms"], 120_000)

        witnesses = self._witnesses(candidate=self.static)
        outcome, detail = await self._score(
            witnesses,
            bodies={"candidate": self.static},
        )
        self.assertEqual(outcome, "failed")
        self.assertIn("repeated-still", detail["checks"])

    async def test_contract_rejects_wrong_timing_and_corrupt_candidate(self):
        outcome, detail = await self._score(
            self._witnesses(),
            challenge=self._challenge(frame_count=16, duration_s=2.0),
        )
        self.assertEqual(outcome, "failed")
        self.assertIn("frame-count", detail["checks"])
        self.assertIn("duration", detail["checks"])

        corrupt = b"not a video"
        outcome, detail = await self._score(
            self._witnesses(candidate=corrupt),
            bodies={"candidate": corrupt},
        )
        self.assertEqual(outcome, "failed")
        self.assertEqual(detail["reason"], "candidate-decode-failed")

    async def test_local_decoder_timeout_is_inconclusive(self):
        with patch.object(
            media_prober,
            "decode_video_bounded",
            side_effect=media_prober.VideoDecodeTimeout("deadline"),
        ):
            outcome, detail = await self._score(self._witnesses())
        self.assertEqual(outcome, "inconclusive")
        self.assertEqual(detail["reason"], "local-decoder-timeout")

    async def test_inconsistent_assignment_timing_is_inconclusive_before_fetch(self):
        with patch.object(
            media_prober,
            "fetch_media_witness",
            side_effect=AssertionError("fetch must not run"),
        ):
            outcome, detail = await self._score(
                self._witnesses(),
                challenge=self._challenge(frame_count=8, fps=8.0, duration_s=4.0),
            )
        self.assertEqual(outcome, "inconclusive")
        self.assertEqual(detail["reason"], "invalid-challenge-or-witness-set")

    async def test_fidelity_requires_reference_agreement_before_candidate_comparison(self):
        witnesses = self._witnesses(fidelity=True)
        outcome, detail = await self._score(witnesses, fidelity=True)
        self.assertEqual(outcome, "healthy")
        self.assertEqual(detail["reference_frame_distance_max"], 0)
        self.assertEqual(detail["phash_tolerance"], 12)
        self.assertEqual(detail["motion_tolerance"], 8.0)

        disagreeing = self._witnesses(fidelity=True, reference_b=self.outlier)
        outcome, detail = await self._score(
            disagreeing,
            fidelity=True,
            bodies={
                "candidate": self.reference,
                "reference-a": self.reference,
                "reference-b": self.outlier,
            },
        )
        self.assertEqual(outcome, "inconclusive")
        self.assertEqual(detail["reason"], "references-disagree")

    async def test_fidelity_fails_candidate_outlier_after_references_agree(self):
        witnesses = self._witnesses(fidelity=True, candidate=self.outlier)
        outcome, detail = await self._score(
            witnesses,
            fidelity=True,
            bodies={
                "candidate": self.outlier,
                "reference-a": self.reference,
                "reference-b": self.reference,
            },
        )
        self.assertEqual(outcome, "failed")
        self.assertEqual(detail["reason"], "candidate-outlier")

    async def test_invalid_video_witness_contract_fails_before_fetch(self):
        witnesses = self._witnesses()
        witnesses[0]["content_type"] = "image/png"
        with patch.object(
            media_prober,
            "fetch_media_witness",
            side_effect=AssertionError("fetch must not run"),
        ):
            outcome, detail = await media_prober.score_video_witnesses(
                self._challenge(),
                witnesses,
                target_worker_id=self.TARGET,
                allowed_origins=[self.ORIGIN],
                max_bytes=1024 * 1024,
                fetch_timeout_s=2,
                decode_timeout_s=5,
            )
        self.assertEqual(outcome, "inconclusive")
        self.assertEqual(detail["reason"], "invalid-challenge-or-witness-set")

        with patch.object(media_prober, "video_dependencies_available", return_value=False):
            outcome, detail = await self._score(self._witnesses())
        self.assertEqual(outcome, "inconclusive")
        self.assertEqual(detail["reason"], "video-dependencies-unavailable")


if __name__ == "__main__":
    unittest.main()
