import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,readFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {createHmac,createHash} from 'node:crypto';

// Ethan (2026-10-30): "Is this firmware also gonna add wireless updates?" Pure checks of the
// Sense firmware's update authorization, compiled for the host. They do not exercise the
// bootloader, the radio or a real board.
const header=fileURLToPath(new URL('../device/sense/wand_sense/wand_update.h',import.meta.url));
const usb=fileURLToPath(new URL('../device/sense/wand_sense/wand_usb_output.h',import.meta.url));
const light=fileURLToPath(new URL('../device/sense/wand_sense/wand_light.h',import.meta.url));
const firmware=readFileSync(new URL('../device/sense/wand_sense/wand_sense.ino',import.meta.url),'utf8');
function run(body){
 const dir=mkdtempSync(join(tmpdir(),'wand-update-'));
 try {
  const source=join(dir,'check.cpp'),binary=join(dir,'check');
  writeFileSync(source,`#include "${header}"\n#include "${light}"\n#include "${usb}"\n#include <string>\n#include <algorithm>\n#include <cassert>\n#include <cstring>\n#include <initializer_list>\n${body}\n`);
  const built=spawnSync('c++',['-std=c++17','-Wall','-Werror','-Wno-unused-function','-Wno-unused-const-variable',source,'-o',binary],{encoding:'utf8'});
  assert.equal(built.status,0,built.stderr);
  const ran=spawnSync(binary,[],{encoding:'utf8'});assert.equal(ran.status,0,ran.stdout+ran.stderr);
  return ran.stdout;
 } finally {rmSync(dir,{recursive:true,force:true});}
}
const hex=(b)=>Buffer.from(b).toString('hex');

test('SHA-256 and HMAC-SHA256 match the published vectors and Node crypto',()=>{
 const long='a'.repeat(1000),key131=Buffer.alloc(131,0xaa);
 const cases=[
  ['',createHash('sha256').update('').digest('hex')],
  ['abc','ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'],
  ['abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq','248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1'],
  [long,createHash('sha256').update(long).digest('hex')],
 ];
 const hmacs=[
  // RFC 4231 test cases 1, 2 and 6 (key longer than the block).
  [Buffer.alloc(20,0x0b),Buffer.from('Hi There'),'b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7'],
  [Buffer.from('Jefe'),Buffer.from('what do ya want for nothing?'),'5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843'],
  [key131,Buffer.from('Test Using Larger Than Block-Size Key - Hash Key First'),'60e431591ee0b67f0d8a26aacbf5b77f8e0bc6213728c5140546040f0ee37f54'],
 ];
 const out=run(`int main(){
  const char *inputs[]={${cases.map(([m])=>JSON.stringify(m)).join(',')}};
  for(const char *m:inputs){WandSha256 s;wandShaInit(s);wandShaUpdate(s,(const uint8_t*)m,strlen(m));uint8_t d[32];wandShaFinal(s,d);char h[65];wandHexEncode(d,32,h);printf("%s\\n",h);}
  ${hmacs.map(([k,m])=>`{const uint8_t k[]={${[...k].join(',')}};const uint8_t m[]={${[...m].join(',')}};uint8_t d[32];wandHmacSha256(k,sizeof(k),m,sizeof(m),d);char h[65];wandHexEncode(d,32,h);printf("%s\\n",h);}`).join('\n')}
 }`).trim().split('\n');
 assert.deepEqual(out,[...cases.map(([,d])=>d),...hmacs.map(([,,d])=>d)]);
});

