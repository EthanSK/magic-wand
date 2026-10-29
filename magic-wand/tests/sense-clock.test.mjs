import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
test('firmware deadlines tolerate a newer command timestamp and clock wrap',()=>{
 const dir=mkdtempSync(join(tmpdir(),'wand-clock-'));
 try {
  const header=fileURLToPath(new URL('../device/sense/wand_sense/wand_time.h',import.meta.url));
  const source=join(dir,'check.cpp'),binary=join(dir,'check');
  writeFileSync(source,`#include "${header}"\n#include <cassert>\nint main(){
   assert(wandElapsed(100,101)==0); // command refresh after this loop's initial tick
   assert(wandElapsed(101,100)==1);
   assert(wandElapsed(4,0xfffffffeU)==6); // millis wraps naturally
   assert(wandElapsed(300101,100)==300001); // genuine five-minute rest still expires
  }\n`);
  const built=spawnSync('c++',['-std=c++17',source,'-o',binary],{encoding:'utf8'});assert.equal(built.status,0,built.stderr);
  const ran=spawnSync(binary,[],{encoding:'utf8'});assert.equal(ran.status,0,ran.stderr);
 } finally {rmSync(dir,{recursive:true,force:true});}
});

test('merged readings keep their mean rate and never overflow',()=>{
 const dir=mkdtempSync(join(tmpdir(),'wand-merge-'));
 try {
  const header=fileURLToPath(new URL('../device/sense/wand_sense/wand_merge.h',import.meta.url));
  const source=join(dir,'check.cpp'),binary=join(dir,'check');
  writeFileSync(source,`#include "${header}"\n#include <cassert>\nint main(){
   WandMerged m={};const int16_t a[3]={1,2,8192};
   const int16_t g1[3]={100,-7,0},g2[3]={300,-8,0},g3[3]={-50,0,1};
   wandMergeAdd(m,1000,g1,a,true);wandMergeAdd(m,10615,g2,a,true);
   assert(m.count==2&&m.first==1000&&m.last==10615&&wandMergeMean(m,0)==200&&wandMergeMean(m,1)==-8);
   WandMerged unsent=m;m=WandMerged{};wandMergeAdd(m,20230,g3,a,true); // newer reading arrived during a failed send
   wandMergeRestore(m,unsent);assert(m.count==3&&m.first==1000&&m.last==20230&&m.gyro[0]==350);
   WandMerged full={};for(int i=0;i<400;++i)wandMergeAdd(full,i,g1,a,true);
   assert(full.count==WAND_MERGE_MAX&&wandMergeMean(full,0)==100&&full.last==399);
   wandMergeRestore(full,unsent);assert(full.count==WAND_MERGE_MAX);
   WandMerged beforeRelease=unsent; beforeRelease.epoch=8;
   WandMerged released={};released.epoch=9;wandMergeAdd(released,30000,g3,a,true);
   wandMergeRestore(released,beforeRelease);
   assert(released.count==1&&released.first==30000&&released.gyro[0]==-50);
   WandMerged newSession={};newSession.epoch=10;wandMergeRestore(newSession,beforeRelease);
   assert(newSession.count==0); // no stale motion after reconnect or sensor change
   WandMerged quiet={};const int16_t z[3]={0,0,0};wandMergeAdd(quiet,5,z,a,false);assert(wandMergeMean(quiet,0)==0&&!quiet.hasGyro);
  }\n`);
  const built=spawnSync('c++',['-std=c++17',source,'-o',binary],{encoding:'utf8'});assert.equal(built.status,0,built.stderr);
  const ran=spawnSync(binary,[],{encoding:'utf8'});assert.equal(ran.status,0,ran.stderr);
 } finally {rmSync(dir,{recursive:true,force:true});}
});
