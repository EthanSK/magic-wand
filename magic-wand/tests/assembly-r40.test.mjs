// Check the delivered R40 meshes and motion, independently of the CAD helpers.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { validateGuide, assemblyComponents } from '../hardware/carbon-rod-holders/assembly/assembly-data.mjs';

const exportsUrl = new URL('../hardware/carbon-rod-holders-r40-crosswise-op1/exports/', import.meta.url);
const read = name => JSON.parse(readFileSync(new URL(name, exportsUrl)));
const guide = read('assembly-guide.json');
const sha = bytes => createHash('sha256').update(bytes).digest('hex');

function bounds(file, pose) {
  const bytes = readFileSync(new URL(file, exportsUrl));
  const triangles = bytes.readUInt32LE(80);
  assert.ok(triangles > 0);
  assert.equal(bytes.length, 84 + 50 * triangles);
  const low = [Infinity, Infinity, Infinity], high = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < triangles; i++) for (let vertex = 0; vertex < 3; vertex++) {
    const start = 84 + 50 * i + 12 + vertex * 12;
    const p = [0, 1, 2].map(axis => bytes.readFloatLE(start + axis * 4));
    for (let axis = 0; axis < 3; axis++) {
      const j = axis * 4;
      const q = pose[j] * p[0] + pose[j + 1] * p[1] + pose[j + 2] * p[2] + pose[j + 3];
      assert.ok(Number.isFinite(q));
      low[axis] = Math.min(low[axis], q); high[axis] = Math.max(high[axis], q);
    }
  }
  return { low, high, span: high.map((v, i) => v - low[i]) };
}

test('R40 keeps the complete component menu and binds every displayed mesh', () => {
  validateGuide(guide);
  assert.deepEqual(Object.keys(assemblyComponents(guide, true)), ['keys', 'xiao', 'battery', 'cable', 'whole']);
  for (const [file, digest] of Object.entries(guide.sources.meshes_sha256)) {
    assert.equal(sha(readFileSync(new URL(file, exportsUrl))), digest, file);
  }
  const bom = read('../complete-assembly.json');
  assert.deepEqual(guide.print_components, Object.fromEntries(Object.entries(bom.groups).map(([n, v]) => [n, v.parts])));
  assert.equal(Object.values(guide.print_components).flat().length, 7);
  assert.ok(guide.modules.whole.note.includes('R40'));
});

test('the rendered OP1 board is crosswise and stays at its checked mount', () => {
  const module = guide.modules.dfr;
  const step = module.steps.find(s => s.title === 'Touch, Click and Release');
  const board = bounds(module.actors.board.file, step.samples.at(-1).board);
  assert.ok(Math.abs(board.span[0] - 30) < .001);
  assert.ok(Math.abs(board.span[1] - 10) < .001);
  assert.ok(Math.abs(board.low[2] - 8.8) < .001);
  assert.ok(Math.abs(board.high[0] + board.low[0]) < .001);
  assert.ok(step.samples.length >= 40);
  assert.ok(step.samples.some(pose => pose.plunger[11] < -.2));
  assert.ok(Math.abs(step.samples.at(-1).plunger[11]) < .03);
});

test('the harness enters from below and upper keycaps remain lifted until it is seated', () => {
  const steps = guide.modules.dfr.steps;
  const plug = steps.find(s => s.title === 'Connect the Cable Underneath');
  assert.equal(plug.samples[0].plug[11], -9);
  assert.equal(plug.samples.at(-1).plug[11], 0);
  const caps = steps.find(s => s.title === 'Refit the Upper Keycaps');
  for (const name of ['keycap_3', 'keycap_4']) {
    assert.ok(plug.samples.at(-1)[name][11] > caps.samples.at(-1)[name][11] + 10);
  }
  const catalog = JSON.parse(readFileSync(new URL('../hardware/carbon-rod-holders/assembly/catalog.json', import.meta.url)));
  assert.ok(catalog.versions.some(v => v.id === 'r39'));
  assert.ok(catalog.versions.some(v => v.id === 'r40'));
});
