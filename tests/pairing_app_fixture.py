# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Manual browser fixture: python -m tests.pairing_app_fixture. No live Grid calls."""

import json
import sys
import tempfile
import threading
import time
from pathlib import Path

import httpx

from tests.test_account_pairing import FakeCore
from validator.account_pairing import PairingController
from validator.operator_app import OperatorServer, Supervisor


def main() -> None:
    core = FakeCore()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "node.env"
        path.touch(mode=0o600)
        path.write_text(
            f"VALIDATOR_API_KEY={core.identity.api_key}\n"
            f"VALIDATOR_PRIVATE_KEY={core.identity.private_key}\n"
            f"VALIDATOR_WALLET={core.identity.wallet}\n"
        )
        supervisor = Supervisor(path)
        supervisor.pairing = PairingController(
            lambda: core.identity, httpx.MockTransport(core.handle)
        )
        # This fixture does not run the network validator or enroll accounts.
        supervisor.start = lambda action: False
        server = OperatorServer(supervisor)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        print(server.origin + "/#" + server.token, flush=True)
        print(
            "Fixture commands: approve, expire, outage, restore, status, quit",
            flush=True,
        )
        try:
            for line in sys.stdin:
                command = line.strip()
                if command == "approve":
                    core.status = "approved"
                elif command == "expire":
                    core.expiry = int(time.time()) - 1
                elif command == "outage":
                    supervisor.pairing.transport = httpx.MockTransport(
                        lambda req: httpx.Response(503)
                    )
                elif command == "restore":
                    supervisor.pairing.transport = httpx.MockTransport(core.handle)
                    core.expiry = int(time.time()) + 590
                elif command == "quit":
                    break
                print(
                    json.dumps(
                        {
                            "calls": len(core.calls),
                            "signed": len(core.signatures),
                            "linked": core.linked,
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
