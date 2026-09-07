# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from validator.update_download import _private_root, _private_file
from validator.update_install import InstallStore
from validator.release_verify import ReleaseVerificationError


class InstallFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config = Path(self.temp.name) / ".env"
        self.config.write_bytes(b"synthetic unchanged identity")
        self.journal = Path(self.temp.name) / "validator.sqlite"
        self.journal.write_bytes(b"synthetic unchanged journal")
        self.store = InstallStore(self.config)

    def tearDown(self):
        self.assertEqual(self.config.read_bytes(), b"synthetic unchanged identity")
        self.assertEqual(self.journal.read_bytes(), b"synthetic unchanged journal")
        self.temp.cleanup()

    def entry(self, number=16):
        _private_root(self.store.root)
        attempt = self.store.root / ("attempt-" + f"{number:032x}")
        _private_root(attempt)
        directory = attempt / "stage-fixture"
        _private_root(directory)
        path = directory / "aipg-validator"
        payload = f"binary fixture {number}".encode()
        with _private_file(path) as output:
            output.write(payload)
        return {
            "tag": f"v0.1.0-preview.{number}",
            "path": path.relative_to(self.store.root).as_posix(),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }


class InstallTests(InstallFixture, unittest.TestCase):
    def test_no_install_state_is_created_by_read(self):
        self.assertIsNone(self.store.selected())
        self.assertFalse(self.store.root.exists())

    def test_pending_handoff_keeps_previous_then_commit_selects_candidate(self):
        old, new = self.entry(16), self.entry(17)
        self.store.write(old, None)
        self.store.write(new, old, pending=True)
        self.assertEqual(InstallStore(self.config).selected(), old)
        self.store.write(new, old)
        self.assertEqual(InstallStore(self.config).selected(), new)
        self.store.write(old, None)
        self.assertEqual(self.store.selected(), old)

    def test_first_interrupted_update_falls_back_to_bootstrap(self):
        self.store.write(self.entry(), None, pending=True)
        self.assertIsNone(InstallStore(self.config).selected())

    def test_changed_binary_never_executes(self):
        entry = self.entry()
        self.store.write(entry, None)
        self.store.executable(entry).write_bytes(b"changed")
        with self.assertRaisesRegex(ReleaseVerificationError, "update_install_changed"):
            self.store.selected()

    def test_paths_and_ambiguous_pointer_are_rejected(self):
        entry = self.entry()
        for path in (
            "../aipg-validator",
            "/tmp/aipg-validator",
            "stage-one/aipg-validator",
            entry["path"] + "/../other",
        ):
            with self.subTest(path=path), self.assertRaises(ReleaseVerificationError):
                self.store.executable({**entry, "path": path})
        with _private_file(self.store.pointer) as output:
            output.write(b'{"phase":"active","phase":"pending"}')
        with self.assertRaises(ValueError):
            self.store.selected()

    def test_failed_atomic_replace_leaves_previous(self):
        old, new = self.entry(16), self.entry(17)
        self.store.write(old, None)
        with (
            patch(
                "validator.update_install.os.replace", side_effect=OSError("fixture")
            ),
            self.assertRaises(OSError),
        ):
            self.store.write(new, old)
        self.assertEqual(self.store.selected(), old)
        self.assertEqual(list(self.store.root.glob("pointer-*")), [])

    @unittest.skipIf(os.name == "nt", "POSIX symlink/ownership fixture")
    def test_symlink_and_writable_directory_rejected(self):
        entry = self.entry()
        path = self.store.executable(entry)
        path.unlink()
        path.symlink_to(self.config)
        with self.assertRaises(ReleaseVerificationError):
            self.store.executable(entry)
        self.store.root.chmod(0o777)
        with self.assertRaises(ReleaseVerificationError):
            self.store.selected()
        self.store.root.chmod(0o700)


if __name__ == "__main__":
    unittest.main()