test('only a fresh, keyed authorization for the exact image hands over, and only forward',()=>{
 const key=Buffer.from('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f','hex');
 const board='1a2b3c4d5e6f7081',nonce='00112233445566778899aabbccddeeff';
 const tag=(version,size,crc,k=key,n=nonce)=>createHmac('sha256',k).update(`wand-sense-update-1|${board}|${n}|${version}|${size}|${crc.toString(16).padStart(4,'0')}`).digest('hex');
 const good=tag(7,132472,0x3849),wrongKey=tag(7,132472,0x3849,Buffer.alloc(32,9)),oldNonce=tag(7,132472,0x3849,key,'ff'.repeat(16));
 const line=(v,s,c,t)=>`UA${v},${s},${c.toString(16).padStart(4,'0')},${t}`;
 run(`static WandUpdateRefusal check(const char *line,uint32_t now=5000,uint32_t mv=3900,bool charging=false,bool held=false,bool key=true,bool ble=true,bool nonce=true,uint32_t version=6,uint32_t limit=397312){
  WandUpdateRequest r; if(!wandParseUpdateRequest(line,strlen(line),r)) return WAND_UPDATE_BOOTLOADER; // marker: parse failure
  uint8_t k[32]; wandHexDecode("${key.toString('hex')}",64,k,32);
  WandUpdateContext c={key,k,ble,nonce,"${nonce}",1000,now,"${board}",version,limit,uint16_t(mv),charging,held};
  return wandAuthorizeUpdate(r,c);
 }
 int main(){
  const char *ok="${line(7,132472,0x3849,good)}";
  assert(check(ok)==WAND_UPDATE_OK);
  // Authentication: wrong key, another nonce, and any changed image field.
  assert(check("${line(7,132472,0x3849,wrongKey)}")==WAND_UPDATE_AUTH);
  assert(check("${line(7,132472,0x3849,oldNonce)}")==WAND_UPDATE_AUTH);
  assert(check("${line(8,132472,0x3849,good)}")==WAND_UPDATE_AUTH);
  assert(check("${line(7,132473,0x3849,good)}")==WAND_UPDATE_AUTH);
  assert(check("${line(7,132472,0x3848,good)}")==WAND_UPDATE_AUTH);
  // No key, Bluetooth only, single-use and 30 s nonces.
  assert(check(ok,5000,3900,false,false,false)==WAND_UPDATE_NO_KEY);
  assert(check(ok,5000,3900,false,false,true,false)==WAND_UPDATE_TRANSPORT);
  assert(check(ok,5000,3900,false,false,true,true,false)==WAND_UPDATE_NONCE);
  assert(check(ok,1000+WAND_UPDATE_NONCE_MS)==WAND_UPDATE_NONCE);
  assert(check(ok,999)==WAND_UPDATE_OK); // a timestamp one tick newer than the nonce is not "49 days"
  // Authenticated but unsafe: versions only move forward; size within the conservative application-size cap.
  assert(check(ok,5000,3900,false,false,true,true,true,7)==WAND_UPDATE_VERSION);
  assert(check(ok,5000,3900,false,false,true,true,true,6,0)==WAND_UPDATE_BOOTLOADER);
  assert(check(ok,5000,3900,false,false,true,true,true,6,132471)==WAND_UPDATE_SIZE);
  assert(check(ok,5000,3599)==WAND_UPDATE_BATTERY);
  assert(check(ok,5000,3599,true)==WAND_UPDATE_OK); // low but charging
  assert(check(ok,5000,3900,false,true)==WAND_UPDATE_BUSY);
  // Authentication precedes image checks: a stranger learns nothing about version or battery.
  assert(check("${line(5,999999,0,wrongKey)}",5000,100)==WAND_UPDATE_AUTH);
  // Malformed lines never parse.
  WandUpdateRequest r;
  for(const char *bad:{"UA","UA7","UA7,1,38499,${good}","UA7,1,3849,${good.slice(2)}","UA-7,1,3849,${good}","UA99999999999,1,3849,${good}","UB7,1,3849,${good}","UA7,1,38g9,${good}"}) assert(!wandParseUpdateRequest(bad,strlen(bad),r));
  // The bootloader layout: s140 7.3.0 code starts at 0x27000, bootloader at 0xF4000, 40 KB reserved.
  assert(wandBankedLimit(0x27000,0xF4000,10*4096)==397312);
  assert(wandBankedLimit(0x27000,0x27000,0)==0 && wandBankedLimit(0xF4000,0x27000,0)==0);
  char t[16]; wandBootloaderText(0x000602,t); assert(strcmp(t,"0.6.2")==0);
  // Post-update result.
  assert(wandUpdateResult(false,7,7)==WAND_UPDATE_RESULT_NONE);
  assert(wandUpdateResult(true,7,7)==WAND_UPDATE_RESULT_INSTALLED);
  assert(wandUpdateResult(true,7,6)==WAND_UPDATE_RESULT_NOT_INSTALLED);
 }`);
});

