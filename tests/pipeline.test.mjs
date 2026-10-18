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

function setup({legacy=false}={}) {
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
  if(legacy)w.device.evaluate(read("tests/fixtures/control-v2-bridge.js"));else w.loadBridge();
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

test("opening with held Middle navigates then selects exactly once on release", () => {
  const s = setup();
  s.w.edge("D2", 0); s.w.advance(0.35);
  s.turn(-10, 0, 0.5); s.turn(0, -9, 0.5);
  assert.equal(s.hud.cell, 9);
  assert.equal(s.hud.action, null);
  s.w.edge("D2", 1); s.w.advance(0.1);
  assert.equal(s.hud.action.text, "Opens Keys mode");
  assert(s.hud.open);
});

test("screen-edge overflow is discarded, so reversing responds immediately", () => {
  const s = setup();
  for (let i = 0; i < 200; i++) s.pipeline.receiver.handleFrame(0, 127, 0);
  assert.equal(s.mac.location().y, s.mac.height - 1);
  s.pipeline.receiver.handleFrame(0, -3, 0);
  assert.equal(s.mac.location().y, s.mac.height - 4);
});

test("held LOW circles use wheel events and cyan; release cancels without a click", () => {
  const s = setup(); s.pipeline.receiver.handleLine("@BOTTOM 1"); let x = 80, y = 0;
  for (let i = 1; i <= 105; i++) {
    const a = i / 35 * Math.PI * 2, nx = 80 * Math.cos(a), ny = 80 * Math.sin(a);
    s.w.advance(1 / 35);
    s.pipeline.receiver.handleFrame(Math.round(nx - x), Math.round((ny - y) * 1.4), 0); x = nx; y = ny;
  }
  assert(s.macEvents.some(e => e.type === "scroll" && e.dy > 0));
  s.w.advance(0.01);
  assert.deepEqual(s.w.colors(), [0, 1, 1]);
  s.pipeline.receiver.handleLine("@BOTTOM 0");
  assert(!s.pipeline.receiver.pointerRouter.circle.active);
  const count = s.macEvents.filter(e => e.type === "scroll").length;
  s.pipeline.receiver.handleFrame(20, 20, 0);
  assert.equal(s.macEvents.filter(e => e.type === "scroll").length, count);
});

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
  s.w.advance(0.15);
  assert.equal(s.hud.action, null, "a tap waits for the shortened double-click interval");
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

test("HIGH clicks once after settling, a tap exits; tap then hold drags and restores HIGH", () => {
  const s=setup();s.press("D1",.06);s.w.advance(.1);
  assert(s.w.ctx.moveLatched);assert.deepEqual(s.w.colors(),[0,0,1]);
  assert(!s.macEvents.some(e=>e.type==="down"),"entry never clicks");
  const start=s.mac.location();s.turn(10,0,.5);
  assert(s.mac.location().x>start.x+100);
  s.turn(0,0,.19);assert(!s.macEvents.some(e=>e.type==="down"));
  const fixed=s.mac.location();s.turn(0,0,.15);
  let clicks=s.macEvents.filter(e=>e.type==="down"||e.type==="up");
  assert.deepEqual(clicks.map(e=>e.type),["down","up"]);
  assert(clicks.every(e=>e.x===fixed.x&&e.y===fixed.y));
  s.w.advance(2);assert.equal(s.macEvents.filter(e=>e.type==="down").length,1,"stillness does not repeat");
  s.press("D1",.06);assert(!s.w.ctx.moveLatched,"a single tap exits HIGH");
  s.w.advance(.9);s.press("D1",.06);s.w.advance(.9);s.macEvents.length=0;
  s.press("D1",.06);s.w.advance(.05);s.w.edge("D1",0);s.w.advance(.3);
  s.turn(6,4,.3);s.w.edge("D1",1);s.w.advance(.1);
  const types=s.macEvents.map(e=>e.type);
  assert(types.includes("down")&&types.includes("drag")&&types.at(-1)==="up");
  assert(s.w.ctx.moveLatched,"a drop restores prior HIGH");
  s.press("D2",.12);s.w.advance(.1);assert(s.hud.open);
  s.press("D1",.06);s.w.advance(.1);
  assert(s.hud.open&&s.w.ctx.hudOpen,"Bottom leaves the Middle HUD open");
});

test("Legacy Bottom + Middle scrolls both axes as separate wheel events and never clicks", () => {
  const s = setup({legacy:true});
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
  s.press("D1", 0.06); s.w.advance(0.4);
  assert.deepEqual(s.w.colors(), [0, 0, 1], "mouse stays blue while recording");
  s.w.advance(0.35);
  assert.deepEqual(s.w.colors(), [0, 0, 1], "mouse stays steady blue");
  s.press("D1", 0.06); s.w.advance(0.3);
  assert(!s.w.ctx.moveLatched);
  assert.deepEqual(s.w.colors(), [1, 0, 0], "recording red returns when idle");
  s.press("D30", 0.08); s.w.advance(0.05);
  assert(!s.pipeline.agentFlow.recording, "a later press stops on release");
  assert.deepEqual(s.w.colors(), [0, 0, 0]);
});


test('receiver accepts wide UART motion and still clamps to the screen', () => {
 const s=setup();const before=s.mac.location();
 s.pipeline.receiver.handleFrame(300,200,0);
 assert.deepEqual(s.mac.location(),{x:Math.min(before.x+300,s.mac.width-1),y:Math.min(before.y+200,s.mac.height-1)});
 s.pipeline.receiver.handleFrame(-4095,-4095,0);assert.deepEqual(s.mac.location(),{x:0,y:0});
 const at=s.mac.location();s.pipeline.receiver.handleFrame(4096,0,0);assert.deepEqual(s.mac.location(),at);
});


test("Bottom double tap recenters but a held second press remains a drag", () => {
 const s=setup();
 s.mac.mouse('move',{x:100,y:120});
 s.press('D1',0.08);s.w.advance(0.08);s.press('D1',0.08);s.w.advance(0.05);
 assert.deepEqual(s.mac.location(),{x:s.mac.width/2,y:s.mac.height/2});
 assert(s.w.ctx.moveLatched,'recenter keeps follow active');
 assert.equal(s.macEvents.filter(e=>e.type==='down').length,0,'recenter does not click');
 s.w.advance(0.5);s.press('D1',0.08);s.w.advance(0.08);s.w.edge('D1',0);s.w.advance(0.3);
 assert(s.mac.buttonDown,'second press held drags');
 s.w.edge('D1',1);s.w.advance(0.05);assert(!s.mac.buttonDown);
});

test('Bottom double tap centres mouse while preserving the independent HUD',()=>{
 for(const mode of ['off','mouse','hud','scroll']) {
  const s=setup();
  if(mode==='mouse'){s.press('D1',.06);s.w.advance(.5);}
  if(mode==='hud'){s.press('D2',.06);s.w.advance(.5);}
  if(mode==='scroll'){s.pipeline.receiver.scrollActive=true;}
  s.press('D1',.06);s.w.advance(.07);s.press('D1',.06);s.w.advance(.1);
  assert(s.w.ctx.moveLatched,mode+' enables follow');
  assert.equal(s.pipeline.receiver.hudSession,mode==='hud',mode+' preserves the Middle HUD');assert(!s.pipeline.receiver.scrollActive);
  const p=s.mac.location();assert.equal(p.x,s.mac.width/2);assert.equal(p.y,s.mac.height/2);
  assert.equal(s.pipeline.receiver.buttons,0);
 }
});


test('Legacy releasing a page-scroll chord enables mouse follow even when it started off',()=>{
 for(const prior of [false,true]) {
  const s=setup({legacy:true});
  if(prior){s.press('D1',.06);s.w.advance(.4);}
  s.w.edge('D1',0);s.w.advance(.03);s.w.edge('D2',0);s.w.advance(.15);
  s.turn(0,8,.4);s.w.edge('D1',1);s.w.edge('D2',1);s.w.advance(.3);
  assert(s.w.ctx.moveLatched,'page scroll returns to mouse follow');
  assert(s.pipeline.receiver.dwell.following);
  assert(!s.pipeline.receiver.scrollActive);
 }
});
