# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Notification-only release checks. This module never downloads or runs updates."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Awaitable, Callable

import httpx

from . import __release_tag__

_RELEASES_URL = "https://api.github.com/repos/AIPowerGrid/grid-validator/releases?per_page=10"
_DOWNLOAD_ROOT = "https://github.com/AIPowerGrid/grid-validator/releases/tag/"
_MAX_RESPONSE_BYTES = 256 * 1024
_TAG_RE = re.compile(
    r"^v(?P<major>[0-9]+)\.(?P<minor>[0-9]+)\.(?P<patch>[0-9]+)"
    r"(?:-(?P<stage>preview|alpha|beta|rc)(?:\.(?P<number>[0-9]+))?)?$"
)
_STAGE_RANK = {"preview": 0, "alpha": 1, "beta": 2, "rc": 3}


@dataclass(frozen=True)
class UpdateNotice:
    current_tag: str
    latest_tag: str
    url: str


@dataclass(frozen=True)
class UpdateResult:
    status: str
    current_tag: str
    latest_tag: str = ""
    url: str = ""


def _version_key(tag: str) -> tuple[int, int, int, int, int, int] | None:
    if not isinstance(tag, str) or len(tag) > 64:
        return None
    match = _TAG_RE.fullmatch(tag)
    if not match:
        return None
    stage = match.group("stage")
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        1 if stage is None else 0,
        _STAGE_RANK.get(stage or "preview", 0),
        int(match.group("number") or 0),
    )


async def _fetch_releases() -> list[dict]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"aipg-validator/{__release_tag__}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with httpx.AsyncClient(timeout=3.0, follow_redirects=False, trust_env=False) as client:
        async with client.stream("GET", _RELEASES_URL, headers=headers) as response:
            response.raise_for_status()
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > _MAX_RESPONSE_BYTES:
                    raise RuntimeError("release response exceeds size limit")
    payload = json.loads(body)
    if not isinstance(payload, list):
        raise RuntimeError("release response is not a list")
    return payload


async def inspect_update(
    *,
    current_tag: str = __release_tag__,
    fetch_releases: Callable[[], Awaitable[list[dict]]] | None = None,
) -> UpdateResult:
    """Inspect release metadata, not artifact authenticity or Grid eligibility."""
    current_key = _version_key(current_tag)
    if current_key is None:
        return UpdateResult("source_build", current_tag)
    try:
        releases = await asyncio.wait_for((fetch_releases or _fetch_releases)(), timeout=8)
        if not isinstance(releases, list):
            raise ValueError("Invalid releases")
    except Exception:
        return UpdateResult("unavailable", current_tag)

    candidates: list[tuple[tuple[int, int, int, int, int, int], str]] = []
    for item in releases[:10]:
        if not isinstance(item, dict) or item.get("draft") is not False:
            continue
        tag = str(item.get("tag_name") or "")
        key = _version_key(tag)
        # A stable installation must never be invited onto a preview channel.
        if key is not None and (not current_key[3] or key[3]):
            candidates.append((key, tag))
    if not candidates:
        return UpdateResult("unavailable", current_tag)
    latest_key, latest_tag = max(candidates)
    if latest_key <= current_key:
        return UpdateResult("current", current_tag)
    return UpdateResult(
        status="available",
        current_tag=current_tag,
        latest_tag=latest_tag,
        url=f"{_DOWNLOAD_ROOT}{latest_tag}",
    )


async def check_for_update(
    *,
    current_tag: str = __release_tag__,
    fetch_releases: Callable[[], Awaitable[list[dict]]] | None = None,
) -> UpdateNotice | None:
    """Compatibility wrapper for notification-only runtime checks."""
    result = await inspect_update(current_tag=current_tag, fetch_releases=fetch_releases)
    if result.status != "available":
        return None
    return UpdateNotice(result.current_tag, result.latest_tag, result.url)
