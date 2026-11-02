import test from 'node:test';
import assert from 'node:assert/strict';
import { ViewInput } from '../../printed-loop-wand/preview/view-input.mjs';
import { applyViewerWheel } from './wheel-input.mjs';

test('mouse wheel zooms while drag/arrow mode remains Turn', () => {
  const input = new ViewInput(); const before = input.snapshot();
  applyViewerWheel(input, { deltaY: 60 }, 600, 800);
  assert.ok(input.distance > before.distance);
  assert.equal(input.yaw, before.yaw); assert.equal(input.pitch, before.pitch);
  assert.equal(input.mode, 'turn');
  input.drag(20, 0, 600); assert.notEqual(input.yaw, before.yaw);
});
test('explicit wand override rotates immediately, and pinch still zooms', () => {
  const input = new ViewInput({ mode: 'move' }); const before = input.snapshot();
  applyViewerWheel(input, { deltaY: 60 }, 600, 800, true);
  assert.notEqual(input.pitch, before.pitch); assert.equal(input.distance, before.distance);
  assert.equal(input.mode, 'move');
  const pitch = input.pitch;
  applyViewerWheel(input, { deltaY: 10, ctrlKey: true }, 600, 800, true);
  assert.equal(input.pitch, pitch); assert.notEqual(input.distance, before.distance);
});
