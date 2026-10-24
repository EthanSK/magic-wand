import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,copyFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
test('known calibration survives restart per device, and deep rest requires fresh evidence',{skip:process.platform!=='darwin'},()=>{
 const dir=mkdtempSync(join(tmpdir(),'wand-calibration-'));
 try {
  copyFileSync(new URL('./native-calibration-main.swift',import.meta.url),join(dir,'main.swift'));
  const sources=['WandCalibration.swift','WandPointerControl.swift'].map(n=>fileURLToPath(new URL('../receiver/Sources/'+n,import.meta.url)));
  const build=spawnSync('swiftc',['-O',...sources,join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});
  assert.equal(build.status,0,build.stderr);
  const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(run.status,0,run.stdout+run.stderr);
 }finally{rmSync(dir,{recursive:true,force:true})}
});
