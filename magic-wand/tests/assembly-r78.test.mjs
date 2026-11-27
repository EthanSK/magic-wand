import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { validateGuide } from '../hardware/carbon-rod-holders/assembly/assembly-data.mjs';

const base = new URL('../hardware/carbon-rod-holders-r78-low-battery/exports/', import.meta.url);
const previous = new URL('../../carbon-rod-holders-r77-even-keys/exports/', base);
const read = (url, path) => JSON.parse(readFileSync(new URL(path, url)));
const current = validateGuide(read(base, 'assembly-guide.json'));
const old = validateGuide(read(previous, 'assembly-guide.json'));
const fit = read(base, 'fit78.json');

test('every battery insertion, removal and seated pose follows the lowered rails', () => {
  assert.equal(current.revision, 'R78');
  const modules = Object.keys(old.modules).filter(id => old.modules[id].actors.battery);
  assert.deepEqual(modules.sort(), ['battery', 'finger_rest', 'key']);
  for (const id of modules) {
    const updated = current.modules[id];
    old.modules[id].steps.forEach((step, i) => {
      assert.equal(updated.steps[i].samples.length, step.samples.length);
      step.samples.forEach((sample, j) => {
        const pose = updated.steps[i].samples[j].battery;
        if (!sample.battery) return assert.equal(pose, sample.battery);
        const expected = [...sample.battery];
        expected[7] += 2;
        expected[11] += .8;
        assert.deepEqual(pose, expected);
      });
    });
  }
  assert.equal(fit.battery_to_deck_mm, 2.3);
  assert.equal(fit.pack_end_projection_mm, 4.5);
  assert.ok(fit.minimum_fitted_socket_and_tape_gap_mm >= .2);
  assert.ok(fit.spring_contact_mm3 > 0);
  assert.ok(fit.rigid_rail_rear_path_overlap_mm3 < .001);
  assert.equal(fit.passes, true);
  assert.equal(fit.physical_fit_verified, false);
});

test('the guide and both slices use the checked R78 carrier and a clear battery path', () => {
  for (const [path, hash] of Object.entries(current.sources.meshes_sha256)) {
    assert.equal(createHash('sha256').update(readFileSync(new URL(path, base))).digest('hex'), hash);
  }
  assert.equal(current.sources.meshes_sha256['Key_Carrier-assembly.stl'], fit.carrier_sha256);
  const review = read(base, 'print-mechanisms/review.json');
  const frame = read(base, 'print-mechanisms/layout.frame.json').parts;
  assert.equal(review.carrier_sha256, fit.carrier_sha256);
  assert.equal(frame.Key_Carrier.source_sha256, fit.carrier_sha256);
  assert.equal(Object.keys(frame).length, 9);
  for (const [name, prefix] of [['primary', ''], ['reopened', 'reopened-']]) {
    const paths = read(base, 'print-mechanisms/'+prefix+'fit.json');
    assert.equal(paths.archive_sha256, review.slices[name].archive_sha256);
    assert.deepEqual(paths.parts.Key_Carrier.battery_rear_insertion_and_removal.obstructed_poses, []);
    for (const part of Object.values(paths.parts)) {
      for (const path of Object.values(part)) assert.deepEqual(path.obstructed_poses, []);
    }
  }
});
