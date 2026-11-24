import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {assemblyComponents, validateGuide} from '../hardware/carbon-rod-holders/assembly/assembly-data.mjs';

const files = new URL('../hardware/carbon-rod-holders-r65-op1-seat/exports/', import.meta.url);
const load = path => JSON.parse(readFileSync(new URL(path, files)));
const guide = validateGuide(load('assembly-guide.json'));
const wired = ['board', 'plug', 'op1_wire', 'housing', 'sockets'];

test('the fitted R65 kit and all visual references use the intended exports', () => {
  const old = load('../../carbon-rod-holders-r64-under-entry/exports/assembly-guide.json');
  assert.equal(guide.revision, 'R65');
  assert.deepEqual(guide.print_components.keys, [...old.print_components.keys, 'OP1_Seat_Sled'].sort());
  for (const [path, expected] of Object.entries(guide.sources.meshes_sha256)) {
    const bytes = readFileSync(new URL(path, files));
    assert.equal(createHash('sha256').update(bytes).digest('hex'), expected);
  }
  const {dfr} = assemblyComponents(guide, true).keys.views;
  assert.equal(dfr.steps[0].title, 'Place the board on its seat');
  assert.ok(dfr.steps.at(-1).samples.every(s => s.op1_seat));
});

test('load the loose seat first, carry it with the board and reverse both motions for removal', () => {
  for (const id of ['op1_clips', 'pin_hinge', 'dfr']) {
    const {steps} = guide.modules[id];
    const [outside, entry] = steps;
    assert.equal(entry.title, 'Seat the OP1 board');
    const start = outside.samples[0], docked = outside.samples.at(-1);
    for (const sample of outside.samples) assert.deepEqual(sample.op1_seat, start.op1_seat);
    assert.ok(start.board[11] - docked.board[11] >= 5);
    assert.deepEqual(docked, entry.samples[0]);
    for (const sample of entry.samples) {
      assert.ok(!sample.switch && !sample.lid && sample.carrier && sample.rod);
      for (const actor of wired) {
        for (const key of [3,7,11]) {
          const relative = sample[actor][key] - sample.op1_seat[key];
          assert.ok(Math.abs(relative - (docked[actor][key]-docked.op1_seat[key])) < 1e-6);
        }
      }
    }
    for (let i=1; i<steps.length; i++) {
      const before = steps[i-1].samples.at(-1), after = steps[i].samples[0];
      for (const actor of ['op1_seat', ...wired]) {
        assert.deepEqual(before[actor], after[actor], id+' / '+steps[i].title+' / '+actor);
      }
    }
    if (id !== 'dfr') {
      assert.deepEqual(steps.at(-1).samples, [...outside.samples].reverse());
      assert.deepEqual(steps.at(-2).samples, [...entry.samples].reverse());
    }
  }
});
