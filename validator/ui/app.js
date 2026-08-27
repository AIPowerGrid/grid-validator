// SPDX-License-Identifier: AGPL-3.0-or-later
"use strict";
const el = (id) => document.getElementById(id);
let token = location.hash.slice(1);
if (token) {
  sessionStorage.setItem("aipg-local-session", token);
  history.replaceState(null, "", location.pathname);
} else token = sessionStorage.getItem("aipg-local-session") || "";
const phases = {starting:"Starting", registering:"Registering", registered:"Registered", heartbeat:"Connected", probing:"Validating", waiting:"Waiting for assignments", retrying:"Reconnecting", error:"Needs attention", enrolling:"Setting up node", enrolled:"Ready to start", stopping:"Stopping", stopped:"Stopped"};
const errors = {
  configuration_invalid:"Configuration is incomplete or invalid. New operators can set up a node; existing operators should restore their configuration, not replace their identity.",
  credentials_rejected:"The Grid rejected this node's credentials. Check the validator key and linked signing identity. Do not create extra keys to troubleshoot.",
  grid_unavailable:"The Grid could not be reached. Check your connection. The running node will retry automatically.",
  already_running:"Another validator is using this state directory. Stop that instance before starting here.",
  enrollment_failed:"Setup could not finish. Existing configuration was kept. Retry with the same identity; do not paste a personal wallet key.",
  runtime_error:"The validator encountered a local error. Download diagnostics and retry after checking your configuration.",
  process_exited:"The validator exited unexpectedly. Its identity and recovery queue were kept. You can start it again.",
  local_access:"The app could not start the validator. Check access to the executable and configuration folder."
};
let busy = false;
async function request(path, options={}) {
  const response = await fetch(path, {...options, cache:"no-store", headers:{Authorization:`Bearer ${token}`, ...options.headers}});
  if (!response.ok) throw new Error(response.status === 401 || response.status === 403 ? "Local session expired. Reopen the app from the validator menu." : "The local app could not complete that operation. Refresh or reopen it.");
  return response.json();
}
function showError(message) { el("error").hidden = !message; el("error").textContent = message || ""; }
function age(value) { return value ? Math.max(0,Math.floor((Date.now()-Date.parse(value))/1000)) : null; }
function render(data) {
  el("version").textContent = data.version;
  el("phase").textContent = phases[data.phase] || "Unknown state";
  el("setup").hidden = data.configured;
  el("setup").disabled = data.running || busy;
  el("start").disabled = !data.configured || data.running || busy;
  el("stop").disabled = !data.running || data.phase === "stopping" || busy;
  el("diagnostics").disabled = false;
  el("registration").textContent = data.validator_id ? "Registered" : "Not checked";
  el("validator-id").textContent = data.validator_id;
  const seconds = age(data.heartbeat_at);
  el("heartbeat").textContent = seconds === null ? "Not received" : `${seconds}s ago`;
  const fresh = data.running && seconds !== null && seconds < 150;
  el("heartbeat").className = fresh ? "fresh" : "stale";
  el("connection").textContent = fresh ? "Grid acknowledged" : data.running ? "Awaiting fresh heartbeat" : "Not running";
  el("accepted").textContent = data.accepted;
  el("pending").textContent = data.pending === null ? "Not checked" : `${data.pending} pending`;
  el("dead").textContent = data.dead === null ? "" : `${data.dead} need review`;
  el("message").textContent = data.phase === "probing" ? `${data.assignments} assigned checks in progress.` : data.phase === "stopping" ? "Stopping local work. Journaled assignments and evidence remain available for recovery." : data.phase === "waiting" ? "Connected. No new assignment is not a failure. Accepted evidence is counted only after Grid acknowledgement." : data.phase === "enrolling" ? "Creating a dedicated local signer and obtaining a validator-only key." : data.configured ? "Your signing identity stays on this computer." : "No node credentials have been configured.";
  showError(errors[data.error]);
  const items = data.events.slice().reverse().map(event => {
    const li = document.createElement("li");
    const time = document.createElement("time");
    time.textContent = new Date(event.at).toLocaleTimeString();
    const label = document.createElement("span");
    label.textContent = errors[event.error] || `${phases[event.phase] || event.phase}${event.accepted ? `: ${event.accepted} evidence accepted` : ""}`;
    li.append(time,label); return li;
  });
  if (items.length) el("events").replaceChildren(...items);
}
async function refresh() {
  try { render(await request("/status.json")); }
  catch(error) {
    showError(error.message);
    el("phase").textContent = "Local app unavailable";
    for (const id of ["setup","start","stop","diagnostics"]) el(id).disabled = true;
  }
}
async function control(action) {
  if (busy) return;
  busy = true;
  for (const id of ["setup","start","stop"]) el(id).disabled = true;
  try { await request("/control", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action})}); }
  catch(error) {
    busy=false;
    await refresh();
    showError(error.message);
    return;
  }
  busy=false;
  await refresh();
}
el("start").addEventListener("click", () => control("run"));
el("stop").addEventListener("click", () => control("stop"));
el("setup").addEventListener("click", () => {
  el("consent").returnValue = "";
  el("consent").showModal();
});
el("consent").addEventListener("close", () => { if(el("consent").returnValue === "confirm") control("enroll"); });
el("consent").addEventListener("keydown", event => {
  if (event.key === "Escape") {
    event.preventDefault();
    el("consent").close("cancel");
  }
});
el("diagnostics").addEventListener("click", async () => {
  try {
    const data = await request("/diagnostics.json");
    const url = URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:"application/json"}));
    const link=document.createElement("a"); link.href=url; link.download="aipg-validator-diagnostics.json"; link.click(); setTimeout(() => URL.revokeObjectURL(url),1000);
  } catch(error) { showError(error.message); }
});
async function poll() { await refresh(); setTimeout(poll,3000); }
poll();
