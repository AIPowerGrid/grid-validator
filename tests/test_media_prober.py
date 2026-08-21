import gzip
import hashlib
import logging
import unittest
from unittest.mock import patch

import httpx

from validator import media_prober


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


if __name__ == "__main__":
    unittest.main()
