// Regressions for full-turn accessory inspection: pole crossing must stay
// continuous, and camera-relative panning must keep working upside down.
import test from 'node:test';
import assert from 'node:assert/strict';
import { FreeViewInput } from '../hardware/printed-loop-wand/preview/free-view-input.mjs';
import { Vector3 } from '../../docs/lib/three-0.185.1/three.module.min.js';
import { applyViewerWheel } from '../hardware/carbon-rod-holders-r5/preview/wheel-input.mjs';
import { bindFreeViewControls } from '../hardware/printed-loop-wand/preview/free-view-controls.mjs';

const near = (a, b, epsilon = 1e-8) => assert.ok(Math.abs(a - b) < epsilon, a + ' != ' + b);
const vectorNear = (a, b) => a.forEach((n, i) => near(n, b[i]));
function view() {
  const input = new FreeViewInput({ minDistance: 1, maxDistance: 10000 });
  input.setHome({ yaw: 0, pitch: 0, distance: 100, target: [0, 0, 0] });
  return input;
}

test('vertical orbit passes both poles and completes repeated full turns', () => {
  const input = view();
  for (let orbit = 0; orbit < 3; orbit++) {
    for (let step = 0; step < 360; step++) input.turn(0, (Math.PI / 180) / .006);
    vectorNear(input.camera(), [0, 0, 100]);
    vectorNear(input.cameraUp(), [0, 1, 0]);
  }
});

test('camera up stays continuous when crossing the old vertical stop', () => {
  const input = view();
  input.turn(0, (Math.PI / 2 - .001) / .006);
  const before = new Vector3(...input.cameraUp());
  input.turn(0, .002 / .006);
  const after = new Vector3(...input.cameraUp());
  assert.ok(before.dot(after) > .9999);
  assert.ok(input.camera()[2] < 0, 'camera crosses the pole instead of stopping');
});

test('pan follows camera axes upside down without changing selected mode', () => {
  const input = view();
  input.turn(0, Math.PI / .006);
  const before = input.snapshot();
  input.pointerDown(1, 10, 20, 'move');
  input.pointerMove(1, 30, 40, 600);
  input.pointerUp(1);
  assert.equal(input.mode, 'turn');
  assert.deepEqual(input.snapshot().rotation, before.rotation);
  assert.ok(input.target[0] < 0 && input.target[1] < 0);
});

test('mixed orbits remain finite and snapshots preserve roll', () => {
  const input = view();
  for (let step = 0; step < 10000; step++) input.turn(17, 23);
  const saved = JSON.parse(JSON.stringify(input.snapshot()));
  const restored = view();
  assert.equal(restored.restore(saved), true);
  vectorNear(restored.camera(), input.camera());
  vectorNear(restored.cameraUp(), input.cameraUp());
  near(saved.rotation.reduce((sum, n) => sum + n*n, 0), 1);
  const before = restored.snapshot();
  assert.equal(restored.restore({ ...saved, rotation: [0, 0, 0, 0] }), false);
  assert.equal(restored.restore({ ...saved, rotation: [1e308, 1e308, 1e308, 1e308] }), false);
  assert.deepEqual(restored.snapshot(), before);
});

test('fit frames every corner at arbitrary rolled angles and narrow aspect', () => {
  const input = view();
  input.turn(219, 347);
  const min = [-40, -20, -15], max = [60, 150, 35], aspect = .45;
  const orientation = input.snapshot().rotation;
  input.fitBounds(min, max, { aspect });
  assert.deepEqual(input.snapshot().rotation, orientation);
  const camera = new Vector3(...input.camera());
  const back = new Vector3(...input.camera()).sub(new Vector3(...input.target)).normalize();
  const up = new Vector3(...input.cameraUp()), right = up.clone().cross(back).normalize();
  const tanY = Math.tan(input.fov * Math.PI / 360);
  for (let bits = 0; bits < 8; bits++) {
    const relative = new Vector3(...min.map((n, i) => bits & (1 << i) ? max[i] : n)).sub(camera);
    const depth = -relative.dot(back);
    assert.ok(depth > 0);
    assert.ok(Math.abs(relative.dot(up)) / depth < tanY);
    assert.ok(Math.abs(relative.dot(right)) / depth < tanY * aspect);
  }
});

test('standard top and bottom views can immediately rotate farther', () => {
  const input = view();
  for (const name of ['top', 'bottom']) {
    assert.equal(input.setView(name), true);
    const before = input.camera();
    input.turn(0, 30);
    assert.notDeepEqual(input.camera(), before);
  }
});

test('mouse wheel zooms while the wand override keeps rotating beyond either pole', () => {
  const input = view(), original = input.snapshot();
  applyViewerWheel(input, { deltaY: 100 }, 600, 600, false);
  assert.ok(input.distance > original.distance);
  assert.deepEqual(input.snapshot().rotation, original.rotation);
  const heights = [];
  for (let i = 0; i < 80; i++) {
    applyViewerWheel(input, { deltaY: 100 }, 600, 600, true);
    heights.push(input.camera()[1]);
  }
  assert.ok(Math.min(...heights) < -.99 * input.distance);
  assert.ok(Math.max(...heights) > .99 * input.distance);
  assert.equal(input.mode, 'turn');
});

