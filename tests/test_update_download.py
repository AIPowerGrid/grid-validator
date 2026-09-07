# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Staging safety; fixture provenance is mocked, downloads use HTTPX transport."""

import hashlib
import io
import os
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import httpx

from validator import update_download as ud
from validator.release_verify import ReleaseVerificationError, VerifiedRelease


def archive_bytes(
    name="aipg-validator", payload=b"fixture executable", mode=stat.S_IFREG | 0o700
):
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        member = zipfile.ZipInfo(name)
        member.external_attr = mode << 16
        archive.writestr(member, payload)
    return raw.getvalue()


def release_for(raw):
    return VerifiedRelease(
        "v0.1.0-preview.17",
        "a" * 40,
        "linux-x64",
        "aipg-validator-linux-x64.zip",
        len(raw),
        hashlib.sha256(raw).hexdigest(),
        "b" * 64,
        True,
    )


class ArchiveTests(unittest.TestCase):
    def test_compression_bomb_and_crc_failure_leave_no_executable(self):
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("aipg-validator", b"x" * 1_000_000)
        corrupt = bytearray(archive_bytes())
        offset = corrupt.find(b"fixture executable")
        self.assertGreater(offset, 0)
        corrupt[offset] ^= 1
        for data in (raw.getvalue(), bytes(corrupt)):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                path = root / "download.zip"
                path.write_bytes(data)
                with self.assertRaises((ReleaseVerificationError, zipfile.BadZipFile)):
                    ud.extract_verified_archive(path, root, release_for(data))
                self.assertFalse((root / "aipg-validator").exists())

    def test_exact_digest_and_regular_file_extract_privately(self):
        raw = archive_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "download.zip"
            archive.write_bytes(raw)
            target, digest = ud.extract_verified_archive(
                archive, root, release_for(raw)
            )
            self.assertEqual(target.read_bytes(), b"fixture executable")
            self.assertEqual(digest, hashlib.sha256(target.read_bytes()).hexdigest())
            if os.name != "nt":
                self.assertEqual(target.stat().st_mode & 0o777, 0o700)

    def test_tamper_size_and_digest_do_not_create_executable(self):
        raw = archive_bytes()
        for changed in (raw + b"x", raw[:-1] + bytes([raw[-1] ^ 1])):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                archive = root / "download.zip"
                archive.write_bytes(changed)
                with self.assertRaises(ReleaseVerificationError):
                    ud.extract_verified_archive(archive, root, release_for(raw))
                self.assertFalse((root / "aipg-validator").exists())

    def test_paths_links_devices_and_extra_entries_rejected(self):
        variants = [
            archive_bytes("../escape"),
            archive_bytes("nested/aipg-validator"),
            archive_bytes("/aipg-validator"),
            archive_bytes(mode=stat.S_IFLNK | 0o700),
            archive_bytes(mode=stat.S_IFCHR | 0o700),
            archive_bytes(payload=b""),
        ]
        extra = io.BytesIO(archive_bytes())
        with zipfile.ZipFile(extra, "a") as archive:
            archive.writestr("unexpected", b"extra")
        variants.append(extra.getvalue())
        for raw in variants:
            with (
                self.subTest(digest=hashlib.sha256(raw).hexdigest()),
                tempfile.TemporaryDirectory() as tmp,
            ):
                root = Path(tmp)
                archive = root / "download.zip"
                archive.write_bytes(raw)
                with self.assertRaises(ReleaseVerificationError):
                    ud.extract_verified_archive(archive, root, release_for(raw))
                self.assertEqual(list(root.iterdir()), [archive])

    def test_existing_target_is_not_overwritten_or_deleted(self):
        raw = archive_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "download.zip"
            archive.write_bytes(raw)
            target = root / "aipg-validator"
            target.write_bytes(b"previous executable")
            with self.assertRaises(FileExistsError):
                ud.extract_verified_archive(archive, root, release_for(raw))
            self.assertEqual(target.read_bytes(), b"previous executable")

    @unittest.skipIf(
        os.name == "nt", "Windows symlink creation requires a separate native policy"
    )
    def test_symlink_root_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "real").mkdir()
            (root / "link").symlink_to(root / "real", target_is_directory=True)
            with self.assertRaises(ReleaseVerificationError):
                ud._private_root(root / "link")


class DownloadTests(unittest.IsolatedAsyncioTestCase):
    async def download(self, handler, *, limit=1024):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "download"
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(handler), trust_env=False
            ) as client:
                await ud._download(
                    client,
                    "https://github.com/AIPowerGrid/grid-validator/releases/download/v0.1.0-preview.17/test.zip",
                    target,
                    limit,
                )
            return target.read_bytes()

    async def test_pinned_asset_redirect_and_stream(self):
        seen = []

        def handler(request):
            seen.append(request)
            if request.url.host == "github.com":
                return httpx.Response(
                    302,
                    headers={
                        "location": "https://release-assets.githubusercontent.com/asset"
                    },
                )
            return httpx.Response(
                200,
                headers={"content-length": "7"},
                stream=httpx.ByteStream(b"payload"),
            )

        self.assertEqual(await self.download(handler), b"payload")
        self.assertEqual(len(seen), 2)
        self.assertTrue(
            all(request.headers["accept-encoding"] == "identity" for request in seen)
        )
        self.assertTrue(all("authorization" not in request.headers for request in seen))

    async def test_untrusted_redirects_never_requested(self):
        for location in (
            "http://release-assets.githubusercontent.com/a",
            "https://evil.example/a",
            "https://127.0.0.1/a",
            "https://github.com.evil.example/a",
            "https://user:pass@release-assets.githubusercontent.com/a",
            "https://release-assets.githubusercontent.com:8443/a",
        ):
            seen = []

            def handler(request):
                seen.append(request)
                return httpx.Response(302, headers={"location": location})

            with (
                self.subTest(location=location),
                self.assertRaises(ReleaseVerificationError),
            ):
                await self.download(handler)
            self.assertEqual(len(seen), 1)

    async def test_size_encoding_and_incomplete_reply_rejected(self):
        for headers, data in (
            ({"content-length": "2000"}, b"x"),
            ({"content-encoding": "gzip"}, b"x"),
            ({}, b"x" * 1025),
            ({"content-length": "10"}, b"short"),
            ({}, b""),
        ):

            def handler(_request):
                return httpx.Response(
                    200, headers=headers, stream=httpx.ByteStream(data)
                )

            with (
                self.subTest(headers=headers),
                self.assertRaises(ReleaseVerificationError),
            ):
                await self.download(handler)

    async def test_redirect_loop_is_bounded(self):
        seen = []

        def handler(request):
            seen.append(request)
            return httpx.Response(
                302,
                headers={
                    "location": "https://release-assets.githubusercontent.com/loop"
                },
            )

        with self.assertRaises(ReleaseVerificationError):
            await self.download(handler)
        self.assertEqual(len(seen), 4)


