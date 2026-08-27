# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Maintainer-only native pairing qualification; never upload the private workspace."""

import argparse
import getpass
import hashlib
import http.client
import importlib.util
import json
import os
import platform
import re
import secrets
import stat
import sys
import time
import zipfile
from pathlib import Path

import httpx
from dotenv import dotenv_values

from validator.account_pairing import CODE, CONSOLE_URL, PAIR_ID, _unique_object
from validator.cli import _write_private_env

spec = importlib.util.spec_from_file_location(
    "native_canary", Path(__file__).with_name("native-live-canary.py")
)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
require = native.require


def read_json(path: Path, *, private: bool = False) -> dict:
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_size <= 16384, "unsafe_json_file")
    if private and os.name != "nt":
        require(
            info.st_uid == os.getuid() and not info.st_mode & 0o077,
            "review_file_not_private",
        )
    with path.open("rb") as source:
        body = source.read(16385)
    require(len(body) <= 16384, "unsafe_json_file")
    data = json.loads(body, object_pairs_hook=_unique_object)
    require(isinstance(data, dict), "invalid_json_object")
    return data


def private_json(path: Path, value: dict) -> None:
    _write_private_env(path, [json.dumps(value, separators=(",", ":"))])


def platform_name() -> str:
    key = (sys.platform, platform.machine().lower())
    supported = {
        ("win32", "amd64"): "windows-x64",
        ("linux", "x86_64"): "linux-x64",
        ("linux", "aarch64"): "linux-arm64",
    }
    require(key in supported, "windows_or_linux_required")
    return supported[key]


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def verify_candidate(root: Path, commit: str, target: str) -> tuple[Path, dict]:
    manifest = read_json(root / "validator-release.json")
    require(
        manifest.get("schema") == "aipg-validator-release-v1"
        and manifest.get("commit") == commit
        and manifest.get("release_class") == "build"
        and manifest.get("tag") == ""
        and re.fullmatch(r"\d+\.\d+\.\d+", manifest.get("version", "")),
        "candidate_identity_mismatch",
    )
    name = "aipg-validator-" + target + ".zip"
    entries = [row for row in manifest.get("assets", []) if row.get("name") == name]
    require(len(entries) == 1, "candidate_manifest_mismatch")
    archive_path = root / name
    require(
        archive_path.is_file()
        and not archive_path.is_symlink()
        and 0 < archive_path.stat().st_size <= 512 * 1024 * 1024
        and archive_path.stat().st_size == entries[0].get("bytes")
        and digest(archive_path) == entries[0].get("sha256"),
        "candidate_archive_mismatch",
    )
    executable = "aipg-validator.exe" if target == "windows-x64" else "aipg-validator"
    binary = root / executable
    require(not binary.exists(), "candidate_already_extracted")
    with zipfile.ZipFile(archive_path) as archive:
        files = archive.infolist()
        require(
            len(files) == 1
            and files[0].filename == executable
            and not files[0].is_dir()
            and not files[0].flag_bits & 1
            and stat.S_IFMT(files[0].external_attr >> 16) in (0, stat.S_IFREG)
            and 0 < files[0].file_size < 512 * 1024 * 1024,
            "unsafe_candidate_archive",
        )
        with binary.open("xb") as output, archive.open(files[0]) as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                output.write(chunk)
    if os.name != "nt":
        binary.chmod(0o700)
    return binary, {
        "source_commit": commit,
        "binary_version": "v" + manifest["version"] + "-dev",
        "archive_sha256": entries[0]["sha256"],
        "release_provenance": False,
        "artifact_kind": "reviewed_ci_build_only",
    }


def fetch_candidate(
    root: Path, run_id: str, commit: str, target: str
) -> tuple[Path, dict]:
    require(
        re.fullmatch(r"[0-9]{1,20}", run_id) and re.fullmatch(r"[a-f0-9]{40}", commit),
        "invalid_candidate_reference",
    )
    run = json.loads(
        native.command(
            [
                "gh",
                "api",
                f"repos/{native.REPO}/actions/runs/{run_id}",
            ]
        )
    )
    require(
        run.get("head_sha") == commit
        and run.get("head_branch") == "master"
        and run.get("event") in {"push", "workflow_dispatch"}
        and run.get("path") == ".github/workflows/release-binaries.yml"
        and run.get("conclusion") == "success"
        and run.get("head_repository", {}).get("full_name") == native.REPO,
        "candidate_run_not_qualified",
    )
    require(not root.exists(), "candidate_directory_exists")
    root.mkdir()
    native.command(
        [
            "gh",
            "run",
            "download",
            run_id,
            "--repo",
            native.REPO,
            "--name",
            "aipg-validator-release-payload",
            "--dir",
            str(root),
        ],
        timeout=300,
    )
    binary, metadata = verify_candidate(root, commit, target)
    return binary, {**metadata, "build_run": run_id}


