# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Owner-approved Windows canary. Never print child output or upload private state."""

import argparse
import hashlib
import http.client
import json
import os
import queue
import re
import signal
import subprocess
import threading
import time
import uuid
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

REPO = "AIPowerGrid/grid-validator"
RELEASES = {
    "v0.1.0-preview.13": "5fa00bff24ce7749fa3316b68cecdb975155339d",
    "v0.1.0-preview.14": "d5e7b3e2ef9ac8c5c905432ec5b5613f2f3c7444",
}
CURRENT = "v0.1.0-preview.14"
PREVIOUS = "v0.1.0-preview.13"
GRID = "https://api.aipowergrid.io"
ASSET = "aipg-validator-windows-x64.zip"
EXE = "aipg-validator.exe"


class Failed(RuntimeError):
    """Only fixed safe error codes may leave the harness."""


def require(condition, code):
    if not condition:
        raise Failed(code)


def command(args, *, env=None, cwd=None, input=None, expected=0, timeout=90):
    process = subprocess.Popen(
        args,
        env=env,
        cwd=cwd,
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        start_new_session=os.name != "nt",
    )
    try:
        output, _ = process.communicate(input=input, timeout=timeout)
    except subprocess.TimeoutExpired:
        stop_tree(process)
        process.communicate(timeout=10)
        raise Failed("command_timeout") from None
    require(process.returncode == expected, "command_failed")
    return output


def verify_archive(directory, tag):
    manifest = json.loads((directory / "validator-release.json").read_text())
    require(
        manifest.get("tag") == tag and manifest.get("commit") == RELEASES[tag],
        "release_identity_mismatch",
    )
    assets = [item for item in manifest.get("assets", []) if item.get("name") == ASSET]
    require(len(assets) == 1, "archive_manifest_mismatch")
    path = directory / ASSET
    require(path.stat().st_size == assets[0]["bytes"], "archive_size_mismatch")
    require(
        hashlib.sha256(path.read_bytes()).hexdigest() == assets[0]["sha256"],
        "archive_hash_mismatch",
    )
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        require(
            len(entries) == 1
            and entries[0].filename == EXE
            and 0 < entries[0].file_size < 512 * 1024 * 1024
            and not entries[0].is_dir()
            and (entries[0].external_attr >> 16) & 0o170000 != 0o120000,
            "unsafe_archive",
        )
        target = directory / EXE
        require(not target.exists(), "binary_already_exists")
        with target.open("xb") as output, archive.open(entries[0]) as source:
            while chunk := source.read(1024 * 1024):
                output.write(chunk)
    return {"tag": tag, "commit": RELEASES[tag], "archive_sha256": assets[0]["sha256"]}


def fetch(root):
    require(not root.exists(), "artifact_directory_exists")
    root.mkdir(parents=True)
    verified = []
    for tag, commit in RELEASES.items():
        print("Verifying published " + tag, flush=True)
        directory = root / tag
        directory.mkdir()
        command(
            [
                "gh",
                "release",
                "download",
                tag,
                "--repo",
                REPO,
                "--dir",
                str(directory),
                "--pattern",
                ASSET,
                "--pattern",
                "validator-release.json",
            ],
            timeout=180,
        )
        # Verify both signed objects before trusting manifest fields or extracting code.
        for name in (ASSET, "validator-release.json"):
            command(
                [
                    "gh",
                    "attestation",
                    "verify",
                    str(directory / name),
                    "--repo",
                    REPO,
                    "--signer-workflow",
                    REPO + "/.github/workflows/release-binaries.yml",
                    "--source-ref",
                    "refs/tags/" + tag,
                    "--source-digest",
                    commit,
                    "--deny-self-hosted-runners",
                ],
                timeout=180,
            )
        verified.append(verify_archive(directory, tag))
    (root / "verified.json").write_text(json.dumps(verified), encoding="utf-8")
    print("Published archives and manifests passed provenance and checksum checks.")


