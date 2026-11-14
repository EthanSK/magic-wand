import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {validateGuide,assemblyComponents} from '../hardware/carbon-rod-holders/assembly/assembly-data.mjs';
const base=new URL('../hardware/carbon-rod-holders-r39-retention/exports/',import.meta.url);
const guide=JSON.parse(readFileSync(new URL('assembly-guide.json',base)));

test('R39 serves all components and binds its guide to the exact current meshes',()=>{
 validateGuide(guide);
 const c=assemblyComponents(guide,true);
 assert.deepEqual(Object.keys(c),['keys','xiao','battery','cable','whole']);
 assert.ok(c.battery.views.battery_latch);
 assert.ok(c.keys.views.finger_rest);
 for(const i of [0,2,3,4]) {
  assert.ok(c.whole.views.whole.actors[`keys_keycap_${i}`]);
  for(const step of c.whole.views.whole.steps) for(const sample of step.samples)
   assert.deepEqual(sample[`keys_keycap_${i}`],sample[`keys_switch_${i}`]);
 }
 for(const [path,digest] of Object.entries(guide.sources.meshes_sha256))
  assert.equal(createHash('sha256').update(readFileSync(new URL(path,base))).digest('hex'),digest,path);
});
test('battery removal visibly unlocks before lifting and cable guide moves every wire in and out',()=>{
 const steps=guide.modules.battery.steps;
 const unlock=steps.findIndex(x=>x.title==='Release the Battery Door');
 const lift=steps.findIndex(x=>x.title==='Lift the Door Out');
 assert.ok(unlock>=0&&lift===unlock+1);
 assert.equal(steps[unlock].samples.at(-1).morphs.door,1);
 assert.equal(steps[lift].samples.at(-1).door[11],15);
 const cable=guide.modules.cable.steps;
 for(let i=1;i<=12;i++){
  const into=cable.find(s=>s.title===`Feed Wire ${i}`),out=cable.find(s=>s.title===`Remove Wire ${i}`);
  assert.ok(into&&out);
  assert.notDeepEqual(into.samples[0][`wire_${i-1}`],into.samples.at(-1)[`wire_${i-1}`]);
  assert.notDeepEqual(out.samples[0][`wire_${i-1}`],out.samples.at(-1)[`wire_${i-1}`]);
 }
 assert.ok(guide.modules.whole.actors.rod.frame);
});
