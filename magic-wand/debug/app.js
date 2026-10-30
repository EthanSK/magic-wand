// Magic Wand monitor page. Read-only: it only fetches /api/state from this local server.
// Everything here is presentation: plain wording for the receiver's own evidence.
"use strict";

const VISIBLE_POLL_MS = 1000;
const HIDDEN_POLL_MS = 5000;
const FAILED_POLL_MS = 2000;
const TIMELINE_ROWS = 160;

const LIGHT_COLOURS = {
  update: "orange", disconnected: "orange", calibration: "orange", scroll: "cyan", app: "green",
  staging: "purple", mouse: "blue", hud: "orange", recording: "red", idle: "off", sleep: "off", off: "off",
};
const LANE_NAMES = { speech: "Speech", hud: "HUD", review: "Review", mouse: "Pointer", scroll: "Scroll" };
const LANE_HELP = {
  speech: "The speech button starts and stops Agent Flow speech to text.",
  hud: "Hold the HUD button to show the HUD; release to use the outlined card.",
  review: "Review changes or Stage files in VS Code.",
  mouse: "Tap the mouse button to turn the pointer on or off. Double tap recenters.",
  scroll: "Hold the mouse button over a page to scroll, or over something draggable to drag.",
};
const BASIS = {
  light: ["from light", "Read from the wand’s light. A higher-priority light can hide this."],
  log: ["best guess", "Pieced together from Wand Receiver’s log."],
  receiver: ["live", "From Wand Receiver’s live snapshot."],
};
const HUD_REASONS = {
  "context ended": "By Agentic Mouse",
  "middle double click": "By HUD button double-click",
  "navigation timed out": "HUD button hold signal stopped",
  "context missing": "Agentic Mouse wasn’t showing it",
};
const HOLD_ENDS = {
  "motion button state": "Release seen in motion data",
  "sensor button state": "Release seen in sensor data",
  "all buttons released": "All buttons released",
  "button telemetry timeout": "Button signal stopped, so the hold was cancelled",
};
const FILTERS = [["key", "Key events"], ["buttons", "Buttons"], ["all", "Everything"]];
const BUTTON_CATEGORIES = new Set(["buttons", "hud", "review", "recording"]);

const $ = (id) => document.getElementById(id);
let skew = 0;            // browser clock minus server clock, in seconds
let lastOk = 0;
let filter = "key";
let state = null;
let timelineKey = "";
let timer = 0;

// --- small helpers --------------------------------------------------------

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "text") node.textContent = value;
    else if (key === "dataset") Object.assign(node.dataset, value);
    else node.setAttribute(key, value === true ? "" : String(value));
  }
  for (const child of children) if (child !== null && child !== undefined && child !== "") node.append(child);
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

function lightKey(light) {
  return light.mode === "app" && light.name !== "App review" ? "staging" : light.mode;
}

function lightPhrase(light) {
  const colour = LIGHT_COLOURS[lightKey(light)];
  return light.name + (colour && colour !== "off" ? " (" + colour + ")" : "");
}

// --- plain current state --------------------------------------------------

