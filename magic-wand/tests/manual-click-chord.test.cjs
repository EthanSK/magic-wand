const test = require('node:test');
const assert = require('node:assert/strict');
const { createWand, read } = require('./harness.cjs');

for (const bridge of ['readable', 'fragments']) {
  for (const following of [false, true]) {
    for (const centreFirstRelease of [false, true]) {
      test(`centre held then left clicks once (${bridge}, follow ${following}, centre released first ${centreFirstRelease})`, () => {
        const w = createWand({ bridge });
        w.calibrate(); w.loadBridge();
        w.ctx.setMouseFollow(following);
        w.edge('D1', 0); w.advance(0.4);
        w.lines.length = 0; w.frames.length = 0;
        w.edge('D2', 0);
        assert.equal(w.lines.filter(l => l === '@LEFTCLICK').length, 1, 'click arrives on the left press, before the 80 ms HUD timer');
        w.advance(0.5);
        assert.equal(w.lines.filter(l => l === '@LEFTCLICK').length, 1, 'holding does not repeat');
        w.edge(centreFirstRelease ? 'D1' : 'D2', 1);
        w.advance(0.1);
        w.edge(centreFirstRelease ? 'D2' : 'D1', 1);
        w.advance(0.5);
        assert.equal(w.ctx.moveLatched, following, 'restore the mouse-follow choice from before the centre hold');
        assert(!w.lines.some(l => l.startsWith('@MIDDLE ')), 'neither chord edge operates the HUD');
        assert(!w.frames.some(f => f[2] !== 0), 'centre release never adds a firmware click or drag');
        w.tap('D2');
        assert(w.lines.includes('@MIDDLE 1') && w.lines.includes('@MIDDLE 0'), 'a later standalone left tap still operates the HUD');
      });
    }
  }
  test(`repeat left presses, reverse order, screenshots and speech (${bridge})`, () => {
    const w = createWand({ bridge }); w.calibrate(); w.loadBridge();
    w.edge('D1', 0);
    w.tap('D2'); w.tap('D2');
    assert.equal(w.lines.filter(l => l === '@LEFTCLICK').length, 2, 'each fresh left press clicks once during the same centre hold');
    w.edge('D1', 1); w.advance(0.5); w.lines.length = 0;
    w.edge('D2', 0); w.advance(0.1); w.edge('D1', 0); w.advance(0.3);
    w.edge('D1', 1); w.edge('D2', 1);
    assert(!w.lines.includes('@LEFTCLICK'), 'left held before centre retains the existing independent controls');
    assert(w.lines.includes('@MIDDLE 1') && w.lines.includes('@MIDDLE 0'));
    w.advance(0.5); w.lines.length = 0;
    w.ctx.wandShot = 1;
    w.edge('D1', 0); w.tap('D2'); w.edge('D1', 1);
    assert(!w.lines.includes('@LEFTCLICK'), 'native screenshot selection keeps ownership of centre');
    w.ctx.wandShot = 0; w.lines.length = 0;
    w.tap('D30');
    assert(w.lines.includes('@STT 1') && w.lines.includes('@STT 0'), 'the right speech button is unchanged');
  });
  test(`three-button sleep keeps its route, with immediate click precedence (${bridge})`, () => {
    for (const order of [['D30', 'D1', 'D2'], ['D1', 'D2', 'D30']]) {
      const w = createWand({ bridge }); w.calibrate(); w.loadBridge();
      w.ctx.NRF.getSecurityStatus = () => ({ connected: w.ctx.connected });
      w.device.evaluate(read('device/wand-power-policy.js'));
      for (const pin of order) w.edge(pin, 0);
      assert.equal(w.lines.filter(l => l === '@LEFTCLICK').length, order[0] === 'D30' ? 0 : 1, 'right-first avoids completing the immediate click gesture before the third press');
      assert(w.ctx.wandPowerManual, 'all three still enter manual standby');
    }
  });
}
