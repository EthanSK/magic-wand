const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const test=require('node:test'),assert=require('node:assert/strict');
const folder=path.join(__dirname,'../device/generated/persistent');
const manifest=JSON.parse(fs.readFileSync(path.join(folder,'manifest.json'),'utf8'));
const files=Object.fromEntries(manifest.files.map(r=>[r.storageName,fs.readFileSync(path.join(folder,r.file),'utf8')]));
files['wand.zero']=JSON.stringify({x:1,y:2,z:3});
const shim=fs.readFileSync(path.join(__dirname,'../../docs/sim/espruino.js'),'utf8');
test('saved payload manifest matches the bytes and fits storage with calibration headroom',()=>{
 let total=0;
 for(const record of manifest.files){
  const data=fs.readFileSync(path.join(folder,record.file));assert.equal(data.length,record.bytes);
  assert.equal(require('node:crypto').createHash('sha256').update(data).digest('hex'),record.sha256);
  let checksum=0;for(const byte of data)checksum=(Math.imul(checksum,31)+byte)>>>0;
  assert.equal(checksum,record.checksum31);total+=data.length+40;
 }
 assert(total+512<=40960,'leave space for the private calibration record and storage overhead');
 assert(!('wand.zero' in Object.fromEntries(manifest.files.map(r=>[r.storageName,r]))));
});
function boot(){
 let now=0,next=0,asleep=false,wakes=0;const timers=new Map(),lines=[];
 const host={now:()=>now,setTimeout:(fn,ms)=>{timers.set(++next,{fn,at:now+ms/1000});return next},setInterval:(fn,ms)=>{timers.set(++next,{fn,at:now+ms/1000,every:ms/1000});return next},clearTimeout:id=>timers.delete(id),clearInterval:id=>timers.delete(id),emit:events=>{for(const e of events)if(e.type==='line')lines.push(e.text)},onError:e=>{throw e}};
 const c=vm.createContext({__host:host});vm.runInContext(shim,c);const device=vm.runInContext('WandEspruino.install(globalThis,__host)',c);
 const original=c.require;
 c.require=name=>name==='Storage'?{read:n=>n==='wand.boot.v4'?c.WandEspruino.prepareFirmware(files[n]+'\nonInit();').replace(/\nonInit\(\);\s*$/,''):files[n],readJSON:n=>files[n]?JSON.parse(files[n]):undefined,write:(n,v)=>{files[n]=v;return true}}:original(name);
 c.NRF.getSecurityStatus=()=>({connected:!!c.connected});
 c.NRF.sleep=()=>{asleep=true;device.disconnect()};c.NRF.wake=()=>{asleep=false;wakes++};
 vm.runInContext(files['.bootcde'],c);
 function advance(seconds){const end=now+seconds;for(;;){const due=[...timers].filter(([,t])=>t.at<=end+1e-9).sort((a,b)=>a[1].at-b[1].at)[0];if(!due)break;const[id,t]=due;now=t.at;if(t.every)t.at+=t.every;else timers.delete(id);t.fn()}now=end}
 return {c,device,lines,advance,get asleep(){return asleep},get wakes(){return wakes}};
}
test('complete flash boot starts from an empty interpreter with calibration and every program part',()=>{
 for(let i=0;i<3;i++){
  const b=boot();assert.equal(b.c.WAND_PERSISTENT_IMAGE,manifest.image);assert.equal(b.c.WAND_POWER_POLICY_VERSION,2);
  assert(b.c.wandState().calibrated);assert.equal(b.c.wandMotionReady,true);assert.equal(b.c.onInit,undefined);
  assert.equal(b.c.wandPowerWatches.length,3);assert(b.c.WAND_BRIDGE_REVISION);
  b.device.connect();assert(b.c.wandState().calibrated);b.device.setPin('D1',0);b.advance(.3);b.device.setPin('D1',1);b.c.setMouseFollow(true);b.advance(.3);
  for(let n=0;n<20;n++){b.advance(.02);b.device.accel({x:50,y:0,z:200})}
  assert(b.lines.some(s=>s.startsWith('@RAW ')),'real saved motion code emits raw pointer data');
  b.device.setPin('D30',0);b.advance(.1);b.device.setPin('D30',1);assert(b.lines.some(s=>s.startsWith('@STT ')));
  b.device.setPin('D2',0);b.advance(.3);b.device.setPin('D2',1);assert(b.lines.some(s=>s.startsWith('@MIDDLE ')));
 }
});
test('saved firmware darkens, deeply sleeps and wakes by button without any Mac upload',()=>{
 const b=boot();b.advance(61);assert.deepEqual(Array.from(b.device.lights()),[0,0,0]);
 b.advance(240);assert(b.asleep);const count=b.wakes;b.device.setPin('D1',0);assert(!b.asleep);assert.equal(b.wakes,count+1);
 b.device.setPin('D1',1);b.device.connect();assert(b.c.wandState().calibrated);
});