/** The big headline: what the wand is doing, in words. Connection problems keep the server's wording. */
function activity(s) {
  const h = s.headline;
  if (h.state !== "ready") return { title: h.title, tone: h.tone, sentence: h.detail || "" };
  const lane = (id) => s.lanes.find((item) => item.id === id) || {};
  const key = lightKey(s.light);
  let title = "Connected";
  let tone = "good";
  let sentence = "";
  if (s.power.state === "desk-idle") {
    title = "Desk Idle";
    tone = "sleep";
    sentence = "Resting on the desk with its lights off. Pick it up to wake it.";
  } else if (key === "mouse") {
    title = "Pointer On"; sentence = "The wand is moving the pointer.";
  } else if (key === "scroll") {
    title = "Scrolling"; sentence = "The mouse button is scrolling the page.";
  } else if (key === "hud") {
    title = "HUD Open"; sentence = "The HUD is open.";
  } else if (key === "app") {
    title = "App Review"; sentence = "App review is active.";
  } else if (key === "staging") {
    title = "File Staging"; sentence = "VS Code file staging is active.";
  } else if (key === "recording") {
    title = "Recording"; tone = "record"; sentence = "Agent Flow is recording speech. Pointer off, HUD closed.";
  } else if (key === "idle") {
    title = "Idle"; sentence = "Awake. Pointer off, HUD closed, not recording.";
  } else if (key === "calibration") {
    title = "Calibrating"; tone = "warn"; sentence = "Keep it still with no buttons pressed for two seconds.";
  } else if (key === "update") {
    title = "Updating"; tone = "warn"; sentence = "Wand Receiver is updating the wand’s code.";
  } else {
    sentence = "Connected and ready.";
  }
  if (lane("speech").tone === "on" && key !== "recording") sentence += " Agent Flow is recording speech.";
  if (s.power.state === "awake" && s.power.detail) sentence += " Resting on the desk.";
  if ((h.detail || "").includes("Deep sleep requested")) sentence += " Deep sleep requested.";
  return { title, tone, sentence };
}

/** Plain wording for one button lane. Unknown is explained, never guessed. */
function laneView(lane, s) {
  const on = lane.tone === "on";
  const off = lane.tone === "off";
  let value = lane.value;
  if (lane.id === "speech") value = on ? "Recording" : off ? "Not recording" : value;
  if (lane.id === "mouse") value = on ? "On" : off ? "Off" : value;
  if (lane.id === "scroll") value = on ? "Scrolling" : off ? "Not scrolling" : value;
  let note = lane.note;
  if (lane.tone === "unknown") {
    value = "Can’t tell";
    if (note && note.startsWith("The light shows")) note = "Hidden while the light shows " + lightPhrase(s.light) + ".";
    else if (lane.id === "review" && note) note = "No review activity since Wand Receiver started.";
    else if (lane.id === "speech") note = "Needs Wand Receiver running.";
    else if (s.headline.state !== "ready") note = "Needs a connected wand.";
  }
  let last = lane.last;
  if (last) {
    let label = last.label;
    if (label.startsWith("HUD closed (")) {
      const reason = HUD_REASONS[label.slice(12, -1)] || label.slice(12, -1);
      label = reason.startsWith("By ") ? "HUD closed by " + reason.slice(3) : "HUD closed: " + reason;
    } else if (label === "Mouse button") label = "Last click";
    else if (label.startsWith("Last hold: ")) label = label.includes("drag") ? "Last mouse button hold dragged" : "Last mouse button hold scrolled";
    last = { label, t: last.t };
  }
  return { id: lane.id, name: LANE_NAMES[lane.id] || lane.lane, help: LANE_HELP[lane.id] || "", value,
    tone: lane.tone, basis: BASIS[lane.basis] || null, since: lane.since, note, last };
}

// --- activity wording -----------------------------------------------------

