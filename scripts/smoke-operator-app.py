# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Offline native-binary HTTP/child-process smoke; never print the private URL."""

import http.client
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit


def smoke(binary: Path) -> None:
    with tempfile.TemporaryDirectory() as directory:
        config = Path(directory) / "node.env"
        # Present but invalid credentials exercise the managed child without Grid traffic.
        config.write_text(
            "VALIDATOR_API_KEY=invalid\nVALIDATOR_PRIVATE_KEY=invalid\nVALIDATOR_WALLET=invalid\n",
            encoding="utf-8",
        )
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("VALIDATOR_", "GRID_"))
        }
        env["VALIDATOR_ENV"] = str(config)
        env["PYTHONUNBUFFERED"] = "1"
        process = subprocess.Popen(
            [str(binary.resolve()), "app", "--no-browser"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
            text=True,
        )
        lines: queue.Queue[str] = queue.Queue()

        def read() -> None:
            assert process.stdout is not None
            for line in process.stdout:
                lines.put(line)

        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        try:
            line = lines.get(timeout=60)
            assert line.startswith("Local validator app: "), "App did not open"
            url = urlsplit(line.removeprefix("Local validator app: ").strip())
            assert url.hostname == "127.0.0.1" and url.port and len(url.fragment) >= 32
            print("Packaged app listening on loopback.", flush=True)
            origin = f"http://{url.netloc}"

            def request(
                path: str, action: str | None = None, auth: bool = True
            ) -> tuple[int, bytes]:
                connection = http.client.HTTPConnection(
                    "127.0.0.1", url.port, timeout=10
                )
                headers = {"Authorization": "Bearer " + url.fragment} if auth else {}
                body = None
                if action:
                    headers.update(
                        {"Origin": origin, "Content-Type": "application/json"}
                    )
                    body = json.dumps({"action": action})
                try:
                    connection.request("POST" if action else "GET", path, body, headers)
                    response = connection.getresponse()
                    return response.status, response.read()
                finally:
                    connection.close()

            for asset in ("/", "/app.js", "/app.css", "/logo.png"):
                code, payload = request(asset)
                assert code == 200 and payload, "Packaged UI asset missing"
            assert request("/status.json", auth=False)[0] == 401
            print("Packaged assets and session guard passed.", flush=True)
            for _ in range(2):
                assert request("/control", "run")[0] == 202
                deadline = time.monotonic() + 30
                while True:
                    code, body = request("/status.json")
                    assert code == 200
                    state = json.loads(body)
                    if (
                        state["error"] == "configuration_invalid"
                        and not state["running"]
                    ):
                        break
                    assert time.monotonic() < deadline, (
                        "Managed child did not fail cleanly"
                    )
                    time.sleep(0.1)
            print("Managed child failure and restart passed.", flush=True)
            code, diagnostics = request("/diagnostics.json")
            assert code == 200
            for secret in (url.fragment, str(config), "VALIDATOR_PRIVATE_KEY"):
                assert secret.encode() not in diagnostics, (
                    "Diagnostics exposed local material"
                )
            assert request("/control", "stop")[0] == 202
            assert "VALIDATOR_PRIVATE_KEY=invalid" in config.read_text(encoding="utf-8")
            assert request("/control", "quit")[0] == 202
            assert process.wait(timeout=30) == 0, "App did not exit cleanly"
            print("Packaged app shutdown passed.", flush=True)
        finally:
            if process.poll() is None:
                if os.name == "nt":
                    # TerminateProcess alone leaves a onefile bootloader's child alive.
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=15,
                    )
                else:
                    process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            reader.join(timeout=5)
            if process.stdout and not reader.is_alive():
                process.stdout.close()
    print(
        "Packaged operator app: assets, authentication, child failure/restart, safe diagnostics passed."
    )


if __name__ == "__main__":
    smoke(Path(sys.argv[1]))