def pairing(app: native.App, action: str, **fields) -> dict:
    status, body = app.request("/pairing", action, fields=fields, timeout=45)
    require(status == 200, "pairing_local_request_rejected")
    value = json.loads(body)
    require(isinstance(value, dict), "pairing_local_response_invalid")
    return value


def poll(
    app: native.App, predicate, deadline: float, *, allow_unavailable=False
) -> dict:
    while time.monotonic() < deadline:
        value = pairing(app, "refresh")
        if predicate(value):
            return value
        require(
            value.get("status") != "error"
            or (allow_unavailable and value.get("error") == "unavailable"),
            "pairing_failed",
        )
        time.sleep(5)  # Leave room for consent/removal under Core's 30/minute reads.
    raise native.Failed("pairing_wait_timed_out")


def request_review(workspace: Path, value: dict, phase: str) -> str:
    pair_id = value.get("pairing_id", "")
    require(
        PAIR_ID.fullmatch(pair_id)
        and value.get("approval_url") == CONSOLE_URL + "/" + pair_id,
        "invalid_review_destination",
    )
    ticket = secrets.token_hex(16)
    private_json(
        workspace / "review-request.json",
        {
            "phase": phase,
            "ticket": ticket,
            "validator_id": value["validator_id"],
            "pairing_id": pair_id,
            "approval_url": value["approval_url"],
        },
    )
    return ticket


def confirmed_review(workspace: Path, value: dict, ticket: str) -> bool:
    path = workspace / "review-response.json"
    if not path.exists():
        return False
    response = read_json(path, private=True)
    require(
        set(response) == {"ticket", "pairing_id", "comparison_code"},
        "invalid_review_response",
    )
    if response["ticket"] != ticket:
        return False  # A prior phase's consent is not consent for this request.
    require(
        response["pairing_id"] == value.get("pairing_id")
        and CODE.fullmatch(response.get("comparison_code", ""))
        and secrets.compare_digest(
            response["comparison_code"], value.get("comparison_code", "")
        ),
        "console_code_does_not_match",
    )
    return True


def review(workspace: Path) -> int:
    """Maintainer enters the Console code locally; never as a command-line argument."""
    require(sys.stdin.isatty(), "interactive_review_required")
    request = read_json(workspace / "review-request.json", private=True)
    require(
        request.get("phase") in {"node-removal", "owner-removal"}
        and PAIR_ID.fullmatch(request.get("pairing_id", ""))
        and re.fullmatch(r"[a-f0-9]{32}", request.get("ticket", "")),
        "invalid_review_request",
    )
    code = (
        getpass.getpass("Code shown by the approved Console request (hidden): ")
        .strip()
        .upper()
    )
    require(CODE.fullmatch(code), "invalid_comparison_code")
    private_json(
        workspace / "review-response.json",
        {
            "ticket": request["ticket"],
            "pairing_id": request["pairing_id"],
            "comparison_code": code,
        },
    )
    print('{"check":"local_review_recorded"}')
    return 0


def discard_confirmation_response(app: native.App, value: dict) -> None:
    body = json.dumps(
        {
            "action": "confirm",
            **{
                k: value[k]
                for k in (
                    "pairing_id",
                    "review_hash",
                    "comparison_code",
                )
            },
        }
    )
    connection = http.client.HTTPConnection("127.0.0.1", app.port, timeout=45)
    try:
        connection.request(
            "POST",
            "/pairing",
            body,
            {
                "Authorization": "Bearer " + app.token,
                "Origin": f"http://127.0.0.1:{app.port}",
                "Content-Type": "application/json",
            },
        )
        # Core may already have committed. Deliberately discard the local result;
        # the next app must discover the association without another signature.
        connection.getresponse().close()
    finally:
        connection.close()


def clean_pairing(binary: Path, config: Path, expected_fingerprint: bytes) -> None:
    require(
        native.fingerprint(config) == expected_fingerprint, "cleanup_config_changed"
    )
    with native.opened_app(binary, config) as app:
        value = pairing(app, "refresh")
        if value.get("status") == "linked":
            value = pairing(
                app, "unlink", **{k: value[k] for k in ("pairing_id", "review_hash")}
            )
        elif value.get("status") in {"pending", "approved"}:
            value = pairing(app, "cancel", pairing_id=value["pairing_id"])
        require(
            value.get("status") in {"none", "cancelled", "expired"},
            "pairing_cleanup_unproven",
        )