function describeEvent(item) {
  const event = item.event;
  const detail = item.detail || null;
  const summary = item.summary || "";
  let title = summary;
  let text = detail;
  let key = false;
  let code = item.category === "diagnostic" || item.level === "error";
  switch (event) {
    case "STARTED": title = "Wand Receiver started"; key = true; break;
    case "STOPPING": title = "Wand Receiver stopping"; key = true; break;
    case "STOPPED": title = "Wand Receiver stopped"; key = true; break;
    case "ALREADY_RUNNING": title = "Second Wand Receiver launch ignored"; key = true; break;
    case "RADIO_STATE": key = item.level !== "info"; break;
    case "SCANNING_FOR_PUCK": title = "Looking for the wand"; break;
    case "CONNECTING": title = "Connecting to the wand"; break;
    case "CONNECTED_TO_PUCK": title = "Bluetooth connected"; text = "Loading the wand’s code next."; key = true; break;
    case "CHECKING_RUNTIME": title = "Checking the wand’s code"; text = null; break;
    case "UPLOADING_RUNTIME": title = "Uploading the wand’s code"; key = true; break;
    case "RUNTIME_READY": title = "Connected and ready"; key = true; break;
    case "DISCONNECTED": title = "Disconnected"; key = true; break;
    case "CONNECTION_TIMEOUT": title = "Couldn’t reach the wand; retrying"; key = true; break;
    case "DEEP_STANDBY_REQUESTED":
      title = "Deep sleep requested"; text = "Five minutes resting. A grip button wakes it; pickup alone can’t."; key = true; break;
    case "DEEP_STANDBY_RESUMED": title = "Woke from deep sleep"; key = true; break;
    case "POWER_POLICY_READY": title = "Sleep rules loaded on the wand"; break;
    case "DESK_SLEEP": title = "Desk idle: lights off"; text = "Still connected. Picking it up wakes it."; key = true; break;
    case "DESK_WAKE": title = "Woke from desk idle"; key = true; break;
    case "TABLE_REST_CONFIRMED": title = "Put down on the desk"; key = true; break;
    case "AUTO_PICKUP": title = "Picked up: pointer back on"; key = true; break;
    case "AUTO_PICKUP_KEPT_STATE":
      title = "Picked up";
      text = detail === "Pointer on" ? "Pointer stays on" : detail === "Pointer off" ? "Pointer stays off" : detail;
      key = true; break;
    case "AUTO_PUT_DOWN": title = "Put down: pointer paused"; key = true; break;
    case "DEVICE_LIGHT": {
      const mode = summary.replace(/^Light: /, "");
      const colour = { Pointer: "blue", Scrolling: "cyan", HUD: "orange", Recording: "red", "App review": "green",
        Updating: "orange", Disconnected: "orange", Calibrating: "orange", Sleeping: "off", Idle: "off" }[mode];
      title = "Light: " + mode + (colour ? " (" + colour + ")" : "");
      break;
    }
    case "RECORDING_STATE":
      title = summary === "Recording started" ? "Agent Flow started recording" : "Agent Flow stopped recording"; key = true; break;
    case "SPEECH_BUTTON":
      title = summary.startsWith("Speech button pressed") ? "Speech button pressed" : "Speech button released";
      text = item.level === "warn" ? "Agent Flow wasn’t available" : null;
      key = item.level === "warn"; break;
    case "HUD_CLOSED": title = "HUD closed"; text = HUD_REASONS[detail] || detail; key = true; break;
    case "HUD_HOLD_RELEASED": title = "HUD card used"; text = "Released HUD button"; key = true; break;
    case "HUD_TAP_USED": title = "HUD card used"; text = "Tapped HUD button"; key = true; break;
    case "POINTER_MODE_ENTERED": title = "Pointer mode"; break;
    case "POINTER_RECENTER": title = "Pointer recentered"; text = "Mouse button double tap"; key = true; break;
    case "HIGH_DWELL_CLICK": title = "Clicked by holding still"; break;
    // BOTTOM_HOLD_* are the receiver log's legacy tags for the mouse button.
    case "BOTTOM_HOLD_TARGET": {
      const target = summary.replace(/^Mouse button hold: /, "");
      if (target === "drag") title = "Mouse button held: dragging";
      else if (target === "tap-then-hold drag") title = "Mouse button tap-then-hold: dragging";
      else title = "Mouse button held: scrolling";
      if (target.startsWith("late")) text = "The target check finished late, so it kept scrolling.";
      if (target.startsWith("unknown")) text = "Target unknown, so it kept scrolling.";
      key = true; break;
    }
    case "BOTTOM_HOLD_RECOVERED": title = "Mouse button hold ended"; text = HOLD_ENDS[detail] || detail; break;
    case "SCROLL_BEGIN": title = "Scroll chord started"; break;
    case "SCROLL_END": title = "Scroll chord ended"; break;
    case "SCROLL_FINISHED_MOUSE_ON": title = "Scrolling stopped: pointer back on"; break;
    case "WAND_REVIEW_SHORTCUT": case "WAND_REVIEW_EXIT": case "WAND_REVIEW_COMMIT": key = true; break;
    case "RAW_DELIVERY": {
      const match = summary.match(/(\d+) in ([\d.]+) s/);
      if (match) title = "Motion data: " + (Number(match[1]) / Number(match[2])).toFixed(1) + " updates a second";
      text = detail ? detail.replace("max gap", "longest gap") : null;
      break;
    }
    case "MOVEMENT_REPORTS_POSTED": title = summary.replace("Pointer moves posted: ", "Pointer moves so far: "); break;
    case "WAND_CALIBRATED": title = "Calibrated"; text = null; key = true; break;
    case "KNOWN_CALIBRATION_RESTORE_REQUESTED": title = "Restoring saved calibration"; break;
    case "KNOWN_CALIBRATION_SAVED": key = true; break;
    case "DEVICE_ERROR":
      if (item.level === "error") { title = "Wand code error"; key = true; }
      else title = "Echoed wand code (not an error)";
      break;
    case "DEVICE": title = summary === "Device diagnostic" ? "Wand diagnostic" : summary; break;
    // The receiver logs the rotation setting at every start; a menu change also logs OPTION_CHANGED.
    case "OPTION_CHANGED": case "CONTROL_VERSION": case "ACCESSIBILITY": key = true; break;
    default: break;
  }
  if (item.level === "error") key = true;
  if (item.category === "recording" && event === "DEVICE") code = false;
  return { t: item.t, event, category: item.category, level: item.level, title, detail: text, key, code };
}

