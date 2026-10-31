import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,copyFileSync,rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

// Ethan, 2026-10-31: the pointer jumped back, often after a stop-to-click. A
// passive capture showed macOS reporting the wand's own positions up to 0.37 s
// late. These cases run the real WandPointerOrigin: long lag, the click spot,
// alternating late reports, recenter, negative and large coordinates, physical
// mouse handover (including onto the wand's old path), stale input ordering,
// idle and bounded history. A bare executable: nothing is posted.
test('late macOS cursor reports never move the wand pointer back', {skip:process.platform!=='darwin'}, () => {
 const dir=mkdtempSync(join(tmpdir(),'wand-origin-lag-'));
 try {
  copyFileSync(new URL('fixtures/pointer-origin-lag-main.swift',import.meta.url),join(dir,'main.swift'));
  const built=spawnSync('swiftc',['-O',fileURLToPath(new URL('../receiver/Sources/WandPointerControl.swift',import.meta.url)),join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});
  assert.equal(built.status,0,built.stderr);
  const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});
  assert.equal(run.status,0,run.stdout+run.stderr);
  assert.match(run.stdout,/PASS origin scenarios/);
 } finally {rmSync(dir,{recursive:true,force:true});}
});
