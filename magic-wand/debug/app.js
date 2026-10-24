// Magic Wand monitor page. Read-only: it only fetches /api/state from this local server.
"use strict";

const VISIBLE_POLL_MS = 1000;
const HIDDEN_POLL_MS = 5000;
const FAILED_POLL_MS = 2000;
const BASIS = {
  status: ["Status", "From Wand Receiver’s status file"],
  light: ["Light", "From the wand’s light report: a higher-priority light can hide this lane"],
  log: ["Log", "Best effort from Wand Receiver’s log"],
  receiver: ["Receiver", "From Wand Receiver’s live snapshot"],
};
const FILTERS = [
  ["all", "All"], ["connection", "Connection"], ["sleep", "Sleep"], ["buttons", "Buttons"], ["hud", "HUD"],
  ["review", "Review"], ["recording", "Recording"], ["light", "Light"], ["motion", "Motion"], ["error", "Errors"],
  ["diagnostic", "Diagnostics"],
];
const FILTER_GROUPS = { maintenance: "diagnostic", settings: "diagnostic" };

const $ = (id) => document.getElementById(id);
let skew = 0;            // browser clock minus server clock, in seconds
let lastOk = 0;
let filter = "all";
let state = null;
let timelineKey = "";
let timer = 0;

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "text") node.textContent = value;
    else if (key === "dataset") Object.assign(node.dataset, value);
    else node.setAttribute(key, value === true ? "" : String(value));
  }
  for (const child of children) if (child !== null && child !== undefined) node.append(child);
  return node;
}

function setText(node, text) {
  const value = text ?? "";
  if (node.textContent !== value) node.textContent = value;
}

function serverNow() { return Date.now() / 1000 - skew; }

function ago(t) {
  if (typeof t !== "number") return "";
  const s = Math.max(0, serverNow() - t);
  if (s < 5) return "just now";
  if (s < 60) return Math.floor(s) + " s ago";
  if (s < 3600) return Math.floor(s / 60) + " min ago";
  if (s < 86400) return Math.floor(s / 3600) + " h " + Math.floor((s % 3600) / 60) + " min ago";
  return Math.floor(s / 86400) + " d ago";
}

function span(t) {
  if (typeof t !== "number") return "";
  const s = Math.max(0, serverNow() - t);
  if (s < 60) return Math.floor(s) + " s";
  if (s < 3600) return Math.floor(s / 60) + " min";
  if (s < 86400) return Math.floor(s / 3600) + " h " + Math.floor((s % 3600) / 60) + " min";
  return Math.floor(s / 86400) + " d";
}