function isButton(item, edge) { return item && item.event === "BUTTON" && item.title.endsWith(" " + edge); }

/** Newest first. Merge a click (down, up, optional stop-to-click marker) or a quick speech button tap into one row. */
function mergeClicks(items) {
  const out = [];
  for (let i = 0; i < items.length; i += 1) {
    const a = items[i];
    const b = items[i + 1];
    const c = items[i + 2];
    if (a.event === "HIGH_DWELL_CLICK" && isButton(b, "up") && isButton(c, "down") && a.t - c.t <= 1) {
      out.push({ ...a, title: "Clicked by holding still", category: "buttons" });
      i += 2;
    } else if (isButton(a, "up") && isButton(b, "down") && a.t - b.t <= 1 && a.title.split(" ")[0] === b.title.split(" ")[0]) {
      out.push({ ...a, title: a.title.split(" ")[0] + " click" });
      i += 1;
    } else if (a.title === "Speech button released" && b && b.title === "Speech button pressed" && !a.detail && !b.detail && a.t - b.t <= 1.5) {
      out.push({ ...a, title: "Speech button tapped" });
      i += 1;
    } else {
      out.push(a);
    }
  }
  return out;
}

/** Collapse back-to-back repeats (within two minutes) into one row with a count. */
function collapseRepeats(items) {
  const out = [];
  for (const item of items) {
    const prev = out[out.length - 1];
    if (prev && prev.title === item.title && (prev.detail || "") === (item.detail || "") && prev.oldest - item.t <= 120) {
      prev.count += 1;
      prev.oldest = item.t;
    } else {
      out.push({ ...item, count: 1, oldest: item.t });
    }
  }
  return out;
}

function prepareTimeline(timeline, view) {
  // The recording light echoes Agent Flow's own start/stop, so Buttons shows only the latter.
  // Merge after filtering: light changes often land between a press and its release.
  const chosen = timeline.map(describeEvent).filter((item) => view === "all" ||
    (view === "key" ? item.key : (BUTTON_CATEGORIES.has(item.category) && item.event !== "DEVICE") || item.event === "HIGH_DWELL_CLICK"));
  return collapseRepeats(mergeClicks(chosen)).slice(0, TIMELINE_ROWS);
}

/** Errors that recurred during this connection, and older ones kept for reference. */
function splitErrors(s) {
  const groups = (s.errors && s.errors.groups) || [];
  const boundary = (s.headline.state === "ready" && s.headline.since) || s.receiver.startedAt || null;
  if (!boundary) return { boundary: null, current: groups, earlier: [] };
  return { boundary, current: groups.filter((g) => g.last >= boundary), earlier: groups.filter((g) => g.last < boundary) };
}

