import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,copyFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
// Synthetic hand-motion profiles on the actual V3 controller: deterministic regression
// evidence, not physical acceptance of the wand's scrolling feel.
test('V3 held-scroll motion profiles, reversal and stop safety', {skip:process.platform!=='darwin'},()=>{
 const dir=mkdtempSync(join(tmpdir(),'wand-sustained-'));
 try {
 copyFileSync(new URL('./fixtures/sustained-scroll-main.swift',import.meta.url),join(dir,'main.swift'));
 const sources=['../receiver/Sources/WandPointerControl.swift','./fixtures/sustained-scroll-sim.swift'].map(path=>new URL(path,import.meta.url).pathname);
 const compile=spawnSync('swiftc',['-O',...sources,join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});
 assert.equal(compile.status,0,compile.stderr);
 const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(run.status,0,run.stdout+run.stderr);
 } finally {rmSync(dir,{recursive:true,force:true});}
});
