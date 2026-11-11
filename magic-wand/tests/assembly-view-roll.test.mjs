// Two-finger twist roll in the assembly viewer: every event path rolls about
// the view axis, while orbit, pan, pinch zoom and reset keep their behaviour.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { Vector3 } from '../../docs/lib/three-0.185.1/three.module.min.js';
import { bindFreeViewControls } from '../hardware/printed-loop-wand/preview/free-view-controls.mjs';
import {
  RollingViewInput, bindTwistGestures, routeAssemblyWheel, rollHint, rollSupport, ROLL_PER_WHEEL_PIXEL,
} from '../hardware/carbon-rod-holders/assembly/view-roll.mjs';

const near = (a, b, epsilon = 1e-8) => assert.ok(Math.abs(a - b) < epsilon, a + ' != ' + b);
const vectorNear = (a, b, epsilon) => a.forEach((n, i) => near(n, b[i], epsilon));
function view() {
  const input = new RollingViewInput({ minDistance: 1, maxDistance: 10000 });
  input.setHome({ yaw: 0, pitch: 0, distance: 100, target: [0, 0, 0] });
  return input;
}
function fakeCanvas() {
  const handlers = new Map();
  return {
    handlers,
    addEventListener: (name, handler) => handlers.set(name, handler),
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 600, height: 600 }),
    focus() {}, setPointerCapture() {},
  };
}
function gesture(values = {}) {
  const event = { rotation: 0, scale: 1, clientX: 300, clientY: 300, prevented: false, ...values };
  event.preventDefault = () => { event.prevented = true; };
  return event;
}

test('a clockwise roll turns the model clockwise about the view axis only', () => {
  const input = view();
  const camera = input.camera(), target = [...input.target], distance = input.distance;
  assert.equal(input.roll(Math.PI / 2), true);
  // World +Y was screen up; after a clockwise quarter turn it points screen right.
  vectorNear(input.cameraUp(), [-1, 0, 0]);
  vectorNear(input.cameraBasis().right, [0, 1, 0]);
  vectorNear(input.camera(), camera);
  assert.deepEqual(input.target, target);
  assert.equal(input.distance, distance);
  assert.equal(input.mode, 'turn');
  assert.equal(input.roll(0), false);
  assert.equal(input.roll(Number.NaN), false);
});

test('roll keeps the view axis at any orbit, and orbit stays screen-relative after it', () => {
  const input = view();
  input.turn(57, 31);
  const back = input.cameraBasis().back, camera = input.camera();
  input.roll(.7);
  vectorNear(input.cameraBasis().back, back);
  vectorNear(input.camera(), camera);
  // A horizontal drag turns about the rolled screen up axis, so up is kept.
  const up = input.cameraUp();
  input.turn(50, 0);
  vectorNear(input.cameraUp(), up);
  input.pointerDown(1, 0, 0); input.pointerMove(1, 40, 0, 600);
  vectorNear(input.cameraUp(), up);
  input.pointerUp(1);
});

test('reset and standard views clear roll; fit and snapshots keep it', () => {
  const input = view();
  input.turn(20, 10); input.roll(1.1);
  const rolled = input.snapshot();
  const restored = view();
  assert.equal(restored.restore(JSON.parse(JSON.stringify(rolled))), true);
  vectorNear(restored.cameraUp(), input.cameraUp());
  input.fitBounds([-10, -10, -10], [10, 20, 30], { aspect: 1.5 });
  assert.deepEqual(input.snapshot().rotation, rolled.rotation);
  input.setView('front');
  vectorNear(input.cameraUp(), [0, 1, 0]);
  input.roll(.9);
  assert.equal(input.key({ key: '0' }, 600), true);
  vectorNear(input.cameraUp(), [0, 1, 0]);
  vectorNear(input.camera(), [0, 0, 100]);
});

