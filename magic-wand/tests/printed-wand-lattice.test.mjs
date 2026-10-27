import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
test('Lightweight studies preserve source/export freshness, both hands and prepared print checks',()=>{
  const r=spawnSync('python3',['-B',fileURLToPath(new URL('../hardware/printed-loop-wand/lattice-study/verify_release.py',import.meta.url))],{encoding:'utf8'});
  assert.equal(r.status,0,r.stdout+r.stderr);
});