def run(args) -> int:
    target = platform_name()
    workspace, report_path = args.workspace.resolve(), args.report.resolve()
    require(
        not workspace.exists() and not report_path.exists(), "existing_canary_state"
    )
    require(
        not report_path.is_relative_to(workspace), "public_report_inside_private_state"
    )
    workspace.mkdir(parents=True, mode=0o700)
    config = workspace / "node.env"
    report = {
        "schema": "aipg.validator.native-pairing-canary.v1",
        "first_party": True,
        "platform": target,
        "checks": [],
        "passed": False,
    }
    binary = None
    touched_pairing = False
    before = None
    expected_wallet = None

    def emit(check: str) -> None:
        report["checks"].append(check)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps({"check": check, "validator_id": report.get("validator_id")}),
            flush=True,
        )

    try:
        binary, metadata = fetch_candidate(
            workspace / "artifacts", args.run_id, args.commit, target
        )
        report.update(metadata)
        require(
            native.command(
                [str(binary), "--version"], env=native.binary_env(config)
            ).strip()
            == "aipg-validator " + metadata["binary_version"],
            "binary_version_mismatch",
        )
        with httpx.Client(
            timeout=15, trust_env=False, follow_redirects=False
        ) as client:
            caps = native.core_json(client, "GET", "/v1/validator/capabilities")
            health = native.core_json(client, "GET", "/health")
            require(
                health.get("build_commit") == args.core_commit,
                "unexpected_core_revision",
            )
            require(
                caps.get("economic_effect") == "none"
                and caps.get("probe_policy", {}).get("quality_eligible") is False
                and all(
                    caps.get("features", {}).get(k) is False
                    for k in (
                        "account_pairing",
                        "validator_rewards",
                        "staking_required",
                        "image_fidelity",
                        "video_validation",
                    )
                ),
                "scoped_unpaid_pilot_required",
            )
        report["core_commit"] = args.core_commit
        emit("reviewed_candidate_and_dark_core_verified")
        native.command(
            [str(binary), "enroll"],
            env=native.binary_env(config),
            cwd=workspace,
            input="n\n",
        )
        require(not config.exists(), "cancel_created_identity")
        deadline = time.monotonic() + args.minutes * 60
        with native.opened_app(binary, config) as app:
            require(
                app.request(auth=False)[0] == 401 and not config.exists(),
                "implicit_or_unprotected_enrollment",
            )
            app.action("enroll")
            app.wait(lambda s: s["phase"] == "enrolled" and not s["running"], 120)
            before = native.fingerprint(config)
            expected_wallet = dotenv_values(config).get("VALIDATOR_WALLET")
            require(
                isinstance(expected_wallet, str)
                and re.fullmatch(r"0x[a-f0-9]{40}", expected_wallet),
                "enrolled_signer_missing",
            )
            app.action("run")
            state = app.wait(
                lambda s: bool(s["validator_id"]) and bool(s["heartbeat_at"]), 120
            )
            report["validator_id"] = native.public_identity(state)
            emit("registered_waiting_for_scoped_admission")
            poll(
                app,
                lambda s: s.get("status") == "none",
                min(deadline, time.monotonic() + 600),
                allow_unavailable=True,
            )
            touched_pairing = True  # A lost response can hide a committed request.
            initial = pairing(app, "start")
            require(initial.get("status") == "pending", "pairing_start_failed")
            cancelled = pairing(app, "cancel", pairing_id=initial["pairing_id"])
            require(cancelled.get("status") == "cancelled", "pairing_cancel_failed")
            emit("unconfirmed_request_cancelled")
            # Finish an ordinary unpaid round before intentionally restarting.
            state = app.wait(
                lambda s: s["accepted"] > 0 and s["pending"] == 0 and s["dead"] == 0,
                max(1, deadline - time.monotonic()),
            )
            report["accepted_reports_before_pairing"] = state["accepted"]
            app.action("stop")
            app.wait(lambda s: not s["running"], 45)
            emit("signed_evidence_accepted_before_pairing")

        for phase in ("node-removal", "owner-removal"):
            with native.opened_app(binary, config) as app:
                require(
                    json.loads(app.request("/pairing.json")[1])["status"] == "idle",
                    "restart_implicitly_queried_pairing",
                )
                value = pairing(app, "start")
                require(value.get("status") == "pending", "pairing_start_failed")
                ticket = request_review(workspace, value, phase)
                emit("waiting_for_console_approval_" + phase)
                until = min(deadline, time.monotonic() + 540)
                approved = poll(app, lambda s: s.get("status") == "approved", until)
                while not confirmed_review(workspace, approved, ticket):
                    require(time.monotonic() < until, "explicit_code_review_timed_out")
                    time.sleep(2)
                # Polling and external approval have not confirmed locally.
                require(
                    pairing(app, "refresh").get("status") == "approved",
                    "approval_implicitly_linked",
                )
            with native.opened_app(binary, config) as app:
                fields = {
                    k: approved[k]
                    for k in ("pairing_id", "review_hash", "comparison_code")
                }
                require(
                    pairing(app, "confirm", **fields).get("error") == "changed",
                    "restart_bypassed_local_review",
                )
                refreshed = pairing(app, "refresh")
                require(
                    refreshed.get("status") == "approved"
                    and confirmed_review(workspace, refreshed, ticket),
                    "review_changed_after_restart",
                )
                discard_confirmation_response(app, refreshed)
            with native.opened_app(binary, config) as app:
                linked = poll(
                    app,
                    lambda s: s.get("status") == "linked",
                    min(deadline, time.monotonic() + 30),
                )
                require(
                    linked.get("pairing_id") == approved["pairing_id"],
                    "recovered_wrong_association",
                )
                emit("explicit_confirmation_recovered_" + phase)
                if phase == "node-removal":
                    removed = pairing(
                        app,
                        "unlink",
                        **{k: linked[k] for k in ("pairing_id", "review_hash")},
                    )
                    require(removed.get("status") == "none", "node_removal_failed")
                    emit("exact_node_removal_verified")
                else:
                    emit("waiting_for_console_owner_removal")
                    poll(
                        app,
                        lambda s: s.get("status") in {"none", "cancelled"},
                        min(deadline, time.monotonic() + 540),
                    )
                    emit("console_owner_removal_observed")
                require(
                    native.fingerprint(config) == before, "pairing_changed_credentials"
                )

        with native.opened_app(binary, config) as app:
            app.action("run")
            state = app.wait(
                lambda s: bool(s["heartbeat_at"])
                and s["accepted"] > 0
                and s["pending"] == 0
                and s["dead"] == 0,
                max(1, deadline - time.monotonic()),
            )
            require(
                native.public_identity(state) == report["validator_id"]
                and native.fingerprint(config) == before,
                "pairing_changed_identity",
            )
            report["accepted_reports_after_pairing"] = state["accepted"]
            diagnostics = app.request("/diagnostics.json")[1]
            values = dotenv_values(config)
            for secret in (
                app.token,
                str(config),
                values["VALIDATOR_PRIVATE_KEY"],
                values["VALIDATOR_API_KEY"],
                approved["pairing_id"],
                approved["comparison_code"],
            ):
                require(
                    secret.encode() not in diagnostics,
                    "diagnostics_leaked_private_material",
                )
            emit("same_identity_evidence_after_pairing_and_redacted_diagnostics")
        report["passed"] = True
    except Exception as exc:
        report["failure"] = (
            str(exc) if isinstance(exc, native.Failed) else "canary_exception"
        )
    finally:
        if touched_pairing:
            try:
                clean_pairing(binary, config, before)
                report["pairing_cleanup_verified"] = True
            except Exception:
                report["passed"] = False
                report["pairing_cleanup_failed"] = True
        if binary is not None:
            try:
                report["cleanup"] = native.cleanup(binary, config, expected_wallet)
                if report["passed"]:
                    require(
                        report["cleanup"]["suspended"]
                        and report["cleanup"]["keys_revoked"] > 0,
                        "complete_retirement_not_proven",
                    )
            except Exception:
                report["passed"] = False
                report["cleanup_failed"] = True
        emit("pairing_canary_finished")
    return 0 if report["passed"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("run", "review"))
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--commit")
    parser.add_argument("--core-commit")
    parser.add_argument("--minutes", type=int, choices=(30, 75), default=75)
    parser.add_argument("--approve-live-canary", action="store_true")
    args = parser.parse_args()
    if args.mode == "review":
        return review(args.workspace.resolve())
    require(
        args.approve_live_canary
        and args.report
        and args.run_id
        and args.commit
        and re.fullmatch(r"[a-f0-9]{40}", args.core_commit or ""),
        "explicit_live_approval_and_exact_revisions_required",
    )
    return run(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print('{"error":"pairing_canary_failed_no_private_output"}')
        raise SystemExit(1)
