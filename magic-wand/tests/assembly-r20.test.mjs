import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { routePose } from '../hardware/carbon-rod-holders-r20-finger-guard/preview/assembly-recipe.mjs';
const base = new URL('../hardware/carbon-rod-holders-r20-finger-guard/', import.meta.url);
const data = JSON.parse(readFileSync(new URL('exports/assembly-guide.json', base)));
const hash = file => createHash('sha256').update(readFileSync(new URL(file, base))).digest('hex');

test('R20 routes bind to the delivered geometry and a clear seated pose', () => {
  assert.equal(data.generator_sha256, hash('assembly20.py'));
  for (const [name, digest] of Object.entries(data.meshes_sha256)) assert.equal(hash(`exports/${name}-assembly.stl`), digest);
  assert.equal(data.paths.hand.first_collision_index, null);
  assert.equal(data.paths.hand.samples.length, 241);
  assert.ok(data.paths.hand.samples.every(row => Object.keys(row.overlaps_mm3).length === 0));
  assert.equal(routePose(data, 'hand', 1).offset_mm, 0);
  assert.ok(Math.abs(data.nominal_stop_gap_mm - .3) < 1e-8);
  assert.equal(data.physical_fit_verified, false);
});

test('ring-end playback stops before measured collision instead of clipping through', () => {
  const path = data.paths.rings, last = routePose(data, 'rings', 1);
  assert.ok(path.first_collision_index > 0);
  assert.equal(last.index, path.first_collision_index - 1);
  assert.deepEqual(last.overlaps_mm3, {});
  assert.ok(path.samples[path.first_collision_index].overlaps_mm3.key_holder > .01);
  assert.equal(last.blocked, true);
  assert.equal(routePose(data, 'rings', 0).offset_mm, 60);
  assert.throws(() => routePose(data, 'missing', 0));
  assert.throws(() => routePose(data, 'hand', NaN));
});
