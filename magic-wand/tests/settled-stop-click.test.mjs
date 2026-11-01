// Inert click-lane regressions for the settled first click and 300 ms repeats; never sends live input.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,mkdtempSync,copyFileSync,rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

const sources=new URL('../receiver/Sources/',import.meta.url);

test('the receiver passes the stillness rest flag to the click lane only', ()=>{
 const main=readFileSync(new URL('main.swift',sources),'utf8');
 assert.match(main,/fineMove:sample\.fineMoving,resting:sample\.resting\)/);
 assert.match(main,/fineMove:fineMove,resting:resting\)/);
 const control=readFileSync(new URL('WandPointerControl.swift',sources),'utf8');
 assert.match(control,/static let settleHold=0\.06\b/,'Ethan approved 60 ms of idleness');
 assert.match(control,/resting:!permitted\)/);
});

test('slowed stops and tiny re-targets click promptly, still pointers repeat, tremor and slow aiming do not click', {skip:process.platform!=='darwin'}, ()=>{
 const dir=mkdtempSync(join(tmpdir(),'wand-settled-stop-'));
 try {
  copyFileSync(new URL('fixtures/settled-stop-click-main.swift',import.meta.url),join(dir,'main.swift'));
  const built=spawnSync('swiftc',['-O',fileURLToPath(new URL('WandPointerControl.swift',sources)),join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});
  assert.equal(built.status,0,built.stderr);
  for(const hz of ['104','240']) {
  const run=spawnSync(join(dir,'check'),[hz],{encoding:'utf8',timeout:30000});
  assert.equal(run.status,0,run.stdout+run.stderr);
  assert.match(run.stdout,/PASS: prompt first and re-target clicks/);
  assert.match(run.stdout,/PASS: cancellation, scroll recoil and missing readings/);
  assert.match(run.stdout,/PASS: coherent sub-pixel restart cancels repetition/);
  }
 } finally {rmSync(dir,{recursive:true,force:true});}
});
