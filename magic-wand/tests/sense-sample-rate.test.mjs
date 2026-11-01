// Compile the real register functions with an inert IMU, never a physical board.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
test('runtime sample-rate changes verify registers, preserve ranges/modes and revert',()=>{
 const firmware=new URL('../device/sense/wand_sense/',import.meta.url);
 const text=readFileSync(new URL('wand_sense.ino',firmware),'utf8');
 function method(name){const start=text.indexOf('static '+name);assert(start>=0,name);let end=text.indexOf('{',start)+1,depth=1;while(depth){if(text[end]==='{')depth++;if(text[end]==='}')depth--;end++;}return text.slice(start,end);}
 const code=readFileSync(new URL('fixtures/sense-rate-main.cpp',import.meta.url),'utf8').replace('/*LIVE_RATE_FUNCTIONS*/',method('void setIMUMode(')+'\n'+method('bool configureSampleRate('));
 const dir=mkdtempSync(join(tmpdir(),'wand-rate-'));
 try {
  writeFileSync(join(dir,'main.cpp'),code);
  const built=spawnSync('c++',['-std=c++17','-I',fileURLToPath(firmware),join(dir,'main.cpp'),'-o',join(dir,'check')],{encoding:'utf8'});
  assert.equal(built.status,0,built.stderr);
  const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(run.status,0,run.stdout+run.stderr);
 }finally{rmSync(dir,{recursive:true,force:true});}
});
