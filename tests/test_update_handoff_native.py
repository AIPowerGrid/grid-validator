# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Opt-in frozen app handoff; supply a disposable preview.17 fixture build."""

import contextlib
import hashlib
import http.client
import io
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

from tests.test_update_install import InstallFixture
from validator import update_handoff as uh


@unittest.skipUnless(
    os.getenv("TEST_VALIDATOR_UPDATE_BINARY"), "native update fixture not supplied"
)
class NativeHandoffTests(InstallFixture, unittest.TestCase):
    def candidate(self):
        entry = self.entry(17)
        path = self.store.executable(entry)
        if os.name == "nt":
            renamed = path.with_suffix(".exe")
            path.rename(renamed)
            path = renamed
            entry["path"] = path.relative_to(self.store.root).as_posix()
        with (
            Path(os.environ["TEST_VALIDATOR_UPDATE_BINARY"]).open("rb") as source,
            path.open("wb") as output,
        ):
            shutil.copyfileobj(source, output)
        if os.name != "nt":
            path.chmod(0o700)
        digest = hashlib.sha256()
        with path.open("rb") as source:
            while chunk := source.read(65536):
                digest.update(chunk)
        entry["sha256"] = digest.hexdigest()
        return entry

    def test_frozen_app_handoff_and_wrong_version_rollback(self):
        entry = self.candidate()
        original = subprocess.Popen
        children = []

        def launch(*args, **kwargs):
            process = original(*args, **kwargs)
            children.append(process)
            return process

        with patch.object(uh.subprocess, "Popen", side_effect=launch):
            try:
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertTrue(
                        uh.handoff(self.config, entry, False, open_browser=False)
                    )
                self.assertEqual(self.store.selected(), entry)
                url = urlsplit(
                    output.getvalue().strip().split("Updated local validator app: ")[1]
                )
                connection = http.client.HTTPConnection(
                    url.hostname, url.port, timeout=5
                )
                connection.request(
                    "POST",
                    "/control",
                    json.dumps({"action": "quit"}),
                    {
                        "Authorization": "Bearer " + url.fragment,
                        "Origin": f"http://{url.netloc}",
                        "Content-Type": "application/json",
                    },
                )
                response = connection.getresponse()
                self.assertEqual(response.status, 202)
                response.read()
                connection.close()
                children[0].wait(timeout=20)
                self.assertEqual(children[0].returncode, 0)
                wrong = {**entry, "tag": "v0.1.0-preview.999"}
                self.assertFalse(
                    uh.handoff(self.config, wrong, False, open_browser=False)
                )
                self.assertEqual(self.store.selected(), entry)
                self.assertTrue(all(child.poll() is not None for child in children))
            finally:
                for child in children:
                    uh.stop_owned(child)


if __name__ == "__main__":
    unittest.main()
