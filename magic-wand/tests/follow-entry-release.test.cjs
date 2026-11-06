// Check the real bridge's follow choice at each physical edge. A held mouse
// button can own precision/scroll/drag input without starting latched follow.
const test = require('node:test');
const assert = require('node:assert/strict');
const { createWand } = require('./harness.cjs');

for (const bridge of ['readable', 'fragments']) {
  for (const manual of [false, true]) {
    test(`follow entry waits for release (${bridge}, manual=${manual})`, () => {
      const w = createWand({ bridge });
      w.calibrate(); w.loadBridge();
      w.ctx.wandManualClickExperiment = manual;
      w.lines.length = 0; w.frames.length = 0;

      w.edge('D1', 0);
      w.advance(0.06);
      assert.equal(w.ctx.moveLatched, false, 'down never enables follow');
      assert(!w.lines.includes('@FOLLOW 1'), 'the receiver never sees premature entry');
      assert(w.device.awake, 'held controls still receive sensor input');
      w.edge('D1', 1);
      assert.equal(w.ctx.moveLatched, true, 'a short entry release enables follow');
      assert.equal(w.lines.filter(l => l === '@FOLLOW 1').length, 1);
      w.advance(0.4);
      assert(!w.frames.some(f => f[2] === 1), 'entry does not click');

      if (!manual) {
        w.edge('D1', 0);
        assert.equal(w.ctx.moveLatched, true, 'exit keeps its existing down behavior');
        w.advance(0.06); w.edge('D1', 1);
        assert.equal(w.ctx.moveLatched, false, 'exit keeps its existing release behavior');
        assert(!w.frames.some(f => f[2] === 1), 'ordinary exit does not click');
      }
    });
  }

  test(`Sense held readings keep follow off until release (${bridge})`, () => {
    const w = createWand({ bridge: false });
    w.calibrate();
    w.device.evaluate('global.wandRawPointer=true;global.wandHostHeldScroll=true;');
    w.loadBridge(bridge); w.lines.length = 0;
    w.edge('D1', 0); w.advance(0.12); // Existing cold-sensor and switch settling.
    w.motion({ x: 134, y: 0, z: 268 });
    const held = w.lines.filter(l => l.startsWith('@RAW '));
    assert(held.length > 0, 'native scroll/drag receives held sensor readings');
    assert(held.every(l => (Number(l.split(',')[3]) & 5) === 5),
      'held and follow-off flags stay distinct');
    assert(!w.lines.includes('@FOLLOW 1'));
    w.edge('D1', 1);
    assert.equal(w.ctx.moveLatched, true);
    assert.equal(w.lines.filter(l => l === '@FOLLOW 1').length, 1);
    w.lines.length = 0; w.advance(0.08); w.motion(); // Existing release jolt guard.
    assert(w.lines.some(l => l.startsWith('@RAW ') && (Number(l.split(',')[3]) & 5) === 0),
      'only fresh released readings enter normal follow');
  });

  test(`a held entry and cancelled entry cannot latch follow (${bridge})`, () => {
    const w = createWand({ bridge });
    w.calibrate(); w.loadBridge(); w.lines.length = 0;
    w.edge('D1', 0); w.advance(0.4);
    assert.equal(w.ctx.moveLatched, false, 'a longer hold does not enable follow');
    w.ctx.setHUDOpen(true); w.ctx.setHUDOpen(false);
    w.ctx.setWandReviewTracking(true); w.ctx.setWandReviewTracking(false);
    w.advance(1.1);
    assert(w.ctx.gyroAwake, 'closing HUD/review cannot stop a held entry sensor');
    assert(!w.lines.includes('@FOLLOW 1'));
    w.edge('D1', 1);
    assert.equal(w.ctx.moveLatched, false, 'held release keeps its existing off choice');
    w.advance(1.1);
    assert(!w.ctx.gyroAwake, 'ordinary sleep resumes after releasing the hold');

    w.edge('D1', 0); w.advance(0.03);
    w.ctx.setMouseFollow(false); w.edge('D1', 1);
    assert.equal(w.ctx.moveLatched, false, 'cancellation clears the pending entry');
  });
}
