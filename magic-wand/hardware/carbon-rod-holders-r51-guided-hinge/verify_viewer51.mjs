import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {assemblyComponents, validateGuide} from '../carbon-rod-holders/assembly/assembly-data.mjs';

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
for (const module of Object.values(data.modules)) {
  assert.ok(module.steps.every(s => !/slide.*rod|fit.*onto the rod|adjust the stop screw|pinch the bracket/i.test(s.title)));
  assert.ok(!Object.keys(module.actors).some(k=>k.includes('adjustment_screw')));
}
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
