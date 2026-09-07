# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

import contextlib
import http.client
import io
import json
import subprocess
import sys
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit

from tests.test_update_install import InstallFixture
from validator import update_handoff as uh


class HandoffTests(InstallFixture, unittest.TestCase):
    """Real child/HTTP/selection protocol; simulated frozen identity, no Grid."""

    def spawn(self, entry, mode="normal"):
        original = subprocess.Popen
        self.children = []
        executable = str(self.store.executable(entry))
        program = (
            "import sys; from validator import update_handoff as h, operator_app as a; "
            f"sys.frozen=True; sys.executable={executable!r}; "
            f"h.__release_tag__=a.__release_tag__={entry['tag']!r}; "
            "sys.exit(h.updated_app())"
        )
        if mode == "failed":
            program = "import sys; sys.exit(1)"
        if mode == "wrong-version":
            program = program.replace(repr(entry["tag"]), repr("v0.1.0-preview.999"))

        def launch(_args, **kwargs):
            child = original([sys.executable, "-c", program], **kwargs)
            self.children.append(child)
            return child

        return patch.object(uh.subprocess, "Popen", side_effect=launch)

    def test_real_app_handoff_commits_and_quits_without_touching_identity(self):
        entry = self.entry(17)
        output = io.StringIO()
        with (
            self.spawn(entry),
            contextlib.redirect_stdout(output),
            patch.object(uh.webbrowser, "open") as browser,
        ):
            try:
                self.assertTrue(
                    uh.handoff(self.config, entry, False, open_browser=False)
                )
                browser.assert_not_called()
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
                self.assertEqual(connection.getresponse().status, 202)
                connection.close()
                self.children[0].wait(timeout=10)
                self.assertEqual(self.children[0].returncode, 0)
            finally:
                for child in self.children:
                    uh.stop_owned(child)

    def test_failed_start_and_wrong_version_restore_previous(self):
        old, new = self.entry(16), self.entry(17)
        self.store.write(old, None)
        for mode in ("failed", "wrong-version"):
            with self.subTest(mode=mode), self.spawn(new, mode):
                self.assertFalse(
                    uh.handoff(self.config, new, False, open_browser=False)
                )
                self.assertEqual(self.store.selected(), old)
                self.assertTrue(
                    all(child.poll() is not None for child in self.children)
                )

    def test_failed_pointer_commit_stops_candidate_and_keeps_previous(self):
        old, new = self.entry(16), self.entry(17)
        self.store.write(old, None)
        real_write = uh.InstallStore.write

        def write(store, active, previous, *, pending=False):
            if pending:
                raise OSError("disk failure fixture")
            return real_write(store, active, previous, pending=pending)

        with self.spawn(new), patch.object(uh.InstallStore, "write", write):
            self.assertFalse(uh.handoff(self.config, new, False, open_browser=False))
        self.assertEqual(self.store.selected(), old)
        self.assertTrue(all(child.poll() is not None for child in self.children))


if __name__ == "__main__":
    unittest.main()
