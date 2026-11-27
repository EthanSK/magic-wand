// Verify the moved battery throughout assembly and preserve the unmodified bought parts and kit motions. — GPT-6.2 Astra
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {assemblyComponents, validateGuide} from '../hardware/carbon-rod-holders/assembly/assembly-data.mjs';

const current = new URL('../hardware/carbon-rod-holders-r72-inboard-battery/exports/', import.meta.url);
const previous = new URL('../hardware/carbon-rod-holders-r71-contained-battery/exports/', import.meta.url);
const guideAt = dir => validateGuide(JSON.parse(readFileSync(new URL('assembly-guide.json',dir))));

test('every R72 battery pose moves inward by the same distance and every other motion is preserved', () => {
  const guide = guideAt(current), baseline = guideAt(previous);
  assert.equal(guide.revision,'R72');
  assert.ok(assemblyComponents(guide,true).keys);
  let moved = 0;
  for (const [id, module] of Object.entries(guide.modules)) {
    const old = baseline.modules[id];
    assert.equal(module.steps.length,old.steps.length);
    for (const [index, step] of module.steps.entries()) {
      const samples = old.steps[index].samples.map(sample => {
        if (!sample.battery) return sample;
        const battery = [...sample.battery];
        battery[3] += 8;
        moved++;
        return {...sample, battery};
      });
      assert.deepEqual(step.samples,samples);
    }
  }
  assert.equal(moved,guide.r72_changes.moved_battery_poses);
  assert.ok(moved > 0);
  assert.deepEqual(guide.print_components.keys,baseline.print_components.keys);
  for (const [path, digest] of Object.entries(guide.sources.meshes_sha256)) {
    assert.equal(createHash('sha256').update(readFileSync(new URL(path,current))).digest('hex'),digest,path);
  }
});
