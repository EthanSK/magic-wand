import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
test('Print V8 contact-facing airflow, lower ergonomic loop, higher buttons, both hands and matched projects stay reproducible',()=>{
 const r=spawnSync('python3',['-B',fileURLToPath(new URL('../hardware/printed-loop-wand/v8/verify_release.py',import.meta.url)),'--check'],{encoding:'utf8'});
 assert.equal(r.status,0,r.stdout+r.stderr);
});
