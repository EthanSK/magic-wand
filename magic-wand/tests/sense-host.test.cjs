// The Sense runs the canonical Puck program on the Mac: same base, bridge and
// power policy, fed by real Sense pins and readings. Simulated clock; no hardware.
const test = require("node:test"), assert = require("node:assert/strict");
const vm = require("node:vm"), crypto = require("node:crypto");
const { read } = require("./harness.cjs");

function createSense({ zero, options } = {}) {
  let now = 100, next = 0;
  const timers = new Map(), lines = [], lights = [], imu = [], logs = [];
  let sleeps = 0, api;
  const native = {
    now: () => now,
    schedule: (id, ms, repeat) => timers.set(id, { at: now + ms / 1000, every: repeat ? ms / 1000 : 0 }),
    cancel: (id) => timers.delete(id),
    text: (t) => lines.push(t), light: (r, g, b) => lights.push([r, g, b]), imu: (m) => imu.push(m),
    sleep: () => sleeps++, log: (t) => logs.push(t),
  };
  const ctx = vm.createContext({ __native: native });
  vm.runInContext(read("docs/sim/espruino.js"), ctx);
  vm.runInContext(read("device/sense/wand-sense-host.js"), ctx);
  api = vm.runInContext("WandSenseHost.create(globalThis, __native)", ctx);
  const bridge = read("device/generated/wand-mode-bridge.compact.js");
  const runtime = read("device/generated/wand-runtime-version.txt").trim();
  const revision = crypto.createHash("sha256").update(bridge).digest("hex");
  const ok = api.boot(read("device/wand-mouse-prototype.js"), bridge, read("device/generated/wand-power-policy.compact.js"), zero || "", runtime, revision, options);
  function advance(seconds) {
    const end = now + seconds;
    for (;;) {
      const due = [...timers].filter(([, t]) => t.at <= end + 1e-9).sort((a, b) => a[1].at - b[1].at)[0];
      if (!due) break;
      const [id, t] = due; now = t.at;
      if (t.every) t.at += t.every; else timers.delete(id);
      api.fire(id);
    }
    now = end;
  }
  // One frame every 1/104 s, as the Sense firmware streams it.
  function frames(count, mask, gyro = [0, 0, 0], acc = [0, 0, 8192]) {
    for (let i = 0; i < count; i++) { advance(1 / 104); api.deliver(now, mask, acc, gyro); }
  }
  return { api, ctx, ok, lines, lights, imu, logs, runtime, revision, advance, frames, get sleeps() { return sleeps; }, get now() { return now; } };
}

