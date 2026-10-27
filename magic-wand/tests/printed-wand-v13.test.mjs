import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
test('Print V13 upper-flared detachable loop, upward-seating loop, independent upper stops, clear downward release, curved cells and rounded rails and retained full spiral, both hands and matched projects stay reproducible',()=>{
 const r=spawnSync('python3',['-B',fileURLToPath(new URL('../hardware/printed-loop-wand/v13/verify_release.py',import.meta.url)),'--check'],{encoding:'utf8'});
 assert.equal(r.status,0,r.stdout+r.stderr);
});
