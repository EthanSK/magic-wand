import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {assemblyComponents, validateGuide} from '../hardware/carbon-rod-holders/assembly/assembly-data.mjs';

const directory = new URL('../hardware/carbon-rod-holders-r64-under-entry/exports/', import.meta.url);
const load = name => JSON.parse(readFileSync(new URL(name, directory)));
const guide = validateGuide(load('assembly-guide.json'));
const entry = load('under-entry.json');
const fit = load('click-fit.json');

test('all supplied fittings are named and every viewer mesh matches its source', () => {
  const names = ['Key_Carrier','Touch_Paddle','Rod_Collet','Hinge_Pin','Hinge_Pin_Snug',
    'Pin_Clip','Pin_Clip_Spare','OP1_Lid_Stop','DFR_Post_Bar','DFR_Clip_Left','DFR_Clip_Right',
    'Socket_Backer_Left','Socket_Backer_Right'];
  assert.deepEqual([...guide.print_components.keys].sort(), names.sort());
  for (const module of Object.values(guide.modules)) {
    for (const spec of Object.values(module.actors)) {
      for (const path of [spec.file,spec.morphFile].filter(Boolean)) {
        const bytes = readFileSync(new URL(path,directory));
        assert.equal(createHash('sha256').update(bytes).digest('hex'), guide.sources.meshes_sha256[path]);
      }
    }
  }
  assert.equal(guide.revision,'R64');
  const keys = assemblyComponents(guide,true).keys.views;
  const assembled = keys.dfr.steps;
  for (const required of ['Seat the OP1 board','Press in the pin clip','Fit the Keycaps','Seat the rod grip','Press the lower half of the pad']) {
    assert.ok(assembled.some(step => step.title===required), required);
  }
  assert.ok(keys.key.steps.some(step=>step.title==='Slide In the Lower-Left Socket'));
  assert.deepEqual(Object.keys(assembled[0].samples[0]).filter(k=>k!=='morphs').sort(),
    ['board','carrier','housing','op1_wire','plug','rod','sockets']);
});

test('under-entry guides follow the checked board and white connector path both ways', () => {
  for (const key of ['dfr','op1_clips','pin_hinge']) {
    const module = guide.modules[key];
    assert.ok(module.stagedActors && module.annotationsByStep);
    const steps = module.steps;
    const insert = steps.find(s => s.title==='Seat the OP1 board');
    assert.ok(insert.samples.every(s => !s.switch && !s.lid && !s.pin_clip && s.rod && s.carrier));
    const final = insert.samples.at(-1);
    const fitSwitch = steps.find(s=>s.title==='Fit the mouse switch');
    for (const id of ['board','housing','sockets','plug','op1_wire']) {
      assert.deepEqual(fitSwitch.samples[0][id], final[id]);
      assert.deepEqual(fitSwitch.samples.at(-1)[id], final[id]);
    }
    for (const id of ['board','housing','sockets','plug','op1_wire']) {
      for (const offset of entry.entry_offsets_mm) {
        assert.ok(insert.samples.some(s => [3,7,11].every((c,i) => Math.abs(s[id][c]-final[id][c]-offset[i])<1e-6)));
      }
    }
    const removal = steps.find(s => s.title==='Lift the OP1 board');
    if (removal) assert.deepEqual(removal.samples.map(s=>s.board),insert.samples.map(s=>s.board).reverse());
    assert.ok(steps.indexOf(insert)<steps.findIndex(s=>s.title==='Fit the mouse switch'));
  }
});

test('retaining clip enters from the rear and the contact bar pivots about the fitted hinge', () => {
  const {steps} = guide.modules.pin_hinge;
  const clip = steps.find(s => s.title==='Press in the pin clip');
  const first = clip.samples[0].pin_clip, last = clip.samples.at(-1).pin_clip;
  assert.ok(first[7]-last[7]>10);
  assert.equal(first[11],last[11]);
  const [y,z] = fit.centreline_yz_mm;
  const press = steps.find(s=>s.title==='Press the lower half of the pad').samples;
  for (const {cap} of press) {
    assert.ok(Math.abs(cap[5]*y+cap[6]*z+cap[7]-y)<1e-7);
    assert.ok(Math.abs(cap[9]*y+cap[10]*z+cap[11]-z)<1e-7);
  }
  assert.ok(Math.max(...press.map(s=>Math.asin(s.cap[9])*180/Math.PI))<fit.case_stop_deg);
});

test('installed actors stay in place between neighboring assembly steps', () => {
  for (const name of ['dfr','op1_clips','pin_hinge']) {
    const {steps,actors} = guide.modules[name];
    for (let i=1; i<steps.length; i++) {
      const end = steps[i-1].samples.at(-1), start = steps[i].samples[0];
      for (const key of Object.keys(actors)) {
        if (!(key in start && key in end)) continue;
        assert.ok(start[key].every((v,j)=>Math.abs(v-end[key][j])<1e-7),
          name+' / '+steps[i].title+' / '+key);
      }
    }
  }
});
