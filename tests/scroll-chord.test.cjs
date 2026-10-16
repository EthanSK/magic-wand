// Bottom + Middle two-axis scrolling with the current bridge applied.
// Ported from the wand's original chord regression; the bridge adds a one-second sensor grace,
// so "sensor off" checks wait for it.
const test = require("node:test");
const assert = require("node:assert/strict");
const { createWand } = require("./harness.cjs");

for (const bridge of ["readable", "fragments"]) {
  test(`scroll chord in both press orders, diagonals and clean release (${bridge} bridge)`, () => {
    const w = createWand({ bridge });
    const { ctx, frames, lines } = w;
    w.calibrate();
    w.loadBridge();
    const grace = () => w.advance(1.01);

    function chord(first, priorFollow = false) {
      ctx.setMouseFollow(priorFollow);
      grace();
      lines.length = 0; frames.length = 0;
      const second = first === "D1" ? "D2" : "D1";
      w.edge(first, 0); w.advance(0.03); w.edge(second, 0);
      assert(ctx.scrollHeld);
      assert.deepEqual(w.colors(), [0, 1, 1], "scrolling is cyan");
      assert(!ctx.moveLatched);
      for (let i = 0; i < 50; i++) w.motion({ x: 1474, y: 268, z: 1742 });
      assert(ctx.scrollX !== 0 && ctx.scrollY !== 0, "both scroll axes track rotation");
      assert(lines.some((l) => l.startsWith("@SCROLL B,")));
      assert(lines.some((l) => l.startsWith("@SCROLL U,")));
      assert(!lines.some((l) => l.startsWith("@MIDDLE 1")), "a quick chord does not open the HUD");
      w.edge(first, 1);
      assert(!ctx.scrollHeld && ctx.scrollSuppress);
      assert(lines.some((l) => l.startsWith("@SCROLL E,")));
      // Physical Bottom edge reports cancel circle recognition; they are not HUD actions.
      const actionLines = () => lines.filter((l) => l.startsWith("@") && !["@BOTTOM ","@IMU ","@FOLLOW "].some(prefix=>l.startsWith(prefix)));
      const count = actionLines().length;
      w.advance(0.4); w.edge(second, 1); w.advance(0.3);
      assert(!ctx.scrollSuppress);
      assert.equal(ctx.moveLatched, priorFollow, "prior pointer follow is restored");
      assert.equal(actionLines().length, count, "the held remainder does not activate the HUD");
      assert(frames.every((f) => f[2] === 0), "the chord never clicks");
      if (!priorFollow) { grace(); assert(!ctx.gyroAwake && w.device.sampleRate===1.6); } else assert(w.device.awake);
    }
    chord("D1"); chord("D2"); chord("D1", true); chord("D2", true);

    // A circle scrolls in all four directions.
    ctx.setMouseFollow(false); grace(); lines.length = 0;
    w.edge("D1", 0); w.edge("D2", 0);
    for (let i = 0; i < 240; i++) {
      const t = (i / 240) * Math.PI * 4;
      w.motion({ x: ctx.bias.x + Math.sin(t) * 2680, y: ctx.bias.y, z: ctx.bias.z + Math.cos(t) * 2680 });
    }
    const curve = lines.filter((l) => l.startsWith("@SCROLL U,")).map((l) => l.slice(10).split(",").map(Number));
    const deltas = curve.slice(1).map((p, i) => [p[0] - curve[i][0], p[1] - curve[i][1]]);
    assert([0, 1].every((axis) => deltas.some((d) => d[axis] > 0) && deltas.some((d) => d[axis] < 0)), "circular motion scrolls in all four directions");
    w.edge("D1", 1); w.edge("D2", 1);

    // A HUD context arriving mid-chord cannot stop the scroll sensor.
    ctx.setMouseFollow(false); grace();
    w.edge("D2", 0); w.advance(0.1);
    assert(ctx.hudHeld);
    w.edge("D1", 0);
    assert(ctx.scrollHeld);
    ctx.setHUDOpen(true); assert(w.device.awake, "late HUD context cannot stop the scroll sensor");
    ctx.setHUDOpen(false); assert(w.device.awake);
    w.edge("D1", 1); w.edge("D2", 1); grace();
    assert(!ctx.gyroAwake && w.device.sampleRate===1.6);

    // Re-pressing while Middle stays held resumes scrolling; disconnect stops everything.
    w.edge("D1", 0); w.advance(0.02); w.edge("D2", 0); w.edge("D1", 1);
    assert(!ctx.scrollHeld);
    w.edge("D1", 0);
    assert(ctx.scrollHeld, "re-press while middle remains held resumes scroll");
    w.device.disconnect();
    assert(!w.device.awake && !ctx.scrollHeld);
  });
}
