// Device behaviour with the bridge applied, through the same Espruino shim as the website.
// Ported from the wand's original regression script; each scenario runs twice: the readable
// bridge evaluated whole, and the compacted bridge sent one statement at a time like the receiver.
const test = require("node:test");
const assert = require("node:assert/strict");
const { createWand } = require("./harness.cjs");

for (const bridge of ["readable", "fragments"]) {
  test(`exclusive modes, lights, calibration and guards (${bridge} bridge)`, () => {
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
    assert(!w.device.awake, "sensor sleeps after one idle second");
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
    assert(ctx.wandPointerPauseUntil > w.now + 0.99, "release parks the pointer for one second");
    w.advance(1.01);
    assert(w.device.awake, "prior HIGH mode keeps the sensor awake");
    ctx.setMouseFollow(false);

    // Click then hold drags; release drops and exits.
    w.advance(0.3); w.tap(); w.advance(0.9);
    frames.length = 0;
    w.tap(); w.advance(0.05); w.edge("D1", 0); w.advance(0.3);
    assert(ctx.dragging, "click then long press begins dragging");
    assert.equal(frames.filter((f) => f[2] === 1).length, 1, "drag has one down and no preceding click");
    w.edge("D1", 1);
    assert(!ctx.dragging && !ctx.moveLatched, "release drops and exits drag");
    w.advance(1.01);
    assert(!w.device.awake, "drag release sleeps after grace");
    assert.equal(frames.at(-1)[2], 0, "drag releases the mouse button");

    // Second held press within the Mac's double-click window, after the ordinary click fired.
    w.advance(0.3); w.tap(); w.advance(0.9);
    frames.length = 0;
    w.tap(); w.advance(0.5); w.edge("D1", 0); w.advance(0.3);
    assert(ctx.dragging, "second held press uses the Mac double-click window");
    w.edge("D1", 1);
    assert(!ctx.dragging && !ctx.moveLatched);

    // Double tap while following exits.
    w.advance(0.3); w.tap(); w.advance(0.3); w.tap(); w.advance(0.05); w.tap();
    assert(!ctx.moveLatched, "double click exits latched follow");
    w.advance(0.3);

    // Exclusive HUD and pointer modes.
    w.tap();
    assert(ctx.moveLatched);
    middleTap();
    assert(ctx.hudOpen && !ctx.moveLatched, "HUD entry stops pointer follow");
    frames.length = 0; lines.length = 0;
    w.edge("D1", 0);
    assert(!ctx.hudOpen && ctx.moveLatched, "bottom down leaves the HUD and starts follow");
    assert(lines.includes("@POINTER_MODE"));
    w.edge("D1", 1); w.advance(0.3);
    assert.equal(frames.filter((f) => f[2] === 1).length, 0, "HUD to pointer tap enters without a click");
    frames.length = 0;
    w.tap(); w.advance(0.3);
    assert.equal(frames.filter((f) => f[2] === 1).length, 1, "later bottom tap clicks once");
    middleTap();
    assert(ctx.hudOpen && !ctx.moveLatched);

    // Reapplying the bridge (a reconnect) never duplicates watches; the scroll chord still wins.
    const watchers = w.device.watchCount();
    w.loadBridge();
    assert.equal(w.device.watchCount(), watchers, "reconnect never duplicates mode watchers");
    frames.length = 0;
    w.edge("D1", 0); w.advance(0.03); w.edge("D2", 0);
    assert(ctx.scrollHeld, "two-button chord wins");
    w.edge("D1", 1); w.edge("D2", 1);
    assert(!ctx.scrollHeld);

    // Light priority.
    ctx.setHUDOpen(false); ctx.moveLatched = false; ctx.updateLights();
    assert.deepEqual(w.colors(), [0, 0, 0]);
    ctx.setWandRecording(true);
    assert.deepEqual(w.colors(), [1, 0, 0], "idle recording stays red after speech release");
    ctx.moveLatched = true; ctx.updateLights();
    assert.deepEqual(w.colors(), [0, 0, 1], "pointer blue overrides recording red");
    ctx.setHUDOpen(true); ctx.updateLights();
    assert.deepEqual(w.colors(), [1, 0.2, 0], "HUD orange overrides recording red");
    ctx.scrollHeld = true; ctx.updateLights();
    assert.deepEqual(w.colors(), [0, 1, 1], "scroll cyan overrides recording red");
    ctx.scrollHeld = false; ctx.setHUDOpen(false); ctx.setWandRecording(false);
    assert.deepEqual(w.colors(), [0, 0, 0], "stopping recording clears idle light");
    ctx.setWandRecording(true); ctx.connected = false; ctx.updateLights();
    assert.deepEqual(w.colors(), [0.08, 0.016, 0], "disconnected overrides stale recording");
    ctx.WAND_UPDATING = true; ctx.updateLights();
    assert.deepEqual(w.colors(), [1, 0, 0], "update red retains priority");

    // Reconnect keeps calibration; a missing calibration restarts on the next press.
    ctx.connected = true; ctx.WAND_UPDATING = false; ctx.setWandRecording(false);
    const savedBias = JSON.stringify(ctx.bias);
    w.device.disconnect(); w.device.connect();
    assert.equal(JSON.stringify(ctx.bias), savedBias, "reconnect retains valid calibration");
    assert(!ctx.calibrationLit && !w.device.awake);
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
    assert(!w.device.awake, "idle grace is bounded");
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
    assert(ctx.tapPending, "ordinary latched click waits for the double-tap decision");
    for (let i = 0; i < 7; i++) paced(0.03);
    assert(!moved(), "pointer stays fixed while its click is pending");
    assert(!frames.some((f) => f[2] === 1), "pending click has not fired early");
    paced(0.04);
    assert.equal(frames.filter((f) => f[2] === 1).length, 1, "pending click emits once at the fixed position");
    assert(frames.filter((f) => f[2] === 1).every((f) => f[0] === 0 && f[1] === 0), "click frame has no motion");
    assert(moved(), "following resumes after the click decision");

    frames.length = 0; w.edge("D30", 0); paced(0.03);
    assert(!moved(), "speech press does not jolt a following pointer");
    paced(0.03);
    assert(moved(), "following resumes while speech stays held");
    frames.length = 0; w.edge("D30", 1); paced(0.06);
    assert(!moved(), "speech release rebound is rejected");
    paced(0.02);
    paced(0.03);
    assert(moved());

    prepareIdle(); w.edge("D1", 0); w.advance(0.02); w.edge("D2", 0);
    assert(ctx.scrollHeld);
    paced(0.03);
    assert.equal(ctx.scrollX, 0, "scroll chord press has no scroll kick");
    paced(0.09);
    assert.notEqual(ctx.scrollX, 0, "two-axis scrolling resumes after settling");
    w.edge("D1", 1); w.edge("D2", 1);
  });
}
