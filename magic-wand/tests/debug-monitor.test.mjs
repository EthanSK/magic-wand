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
  for (const leaked of [DEVICE, HOME, "12.25", "998.75", "-4.5", "0.99"]) assert.ok(!response.body.includes(leaked), leaked + " leaked");
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