test('firmware lights stay in their own colour families and stop like every board-owned light',()=>{
 run(`static bool same(WandRgb a,WandRgb b){return a.r==b.r&&a.g==b.g&&a.b==b.b;}
 int main(){
  const WandRgb host[]={{0,255,0},{255,0,0},{0,0,255},{0,255,255}},orange={255,80,0},white={255,255,255};
  for(const WandRgb &c:host){assert(!same(c,WAND_FIRMWARE_MAGENTA));}
  assert(!same(WAND_FIRMWARE_MAGENTA,orange)&&!same(WAND_FIRMWARE_MAGENTA,white));
  // Handoff: three fast flashes, 600 ms in all.
  assert(WAND_HANDOFF_STEPS*WAND_HANDOFF_STEP_MS==600);
  for(uint8_t i=0;i<WAND_HANDOFF_STEPS;++i) assert(same(wandHandoffColour(i),i%2?WAND_LIGHT_DARK:WAND_FIRMWARE_MAGENTA));
  // Verification: slower than every other board-owned animation, and wraps with millis().
  assert(WAND_VERIFY_BLINK_MS>WAND_LOADING_BLINK_MS&&WAND_VERIFY_BLINK_MS>WAND_HANDOFF_STEP_MS);
  const uint32_t since=0xfffffe00U;
  for(uint32_t ms=0;ms<3000;ms+=50) assert(same(wandVerifyColour(since+ms,since),(ms/500)%2?WAND_LIGHT_DARK:WAND_FIRMWARE_MAGENTA));
  // White means not ready, distinct from the shorter two-flash sleep cue.
  assert(WAND_NOT_READY_PHASE_MS==275);
  for(uint32_t ms=0;ms<=60000;++ms) assert(same(wandNotReadyColour(since+ms,since),(ms/275)%2?WAND_LIGHT_DARK:WAND_NOT_READY_WHITE));
  assert(same(wandNotReadyColour(1000,1001),WAND_NOT_READY_WHITE));
 }`);
 const loop=firmware.slice(firmware.indexOf('void loop()'));
 assert.match(firmware,/session = from;[^\n]*loadingBlink = false; verifyBlink = false;/,'a host session ends the verification light');
 assert.match(loop,/chordPhase = 1; chordAt = now; loadingBlink = false; verifyBlink = false;/);
 assert.match(loop,/localDark = true; loadingBlink = false; verifyBlink = false; setLight\(0, 0, 0\);/);
 assert(loop.indexOf('OFFLINE_DARK_MS')<loop.indexOf('else if (verifyBlink)'),'the offline dark still wins');
 assert(loop.indexOf('else if (loadingBlink)')<loop.indexOf('else if (!localDark)'),'installation colours take priority over ordinary not-ready pulses');
 assert.match(loop,/wandNotReadyColour\(now, notReadySince\)/);
});

