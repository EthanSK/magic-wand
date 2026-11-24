import test from 'node:test';
import assert from 'node:assert/strict';
import {installDrawingMode} from '../hardware/carbon-rod-holders/assembly/viewer-drawing.mjs';

// Exercise pointer lifetime and view ownership without a browser transport's
// synthetic held-button state. Actual browser input is checked separately. GPT-6.1 Sol.
function page() {
  const calls = [], context = new Proxy({}, {get: (_, name) => (...args) => calls.push([name, ...args])});
  class Element extends EventTarget {
    children = []; dataset = {}; inert = false;
    append(...elements) { this.children.push(...elements); }
    setAttribute(name, value) { this[name] = value; }
    getContext() { return context; }
    getBoundingClientRect() { return {left: 10, top: 20, width: this.width ?? 800, height: this.height ?? 600}; }
    focus() { document.focused = this; }
    setPointerCapture(id) { this.capture = id; }
    hasPointerCapture(id) { return this.capture === id; }
    releasePointerCapture(id) { this.capture = null; this.dispatchEvent(event('lostpointercapture', {pointerId: id})); }
  }
  const document = new EventTarget();
  document.createElement = () => new Element();
  document.defaultView = {devicePixelRatio: 2};
  const view = new Element(); view.ownerDocument = document;
  let resize, starts = 0;
  const previousObserver = globalThis.ResizeObserver;
  globalThis.ResizeObserver = class {constructor(callback) { resize = callback; } observe() {}};
  const targets = [new Element(), new Element()]; targets[1].inert = true;
  let drawing;
  try { drawing = installDrawingMode({view, freezeTargets: targets, onStart: () => starts++}); }
  finally { globalThis.ResizeObserver = previousObserver; }
  const [canvas, toolbar] = view.children, [toggle, undo, clear] = toolbar.children;
  return {document, view, canvas, toggle, undo, clear, targets, calls, drawing, resize, starts: () => starts};
}
function event(type, values = {}) {
  return Object.assign(new Event(type, {cancelable: true}), values);
}
function stroke(canvas, id, x = 30) {
  canvas.dispatchEvent(event('pointerdown', {pointerId: id, button: 0, clientX: x, clientY: 40}));
  canvas.dispatchEvent(event('pointermove', {pointerId: id, clientX: x + 10, clientY: 50,
    getCoalescedEvents: () => [{clientX: x + 5, clientY: 45}, {clientX: x + 10, clientY: 50}]}));
  canvas.dispatchEvent(event('pointerup', {pointerId: id}));
}

test('drawing locks the view, paints a continuous path and preserves ink after Done', () => {
  const p = page();
  assert.equal(p.canvas.hidden, true);
  p.toggle.dispatchEvent(event('click'));
  assert.equal(p.starts(), 1);
  assert.ok(p.targets.every(target => target.inert));
  stroke(p.canvas, 1);
  assert.ok(p.calls.some(call => JSON.stringify(call) === JSON.stringify(['lineTo', 30, 30])));
  assert.equal(p.undo.disabled, false);
  assert.equal(p.canvas.capture, null);
  p.toggle.dispatchEvent(event('click'));
  assert.equal(p.canvas.hidden, false);
  assert.equal(p.canvas.dataset.active, 'false');
  assert.deepEqual(p.targets.map(target => target.inert), [false, true]);
  p.undo.dispatchEvent(event('click'));
  assert.equal(p.canvas.hidden, true);
});

test('cancelled pointers cannot continue drawing; a new stroke and keyboard undo still work', () => {
  const p = page(); p.toggle.dispatchEvent(event('click'));
  p.canvas.dispatchEvent(event('pointerdown', {pointerId: 1, button: 0, clientX: 30, clientY: 40}));
  p.canvas.dispatchEvent(event('pointercancel', {pointerId: 1}));
  const count = p.calls.length;
  p.canvas.dispatchEvent(event('pointermove', {pointerId: 1, clientX: 100, clientY: 100}));
  assert.equal(p.calls.length, count);
  stroke(p.canvas, 2);
  p.document.dispatchEvent(event('keydown', {key: 'z', metaKey: true}));
  assert.equal(p.undo.disabled, false);
  p.document.dispatchEvent(event('keydown', {key: 'z', ctrlKey: true}));
  assert.equal(p.undo.disabled, true);
  p.document.dispatchEvent(event('keydown', {key: 'Escape'}));
  assert.equal(p.toggle.textContent, 'Draw');
  assert.equal(p.document.focused, p.toggle);
});

test('Clear, a changed view and resizing discard ink that would point at the wrong part', () => {
  const p = page(); p.toggle.dispatchEvent(event('click'));
  for (const reset of [() => p.clear.dispatchEvent(event('click')), p.drawing.clear,
    () => { p.view.width = 700; p.resize(); }]) {
    stroke(p.canvas, 1);
    reset();
    assert.equal(p.undo.disabled, true);
    assert.equal(p.canvas.capture, null);
  }
});
