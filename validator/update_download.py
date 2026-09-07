# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Bounded download and private staging. Never launches or activates a binary."""

from __future__ import annotations

import asyncio
import hashlib
import os
import shutil
import stat
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from urllib.parse import urljoin, urlsplit

import httpx

from .release_verify import (
    ARCHIVE_LIMIT,
    ATTESTATION_LIMIT,
    MANIFEST_LIMIT,
    REPOSITORY,
    ReleaseVerificationError,
    VerifiedRelease,
    verify_release,
)
from .update_check import _version_key

DOWNLOAD_SECONDS = 300


@dataclass(frozen=True)
class PreparedUpdate:
    directory: Path
    executable: Path
    executable_sha256: str
    release: VerifiedRelease


def _protect(path: Path, *, directory: bool = False) -> None:
    if os.name == "nt":
        from .cli import _protect_windows_file

        _protect_windows_file(path)
    else:
        path.chmod(0o700 if directory else 0o600)


def _private_root(root: Path) -> None:
    try:
        root.mkdir(mode=0o700)
    except FileExistsError:
        pass
    info = root.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or getattr(info, "st_file_attributes", 0) & 0x400
        or (os.name != "nt" and (info.st_uid != os.geteuid() or info.st_mode & 0o022))
    ):
        raise ReleaseVerificationError("unsafe_update_directory")
    _protect(root, directory=True)


def _private_file(path: Path) -> BinaryIO:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        _protect(path)
        return os.fdopen(fd, "wb")
    except BaseException:
        os.close(fd)
        raise


def _url_allowed(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        return (
            parsed.scheme == "https"
            and parsed.port in (None, 443)
            and not parsed.username
            and not parsed.password
            and not parsed.fragment
            and parsed.hostname
            in {"github.com", "api.github.com", "release-assets.githubusercontent.com"}
        )
    except ValueError:
        return False


async def _download(
    client: httpx.AsyncClient, url: str, path: Path, limit: int
) -> None:
    if not _url_allowed(url):
        raise ReleaseVerificationError("unsafe_update_url")
    # Redirects carry no credentials and may leave GitHub only for its exact
    # release asset host. No arbitrary storage host, proxy or encoded payload.
    for redirect in range(4):
        async with client.stream(
            "GET", url, headers={"Accept-Encoding": "identity"}
        ) as response:
            if response.status_code in {301, 302, 303, 307, 308}:
                target = urljoin(url, response.headers.get("location", ""))
                if (
                    redirect == 3
                    or not response.headers.get("location")
                    or not _url_allowed(target)
                    or urlsplit(target).hostname
                    != "release-assets.githubusercontent.com"
                ):
                    raise ReleaseVerificationError("unsafe_update_redirect")
                url = target
                continue
            response.raise_for_status()
            if (
                response.status_code != 200
                or response.headers.get("content-encoding", "identity") != "identity"
            ):
                raise ReleaseVerificationError("invalid_update_response")
            length = response.headers.get("content-length")
            if length is not None and (
                not length.isdigit() or len(length) > 12 or int(length) > limit
            ):
                raise ReleaseVerificationError("update_download_size")
            count = 0
            with _private_file(path) as output:
                async for chunk in response.aiter_raw(64 * 1024):
                    count += len(chunk)
                    if count > limit:
                        raise ReleaseVerificationError("update_download_size")
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            if count == 0 or (length is not None and count != int(length)):
                raise ReleaseVerificationError("incomplete_update_download")
            return
    raise ReleaseVerificationError("unsafe_update_redirect")


def extract_verified_archive(
    archive: Path, directory: Path, release: VerifiedRelease
) -> tuple[Path, str]:
    """Verify and extract through the same open file, never ZipFile.extract()."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(archive, flags)
    with os.fdopen(fd, "rb") as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size != release.size:
            raise ReleaseVerificationError("archive_size_mismatch")
        digest = hashlib.sha256()
        while chunk := source.read(64 * 1024):
            digest.update(chunk)
        if digest.hexdigest() != release.sha256:
            raise ReleaseVerificationError("archive_digest_mismatch")
        source.seek(0)
        expected = (
            "aipg-validator.exe"
            if release.platform == "windows-x64"
            else "aipg-validator"
        )
        with zipfile.ZipFile(source) as bundle:
            members = bundle.infolist()
            if len(members) != 1 or members[0].filename != expected:
                raise ReleaseVerificationError("unexpected_archive_member")
            member = members[0]
            mode = (member.external_attr >> 16) & 0xFFFF
            if (
                member.is_dir()
                or (mode and not stat.S_ISREG(mode))
                or member.flag_bits & 1
                or member.compress_type
                not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                or not 0 < member.file_size <= ARCHIVE_LIMIT
                or member.file_size > max(1, member.compress_size) * 100
            ):
                raise ReleaseVerificationError("unsafe_archive_member")
            target = directory / expected
            extracted = hashlib.sha256()
            count = 0
            output = _private_file(target)
            try:
                with output, bundle.open(member) as payload:
                    while chunk := payload.read(64 * 1024):
                        count += len(chunk)
                        if count > member.file_size or count > ARCHIVE_LIMIT:
                            raise ReleaseVerificationError("archive_expansion_limit")
                        extracted.update(chunk)
                        output.write(chunk)
                    output.flush()
                    os.fsync(output.fileno())
                if count != member.file_size:
                    raise ReleaseVerificationError("incomplete_archive_member")
                if os.name != "nt":
                    target.chmod(0o700)
                return target, extracted.hexdigest()
            except BaseException:
                # The caller owns a freshly created stage; never touch config,
                # journal, the active executable or an earlier release slot.
                target.unlink(missing_ok=True)
                raise


async def prepare_update(
    root: Path, *, tag: str, current_tag: str, platform: str
) -> PreparedUpdate:
    """Called in a killable updater child; the app applies an overall deadline."""
    current, target = _version_key(current_tag), _version_key(tag)
    if (
        current is None
        or target is None
        or target <= current
        or (current[3] and not target[3])
    ):
        raise ReleaseVerificationError("update_not_newer")
    _private_root(root)
    directory = Path(tempfile.mkdtemp(prefix="stage-", dir=root))
    _protect(directory, directory=True)
    try:
        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=False,
            trust_env=False,
            headers={
                "User-Agent": "aipg-validator-updater",
                "Accept-Encoding": "identity",
            },
        ) as client:
            manifest_path = directory / "validator-release.json"
            await asyncio.wait_for(
                _download(
                    client,
                    f"{REPOSITORY}/releases/download/{tag}/validator-release.json",
                    manifest_path,
                    MANIFEST_LIMIT,
                ),
                30,
            )
            manifest = manifest_path.read_bytes()
            manifest_digest = hashlib.sha256(manifest).hexdigest()
            attestations_path = directory / "attestations.json"
            await asyncio.wait_for(
                _download(
                    client,
                    f"https://api.github.com/repos/AIPowerGrid/grid-validator/attestations/sha256:{manifest_digest}",
                    attestations_path,
                    ATTESTATION_LIMIT,
                ),
                30,
            )
            release = verify_release(
                manifest, attestations_path.read_bytes(), tag=tag, platform=platform
            )
            archive = directory / release.archive
            await asyncio.wait_for(
                _download(
                    client,
                    f"{REPOSITORY}/releases/download/{tag}/{release.archive}",
                    archive,
                    release.size,
                ),
                DOWNLOAD_SECONDS,
            )
        executable, digest = extract_verified_archive(archive, directory, release)
        return PreparedUpdate(directory, executable, digest, release)
    except BaseException:
        shutil.rmtree(directory)
        raise