test('touch twist rolls by the finger-pair angle while pinch and pan keep working', () => {
  const input = view();
  input.pointerDown(1, 0, 0); input.pointerDown(2, 100, 0);
  input.pointerMove(2, 0, 100, 600);
  vectorNear(input.cameraUp(), [-1, 0, 0]);
  near(input.distance, 100);
  assert.notDeepEqual(input.target, [0, 0, 0], 'the moving midpoint still pans');
  input.pointerUp(1); input.pointerUp(2);

  const pinch = view();
  pinch.pointerDown(1, 0, 0); pinch.pointerDown(2, 100, 0);
  const rotation = pinch.snapshot().rotation;
  pinch.pointerMove(2, 200, 0, 600);
  vectorNear(pinch.snapshot().rotation, rotation);
  near(pinch.distance, 50);

  // Crossing the ±180° angle boundary is a small twist, not nearly a full turn.
  const edge = view();
  edge.pointerDown(1, 0, 0); edge.pointerDown(2, -100, 1);
  edge.pointerMove(2, -100, -1, 600);
  assert.ok(new Vector3(...edge.cameraUp()).dot(new Vector3(0, 1, 0)) > .999);

  // A single finger still orbits instead of rolling.
  const single = view();
  single.pointerDown(1, 0, 0); single.pointerMove(1, 0, 600, 600, 1000);
  vectorNear(single.camera(), [0, 0, 100]);
  vectorNear(single.cameraUp(), [0, 1, 0]);
});

test('WebKit twist rolls and gesture pinch zooms, listening on the canvas only', () => {
  const input = view(), canvas = fakeCanvas();
  let frames = 0;
  const gestures = bindTwistGestures({ canvas, input, render: () => frames++, blurTarget: null });
  assert.deepEqual([...canvas.handlers.keys()].sort(), ['gesturechange', 'gestureend', 'gesturestart']);
  const start = gesture();
  canvas.handlers.get('gesturestart')(start);
  assert.equal(start.prevented, true, 'a twist on the canvas cannot zoom the page');
  assert.equal(gestures.active, true);
  canvas.handlers.get('gesturechange')(gesture({ rotation: 45 }));
  canvas.handlers.get('gesturechange')(gesture({ rotation: 90 }));
  vectorNear(input.cameraUp(), [-1, 0, 0]);
  near(input.distance, 100);
  const change = gesture({ rotation: 90, scale: 2 });
  canvas.handlers.get('gesturechange')(change);
  assert.equal(change.prevented, true);
  near(input.distance, 50);
  vectorNear(input.target, [0, 0, 0]);
  vectorNear(input.cameraUp(), [-1, 0, 0]);
  assert.equal(input.mode, 'turn');
  assert.equal(frames, 3);
  canvas.handlers.get('gestureend')(gesture());
  assert.equal(gestures.active, false);
});

test('a gesture change without its start sets a baseline instead of jumping', () => {
  const input = view(), canvas = fakeCanvas();
  bindTwistGestures({ canvas, input, render() {}, blurTarget: null });
  const rotation = input.snapshot().rotation;
  canvas.handlers.get('gesturechange')(gesture({ rotation: 120, scale: 3 }));
  assert.deepEqual(input.snapshot().rotation, rotation);
  near(input.distance, 100);
  canvas.handlers.get('gesturechange')(gesture({ rotation: 210, scale: 3 }));
  vectorNear(input.cameraUp(), [-1, 0, 0]);
});

test('window blur ends a WebKit gesture', () => {
  const input = view(), canvas = fakeCanvas(), blur = new Map();
  const gestures = bindTwistGestures({ canvas, input, render() {}, blurTarget: { addEventListener: (name, fn) => blur.set(name, fn) } });
  canvas.handlers.get('gesturestart')(gesture());
  blur.get('blur')();
  assert.equal(gestures.active, false);
});

test('touch PointerEvents own a two-finger gesture so WebKit touch events cannot double it', () => {
  const input = view(), canvas = fakeCanvas();
  bindTwistGestures({ canvas, input, render() {}, blurTarget: null });
  input.pointerDown(1, 0, 0); input.pointerDown(2, 100, 0);
  const rotation = input.snapshot().rotation;
  canvas.handlers.get('gesturestart')(gesture());
  canvas.handlers.get('gesturechange')(gesture({ rotation: 90, scale: 2 }));
  assert.deepEqual(input.snapshot().rotation, rotation);
  near(input.distance, 100);
  input.pointerMove(2, 0, 100, 600);
  vectorNear(input.cameraUp(), [-1, 0, 0]);
});

