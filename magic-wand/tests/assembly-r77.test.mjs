import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { validateGuide } from '../hardware/carbon-rod-holders/assembly/assembly-data.mjs';

const root = new URL('../hardware/carbon-rod-holders-r77-even-keys/exports/', import.meta.url);
const read = path => readFileSync(new URL(path, root));
const guide = validateGuide(JSON.parse(read('assembly-guide.json')));
const fit = JSON.parse(read('fit77.json'));

test('the finger-rest view and animation use the same equally spaced, unturned keys', () => {
  const key = guide.modules.key;
  const seated = key.steps.at(-1).samples.at(-1);
  const pitch = (first, second) => Number((seated[second][7] - seated[first][7]).toFixed(3));
  assert.deepEqual([pitch('socket_0','socket_3'), pitch('socket_2','socket_4')], fit.key_pitches_mm);
  assert.deepEqual(fit.cap_edge_gaps_mm, [.55, .55]);
  for (const i of [0,2,3,4]) {
    for (const pose of guide.modules.finger_rest.steps[0].samples) {
      assert.deepEqual(pose['socket_'+i], seated['socket_'+i]);
    }
  }
  const slide = key.steps.find(s => s.title === 'Slide In the Lower-Left Socket');
  const start = slide.samples[0].socket_0;
  assert.equal(start[0], 1);
  assert.equal(start[5], 1);
  assert.equal(start[7], seated.socket_0[7]+1.5);
  assert.deepEqual(key.steps[0].samples.at(-1).socket_0, start);
  assert.deepEqual(slide.samples.at(-1).socket_0, seated.socket_0);
});

test('both hinge views show the same checked paddle and straight leads', () => {
  assert.equal(guide.revision, 'R77');
  assert.equal(createHash('sha256').update(read('../guide77.py')).digest('hex'), guide.sources.generator_sha256);
  for (const part of Object.values(guide.modules)) {
    for (const [actor, file] of [['sensor_lead','Gravity_Wires-assembly.stl'], ['cap','Touch_Paddle-assembly.stl']]) {
      if (part.actors.sensor_lead) assert.equal(part.actors[actor].file, file);
    }
  }
  for (const [path, digest] of Object.entries(guide.sources.meshes_sha256)) {
    assert.equal(createHash('sha256').update(read(path)).digest('hex'), digest);
  }
  assert.equal(guide.sources.meshes_sha256['Key_Carrier-assembly.stl'], fit.carrier_sha256);
  assert.equal(guide.sources.meshes_sha256['Touch_Paddle-assembly.stl'], fit.paddle_sha256);
  assert.equal(fit.passes, true);
  assert.ok(fit.rear_hinge_asymmetry_mm3 < .002);
  assert.ok(fit.wire_clearances_mm.clip_during_insertion > 1);
  assert.equal(fit.physical_fit_verified, false);
});

test('the reviewed print plate uses the two revised parts and leaves the fitting routes open', () => {
  const folder = 'print-mechanisms/';
  const review = JSON.parse(read(folder+'review.json'));
  const frame = JSON.parse(read(folder+'layout.frame.json'));
  assert.equal(review.carrier_sha256, fit.carrier_sha256);
  for (const [part, sha] of [['Key_Carrier', fit.carrier_sha256], ['Touch_Paddle', fit.paddle_sha256]]) {
    assert.equal(frame.parts[part].source_sha256, sha);
  }
  for (const [name, prefix] of [['primary',''], ['reopened','reopened-']]) {
    const clearance = JSON.parse(read(folder+prefix+'fit.json'));
    assert.equal(clearance.archive_sha256, review.slices[name].archive_sha256);
    for (const routes of Object.values(clearance.parts)) {
      for (const result of Object.values(routes)) assert.equal(result.obstructed_poses.length, 0);
    }
  }
});
