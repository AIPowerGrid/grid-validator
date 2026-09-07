# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Opt-in frozen handoff; supply disposable preview.0 and preview.17 builds."""

import contextlib
import hashlib
import http.client
import io
import json
import os
import queue
import shutil
import subprocess
import threading
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
    def cold_launch(self, expected_tag):
        env = os.environ.copy()
        env.update(VALIDATOR_ENV=str(self.config), PYINSTALLER_RESET_ENVIRONMENT="1")
        options = (
            {"creationflags": subprocess.CREATE_NO_WINDOW}
            if os.name == "nt"
            else {"start_new_session": True}
        )
        process = subprocess.Popen(
            [os.environ["TEST_VALIDATOR_BOOTSTRAP_BINARY"], "app", "--no-browser"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
            **options,
        )
        result = queue.Queue()

        def read():
            for _ in range(5):
                line = process.stdout.readline(4097)
                if line.startswith(b"Local validator app: "):
                    result.put(line.decode().strip().split("Local validator app: ")[1])
                    return
                if not line:
                    return

        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        try:
            url = urlsplit(result.get(timeout=40))
            connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
            headers = {
                "Authorization": "Bearer " + url.fragment,
                "Origin": f"http://{url.netloc}",
                "Content-Type": "application/json",
            }
            connection.request("GET", "/status.json", headers=headers)
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read())["version"], expected_tag)
            connection.close()
            connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
            connection.request(
                "POST", "/control", json.dumps({"action": "quit"}), headers
            )
            response = connection.getresponse()
            self.assertEqual(response.status, 202)
            response.read()
            connection.close()
            process.wait(timeout=20)
            self.assertEqual(process.returncode, 0)
        finally:
            uh.stop_owned(process)
            reader.join(timeout=5)
            process.stdout.close()

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
                with patch.object(uh.webbrowser, "open") as browser:
                    self.assertTrue(
                        uh.handoff(
                            self.config, entry, False, port=url.port, token=url.fragment
                        )
                    )
                    browser.assert_not_called()
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
                children[-1].wait(timeout=20)
                self.assertEqual(children[-1].returncode, 0)
                self.cold_launch(entry["tag"])
                wrong = {**entry, "tag": "v0.1.0-preview.999"}
                self.assertFalse(
                    uh.handoff(self.config, wrong, False, open_browser=False)
                )
                self.assertEqual(self.store.selected(), entry)
                real_write = uh.InstallStore.write

                def fail_pending(store, active, previous, *, pending=False):
                    if pending:
                        raise OSError("fixture disk failure after readiness")
                    return real_write(store, active, previous, pending=pending)

                with patch.object(uh.InstallStore, "write", fail_pending):
                    self.assertFalse(
                        uh.handoff(self.config, entry, False, open_browser=False)
                    )
                self.assertEqual(self.store.selected(), entry)
                self.cold_launch(entry["tag"])
                self.store.write(entry, None, pending=True)
                self.cold_launch("v0.1.0-preview.0")
                self.assertTrue(all(child.poll() is not None for child in children))
            finally:
                for child in children:
                    uh.stop_owned(child)


if __name__ == "__main__":
    unittest.main()