// --- rendering ------------------------------------------------------------

function tick() {
  for (const node of document.querySelectorAll("[data-t]")) setText(node, ago(Number(node.dataset.t)));
  for (const node of document.querySelectorAll("[data-d]")) setText(node, span(Number(node.dataset.d)));
  const feed = $("feed");
  if (lastOk && Date.now() - lastOk > 4000 && feed.dataset.state !== "down") {
    feed.dataset.state = "down";
    setText(feed, "Monitor stopped · run python3 debug/server.py");
  }
}

function renderHeadline(s) {
  const now = activity(s);
  document.body.dataset.tone = now.tone;
  setText($("headline"), now.title);
  setText($("headline-detail"), now.sentence);
  if (document.title !== now.title + " · Magic Wand") document.title = now.title + " · Magic Wand";

  const h = s.headline;
  const pills = [];
  if (h.state === "ready") {
    pills.push(el("span", { class: "pill good" }, "Connected", h.since ? el("span", { class: "pill-time" }, " · ", lasting(h.since)) : null));
    pills.push(el("span", { class: "pill" }, s.power.label));
    if (s.battery && s.battery.state === "reported") pills.push(el("span", { class: "pill", title: "Estimated from voltage" }, "Battery about " + s.battery.percent + "%"));
  } else if (h.since) {
    pills.push(el("span", { class: "pill" }, "For ", lasting(h.since)));
  }
  $("status-row").replaceChildren(...pills);

  const process = { running: "Running", unverified: "Running (name unchecked)", stopped: "Stopped", other: "Stopped", unknown: "Unknown" }[s.receiver.process] || "Unknown";
  setText($("fresh-process"), process);
  const last = s.sources.log.lastEventAt;
  $("fresh-log").replaceChildren(last ? relative(last) : document.createTextNode(s.sources.log.present ? "None yet" : "No log file"));
}

function laneItem(view) {
  const value = el("span", { class: "lane-value", text: view.value });
  const head = el("div", { class: "lane-head" }, el("span", { class: "lane-name", text: view.name }), value);
  const meta = el("p", { class: "lane-meta" });
  const bits = [];
  if (view.basis && view.tone !== "unknown") bits.push(el("span", { class: "basis", title: view.basis[1], text: view.basis[0] }));
  if (view.since) bits.push(el("span", {}, "for ", lasting(view.since)));
  if (view.note) bits.push(el("span", { text: view.note }));
  if (view.last) bits.push(el("span", {}, view.last.label + " ", relative(view.last.t)));
  bits.forEach((bit, index) => { if (index) meta.append(" · "); meta.append(bit); });
  return el("li", { class: "lane", dataset: { lane: view.id, tone: view.tone } },
    head, el("p", { class: "lane-help", text: view.help }), meta);
}

