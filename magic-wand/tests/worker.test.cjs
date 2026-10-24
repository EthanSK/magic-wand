// Runs docs/sim/worker.js as the browser would, in a worker-shaped VM with a simulated clock:
// it must load the real device code and bridge, calibrate, connect, and turn aim into motion.
const test = require("node:test");
const assert = require("node:assert/strict");
const vm = require("vm");
const { read } = require("./harness.cjs");

function createWorker() {
  let nowMs = 5000;
  let nextTimer = 0;
  const timers = new Map();
  const messages = [];
  const files = {
    shim: "docs/sim/espruino.js",
    device: "docs/device/wand-mouse-prototype.js",
    bridge: "docs/device/wand-mode-bridge.compact.js",
  };
  const ctx = vm.createContext({});
  Object.assign(ctx, {
    self: ctx,
    console,
    performance: { now: () => nowMs },
    setTimeout: (fn, ms) => { timers.set(++nextTimer, { fn, at: nowMs + ms }); return nextTimer; },
    setInterval: (fn, ms) => { timers.set(++nextTimer, { fn, at: nowMs + ms, every: ms }); return nextTimer; },
    clearTimeout: (id) => timers.delete(id),
    clearInterval: (id) => timers.delete(id),
    postMessage: (message) => messages.push(JSON.parse(JSON.stringify(message))),
    importScripts: (url) => vm.runInContext(read(files[url]), ctx, { filename: files[url] }),
    fetch: async (url) => ({ ok: true, status: 200, text: async () => read(files[url]) }),
  });
  vm.runInContext(read("docs/sim/worker.js"), ctx, { filename: "docs/sim/worker.js" });
  const send = (data) => ctx.onmessage({ data });
  const advance = (ms) => {
    const end = nowMs + ms;
    for (;;) {
      const due = [...timers].filter(([, timer]) => timer.at <= end).sort((a, b) => a[1].at - b[1].at)[0];
      if (!due) break;
      const [id, timer] = due;
      nowMs = timer.at;
      if (timer.every) timer.at += timer.every;
      else timers.delete(id);
      timer.fn();
    }
    nowMs = end;
  };
  const frames = () => messages.filter((m) => m.type === "events").flatMap((m) => m.events).filter((e) => e.type === "frame");
  const state = () => messages.filter((m) => m.type === "state").at(-1).state;
  return { ctx, messages, send, advance, frames, state };
}

async function boot() {
  const worker = createWorker();
  worker.send({ type: "init", urls: { shim: "shim", device: "device", bridge: "bridge" } });
  for (let i = 0; i < 10; i++) await new Promise((resolve) => setImmediate(resolve));
  return worker;
}

test("the worker boots the real device code, calibrates and connects", async () => {
  const worker = await boot();
  const fatal = worker.messages.find((m) => m.type === "fatal" || m.type === "device-error");
  assert.equal(fatal, undefined, fatal && fatal.message);
  assert(worker.messages.some((m) => m.type === "ready"), "ready");
  assert.equal(worker.state().calibrated, true);
  const lines = worker.messages.filter((m) => m.type === "events").flatMap((m) => m.events).filter((e) => e.type === "line").map((e) => e.text);
  assert(lines.includes("WAND_MODE_ROUTING_READY"), "bridge applied");
  assert(!lines.some((line) => line.startsWith("Uncaught")), lines.find((line) => line.startsWith("Uncaught")));
});

test("aim becomes pointer motion while following, including a move after a pause", async () => {
  const worker = await boot();
  worker.send({ type: "eval", code: "global.WAND_UPDATING=false;setHUDOpen(false);updateLights();" });
  worker.send({ type: "aim", yaw: 0, pitch: 0 });
  worker.send({ type: "pin", pin: "D1", value: 0 });
  worker.advance(60);
  worker.send({ type: "pin", pin: "D1", value: 1 });
  worker.advance(300);
  assert.equal(worker.state().moveLatched, true, "a tap starts following");
  const sumX = () => worker.frames().reduce((sum, frame) => sum + frame.x, 0);

  // A steady sweep: 10 degrees right over half a second.
  const before = sumX();
  for (let i = 1; i <= 30; i++) {
    worker.send({ type: "aim", yaw: (10 * i) / 30, pitch: 0 });
    worker.advance(16.7);
  }
  worker.advance(200);
  const sweep = sumX() - before;
  assert(sweep > 600 && sweep < 900, `a 10° sweep moves about 864 counts at full gain (got ${sweep})`);

  // Hold still for a second, then one quick 5 degree move: it must not be spread into the pause.
  worker.advance(1000);
  const paused = sumX();
  worker.send({ type: "aim", yaw: 15, pitch: 0 });
  worker.advance(300);
  const jump = sumX() - paused;
  assert(jump > 250, `a move after a pause keeps its size (got ${jump})`);

  // One tap stops following, and the gyro sleeps while pickup sensing stays on.
  for (const ms of [60]) { worker.send({ type: "pin", pin: "D1", value: 0 }); worker.advance(ms); worker.send({ type: "pin", pin: "D1", value: 1 }); worker.advance(40); }
  worker.advance(1200);
  assert.equal(worker.state().moveLatched, false);
  assert.equal(worker.state().awake, true, "low-power accelerometer stays on for pickup sensing");
});
