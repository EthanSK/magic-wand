// Playback must survive scrubbing, background pauses and replay without
// accumulating scene transforms or carrying elapsed time across a pause.
import test from 'node:test';
import assert from 'node:assert/strict';
import { AssemblyTimeline } from '../hardware/printed-loop-wand/preview/assembly-timeline.mjs';

const steps = [{ duration: 2, id: 'insert' }, { duration: 3, id: 'retain' }];

test('seek is deterministic in both directions and at step boundaries', () => {
  const t = new AssemblyTimeline(steps);
  t.seek(3.5); assert.equal(t.state.index, 1); assert.equal(t.state.fraction, .5);
  t.seek(2); assert.equal(t.state.index, 1); assert.equal(t.state.fraction, 0);
  t.seek(1); assert.equal(t.state.index, 0); assert.equal(t.state.fraction, .5);
  t.seek(-20); assert.equal(t.time, 0);
  t.seek(20); assert.equal(t.state.fraction, 1); assert.equal(t.time, 5);
});

test('pause and speed changes do not consume time from the previous frame', () => {
  const t = new AssemblyTimeline(steps);
  t.play(); t.tick(1000); t.tick(1500); assert.equal(t.time, .5);
  t.pause(); t.tick(99999); assert.equal(t.time, .5);
  t.play(); t.tick(100000); t.tick(100500); assert.equal(t.time, 1);
  t.setSpeed(2); t.tick(101000); t.tick(101500); assert.equal(t.time, 2);
});

test('playback stops on the final pose and replays from the start', () => {
  const t = new AssemblyTimeline(steps);
  t.play(); t.tick(0); t.tick(6000);
  assert.equal(t.time, 5); assert.equal(t.playing, false); assert.equal(t.state.fraction, 1);
  t.play(); assert.equal(t.time, 0); assert.equal(t.playing, true);
  t.tick(7000); assert.equal(t.time, 0);
});

test('changing recipes resets playback and validates its input', () => {
  const t = new AssemblyTimeline(steps); t.play(); t.seek(4);
  t.setSteps([{ duration: 1 }]); assert.equal(t.time, 0); assert.equal(t.playing, false);
  for (const value of [[], [{ duration: 0 }], [{ duration: NaN }]]) assert.throws(() => t.setSteps(value));
  assert.throws(() => t.seek(Infinity)); assert.throws(() => t.setSpeed(-1));
});
