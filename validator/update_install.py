# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Private versioned installs; never overwrite a running or service executable."""

from __future__ import annotations

import hashlib
import os
import re
import stat
import uuid
from pathlib import Path
from typing import Any

from .release_verify import ARCHIVE_LIMIT, ReleaseVerificationError, _json
from .update_check import _version_key
from .update_download import _private_file, _private_root


class InstallStore:
    def __init__(self, config: Path):
        self.root = config.parent / (config.name + ".updates")
        self.pointer = self.root / "active.json"

    @staticmethod
    def check_path(path: Path, directory: bool = False) -> None:
        info = path.lstat()
        if (
            (
                not stat.S_ISDIR(info.st_mode)
                if directory
                else not stat.S_ISREG(info.st_mode)
            )
            or getattr(info, "st_file_attributes", 0) & 0x400
            or (
                os.name != "nt"
                and (info.st_uid != os.geteuid() or info.st_mode & 0o022)
            )
        ):
            raise ReleaseVerificationError("unsafe_update_path")

    def executable(self, entry: dict[str, Any]) -> Path:
        if (
            not isinstance(entry, dict)
            or set(entry) != {"tag", "path", "sha256"}
            or not isinstance(entry["tag"], str)
            or _version_key(entry["tag"]) is None
            or not isinstance(entry["path"], str)
            or not re.fullmatch(
                r"attempt-[a-f0-9]{32}/stage-[A-Za-z0-9_-]+/aipg-validator(?:\.exe)?",
                entry["path"],
            )
            or not isinstance(entry["sha256"], str)
            or not re.fullmatch(r"[a-f0-9]{64}", entry["sha256"])
        ):
            raise ReleaseVerificationError("invalid_update_install")
        path = self.root / entry["path"]
        self.check_path(self.root, directory=True)
        self.check_path(path.parent.parent, directory=True)
        self.check_path(path.parent, directory=True)
        self.check_path(path)
        with os.fdopen(
            os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)), "rb"
        ) as source:
            if not 0 < os.fstat(source.fileno()).st_size <= ARCHIVE_LIMIT:
                raise ReleaseVerificationError("invalid_update_install")
            digest = hashlib.sha256()
            while chunk := source.read(65536):
                digest.update(chunk)
        if digest.hexdigest() != entry["sha256"]:
            raise ReleaseVerificationError("update_install_changed")
        return path

    def selected(self) -> dict[str, Any] | None:
        if not self.root.exists():
            return None
        self.check_path(self.root, directory=True)
        if not self.pointer.exists():
            return None
        self.check_path(self.pointer)
        with self.pointer.open("rb") as source:
            state = _json(source.read(4097), 4096)
        if (
            set(state) != {"schema", "phase", "active", "previous"}
            or state["schema"] != "aipg.validator.install.v1"
            or not isinstance(state["phase"], str)
            or state["phase"] not in {"pending", "active"}
        ):
            raise ReleaseVerificationError("invalid_update_install")
        # An interrupted handoff never promotes the uncommitted candidate.
        entry: dict[str, Any] | None = (
            state["previous"] if state["phase"] == "pending" else state["active"]
        )
        if entry is not None:
            self.executable(entry)
        return entry

    def write(
        self,
        active: dict[str, Any] | None,
        previous: dict[str, Any] | None,
        *,
        pending: bool = False,
    ) -> None:
        import json

        _private_root(self.root)
        for entry in (active, previous):
            if entry is not None:
                self.executable(entry)
        value = {
            "schema": "aipg.validator.install.v1",
            "phase": "pending" if pending else "active",
            "active": active,
            "previous": previous,
        }
        temp = self.root / ("pointer-" + uuid.uuid4().hex)
        try:
            with _private_file(temp) as output:
                output.write(json.dumps(value).encode())
                output.flush()
                os.fsync(output.fileno())
            os.replace(temp, self.pointer)
            if os.name != "nt":
                fd = os.open(self.root, os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
        finally:
            temp.unlink(missing_ok=True)

    def from_preparation(self, result: dict[str, Any], tag: str) -> dict[str, Any]:
        try:
            path = Path(result["executable"])
            entry = {
                "tag": tag,
                "path": path.relative_to(self.root).as_posix(),
                "sha256": result["executable_sha256"],
            }
            if result["release"]["tag"] != tag:
                raise ValueError("tag mismatch")
            self.executable(entry)
            return entry
        except (KeyError, TypeError, ValueError) as exc:
            raise ReleaseVerificationError("invalid_update_install") from exc