function renderLanes(s) {
  for (const list of document.querySelectorAll(".lanes")) {
    const items = s.lanes.filter((lane) => lane.button === list.dataset.button).map((lane) => laneItem(laneView(lane, s)));
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
  if (detail) {
    node.append(detail);
    if (s.power.since) node.append(" For ", lasting(s.power.since), ".");
  } else if (s.power.since) {
    node.append(s.power.label + " for ", lasting(s.power.since), ".");
  }
}

function renderLight(s) {
  const light = s.light;
  document.body.dataset.light = lightKey(light);
  setText($("light-name"), light.name);
  setText($("light-detail"), light.detail || "");
  fillFacts($("light-facts"), [["Showing for", light.since ? lasting(light.since) : null]]);
}

function renderDelivery(s) {
  const latest = s.delivery.latest;
  const rate = $("delivery-rate");
  setText(rate, latest ? latest.rate + " updates a second" : "Not measured yet");
  // A measurement from minutes ago is history: dim it so it doesn't read as live.
  rate.dataset.old = latest && serverNow() - latest.t > 60 ? "true" : "false";
  const history = s.delivery.history || [];
  const peak = Math.max(1, ...history.map((d) => d.rate));
  $("delivery-bars").replaceChildren(...history.map((d) => {
    const bar = el("span", { title: d.rate + " a second at " + clock(d.t) + ", longest gap " + d.maxGapMs + " ms" });
    bar.style.height = Math.max(6, Math.round((d.rate / peak) * 100)) + "%"; // CSSOM, allowed by the page's CSP
    return bar;
  }));
  fillFacts($("delivery-facts"), [
    ["Longest gap", latest && typeof latest.maxGapMs === "number" ? latest.maxGapMs.toLocaleString() + " ms" : null],
    ["Measured", latest ? relative(latest.t) : null, latest ? "over " + latest.seconds.toFixed(1) + " s" : null],
    ["Pointer moves", s.movement ? s.movement.total.toLocaleString() + "+" : null, s.movement ? "since Wand Receiver started" : null],
  ]);
}

function renderSettings(s) {
  const st = s.settings;
  if (!st) { fillFacts($("settings-facts"), [["Settings", "Not reported"]]); return; }
  const trace = st.reviewTrace || {};
  let capture = onOff(trace.enabled);
  if (trace.enabled && trace.dropped) capture += " · " + trace.dropped + " dropped";
  if (trace.diskError) capture += " · can’t write to disk";
  fillFacts($("settings-facts"), [
    ["Control version", st.controlVersion || "Not reported"],
    ["Rotation-independent controls", onOff(st.orientationCompensation)],
    ["Flick to scroll", onOff(st.flickScroll)],
    ["Review with nods and shakes", onOff(st.reviewAxisGestures)],
    ["Review gesture capture", capture],
  ]);
}

function renderReceiver(s) {
  const r = s.receiver;
  const pub = r.published || {};
  const running = r.version ? r.version + (r.build ? " (build " + r.build + ")" : "") : null;
  const source = pub.receiver ? pub.receiver + (pub.receiverBuild ? " (build " + pub.receiverBuild + ")" : "") : null;
  fillFacts($("receiver-facts"), [
    ["Installed", running || (r.process === "running" ? "Not found" : null)],
    ["This checkout", running && source && running !== source ? source : null, "differs from installed"],
    ["Wand code", r.deviceCode || pub.deviceRuntime],
    ["Started", r.startedAt ? relative(r.startedAt) : null],
    ["Sleep rules loaded", r.powerPolicyReadyAt ? relative(r.powerPolicyReadyAt) : null],
    ["Calibrated", r.calibratedAt ? relative(r.calibratedAt) : null],
    ["Accessibility", r.accessibility === true ? "Allowed" : r.accessibility === false ? "Not allowed" : null],
    ["Bluetooth", r.bluetooth],
    batteryRow(s.battery),
  ]);
}

/** Battery is a voltage estimate with a measurement time; an old reading is never shown as current. */
function batteryRow(battery) {
  if (!battery || battery.state === "not-reported" || typeof battery.percent !== "number") {
    return ["Battery", "Not reported", battery && battery.detail ? battery.detail : null];
  }
  const reading = el("span", {}, "About " + battery.percent + "%" + (typeof battery.volts === "number" ? " · " + battery.volts.toFixed(2) + " V" : ""));
  const when = typeof battery.measuredAt === "number" ? battery.measuredAt : null;
  const hint = el("small", {}, battery.state === "stale" ? "last reading, not current · " : "voltage estimate · measured ", when ? relative(when) : "");
  reading.append(" ", hint);
  return ["Battery", reading];
}

function errorItem(g) {
  return el("li", {},
    el("span", { class: "kind", text: g.kind === "Device" ? "Wand code" : "Wand Receiver" }),
    el("span", { class: "summary", text: g.summary }),
    el("span", { class: "count", text: g.count > 1 ? "×" + g.count : "" }),
    el("span", { class: "when" }, "Last ", relative(g.last), g.count > 1 ? " · first " + clock(g.first) : ""));
}

function renderErrors(s) {
  const { boundary, current, earlier } = splitErrors(s);
  const list = $("errors");
  const scope = s.headline.state === "ready" && s.headline.since ? "since connecting" : "since Wand Receiver started";
  document.body.dataset.errors = current.length ? "yes" : "no";
  if (current.length) {
    list.replaceChildren(...current.map(errorItem));
  } else {
    list.replaceChildren(el("li", { class: "empty" }, boundary ? "No errors " + scope + " " : "No errors in the recent log.",
      boundary ? relative(boundary) : null, boundary ? "." : null));
  }
  const older = $("errors-earlier");
  older.hidden = !earlier.length;
  setText($("errors-earlier-label"), earlier.length === 1 ? "1 earlier error, before then" : earlier.length + " earlier errors, before then");
  $("errors-earlier-list").replaceChildren(...earlier.map(errorItem));
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
  const head = s.timeline[0];
  const key = filter + "|" + s.timeline.length + "|" + (head ? head.t + head.event + head.summary : "");
  if (key === timelineKey) return;
  timelineKey = key;
  const items = prepareTimeline(s.timeline, filter);
  const list = $("timeline");
  if (!items.length) {
    const empty = filter === "key" ? "No key events in the recent log. Everything shows the rest." : "No activity in the recent log.";
    list.replaceChildren(el("li", { class: "empty", text: empty }));
    return;
  }
  list.replaceChildren(...items.map((item) => el("li", { dataset: { cat: item.category, level: item.level } },
    el("time", { datetime: new Date(item.t * 1000).toISOString(), text: clock(item.t) }),
    el("span", { class: "dot", "aria-hidden": "true" }),
    el("span", { class: "what" },
      el("span", { class: "summary", text: item.title }),
      item.count > 1 ? el("span", { class: "repeat", title: item.count + " times since " + clock(item.oldest), "aria-label": item.count + " times", text: "×" + item.count }) : null,
      el("span", { class: "ago", dataset: { t: String(item.t) }, text: ago(item.t) }),
      item.detail ? el("span", { class: item.code ? "detail code" : "detail", text: item.detail }) : null))));
}

function renderRaw(s) {
  const src = s.sources;
  const log = src.log;
  const levels = Array.isArray(s.light.levels) ? "red " + s.light.levels[0] + " · green " + s.light.levels[1] + " · blue " + s.light.levels[2] : null;
  fillFacts($("sources"), [
    ["Status file", src.status.present ? (src.status.valid ? "Readable" : "Unreadable: " + (src.status.error || "unknown")) : "Missing"],
    ["Status last changed", src.status.changedAt ? relative(src.status.changedAt) : null, "it changes only when state changes, so its age isn’t a heartbeat"],
    ["Receiver process", { running: "Running", unverified: "Running, name unchecked", stopped: "Stopped", other: "Not Wand Receiver", unknown: "Unknown" }[src.process.state] || src.process.state],
    ["Log", log.present ? log.lines.toLocaleString() + " lines read" : "Missing",
      log.present ? log.unparsed + " unreadable · " + log.rotationsSeen + " rotations seen" + (log.bytesSkipped ? " · " + log.bytesSkipped + " bytes skipped" : "") : null],
    ["Log covers", log.firstEventAt ? clock(log.firstEventAt) + " to " + clock(log.lastEventAt) : null],
    ["LED brightness", levels],
    ["Echoed wand code", s.errors.echoes ? s.errors.echoes + (s.errors.echoes === 1 ? " line" : " lines") : null,
      s.errors.echoes ? "mentions Error but isn’t a failure" : null],
    ["Hidden rest samples", log.hiddenRestSamples || null],
    ["Receiver snapshot", src.debug.present ? (src.debug.used ? "In use" : "Ignored: " + src.debug.reason) : "Not provided", src.debug.present ? null : "optional debug.json"],
  ]);
  setText($("raw-status"), s.raw.status ? JSON.stringify(s.raw.status, null, 2) : "Not available");
  setText($("raw-log"), s.raw.log.length ? s.raw.log.slice().reverse().join("\n") : "No log lines read");
}

function render(s) {
  state = s;
  renderHeadline(s);
  renderLanes(s);
  renderPower(s);
  renderLight(s);
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
    setText(feed, "Live");
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