def binary_env(config, overrides=None):
    allowed = {
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "PATH",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
        "PATHEXT",
        "HOME",
        "TMPDIR",
    }
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    env.update(
        VALIDATOR_ENV=str(config),
        PYTHONUNBUFFERED="1",
        PYTHONIOENCODING="utf-8",
        PROBE_INTERVAL_S="30",
        VALIDATOR_UPDATE_CHECK="false",
    )
    env.update(overrides or {})
    return env


def stop_tree(process):
    if os.name != "nt":
        # Every harness child owns its process group, including frozen children.
        # The parent may already have exited while descendants retain its pipes.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except PermissionError:
            # A disappearing group can race cleanup on macOS. Do not treat an
            # actual permission failure against a remaining group as success.
            groups = subprocess.run(
                ["ps", "-axo", "pgid="],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            ).stdout.split()
            if str(process.pid) in groups:
                raise
        process.wait(timeout=10)
    elif process.poll() is None:
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
        )
        process.wait(timeout=20)


class App:
    def __init__(self, binary, config, overrides=None):
        self.process = subprocess.Popen(
            [str(binary), "app", "--no-browser"],
            env=binary_env(config, overrides),
            cwd=config.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=os.name != "nt",
        )
        lines = queue.Queue(maxsize=4)

        def read():
            for line in self.process.stdout:
                if lines.full():
                    continue
                lines.put(line[:4096])

        self.reader = threading.Thread(target=read, daemon=True)
        self.reader.start()
        try:
            line = lines.get(timeout=60)
            require(line.startswith("Local validator app: "), "app_did_not_open")
            url = urlsplit(line.removeprefix("Local validator app: ").strip())
            require(
                url.hostname == "127.0.0.1" and url.port and len(url.fragment) >= 32,
                "invalid_local_app_url",
            )
            self.port, self.token = url.port, url.fragment
        except BaseException:
            stop_tree(self.process)
            raise

    def request(
        self, path="/status.json", action=None, auth=True, fields=None, timeout=10
    ):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=timeout)
        headers = {"Authorization": "Bearer " + self.token} if auth else {}
        body = None
        if action:
            headers.update(
                Origin=f"http://127.0.0.1:{self.port}",
                **{"Content-Type": "application/json"},
            )
            body = json.dumps({"action": action, **(fields or {})})
        try:
            conn.request("POST" if action else "GET", path, body, headers)
            response = conn.getresponse()
            data = response.read(131073)
            require(len(data) <= 131072, "oversized_app_response")
            return response.status, data
        finally:
            conn.close()

    def state(self):
        status, body = self.request()
        require(status == 200, "app_status_failed")
        return json.loads(body)

    def action(self, action):
        require(self.request("/control", action)[0] == 202, "app_action_rejected")

    def wait(self, predicate, seconds=90):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            state = self.state()
            if predicate(state):
                return state
            require(self.process.poll() is None, "app_exited")
            time.sleep(1)
        raise Failed("app_state_timeout")

    def close(self):
        try:
            self.action("quit")
            require(self.process.wait(timeout=40) == 0, "app_exit_failed")
        finally:
            stop_tree(self.process)
            self.reader.join(timeout=5)
            if not self.reader.is_alive():
                self.process.stdout.close()


@contextmanager
def opened_app(*args, **kwargs):
    app = App(*args, **kwargs)
    try:
        yield app
    finally:
        app.close()


def fingerprint(config):
    return hashlib.sha256(config.read_bytes()).digest()


def public_identity(state):
    value = state.get("validator_id")
    require(
        isinstance(value, str) and re.fullmatch(r"val_[0-9a-f]{32}", value),
        "missing_validator_id",
    )
    return value


def core_json(client, method, path, *, token="", body=None):
    headers = {"Accept": "application/json", "Accept-Encoding": "identity"}
    if token:
        headers["Authorization"] = "Bearer " + token
    with client.stream(method, GRID + path, headers=headers, json=body) as response:
        require(response.status_code == 200, "core_request_failed")
        data = bytearray()
        for chunk in response.iter_bytes(chunk_size=4096):
            data.extend(chunk)
            require(len(data) <= 65536, "oversized_core_response")
        return json.loads(data)


