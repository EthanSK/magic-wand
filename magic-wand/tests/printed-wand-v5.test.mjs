import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
test('Print V5 top-slide mounts, both hands and single-wand mass comparison stay reproducible',()=>{
 const r=spawnSync('python3',['-B',fileURLToPath(new URL('../hardware/printed-loop-wand/v5/verify_release.py',import.meta.url)),'--check'],{encoding:'utf8'});
 assert.equal(r.status,0,r.stdout+r.stderr);
});
