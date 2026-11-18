import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {assemblyComponents, validateGuide} from '../carbon-rod-holders/assembly/assembly-data.mjs';

import { rodFrame } from '../carbon-rod-holders/assembly/rod-transitions.mjs';

const base = new URL(process.argv[2] || 'http://127.0.0.1:8849/magic-wand/hardware/carbon-rod-holders/assembly/');
const get = async url => {
  const response = await fetch(url);
  assert.ok(response.ok, String(url));
  return response;
};
const catalog = await (await get(new URL('catalog.json',base))).json();
const version = catalog.versions.find(item => item.id === 'r51');
const url = new URL(version.guide, base);
const data = validateGuide(await (await get(url)).json());
const components = assemblyComponents(data, version.groupKeys);
assert.deepEqual(Object.values(data.print_components).flat().sort(),['Battery_End_Door','DFRobot_Hole_Bracket','Key_Carrier']);
assert.ok(components.keys.views.pin_hinge);
assert.ok(components.xiao.views.xiao_latch && components.battery.views.battery_latch && components.cable);
for (const [id, module] of Object.entries(data.modules)) {
  if (id === 'whole') continue;
  assert.ok(module.steps.every(s => !/slide.*rod|fit.*onto the rod|adjust the stop screw|pinch the bracket/i.test(s.title)));
  assert.ok(!Object.keys(module.actors).some(k=>k.includes('adjustment_screw')));
}
const keys = components.keys.views[components.keys.defaultView];
const whole = components.whole.views.whole;
validateGuide({ ...data, modules: { keys, whole } });
const finalKeys = keys.steps.at(-1).samples.at(-1);
for (const index of [0, 2, 3, 4]) {
  for (const type of ['switch', 'socket', 'keycap']) {
    const id = type + '_' + index;
    assert.deepEqual(finalKeys[id], components.keys.views.key.steps.at(-1).samples.at(-1)[id]);
  }
}
assert.equal(keys.steps.at(-1).title, 'Press the lower half of the pad');
assert.ok(keys.steps.findIndex(step => step.title === 'Fit the locknut')
  < keys.steps.findIndex(step => step.title === 'Fit the Keycaps'));
assert.deepEqual(Object.keys(whole.steps[0].samples[0]), ['rod']);
// Scrubbing in either direction must give the same camera, parts and shapes
// on both sides of each cut, including newly introduced wires and keys.
const at = (step, t) => rodFrame(step, t, whole.frameBounds);
function effectiveFrame(step, t) {
  const { pose, opacity, bounds } = at(step, t);
  const result = {};
  for (const id of Object.keys(whole.actors)) {
    if (pose[id]) result[id] = [pose[id], opacity[id] ?? 1, pose.morphs?.[id] ?? 0];
  }
  return { result, bounds };
}
for (let i = 1; i < whole.steps.length; ++i) {
  assert.deepEqual(effectiveFrame(whole.steps[i-1], 1), effectiveFrame(whole.steps[i], 0),
    'Discontinuous boundary before ' + whole.steps[i].title);
}
const intro = whole.steps[0];
const looseKey = 'keys_keycap_0';
const middle = at(intro, 0.5);
assert.equal(middle.opacity[looseKey], 0.5);
assert.ok(middle.pose[looseKey][11] > at(intro, 1).pose[looseKey][11]);
assert.deepEqual(middle.bounds, at(intro, 0).bounds.map((corner,i) =>
  corner.map((n,j) => (n + at(intro, 1).bounds[i][j]) / 2)));
assert.ok(at(intro, 0.95).opacity[looseKey] > middle.opacity[looseKey]);
assert.deepEqual(at(intro, 0.5), middle);
const finalRod = whole.steps.at(-1).samples.at(-1);
for (const id of Object.keys(whole.actors)) assert.ok(finalRod[id], id);
let lastMount = -1;
for (const mount of whole.rodMounts) {
  const index = whole.steps.findIndex(step => step.title === mount.title);
  assert.ok(index > lastMount);
  lastMount = index;
  const slide = whole.steps[index];
  const rootId = mount.id + '_' + mount.root;
  assert.ok(slide.samples[0][rootId][7] > 175, 'holder starts beyond the free end');
  assert.deepEqual(slide.samples.at(-1)[rootId], mount.placement);
  assert.deepEqual(finalRod[rootId], mount.placement);
  assert.ok(whole.steps.slice(index+1).every(step => step.samples.every(pose =>
    pose[rootId].every((value,i) => value === mount.placement[i]))));
}
const emptyClip = whole.steps.find(step => step.title === 'Slide the empty cable clip onto the rod');
assert.ok(emptyClip.samples.every(frame => !Object.hasOwn(frame,'cable_wire_0')));
assert.equal(whole.steps.filter(step => /^Feed Wire /.test(step.title)).length,12);
assert.deepEqual(finalRod.keys_keycap_0,finalKeys.keycap_0);
assert.ok(!whole.steps.some(step => /withdraw|lift out|slide the lid out|remove wire/i.test(step.title)));
for (const [name,sha] of Object.entries(data.sources.meshes_sha256)) {
  const b = await (await get(new URL(name,url))).arrayBuffer();
  assert.equal(createHash('sha256').update(new Uint8Array(b)).digest('hex'),sha,name);
}
for (const m of ['dfr','pin_hinge']) {
  const steps = data.modules[m].steps;
  for (let i=1;i<steps.length;i++) {
    const a=steps[i-1].samples.at(-1), b=steps[i].samples[0];
    for(const k of Object.keys(data.modules[m].actors)) {
      const jump = Math.max(...a[k].map((val,n)=>Math.abs(b[k][n]-val)));
      assert.ok(jump<.04, m+' / '+steps[i].title+' / '+k+' / '+jump);
    }
  }
}
console.log('R51 verified over HTTP, '+Object.keys(data.sources.meshes_sha256).length+' distinct meshes, continuous hinge assembly and removal, and '+Object.keys(components).length+' selectable components.');
