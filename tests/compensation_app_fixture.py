# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Disposable browser fixture with synthetic rewards; no live Grid or transfers."""

import json
import sys
import tempfile
import threading
from pathlib import Path

import httpx

from tests.test_compensation import FakeCompensation
from validator.cli import _write_private_env
from validator.compensation import CompensationController
from validator.operator_app import OperatorServer, Supervisor


def main() -> None:
    core = FakeCompensation()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "node.env"
        _write_private_env(
            path,
            [
                f"VALIDATOR_API_KEY={core.identity.api_key}",
                f"VALIDATOR_PRIVATE_KEY={core.identity.private_key}",
                f"VALIDATOR_WALLET={core.identity.wallet}",
            ],
        )
        supervisor = Supervisor(path)
        supervisor.start = lambda action: False
        supervisor.compensation = CompensationController(
            lambda: core.identity, httpx.MockTransport(core.handle)
        )
        server = OperatorServer(supervisor)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        print(server.origin + "/#" + server.token, flush=True)
        try:
            for line in sys.stdin:
                command = line.strip()
                if command == "approve":
                    core.status = "awaiting_node"
                elif command == "outage":
                    supervisor.compensation.transport = httpx.MockTransport(
                        lambda request: httpx.Response(503)
                    )
                elif command == "restore":
                    supervisor.compensation.transport = httpx.MockTransport(core.handle)
                elif command == "quit":
                    break
                print(
                    json.dumps(
                        {
                            "calls": len(core.calls),
                            "signed": len(core.signatures),
                            "status": core.status,
                        }
                    ),
                    flush=True,
                )
        finally:
            server.shutdown()
            server.server_close()
            supervisor.close()
            thread.join(5)


if __name__ == "__main__":
    main()
