// Inert click-lane regressions for the visible precision pause; never sends live input.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,mkdtempSync,copyFileSync,rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

const sources=new URL('../receiver/Sources/',import.meta.url);

test('the tuned motion signal alone vetoes the ordinary click; fine aiming is bounded in the dwell', ()=>{
 const main=readFileSync(new URL('main.swift',sources),'utf8');
 // Receiver192: the veto is ignored only while the Sense stillness gate holds the reading at rest.
 assert.match(main,/dwell\.intent\(sample\.intent && !sample\.resting,now:now\)/);
 assert.doesNotMatch(main,/dwell\.intent\([^)]*fineMoving/, 'invisible sub-pixel readings must not postpone clicks without bound');
 const control=readFileSync(new URL('WandPointerControl.swift',sources),'utf8');
 assert.match(control,/let quietForClick = !permitted \|\| smoothSpeed<=v\[5\] \|\| v\[2\]==0/);
});

test('visible stops click after the 200 ms pause; slow aiming, fine targets and fast stops are preserved', {skip:process.platform!=='darwin'}, ()=>{
 const dir=mkdtempSync(join(tmpdir(),'wand-visible-stop-'));
 try {
  copyFileSync(new URL('fixtures/visible-stop-click-main.swift',import.meta.url),join(dir,'main.swift'));
  const built=spawnSync('swiftc',['-O',fileURLToPath(new URL('WandPointerControl.swift',sources)),join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});
  assert.equal(built.status,0,built.stderr);
  const run=spawnSync(join(dir,'check'),[],{encoding:'utf8',timeout:30000});
  assert.equal(run.status,0,run.stdout+run.stderr);
  assert.match(run.stdout,/PASS: visible stops click sooner/);
  assert.match(run.stdout,/PASS: the precision pause starts at the last visible step/);
 } finally {rmSync(dir,{recursive:true,force:true});}
});
