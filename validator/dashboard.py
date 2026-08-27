# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Read-only local dashboard for validator operators.

The dashboard intentionally uses the Python standard library so the V0 node stays
easy to package. It binds to localhost by default and exposes only configuration
status plus Grid reachability; secrets are never rendered.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import metadata
from typing import Any

from .config import Settings
from .grid_client import GridClient


def _short(value: str, left: int = 6, right: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= left + right + 3:
        return value
    return f"{value[:left]}...{value[-right:]}"


def _version() -> str:
    try:
        return metadata.version("aipg-validator")
    except metadata.PackageNotFoundError:
        return "source"


async def _grid_snapshot() -> dict[str, Any]:
    grid = GridClient()
    capabilities: dict[str, Any] = {}
    registration: dict[str, Any] = {}
    scorecards: dict[str, Any] = {}
    try:
        capabilities = await grid.validator_capabilities()
        registration = await grid.validator_registration()
        scorecards = await grid.validator_scorecards(limit=10, since_hours=24)
        workers = await grid.list_workers()
        models = sorted({model for worker in workers for model in (worker.get("models") or [])})
        return {
            "ok": True,
            "capabilities": capabilities,
            "registration": registration,
            "scorecards": scorecards,
            "models": models,
            "model_count": len(models),
            "workers": workers,
            "worker_count": len(workers),
            "error": "",
        }
    except Exception as exc:  # pragma: no cover - network-dependent
        return {
            "ok": False,
            "capabilities": capabilities,
            "registration": registration,
            "scorecards": scorecards,
            "models": [],
            "model_count": 0,
            "workers": [],
            "worker_count": 0,
            "error": f"{type(exc).__name__}: {exc}",
        }
    finally:
        await grid.aclose()


def collect_status() -> dict[str, Any]:
    config_error = ""
    try:
        Settings.validate()
        config_ok = True
    except RuntimeError as exc:
        config_ok = False
        config_error = str(exc)

    data: dict[str, Any] = {
        "version": _version(),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "ok": config_ok,
            "error": config_error,
            "env_file": str(Settings.ENV_FILE) if hasattr(Settings, "ENV_FILE") else "",
            "grid_api_url": Settings.GRID_API_URL,
            "stake_required": Settings.REQUIRE_STAKE,
            "validator_wallet": _short(Settings.VALIDATOR_WALLET),
            "has_private_key": bool(Settings.VALIDATOR_PRIVATE_KEY),
            "probe_interval_s": Settings.PROBE_INTERVAL_S,
            "probe_timeout_s": Settings.PROBE_TIMEOUT_S,
        },
        "grid": {
            "ok": False,
            "capabilities": {},
            "registration": {},
            "scorecards": {},
            "models": [],
            "model_count": 0,
            "workers": [],
            "worker_count": 0,
            "error": "config-invalid",
        },
    }

    if config_ok:
        data["grid"] = asyncio.run(_grid_snapshot())
    return data


