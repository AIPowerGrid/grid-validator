# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Operator-friendly CLI for configuring, testing, and running a validator.

    init   one-time interactive setup -> writes .env (chmod 600)
    check  verify config + grid + stake + scorecards, run ONE probe round, print results
    self-test  exercise packaged image/video decoders without contacting the Grid
    run    start the validator loop
    dashboard  serve a read-only local status page
    queue  inspect or explicitly retry local dead letters
    suspend  stop receiving new assignments with a signed control request
    rotate  bind the stable validator identity to a newly linked signing wallet
"""

import argparse
import asyncio
import getpass
import os
import stat
import sys
import tempfile
import time
import warnings
from pathlib import Path

from dotenv import dotenv_values


def _enabled(value: object) -> str:
    return "yes" if bool(value) else "no"


def _capability_lines(capabilities: dict) -> list[str]:
    features = capabilities.get("features") or {}
    mode = capabilities.get("mode") or "unavailable"
    version = capabilities.get("validator_api_version") or "unknown"
    available = capabilities.get("available")
    endpoint = "available" if available else "not deployed"
    lines = [
        f"INFO Validator API: {endpoint} (mode={mode}, version={version})",
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
        return [f"INFO Scorecards: unavailable ({note})"]

    items = scorecards.get("items") or []
    count = scorecards.get("count", len(items))
    window = scorecards.get("window_hours") or "?"
    economic_effect = scorecards.get("economic_effect") or "none"
    lines = [
        f"INFO Scorecards: {count} subject(s) over {window}h "
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


def _qualification_lines(registration: dict) -> list[str]:
    """Render the authenticated operator's safe qualification progress."""
    qualification = registration.get("operator_qualification")
    if not isinstance(qualification, dict):
        return []

    status = str(qualification.get("status") or "unreviewed")
    if status == "unreviewed":
        return [
            "INFO Operator qualification: unreviewed; share only this validator ID "
            "privately to request cohort review."
        ]
    if status == "candidate":
        elapsed_hours = float(qualification.get("elapsed_seconds") or 0) / 3600
        minimum_hours = float(qualification.get("minimum_seconds") or 0) / 3600
        coverage = float(qualification.get("sample_coverage") or 0)
        minimum_coverage = float(qualification.get("minimum_sample_coverage") or 0)
        samples = int(qualification.get("heartbeat_samples") or 0)
        expected = int(qualification.get("expected_samples") or 0)
        lines = [
            "INFO Operator qualification: candidate "
            f"{elapsed_hours:.1f}h/{minimum_hours:.1f}h; heartbeat coverage "
            f"{coverage:.0%}/{minimum_coverage:.0%} ({samples}/{expected} samples)."
        ]
        if qualification.get("time_ready") and qualification.get("coverage_ready"):
            lines.append(
                "INFO Qualification telemetry is ready; maintainer independence "
                "review is still required."
            )
        return lines
    if status == "verified":
        if qualification.get("independent_vote_eligible"):
            expires = qualification.get("expires_at") or "the recorded review expiry"
            return [f"OK Operator independence: verified through {expires}."]
        if not qualification.get("review_current"):
            return [
                "WARN Operator independence: review expired; maintainer renewal required."
            ]
        return [
            "WARN Operator independence: review is current but the validator heartbeat "
            "is not fresh."
        ]
    if status == "rejected":
        return [
            "WARN Operator qualification: rejected; contact the maintainer before running."
        ]
    return [f"WARN Operator qualification: unknown status {status!r}."]


def _env_path(args=None) -> Path:
    configured = getattr(args, "env", None) or os.getenv("VALIDATOR_ENV")
    return Path(configured).expanduser() if configured else Path.cwd() / ".env"


def _protect_windows_file(path: Path) -> None:
    """Replace inherited permissions with a protected, owner-only Windows DACL."""
    import ctypes
    from ctypes import wintypes

    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    convert = advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW
    convert.argtypes = [wintypes.LPCWSTR, wintypes.DWORD,
                        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.DWORD)]
    convert.restype = wintypes.BOOL
    apply = advapi.SetFileSecurityW
    apply.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p]
    apply.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    descriptor = ctypes.c_void_p()
    # Protected DACL, full file access for the owner only (Owner Rights SID).
    if not convert("D:P(A;;FA;;;OW)", 1, ctypes.byref(descriptor), None):
        raise OSError("Could not create private Windows file permissions")
    try:
        if not apply(str(path), 0x80000004, descriptor):
            raise OSError("Could not protect identity file; use a private NTFS folder")
    finally:
        kernel.LocalFree(descriptor)