def cleanup(binary, config, expected_wallet=None):
    """Retire only the identity generated in this fresh canary directory."""
    if not config.exists():
        return {"suspended": False, "keys_revoked": 0}
    import httpx
    from dotenv import dotenv_values
    from eth_account import Account
    from eth_account.messages import encode_defunct
    from validator.enrollment import DOMAIN, IDENTITY_ORIGIN, URI, validated_message

    values = dotenv_values(config)
    require(
        values.get("VALIDATOR_IDENTITY_ORIGIN") == IDENTITY_ORIGIN
        and values.get("GRID_API_URL") == GRID,
        "cleanup_identity_not_generated",
    )
    account = Account.from_key(values["VALIDATOR_PRIVATE_KEY"])
    wallet = account.address.lower()
    require(
        wallet == values.get("VALIDATOR_WALLET")
        and (expected_wallet is None or wallet == expected_wallet),
        "cleanup_identity_mismatch",
    )
    suspended = False
    key = values.get("VALIDATOR_API_KEY")
    with httpx.Client(timeout=15, trust_env=False, follow_redirects=False) as client:
        # Suspension is required only if enrollment reached registration.
        if key:
            response = client.get(
                GRID + "/v1/validator/registration",
                headers={"Authorization": "Bearer " + key},
            )
            if response.status_code == 200:
                command(
                    [str(binary), "suspend"], env=binary_env(config), cwd=config.parent
                )
                registered = core_json(
                    client, "GET", "/v1/validator/registration", token=key
                )
                require(
                    registered.get("status") == "suspended", "cleanup_suspend_failed"
                )
                suspended = True
            else:
                require(
                    response.status_code == 403
                    and response.json()
                    == {"detail": "validator registration required"},
                    "cleanup_registration_unknown",
                )
        challenge = core_json(
            client,
            "POST",
            "/v1/accounts/wallet/challenge",
            body={"address": wallet, "domain": DOMAIN, "uri": URI, "chain_id": 8453},
        )
        message = validated_message(challenge, wallet, datetime.now(timezone.utc))
        signature = (
            "0x"
            + bytes(
                Account.sign_message(
                    encode_defunct(text=message), account.key
                ).signature
            ).hex()
        )
        session = core_json(
            client,
            "POST",
            "/v1/accounts/wallet/verify",
            body={"address": wallet, "message": message, "signature": signature},
        )
        require(session.get("wallet") == wallet, "cleanup_session_mismatch")
        token = session["access_token"]
        owner = core_json(client, "GET", "/v1/account", token=token)
        require(
            owner.get("wallet") == wallet
            and owner.get("account_id") == session.get("account_id"),
            "cleanup_account_mismatch",
        )
        keys = owner.get("keys")
        require(isinstance(keys, list) and len(keys) <= 3, "cleanup_unexpected_keys")
        for item in keys:
            require(
                item.get("label") == "validator-dedicated-node"
                and re.fullmatch(r"[a-f0-9]{12}", item.get("id", "")),
                "cleanup_unexpected_key",
            )
        count = 0
        for item in keys:
            if not item.get("revoked"):
                result = core_json(
                    client, "DELETE", "/v1/account/keys/" + item["id"], token=token
                )
                require(result.get("count") == 1, "cleanup_revoke_failed")
                count += 1
        owner = core_json(client, "GET", "/v1/account", token=token)
        require(
            all(item.get("revoked") for item in owner["keys"]),
            "cleanup_keys_still_active",
        )
        if key:
            rejected = client.get(
                GRID + "/v1/validator/registration",
                headers={"Authorization": "Bearer " + key},
            )
            require(rejected.status_code == 401, "revoked_key_still_authenticates")
    return {"suspended": suspended, "keys_revoked": count}


