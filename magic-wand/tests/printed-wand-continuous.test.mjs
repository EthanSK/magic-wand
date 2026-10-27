import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
test('Continuous Two wide spirals preserves the removable loop and checked print files',()=>{
  const r=spawnSync('python3',['-B',fileURLToPath(new URL('../hardware/printed-loop-wand/continuous-two-wide/verify_release.py',import.meta.url))],{encoding:'utf8'});
  assert.equal(r.status,0,r.stdout+r.stderr);
});