function clock(t) {
  return new Date(t * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
}

function relative(t) { return el("span", { class: "rel", dataset: { t: String(t) }, text: ago(t) }); }

function lasting(t) { return el("span", { class: "rel", dataset: { d: String(t) }, text: span(t) }); }

function onOff(value, on = "On", off = "Off") { return value === true ? on : value === false ? off : "Not reported"; }

function fillFacts(node, rows) {
  const fragment = document.createDocumentFragment();
  for (const [label, value, hint] of rows) {
    if (value === null || value === undefined || value === "") continue;
    const dd = el("dd");
    if (value instanceof Node) dd.append(value); else dd.textContent = String(value);
    if (hint) dd.append(" ", el("small", { text: hint }));
    fragment.append(el("dt", { text: label }), dd);
  }
  node.replaceChildren(fragment);
}

function tick() {
  for (const node of document.querySelectorAll("[data-t]")) setText(node, ago(Number(node.dataset.t)));
  for (const node of document.querySelectorAll("[data-d]")) setText(node, span(Number(node.dataset.d)));
  const feed = $("feed");
  if (lastOk && Date.now() - lastOk > 4000 && feed.dataset.state !== "down") {
    feed.dataset.state = "down";
    setText(feed, "Monitor stopped · run python3 debug/server.py");
  }
}

// --- rendering ------------------------------------------------------------

function renderHeadline(s) {
  const h = s.headline;
  document.body.dataset.tone = h.tone;
  setText($("headline"), h.title);
  setText($("headline-detail"), h.detail || "");
  $("headline-since").replaceChildren(...(h.since ? ["For ", lasting(h.since)] : []));
  if (document.title !== h.title + " · Magic Wand") document.title = h.title + " · Magic Wand";

  const process = { running: "Running", unverified: "Found, name unchecked", stopped: "Stopped", other: "Not Wand Receiver", unknown: "Unknown" }[s.receiver.process] || "Unknown";
  setText($("fresh-process"), process + (s.sources.process.checkedAt ? " · checked " + ago(s.sources.process.checkedAt) : ""));
  const changed = s.sources.status.changedAt;
  $("fresh-status").replaceChildren(changed ? relative(changed) : document.createTextNode(s.sources.status.present ? "Unknown" : "No status file"));
  const last = s.sources.log.lastEventAt;
  $("fresh-log").replaceChildren(last ? relative(last) : document.createTextNode(s.sources.log.present ? "No events yet" : "No log file"));
}

function renderLight(s) {
  const light = s.light;
  let key = light.mode;
  if (key === "app" && light.name !== "App review") key = "staging";
  document.body.dataset.light = key;
  setText($("light-name"), light.name);
  setText($("light-detail"), light.detail || "");
  const levels = Array.isArray(light.levels) ? "R " + light.levels[0] + " · G " + light.levels[1] + " · B " + light.levels[2] : null;
  fillFacts($("light-facts"), [
    ["Showing for", light.since ? lasting(light.since) : null],
    ["LED levels", levels],
    ["Source", light.basis === "status" ? "Receiver status" : light.basis === "log" ? "Receiver log" : null],
  ]);
}

function laneItem(lane) {
  const value = el("span", { class: "lane-value" }, lane.value);
  const basis = BASIS[lane.basis];
  if (basis && lane.tone !== "unknown") value.append(el("span", { class: "basis", title: basis[1], text: basis[0] }));
  const meta = el("span", { class: "lane-meta" });
  const bits = [];
  if (lane.since) bits.push(["for ", lane.since, true]);
  if (lane.note) bits.push([lane.note, null]);
  if (lane.last) bits.push([lane.last.label + " ", lane.last.t]);
  bits.forEach(([text, t, duration], index) => {
    if (index) meta.append(" · ");
    meta.append(text);
    if (t) meta.append(duration ? lasting(t) : relative(t));
  });
  return el("li", { class: "lane", dataset: { lane: lane.id, tone: lane.tone } },
    el("span", { class: "lane-name", text: lane.lane }), value, meta);
}

function renderLanes(s) {
  for (const list of document.querySelectorAll(".lanes")) {
    const items = s.lanes.filter((lane) => lane.button === list.dataset.button).map(laneItem);
    list.replaceChildren(...items);
  }
}

function renderPower(s) {
  for (const step of document.querySelectorAll("#track li[data-step]")) {
    if (step.dataset.step === s.power.state) step.setAttribute("aria-current", "step");
    else step.removeAttribute("aria-current");
  }
  const node = $("power-detail");
  node.replaceChildren();
  const detail = s.power.detail || "";
  node.append(detail);
  if (s.power.since) node.append((detail ? " " : "") + "For ", lasting(s.power.since), ".");
}

function renderDelivery(s) {
  const latest = s.delivery.latest;
  setText($("delivery-rate"), latest ? latest.rate + " reports/s" : "Not logged yet");
  const history = s.delivery.history || [];
  const peak = Math.max(1, ...history.map((d) => d.rate));
  $("delivery-bars").replaceChildren(...history.map((d) => {
    const bar = el("span", { title: d.rate + "/s at " + clock(d.t) + ", max gap " + d.maxGapMs + " ms" });
    bar.style.height = Math.max(6, Math.round((d.rate / peak) * 100)) + "%"; // CSSOM, allowed by the page's CSP
    return bar;
  }));
  fillFacts($("delivery-facts"), [
    ["Max gap", latest && typeof latest.maxGapMs === "number" ? latest.maxGapMs.toLocaleString() + " ms" : null],
    ["Window", latest ? latest.reports + " reports in " + latest.seconds.toFixed(2) + " s" : null],
    ["Measured", latest ? relative(latest.t) : null],
    ["Pointer moves", s.movement ? s.movement.total.toLocaleString() : null, s.movement ? "logged every 100 since receiver start" : null],
  ]);
}

function renderSettings(s) {
  const st = s.settings;
  if (!st) { fillFacts($("settings-facts"), [["Settings", "Not reported"]]); return; }
  const trace = st.reviewTrace || {};
  let capture = onOff(trace.enabled);
  if (trace.enabled) capture += " · " + (trace.buffered ?? 0) + " buffered · " + (trace.dropped ?? 0) + " dropped";
  if (trace.diskError) capture += " · disk error";
  fillFacts($("settings-facts"), [
    ["Control version", st.controlVersion || "Not reported"],
    ["Rotation-independent controls", onOff(st.orientationCompensation)],
    ["Flick to scroll", onOff(st.flickScroll)],
    ["Review with nods and shakes", onOff(st.reviewAxisGestures)],
    ["Review capture", capture],
  ]);
}

function renderReceiver(s) {
  const r = s.receiver;
  const pub = r.published || {};
  const running = r.version ? r.version + (r.build ? " (" + r.build + ")" : "") : null;
  const source = pub.receiver ? pub.receiver + (pub.receiverBuild ? " (" + pub.receiverBuild + ")" : "") : null;
  fillFacts($("receiver-facts"), [
    ["Running version", running || (r.process === "running" ? "Not found" : null)],
    ["Source version", source, running && source && running !== source ? "differs from running" : null],
    ["Device code", r.deviceCode || pub.deviceRuntime, r.deviceCode ? "from log" : pub.deviceRuntime ? "published" : null],
    ["Accessibility", r.accessibility === true ? "Allowed" : r.accessibility === false ? "Not allowed" : null],
    ["Bluetooth", r.bluetooth],
    ["Battery", "Not reported", s.battery.detail],
    ["Started", r.startedAt ? relative(r.startedAt) : null],
    ["Power policy ready", r.powerPolicyReadyAt ? relative(r.powerPolicyReadyAt) : null],
    ["Calibrated", r.calibratedAt ? relative(r.calibratedAt) : null],
  ]);
}

function renderErrors(s) {
  const groups = s.errors.groups || [];
  const list = $("errors");
  if (!groups.length) {
    list.replaceChildren(el("li", { class: "empty", text: "No errors in the recent log." }));
  } else {
    list.replaceChildren(...groups.map((g) => el("li", {},
      el("span", { class: "kind", text: g.kind }),
      el("span", { class: "summary", text: g.summary }),
      el("span", { class: "count", text: g.count > 1 ? "×" + g.count : "" }),
      el("span", { class: "when" }, "Last ", relative(g.last), g.count > 1 ? " · first " + clock(g.first) : ""))));
  }
  const note = $("echo-note");
  note.replaceChildren();
  if (s.errors.echoes) {
    const lines = s.errors.echoes === 1 ? "1 echoed code line that mentions" : s.errors.echoes + " echoed code lines that mention";
    note.append("Ignored " + lines + " Error; echoed code isn’t a failure. Last ", relative(s.errors.lastEchoAt), ".");
  }
}

function renderFilters() {
  const group = $("filters");
  if (group.childElementCount) return;
  for (const [id, label] of FILTERS) {
    const button = el("button", { type: "button", "aria-pressed": id === filter ? "true" : "false", dataset: { filter: id }, text: label });
    button.addEventListener("click", () => {
      filter = id;
      for (const other of group.children) other.setAttribute("aria-pressed", other.dataset.filter === id ? "true" : "false");
      timelineKey = "";
      if (state) renderTimeline(state);
    });
    group.append(button);
  }
}

function renderTimeline(s) {
  const items = s.timeline.filter((item) => filter === "all" || (FILTER_GROUPS[item.category] || item.category) === filter);
  const key = filter + "|" + items.length + "|" + (items[0] ? items[0].t + items[0].event + items[0].summary : "");
  if (key === timelineKey) return;
  timelineKey = key;
  const list = $("timeline");
  if (!items.length) {
    list.replaceChildren(el("li", { class: "empty", text: filter === "all" ? "No activity in the log yet." : "No matching activity in the recent log." }));
    return;
  }
  list.replaceChildren(...items.map((item) => el("li", { dataset: { cat: item.category, level: item.level } },
    el("time", { datetime: new Date(item.t * 1000).toISOString(), text: clock(item.t) }),
    el("span", { class: "dot", "aria-hidden": "true" }),
    el("span", { class: "what" },
      el("span", { class: "summary", text: item.summary }),
      el("span", { class: "ago", dataset: { t: String(item.t) }, text: ago(item.t) }),
      item.detail ? el("span", { class: "detail", text: item.detail }) : null))));
}

function renderRaw(s) {
  const src = s.sources;
  const log = src.log;
  fillFacts($("sources"), [
    ["status.json", src.status.present ? (src.status.valid ? "Valid" : "Unreadable: " + (src.status.error || "unknown")) : "Missing",
      src.status.present ? "changes only when state changes" : null],
    ["Receiver process", src.process.state],
    ["Log", log.present ? log.lines.toLocaleString() + " lines read" : "Missing",
      log.present ? log.unparsed + " unparsed · " + log.rotationsSeen + " rotations seen" + (log.bytesSkipped ? " · " + log.bytesSkipped + " bytes skipped" : "") : null],
    ["Log covers", log.firstEventAt ? clock(log.firstEventAt) + " to " + clock(log.lastEventAt) : null],
    ["Hidden rest samples", log.hiddenRestSamples || null],
    ["Receiver snapshot", src.debug.present ? (src.debug.used ? "In use" : "Ignored: " + src.debug.reason) : "Not provided", src.debug.present ? null : "optional debug.json"],
  ]);
  setText($("raw-status"), s.raw.status ? JSON.stringify(s.raw.status, null, 2) : "Not available");
  setText($("raw-log"), s.raw.log.length ? s.raw.log.slice().reverse().join("\n") : "No log lines read");
}

function render(s) {
  state = s;
  renderHeadline(s);
  renderLight(s);
  renderLanes(s);
  renderPower(s);
  renderDelivery(s);
  renderSettings(s);
  renderReceiver(s);
  renderErrors(s);
  renderTimeline(s);
  renderRaw(s);
}

// --- polling --------------------------------------------------------------

async function poll() {
  clearTimeout(timer);
  let delay = document.hidden ? HIDDEN_POLL_MS : VISIBLE_POLL_MS;
  try {
    const response = await fetch("/api/state", { cache: "no-store", headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("HTTP " + response.status);
    const s = await response.json();
    skew = Date.now() / 1000 - s.now;
    lastOk = Date.now();
    const feed = $("feed");
    feed.dataset.state = "live";
    setText(feed, "Monitor live");
    render(s);
  } catch (error) {
    delay = FAILED_POLL_MS;
    const feed = $("feed");
    feed.dataset.state = "down";
    setText(feed, "Monitor stopped · run python3 debug/server.py");
  }
  timer = setTimeout(poll, delay);
}

document.addEventListener("visibilitychange", () => { if (!document.hidden) poll(); });
document.addEventListener("DOMContentLoaded", () => {
  renderFilters();
  poll();
  setInterval(tick, 1000);
});
