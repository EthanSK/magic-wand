import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,copyFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
test('V3 straight-drag continuation, reversal and stop safety', {skip:process.platform!=='darwin'},()=>{
 const dir=mkdtempSync(join(tmpdir(),'wand-sustained-'));
 try {
 copyFileSync(new URL('./fixtures/sustained-scroll-main.swift',import.meta.url),join(dir,'main.swift'));
 const compile=spawnSync('swiftc',['-O',new URL('../receiver/Sources/WandPointerControl.swift',import.meta.url).pathname,join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});
 assert.equal(compile.status,0,compile.stderr);
 const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(run.status,0,run.stdout+run.stderr);
 } finally {rmSync(dir,{recursive:true,force:true});}
});
