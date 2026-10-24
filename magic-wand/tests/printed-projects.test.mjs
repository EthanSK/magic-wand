import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

test('shared Bambu projects match current CAD and contain no private paths', () => {
  const script = fileURLToPath(new URL('../hardware/printed-loop-wand/print_projects.py', import.meta.url));
  const result = spawnSync('python3', [script, '--check'], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stdout + result.stderr);
});
