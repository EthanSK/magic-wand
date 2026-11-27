// The guard and both battery exits are checked against the same exported
// carrier the viewer shows. The green PCB, paddle and mechanical click are R73's.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {validateGuide} from '../hardware/carbon-rod-holders/assembly/assembly-data.mjs';

const here = new URL('../hardware/carbon-rod-holders-r74-smooth-through/exports/', import.meta.url);
const prior = new URL('../hardware/carbon-rod-holders-r73-inset-guard/exports/', import.meta.url);
const json = url => JSON.parse(readFileSync(url));
const guide = () => validateGuide(json(new URL('assembly-guide.json', here)));
const hash = url => createHash('sha256').update(readFileSync(url)).digest('hex');

test('R74 clears the pouch through both ends and keeps the real key fittings accessible', () => {
  const fit = json(new URL('fit74.json', here));
  assert.equal(hash(new URL('Key_Carrier-assembly.stl', here)), fit.carrier_sha256);
  assert.equal(fit.passes, true);
  assert.ok(fit.old_lane_overlap_mm3 > 50);
  assert.ok(fit.rigid_lane_overlap_mm3 < .01);
  assert.ok(fit.spring_contact_mm3 > .1);
  assert.deepEqual(fit.key_obstructions, []);
  assert.equal(fit.key_poses, 336);
  assert.equal(fit.physical_fit_verified, false);
});

test('R74 shows the complete forward battery exit and keeps the R73 touchpad assembly', () => {
  const current = guide();
  const old = validateGuide(json(new URL('assembly-guide.json', prior)));
  const [install, remove] = current.modules.battery.steps;
  const end = install.samples.at(-1).battery;
  assert.deepEqual(end, remove.samples[0].battery);
  assert.deepEqual(install.samples, old.modules.battery.steps[0].samples);
  assert.ok(remove.samples.at(-1).battery[7] < end[7] - 46);
  for (let i = 1; i < remove.samples.length; ++i) {
    const before = remove.samples[i - 1].battery;
    const after = remove.samples[i].battery;
    assert.ok(after[7] <= before[7]);
    assert.deepEqual(after.filter((_, k) => k !== 7), before.filter((_, k) => k !== 7));
  }
  assert.deepEqual(current.modules.dfr.steps, old.modules.dfr.steps);
  assert.equal(new URL(current.modules.dfr.actors.cap.file, here).href,
               new URL(old.modules.dfr.actors.cap.file, prior).href);
  for (const [name, digest] of Object.entries(current.sources.meshes_sha256)) {
    assert.equal(hash(new URL(name, here)), digest);
  }
});

test('both R74 slices keep the socket pocket open and ground the guard at both ends', () => {
  const out = new URL('print-mechanisms/', here);
  const review = json(new URL('review.json', out));
  for (const [label, prefix] of [['primary', ''], ['reopened', 'reopened-']]) {
    const slice = review.slices[label];
    const guard = json(new URL(`${prefix}guard-review.json`, out));
    assert.equal(guard.archive_sha256, slice.archive_sha256);
    assert.equal(slice.part_count, 9);
    assert.equal(slice.route_groups, 80);
    assert.equal(guard.passes, true);
    assert.deepEqual(guard.new_runs_for_inspection, []);
    assert.ok(Object.values(guard.parts).every(part => !part.floating_starts.length));
    assert.ok(guard.reviewed_bridges.some(bridge => bridge.passes && bridge.run.two_anchors));
  }
});
