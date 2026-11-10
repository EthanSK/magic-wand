// Exercise complete component recipes and the actual shared-menu inputs.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { validateGuide, sampledPose, identity } from '../hardware/carbon-rod-holders/assembly/assembly-data.mjs';
import { legacyR20 } from '../hardware/carbon-rod-holders/assembly/legacy-r20.mjs';

test('printed-parts catalog includes every assembly and preserves physical-fit limits', async () => {
  const oldFetch = globalThis.fetch;
  globalThis.fetch = async url => new Response(readFileSync(url));
  try {
    const guide = validateGuide(await legacyR20());
    assert.deepEqual(Object.keys(guide.modules), ['xiao', 'battery', 'keys', 'finger_guard', 'cable']);
    assert.equal(guide.physical_fit_verified, false);
    assert.match(guide.modules.xiao.note, /reused the R19 keeper/);
    assert.match(guide.modules.xiao.note, /still needs checking/);
    assert.match(guide.modules.cable.note, /unmeasured/);
    for (const module of Object.values(guide.modules)) {
      for (const actor of Object.values(module.actors)) if (actor.file) assert.ok(readFileSync(new URL(actor.file, actor.baseUrl)).length > 84);
      for (let i = 0; i < module.steps.length - 1; i++) {
        const end = sampledPose(module, i, 1), start = sampledPose(module, i + 1, 0);
        for (const id of Object.keys(module.actors)) for (let j = 0; j < 12; j++) assert.ok(Math.abs(end[id][j] - start[id][j]) < 1e-8, `${module.label}/${id}`);
      }
    }
    const guard = guide.modules.finger_guard;
    assert.equal(sampledPose(guard, 0, 0).guard[7], -60);
    assert.deepEqual(sampledPose(guard, 0, 1).guard, identity());
    assert.throws(() => sampledPose(guard, -1, 0));
    assert.throws(() => sampledPose(guard, 0, NaN));
    assert.throws(() => validateGuide({ ...guide, units: 'inches' }));
  } finally { globalThis.fetch = oldFetch; }
});

test('tower illustration is tied to actual R20 extrusion and handles leading decimals', () => {
  const base = new URL('../hardware/carbon-rod-holders/assembly/', import.meta.url);
  const data = JSON.parse(readFileSync(new URL('tower-r20.json', base)));
  const hash = file => createHash('sha256').update(readFileSync(new URL(file, base))).digest('hex');
  assert.equal(data.source_sha256, hash('../../carbon-rod-holders-r20-finger-guard/exports/R20-A1-mini-PETG.gcode.3mf'));
  assert.equal(data.generator_sha256, hash('tower_paths.py'));
  assert.ok(data.segments.length > 20000);
  assert.equal(data.bounds_mm[0][2], .2);
  assert.equal(data.bounds_mm[1][2], 35.2);
  assert.ok(data.segments.every(segment => segment.length === 6 && segment.every(Number.isFinite)));
});

test('R23 assembly stays tied to the exported carrier and fit variants', () => {
  const directory = new URL('../hardware/carbon-rod-holders/assembly/', import.meta.url);
  const read = url => JSON.parse(readFileSync(url));
  const sha = url => createHash('sha256').update(readFileSync(url)).digest('hex');
  const catalog = read(new URL('catalog.json', directory));
  assert.ok(catalog.versions.some(version => version.id === catalog.current));
  const version = catalog.versions.find(version => version.id === 'r23');
  const guideURL = new URL(version.guide, directory);
  const guide = validateGuide(read(guideURL));
  const manifestURL = new URL('manifest.json', guideURL);
  const manifest = read(manifestURL);
  assert.equal(guide.revision, manifest.revision);
  assert.equal(guide.sources.manifest_sha256, sha(manifestURL));
  assert.equal(guide.sources.centre_motion_sha256, sha(new URL('centre-motion.json', guideURL)));
  assert.equal(guide.sources.generator_sha256, sha(new URL('../assembly23.py', guideURL)));
  assert.equal(guide.physical_fit_verified, false);
  const meshes = guide.sources.meshes_sha256;
  for (const module of Object.values(guide.modules)) {
    for (const { file } of Object.values(module.actors)) {
      assert.equal(meshes[file], sha(new URL(file, guideURL)), file);
    }
  }
  for (const [name, part] of Object.entries(manifest.parts)) {
    assert.equal(meshes[`${name}-assembly.stl`], part.assembly_stl_sha256, name);
  }
  assert.notEqual(guide.modules.centre_shallow.actors.paddle.file, guide.modules.centre_deep.actors.paddle.file);
  for (const id of ['battery', 'battery_easy']) {
    const { actors, steps } = guide.modules[id];
    assert.equal(actors.spacer, undefined);
    const door = steps.find(step => step.title === 'Drop In the Door').samples.map(sample => sample.door);
    assert.ok(door.every(pose => pose[3] === 0 && pose[7] === 0));
    assert.ok(door[0][11] > 0 && door.at(-1)[11] === 0);
  }
  assert.notEqual(guide.modules.battery.actors.door.file, guide.modules.battery_easy.actors.door.file);
  if (version.helper) {
    const tower = read(new URL(version.helper, directory));
    assert.equal(tower.source_sha256, sha(new URL('R23-A1-mini-PETG.gcode.3mf', guideURL)));
    assert.ok(tower.segments.length > 0);
  }
});