test('the firmware exposes no open updater and keeps the key off Bluetooth',()=>{
 assert.doesNotMatch(firmware,/^\s*BLEDfu\s+\w+\s*;|\.begin\(\);?\s*\/\/\s*dfu|bledfu\.begin|addService\(bledfu\)/m,'no open DFU control point is declared or started');
 assert.match(firmware,/static const char FIRMWARE\[\] = "wand-sense-8";\nstatic const uint32_t FIRMWARE_NUMBER = 8;/);
 const number=firmware.match(/static const uint32_t FIRMWARE_NUMBER = (\d+);/)[1];
 assert.equal(firmware.match(/static const char FIRMWARE\[\] = "wand-sense-(\d+)";/)[1],number,'the name and number agree');
 assert.match(firmware,new RegExp(`static const char WAND_IMAGE_MARKER\\[\\] = "WANDIMG1;xiao-nrf52840-sense;${number}";`),'the image marker carries the same number');
 assert.match(firmware,/\(void\)\*\(volatile const char \*\)WAND_IMAGE_MARKER;/,'the marker stays in the linked image');
 assert.match(firmware,/if \(c == 'U' \|\| c == 'K'\) \{ if \(session == from\) updateCommand\(line, length, from\); return; \}/,'only the current host session');
 const update=firmware.slice(firmware.indexOf('static void updateCommand('),firmware.indexOf('static int hexValue('));
 assert.match(update,/if \(line\[0\] == 'K'\) \{\n    if \(from != USB_LINK\) \{ sendUpdate\(from, "NO transport"\); return; \}/);
 assert.match(update,/nonceValid = false; \/\/ Single use, success or not\.\n  if \(result != WAND_UPDATE_OK\)/);
 assert(update.indexOf('wandAuthorizeUpdate(')<update.indexOf('enterUpdater('),'authorize before any handoff');
 assert.match(firmware,/static void endSession\(bool restarting\) \{\n  if \(session == NONE\) return;\n  nonceValid = false;/);
 assert.match(firmware,/char usbLine\[112\], bleLine\[112\];/);
 // The extracted handoff keeps the library's exact peer-data layout and magic.
 const handoff=firmware.slice(firmware.indexOf('static const char *enterUpdater('),firmware.indexOf('static void updateCommand('));
 for(const part of ['(peer_data_t *)(0x20007F80UL)','offsetof(peer_data_t, crc16) == 60','sd_power_gpregret_set(0, 0xB1)','sd_softdevice_disable()','bootloader_util_app_start(NRF_UICR->NRFFW[0])','writeFile(UPDATE_PENDING_FILE'])
  assert(handoff.includes(part),part);
 // Identity reports what the receiver needs for a fail-closed preflight.
 for(const field of ['firmwareNumber','bootloader','softDevice','codeStart','bootloaderStart','updater','updateKey','update'])
  assert.match(firmware,new RegExp(`\\\\"${field}\\\\":`),field);
});


test('USB identity finishes across a 256-byte FIFO without interleaved or replayed sensor frames',()=>{
 const identity='\nI'+JSON.stringify({protocol:'wand-sense-1',firmware:'wand-sense-6',id:'1a2b3c4d5e6f7081',imu:true,gyroDpsPerLsb:0.0175,accelGPerLsb:0.000122,odr:104,merge:true,wake:false,firmwareNumber:6,bootloader:'0.6.2',softDevice:291,codeStart:159744,bootloaderStart:999424,updater:1,updateKey:false,update:'not-installed',updateTarget:7})+'\n';
 assert(identity.length>256&&identity.length<=512);
 run(`struct FakeUSB {
  bool connected=true; size_t room=0; std::string wire;
  explicit operator bool() const { return connected; }
  int availableForWrite() const { return int(room); }
  size_t write(const uint8_t *p,size_t n) { assert(n<=room && n<=256); room-=n; wire.append((const char*)p,n); return n; }
 };
 int main(){
  FakeUSB port; WandUsbOutput output;
  const std::string identity=${JSON.stringify(identity)};
  const char *sensor="\\nS1,2,0,0,0,0,0,0,0,0,0,0,0\\n";
  assert(output.write(port,identity.data(),identity.size()));
  assert(!output.write(port,sensor,strlen(sensor))); // not queued behind identity
  port.room=256; output.drain(port); assert(port.wire.size()==256);
  assert(!output.write(port,sensor,strlen(sensor)));
  port.room=1; output.drain(port);
  port.room=256; output.drain(port); assert(port.wire==identity);
  port.room=0; assert(!output.write(port,sensor,strlen(sensor))); // sensor stays with the existing merge caller
  port.room=256; assert(output.write(port,sensor,strlen(sensor)));
  assert(port.wire==identity+sensor);
  // A USB disconnect drops the unfinished old control frame. Re-identifying
  // starts with the protocol newline and does not replay its old remainder.
  port.room=80; assert(output.write(port,identity.data(),identity.size()));
  port.connected=false; output.drain(port); assert(output.length==0);
  port.wire.clear(); port.connected=true; port.room=256;
  assert(output.write(port,identity.data(),identity.size()));
  while(output.length){port.room=64;output.drain(port);}
  assert(port.wire==identity);
  assert(!output.write(port,identity.data(),513));
 }`);
 assert.match(firmware,/usbOutput\.drain\(Serial\);/,'the main loop drains even without a session');
});

test('pending version is read back before GO and failed results clear only after a matching acknowledged erase',()=>{
 run(`int main(){
  uint8_t record[4]={}; bool writeOK=true,readOK=true,corrupt=false; int reads=0,go=0;
  auto write=[&](const uint8_t *p,size_t n){if(!writeOK)return false;memcpy(record,p,n);return true;};
  auto read=[&](uint8_t *p,size_t n){++reads;if(!readOK)return false;memcpy(p,record,n);if(corrupt)p[3]^=1;return true;};
  auto handoff=[&]{if(wandSaveUpdateRecord(7,write,read))++go;};
  writeOK=false;handoff();assert(go==0&&reads==0);
  writeOK=true;readOK=false;handoff();assert(go==0);
  readOK=true;corrupt=true;handoff();assert(go==0);
  corrupt=false;handoff();assert(go==1&&record[3]==7);
  assert(wandReviewedBootloader(0x000601) && wandReviewedBootloader(0x000602));
  for(uint32_t v:{0x000600U,0x000603U,0x000700U})assert(!wandReviewedBootloader(v));
  assert(wandAcknowledgeFailedResult("UR6,7",5,6,7,WAND_UPDATE_RESULT_NOT_INSTALLED));
  for(const char *line:{"UR6,8","UR7,7","UR6,7x","UR6","UV","UR6,4294967296"})assert(!wandAcknowledgeFailedResult(line,strlen(line),6,7,WAND_UPDATE_RESULT_NOT_INSTALLED));
  assert(!wandAcknowledgeFailedResult("UR6,7",5,6,7,WAND_UPDATE_RESULT_INSTALLED));
  bool exists=true;assert(!wandClearUpdateRecord([]{},[&]{return exists;}));
  assert(wandClearUpdateRecord([&]{exists=false;},[&]{return exists;}));
 }`);
 const handoff=firmware.slice(firmware.indexOf('static const char *enterUpdater('),firmware.indexOf('static void updateCommand('));
 assert(handoff.indexOf('wandSaveUpdateRecord(')<handoff.indexOf('"GO"'));
 assert(handoff.indexOf('"GO"')<handoff.indexOf('bootloader_util_app_start('));
 assert.match(handoff,/return "storage";/);
 assert.match(firmware,/uint8_t pending\[4\] = \{\};/);
 assert.match(firmware,/wandAcknowledgeFailedResult\(line, length, FIRMWARE_NUMBER, updateTarget, updateResult\)/);
 assert.match(firmware,/wandClearUpdateRecord\(/);
});
