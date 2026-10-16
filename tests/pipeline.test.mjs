// End to end through the demo's wiring: the real device code and bridge (via the Espruino shim),
// the receiver port, Agentic Mouse's HUD port and Agent Flow's primary control. Only button
// edges and gyro readings drive it, like the physical wand.
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { createPipeline } from "../docs/sim/pipeline.mjs";
import { MacScreen } from "../docs/sim/mac.mjs";

const require = createRequire(import.meta.url);
const { createWand, read } = require("./harness.cjs");
const manifest = JSON.parse(read("wand.json"));
const layout = JSON.parse(read("data/agentic-mouse-hud.json"));

function setup() {
  let pipeline = null;
  const w = createWand({ bridge: "fragments", onEvents: (events) => pipeline && pipeline.handle(events) });
  const mac = new MacScreen();
  const macEvents = [];
  mac.subscribe((event) => macEvents.push(event));
  let hud = null;
  pipeline = createPipeline({
    // Bluetooth writes are asynchronous; each command reaches the Puck on a later tick.
    send: (command) => w.clock.setTimeout(() => w.device.evaluate(command), 0),
    timers: w.clock, manifest, layout, mac,
    onHud: (state) => { hud = state; },
  });
  w.calibrate();
  w.loadBridge();
  pipeline.receiver.ready();
  w.advance(0.05);
  /** Turn the wand at a steady rate; +yaw is right and +pitch is down, in degrees. */
  const turn = (yaw, pitch, seconds) => {
    const steps = Math.round(seconds * 104);
    const rate = { yaw: yaw / seconds, pitch: pitch / seconds };
    for (let i = 0; i < steps; i++) w.paced(1 / 104, { x: -rate.pitch * 134, y: 0, z: -rate.yaw * 134 });
  };
  const press = (pin, seconds) => { w.edge(pin, 0); w.advance(seconds); w.edge(pin, 1); };
  return { w, mac, macEvents, pipeline, turn, press, get hud() { return hud; } };
}

test("Middle opens the HUD on Switch App, turning moves the outline without wrapping, a tap uses the card", () => {
  const s = setup();
  s.press("D2", 0.12);
  s.w.advance(0.1);
  assert(s.hud.open, "HUD opens");
  assert.equal(s.hud.cell, 11, "starts on Switch App");
  assert(s.w.ctx.hudOpen, "device is in HUD mode");
  assert.deepEqual(s.w.colors(), [1, 0.2, 0], "HUD is orange");

  s.turn(12, 0, 0.5);
  s.w.advance(0.1);
  assert.equal(s.hud.cell, 11, "the outline stops at the right edge instead of wrapping");
  s.turn(-10, 0, 0.5);
  s.w.advance(0.1);
  assert.equal(s.hud.cell, 8, "turning left moves one card to Back");
  s.turn(0, -9, 0.5);
  s.w.advance(0.1);
  assert.equal(s.hud.cell, 9, "turning up moves to Keys mode");

  s.press("D2", 0.12);
  s.w.advance(0.5);
  assert.equal(s.hud.action, null, "a tap waits for the Mac's double-click interval");
  s.w.advance(0.5);
  assert.equal(s.hud.action.text, "Opens Keys mode", "the outlined card is used once");
  assert(s.hud.open, "the HUD stays open after using a card");

  s.press("D2", 0.12); s.w.advance(0.15); s.press("D2", 0.12); s.w.advance(0.2);
  assert(!s.hud.open, "double tap closes the HUD");
  assert(!s.w.ctx.hudOpen, "device leaves HUD mode");
  assert.deepEqual(s.w.colors(), [0, 0, 0]);
});

test("holding Middle on a wheel card turns its wheel with tilt", () => {
  const s = setup();
  s.press("D2", 0.12); s.w.advance(0.1);
  s.turn(-8.5, 0, 0.4); s.turn(-8.5, 0, 0.4); s.turn(-8.5, 0, 0.4);
  s.turn(0, 8, 0.4);
  s.w.advance(0.1);
  assert.equal(s.hud.cell, 1, "Horizontal Scroll + Wheel is outlined");
  s.w.edge("D2", 0); s.w.advance(0.35);
  assert(s.hud.pressed, "holding Middle holds the card");
  s.turn(0, -9, 0.5);
  s.w.advance(0.1);
  assert.equal(s.hud.action.kind, "wheel");
  assert.equal(s.hud.action.text, "Scroll Left", "tilting up gives the wheel's up-ratchet action");
  s.w.edge("D2", 1); s.w.advance(0.2);
  assert(!s.hud.pressed && s.hud.open, "release ends the hold and keeps the HUD");
});

