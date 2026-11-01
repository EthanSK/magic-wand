import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,copyFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
test('experiment requests are reversible, acknowledged and bounded; counters never schedule input', {skip:process.platform!=='darwin'},()=>{
 const dir=mkdtempSync(join(tmpdir(),'wand-experiment-'));
 try {
  copyFileSync(new URL('fixtures/experiment-main.swift',import.meta.url),join(dir,'main.swift'));
  const sources=['WandExperiment.swift','WandExperimentModel.swift'].map(n=>fileURLToPath(new URL('../receiver/Sources/'+n,import.meta.url)));
  const built=spawnSync('swiftc',['-O',...sources,join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});
  assert.equal(built.status,0,built.stderr);
  const run=spawnSync(join(dir,'check'),[],{encoding:'utf8',timeout:30000});
  assert.equal(run.status,0,run.stdout+run.stderr);
  assert.match(run.stdout,/PASS: reversible rate control/);
 }finally{rmSync(dir,{recursive:true,force:true});}
});