test('Option-scroll rolls without zooming; plain scroll and pinch keep zooming', () => {
  const options = { height: 600, pageHeight: 600 };
  const input = view();
  input.setMode('move');
  assert.equal(routeAssemblyWheel(input, { deltaX: -100, altKey: true }, options), true);
  near(input.distance, 100);
  // Natural-scrolling fingers moving right turn the model clockwise.
  const up = input.cameraUp();
  near(up[0], -Math.sin(100 * ROLL_PER_WHEEL_PIXEL));
  vectorNear(input.target, [0, 0, 0]);
  assert.equal(input.mode, 'move');

  for (const event of [{ deltaY: 100 }, { deltaY: 10, ctrlKey: true }, { deltaY: 100, altKey: true, ctrlKey: true },
    { deltaY: 100, altKey: true, metaKey: true }]) {
    const zoom = view(), rotation = zoom.snapshot().rotation;
    assert.equal(routeAssemblyWheel(zoom, event, options), true);
    assert.notEqual(zoom.distance, 100, JSON.stringify(event));
    assert.deepEqual(zoom.snapshot().rotation, rotation);
    assert.equal(zoom.mode, 'turn');
  }
  assert.equal(routeAssemblyWheel(view(), { deltaX: 0, deltaY: 0, altKey: true }, options), false);
});

test('the wand override reaches the shared wheel turn through the router', () => {
  const input = view(), rotation = input.snapshot().rotation;
  assert.equal(routeAssemblyWheel(input, { deltaY: 100 }, { height: 600, pageHeight: 600, wandRotate: true }), true);
  near(input.distance, 100);
  assert.notDeepEqual(input.snapshot().rotation, rotation);
  assert.equal(input.mode, 'turn');
});

test('pinch wheel is consumed during a WebKit gesture and zooms again afterwards', () => {
  const previousWindow = globalThis.window;
  globalThis.window = { addEventListener() {} };
  try {
    const input = view(), canvas = fakeCanvas();
    const gestures = bindTwistGestures({ canvas, input, render() {}, blurTarget: null });
    bindFreeViewControls({ canvas, input, height: () => 600, render() {}, chooseMode() {}, fit() {},
      wheel: event => routeAssemblyWheel(input, event, { gestureActive: gestures.active, height: 600, pageHeight: 600 }) });
    const wheel = values => {
      const event = { deltaY: 10, ctrlKey: true, clientX: 300, clientY: 300, prevented: false, ...values };
      event.preventDefault = () => { event.prevented = true; };
      canvas.handlers.get('wheel')(event);
      return event;
    };
    canvas.handlers.get('gesturestart')(gesture());
    const during = wheel();
    near(input.distance, 100);
    assert.equal(during.prevented, true, 'the matching browser pinch is still kept off the page');
    canvas.handlers.get('gestureend')(gesture());
    const after = wheel();
    assert.notEqual(input.distance, 100);
    assert.equal(after.prevented, true);
  } finally {
    if (previousWindow === undefined) delete globalThis.window;
    else globalThis.window = previousWindow;
  }
});

test('the hint names only roll inputs this browser can deliver', () => {
  assert.equal(rollHint({ twist: false, mac: true }), 'Option-scroll to roll');
  assert.equal(rollHint({ twist: true, mac: true }), 'Twist or Option-scroll to roll');
  assert.equal(rollHint({ twist: true, mac: false }), 'Twist or Alt-scroll to roll');
  // Chromium on a Mac trackpad exposes no rotation and no touch points.
  assert.deepEqual(rollSupport({}, { platform: 'MacIntel', maxTouchPoints: 0 }), { twist: false, mac: true });
  assert.deepEqual(rollSupport({ GestureEvent() {} }, { platform: 'MacIntel', maxTouchPoints: 0 }), { twist: true, mac: true });
  assert.deepEqual(rollSupport({}, { userAgentData: { platform: 'Windows' }, platform: 'Win32', maxTouchPoints: 10 }), { twist: true, mac: false });
  const html = readFileSync(new URL('../hardware/carbon-rod-holders/assembly/index.html', import.meta.url), 'utf8');
  assert.match(html, /Scroll or pinch to zoom · Option-scroll to roll/);
});
