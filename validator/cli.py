# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Operator-friendly CLI:  aipg-validator <init | check | run | dashboard>

    init   one-time interactive setup → writes .env (chmod 600)
    check  verify config + grid + stake + scorecards, run ONE probe round, print results
    run    start the validator loop
    dashboard  serve a read-only local status page
"""

import argparse
import asyncio
import getpass
import os
import stat
import sys
import time
from pathlib import Path


def _enabled(value: object) -> str:
    return "yes" if bool(value) else "no"


def _capability_lines(capabilities: dict) -> list[str]:
    features = capabilities.get("features") or {}
    mode = capabilities.get("mode") or "unavailable"
    version = capabilities.get("validator_api_version") or "unknown"
    available = capabilities.get("available")
    endpoint = "available" if available else "not deployed"
    lines = [
        f"ℹ️  Validator API: {endpoint} (mode={mode}, version={version})",
        f"   attest={_enabled(features.get('attest'))} "
        f"inventory={_enabled(features.get('worker_inventory'))} "
        f"targeted={_enabled(features.get('targeted_probe'))} "
        f"assignments={_enabled(features.get('assignments'))} "
        f"rewards={_enabled(features.get('validator_rewards'))} "
        f"stake_required={_enabled(features.get('staking_required'))}",
    ]
    if not capabilities.get("targeted_probe_enabled"):
        lines.append("   probing mode: unavailable (no assignment means no probe)")
    else:
        lines.append("   probing mode: targeted worker probes enabled")
    if capabilities.get("economic_effect") and capabilities.get("economic_effect") != "none":
        lines.append(f"   economic effect: {capabilities['economic_effect']}")
    if capabilities.get("error"):
        lines.append(f"   capability note: {capabilities['error']}")
    return lines


def _scorecard_lines(scorecards: dict, *, max_items: int = 3) -> list[str]:
    """Human-readable summary of aggregate validator evidence.

    Scorecards are informational in V0. Keep the CLI language explicit so an
    operator does not read a failed aggregate as a strike or slash.
    """
    if not scorecards.get("available"):
        note = scorecards.get("error") or "scorecards endpoint not deployed"
        return [f"ℹ️  Scorecards: unavailable ({note})"]

    items = scorecards.get("items") or []
    count = scorecards.get("count", len(items))
    window = scorecards.get("window_hours") or "?"
    economic_effect = scorecards.get("economic_effect") or "none"
    lines = [
        f"ℹ️  Scorecards: {count} subject(s) over {window}h "
        f"(economic_effect={economic_effect})"
    ]
    if not items:
        lines.append("   no validator evidence yet")
        return lines

    for item in items[:max_items]:
        subject = item.get("subject_id") or item.get("worker_id") or item.get("model") or "unknown"
        model = item.get("model") or "unknown-model"
        total = item.get("total", item.get("observations", 0))
        healthy = item.get("healthy", 0)
        slow = item.get("slow", 0)
        failed = item.get("failed", 0)
        latency = item.get("avg_latency_ms")
        latency_part = f", avg_latency={int(latency)}ms" if isinstance(latency, (int, float)) else ""
        lines.append(
            f"   {subject} / {model}: total={total} "
            f"healthy={healthy} slow={slow} failed={failed}{latency_part}"
        )
    if len(items) > max_items:
        lines.append(f"   ... {len(items) - max_items} more subject(s)")
    return lines


def _cmd_init(args) -> int:
    """Interactive .env creation — no prior knowledge required."""
    from .config import normalize_grid_url, normalize_wallet, wallet_from_private_key

    env_path = Path.cwd() / ".env"
    try:
        if env_path.exists() and input(f"{env_path} exists. Overwrite? [y/N] ").lower() != "y":
            print("Keeping existing .env.")
            return 0

        print("\nAIPG Validator setup — press Enter to accept [defaults].\n")
        grid = input("Grid API URL [https://api.aipowergrid.io]: ").strip() or "https://api.aipowergrid.io"
        try:
            grid = normalize_grid_url(grid)
        except RuntimeError as exc:
            print(f"❌ {exc}")
            return 1
        api_key = input("Validator grid API key (required): ").strip()
        if not api_key:
            print("❌ Validator grid API key is required.")
            return 1
        wallet = input("Validator wallet address 0x… (must be linked to your Grid account): ").strip()
        if wallet:
            try:
                wallet = normalize_wallet(wallet)
            except RuntimeError as exc:
                print(f"❌ {exc}")
                return 1
        staked = input("Run with on-chain stake required? [y/N] ").lower() == "y"
        pk = getpass.getpass("Validator private key (kept local, chmod 600): ").strip()
        if not pk:
            print("❌ Validator private key is required for registration and evidence signing.")
            return 1
        try:
            derived_wallet = wallet_from_private_key(pk)
        except RuntimeError as exc:
            print(f"❌ {exc}")
            return 1
        if wallet and wallet.lower() != derived_wallet:
            print("❌ Validator wallet does not match the private key.")
            print(f"   Configured wallet: {wallet}")
            print(f"   Key wallet:        {derived_wallet}")
            return 1
        if not wallet:
            wallet = derived_wallet
            print(f"Derived validator wallet: {wallet}")
    except EOFError:
        print("❌ Interactive setup requires a terminal.")
        print("   Run `aipg-validator init` from a shell, or create `.env` from `.env.template`.")
        return 1

    lines = [
        f"GRID_API_URL={grid}",
        f"VALIDATOR_API_KEY={api_key}",
        f"VALIDATOR_WALLET={wallet.lower() if wallet else ''}",
        f"VALIDATOR_PRIVATE_KEY={pk}",
        f"VALIDATOR_REQUIRE_STAKE={'true' if staked else 'false'}",
        "BASE_RPC_URL=https://mainnet.base.org",
        "AIPG_TOKEN_ADDR=0xa1c0deCaFE3E9Bf06A5F29B7015CD373a9854608",
        "VALIDATOR_STAKING_ADDR=",
        "VALIDATOR_MIN_STAKE=50000",
        "PROBE_INTERVAL_S=60",
        "DASHBOARD_HOST=127.0.0.1",
        "DASHBOARD_PORT=8790",
    ]
    env_path.write_text("\n".join(lines) + "\n")
    os.chmod(env_path, stat.S_IRUSR | stat.S_IWUSR)  # 600 — protects the private key
    print(f"\n✅ Wrote {env_path} (chmod 600). Next: `aipg-validator check`")
    return 0


def _cmd_check(args) -> int:
    """One-shot health check so an operator knows it works before running 24/7."""
    from . import staking
    from .config import Settings
    from .grid_client import GridClient
    from .main import probe_round

    try:
        Settings.validate()
    except RuntimeError as e:
        print(f"❌ Config: {e}")
        return 1
    print(f"✅ Config OK → grid {Settings.GRID_API_URL}")

    if Settings.REQUIRE_STAKE:
        try:
            staking.assert_eligible()
            print("✅ Stake: eligible")
        except (staking.NotDeployed, RuntimeError) as e:
            print(f"❌ Stake: {e}")
            return 1
    else:
        print("ℹ️  Stake: gate disabled (V0 preview)")

    async def _go():
        grid = GridClient()
        try:
            from . import attest

            try:
                registration = await grid.register_validator(
                    attest.sign(attest.build_registration(int(time.time())))
                )
            except Exception as exc:
                print(f"❌ Validator registration failed: {exc}")
                return False
            print(
                f"✅ Validator registered: {registration.get('validator_id', 'unknown')} "
                f"({registration.get('status', 'active')})"
            )
            capabilities = await grid.validator_capabilities()
            for line in _capability_lines(capabilities):
                print(line)
            scorecards = await grid.validator_scorecards(limit=3, since_hours=24)
            for line in _scorecard_lines(scorecards):
                print(line)
            print("✅ Grid reachable — validator registration and API available")
            if args.no_probe:
                print("ℹ️  Probe skipped (--no-probe).")
                return True
            print("Running one probe round...\n")
            try:
                attempted = await probe_round(grid, 0)
            except Exception as exc:
                print(f"❌ Probe round failed: {exc}")
                return False
            if attempted <= 0:
                print("❌ No Grid assignment was available; no canary was submitted.")
                return False
            print(f"✅ Probe round submitted {attempted} canary job(s).")
            return True
        finally:
            await grid.aclose()

    if not asyncio.run(_go()):
        return 1
    print("\n✅ check complete.")
    return 0


def _cmd_run(args) -> int:
    from .main import run
    try:
        asyncio.run(run())
    except RuntimeError as exc:
        print(f"❌ Startup: {exc}")
        return 1
    return 0


def _cmd_dashboard(args) -> int:
    from .dashboard import run_dashboard

    try:
        run_dashboard(host=args.host, port=args.port)
    except (OSError, RuntimeError) as exc:
        print(f"❌ Dashboard: {exc}")
        return 1
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="aipg-validator", description="AIPG validator node")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="interactive setup → .env")
    check = sub.add_parser("check", help="verify config/grid/stake/scorecards + one probe round")
    check.add_argument(
        "--no-probe",
        action="store_true",
        help="verify config/Grid/capabilities/scorecards without submitting a canary job",
    )
    sub.add_parser("run", help="start the validator loop")
    dashboard = sub.add_parser("dashboard", help="serve local read-only dashboard")
    dashboard.add_argument("--host", default=None, help="bind host (default: DASHBOARD_HOST)")
    dashboard.add_argument("--port", default=None, type=int, help="bind port (default: DASHBOARD_PORT)")
    args = p.parse_args(argv)
    return {
        "init": _cmd_init,
        "check": _cmd_check,
        "run": _cmd_run,
        "dashboard": _cmd_dashboard,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
