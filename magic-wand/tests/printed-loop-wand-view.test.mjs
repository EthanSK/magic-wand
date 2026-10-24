// Printed loop wand preview input: scrolling turns by default (the wand's Bottom hold arrives as
// scroll events), Move and Zoom are deliberate, pinch always zooms, and large inputs are limited.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { ViewInput, normalizeWheel, MODES, frameBounds } from "../hardware/printed-loop-wand/preview/view-input.mjs";

const preview = join(dirname(fileURLToPath(import.meta.url)), "..", "hardware", "printed-loop-wand", "preview");
const HOME = { yaw: 1.3, pitch: 0.22, distance: 900, target: [0, -10, 250] };
const H = 800;

function view(mode) {
  const v = new ViewInput({ fov: 32, mode });
  v.setHome(HOME);
  return v;
}
const right = (v) => [Math.cos(v.yaw), 0, -Math.sin(v.yaw)];
const dot = (a, b) => a.reduce((s, x, i) => s + x * b[i], 0);

test("reset framing keeps every box corner inside wide and tall viewports", () => {
  const min = [-20, -220, -30], max = [20, 60, 478];
  for (const aspect of [0.35, 0.62, 1, 2.4]) {
    const home = frameBounds(min, max, { aspect });
    const v = view();
    v.setHome(home);
    const camera = v.camera();
    const sy = Math.sin(home.yaw), cy = Math.cos(home.yaw), sp = Math.sin(home.pitch), cp = Math.cos(home.pitch);
    const right = [cy, 0, -sy], up = [-sp * sy, cp, -sp * cy], back = [cp * sy, sp, cp * cy];
    const tanY = Math.tan(32 * Math.PI / 360);
    for (let bits = 0; bits < 8; bits++) {
      const p = camera.map((c, i) => ((bits & (1 << i)) ? max[i] : min[i]) - c);
      const depth = -dot(p, back);
      assert.ok(depth > 0);
      assert.ok(Math.abs(dot(p, right)) / (depth * tanY * aspect) < 0.86);
      assert.ok(Math.abs(dot(p, up)) / (depth * tanY) < 0.86);
    }
    v.zoomSteps(2);
    v.turn(40, 20);
    const scale = v.distance / home.distance, yaw = v.yaw;
    const next = frameBounds(min, max, { aspect: aspect / 2 });
    v.setHome(next, true);
    assert.equal(v.yaw, yaw, "resizing preserves the user's chosen angle");
    assert.ok(Math.abs(v.distance / next.distance - scale) < 1e-12, "resizing preserves relative zoom");
  }
});

test("scrolling turns the model by default instead of zooming", () => {
  const v = view();
  assert.equal(v.mode, "turn");
  assert.equal(v.wheel({ deltaY: 100, deltaMode: 0 }, H), true);
  assert.equal(v.distance, HOME.distance);
  assert.notEqual(v.pitch, HOME.pitch);
  assert.deepEqual(v.target, HOME.target);
  const pitch = v.pitch;
  v.wheel({ deltaX: 100, deltaMode: 0 }, H);
  assert.notEqual(v.yaw, HOME.yaw, "horizontal scrolling turns too");
  assert.equal(v.pitch, pitch);
  assert.equal(v.distance, HOME.distance);
});

test("pinch and Zoom mode zoom deliberately, within limits", () => {
  const v = view();
  v.wheel({ deltaY: -50, ctrlKey: true }, H);
  assert.ok(v.distance < HOME.distance, "pinch out zooms in even in Turn mode");
  v.reset();
  v.setMode("zoom");
  v.wheel({ deltaY: 100 }, H);
  assert.ok(v.distance > HOME.distance);
  assert.equal(v.yaw, HOME.yaw);
  v.reset();
  v.zoomSteps(1);
  assert.ok(v.distance < HOME.distance);
  v.zoomSteps(-2);
  assert.ok(v.distance > HOME.distance);
  for (let i = 0; i < 200; i++) v.zoomSteps(1);
  assert.equal(v.distance, v.minDistance);
  for (let i = 0; i < 200; i++) v.zoomSteps(-1);
  assert.equal(v.distance, v.maxDistance);
});

