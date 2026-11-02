// Exercise the real bridge's reversible manual-click flag without native input.
// The Mac owns the click; the device must preserve follow and consume quiet holds.
const test = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { createWand } = require('./harness.cjs');

for (const bridge of ['readable', 'fragments']) {
  test(`manual-click experiment preserves follow, entry and quiet-stop lights (${bridge})`, () => {
    const w = createWand({ bridge });
    w.calibrate(); w.loadBridge();
    const { ctx, frames } = w;
    ctx.wandManualClickExperiment = true;
    frames.length = 0;
    w.tap(); w.advance(0.4);
    assert(ctx.moveLatched, 'entry tap turns follow on');
    assert(!frames.some(f => f[2] === 1), 'entry never clicks');
    frames.length = 0;
    w.tap(); w.advance(0.4);
    assert(ctx.moveLatched, 'a manual click tap keeps follow on');
    assert(!frames.some(f => f[2] === 1), 'the bridge does not duplicate the native host click');

    w.edge('D1', 0); w.advance(0.25);
    // The real native hold boundary sends this command only after fresh physical
    // held evidence and after ruling out an actual scroll or native drag.
    ctx.setMouseFollow(false);
    assert.deepEqual(w.colors(), [0, 0, 0], 'quiet stop turns blue off while the button remains held');
    frames.length = 0;
    w.edge('D1', 1); w.advance(0.4);
    assert(!ctx.moveLatched && !frames.some(f => f[2] === 1), 'quiet hold release stays off and silent');
    w.tap(); w.advance(0.4);
    assert(ctx.moveLatched, 'the next entry tap starts follow normally');
    ctx.wandManualClickExperiment = false;
    frames.length = 0; w.tap(); w.advance(0.4);
    assert(!ctx.moveLatched && !frames.some(f => f[2] === 1), 'turning the experiment off restores the ordinary exit tap');
  });
}

test('manual mode blocks both pending and new automatic clicks, leaving the existing click state machine intact', () => {
  const source = readFileSync(join(__dirname, '../receiver/Sources/main.swift'), 'utf8');
  assert.match(source, /let gate=manualClickExperiment \? "manual-click experiment" : WandClickGate\.blocker/);
  assert.match(source, /guard ready,!restoring,!actionPause\.paused,!manualClickExperiment,!recordingPointerPaused/);
  assert.match(source, /guard self\.ready,!self\.restoring,!self\.actionPause\.paused,!self\.manualClickExperiment/);
  assert.match(source, /if value=="0" \{refreshManualClickExperiment\(\)\}/, 'a requested mode applies at physical release');
});
