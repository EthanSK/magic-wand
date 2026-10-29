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
