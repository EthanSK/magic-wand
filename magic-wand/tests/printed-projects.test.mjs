import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { readFileSync } from 'node:fs';

test('shared Bambu projects match current CAD and contain no private paths', () => {
  const script = fileURLToPath(new URL('../hardware/printed-loop-wand/print_projects.py', import.meta.url));
  const result = spawnSync('python3', [script, '--check'], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stdout + result.stderr);
});

test('the shared plate includes two whole spiral wands, not only two handles', () => {
  const receipt = JSON.parse(readFileSync(new URL('../../magic-wand-3d-models/manifest.json', import.meta.url), 'utf8'));
  const pair = receipt.projects.pair;
  assert.equal(pair.parts, 8);
  for (const name of ['shaft-lower-tapered-spiral', 'shaft-upper-tapered-spiral', 'tip-xiao']) {
    assert.equal(pair.part_names.filter((part) => part === name).length, 2, name);
  }
  assert.equal(pair.part_names.filter((part) => part === 'handle-tapered-spiral').length, 1);
  assert.equal(pair.part_names.filter((part) => part === 'handle-tapered-mug-spiral').length, 1);
});
