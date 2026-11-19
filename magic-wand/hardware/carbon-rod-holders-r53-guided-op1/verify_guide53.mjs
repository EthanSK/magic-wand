import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { assemblyComponents, validateGuide } from '../carbon-rod-holders/assembly/assembly-data.mjs';
import { rodFrame } from '../carbon-rod-holders/assembly/rod-transitions.mjs';

const url = new URL(process.argv[2] || './exports/assembly-guide.json', import.meta.url);
async function bytes(u) {
  if (u.protocol === 'file:') return readFile(u);
  const reply = await fetch(u);
  assert.ok(reply.ok, u.href);
  return Buffer.from(await reply.arrayBuffer());
}
const guide = validateGuide(JSON.parse(await bytes(url)));
assert.equal(guide.revision, 'R53');
const components = assemblyComponents(guide, true);
const parts = guide.print_components.keys;
assert.equal(new Set(parts).size, 7);
assert.equal(new Set(Object.values(guide.print_components).flat()).size, 12);
const keys = components.keys.views.dfr;
const hinge = components.keys.views.pin_hinge;
const board = components.keys.views.op1_clips;
const whole = components.whole.views.whole;
validateGuide({ ...guide, modules: { keys, hinge, board, whole } });
for (const id of ['hinge_cap', 'lid', 'cap', 'carrier', 'post_bar', 'clip_left', 'clip_right']) {
  assert.ok(keys.actors[id], id);
}
for (const id of ['axle_screw', 'locknut', 'bearing_sleeve']) assert.ok(!(id in keys.actors), id);
function pose(frame, id) { return frame[id] ?? frame.pose?.[id]; }
for (const mod of [keys, hinge, board]) {
  for (let i = 1; i < mod.steps.length; i++) {
    const previous = mod.steps[i-1].samples.at(-1);
    const next = mod.steps[i].samples[0];
    for (const id of Object.keys(mod.actors)) {
      const a = pose(previous, id), b = pose(next, id);
      assert.ok(a && b && a.every((x,j) => Math.abs(x-b[j]) < .04), id + ' at ' + mod.steps[i].title);
    }
  }
}
for (let i = 1; i < whole.steps.length; i++) {
  const before = rodFrame(whole.steps[i-1], 1, whole.frameBounds);
  const after = rodFrame(whole.steps[i], 0, whole.frameBounds);
  for (const id of Object.keys(whole.actors)) {
    assert.deepEqual(before.pose[id], after.pose[id], id + ' at ' + whole.steps[i].title);
  }
}
for (const [file, hash] of Object.entries(guide.sources.meshes_sha256)) {
  assert.equal(createHash('sha256').update(await bytes(new URL(file, url))).digest('hex'), hash, file);
}
console.log('Verified seven mechanism pieces, 12 pieces on the assembled rod and all viewer meshes.');