test("boots the complete canonical program and passes the receiver's own handshake", () => {
  const s = createSense({ zero: '{"x":10,"y":-20,"z":5}' });
  assert.equal(s.ok, true, s.logs.join("\n"));
  assert.deepEqual(s.logs, []);
  assert.equal(s.ctx.wandMotionReady, true);
  assert.equal(s.ctx.CONFIG.ySign, 1, "Sense vertical direction matches the verified mounting");
  assert.equal(s.ctx.WAND_POWER_POLICY_VERSION, 4);
  assert.equal(s.ctx.WAND_BRIDGE_REVISION, s.revision);
  assert.deepEqual(JSON.parse(JSON.stringify(s.ctx.bias)), { x: 10, y: -20, z: 5 }, "per-device zero restored before connect");
  // Only the connect handler's ordinary state lines, as after a real Puck connection; never a ready marker.
  assert(s.lines.every((l) => /^(@FOLLOW |WAND_LIGHT_STATE )/.test(l)), s.lines.join("\n"));
  // Exactly the receiver's handshake text, through the console accumulator.
  s.api.repl("\u0003\u0003\n\u0010global.WAND_UPDATING=true;if(typeof loadingLight==='function')loadingLight();");
  s.api.repl(`if(global.WAND_RUNTIME_VERSION==="${s.runtime}"){if(!global.wandBridgeOriginalSend)global.wandBridgeOriginalSend=mouse.send;mouse.send=function(x,y,b,cb){Bluetooth.println("@WAND "+x+","+y+","+b);if(cb)cb();};if(!connected)onConnect();print("WAND_BRIDGE_READY");}else print("WAND_NEEDS_CONFIG");`);
  assert(s.lines.includes("WAND_BRIDGE_READY"));
  s.api.repl(`E.setFlags({pretokenise:1});global.wandDoubleClickSeconds=0.3;if(global.WAND_BRIDGE_REVISION==='${s.revision}'&&global.wandMotionReady!==false)print('WAND_MODE_ROUTING_READY');else print('WAND_PATCH_NEEDED');`);
  assert(s.lines.includes("WAND_MODE_ROUTING_READY"));
  s.api.repl("if(global.WAND_POWER_POLICY_VERSION===4&&typeof global.wandEnterDeepStandby==='function'&&global.wandPowerWatches&&global.wandPowerWatches.length===3)print('WAND_POWER_POLICY_READY');else print('WAND_POWER_POLICY_NEEDED');");
  assert(s.lines.includes("WAND_POWER_POLICY_READY"));
  s.api.repl("global.wandShot=0;global.wandRawPointer=true;global.wandRawBias=undefined;global.wandRawActive=false;global.WAND_UPDATING=false;setHUDOpen(false);updateLights();");
  assert.deepEqual(s.lights.at(-1), [0, 0, 0], "idle is dark");
});

test("multi-line console input runs only when complete", () => {
  const s = createSense();
  s.api.repl("global.wandTestValue=(function(){");
  assert.equal(s.ctx.wandTestValue, undefined);
  s.api.repl("return 7;");
  s.api.repl("})();");
  assert.equal(s.ctx.wandTestValue, 7);
  s.api.repl("global.wandTestValue=(function(){\u0003");
  s.api.repl("global.wandTestValue=8;");
  assert.equal(s.ctx.wandTestValue, 8, "Ctrl-C discards partial input");
});

test("Sense buttons drive the canonical lanes and motion uses the real reading time", () => {
  const s = createSense({ zero: '{"x":0,"y":0,"z":0}' });
  s.api.repl("global.WAND_UPDATING=false;updateLights();");
  s.frames(3, 0);
  s.lines.length = 0;
  s.frames(1, 1); // Bottom down
  assert(s.lines.includes("@BOTTOM 1"));
  assert.equal(s.ctx.moveLatched, true);
  assert.equal(s.imu.at(-1), 2, "gyro requested at the accepted 104 Hz");
  s.frames(2, 1);
  s.frames(1, 0); // short tap: follow latches without a click
  assert(s.lines.includes("@BOTTOM 0"));
  assert.equal(s.ctx.moveLatched, true);
  assert(!s.lines.some((l) => /^@WAND .*,1$/.test(l)), "tap never clicks");
  s.lines.length = 0;
  s.advance(0.2);
  s.frames(20, 0, [0, 0, -134 * 30]);
  const raw = s.lines.filter((l) => l.startsWith("@RAW "));
  assert(raw.length >= 15, s.lines.join("\n"));
  const dt = raw.slice(2).map((l) => Number(l.slice(5).split(",")[0]));
  assert(dt.every((v) => Math.abs(v - 9615) < 50), "dt comes from reading times: " + dt.join(","));
  assert(s.lines.some((l) => l.startsWith("@ZERO ")));
  // Middle and Top reach their own lanes.
  s.lines.length = 0;
  s.frames(12, 2); s.frames(1, 0);
  assert(s.lines.includes("@MIDDLE 1") && s.lines.includes("@MIDDLE 0"));
  s.frames(1, 4); s.frames(1, 0);
  assert(s.lines.includes("@STT 1") && s.lines.includes("@STT 0"));
});

