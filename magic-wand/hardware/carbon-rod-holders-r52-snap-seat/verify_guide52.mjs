import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { assemblyComponents, validateGuide } from '../carbon-rod-holders/assembly/assembly-data.mjs';
import { rodFrame } from '../carbon-rod-holders/assembly/rod-transitions.mjs';

const base = new URL(process.argv[2] || 'http://127.0.0.1:8849/magic-wand/hardware/carbon-rod-holders/assembly/');
async function get(url) {
  const response = await fetch(url);
  assert.ok(response.ok, String(url));
  return response;
}
const catalog = await (await get(new URL('catalog.json', base))).json();
const version = catalog.versions.find(entry => entry.id === 'r52');
const url = new URL(version.guide, base);
const guide = validateGuide(await (await get(url)).json());
const components = assemblyComponents(guide, version.groupKeys);
const clipView = components.keys.views.op1_clips;
const keys = components.keys.views.dfr;
const whole = components.whole.views.whole;
validateGuide({ ...guide, modules: { keys, whole, clipView } });
assert.equal(new Set(Object.values(guide.print_components).flat()).size, 9);
assert.equal(clipView.steps.length, 8);
assert.ok(!('fasteners' in keys.actors));
for (const module of [clipView, keys, whole]) {
  for (const note of module.annotations ?? []) assert.ok(module.actors[note.actor], note.actor);
}
for (const arm of ['front_op1_arm', 'rear_op1_arm']) {
  assert.ok(clipView.actors[arm].morphFile);
  const lift = clipView.steps.find(step => step.title === 'Lift the two retaining arms');
  const engage = clipView.steps.find(step => step.title === 'Seat both pegs');
  assert.equal(lift.samples[0].morphs[arm], 0);
  assert.equal(lift.samples.at(-1).morphs[arm], 1);
  assert.equal(engage.samples[0].morphs[arm], 1);
  assert.equal(engage.samples.at(-1).morphs[arm], 0);
}
const titles = keys.steps.map(step => step.title);
assert.ok(titles.indexOf('Seat both pegs') < titles.indexOf('Fit the locknut'));
assert.ok(titles.indexOf('Fit the locknut') < titles.indexOf('Fit the Keycaps'));
for (const module of [clipView, keys, components.keys.views.pin_hinge]) {
  for (let i = 1; i < module.steps.length; i++) {
    const previous = module.steps[i - 1].samples.at(-1);
    const next = module.steps[i].samples[0];
    for (const key of Object.keys(module.actors)) {
      assert.ok(previous[key].every((value, j) => Math.abs(value - next[key][j]) < .04), key + ' / ' + module.steps[i].title);
      assert.equal(previous.morphs?.[key] ?? 0, next.morphs?.[key] ?? 0);
    }
  }
}
function visibleFrame(step, position) {
  const { pose, opacity, bounds } = rodFrame(step, position, whole.frameBounds);
  const visible = Object.fromEntries(Object.keys(whole.actors).filter(id => pose[id])
    .map(id => [id, [pose[id], opacity[id] ?? 1, pose.morphs?.[id] ?? 0]]));
  return { visible, bounds };
}
for (let i = 1; i < whole.steps.length; i++) {
  assert.deepEqual(visibleFrame(whole.steps[i - 1], 1), visibleFrame(whole.steps[i], 0), whole.steps[i].title);
}
for (const [name, sha] of Object.entries(guide.sources.meshes_sha256)) {
  const bytes = await (await get(new URL(name, url))).arrayBuffer();
  assert.equal(createHash('sha256').update(new Uint8Array(bytes)).digest('hex'), sha, name);
}
console.log('Verified 9 printed parts, 8 OP1 fitting and removal steps, both arm motions, all viewer mesh hashes and ' + (whole.steps.length - 1) + ' whole-rod joins.');
