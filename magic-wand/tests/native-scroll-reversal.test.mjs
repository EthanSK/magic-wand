import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,copyFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
// Actual V3 controller with inert output. A deliberate opposite stroke must
// not continue old-direction page output while it qualifies as a reversal.
test('page scroll reversals do not kick in the old direction or replay skipped output',{skip:process.platform!=='darwin'},()=>{
 const d=mkdtempSync(join(tmpdir(),'wand-reversal-'));
 try {
  copyFileSync(new URL('fixtures/scroll-reversal-main.swift',import.meta.url),join(d,'main.swift'));
  const b=spawnSync('swiftc',[new URL('../receiver/Sources/WandPointerControl.swift',import.meta.url).pathname,join(d,'main.swift'),'-o',join(d,'check')],{encoding:'utf8'});
  assert.equal(b.status,0,b.stderr);
  const r=spawnSync(join(d,'check'),[],{encoding:'utf8'});assert.equal(r.status,0,r.stdout+r.stderr);
 } finally {rmSync(d,{recursive:true,force:true})}
});
