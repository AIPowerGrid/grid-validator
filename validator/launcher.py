# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Interactive console launcher; every action uses a fresh config process."""

import os
import subprocess
import sys
import webbrowser
from pathlib import Path

CONSOLE_URL = "https://console.aipowergrid.io/dashboard/validators"


def operator_config(path: Path) -> dict[str, str | None]:
    """Read fresh identity values without importing the runtime's cached Settings."""
    from dotenv import dotenv_values

    if path.is_file() and path.stat().st_size > 65536:
        raise OSError("Operator configuration exceeds its size limit")
    values = dotenv_values(path, interpolate=False) if path.is_file() else {}
    return {
        key: os.environ.get(key, values.get(key))
        for key in (
            "GRID_API_URL",
            "VALIDATOR_API_KEY",
            "VALIDATOR_PRIVATE_KEY",
            "VALIDATOR_WALLET",
        )
    }


def config_path() -> Path:
    configured = os.getenv("VALIDATOR_ENV")
    if configured:
        return Path(configured).expanduser().resolve()
    local = Path.cwd() / ".env"
    if local.is_file():
        return local
    if getattr(sys, "frozen", False):
        adjacent = Path(sys.executable).resolve().parent / ".env"
        if adjacent.is_file():
            return adjacent
    return Path.home() / ".aipg-validator" / ".env"


def command_prefix() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-m", "validator"]


def run_menu() -> int:
    from . import __release_tag__

    path = config_path()
    print(f"\nAI Power Grid Validator {__release_tag__}")
    print(f"Config: {path}")
    print("Preview: no validator rewards or stake required.")
    print("New operator? Choose 1 for automatic dedicated-account setup.")
    print("Never paste your everyday wallet's private key into this app.")
    actions = {
        "1": ["enroll"],
        "3": ["init"],
        "4": ["check", "--no-probe"],
        "5": ["run"],
        "6": ["self-test"],
        "7": ["prepare-wallet"],
        "8": ["app"],
    }
    while True:
        print("\n1. Set up a new dedicated validator account (recommended)")
        print("2. Open Console (existing-account management)")
        print("3. Configure an existing API key (advanced)")
        print("4. Check registration (no probe)")
        print("5. Run validator (leave this window open)")
        print("6. Offline decoder self-test")
        print("7. Prepare/show signing address only (advanced)")
        print("8. Open local operator app (browser controls)")
        print("0. Exit")
        try:
            choice = input("Choose an option: ").strip()
            if choice == "0":
                return 0
            if choice == "2":
                print(CONSOLE_URL)
                print(
                    "Linking requires proof of wallet ownership, not just an address."
                )
                print("If your prepared address is not available in your wallet, stop")
                print("and ask for enrollment help. Do not export a funded wallet key.")
                if not webbrowser.open(CONSOLE_URL):
                    print("Open the Console URL above in your browser.")
                continue
            action = actions.get(choice)
            if action is None:
                print("Choose one of the numbered options above.")
                continue
            if choice == "3":
                from dotenv import dotenv_values

                existing = dotenv_values(path) if path.exists() else {}
                if not existing.get("VALIDATOR_PRIVATE_KEY"):
                    print("New operators should use automatic setup, option 1.")
                    continue
            path.parent.mkdir(parents=True, exist_ok=True)
            env = os.environ.copy()
            env["VALIDATOR_ENV"] = str(path)
            # A separate process prevents init/check/run from reusing stale Settings.
            result = subprocess.run(command_prefix() + action, env=env, check=False)
            if result.returncode:
                print(
                    f"Command exited with code {result.returncode}; see the message above."
                )
                print("Do not create more API keys to troubleshoot a startup error.")
        except EOFError:
            return 0
        except KeyboardInterrupt:
            print("\nStopped. Choose 0 to close this window.")
        except (OSError, webbrowser.Error):
            print(
                "Could not start that action. Check access to the config folder and executable."
            )
