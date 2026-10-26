import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
test('Print V4 retains helix, continuous taper, both handed grips and complete matched projects', () => {
  const script=fileURLToPath(new URL('../hardware/printed-loop-wand/v4/verify_release.py',import.meta.url));
  const result=spawnSync('python3',['-B',script,'--check'],{encoding:'utf8'});
  assert.equal(result.status,0,result.stdout+result.stderr);
});
