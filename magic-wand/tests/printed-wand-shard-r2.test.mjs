import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
test('Shard R2 repairs preserve final CAD receipts, both-handed normal meshes, actual switch holes, battery loading and weighted-cap settings',()=>{
 const r=spawnSync('python3',['-B',fileURLToPath(new URL('../hardware/printed-loop-wand/shard-tube-r2/verify_release.py',import.meta.url))],{encoding:'utf8'});
 assert.equal(r.status,0,r.stdout+r.stderr);
});