class PrepareTests(unittest.IsolatedAsyncioTestCase):
    async def test_interrupted_archive_download_removes_partial_stage(self):
        raw = archive_bytes()
        client_type = httpx.AsyncClient

        class BrokenStream(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b"partial"
                raise httpx.ReadError("fixture interruption")

        def handler(request):
            stream = (
                BrokenStream()
                if request.url.path.endswith(".zip")
                else httpx.ByteStream(b'{"fixture":true}')
            )
            return httpx.Response(200, stream=stream)

        def client(**kwargs):
            return client_type(transport=httpx.MockTransport(handler), **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "updates"
            root.mkdir(mode=0o700)
            (root / "previous").write_bytes(b"old release")
            with (
                patch.object(ud.httpx, "AsyncClient", side_effect=client),
                patch.object(ud, "verify_release", return_value=release_for(raw)),
            ):
                with self.assertRaises(httpx.ReadError):
                    await ud.prepare_update(
                        root,
                        tag="v0.1.0-preview.17",
                        current_tag="v0.1.0-preview.16",
                        platform="linux-x64",
                    )
            self.assertEqual([path.name for path in root.iterdir()], ["previous"])
            self.assertEqual((root / "previous").read_bytes(), b"old release")

    async def test_provenance_precedes_archive_and_existing_state_survives(self):
        raw = archive_bytes()
        release = release_for(raw)
        events = []
        client_type = httpx.AsyncClient

        def handler(request):
            events.append(request.url.path)
            content = raw if request.url.path.endswith(".zip") else b'{"fixture":true}'
            return httpx.Response(200, stream=httpx.ByteStream(content))

        def client(**kwargs):
            self.assertIs(kwargs["trust_env"], False)
            self.assertIs(kwargs["follow_redirects"], False)
            return client_type(transport=httpx.MockTransport(handler), **kwargs)

        def verify(*_args, **_kwargs):
            events.append("verified")
            return release

        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            (parent / ".env").write_bytes(b"existing identity fixture")
            (parent / "journal.sqlite").write_bytes(b"existing queued evidence fixture")
            with (
                patch.object(ud.httpx, "AsyncClient", side_effect=client),
                patch.object(ud, "verify_release", side_effect=verify),
            ):
                prepared = await ud.prepare_update(
                    parent / "updates",
                    tag=release.tag,
                    current_tag="v0.1.0-preview.16",
                    platform="linux-x64",
                )
            self.assertEqual(prepared.executable.read_bytes(), b"fixture executable")
            self.assertLess(
                events.index("verified"),
                next(i for i, event in enumerate(events) if event.endswith(".zip")),
            )
            self.assertEqual(
                (parent / ".env").read_bytes(), b"existing identity fixture"
            )
            self.assertEqual(
                (parent / "journal.sqlite").read_bytes(),
                b"existing queued evidence fixture",
            )

    async def test_failed_signature_cleans_only_new_stage(self):
        client_type = httpx.AsyncClient
        seen = []

        def handler(request):
            seen.append(request.url.path)
            return httpx.Response(200, stream=httpx.ByteStream(b'{"fixture":true}'))

        def client(**kwargs):
            return client_type(transport=httpx.MockTransport(handler), **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "updates"
            root.mkdir(mode=0o700)
            (root / "previous").write_bytes(b"old release")
            with (
                patch.object(ud.httpx, "AsyncClient", side_effect=client),
                patch.object(
                    ud,
                    "verify_release",
                    side_effect=ReleaseVerificationError("bad_signature"),
                ),
            ):
                with self.assertRaises(ReleaseVerificationError):
                    await ud.prepare_update(
                        root,
                        tag="v0.1.0-preview.17",
                        current_tag="v0.1.0-preview.16",
                        platform="linux-x64",
                    )
            self.assertEqual([p.name for p in root.iterdir()], ["previous"])
            self.assertFalse(any(url.endswith(".zip") for url in seen))

    async def test_downgrade_and_stable_to_preview_do_not_touch_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "updates"
            for current, target in (
                ("v0.1.0-preview.17", "v0.1.0-preview.16"),
                ("v0.1.0", "v0.2.0-preview.1"),
                ("v0.1.0-dev", "v0.1.0-preview.17"),
            ):
                with self.assertRaises(ReleaseVerificationError):
                    await ud.prepare_update(
                        root, tag=target, current_tag=current, platform="linux-x64"
                    )
            self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()