test("desk accelerometer sensing uses real gravity at the requested low rate", () => {
  const s = createSense({ zero: '{"x":0,"y":0,"z":0}' });
  s.api.repl("global.WAND_UPDATING=false;setMouseFollow(false);");
  s.advance(1.2);
  assert.equal(s.imu.at(-1), 1, "accelerometer-only desk sensing");
  s.lines.length = 0;
  for (let i = 0; i < 30; i++) { s.advance(0.08); s.api.deliver(s.now, 0, [100, -200, 8100], null); }
  const imu = s.lines.filter((l) => l.startsWith("@IMU "));
  assert(imu.length >= 3 && imu.length <= 5, imu.join("\n"));
  assert(imu[0].startsWith("@IMU 100,-200,8100,0,0,0,0"), imu[0]);
});

test("all three buttons start the canonical warning, then ask the firmware for button-wake sleep", () => {
  const s = createSense({ zero: '{"x":0,"y":0,"z":0}' });
  s.api.repl("global.WAND_UPDATING=false;updateLights();");
  s.frames(1, 1); s.frames(1, 3); s.frames(1, 7);
  s.advance(0.05);
  assert.deepEqual(s.lights.at(-1), [1, 1, 1], "first flash");
  s.advance(0.4);
  assert.equal(s.sleeps, 1);
  assert(s.lines.includes("WAND_POWER_STANDBY_ENTERED"));
  const before = s.lines.length;
  s.frames(1, 0);
  assert(!s.lines.slice(before).some((l) => /^@(STT|MIDDLE|BOTTOM|WAND)/.test(l)), "the chord release fires no action");
});

test("teardown stops every timer and output", () => {
  const s = createSense({ zero: '{"x":0,"y":0,"z":0}' });
  s.api.repl("global.WAND_UPDATING=true;updateLights();");
  s.api.teardown();
  const count = s.lights.length;
  s.advance(5);
  s.api.deliver(s.now, 1, [0, 0, 8192], [0, 0, 0]);
  s.api.repl("print('late')");
  assert.equal(s.lights.length, count);
  assert(!s.lines.includes("late"));
});

test("Sense pointer gain changes only the pointer gain reported to the receiver", () => {
  const plain = createSense({ zero: '{"x":0,"y":0,"z":0}' }), faster = createSense({ zero: '{"x":0,"y":0,"z":0}', options: { pointerGain: 1.466 } });
  for (const s of [plain, faster]) {
    s.api.repl("global.WAND_UPDATING=false;setMouseFollow(true);");
    s.advance(0.2); s.frames(5, 0, [0, 0, -1340]);
  }
  const zero = (s) => JSON.parse(s.lines.find((l) => l.startsWith("@ZERO ")).slice(6));
  const a = zero(plain), b = zero(faster);
  assert(Math.abs(b[2] / a[2] - 1.466) < 1e-9, `gain ${a[2]} -> ${b[2]}`);
  assert.deepEqual(b.slice(3), a.slice(3), "vertical gain, speed curve, held gain, slack and signs unchanged");
  assert.equal(b[12], 1, "Sense vertical direction kept");
  assert.equal(faster.ctx.CONFIG.deadZone, plain.ctx.CONFIG.deadZone, "HUD dead zone unchanged");
  const ignored = createSense({ options: { pointerGain: 40 } });
  assert.equal(ignored.ctx.CONFIG.gain, plain.ctx.CONFIG.gain, "out-of-range gain ignored");
});

// A live maintenance bridge update must keep the requested Sense sensitivity.
test("Sense tuning survives repeated bridge replacement without multiplying twice", () => {
  const s = createSense({zero: '{"x":0,"y":0,"z":0}', options: {pointerGain: 1.466}});
  const gain = s.ctx.CONFIG.gain;
  for (let i=0;i<2;i++) {
    s.api.device.loadFragments(read("device/generated/wand-mode-bridge.compact.js"));
    s.api.configurePointer(1.466);
    assert.equal(s.ctx.CONFIG.gain, gain);
    assert.equal(s.ctx.CONFIG.ySign, 1);
  }
});