test("Move mode drags and scrolls the view without turning or zooming", () => {
  const v = view("move");
  v.pointerDown(1, 100, 100);
  v.pointerMove(1, 160, 100, H);
  v.pointerUp(1);
  assert.equal(v.yaw, HOME.yaw);
  assert.equal(v.distance, HOME.distance);
  // Dragging right moves the model right, so the view's centre moves left.
  assert.ok(dot(v.target, right(v)) < dot(HOME.target, right(v)));
  const after = [...v.target];
  v.wheel({ deltaY: 80 }, H);
  assert.notDeepEqual(v.target, after);
  assert.equal(v.distance, HOME.distance);
});

test("dragging turns, and a mode change or cancel never jumps a drag in progress", () => {
  const v = view();
  v.pointerDown(1, 0, 0);
  v.pointerMove(1, 50, 0, H);
  assert.ok(v.yaw < HOME.yaw);
  const yaw = v.yaw;
  v.setMode("move");
  assert.equal(v.pointerMove(1, 400, 400, H), false, "the old drag ends with the mode change");
  assert.equal(v.yaw, yaw);
  assert.deepEqual(v.target, HOME.target);
  v.pointerDown(2, 0, 0);
  v.cancel();
  assert.equal(v.pointerMove(2, 100, 100, H), false);
});

test("two fingers pinch to zoom", () => {
  const v = view();
  v.pointerDown(1, 100, 100);
  v.pointerDown(2, 200, 100);
  v.pointerMove(2, 300, 100, H);
  assert.ok(v.distance < HOME.distance);
  assert.equal(v.yaw, HOME.yaw);
});

test("wheel units are normalised and huge or invalid inputs are limited", () => {
  assert.deepEqual(normalizeWheel({ deltaY: 3, deltaMode: 1 }), { dx: 0, dy: 48 });
  assert.deepEqual(normalizeWheel({ deltaY: 1, deltaMode: 2 }, 600), { dx: 0, dy: 240 });
  assert.deepEqual(normalizeWheel({ deltaX: -1e9, deltaY: 1e9 }), { dx: -240, dy: 240 });
  assert.deepEqual(normalizeWheel({ deltaY: Number.NaN }), { dx: 0, dy: 0 });
  const a = view(), b = view();
  a.wheel({ deltaY: 1e9 }, H);
  b.wheel({ deltaY: 240 }, H);
  assert.equal(a.pitch, b.pitch);
  assert.ok(Math.abs(a.pitch) <= 1.45);
  assert.equal(view().wheel({ deltaY: 0 }, H), false, "empty events are left alone");
  const z = view("zoom");
  for (let i = 0; i < 100; i++) z.wheel({ deltaY: 1e9 }, H);
  assert.equal(z.distance, z.maxDistance);
});

test("keyboard follows the mode and Reset view restores the framing", () => {
  const v = view();
  assert.equal(v.key({ key: "ArrowLeft" }, H), true);
  assert.notEqual(v.yaw, HOME.yaw);
  assert.equal(v.key({ key: "+" }, H), true);
  assert.ok(v.distance < HOME.distance);
  assert.equal(v.key({ key: "m" }, H), true);
  assert.equal(v.mode, "move");
  v.key({ key: "ArrowUp" }, H);
  assert.notDeepEqual(v.target, HOME.target);
  assert.equal(v.key({ key: "0" }, H), true);
  assert.deepEqual([v.yaw, v.pitch, v.distance, v.target], [HOME.yaw, HOME.pitch, HOME.distance, HOME.target]);
  assert.equal(v.key({ key: "q" }, H), false);
  assert.equal(v.setMode("spin"), false);
  assert.deepEqual(MODES, ["turn", "move", "zoom"]);
});

test("the page wires scrolling to the 3D view only and shows the controls", () => {
  const source = readFileSync(join(preview, "preview.mjs"), "utf8");
  const html = readFileSync(join(preview, "index.html"), "utf8");
  const wheel = [...source.matchAll(/(\w+)\.addEventListener\('wheel'/g)].map((m) => m[1]);
  assert.deepEqual(wheel, ["canvas"], "no page- or sidebar-wide wheel capture");
  assert.match(source, /passive: false/);
  assert.match(source, /'pointercancel', 'lostpointercapture'/);
  assert.match(source, /addEventListener\('blur'/);
  for (const label of ["Turn", "Move", "Zoom", "Reset view"]) assert.ok(html.includes(`>${label}</button>`), label);
  assert.match(html, /aria-label="Zoom in"/);
  assert.match(html, /aria-label="Zoom out"/);
  assert.doesNotMatch(source + html, /whether/i);
  assert.doesNotMatch(source + html, /AXSlider|role="slider"/);
});