def _render_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AIPG Validator</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0e1116; --panel: #171c24; --line: #293241;
      --text: #eef2f6; --muted: #98a2b3;
      --ok: #3ddc97; --bad: #ff6b6b; --warn: #ffd166;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font: 15px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    main { width: min(1120px, calc(100vw - 32px)); margin: 32px auto; }
    header {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 24px;
    }
    h1 { margin: 0; font-size: 28px; letter-spacing: 0; }
    h2 { margin: 0 0 12px; font-size: 16px; letter-spacing: 0; }
    .subtle { color: var(--muted); }
    .grid { display: grid; gap: 14px; grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .panel { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; }
    .span-2 { grid-column: span 2; }
    .span-4 { grid-column: span 4; }
    .metric { font-size: 32px; font-weight: 700; }
    .ok { color: var(--ok); }
    .bad { color: var(--bad); }
    .warn { color: var(--warn); }
    dl { margin: 0; display: grid; grid-template-columns: 180px minmax(0, 1fr); gap: 8px 12px; }
    dt { color: var(--muted); }
    dd { margin: 0; overflow-wrap: anywhere; }
    ul { margin: 0; padding-left: 18px; }
    code { color: #d7e3ff; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border-top: 1px solid var(--line); padding: 8px 6px; text-align: left; vertical-align: top; }
    th { color: var(--muted); font-weight: 600; }
    button {
      appearance: none;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #202838;
      color: var(--text);
      padding: 9px 12px;
      cursor: pointer;
    }
    button:hover { background: #263247; }
    @media (max-width: 760px) {
      .grid { grid-template-columns: 1fr; }
      .span-2, .span-4 { grid-column: auto; }
      header { align-items: flex-start; flex-direction: column; }
      dl { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>AIPG Validator</h1>
      <div class="subtle">Local V0 status dashboard</div>
    </div>
    <button id="refresh">Refresh</button>
  </header>
  <section class="grid">
    <div class="panel"><h2>Config</h2><div id="config" class="metric">...</div></div>
    <div class="panel"><h2>Grid</h2><div id="grid" class="metric">...</div></div>
    <div class="panel"><h2>Models</h2><div id="models" class="metric">...</div></div>
    <div class="panel"><h2>Targeting</h2><div id="targeting" class="metric">...</div></div>
    <div class="panel"><h2>Scorecards</h2><div id="scorecards" class="metric">...</div></div>
    <div class="panel span-2"><h2>Node</h2><dl id="node"></dl></div>
    <div class="panel span-2"><h2>Grid Details</h2><dl id="details"></dl></div>
    <div class="panel span-4"><h2>Operator Qualification</h2><dl id="qualification"></dl></div>
    <div class="panel span-4"><h2>Validator Capabilities</h2><dl id="capabilities"></dl></div>
    <div class="panel span-4"><h2>Recent Evidence Scorecards</h2><div id="scorecard-table"></div></div>
    <div class="panel span-4"><h2>Visible Text Models</h2><ul id="model-list"></ul></div>
  </section>
</main>
<script>
const byId = (id) => document.getElementById(id);
function esc(value) {
  return String(value || "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;"
  }[ch]));
}
function yesNo(value) { return value ? "yes" : "no"; }
function statusText(ok) { return ok ? "OK" : "Issue"; }
function statusClass(ok) { return ok ? "ok" : "bad"; }
function setMetric(id, value, cls) {
  const el = byId(id);
  el.textContent = value;
  el.className = "metric " + (cls || "");
}
function setDl(id, rows) {
  byId(id).innerHTML = rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("");
}
function pct(value) {
  if (typeof value !== "number") return "";
  return `${Math.round(value * 100)}%`;
}
function renderScorecards(scorecards) {
  const rows = (scorecards.items || []).slice(0, 10);
  if (!scorecards.available) {
    byId("scorecard-table").innerHTML =
      `<div class="subtle">${esc(scorecards.error || "Scorecards not available.")}</div>`;
    return;
  }
  if (!rows.length) {
    byId("scorecard-table").innerHTML = "<div class=\"subtle\">No validator evidence in this window.</div>";
    return;
  }
  byId("scorecard-table").innerHTML = `<table>
    <thead><tr>
      <th>Subject</th><th>Model</th><th>Total</th><th>Healthy</th>
      <th>Slow</th><th>Failed</th><th>Avg latency</th>
    </tr></thead>
    <tbody>${rows.map((r) => `<tr>
      <td><code>${esc(r.subject_id || r.worker_id || r.model || "unknown")}</code></td>
      <td><code>${esc(r.model || "")}</code></td>
      <td>${r.total || 0}</td>
      <td>${r.healthy || 0} ${pct(r.healthy_rate)}</td>
      <td>${r.slow || 0} ${pct(r.slow_rate)}</td>
      <td>${r.failed || 0} ${pct(r.failed_rate)}</td>
      <td>${r.avg_latency_ms ? `${Math.round(r.avg_latency_ms)} ms` : ""}</td>
    </tr>`).join("")}</tbody>
  </table>`;
}
async function loadStatus() {
  const res = await fetch("/status.json", { cache: "no-store" });
  const data = await res.json();
  setMetric("config", statusText(data.config.ok), statusClass(data.config.ok));
  setMetric("grid", statusText(data.grid.ok), statusClass(data.grid.ok));
  setMetric("models", data.grid.model_count || 0, "");
  const caps = data.grid.capabilities || {};
  const registration = data.grid.registration || {};
  const qualification = registration.operator_qualification || {};
  const scorecards = data.grid.scorecards || {};
  const features = caps.features || {};
  const targeted = !!caps.targeted_probe_enabled;
  setMetric("targeting", targeted ? "On" : "Off", targeted ? "ok" : "warn");
  setMetric(
    "scorecards",
    scorecards.available ? (scorecards.count || 0) : "Off",
    scorecards.available ? "" : "warn"
  );
  setDl("node", [
    ["Version", data.version],
    ["Checked", data.checked_at],
    ["Env", data.config.env_file],
    ["Wallet", data.config.validator_wallet],
    ["Stake required", yesNo(data.config.stake_required)],
    ["Private key", yesNo(data.config.has_private_key)]
  ]);
  setDl("details", [
    ["Grid API", data.config.grid_api_url],
    ["Probe interval", `${data.config.probe_interval_s}s`],
    ["Probe timeout", `${data.config.probe_timeout_s}s`],
    ["Config error", data.config.error],
    ["Grid error", data.grid.error]
  ]);
  setDl("qualification", [
    ["Validator ID", registration.validator_id || "not registered"],
    ["Registration", registration.status || "unknown"],
    ["Operator status", qualification.status || "not reported by Core"],
    [
      "Elapsed",
      typeof qualification.elapsed_seconds === "number"
        ? `${(qualification.elapsed_seconds / 3600).toFixed(1)}h / ${(
            (qualification.minimum_seconds || 0) / 3600
          ).toFixed(1)}h`
        : ""
    ],
    ["Heartbeat samples", `${qualification.heartbeat_samples || 0} / ${qualification.expected_samples || 0}`],
    ["Heartbeat coverage", `${pct(qualification.sample_coverage)} / ${pct(qualification.minimum_sample_coverage)}`],
    ["Heartbeat fresh", yesNo(qualification.heartbeat_fresh)],
    ["Time ready", yesNo(qualification.time_ready)],
    ["Coverage ready", yesNo(qualification.coverage_ready)],
    ["Review current", yesNo(qualification.review_current)],
    ["Independent vote eligible", yesNo(qualification.independent_vote_eligible)],
    ["Review expires", qualification.expires_at || ""]
  ]);
  setDl("capabilities", [
    ["Endpoint", caps.available ? "available" : "not deployed"],
    ["Mode", caps.mode || "model_routed_v0"],
    ["API version", caps.validator_api_version || "unknown"],
    ["Attestation sink", yesNo(features.attest)],
    ["Worker inventory", yesNo(features.worker_inventory)],
    ["Targeted probe", yesNo(features.targeted_probe)],
    ["Assignments", yesNo(features.assignments)],
    ["Worker scorecards", yesNo(features.worker_scorecards)],
    ["Validator rewards", yesNo(features.validator_rewards)],
    ["Stake required", yesNo(features.staking_required)],
    ["Economic effect", caps.economic_effect || "none"],
    ["Targetable workers", data.grid.worker_count || 0],
    ["Capability error", caps.error || ""]
  ]);
  renderScorecards(scorecards);
  const models = (data.grid.models || []).slice(0, 20);
  byId("model-list").innerHTML = models.length
    ? models.map((m) => `<li><code>${esc(m)}</code></li>`).join("")
    : "<li class=\"subtle\">No models visible.</li>";
}
byId("refresh").addEventListener("click", loadStatus);
loadStatus().catch((err) => {
  setMetric("config", "Issue", "bad");
  setDl("details", [["Dashboard error", err.toString()]]);
});
</script>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "AIPGValidatorDashboard/0.1"

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path in {"/", "/index.html"}:
            self._send_text(_render_html(), "text/html; charset=utf-8")
            return
        if self.path == "/status.json":
            self._send_json(collect_status())
            return
        if self.path == "/healthz":
            self._send_json({"ok": True})
            return
        self.send_error(404)

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def _send_text(self, body: str, content_type: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, body: dict[str, Any]) -> None:
        encoded = json.dumps(body, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def run_dashboard(host: str | None = None, port: int | None = None) -> None:
    bind_host = host or Settings.DASHBOARD_HOST
    bind_port = port or Settings.DASHBOARD_PORT
    if not 1 <= bind_port <= 65535:
        raise RuntimeError("dashboard port must be between 1 and 65535.")
    server = ThreadingHTTPServer((bind_host, bind_port), DashboardHandler)
    url = f"http://{bind_host}:{bind_port}/"
    print(f"AIPG Validator dashboard listening on {url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard.")
    finally:
        server.server_close()
