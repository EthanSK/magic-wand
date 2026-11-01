// Exercise the firmware's actual identity formatter without connecting to hardware.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {spawnSync} from 'node:child_process';

test('reset diagnostics fit one queued identity message at maximum field widths',()=>{
 const source=readFileSync(new URL('../device/sense/wand_sense/wand_sense.ino',import.meta.url),'utf8');
 const start=source.indexOf('  const int n = snprintf(text, sizeof(text),',source.indexOf('static void sendIdentity('));
 const end=source.indexOf('  if (n > 0',start);
 assert(start>=0&&end>start,'one guarded identity formatter');
 const formatter=source.slice(start,end),version=source.match(/static const char FIRMWARE\[\] = "([^"]+)";/)?.[1];
 assert(version);
 const cpp=`#include <cassert>
#include <cstdio>
#include <cstdint>
#include <cstring>
constexpr uint32_t POWER_RESETREAS_RESETPIN_Msk=1,POWER_RESETREAS_DOG_Msk=2,POWER_RESETREAS_SREQ_Msk=4,POWER_RESETREAS_LOCKUP_Msk=8,POWER_RESETREAS_OFF_Msk=65536,POWER_RESETREAS_VBUS_Msk=1048576;
struct FICR {uint32_t DEVICEID[2]={UINT32_MAX,UINT32_MAX};}; FICR ficr; FICR *NRF_FICR=&ficr;
const char FIRMWARE[]="${version}";
uint32_t FIRMWARE_NUMBER=UINT32_MAX,bootResetReason=UINT32_MAX,updateTarget=UINT32_MAX;
bool imuReady=false,wokeFromOff=false,updateKeyPresent=false;
uint16_t activeRateHz=6660;
int WAND_UPDATE_PROTOCOL=255,updateResult=0,MBR_SIZE=0;
const char *wandUpdateResultName(int){return "installed";}
uint32_t SD_FWID_GET(int){return UINT32_MAX;} uint32_t codeStart(){return UINT32_MAX;} uint32_t bootloaderStart(){return UINT32_MAX;}
int main(){char text[512],loader[16];memset(loader,'9',15);loader[15]=0;
${formatter}
assert(n>0&&n<int(sizeof(text)));assert(strlen(text)==size_t(n));fwrite(text,1,n,stdout);}
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-reset-identity-'));
 try {
  const input=join(dir,'main.cpp'),binary=join(dir,'check');writeFileSync(input,cpp);
  const built=spawnSync('c++',['-std=c++17',input,'-o',binary],{encoding:'utf8'});assert.equal(built.status,0,built.stderr);
  const run=spawnSync(binary,[],{encoding:'utf8'});assert.equal(run.status,0,run.stderr);
  assert(Buffer.byteLength(run.stdout)<512);
  const lines=run.stdout.trim().split('\n');assert.equal(lines.length,2,'identity and boot event share one message');
  const identity=JSON.parse(lines[0].slice(1));assert.equal(identity.resetReason,0xffffffff);assert.equal(identity.firmware,version);
  assert.equal(lines[1],'Eboot reset=4294967295 off=1 software=1 watchdog=1 lockup=1 pin=1 vbus=1');
 } finally {rmSync(dir,{recursive:true,force:true});}
});