def _write_private_env(path: Path, lines: list[str]) -> None:
    """Atomically write validator configuration without a world-readable window."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        if sys.platform == "win32":
            _protect_windows_file(Path(temporary))
        else:
            os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        if sys.platform != "win32":
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _upsert_env(path: Path, updates: dict[str, str], *, fresh_lines: list[str]) -> None:
    if path.exists():
        source = path.read_text(encoding="utf-8").splitlines()
    else:
        source = list(fresh_lines)
    pending = dict(updates)
    output: list[str] = []
    for line in source:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key not in updates:
            output.append(line)
            continue
        if key in pending:
            output.append(f"{key}={pending.pop(key)}")
    output.extend(f"{key}={value}" for key, value in pending.items())
    _write_private_env(path, output)


def _cmd_prepare_wallet(args) -> int:
    """Create the validator signing identity before Console enrollment."""
    from eth_account import Account

    from .config import normalize_wallet, wallet_from_private_key

    env_path = _env_path(args)
    existing = dotenv_values(env_path) if env_path.exists() else {}
    private_key = str(existing.get("VALIDATOR_PRIVATE_KEY") or "").strip()
    configured_wallet = str(existing.get("VALIDATOR_WALLET") or "").strip()

    if private_key:
        try:
            wallet = wallet_from_private_key(private_key)
            if configured_wallet and normalize_wallet(configured_wallet) != wallet:
                raise RuntimeError("VALIDATOR_WALLET does not match VALIDATOR_PRIVATE_KEY.")
        except RuntimeError as exc:
            print(f"ERROR Existing validator identity is invalid: {exc}")
            return 1
        if sys.platform == "win32":
            _protect_windows_file(env_path)
        else:
            os.chmod(env_path, stat.S_IRUSR | stat.S_IWUSR)
        print(f"OK Validator signing wallet already prepared: {wallet}")
        print(f"   Identity file: {env_path} (owner-only permissions)")
        return 0

    account = Account.create()
    wallet = account.address.lower()
    private_key = "0x" + bytes(account.key).hex()
    fresh = [
        "GRID_API_URL=https://api.aipowergrid.io",
        "VALIDATOR_API_KEY=",
        f"VALIDATOR_WALLET={wallet}",
        f"VALIDATOR_PRIVATE_KEY={private_key}",
        "VALIDATOR_REQUIRE_STAKE=false",
        "BASE_RPC_URL=https://mainnet.base.org",
        "AIPG_TOKEN_ADDR=0xa1c0deCaFE3E9Bf06A5F29B7015CD373a9854608",
        "VALIDATOR_STAKING_ADDR=",
        "VALIDATOR_MIN_STAKE=50000",
        "PROBE_INTERVAL_S=60",
        "DASHBOARD_HOST=127.0.0.1",
        "DASHBOARD_PORT=8790",
    ]
    _upsert_env(
        env_path,
        {
            "VALIDATOR_WALLET": wallet,
            "VALIDATOR_PRIVATE_KEY": private_key,
        },
        fresh_lines=fresh,
    )
    print(f"OK Created validator signing wallet: {wallet}")
    print(f"   Private key saved only in {env_path} (owner-only permissions); it was not printed.")
    print("   Next: link this public address in the Console, create a validator key,")
    print("   then run `aipg-validator init` to complete setup.")
    return 0


def _cmd_init(args) -> int:
    """Interactive .env creation — no prior knowledge required."""
    from .config import normalize_grid_url, normalize_wallet, wallet_from_private_key

    env_path = _env_path(args)
    existing = dotenv_values(env_path) if env_path.exists() else {}
    existing_pk = str(existing.get("VALIDATOR_PRIVATE_KEY") or "").strip()
    existing_wallet = str(existing.get("VALIDATOR_WALLET") or "").strip()
    try:
        if (
            env_path.exists()
            and not existing_pk
            and input(f"{env_path} exists. Overwrite? [y/N] ").lower() != "y"
        ):
            print("Keeping existing .env.")
            return 0

        print("\nAIPG Validator setup - press Enter to accept [defaults].\n")
        grid_default = str(existing.get("GRID_API_URL") or "https://api.aipowergrid.io").strip()
        grid = input(f"Grid API URL [{grid_default}]: ").strip() or grid_default
        try:
            grid = normalize_grid_url(grid)
        except RuntimeError as exc:
            print(f"ERROR {exc}")
            return 1
        existing_api_key = str(existing.get("VALIDATOR_API_KEY") or "").strip()
        if existing_api_key:
            keep = input("Keep the existing validator API key? [Y/n] ").strip().lower()
            api_key = existing_api_key if keep not in {"n", "no"} else ""
        else:
            api_key = ""
        if not api_key:
            with warnings.catch_warnings():
                warnings.simplefilter("error", getpass.GetPassWarning)
                api_key = getpass.getpass("Validator grid API key (hidden, required): ").strip()
        if not api_key:
            print("ERROR Validator grid API key is required.")
            return 1
        if existing_pk:
            pk = existing_pk
            try:
                derived_wallet = wallet_from_private_key(pk)
                if existing_wallet and normalize_wallet(existing_wallet) != derived_wallet:
                    raise RuntimeError("VALIDATOR_WALLET does not match VALIDATOR_PRIVATE_KEY.")
            except RuntimeError as exc:
                print(f"ERROR Existing validator identity is invalid: {exc}")
                return 1
            wallet = derived_wallet
            print(f"Using prepared validator wallet: {wallet}")
        else:
            wallet = input(
                "Validator wallet address 0x... (must be linked to your Grid account): "
            ).strip()
            if wallet:
                try:
                    wallet = normalize_wallet(wallet)
                except RuntimeError as exc:
                    print(f"ERROR {exc}")
                    return 1
            with warnings.catch_warnings():
                warnings.simplefilter("error", getpass.GetPassWarning)
                pk = getpass.getpass("Dedicated validator private key (kept local): ").strip()
            if not pk:
                print("ERROR Validator private key is required for registration and evidence signing.")
                return 1
            try:
                derived_wallet = wallet_from_private_key(pk)
            except RuntimeError as exc:
                print(f"ERROR {exc}")
                return 1
            if wallet and wallet.lower() != derived_wallet:
                print("ERROR Validator wallet does not match the private key.")
                print(f"   Configured wallet: {wallet}")
                print(f"   Key wallet:        {derived_wallet}")
                return 1
            if not wallet:
                wallet = derived_wallet
                print(f"Derived validator wallet: {wallet}")
        staked_default = str(existing.get("VALIDATOR_REQUIRE_STAKE") or "false").lower() in {
            "1", "true", "yes", "y", "on"
        }
        stake_prompt = "[Y/n]" if staked_default else "[y/N]"
        stake_answer = input(f"Run with on-chain stake required? {stake_prompt} ").strip().lower()
        staked = staked_default if not stake_answer else stake_answer in {"y", "yes"}
    except (EOFError, getpass.GetPassWarning):
        print("ERROR Interactive setup requires a terminal.")
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
    _upsert_env(
        env_path,
        {line.split("=", 1)[0]: line.split("=", 1)[1] for line in lines},
        fresh_lines=lines,
    )
    print(f"\nOK Wrote {env_path} (owner-only permissions). Next: `aipg-validator check --no-probe`")
    return 0


def _cmd_check(args) -> int:
    """One-shot health check so an operator knows it works before running 24/7."""
    from . import attest, staking
    from .config import Settings
    from .grid_client import GridClient
    from .main import probe_round

    try:
        Settings.validate()
    except RuntimeError as e:
        print(f"ERROR Config: {e}")
        return 1
    print(f"OK Config -> grid {Settings.GRID_API_URL}")

    if Settings.REQUIRE_STAKE:
        try:
            staking.assert_eligible()
            print("OK Stake: eligible")
        except (staking.NotDeployed, RuntimeError) as e:
            print(f"ERROR Stake: {e}")
            return 1
    else:
        print("INFO Stake: gate disabled (V0 preview)")

    local_capabilities = attest.runtime_capabilities()
    print(f"OK Local scorers: {', '.join(local_capabilities)}")

    async def _go():
        grid = GridClient()
        try:
            try:
                registration = await grid.register_validator(
                    attest.sign(attest.build_registration(int(time.time())))
                )
            except Exception as exc:
                print(f"ERROR Validator registration failed: {exc}")
                return False
            print(
                f"OK Validator registered: {registration.get('validator_id', 'unknown')} "
                f"({registration.get('status', 'active')})"
            )
            for line in _qualification_lines(registration):
                print(line)
            capabilities = await grid.validator_capabilities()
            for line in _capability_lines(capabilities):
                print(line)
            scorecards = await grid.validator_scorecards(limit=3, since_hours=24)
            for line in _scorecard_lines(scorecards):
                print(line)
            print("OK Grid reachable - validator registration and API available")
            if args.no_probe:
                print("INFO Probe skipped (--no-probe).")
                return True
            print("Running one probe round...\n")
            try:
                attempted = await probe_round(grid, 0)
            except Exception as exc:
                print(f"ERROR Probe round failed: {exc}")
                return False
            if attempted <= 0:
                print("ERROR No Grid assignment was available; no canary was submitted.")
                return False
            print(f"OK Probe round submitted {attempted} canary job(s).")
            return True
        finally:
            await grid.aclose()

    if not asyncio.run(_go()):
        return 1
    print("\nOK check complete.")
    return 0


def _cmd_self_test(_args) -> int:
    """Prove packaged media dependencies and decoder isolation work locally."""
    from .self_test import run_media_decoder_self_test

    try:
        results = run_media_decoder_self_test()
    except Exception as exc:  # noqa: BLE001 - diagnostics must report native failures cleanly
        print(f"ERROR Media self-test failed: {type(exc).__name__}: {exc}")
        return 1
    print(f"OK Image decoder: {results['image']}")
    print(f"OK Video decoder: {results['video']}")
    print("OK Media self-test complete (offline; no assignment or economic effect).")
    return 0


def _cmd_run(args) -> int:
    from .main import run
    try:
        asyncio.run(run())
    except RuntimeError as exc:
        print(f"ERROR Startup: {exc}")
        return 1
    return 0


def _cmd_dashboard(args) -> int:
    from .dashboard import run_dashboard

    try:
        run_dashboard(host=args.host, port=args.port)
    except (OSError, RuntimeError) as exc:
        print(f"ERROR Dashboard: {exc}")
        return 1
    return 0


def _cmd_lifecycle(args) -> int:
    from . import attest
    from .config import Settings
    from .grid_client import GridClient

    try:
        Settings.validate()
    except RuntimeError as exc:
        print(f"ERROR Config: {exc}")
        return 1

    async def _go() -> bool:
        grid = GridClient()
        try:
            registration = await grid.validator_registration()
            if not registration.get("available"):
                print("ERROR Validator registration is unavailable for this account key.")
                return False
            validator_id = str(registration.get("validator_id") or "")
            current_wallet = str(registration.get("signing_wallet") or "").lower()
            if not validator_id or not current_wallet:
                print("ERROR Core returned an incomplete validator registration.")
                return False

            if args.cmd == "suspend":
                if registration.get("status") == "suspended":
                    print(f"OK Validator already suspended: {validator_id}")
                    return True
                envelope = attest.sign(attest.build_suspension(validator_id, int(time.time())))
                result = await grid.suspend_validator(envelope)
                print(f"OK Validator suspended: {result.get('validator_id', validator_id)}")
                print("   No new assignments will be issued. Run `aipg-validator check --no-probe` to resume.")
                return True

            replacement_wallet = Settings.VALIDATOR_WALLET.lower()
            if current_wallet == replacement_wallet:
                print(f"OK Validator already uses configured wallet: {validator_id}")
                return True
            envelope = attest.sign(
                attest.build_rotation(validator_id, current_wallet, int(time.time()))
            )
            result = await grid.rotate_validator(envelope)
            print(
                f"OK Validator wallet rotated: {result.get('validator_id', validator_id)} "
                f"({result.get('status', 'active')})"
            )
            print("   Revoke every previous validator API key in the Console after this node checks healthy.")
            print("   Assignments issued to the previous wallet remain invalid and expire normally.")
            return True
        except Exception as exc:
            print(f"ERROR Validator {args.cmd} failed: {exc}")
            return False
        finally:
            await grid.aclose()

    return 0 if asyncio.run(_go()) else 1


def _cmd_queue(args) -> int:
    from .config import Settings
    from .outbox import AttestationOutbox

    state = AttestationOutbox(Settings.STATE_DB_PATH)
    if args.queue_cmd == "status":
        attestations = state.counts()
        assignments = state.assignment_counts()
        print(
            "Attestations: "
            f"pending={attestations['pending']} dead={attestations['dead']}"
        )
        print(
            "Assignments: "
            f"pending={assignments['pending']} dead={assignments['dead']}"
        )
        dead = state.dead_letters()
        for item in dead["attestations"]:
            print(
                "   dead attestation "
                f"{item['id'][:12]} assignment={item['assignment_id'][:24]} "
                f"attempts={item['attempts']} age={item['age_seconds']}s"
            )
        for item in dead["assignments"]:
            print(
                "   dead assignment "
                f"{item['assignment_id'][:24]} attempts={item['attempts']} "
                f"age={item['age_seconds']}s"
            )
        return 0
    revived = state.retry_dead(args.kind)
    print(
        "Revived dead letters: "
        f"attestations={revived['attestations']} assignments={revived['assignments']}"
    )
    return 0


def main(argv=None) -> int:
    from . import __release_tag__

    p = argparse.ArgumentParser(prog="aipg-validator", description="AIPG validator node")
    p.add_argument("--version", action="version", version=f"%(prog)s {__release_tag__}")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("menu", help="interactive first-run and operator menu")
    prepare = sub.add_parser(
        "prepare-wallet",
        help="create a local signing wallet before Console enrollment",
    )
    prepare.add_argument("--env", default=None, help="identity/config file (default: .env)")
    sub.add_parser("init", help="interactive setup -> .env")
    check = sub.add_parser("check", help="verify config/grid/stake/scorecards + one probe round")
    check.add_argument(
        "--no-probe",
        action="store_true",
        help="verify config/Grid/capabilities/scorecards without submitting a canary job",
    )
    sub.add_parser(
        "self-test",
        help="exercise packaged image/video decoders locally without Grid traffic",
    )
    sub.add_parser("run", help="start the validator loop")
    sub.add_parser("suspend", help="stop new assignments with a signed request")
    sub.add_parser("rotate", help="rotate to the configured, newly linked signing wallet")
    dashboard = sub.add_parser("dashboard", help="serve local read-only dashboard")
    dashboard.add_argument("--host", default=None, help="bind host (default: DASHBOARD_HOST)")
    dashboard.add_argument("--port", default=None, type=int, help="bind port (default: DASHBOARD_PORT)")
    queue = sub.add_parser("queue", help="inspect or recover local validator work")
    queue_sub = queue.add_subparsers(dest="queue_cmd", required=True)
    queue_sub.add_parser("status", help="show pending and dead-letter counts")
    retry = queue_sub.add_parser("retry-dead", help="retry reviewed dead letters")
    retry.add_argument(
        "--kind",
        choices=("all", "attestations", "assignments"),
        default="all",
        help="dead-letter class to retry (default: all)",
    )
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        if sys.stdin is not None and sys.stdin.isatty():
            argv = ["menu"]
        else:
            p.print_help()
            return 0
    args = p.parse_args(argv)
    if args.cmd == "menu":
        from .launcher import run_menu

        return run_menu()
    handler = {
        "init": _cmd_init,
        "prepare-wallet": _cmd_prepare_wallet,
        "check": _cmd_check,
        "self-test": _cmd_self_test,
        "run": _cmd_run,
        "dashboard": _cmd_dashboard,
        "queue": _cmd_queue,
        "suspend": _cmd_lifecycle,
        "rotate": _cmd_lifecycle,
    }[args.cmd]
    try:
        return handler(args)
    except OSError:
        print("ERROR Could not access or protect the local config file. Check folder permissions.")
        return 1
    except KeyboardInterrupt:
        print("\nStopped.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
