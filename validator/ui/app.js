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
  local_access:"The app could not start the validator. Check access to the executable and configuration folder.",
  clock_drift:"This computer's clock differs from the Grid by more than five minutes. Enable automatic date and time, sync the clock, then start the validator again."
};
let busy = false;
let closed = false;
let localAvailable = false;
let configured = false;
let updateState = {status:"not_checked"};
let updateBusy = false;
let nextUpdateCheck = 0;
let updateConsentTag = null;
let renderedVersion = null;
function renderUpdates() {
  const labels = {
    not_checked:"Not checked", checking:"Checking releases...",
    preparing:"Downloading and verifying the update...",
    restarting:"Restarting the app...",
    install_failed:"Update failed. Your installed version and node identity are unchanged. Try again.",
    current:"No newer release found on your release channel.",
    unavailable:"Could not check releases. Try again shortly; your node is unchanged.",
    source_build:"Source build. Update from the reviewed repository using your existing configuration."
  };
  el("updates-status").textContent = updateState.status === "available" ? `${updateState.latest_tag} is available. Keep your existing node configuration when upgrading.` : labels[updateState.status] || labels.unavailable;
  el("updates-check").disabled = !localAvailable || closed || updateBusy || ["checking","preparing","restarting"].includes(updateState.status) || Date.now() < nextUpdateCheck;
  el("updates-install").hidden = !updateState.install_supported || !["available","install_failed"].includes(updateState.status);
  el("updates-install").disabled = !localAvailable || closed || updateBusy;
  const safeURL = typeof updateState.url === "string" && /^https:\/\/github\.com\/AIPowerGrid\/grid-validator\/releases\/tag\/v[0-9]+\.[0-9]+\.[0-9]+(?:-(?:preview|alpha|beta|rc)(?:\.[0-9]+)?)?$/.test(updateState.url);
  el("updates-release").hidden = closed || !localAvailable || updateState.status !== "available" || !safeURL;
  if (safeURL) el("updates-release").href = updateState.url;
  else el("updates-release").removeAttribute("href");
}
async function request(path, options={}) {
  const response = await fetch(path, {...options, cache:"no-store", headers:{Authorization:`Bearer ${token}`, ...options.headers}});
  if (!response.ok) throw new Error(response.status === 401 || response.status === 403 ? "Local session expired. Reopen the app from the validator menu." : "The local app could not complete that operation. Refresh or reopen it.");
  return response.json();
}
function showError(message) { el("error").hidden = !message; el("error").textContent = message || ""; }
function age(value) { return value ? Math.max(0,Math.floor((Date.now()-Date.parse(value))/1000)) : null; }
function renderChecks(checks={}) {
  for (const name of ["configured","registered","heartbeat","assignment","evidence"]) {
    const item = el(`check-${name}`);
    const ready = checks[name] === true;
    item.classList.toggle("ready", ready);
    item.querySelector("small").textContent = ready ? "Confirmed" : "Waiting";
  }
}
function render(data) {
  if (renderedVersion !== null && renderedVersion !== data.version) {
    location.reload();
    return;
  }
  renderedVersion = data.version;
  localAvailable = true;
  configured = data.configured;
  renderPairing();
  renderUpdates();
  renderCompensation();
  el("version").textContent = data.version;
  el("phase").textContent = phases[data.phase] || "Unknown state";
  el("setup").hidden = data.configured;
  el("setup").disabled = data.running || busy;
  el("start").disabled = !data.configured || data.running || busy;
  el("stop").disabled = !data.running || data.phase === "stopping" || busy;
  el("diagnostics").disabled = false;
  el("quit").disabled = busy;
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
  renderChecks(data.checks);
  el("update").hidden = !data.latest_version;
  el("update").textContent = data.latest_version ? `Update available: ${data.latest_version}` : "";
  el("message").textContent = data.phase === "probing" ? `${data.assignments} assigned checks in progress.` : data.phase === "stopping" ? "Stopping local work. Journaled assignments and evidence remain available for recovery." : data.phase === "waiting" ? "Connected. No new assignment is not a failure. Accepted evidence is counted only after Grid acknowledgement." : data.phase === "enrolling" ? "Creating a dedicated local signer and obtaining a validator-only key." : data.configured ? "Your signing identity stays on this computer." : "No node credentials have been configured.";
  showError(errors[data.error] || (data.dead > 0 ? "Some evidence exhausted its retry policy and needs review. Download diagnostics; do not delete the recovery queue." : ""));
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
  if (closed) return;
  try { const data = await request("/status.json"); if (!closed) render(data); }
  catch(error) {
    if (closed) return;
    showError(error.message);
    localAvailable = false;
    renderUpdates();
    renderPairing();
    renderCompensation();
    el("phase").textContent = "Local app unavailable";
    for (const id of ["setup","start","stop","diagnostics","quit"]) el(id).disabled = true;
  }
}
async function control(action) {
  if (busy || closed) return;
  busy = true;
  for (const id of ["setup","start","stop","quit"]) el(id).disabled = true;
  try { await request("/control", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action})}); }
  catch(error) {
    busy=false;
    await refresh();
    showError(error.message);
    return;
  }
  busy=false;
  if (action === "quit") {
    closed = true;
    localAvailable = false;
    renderUpdates();
    renderPairing();
    renderCompensation();
    el("phase").textContent = "App closed";
    el("message").textContent = "Local validator work stopped. Configuration and recovery journal were kept.";
    el("connection").textContent = "Not running";
    el("heartbeat").className = "stale";
    for (const id of ["setup","start","stop","diagnostics","quit"]) el(id).disabled = true;
    showError("");
    return;
  }
  await refresh();
}
el("start").addEventListener("click", () => control("run"));
el("stop").addEventListener("click", () => control("stop"));
el("quit").addEventListener("click", () => control("quit"));
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
const pairingLabels = {
  idle:"Not checked", none:"No account linked", pending:"Waiting for your approval in Console",
  approved:"Approved in Console. Compare the code before confirming here.",
  linked:"Account linked", cancelled:"Request cancelled. No account linked.",
  expired:"Request expired. Start a new link request.", error:"Link needs attention"
};
const pairingErrors = {
  configuration_invalid:"Set up and start this node first. Existing operators should restore their configuration, not replace their identity.",
  unsupported_grid:"Account pairing currently supports the official Grid only. Your node configuration has not changed.",
  credentials_rejected:"The Grid rejected this node's credentials. Restore the correct validator configuration, then check the link again.",
  registration_required:"Start this node to register it, then check the link again. Revoked nodes cannot pair.",
  not_found:"This request is no longer available. Check the link before starting again.",
  changed:"The approval changed or expired. Check the link and review it again before confirming.",
  expired:"The request expired or your computer's clock differs from the Grid. Check your clock and start again.",
  rate_limited:"Too many requests. Wait a minute before checking again.",
  unavailable:"Account linking is unavailable or the Grid could not be reached. Check the link later; a submitted confirmation may already have completed.",
  invalid_contract:"The Grid's pairing reply could not be verified. Check the link again; a previously submitted confirmation may already have completed.",
  app_closed:"The local app is closing. Reopen it to check the link."
};
let pairing = {status:"idle",busy:false};
let pairingBusy = false;
let nextPairingCheck = 0;
let pairingConsent = null;
function renderPairing() {
  const disabled = !localAvailable || !configured || closed || pairingBusy || pairing.busy;
  const pending = ["pending","approved"].includes(pairing.status);
  const expired = pending && pairing.expires_at * 1000 <= Date.now();
  el("pair-status").textContent = pairingBusy || pairing.busy ? "Checking account link..." : expired ? pairingLabels.expired : pairingLabels[pairing.status] || "Unknown link state";
  el("pair-error").hidden = !pairing.error;
  el("pair-error").textContent = pairingErrors[pairing.error] || (pairing.error ? "Account linking could not finish. Check the link again." : "");
  for (const id of ["pair-start","pair-refresh","pair-confirm","pair-cancel","pair-unlink"]) el(id).disabled = disabled;
  el("pair-start").hidden = pairing.status === "linked" || (pending && !expired);
  el("pair-confirm").hidden = pairing.status !== "approved" || expired;
  el("pair-cancel").hidden = !pending || expired;
  el("pair-unlink").hidden = pairing.status !== "linked";
  el("pair-details").hidden = !pairing.validator_id;
  el("pair-node").textContent = pairing.validator_id || "";
  el("pair-expiry").textContent = pending && !expired ? `Expires in ${Math.max(0,Math.ceil(pairing.expires_at-Date.now()/1000))}s` : "";
  el("pair-code").hidden = pairing.status !== "approved" || expired;
  el("pair-code").textContent = pairing.comparison_code || "";
  const safeURL = typeof pairing.approval_url === "string" && /^https:\/\/console\.aipowergrid\.io\/dashboard\/connect-validator\/vpa_[a-f0-9]{64}$/.test(pairing.approval_url);
  el("pair-open").hidden = disabled || !pending || expired || !safeURL;
  if (safeURL) el("pair-open").href = pairing.approval_url;
  else el("pair-open").removeAttribute("href");
  if (el("pair-consent").open && pairingConsent && (
    closed || !localAvailable || expired ||
    (pairingConsent.review_hash && pairingConsent.review_hash !== pairing.review_hash)
  )) el("pair-consent").close("cancel");
}
async function pairingAction(form) {
  if (closed || pairingBusy || !localAvailable) return;
  pairingBusy = true;
  renderPairing();
  try {
    pairing = await request("/pairing", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(form)});
  } catch(error) {
    pairing = {status:"error",error:"unavailable"};
    showError(error.message);
  } finally {
    pairingBusy = false;
    nextPairingCheck = Date.now() + 6000;
    renderPairing();
  }
}
function askPairing(action) {
  if (closed || !localAvailable || pairingBusy || pairing.busy) return;
  pairingConsent = {action};
  if (["confirm","unlink"].includes(action)) {
    pairingConsent.pairing_id = pairing.pairing_id;
    pairingConsent.review_hash = pairing.review_hash;
  }
  if (action === "confirm") pairingConsent.comparison_code = pairing.comparison_code;
  const copy = {
    start:["Link an existing AIPG account?","Create a ten-minute request, then sign in and approve it in Console. Nothing is linked until you compare the code and confirm here.","Create link request"],
    confirm:["Does this match your Console code?","Confirm only if this exact code appears in the Console account you intend to link. This grants that account private visibility of this node.","Code matches - link account"],
    unlink:["Remove the account link?","The account will no longer see this node in its linked-node list. Your validator will keep running with the same keys and evidence history.","Remove account link"]
  }[action];
  el("pair-consent-title").textContent = copy[0];
  el("pair-consent-text").textContent = copy[1];
  el("pair-consent-confirm").textContent = copy[2];
  el("pair-consent-code").hidden = action !== "confirm";
  el("pair-consent-code").textContent = pairingConsent.comparison_code || "";
  el("pair-consent").returnValue = "";
  el("pair-consent").showModal();
}
el("pair-start").addEventListener("click", () => askPairing("start"));
el("pair-confirm").addEventListener("click", () => askPairing("confirm"));
el("pair-unlink").addEventListener("click", () => askPairing("unlink"));
el("pair-refresh").addEventListener("click", () => pairingAction({action:"refresh"}));
el("pair-cancel").addEventListener("click", () => pairingAction({action:"cancel",pairing_id:pairing.pairing_id}));
el("pair-consent").addEventListener("close", () => {
  const form = pairingConsent;
  pairingConsent = null;
  if (el("pair-consent").returnValue === "confirm" && form) pairingAction(form);
});
el("pair-consent").addEventListener("keydown", event => {
  if (event.key === "Escape") { event.preventDefault(); el("pair-consent").close("cancel"); }
});
async function refreshPairing() {
  if (closed || pairingBusy || !localAvailable) return;
  try {
    pairing = await request("/pairing.json");
    renderPairing();
    // Only resume reads of a deliberately started/recovered pending request.
    if (!pairing.busy && ["pending","approved"].includes(pairing.status) && pairing.expires_at * 1000 > Date.now() && Date.now() >= nextPairingCheck && !el("pair-consent").open) await pairingAction({action:"refresh"});
  } catch(error) { showError(error.message); }
}
el("updates-check").addEventListener("click", async () => {
  if (!localAvailable || closed || updateBusy || Date.now() < nextUpdateCheck) return;
  updateBusy = true;
  nextUpdateCheck = Date.now() + 30000;
  renderUpdates();
  try {
    updateState = await request("/updates", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"check"})});
  } catch (_) { updateState = {status:"unavailable"}; }
  finally { updateBusy = false; renderUpdates(); }
});
el("updates-install").addEventListener("click", () => {
  if (!localAvailable || closed || updateBusy || !updateState.install_supported || !["available","install_failed"].includes(updateState.status)) return;
  updateConsentTag = updateState.latest_tag;
  el("update-consent-tag").textContent = updateConsentTag;
  el("update-consent").returnValue = "";
  el("update-consent").showModal();
});
el("update-consent").addEventListener("close", async () => {
  const tag = updateConsentTag;
  updateConsentTag = null;
  if (el("update-consent").returnValue !== "confirm" || !tag || closed || !localAvailable || updateBusy) return;
  updateBusy = true;
  renderUpdates();
  try {
    updateState = await request("/updates", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"install",tag,accept_unsigned:true})});
  } catch (error) { showError(error.message); }
  finally { updateBusy = false; renderUpdates(); }
});
el("update-consent").addEventListener("keydown", event => {
  if (event.key === "Escape") { event.preventDefault(); el("update-consent").close("cancel"); }
});
async function refreshUpdates() {
  if (!localAvailable || closed || updateBusy) return;
  try { updateState = await request("/updates.json"); }
  catch (_) { updateState = {status:"unavailable"}; }
  renderUpdates();
}
const compensationLabels = {
  wallet_required:"Payout wallet needed", awaiting_wallet:"Waiting for wallet approval in Console",
  awaiting_node:"Wallet approved. Review the destination here.", review_required:"Awaiting maintainer review",
  ready_for_payment:"Recipient approved; payment not sent", pending:"Payment pending confirmation",
  sent:"Paid", manual_review:"Payment needs maintainer review", no_payment_due:"No payable work",
  cancelled:"Wallet setup cancelled", expired:"Wallet setup expired", recipient_bound:"Recipient approved",
  scheduled:"Scheduled", earning:"Pilot in progress", awaiting_finalization:"Work awaiting final review", finalized:"Finalized"
};
let compensation = {status:"idle",items:[],campaigns:[],request:null};
let compensationBusy = false;
let compensationConsent = null;
let nextCompensationCheck = 0;
function aipgAmount(value) {
  if (typeof value !== "string" || !/^(0|[1-9][0-9]{0,77})$/.test(value)) return "Unavailable";
  const atomic = BigInt(value), scale = 10n ** 18n;
  const fraction = (atomic % scale).toString().padStart(18,"0").replace(/0+$/,"");
  return `${atomic / scale}${fraction ? `.${fraction}` : ""} AIPG`;
}
function renderCompensation() {
  const disabled = closed || !localAvailable || !configured || compensationBusy || compensation.busy;
  const labels = {idle:"Not checked",ready:compensation.items?.length || compensation.campaigns?.length ? "Reviewed pilot participation" : "No approved compensation pilot for this node.",error:"Compensation unavailable"};
  el("comp-status").textContent = compensationBusy ? "Checking compensation..." : labels[compensation.status] || "Unavailable";
  el("comp-refresh").disabled = disabled;
  el("comp-error").hidden = !compensation.error;
  const errorLabels = {
    unavailable:"Compensation is not enabled or the Grid is unreachable. Your validator can keep running. Check again later.",
    registration_required:"Check this node's registration and Console account link, then retry. Keep this node's identity.",
    changed:"The request changed or may already have completed. Check compensation and reopen wallet setup before confirming.",
    invalid_contract:"The payout request could not be verified. Do not sign elsewhere to bypass this error; contact the maintainer.",
    expired:"Wallet setup expired. Check compensation and start a new wallet request; keep the same validator."
  };
  el("comp-error").textContent = errorLabels[compensation.error] || pairingErrors[compensation.error] || (compensation.error ? "Check compensation again. Your validator and stored identity are unchanged." : "");
  const campaigns = (compensation.campaigns || []).map(campaign => {
    const li = document.createElement("li"), text = document.createElement("div"), title = document.createElement("strong"), detail = document.createElement("small");
    title.textContent = `${campaign.campaign_id}: ${compensationLabels[campaign.status] || "Unknown"}`;
    detail.textContent = `${new Date(campaign.starts_at).toLocaleDateString()} - ${new Date(campaign.ends_at).toLocaleDateString()} | Cap ${aipgAmount(campaign.operator_cap_atomic)} (not earned)${campaign.identity_review_required ? " | Identity review required" : ""}`;
    text.append(title,detail); li.append(text); return li;
  });
  if (compensation.campaigns_has_more) { const li = document.createElement("li"); li.textContent = "Showing the latest 25 pilots."; campaigns.push(li); }
  el("comp-campaigns").replaceChildren(...campaigns);
  const items = (compensation.items || []).map(item => {
    const li = document.createElement("li"), text = document.createElement("div"), title = document.createElement("strong"), detail = document.createElement("small");
    title.textContent = `${aipgAmount(item.amount_atomic)} | ${compensationLabels[item.status] || "Unknown"}`;
    detail.textContent = `${item.campaign_id} | ${item.reviewed_units} reviewed work units`;
    text.append(title,detail); li.append(text);
    if (["wallet_required","expired","cancelled"].includes(item.status) && item.amount_atomic !== "0") {
      const button = document.createElement("button"); button.textContent = "Set payout wallet"; button.disabled = disabled;
      button.addEventListener("click",() => compensationAction({action:"start",allocation_hash:item.allocation_hash})); li.append(button);
    } else if (item.request_id && ["awaiting_wallet","awaiting_node","review_required"].includes(item.status)) {
      const button = document.createElement("button"); button.textContent = "Open wallet setup"; button.disabled = disabled;
      button.addEventListener("click",() => compensationAction({action:"inspect",request_id:item.request_id})); li.append(button);
    }
    if (typeof item.transaction_hash === "string" && /^0x[a-f0-9]{64}$/.test(item.transaction_hash)) {
      const link = document.createElement("a"); link.className = "button"; link.textContent = "View on BaseScan";
      link.href = `https://basescan.org/tx/${item.transaction_hash}`; link.target = "_blank"; link.rel = "noopener noreferrer"; li.append(link);
    }
    return li;
  });
  el("comp-items").replaceChildren(...items);
  el("comp-prev").hidden = !(compensation.offset > 0); el("comp-next").hidden = compensation.next_offset == null;
  el("comp-prev").disabled = el("comp-next").disabled = disabled;
  const current = compensation.request;
  el("comp-request").hidden = !current;
  if (!current) { if (el("comp-consent").open) el("comp-consent").close("cancel"); return; }
  const expired = current.expires_at && current.expires_at * 1000 <= Date.now();
  el("comp-request-status").textContent = expired ? compensationLabels.expired : compensationLabels[current.status] || "Unavailable";
  el("comp-amount").textContent = current.amount_atomic ? `${aipgAmount(current.amount_atomic)} on Base` : "";
  el("comp-recipient").textContent = current.recipient || "";
  el("comp-expiry").textContent = current.expires_at ? `Signing deadline: ${new Date(current.expires_at * 1000).toLocaleString()}` : "";
  const safeURL = typeof current.approval_url === "string" && /^https:\/\/console\.aipowergrid\.io\/dashboard\/validator-payout\/vpc_[a-f0-9]{64}$/.test(current.approval_url);
  el("comp-open").hidden = disabled || expired || current.status !== "awaiting_wallet" || !safeURL;
  if (safeURL) el("comp-open").href = current.approval_url; else el("comp-open").removeAttribute("href");
  el("comp-confirm").hidden = current.status !== "awaiting_node" || expired;
  el("comp-cancel").hidden = !["awaiting_wallet","awaiting_node"].includes(current.status) || expired;
  el("comp-confirm").disabled = el("comp-cancel").disabled = disabled;
  if (el("comp-consent").open && (disabled || expired || compensationConsent?.review_hash !== current.review_hash)) el("comp-consent").close("cancel");
}
async function compensationAction(form) {
  if (closed || !localAvailable || compensationBusy) return;
  compensationBusy = true; renderCompensation();
  try { compensation = await request("/compensation", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(form)}); }
  catch (error) { compensation = {status:"error",error:"unavailable",items:[],campaigns:[],request:null}; showError(error.message); }
  finally { compensationBusy = false; nextCompensationCheck = Date.now() + 6000; renderCompensation(); }
}
el("comp-refresh").addEventListener("click", () => compensationAction({action:"refresh",offset:0}));
el("comp-prev").addEventListener("click", () => compensationAction({action:"refresh",offset:Math.max(0,(compensation.offset || 0)-25)}));
el("comp-next").addEventListener("click", () => { if (compensation.next_offset != null) compensationAction({action:"refresh",offset:compensation.next_offset}); });
el("comp-cancel").addEventListener("click", () => { if (compensation.request) compensationAction({action:"cancel",request_id:compensation.request.request_id}); });
el("comp-confirm").addEventListener("click", () => {
  const current = compensation.request;
  if (closed || !localAvailable || compensationBusy || current?.status !== "awaiting_node") return;
  compensationConsent = {action:"confirm",request_id:current.request_id,review_hash:current.review_hash};
  el("comp-consent-amount").textContent = `${aipgAmount(current.amount_atomic)} on Base`;
  el("comp-consent-recipient").textContent = current.recipient;
  el("comp-consent-campaign").textContent = `Pilot: ${current.campaign_id}`;
  el("comp-consent").returnValue = ""; el("comp-consent").showModal();
});
el("comp-consent").addEventListener("close", () => {
  const form = compensationConsent; compensationConsent = null;
  if (el("comp-consent").returnValue === "confirm" && form) compensationAction(form);
});
el("comp-consent").addEventListener("keydown", event => { if (event.key === "Escape") { event.preventDefault(); el("comp-consent").close("cancel"); } });
async function refreshCompensation() {
  if (closed || !localAvailable || compensationBusy || el("comp-consent").open) return;
  try {
    compensation = await request("/compensation.json"); renderCompensation();
    const current = compensation.request;
    if (current && ["awaiting_wallet","awaiting_node"].includes(current.status) && current.expires_at * 1000 > Date.now() && Date.now() >= nextCompensationCheck && !compensation.busy) await compensationAction({action:"inspect",request_id:current.request_id});
  } catch (error) { showError(error.message); }
}
async function poll() { await refresh(); await refreshPairing(); await refreshUpdates(); await refreshCompensation(); if (!closed) setTimeout(poll,3000); }
poll();
