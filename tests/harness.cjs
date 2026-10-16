// Runs the wand's real device code in a Node VM through the website's own Espruino shim,
// with a deterministic clock. Device tests and the browser demo therefore share one host.
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");
const read = (relative) => fs.readFileSync(path.join(ROOT, relative), "utf8");

/**
 * @param {{bridge?: "readable" | "fragments" | false, strict?: boolean}} options
 *   bridge: "readable" evaluates device/wand-mode-bridge.js in one go, "fragments" sends the
 *   compacted bridge one statement at a time like the receiver, false runs the base program only.
 */
function createWand({ bridge = "fragments", strict = true, onEvents = null } = {}) {
  let now = 0;
  let nextTimer = 0;
  const timers = new Map();
  const lines = [];
  const frames = [];
  const host = {
    now: () => now,
    setTimeout: (fn, ms) => { timers.set(++nextTimer, { fn, at: now + ms / 1000 }); return nextTimer; },
    setInterval: (fn, ms) => { timers.set(++nextTimer, { fn, at: now + ms / 1000, every: ms / 1000 }); return nextTimer; },
    clearTimeout: (id) => timers.delete(id),
    clearInterval: (id) => timers.delete(id),
    emit: (events) => {
      for (const event of events) {
        if (event.type === "line") lines.push(event.text);
        else frames.push([event.x, event.y, event.b]);
      }
      if (onEvents) onEvents(events.map((event) => ({ ...event })));
    },
    onError: (error) => { if (strict) throw error; },
  };
  const ctx = vm.createContext({ __host: host });
  vm.runInContext(read("docs/sim/espruino.js"), ctx, { filename: "docs/sim/espruino.js" });
  const device = vm.runInContext("WandEspruino.install(globalThis, __host)", ctx);
  device.load(read("device/wand-mouse-prototype.js"));

  function advance(seconds) {
    const end = now + seconds;
    for (;;) {
      const due = [...timers].filter(([, timer]) => timer.at <= end + 1e-9).sort((a, b) => a[1].at - b[1].at)[0];
      if (!due) break;
      const [id, timer] = due;
      now = timer.at;
      if (timer.every) timer.at += timer.every;
      else timers.delete(id);
      timer.fn();
    }
    now = end;
  }

  const api = {
    ctx, device, lines, frames, timers,
    /** The same deterministic clock, for the receiver and HUD models. */
    clock: {
      now: host.now, setTimeout: host.setTimeout, clearTimeout: host.clearTimeout,
      setInterval: host.setInterval, clearInterval: host.clearInterval,
    },
    get now() { return now; },
    advance,
    edge(pin, value) { device.setPin(pin, value); },
    tap(pin = "D1", seconds = 0.06) { device.setPin(pin, 0); advance(seconds); device.setPin(pin, 1); },
    motion(gyro = { x: 134, y: 268, z: 402 }) { advance(1 / ctx.CONFIG.sampleRate); return device.accel(gyro); },
    paced(seconds, gyro) { advance(seconds); return device.accel(gyro); },
    colors() { return Array.from(device.lights()); },
    /** Calibrate as a freshly connected, still wand would. */
    calibrate() {
      device.connect();
      for (let i = 0; i < Math.ceil(ctx.CONFIG.sampleRate * 2.1); i++) api.motion({ x: 0, y: 0, z: 0 });
      if (!ctx.bias) throw new Error("calibration did not complete");
      frames.length = 0;
      lines.length = 0;
    },
    loadBridge(kind = bridge) {
      if (kind === "readable") device.evaluate(read("device/wand-mode-bridge.js"));
      else if (kind === "fragments") device.loadFragments(read("device/generated/wand-mode-bridge.compact.js"));
    },
  };
  return api;
}

module.exports = { createWand, ROOT, read };
