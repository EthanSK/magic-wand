// Device behaviour with the bridge applied, through the same Espruino shim as the website.
// Ported from the wand's original regression script; each scenario runs twice: the readable
// bridge evaluated whole, and the compacted bridge sent one statement at a time like the receiver.
const test = require("node:test");
const assert = require("node:assert/strict");
const { createWand } = require("./harness.cjs");

for (const bridge of ["readable", "fragments"]) {
  test(`independent modes, lights, calibration and guards (${bridge} bridge)`, () => {
    const w = createWand({ bridge });
    const { ctx, frames, lines } = w;
    w.calibrate();
    // A same-named global must not be patched instead of the callback the pin watch actually holds.
    ctx.onMoveButton = function staleGlobalCallback() { throw Error("must not call stale global"); };
    w.loadBridge();
    assert(lines.includes("WAND_CALLBACK_MATCH false"), "bridge patched the watched callback, not the stale global");
    assert(lines.includes("WAND_MODE_ROUTING_READY"));
    const middleTap = () => { w.edge("D2", 0); w.advance(0.05); w.edge("D2", 1); };

    // Hold from idle: temporary movement, one endpoint click on release, sensor kept warm briefly.
    frames.length = 0;
    w.edge("D1", 0);
    assert(ctx.moveLatched && w.device.awake);
    assert.deepEqual(w.colors(), [0, 0, 1], "bottom down refreshes blue immediately");
    w.advance(0.5);
    assert(ctx.moveLatched && !ctx.dragging);
    w.edge("D1", 1);
    assert(!ctx.moveLatched && w.device.awake, "held entry stops pointer immediately but keeps sensor warm");
    w.advance(1.01);
    assert(!ctx.gyroAwake && w.device.sampleRate === 1.6, "gyro sleeps; low-power pickup sensing remains at 1.6 Hz");
    assert.equal(frames.filter((f) => f[2] === 1).length, 1, "held movement from idle clicks once on release");
    assert.equal(frames.at(-1)[2], 0, "endpoint click is released");
    const before = frames.length;
    w.device.accel({ x: 134, y: 268, z: 1600 });
    assert.equal(frames.length, before, "returning hand while idle sends no movement");

    // Tap from idle latches without clicking.
    frames.length = 0;
    w.tap();
    assert(ctx.moveLatched, "quick entry tap still latches");
    w.advance(0.3);
    assert.equal(frames.filter((f) => f[2] === 1).length, 0, "entry tap never emits a delayed click");

    // LOW hold from HIGH: reposition, release clicks once, HIGH stays armed.
    w.advance(0.9);
    frames.length = 0;
    w.edge("D1", 0); w.advance(0.3);
    assert(ctx.moveLatched && !ctx.dragging, "ordinary hold never selects text");
    w.edge("D1", 1);
    assert(ctx.moveLatched, "LOW release keeps prior HIGH mode armed");
    assert.equal(frames.filter((f) => f[2] === 1).length, 1, "LOW release clicks once");
    assert(ctx.wandPointerPauseUntil > w.now + 0.29, "release parks the pointer for 300 ms");
    w.advance(1.01);
    assert(w.device.awake, "prior HIGH mode keeps the sensor awake");
    ctx.setMouseFollow(false);

    // Click then hold drags; release drops and restores prior HIGH.
    w.advance(0.3); w.tap(); w.advance(0.9);
    frames.length = 0;
    w.tap(); w.advance(0.05); w.edge("D1", 0); w.advance(0.3);
    assert(ctx.dragging, "click then long press begins dragging");
    assert.equal(frames.filter((f) => f[2] === 1).length, 1, "drag has one down and no preceding click");
    w.edge("D1", 1);
    assert(!ctx.dragging && ctx.moveLatched, "release drops and restores prior HIGH");
    w.advance(1.01);
    assert(w.device.awake, "resumed HIGH keeps the sensor awake");
    ctx.setMouseFollow(false);
    assert.equal(frames.at(-1)[2], 0, "drag releases the mouse button");

    // Second held press within the Mac's double-click window, after the ordinary click fired.
    w.advance(0.3); w.tap(); w.advance(0.9);
    frames.length = 0;
    w.tap(); w.advance(0.25); w.edge("D1", 0); w.advance(0.3);
    assert(ctx.dragging, "second held press uses the shortened 300 ms window");
    w.edge("D1", 1);
    assert(!ctx.dragging && ctx.moveLatched);
    ctx.setMouseFollow(false);

    // A single tap while following exits.
    w.advance(0.3); w.tap(); w.advance(0.3); w.tap();
    assert(!ctx.moveLatched, "single click exits latched follow");
    w.advance(0.3);

    // The host controls HUD visibility; firmware Middle cannot change pointer follow.
    w.tap(); assert(ctx.moveLatched);middleTap();assert(ctx.moveLatched);
    ctx.setHUDOpen(true);assert(ctx.moveLatched && ctx.hudOpen);
    w.edge("D1",0);w.advance(.3);w.edge("D1",1);
    assert(ctx.hudOpen,"Bottom never dismisses the HUD");
    ctx.setMouseFollow(false);assert(ctx.hudOpen);
    ctx.setHUDOpen(false);
    const watchers=w.device.watchCount();w.loadBridge();
    assert.equal(w.device.watchCount(),watchers);
    w.edge("D1",0);w.advance(.03);w.edge("D2",0);
    assert(!ctx.scrollHeld,"independent buttons do not become a chord");
    w.edge("D1",1);w.edge("D2",1);
    // Light priority.
    ctx.setHUDOpen(false); ctx.moveLatched = false; ctx.updateLights();
    assert.deepEqual(w.colors(), [0, 0, 0]);
    ctx.setWandRecording(true);
    assert.deepEqual(w.colors(), [1, 0, 0], "idle recording stays red after speech release");
    ctx.moveLatched = true; ctx.updateLights();
    assert.deepEqual(w.colors(), [1, 0, 0], "recording red replaces pointer blue");
    ctx.setWandRecording(false);
    assert.deepEqual(w.colors(), [0, 0, 1], "pointer is blue again once recording stops");
    ctx.setWandRecording(true);
    ctx.moveLatched=false;ctx.setHUDOpen(true); ctx.updateLights();
    assert.deepEqual(w.colors(), [0, 1, 0], "HUD green overrides recording red");
    ctx.moveLatched=true;ctx.updateLights();
    assert.deepEqual(w.colors(), [0, 1, 0], "the open HUD stays green with mouse follow on");
    ctx.moveLatched=false;ctx.updateLights();
    ctx.scrollHeld = true; ctx.updateLights();
    assert.deepEqual(w.colors(), [0, 1, 1], "scroll cyan overrides recording red");
    ctx.scrollHeld = false; ctx.setHUDOpen(false); ctx.setWandRecording(false);
    assert.deepEqual(w.colors(), [0, 0, 0], "stopping recording clears idle light");
    ctx.setWandRecording(true); ctx.connected = false; ctx.updateLights();
    assert.deepEqual(w.colors(), [.45, .45, .45], "disconnected overrides stale recording");
    ctx.WAND_UPDATING = true; ctx.updateLights();
    assert.deepEqual(w.colors(), [.45, .45, .45], "update uses the old white mix perceived as orange");

    // Reconnect keeps calibration; a missing calibration restarts on the next press.
    ctx.connected = true; ctx.WAND_UPDATING = false; ctx.setWandRecording(false);
    const savedBias = JSON.stringify(ctx.bias);
    w.device.disconnect(); w.device.connect();
    assert.equal(JSON.stringify(ctx.bias), savedBias, "reconnect retains valid calibration");
    assert(!ctx.calibrationLit,"reconnect keeps completed calibration");
    w.advance(1.01);assert(!ctx.gyroAwake && w.device.sampleRate === 1.6,"reconnect returns to low-power pickup sensing");
    ctx.bias = undefined; ctx.calibrationDeadline = w.now - 1; ctx.calibrationLit = false;
    w.edge("D1", 0);
    assert(ctx.calibrationLit && w.device.awake, "button restarts missing calibration");
    w.advance(0.3); w.edge("D1", 1);
    for (let i = 0; i < Math.ceil(ctx.CONFIG.sampleRate * 2.2); i++) w.motion({ x: 0, y: 0, z: 0 });
    assert(ctx.bias && !ctx.calibrationLit, "still readings after release restore calibration");

    // Horizontal scroll boost.
    ctx.scrollX = 10; ctx.scrollY = 10; lines.length = 0; ctx.scrollReport("U");
    assert.equal(lines.at(-1), "@SCROLL U,14000,10000", "horizontal boosted 40 percent; vertical unchanged");
    ctx.scrollX = -10; ctx.scrollY = -10; ctx.scrollReport("U");
    assert.equal(lines.at(-1), "@SCROLL U,-14000,-10000");

    // Warm sensor grace and power.
    ctx.bias = { x: 0, y: 0, z: 0 }; ctx.connected = true; ctx.moveLatched = false; ctx.hudOpen = false; ctx.scrollHeld = false;
    ctx.wakeGyro(); ctx.sleepGyro(); w.advance(0.5);
    assert(w.device.awake, "sensor stays awake during grace");
    ctx.wakeGyro(); w.advance(0.6);
    assert(w.device.awake, "rewake cancels the old sleep timer");
    ctx.sleepGyro(); w.advance(1.01);
    assert(!ctx.gyroAwake && w.device.sampleRate === 1.6, "idle gyro grace is bounded; pickup sensing stays on");
    ctx.wakeGyro(); w.device.disconnect();
    assert(!w.device.awake, "disconnect powers the sensor off immediately");
    assert.equal(ctx.CONFIG.gain, 86.4);
    assert.equal(ctx.CONFIG.yGain, 1.4);
    assert.equal(ctx.CONFIG.sampleRate, 104);
  });

  test(`switch-jolt guards, cold settling and the fixed-position click (${bridge} bridge)`, () => {
    const w = createWand({ bridge });
    const { ctx, frames, lines } = w;
    w.calibrate();
    w.loadBridge();
    function prepareIdle() {
      for (const pin of ["D1", "D2", "D30"]) w.edge(pin, 1);
      ctx.cancelTapGesture(); ctx.clearHoldClick(); ctx.moveGestureMode = undefined;
      ctx.moveLatched = false; ctx.hudOpen = false; ctx.scrollHeld = false; ctx.scrollSuppress = false;
      ctx.bias = { x: 0, y: 0, z: 0 }; ctx.connected = true; ctx.states = []; ctx.busy = false;
      ctx.sleepGyro(); w.advance(1.01); frames.length = 0; lines.length = 0;
    }
    const paced = (dt, z = -1340) => w.paced(dt, { x: 0, y: 0, z });
    const moved = () => frames.some((f) => f[0] || f[1]);

    prepareIdle(); w.edge("D1", 0);
    paced(0.03); paced(0.03); paced(0.03);
    assert(!moved(), "cold sensor suppresses the first 90 ms");
    paced(0.03);
    assert(moved(), "cold sensor moves after 96 ms despite only four processed readings");
    w.edge("D1", 1);

    prepareIdle(); ctx.wakeGyro(); w.advance(0.1); ctx.sleepGyro();
    w.edge("D1", 0); paced(0.03);
    assert(!moved(), "warm press impulse is rejected");
    paced(0.03);
    assert(moved(), "warm hold starts within 60 ms");
    frames.length = 0; w.edge("D1", 1); paced(0.03); paced(0.03);
    assert(!moved(), "release rebound is rejected for 70 ms");
    paced(0.02);
    paced(0.03);
    assert(moved(), "warm follow resumes after deliberate movement crosses the angular tolerance");

    w.advance(0.9); frames.length = 0; w.tap();
    assert(!ctx.moveLatched, "HIGH tap exits immediately without a click");
    for (let i=0;i<10;i++) paced(0.03);
    assert(!moved() && !frames.some(f=>f[2]===1), "exit neither moves nor clicks");
    w.advance(0.9);w.tap();w.advance(0.1);frames.length=0;

    frames.length = 0; w.edge("D30", 0); paced(0.03);
    assert(!moved(), "speech press does not jolt a following pointer");
    paced(0.03);
    assert(moved(), "following resumes while speech stays held");
    frames.length = 0; w.edge("D30", 1); paced(0.06);
    assert(!moved(), "speech release rebound is rejected");
    paced(0.02);
    paced(0.03);
    assert(moved());

    prepareIdle();w.edge("D1",0);w.advance(.02);w.edge("D2",0);w.advance(.1);
    assert(!ctx.scrollHeld,"Bottom and Middle remain independent");
    assert(lines.some(l=>l==="@MIDDLE 1"),"Middle still reaches its owner");
    assert(!lines.includes("@LEFTCLICK"),"Ethan rejected the Bottom+Middle click chord");
    w.edge("D1",1);w.edge("D2",1);

  });
}
