// Inert click-lane regressions for the settled first click and one-second stationary repeats; never sends live input.
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
 assert.match(control,/resting:!permitted\)/);
});

test('slow stops and tiny re-targets keep the precision pause, brisk stops stay quick, still pointers repeat', {skip:process.platform!=='darwin'}, ()=>{
 const dir=mkdtempSync(join(tmpdir(),'wand-settled-stop-'));
 try {
  copyFileSync(new URL('fixtures/settled-stop-click-main.swift',import.meta.url),join(dir,'main.swift'));
  const built=spawnSync('swiftc',['-O',fileURLToPath(new URL('WandPointerControl.swift',sources)),join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});
  assert.equal(built.status,0,built.stderr);
  for(const hz of ['104','240']) {
  const run=spawnSync(join(dir,'check'),[hz],{encoding:'utf8',timeout:30000});
  assert.equal(run.status,0,run.stdout+run.stderr);
  assert.match(run.stdout,/PASS: precision first and re-target clicks/);
  assert.match(run.stdout,/PASS: cancellation, scroll recoil and missing readings/);
  assert.match(run.stdout,/PASS: coherent sub-pixel restart cancels repetition/);
  assert.match(run.stdout,/PASS: stationary repeats stay one interval apart/);
  assert.match(run.stdout,/PASS: one stop is consumed once; tiny deliberate re-target keeps precision pause/);
  }
 } finally {rmSync(dir,{recursive:true,force:true});}
});
