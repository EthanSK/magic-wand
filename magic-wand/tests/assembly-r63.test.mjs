import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { assemblyComponents, validateGuide } from '../hardware/carbon-rod-holders/assembly/assembly-data.mjs';

const guideUrl = new URL('../hardware/carbon-rod-holders-r63-open-hinge/exports/assembly-guide.json', import.meta.url);
const guide = validateGuide(JSON.parse(readFileSync(guideUrl)));
const previous = JSON.parse(readFileSync(new URL('../../carbon-rod-holders-r62-compact-guard/exports/assembly-guide.json', guideUrl)));

test('only the inward-facing switch and socket turn, while the wired socket keeps its outside approach', () => {
  const keys = guide.modules.key;
  for (const earlier of previous.modules.key.steps) {
    const changed = keys.steps.find(step => step.title === earlier.title);
    assert.equal(changed.samples.length, earlier.samples.length);
    changed.samples.forEach((pose, i) => {
      const before = earlier.samples[i];
      for (const family of ['socket', 'switch']) {
        for (const id of [2, 3, 4]) assert.deepEqual(pose[family + '_' + id], before[family + '_' + id]);
        const original = before[family + '_0'];
        const rotated = [...original];
        for (const j of [0, 4, 8]) {
          rotated[j] = original[j + 1] || 0;
          rotated[j + 1] = -original[j] || 0;
        }
        assert.ok(rotated.every((value, j) => pose[family + '_0'][j] === value));
      }
    });
  }
  for (const file of ['Key_Carrier', 'Touch_Paddle', 'Rod_Collet', 'Socket_Backer_Left', 'Battery_Pack']) {
    const name = file + '-assembly.stl';
    assert.equal(guide.sources.meshes_sha256[name], createHash('sha256').update(readFileSync(new URL(name, guideUrl))).digest('hex'));
  }
});

test('the backing strip is withdrawn, the complete holder slides onto the rod, then the grip seats', () => {
  const views = assemblyComponents(guide, true);
  const steps = views.whole.views.whole.steps;
  const slide = steps.findIndex(s => s.title === 'Slide the keys onto the rod');
  const clip = steps.findIndex(s => s.title === 'Clip the grip onto the carbon rod');
  const lock = steps.findIndex(s => s.title === 'Seat the rod grip');
  assert.ok(slide > 0 && slide < clip && clip < lock);
  assert.ok(steps[slide].samples.every(s => !s.keys_left_backer && !s.keys_rod_collet));
  assert.ok(steps.slice(0, slide).every(s => s.samples.every(p => !p.keys_rod_collet)));
  assert.deepEqual(steps.at(-1).samples.at(-1).keys_rod_collet, steps[lock].samples.at(-1).keys_rod_collet);
  assert.ok(views.keys.views.key.steps.find(s => s.title === 'Press In the Switches').samples.every(p => p.left_backer));
});
