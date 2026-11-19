import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { stockLength, stockRodUrl, withStockRods } from '../hardware/carbon-rod-holders/assembly/stock-rod.mjs';

const directory = new URL('../hardware/carbon-rod-holders/assembly/', import.meta.url);
const catalog = JSON.parse(readFileSync(new URL('catalog.json', directory)));

test('the stock STL measures 500 mm between ends, 8 mm across, and 7 mm inside', () => {
  const bytes = readFileSync(stockRodUrl);
  const ends = new Set(), radii = new Set();
  for (let face = 0; face < bytes.readUInt32LE(80); face++) {
    for (let vertex = 0; vertex < 3; vertex++) {
      const offset = 96 + face * 50 + vertex * 12;
      ends.add(Math.round(bytes.readFloatLE(offset + 4) * 1000) / 1000);
      radii.add(Math.round(Math.hypot(bytes.readFloatLE(offset), bytes.readFloatLE(offset + 8)) * 1000) / 1000);
    }
  }
  assert.deepEqual(ends, new Set([0, 500]));
  assert.deepEqual(radii, new Set([3.5, 4]));
  assert.equal(stockLength, 500);
});

test('the current offline CAD and every registered assembly use full stock in every rod view', () => {
  for (const version of catalog.versions.filter(entry => entry.guide)) {
    const url = new URL(version.guide, directory);
    const original = JSON.parse(readFileSync(url));
    const { modules } = withStockRods(original);
    for (const [id, module] of Object.entries(modules)) {
      const actor = module.actors.rod;
      if (!actor) continue;
      const context = version.id + '/' + id;
      assert.equal(new URL(actor.file, url).href, stockRodUrl.href, context);
      if (version.id === catalog.current) {
        assert.equal(new URL(original.modules[id].actors.rod.file, url).href, stockRodUrl.href, context);
      }
      for (const step of module.steps) {
        for (const frame of step.samples) {
          if (!frame.rod) continue;
          const m = frame.rod;
          const end = [m[3] + m[1]*stockLength, m[7] + m[5]*stockLength, m[11] + m[9]*stockLength];
          assert.ok(Math.abs(Math.hypot(end[0]-m[3], end[1]-m[7], end[2]-m[11]) - 500) < .001, context);
          if (id === 'whole') {
            assert.ok(module.frameBounds[0][1] <= Math.min(m[7], end[1]), context);
            assert.ok(module.frameBounds[1][1] >= Math.max(m[7], end[1]), context);
          }
        }
      }
    }
  }
});