def run(artifacts, workspace, report_path, minutes):
    import httpx
    from dotenv import dotenv_values

    require(os.name == "nt", "windows_required")
    require(minutes in {10, 30, 75}, "invalid_canary_window")
    require(
        not workspace.exists() and not report_path.exists(), "existing_canary_state"
    )
    workspace.mkdir(parents=True)
    config = workspace / "node.env"
    binary = artifacts / CURRENT / EXE
    previous = artifacts / PREVIOUS / EXE
    report = {
        "schema": "aipg.validator.native-canary.v1",
        "first_party": True,
        "platform": "windows-x64",
        "release": CURRENT,
        "checks": [],
        "passed": False,
    }

    def emit(name):
        report["checks"].append(name)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        event = {"check": name}
        if "validator_id" in report:
            event["validator_id"] = report["validator_id"]
        print(json.dumps(event), flush=True)

    firewall = "aipg-validator-canary-" + uuid.uuid4().hex
    rule_added = False
    expected_wallet = None
    (workspace / "firewall-rule.txt").write_text(firewall, encoding="ascii")
    try:
        with httpx.Client(
            timeout=15, trust_env=False, follow_redirects=False
        ) as client:
            caps = core_json(client, "GET", "/v1/validator/capabilities")
            require(
                caps.get("economic_effect") == "none"
                and caps.get("probe_policy", {}).get("quality_eligible") is False
                and caps.get("features", {}).get("validator_rewards") is False,
                "economic_boundary_changed",
            )
            health = core_json(client, "GET", "/health")
            require(
                re.fullmatch(r"[a-f0-9]{40}", health.get("build_commit", "")),
                "missing_core_version",
            )
            report["core_commit"] = health["build_commit"]
        emit("unpaid_preview_preflight")
        for tag in RELEASES:
            output = command(
                [str(artifacts / tag / EXE), "--version"], env=binary_env(config)
            )
            require(
                output.strip() == "aipg-validator " + tag, "binary_version_mismatch"
            )
        command(
            [str(binary), "enroll"], env=binary_env(config), cwd=workspace, input="n\n"
        )
        require(not config.exists(), "cancel_created_identity")
        emit("cancel_created_no_identity")
        with opened_app(binary, config) as app:
            require(app.request(auth=False)[0] == 401, "app_auth_guard_failed")
            require(
                not app.state()["configured"] and not config.exists(),
                "app_implicitly_enrolled",
            )
            app.action("enroll")
            app.wait(lambda s: s["phase"] == "enrolled" and not s["running"], 120)
            before = fingerprint(config)
            expected_wallet = dotenv_values(config)["VALIDATOR_WALLET"]
            command(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "$ErrorActionPreference='Stop'; $acl=Get-Acl -LiteralPath $env:VALIDATOR_ENV; "
                    "if (-not $acl.AreAccessRulesProtected -or $acl.Access.Count -ne 1) {exit 1}; "
                    "$sid=$acl.Access[0].IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value; "
                    "if ($sid -ne 'S-1-3-4') {exit 1}",
                ],
                env=binary_env(config),
            )
            emit("explicit_app_enrollment")
            emit("windows_owner_only_identity_acl")
            app.action("enroll")
            app.wait(lambda s: s["phase"] == "enrolled" and not s["running"], 60)
            require(fingerprint(config) == before, "repeat_enrollment_changed_identity")
            emit("repeat_enrollment_preserved_identity")
            app.action("run")
            state = app.wait(
                lambda s: bool(s["validator_id"]) and bool(s["heartbeat_at"]), 120
            )
            report["validator_id"] = public_identity(state)
            emit("registered_and_heartbeat_acknowledged")
            deadline = time.monotonic() + minutes * 60
            while True:
                state = app.state()
                require(not state["error"], "live_runtime_error")
                if (
                    state["accepted"] > 0
                    and state["pending"] == 0
                    and state["dead"] == 0
                ):
                    break
                require(time.monotonic() < deadline, "no_accepted_evidence_in_window")
                time.sleep(5)
            report["accepted_reports"] = state["accepted"]
            emit("signed_evidence_accepted_outbox_drained")
            diagnostics = app.request("/diagnostics.json")[1]
            values = dotenv_values(config)
            for secret in (
                values["VALIDATOR_PRIVATE_KEY"],
                values["VALIDATOR_API_KEY"],
                app.token,
                str(config),
            ):
                require(
                    secret.encode() not in diagnostics,
                    "diagnostics_leaked_private_material",
                )
            emit("diagnostics_redaction")
            app.action("stop")
            app.wait(lambda s: not s["running"], 45)
            require(fingerprint(config) == before, "stop_changed_identity")
            emit("stop_preserved_identity")
        with opened_app(
            binary, config, {"VALIDATOR_API_KEY": "invalid-canary-key"}
        ) as app:
            app.action("run")
            app.wait(
                lambda s: s["error"] == "credentials_rejected" and not s["running"], 120
            )
        require(fingerprint(config) == before, "bad_credentials_changed_identity")
        emit("bad_credentials_rejected_without_config_change")
        for candidate in (previous, binary):
            output = command(
                [str(candidate), "check", "--no-probe"],
                env=binary_env(config),
                cwd=workspace,
            )
            require(
                set(re.findall(r"val_[a-f0-9]{32}", output))
                == {report["validator_id"]},
                "upgrade_changed_registration",
            )
            require(fingerprint(config) == before, "upgrade_changed_credentials")
        emit("published_preview12_to_preview13_same_identity")
        with opened_app(binary, config) as app:
            app.action("run")
            state = app.wait(lambda s: bool(s["heartbeat_at"]), 120)
            require(
                public_identity(state) == report["validator_id"],
                "restart_changed_identity",
            )
            emit("app_restart_preserved_identity")
            command(
                [
                    "netsh",
                    "advfirewall",
                    "firewall",
                    "add",
                    "rule",
                    "name=" + firewall,
                    "dir=out",
                    "action=block",
                    "program=" + str(binary),
                    "enable=yes",
                    "profile=any",
                ]
            )
            rule_added = True
            app.wait(lambda s: s["error"] == "grid_unavailable", 180)
            emit("real_outage_reported")
            heartbeat_before = app.state()["heartbeat_at"]
            command(
                [
                    "netsh",
                    "advfirewall",
                    "firewall",
                    "delete",
                    "rule",
                    "name=" + firewall,
                ]
            )
            rule_added = False
            app.wait(
                lambda s: s["heartbeat_at"] != heartbeat_before
                and s["phase"] == "waiting"
                and s["pending"] == 0
                and s["dead"] == 0
                and not s["error"],
                300,
            )
            require(fingerprint(config) == before, "recovery_changed_identity")
            emit("network_recovered_same_identity")
        report["passed"] = True
    except Exception as exc:
        report["failure"] = str(exc) if isinstance(exc, Failed) else "canary_exception"
    finally:
        if rule_added:
            try:
                command(
                    [
                        "netsh",
                        "advfirewall",
                        "firewall",
                        "delete",
                        "rule",
                        "name=" + firewall,
                    ]
                )
            except Exception:
                report["passed"] = False
                report["firewall_cleanup_failed"] = True
        try:
            report["cleanup"] = cleanup(binary, config, expected_wallet)
            if report["passed"]:
                require(
                    report["cleanup"]["suspended"]
                    and report["cleanup"]["keys_revoked"] > 0,
                    "complete_retirement_not_proven",
                )
        except Exception:
            report["passed"] = False
            report["cleanup_failed"] = True
        emit("canary_finished")
    return 0 if report["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["fetch", "run"])
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--minutes", type=int, default=10, choices=[10, 30, 75])
    parser.add_argument("--approve-live-canary", action="store_true")
    args = parser.parse_args()
    if args.mode == "fetch":
        fetch(args.artifacts.resolve())
        return 0
    require(
        args.approve_live_canary and args.workspace and args.report,
        "explicit_live_approval_required",
    )
    return run(
        args.artifacts.resolve(),
        args.workspace.resolve(),
        args.report.resolve(),
        args.minutes,
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print('{"error":"canary_harness_failed_no_private_output"}')
        raise SystemExit(1)
