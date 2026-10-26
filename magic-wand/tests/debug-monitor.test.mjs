// Read-only Magic Wand monitor (debug/): parser, freshness, rotation, privacy and endpoint checks.
// Every fixture is synthetic and lives in a temporary folder; no receiver files are read.
import { test, after } from "node:test";
import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { mkdtempSync, writeFileSync, appendFileSync, renameSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, basename, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import http from "node:http";
import vm from "node:vm";

const component = join(dirname(fileURLToPath(import.meta.url)), "..");
const debugDir = join(component, "debug");
const server = join(debugDir, "server.py");
const python = process.env.PYTHON || "python3";
const children = [];
const folders = [];

// Built at runtime so the repository privacy scan never sees a literal identity.
const HOME = "/" + "Users" + "/someone";
const DEVICE = ["0A1B2C3D", "4E5F", "6A7B", "8C9D", "0E1F2A3B4C5D"].join("-");
const PUCK = "puck" + ".js 0f0f";
const EMAIL = "someone" + "@" + "gmail.com";

after(() => {
  for (const child of children) child.kill("SIGKILL");
  for (const folder of folders) rmSync(folder, { recursive: true, force: true });
});

const iso = (secondsAgo) => new Date(Date.now() - secondsAgo * 1000).toISOString().replace(/\.\d+Z$/, "Z");
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function folder() {
  const dir = mkdtempSync(join(tmpdir(), "wand-monitor-"));
  folders.push(dir);
  return dir;
}

function status(dir, fields = {}) {
  const value = {
    pid: 0, connected: true, ready: true, recording: false, deskSleeping: false, lightMode: "mouse",
    accessibility: true, bluetoothAuthorization: 3,
    options: { controlVersion: 3, flickScroll: false, orientationCompensation: true, reviewAxisGestures: false },
    reviewTrace: { enabled: false, buffered: 0, dropped: 0, diskError: false, maximumFileBytes: 2097152, maximumFiles: 4 },
    updatedAt: iso(2 * 3600),
    ...fields,
  };
  writeFileSync(join(dir, "status.json"), JSON.stringify(value));
}

function logLines(lines) { return lines.map(([ago, text]) => iso(ago) + " " + text + "\n").join(""); }

function idleProcess() {
  const child = spawn(process.execPath, ["-e", "setTimeout(() => {}, 120000)"], { stdio: "ignore" });
  children.push(child);
  return child;
}

async function exitedPid() {
  const child = spawn(process.execPath, ["-e", "0"], { stdio: "ignore" });
  await new Promise((resolve) => child.on("exit", resolve));
  return child.pid;
}

async function startMonitor(dir, processName = basename(process.execPath)) {
  const child = spawn(python, ["-I", server, "--port", "0", "--support-dir", dir, "--process-name", processName],
    { stdio: ["ignore", "pipe", "pipe"] });
  children.push(child);
  const url = await new Promise((resolve, reject) => {
    let out = "";
    const timer = setTimeout(() => reject(new Error("monitor did not start: " + out)), 8000);
    child.stdout.on("data", (chunk) => {
      out += chunk;
      const match = out.match(/http:\/\/127\.0\.0\.1:(\d+)\//);
      if (match) { clearTimeout(timer); resolve(match[0]); }
    });
    child.stderr.on("data", (chunk) => { out += chunk; });
    child.on("exit", (code) => reject(new Error("monitor exited " + code + ": " + out)));
  });
  const port = Number(new URL(url).port);
  return { url, port, child };
}

function request(port, path, { method = "GET", host } = {}) {
  return new Promise((resolve, reject) => {
    const req = http.request({ host: "127.0.0.1", port, path, method, headers: { Host: host ?? "127.0.0.1:" + port } }, (res) => {
      let body = "";
      res.setEncoding("utf8");
      res.on("data", (chunk) => { body += chunk; });
      res.on("end", () => resolve({ status: res.statusCode, headers: res.headers, body }));
    });
    req.on("error", reject);
    req.end();
  });
}

async function state(port) {
  const response = await request(port, "/api/state");
  assert.equal(response.status, 200);
  return JSON.parse(response.body);
}

function pythonCases(script, input) {
  const result = spawnSync(python, ["-I", "-c", "import sys,json;sys.path.insert(0,sys.argv[1]);import monitor\n" + script, debugDir],
    { input: JSON.stringify(input), encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}

test("echoed device source mentioning Error is not a runtime error", () => {
  const lines = [
    "Uncaught SyntaxError: Unexpected end of Input",
    ">Uncaught Error: Function \"x\" not found!",
    "WAND_DIAG EXCEPTION {\"message\":\"SyntaxError: Unexpected end of Input\",\"stack\":\"    at wandBottomPress (wand.bridge.p1:0:1)\"}",
    "ERROR: Out of Memory!",
    "if(!global.wandDiagError){global.wandDiagError=function(e){print('WAND_DIAG EXCEPTION '+e);};}",
    ">:  catch(e){print('Uncaught '+e);}",
    "print(\"OUT OF MEMORY\");",
  ];
  const out = pythonCases("print(json.dumps([monitor.classify_device_line(l) for l in json.load(sys.stdin)]))", lines);
  assert.deepEqual(out, ["runtime", "runtime", "runtime", "runtime", "echo", "echo", "echo"]);
  const summary = pythonCases("print(json.dumps(monitor.summarize_runtime_error(json.load(sys.stdin))))", lines[2]);
  assert.equal(summary, "SyntaxError: Unexpected end of Input in wandBottomPress");
});

test("sanitising removes identities, home paths and calibration values", () => {
  const text = `CONNECTING ${DEVICE} at ${HOME}/Library/x.json ${PUCK} ${EMAIL} {"x":12.5,"y":-3,"z":1000} restoreWandCalibration({"x":1,"y":2,"z":3})`;
  const out = pythonCases("print(json.dumps(monitor.sanitize(json.load(sys.stdin), 1000)))", text);
  for (const leaked of [DEVICE, HOME, "0f0f", EMAIL, "12.5", "1000"]) assert.ok(!out.includes(leaked), leaked + " leaked: " + out);
  assert.ok(out.includes("‹id›") && out.includes("‹path›") && out.includes("calibration hidden"));
  const parsed = pythonCases("print(json.dumps([monitor.parse_line(l) for l in json.load(sys.stdin)]))", [
    "2026-10-24T17:36:08Z RAW_DELIVERY 269 seconds 5.00 maxGapMs 2400", "not a log line", "2026-10-24T17:36:08Z >WAND_CALIBRATED {\"x\":1}"]);
  assert.equal(parsed[0][1], "RAW_DELIVERY");
  assert.equal(parsed[1], null);
  assert.deepEqual(parsed[2].slice(1), ["WAND_CALIBRATED", ""]);
});

test("unchanged status with a live receiver stays connected; quiet is not lost", async () => {
  const dir = folder();
  const receiver = idleProcess();
  status(dir, { pid: receiver.pid, updatedAt: iso(3 * 3600) });
  writeFileSync(join(dir, "receiver.log"), logLines([
    [4000, "STARTED 1 ACCESSIBILITY true"], [3990, "CONNECTED_TO_PUCK"], [3980, "RUNTIME_READY"],
    [3970, "DEVICE_LIGHT mouse [0.0, 0.0, 1.0]"], [3960, "RAW_DELIVERY 250 seconds 5.00 maxGapMs 40"],
  ]));
  const { port } = await startMonitor(dir);
  const first = await state(port);
  assert.equal(first.headline.state, "ready");
  assert.equal(first.headline.title, "Connected");
  assert.equal(first.receiver.process, "running");
  assert.equal(first.power.state, "awake");
  assert.equal(first.light.name, "Pointer");
  assert.deepEqual(first.light.levels, [0, 0, 1]);
  assert.ok(first.now - first.sources.status.changedAt > 3 * 3600 - 5, "keeps the real state-change time");
  assert.equal(first.delivery.latest.rate, 50);
  assert.equal(first.battery.state, "not-reported");
  const mouse = first.lanes.find((lane) => lane.id === "mouse");
  const hud = first.lanes.find((lane) => lane.id === "hud");
  assert.equal(mouse.value, "On");
  assert.equal(hud.tone, "unknown", "the pointer light hides the HUD state");
  await sleep(1100);
  const second = await state(port);
  assert.equal(second.headline.state, "ready", "still live after another quiet poll");
  assert.ok(second.sources.process.checkedAt > first.sources.process.checkedAt);
});

test("a stopped or different process is not reported live", async () => {
  const dir = folder();
  status(dir, { pid: await exitedPid() });
  const { port, child } = await startMonitor(dir);
  const stopped = await state(port);
  assert.equal(stopped.headline.state, "receiver-stopped");
  assert.equal(stopped.receiver.process, "stopped");
  assert.equal(stopped.power.state, "unknown");
  assert.equal(stopped.lanes.find((lane) => lane.id === "speech").value, "Unknown");

  status(dir, { pid: child.pid });  // a Python process, not the expected receiver name
  await sleep(500);
  const other = await state(port);
  assert.equal(other.receiver.process, "other");
  assert.equal(other.headline.state, "receiver-stopped");
});

test("missing, malformed and partial status files are reported truthfully", async () => {
  const dir = folder();
  const { port } = await startMonitor(dir);
  const missing = await state(port);
  assert.equal(missing.headline.state, "no-status");
  assert.equal(missing.sources.log.present, false);
  writeFileSync(join(dir, "status.json"), "{\"connected\": tr");
  await sleep(500);
  const malformed = await state(port);
  assert.equal(malformed.headline.state, "unreadable");
  assert.match(malformed.headline.detail, /not valid JSON/);
  writeFileSync(join(dir, "status.json"), JSON.stringify({ pid: 1, lightMode: 7 }));
  await sleep(500);
  assert.equal((await state(port)).headline.state, "unreadable");
});

test("history survives log rotation, including lines written just before it", async () => {
  const dir = folder();
  const receiver = idleProcess();
  status(dir, { pid: receiver.pid });
  const log = join(dir, "receiver.log");
  writeFileSync(join(dir, "receiver.previous.log"), logLines([[900, "STARTED 1 ACCESSIBILITY true"]]));
  writeFileSync(log, logLines([[800, "RUNTIME_READY"]]));
  const { port } = await startMonitor(dir);
  const before = await state(port);
  assert.deepEqual(before.timeline.map((item) => item.event).reverse(), ["STARTED", "RUNTIME_READY"]);
  appendFileSync(log, logLines([[30, "RECORDING_STATE true"]]));
  renameSync(log, join(dir, "receiver.previous.log"));
  writeFileSync(log, logLines([[20, "RECORDING_STATE false"], [10, "TABLE_REST_CONFIRMED reference true follow true"]]));
  await sleep(500);
  const afterRotation = await state(port);
  assert.deepEqual(afterRotation.timeline.map((item) => item.event).reverse(),
    ["STARTED", "RUNTIME_READY", "RECORDING_STATE", "RECORDING_STATE", "TABLE_REST_CONFIRMED"]);
  assert.equal(afterRotation.sources.log.rotationsSeen, 1);
  assert.equal(afterRotation.power.since, afterRotation.timeline[0].t, "rest duration starts at the rest event, not receiver startup");
  writeFileSync(log, logLines([[5, "DESK_SLEEP"]]));  // truncated and rewritten
  await sleep(500);
  const truncated = await state(port);
  assert.equal(truncated.timeline[0].event, "DESK_SLEEP");
});

test("deep sleep, desk idle and runtime errors come from the receiver's own evidence", async () => {
  const dir = folder();
  const receiver = idleProcess();
  status(dir, { pid: receiver.pid, connected: false, ready: false, lightMode: "disconnected" });
  writeFileSync(join(dir, "receiver.log"), logLines([
    [700, "STARTED 1 ACCESSIBILITY true"],
    [690, "CONNECTING " + DEVICE],
    [680, "RUNTIME_READY"],
    [670, "WAND_CALIBRATED {\"x\":12.25,\"y\":-4.5,\"z\":998.75}"],
    [660, "REST_SAMPLE 0.01 -0.02 0.99 gyro 0.3 held 0 follow false parked false"],
    [650, "DEVICE_ERROR if(!global.wandDiagError){global.wandDiagError=function(e){};}"],
    [640, "DEVICE_ERROR Uncaught SyntaxError: Unexpected end of Input"],
    [630, "DISCONNECTED The connection failed at " + HOME + "/Library/Bluetooth"],
    [620, "CONNECTING " + DEVICE], [615, "RUNTIME_READY"],
    [300, "TABLE_REST_CONFIRMED reference true follow false"],
    [240, "DESK_SLEEP"],
    [10, "DEEP_STANDBY_REQUESTED"],
    [8, "DISCONNECTED cleanly"],
    [2, "CONNECTION_TIMEOUT"],
  ]));
  const { port } = await startMonitor(dir);
  const response = await request(port, "/api/state");
  const s = JSON.parse(response.body);
  assert.equal(s.headline.state, "deep-sleep");
  assert.match(s.headline.detail, /grip button/);
  assert.match(s.headline.detail, /Picking it up alone won’t/);
  assert.equal(s.power.state, "deep-sleep");
  assert.equal(s.light.name, "Off");
  assert.equal(s.errors.groups.length, 1);
  assert.equal(s.errors.groups[0].summary, "Uncaught SyntaxError: Unexpected end of Input");
  assert.equal(s.errors.echoes, 1);
  // Check exposed text, not numeric timestamps whose fractional digits can
  // coincidentally contain a redacted sensor value such as "0.99".
  const exposedText = [], exposedNumbers = [];
  const collectText = value => {
    if (typeof value === "string") exposedText.push(value);
    else if (typeof value === "number") exposedNumbers.push(value);
    else if (Array.isArray(value)) value.forEach(collectText);
    else if (value && typeof value === "object") Object.values(value).forEach(collectText);
  };
  collectText(s);
  for (const leaked of [DEVICE, HOME, "12.25", "998.75", "-4.5", "0.99"]) assert.ok(!exposedText.some(text => text.includes(leaked)), leaked + " leaked");
  for (const value of [12.25, 998.75, -4.5, 0.99]) assert.ok(!exposedNumbers.includes(value), value + " leaked as a number");
  assert.ok(!/\/Users\/|calibrations\//.test(response.body));

  status(dir, { pid: receiver.pid, connected: true, ready: true, deskSleeping: true, lightMode: "sleep" });
  appendFileSync(join(dir, "receiver.log"), logLines([[1, "RUNTIME_READY"], [0, "DESK_SLEEP"]]));
  await sleep(500);
  const desk = await state(port);
  assert.equal(desk.headline.state, "ready");
  assert.equal(desk.power.state, "desk-idle");
  assert.equal(desk.lanes.find((lane) => lane.id === "mouse").tone, "unknown", "the sleep light hides the mouse state");
});

test("server binds locally, serves only its own files and has no control endpoints", async () => {
  const dir = folder();
  const { url, port } = await startMonitor(dir);
  assert.match(url, /^http:\/\/127\.0\.0\.1:\d+\/$/);
  for (const path of ["/status.json", "/receiver.log", "/../wand.json", "/%2e%2e/wand.json", "/debug/monitor.py", "/api/connect"]) {
    assert.equal((await request(port, path)).status, 404, path);
  }
  for (const method of ["POST", "PUT", "DELETE", "PATCH"]) assert.equal((await request(port, "/api/state", { method })).status, 405, method);
  assert.equal((await request(port, "/api/state", { host: "evil.example" })).status, 403, "DNS rebinding Host refused");
  const page = await request(port, "/");
  assert.equal(page.status, 200);
  assert.match(page.headers["content-security-policy"], /default-src 'none'/);
  assert.equal(page.headers["cache-control"], "no-store");
  const rejected = spawnSync(python, ["-I", server, "--host", "0.0.0.0"], { encoding: "utf8" });
  assert.notEqual(rejected.status, 0, "no option to listen beyond localhost");
  const source = readFileSync(server, "utf8") + readFileSync(join(debugDir, "monitor.py"), "utf8");
  for (const forbidden of ["CoreBluetooth", "bleak", "import serial", "os.kill(pid, signal", "SIGTERM", "SIGUSR1", "CGEvent", ".write_text(", ".write_bytes(", ".unlink(", "os.remove("]) {
    assert.ok(!source.includes(forbidden), "monitor must stay read-only: " + forbidden);
  }
  assert.ok(!/open\([^)]*["'](?:w|a|r\+|x)/.test(source), "monitor opens files read-only");
});

test("page is accessible, local-only and has no controls that change modes", async () => {
  const html = readFileSync(join(debugDir, "index.html"), "utf8");
  const css = readFileSync(join(debugDir, "styles.css"), "utf8");
  const js = readFileSync(join(debugDir, "app.js"), "utf8");
  assert.match(html, /<html lang="en">/);
  assert.match(html, /<main>/);
  assert.equal((html.match(/<h1\b/g) || []).length, 1);
  assert.match(html, /class="skip" href="#activity"/);
  assert.match(html, /aria-live="polite"/);
  assert.match(css, /prefers-reduced-motion: reduce/);
  assert.match(css, /:focus-visible/);
  for (const text of [html, css, js]) {
    assert.ok(!/https?:\/\/(?!127\.0\.0\.1|www\.w3\.org\/2000\/svg)/.test(text), "no remote assets or CDNs");
    assert.ok(!/\bwhether\b/i.test(text), "user-facing wording avoids “whether”");
  }
  assert.ok(!/<form|method="post"|fetch\([^)]*method/i.test(html + js), "no requests that change state");
  assert.equal((js.match(/fetch\(/g) || []).length, 1);
  assert.match(js, /fetch\("\/api\/state"/);
});

test('battery level is a dated voltage estimate, never invented runtime', async()=>{
 const dir=folder(),receiver=idleProcess();
 const sample={percent:72,volts:2.91,measuredAt:Date.now()/1000};
 status(dir,{pid:receiver.pid,battery:sample});
 const {port}=await startMonitor(dir);
 const live=await state(port);
 assert.equal(live.battery.state,'reported');assert.equal(live.battery.percent,72);
 assert.equal(live.battery.volts,2.91);assert.equal(live.battery.basis,'voltage-estimate');
 status(dir,{pid:receiver.pid,battery:{...sample,measuredAt:sample.measuredAt-300}});
 await sleep(500);assert.equal((await state(port)).battery.state,'stale');
 status(dir,{pid:receiver.pid,battery:{percent:true,volts:2.9,measuredAt:sample.measuredAt}});
 await sleep(500);assert.equal((await state(port)).battery.state,'not-reported');
 status(dir,{pid:receiver.pid,battery:{...sample,measuredAt:sample.measuredAt+3600}});
 await sleep(500);assert.equal((await state(port)).battery.state,'not-reported');
});

// A minimal DOM, enough for app.js's render(): the browser is not available to these tests.
class FakeNode {
  constructor(tag) { this.tagName = tag; this.children = []; this.attributes = {}; this.dataset = {}; this.style = {}; this.hidden = false; this._text = ""; }
  append(...items) {
    for (const item of items) {
      if (item instanceof FakeNode && item.tagName === "#fragment") this.children.push(...item.children);
      else this.children.push(item instanceof FakeNode ? item : new FakeText(String(item)));
    }
  }
  replaceChildren(...items) { this.children = []; this._text = ""; this.append(...items); }
  get textContent() { return this.children.length ? this.children.map((child) => child.textContent).join("") : this._text; }
  set textContent(value) { this._text = ""; this.children = String(value) ? [new FakeText(String(value))] : []; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  getAttribute(name) { return this.attributes[name] ?? null; }
  removeAttribute(name) { delete this.attributes[name]; }
  addEventListener() {}
  get childElementCount() { return this.children.filter((child) => !(child instanceof FakeText)).length; }
  *walk() { yield this; for (const child of this.children) if (!(child instanceof FakeText)) yield* child.walk(); }
}
class FakeText extends FakeNode { constructor(text) { super("#text"); this._text = text; } }

function loadPage() {
  const ids = new Map();
  const lanes = ["Top", "Middle", "Bottom"].map((button) => Object.assign(new FakeNode("ul"), { dataset: { button } }));
  const steps = ["awake", "desk-idle", "deep-sleep"].map((step) => Object.assign(new FakeNode("li"), { dataset: { step } }));
  const document = {
    body: new FakeNode("body"), title: "", hidden: false,
    createElement: (tag) => new FakeNode(tag),
    createDocumentFragment: () => new FakeNode("#fragment"),
    createTextNode: (text) => new FakeText(String(text)),
    getElementById(id) { if (!ids.has(id)) ids.set(id, new FakeNode("div")); return ids.get(id); },
    querySelectorAll(selector) {
      if (selector === ".lanes") return lanes;
      if (selector === "#track li[data-step]") return steps;
      const key = { "[data-t]": "t", "[data-d]": "d" }[selector];
      const found = [];
      for (const root of [...ids.values(), ...lanes]) for (const node of root.walk()) if (key && node.dataset[key] !== undefined) found.push(node);
      return found;
    },
    addEventListener() {},
  };
  const context = vm.createContext({ document, Node: FakeNode, Date, Math, Number, JSON, Set, Object, Array, String });
  vm.runInContext(readFileSync(join(debugDir, "app.js"), "utf8"), context);
  const text = (id) => document.getElementById(id).textContent;
  return { context, document, lanes, steps, text };
}

test("page leads with plain current state, files old errors as earlier and quiets repeats", async () => {
  const dir = folder();
  const receiver = idleProcess();
  const battery = { percent: 72, volts: 2.91, measuredAt: Date.now() / 1000 - 30 };
  status(dir, { pid: receiver.pid, lightMode: "mouse", recording: true, battery });
  writeFileSync(join(dir, "receiver.previous.log"), logLines([
    [3000, "STARTED 1 ACCESSIBILITY true"],
    [2990, "DEVICE_ERROR Uncaught SyntaxError: Unexpected end of Input"],
  ]));
  writeFileSync(join(dir, "receiver.log"), logLines([
    [600, "STARTED 2 ACCESSIBILITY true"], [595, "RUNTIME_READY"],
    [500, "DEVICE_LIGHT idle [0.0, 0.0, 0.0]"], [500, "SPEECH_BUTTON 1 SENT"], [500, "DEVICE_LIGHT recording [1.0, 0.0, 0.0]"],
    [500, "SPEECH_BUTTON 0 SENT"], [500, "RECORDING_STATE true"], [500, "DEVICE WAND_RECORDING_LIGHT 1"],
    [300, "HUD_CLOSED context ended"],
    [200, "BOTTOM_HOLD_TARGET scroll"], [190, "BOTTOM_HOLD_TARGET scroll"], [180, "BOTTOM_HOLD_TARGET scroll"],
    [100, "BUTTON LEFT DOWN flags 0 clickCount 1"], [100, "BUTTON LEFT UP flags 0 clickCount 1"], [100, "HIGH_DWELL_CLICK"],
    [90, "MOVEMENT_REPORTS_POSTED 100"], [80, "RAW_DELIVERY 250 seconds 5.00 maxGapMs 40"],
    [10, "DEVICE_LIGHT mouse [0.0, 0.0, 1.0]"],
  ]));
  const { port } = await startMonitor(dir);
  const live = await state(port);
  const page = loadPage();
  page.context.render(live);

  assert.equal(page.text("headline"), "Pointer On");
  assert.equal(page.text("headline-detail"), "The wand is moving the pointer. Agent Flow is recording speech.");
  assert.match(page.text("status-row"), /^Connected · \d+ min.*Battery about 72%$/);
  assert.match(page.text("receiver-facts"), /BatteryAbout 72% · 2\.91 V voltage estimate · measured \d+ s ago/);
  assert.equal(page.document.body.dataset.light, "mouse");
  assert.match(page.text("errors"), /^No errors since connecting/, "an error from an earlier receiver run isn't shown as current");
  assert.equal(page.document.getElementById("errors-earlier").hidden, false);
  assert.equal(page.text("errors-earlier-label"), "1 earlier error, before then");

  const lane = (button, index) => page.lanes.find((list) => list.dataset.button === button).children[index].textContent;
  assert.match(lane("Top", 0), /^SpeechRecording/);
  assert.match(lane("Middle", 0), /HUDCan’t tell.*Hidden while the light shows Pointer \(blue\)\..*HUD closed by Agentic Mouse/);
  assert.match(lane("Bottom", 0), /^PointerOnTap Bottom to turn the pointer on or off/);

  const timeline = page.text("timeline");
  assert.match(timeline, /Agent Flow started recording/);
  assert.match(timeline, /Bottom held: scrolling×3/);
  for (const noise of ["Light:", "Pointer moves", "Motion data", "Recording light", "Top pressed"]) {
    assert.ok(!timeline.includes(noise), "key events hide " + noise);
  }
  const buttons = page.context.prepareTimeline(live.timeline, "buttons").map((row) => row.title);
  assert.ok(buttons.includes("Clicked by holding still"), "down, up and stop-to-click become one row");
  assert.ok(buttons.includes("Top tapped"), "a quick Top press and release become one row");
  assert.ok(!buttons.includes("Left button down") && !buttons.includes("Recording light on"));
  const everything = page.context.prepareTimeline(live.timeline, "all").map((row) => row.title);
  assert.ok(everything.some((title) => title.startsWith("Motion data: 50.0 updates a second")));

  const rendered = [...page.document.getElementById("headline").walk()].length && ["headline", "headline-detail", "status-row", "errors",
    "timeline", "power-detail", "light-name", "delivery-rate", "delivery-facts", "settings-facts", "receiver-facts", "sources"]
    .map(page.text).join(" ") + page.lanes.map((list) => list.textContent).join(" ");
  assert.ok(!/undefined|null|NaN|\[object/.test(rendered), "no placeholder values leak into the page");
  assert.ok(!/\bwhether\b/i.test(rendered));

  status(dir, { pid: receiver.pid, connected: false, ready: false, lightMode: "disconnected", battery });
  appendFileSync(join(dir, "receiver.log"), logLines([[3, "DEEP_STANDBY_REQUESTED"], [2, "DISCONNECTED cleanly"]]));
  await sleep(500);
  page.context.render(await state(port));
  assert.equal(page.text("headline"), "Deep Sleep");
  assert.match(page.text("headline-detail"), /Press any grip button to wake it\. Picking it up alone won’t\./);
  assert.equal(page.steps.find((step) => step.dataset.step === "deep-sleep").getAttribute("aria-current"), "step");
  assert.match(page.lanes.find((list) => list.dataset.button === "Bottom").textContent, /Can’t tell.*Needs a connected wand\./);
  assert.ok(!page.text("status-row").includes("Battery"), "an old battery reading isn't shown as current");
  assert.match(page.text("receiver-facts"), /About 72% · 2\.91 V last reading, not current/);
});
