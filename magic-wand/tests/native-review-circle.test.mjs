import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
test('independent review circles use existing ordered Better Git ratchets', {skip:process.platform!=='darwin'},()=>{
 const dir=mkdtempSync(join(tmpdir(),'wand-review-circles-'));
 try {
  writeFileSync(join(dir,'main.swift'),readFileSync(new URL('./fixtures/review-circle-main.swift',import.meta.url)));
  const build=spawnSync('swiftc',['-O',new URL('../receiver/Sources/WandPointerControl.swift',import.meta.url).pathname,join(dir,'main.swift'),'-o',join(dir,'test')],{encoding:'utf8'});
  assert.equal(build.status,0,build.stderr);
  const run=spawnSync(join(dir,'test'),[],{encoding:'utf8'});assert.equal(run.status,0,run.stdout+run.stderr);
 }finally{rmSync(dir,{recursive:true,force:true});}
});

for(const name of ['review-gesture-main','desk-sleep-main']) {
 test(`native ${name}`, {skip:process.platform!=='darwin'},()=>{
  const dir=mkdtempSync(join(tmpdir(),'wand-native-policy-'));
  try {
   writeFileSync(join(dir,'main.swift'),readFileSync(new URL(`./fixtures/${name}.swift`,import.meta.url)));
   const b=spawnSync('swiftc',['-O',new URL('../receiver/Sources/WandPointerControl.swift',import.meta.url).pathname,join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});
   assert.equal(b.status,0,b.stderr);
   const r=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(r.status,0,r.stdout+r.stderr);
  }finally{rmSync(dir,{recursive:true,force:true});}
 });
}
