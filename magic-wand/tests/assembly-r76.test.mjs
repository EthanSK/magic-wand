import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { validateGuide } from '../hardware/carbon-rod-holders/assembly/assembly-data.mjs';

const root = new URL('../hardware/carbon-rod-holders-r76-matched-finger-rest/exports/', import.meta.url);
const read = path => readFileSync(new URL(path, root));
const json = path => JSON.parse(read(path));

test('R76 shows the seated pack and sockets with the checked fork, and removes the battery by reversing insertion', () => {
  const guide = validateGuide(json('assembly-guide.json'));
  const [install, remove] = guide.modules.battery.steps;
  const seatedKeyParts = guide.modules.key.steps.at(-1).samples.at(-1);
  assert.deepEqual(remove.samples, [...install.samples].reverse());
  assert.ok(install.samples.at(0).battery[7] > install.samples.at(-1).battery[7]);
  for (const sample of guide.modules.finger_rest.steps[0].samples) {
    for (const part of ['battery', 'socket_0', 'socket_2', 'socket_3', 'socket_4']) {
      assert.deepEqual(sample[part], seatedKeyParts[part]);
    }
  }
  assert.equal(guide.revision, 'R76');
  for (const [path, digest] of Object.entries(guide.sources.meshes_sha256)) {
    assert.equal(createHash('sha256').update(read(path)).digest('hex'), digest);
  }
  const proof = json('guard-fit.json');
  const fit = json('fit76.json');
  assert.equal(fit.carrier_sha256, proof.carrier_sha256);
  assert.equal(fit.carrier_sha256, guide.sources.meshes_sha256['Key_Carrier-assembly.stl']);
  assert.equal(fit.passes, true);
  assert.equal(proof.physical_fit_verified, false);
  assert.ok(proof.inner_curve_missing_from_final_mm3 < .005);
  assert.ok(proof.old_installed_pack_to_mirrored_lower_fork_mm > 3.5);
  assert.ok(proof.mirrored_outer_in_seated_socket_mm3 > 1);
});

test('R76 print review covers the same holder and limits the free spans on the finger rest', () => {
  const review = json('print-mechanisms/review.json');
  assert.equal(review.carrier_sha256, json('fit76.json').carrier_sha256);
  for (const slice of Object.values(review.slices)) {
    assert.ok(slice.new_anchored_spans.length > 0);
    for (const { span, reference, bead } of slice.new_anchored_spans) {
      assert.equal(span.two_anchors, true);
      assert.equal(reference.two_anchors, true);
      assert.ok(reference.mm >= span.mm && reference.bend_mm >= span.bend_mm);
      assert.ok(bead.longest_free_mm < 2.7);
    }
  }
});
