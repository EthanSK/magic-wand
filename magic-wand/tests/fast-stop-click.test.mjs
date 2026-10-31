import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,mkdtempSync,copyFileSync,rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

for (const fixture of ['fast-stop-click','fast-stop-settling']) test(`${fixture}: brisk stops preserve precision, stale-data and scroll-release safety`, {skip:process.platform!=='darwin'},()=>{
 const sources=new URL('../receiver/Sources/',import.meta.url);
 const main=readFileSync(new URL('main.swift',sources),'utf8');
 assert(main.includes('let dwell=WandDwellClick(fastStops:true)'));
 assert(main.includes('eligible:gate == nil,pointerX:x,pointerY:y'));
 const dir=mkdtempSync(join(tmpdir(),'wand-fast-stop-'));
 try {
  copyFileSync(new URL(`fixtures/${fixture}-main.swift`,import.meta.url),join(dir,'main.swift'));
  const built=spawnSync('swiftc',['-O',fileURLToPath(new URL('WandPointerControl.swift',sources)),join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});
  assert.equal(built.status,0,built.stderr);
  const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});
  assert.equal(run.status,0,run.stdout+run.stderr);
 } finally {rmSync(dir,{recursive:true,force:true});}
});