test("Bottom follows, clicks at a fixed point, drags, and Bottom from the HUD returns to the pointer", () => {
  const s = setup();
  s.press("D1", 0.06); s.w.advance(0.1);
  assert(s.w.ctx.moveLatched);
  assert.deepEqual(s.w.colors(), [0, 0, 1], "pointer is blue");
  const start = s.mac.location();
  s.turn(10, 0, 0.5);
  assert(s.mac.location().x > start.x + 100, "turning right moves the pointer right");
  s.w.advance(0.1);

  s.macEvents.length = 0;
  s.press("D1", 0.06);
  const fixed = s.mac.location();
  s.turn(4, 0, 0.2);
  assert.deepEqual(s.mac.location(), fixed, "the pointer stays still while the click is decided");
  s.w.advance(0.1);
  const clicks = s.macEvents.filter((event) => event.type === "down" || event.type === "up");
  assert.deepEqual(clicks.map((event) => event.type), ["down", "up"]);
  assert(clicks.every((event) => event.x === fixed.x && event.y === fixed.y), "click lands where the pointer stopped");

  s.w.advance(1);
  s.macEvents.length = 0;
  s.press("D1", 0.06); s.w.advance(0.05);
  s.w.edge("D1", 0); s.w.advance(0.3);
  s.turn(6, 4, 0.3);
  s.w.edge("D1", 1); s.w.advance(0.1);
  const types = s.macEvents.map((event) => event.type);
  assert(types.includes("down") && types.includes("drag") && types.at(-1) === "up", "tap then hold drags and drops");
  assert(s.w.ctx.moveLatched, "a drop restores prior HIGH following");

  s.press("D2", 0.12); s.w.advance(0.1);
  assert(s.hud.open);
  s.press("D1", 0.06); s.w.advance(0.1);
  assert(!s.hud.open, "Bottom closes the HUD");
  assert(s.w.ctx.moveLatched, "and the pointer follows again");
});

test("Bottom + Middle scrolls both axes as separate wheel events and never clicks", () => {
  const s = setup();
  s.macEvents.length = 0;
  s.w.edge("D1", 0); s.w.advance(0.03); s.w.edge("D2", 0); s.w.advance(0.1);
  assert.deepEqual(s.w.colors(), [0, 1, 1], "scrolling is cyan");
  s.turn(10, 10, 1);
  s.w.edge("D1", 1); s.w.edge("D2", 1); s.w.advance(0.2);
  const scrolls = s.macEvents.filter((event) => event.type === "scroll");
  assert(scrolls.length > 4);
  assert(scrolls.every((event) => event.dx === 0 || event.dy === 0), "each wheel event carries one axis");
  const x = scrolls.reduce((sum, event) => sum + event.dx, 0);
  const y = scrolls.reduce((sum, event) => sum + event.dy, 0);
  assert(x > 0 && y > 0, "a diagonal scrolls right and down");
  assert(Math.abs(x / y - 1.4) < 0.15, "horizontal output is boosted 1.4 times");
  assert(!s.macEvents.some((event) => event.type === "down"), "no click");
  assert(!s.hud || !s.hud.open, "no HUD");
});

test("Top starts and stops Agent Flow, and the recording light yields to other modes", () => {
  const s = setup();
  s.press("D30", 0.08); s.w.advance(0.05);
  assert(s.pipeline.agentFlow.recording, "first press starts recording");
  assert.deepEqual(s.w.colors(), [1, 0, 0], "recording is red");
  s.press("D1", 0.06); s.w.advance(0.05);
  assert.deepEqual(s.w.colors(), [0, 0, 1], "pointer blue wins over recording");
  s.press("D1", 0.06); s.w.advance(0.05); s.press("D1", 0.06); s.w.advance(0.3);
  assert(!s.w.ctx.moveLatched);
  assert.deepEqual(s.w.colors(), [1, 0, 0], "recording red returns when idle");
  s.press("D30", 0.08); s.w.advance(0.05);
  assert(!s.pipeline.agentFlow.recording, "a later press stops on release");
  assert.deepEqual(s.w.colors(), [0, 0, 0]);
});