test('mouse modifier panning and focus/fit shortcuts preserve orbit mode', () => {
  const previousWindow = globalThis.window;
  const handlers = new Map();
  const canvas = { addEventListener: (name, handler) => handlers.set(name, handler), focus() {}, setPointerCapture() {} };
  const input = view();
  let fits = 0;
  globalThis.window = { addEventListener() {} };
  try {
    bindFreeViewControls({ canvas, input, height: () => 600, render() {}, wheel: () => false, chooseMode() {}, fit: () => fits++ });
    for (const combination of [{ button: 1 }, { button: 2 }, { button: 0, shiftKey: true }]) {
      const rotation = input.snapshot().rotation;
      const before = [...input.target];
      handlers.get('pointerdown')({ ...combination, pointerId: 1, clientX: 0, clientY: 0, preventDefault() {} });
      handlers.get('pointermove')({ pointerId: 1, clientX: 30, clientY: 20 });
      handlers.get('pointerup')({ pointerId: 1 });
      assert.deepEqual(input.snapshot().rotation, rotation);
      assert.notDeepEqual(input.target, before);
      assert.equal(input.mode, 'turn');
    }
    handlers.get('keydown')({ key: 'f', preventDefault() {} });
    assert.equal(fits, 1);
    assert.equal(handlers.has('dblclick'), false, 'quick repeated drags cannot accidentally reframe');
    let suppressed = false;
    handlers.get('contextmenu')({ preventDefault: () => { suppressed = true; } });
    assert.equal(suppressed, true);
  } finally {
    if (previousWindow === undefined) delete globalThis.window;
    else globalThis.window = previousWindow;
  }
});

test('cursor-centred zoom keeps its target-plane point under the cursor', () => {
  const input = view(); input.turn(32, 57);
  const basis = input.cameraBasis(), x = .55, y = -.23, aspect = 1.8;
  const tangent = Math.tan(input.fov * Math.PI / 360), before = input.distance;
  const point = new Vector3(...input.target)
    .addScaledVector(new Vector3(...basis.right), x * before * tangent * aspect)
    .addScaledVector(new Vector3(...basis.up), y * before * tangent);
  input.zoom(.6); input.keepZoomAnchor(x, y, aspect, before);
  const relative = point.sub(new Vector3(...input.camera()));
  const depth = -relative.dot(new Vector3(...basis.back));
  near(relative.dot(new Vector3(...basis.right)) / (depth*tangent*aspect), x);
  near(relative.dot(new Vector3(...basis.up)) / (depth*tangent), y);
});

test('the remaining touch finger retains Pan after a pinch', () => {
  const input = view(); input.setMode('move');
  input.pointerDown(1, 0, 0); input.pointerDown(2, 30, 30);
  input.pointerMove(1, 5, 5, 600); input.pointerUp(2);
  const rotation = input.snapshot().rotation, before = [...input.target];
  input.pointerMove(1, 20, 20, 600);
  assert.deepEqual(input.snapshot().rotation, rotation);
  assert.notDeepEqual(input.target, before);
});

test('a full-height direct drag makes one complete turn', () => {
  const input = view();
  input.pointerDown(1, 0, 0); input.pointerMove(1, 0, 600, 600, 1000);
  vectorNear(input.camera(), [0, 0, 100]);
  vectorNear(input.cameraUp(), [0, 1, 0]);
});

test('toolbar shortcuts work without intercepting form typing or button arrows', () => {
  const previousWindow = globalThis.window, documentHandlers = new Map();
  const input = view(); let frames = 0;
  const canvas = { addEventListener() {}, ownerDocument: { addEventListener: (name, fn) => documentHandlers.set(name, fn) } };
  globalThis.window = { addEventListener() {} };
  try {
    bindFreeViewControls({ canvas, input, height: () => 600, render() {}, wheel: () => false,
      chooseMode: mode => input.setMode(mode), fit: () => frames++ });
    const key = (key, target) => documentHandlers.get('keydown')({ key, target, preventDefault() {} });
    const button = { closest: () => null }, field = { closest: () => ({}) };
    key('f', button); assert.equal(frames, 1);
    key('f', field); assert.equal(frames, 1);
    key('p', button); assert.equal(input.mode, 'move');
    key('r', button); assert.equal(input.mode, 'turn');
    const camera = input.camera(); key('ArrowDown', button); assert.deepEqual(input.camera(), camera);
    key('ArrowDown', canvas); assert.notDeepEqual(input.camera(), camera);
  } finally {
    if (previousWindow === undefined) delete globalThis.window;
    else globalThis.window = previousWindow;
  }
});
