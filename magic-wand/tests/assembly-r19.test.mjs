// Bind every instructional pose to the current R19 exports and exercise actual
// intermediate loading directions, not just labels or a finished screenshot.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { recipes, assemblyPose } from '../hardware/carbon-rod-holders-r19-lightweight/preview/assembly-recipe.mjs';
const exportsUrl = new URL('../hardware/carbon-rod-holders-r19-lightweight/exports/', import.meta.url);
const data = JSON.parse(readFileSync(new URL('assembly-guide.json', exportsUrl), 'utf8'));
const hash = name => createHash('sha256').update(readFileSync(new URL(name, exportsUrl))).digest('hex');

test('guide references the exact current print meshes', () => {
  assert.equal(data.sources.manifest_sha256, hash('manifest.json'));
  for (const [name, digest] of Object.entries(data.sources.assembly_mesh_sha256)) assert.equal(hash(name + '-assembly.stl'), digest, name);
  assert.equal(data.revision, 'carbon-rod-holders-r19-lightweight');
});

test('XIAO slides toward USB at a tilt, lowers, then accepts its keeper', () => {
  const before = assemblyPose('xiao', 1, 0, data), after = assemblyPose('xiao', 1, 1, data);
  assert.equal(before.boardY, -data.board.slide_mm); assert.ok(Math.abs(after.boardY) < 1e-9);
  assert.equal(before.boardAngle, after.boardAngle); assert.ok(before.boardAngle < 0);
  assert.ok(Math.abs(assemblyPose('xiao', 2, 1, data).boardAngle) < 1e-9);
  assert.equal(assemblyPose('xiao', 3, 0, data).keeperY, -data.board.keeper_travel_mm);
  assert.ok(Math.abs(assemblyPose('xiao', 3, 1, data).keeperY) < 1e-9);
});

test('motion is continuous between steps and finishes with all parts seated', () => {
  for (const [kind, steps] of Object.entries(recipes)) {
    for (let i = 0; i < steps.length - 1; i++) {
      const end = assemblyPose(kind, i, 1, data), start = assemblyPose(kind, i + 1, 0, data);
      for (const key of Object.keys(end)) if (!key.startsWith('rod')) assert.ok(Math.abs(end[key] - start[key]) < 1e-9, `${kind} ${i} ${key}`);
    }
    const pose = assemblyPose(kind, steps.length - 1, 1, data);
    assert.equal(pose.rodY, 0); assert.equal(pose.rodVisible, true);
    if (kind === 'battery') { assert.equal(pose.cellY, 0); assert.equal(pose.cellZ, data.battery.spacer_thickness_mm); assert.equal(pose.doorZ, 0); }
    else { assert.equal(pose.boardY, 0); assert.equal(pose.boardZ, 0); assert.equal(pose.boardAngle, 0); assert.equal(pose.keeperY, 0); }
  }
});
