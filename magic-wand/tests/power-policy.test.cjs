const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const {createWand}=require('./harness.cjs');
const source=fs.readFileSync(path.join(__dirname,'../device/wand-power-policy.js'),'utf8');
const version=Number(source.match(/WAND_POWER_POLICY_VERSION!==(\d+)/)[1]);
const PINS=['D1','D2','D30'],ENTERED='WAND_POWER_STANDBY_ENTERED',CANCELLED='WAND_POWER_STANDBY_CANCELLED';
function setup(){
 const w=createWand();w.calibrate();w.loadBridge();const c=w.ctx;
 let asleep=false,wakes=0,sleeps=0;
 c.NRF.getSecurityStatus=()=>({connected:c.connected});
 // Real NRF.sleep only disconnects a live connection.
 c.NRF.sleep=()=>{asleep=true;sleeps++;if(c.connected)w.device.disconnect()};
 c.NRF.wake=()=>{asleep=false;wakes++};
 vm.runInContext(source,c);
 const count=text=>w.lines.filter(l=>l===text).length;
 return {w,c,count,get asleep(){return asleep},get wakes(){return wakes},get sleeps(){return sleeps}};
}
// The full warning: on, off, on, off at 100 ms each, then standby.
function sleepNow(x){x.c.setWandDeskSleeping(true);assert(x.c.wandEnterDeepStandby());x.w.advance(.401);assert(x.asleep)}
function idle(c){assert.equal(c.wandPowerWarnPhase,undefined);assert.equal(c.wandPowerWarnTimer,undefined)}
test('standby first flashes all three lights twice, then turns off radio, sensors and lights, retaining bias',()=>{
 const x=setup(),{w,c}=x,bias=JSON.stringify(c.bias);
 c.setWandDeskSleeping(true);assert.deepEqual(w.colors(),[0,0,0]);assert(c.wandEnterDeepStandby());
 const seen=[];for(let i=0;i<4;i++){seen.push(w.colors());assert(!x.asleep);assert(c.connected);assert.equal(x.count(ENTERED),0);w.advance(.1)}
 assert.deepEqual(seen,[[1,1,1],[0,0,0],[1,1,1],[0,0,0]]);
 assert(x.asleep);assert.equal(x.sleeps,1);assert.equal(x.count(ENTERED),1);assert.equal(x.count(CANCELLED),0);assert.equal(c.wandPowerSleeps,1);
 assert(!c.connected);assert(!w.device.awake);assert.deepEqual(w.colors(),[0,0,0]);idle(c);assert(c.wandPowerStandby);
 assert.equal(JSON.stringify(c.bias),bias);assert.equal(c.wandPowerOfflineTimer,undefined);assert.equal(c.wandPowerOfflineDeepTimer,undefined);
 w.advance(3600);assert(x.asleep);assert.equal(x.sleeps,1);assert.deepEqual(w.colors(),[0,0,0]);
});
for(const pin of PINS)test(`${pin} wakes standby without sending a control action while disconnected`,()=>{
 const x=setup(),{w,c}=x;sleepNow(x);
 const before=w.lines.length;w.edge(pin,0);assert.equal(x.wakes,1);assert(!x.asleep);
 assert(!w.lines.slice(before).some(l=>/^@(STT|HUD|WAND|MOVE|BOTTOM)/.test(l)));assert.equal(x.count(CANCELLED),0);
 w.edge(pin,1);assert.equal(x.wakes,1);w.device.connect();
 assert.equal(c.wandPowerOfflineTimer,undefined);assert(!c.wandPowerStandby);idle(c);
 c.restoreWandCalibration({x:1,y:2,z:3});assert(c.wandState().calibrated);
 w.advance(3600);assert(!x.asleep);assert.equal(x.sleeps,1);
});
for(const pin of PINS)test(`${pin} cancels the warning at once, during a flash or a gap, and never sleeps later`,()=>{
 for(const at of [.05,.15,.35]){
  const x=setup(),{w,c}=x;c.setWandDeskSleeping(true);assert(c.wandEnterDeepStandby());w.advance(at);
  w.edge(pin,0);idle(c);assert.equal(x.count(CANCELLED),1);assert.equal(x.count(ENTERED),0);
  // The bridge's own light state is restored, not a leftover flash.
  const lit=w.colors();c.updateLights();assert.deepEqual(w.colors(),lit);
  w.advance(1);w.edge(pin,1);w.advance(3600);
  assert(!x.asleep);assert.equal(x.sleeps,0);assert(c.connected);assert(!c.wandPowerStandby);assert.equal(x.count(ENTERED),0);
  // A later request is a fresh, complete warning.
  sleepNow(x);assert.equal(x.sleeps,1);assert.equal(x.count(ENTERED),1);assert.equal(x.count(CANCELLED),1);
 }
});
test('a grip already down at a flash step cancels before its debounced watch arrives',()=>{
 const x=setup(),{w,c}=x;assert(c.wandEnterDeepStandby());const read=c.digitalRead;
 c.digitalRead=p=>p==='D30'?0:read(p);w.advance(.1);c.digitalRead=read;
 idle(c);assert.equal(x.count(CANCELLED),1);w.advance(10);assert(!x.asleep);assert.equal(x.count(ENTERED),0);
});
test('a held grip refuses standby without flashing',()=>{
 for(const pin of PINS){const x=setup();x.w.edge(pin,0);const lit=x.w.colors();assert.equal(x.c.wandEnterDeepStandby(),false);
  idle(x.c);assert.deepEqual(x.w.colors(),lit);x.w.advance(1);assert(!x.asleep);assert.equal(x.count(CANCELLED),0)}
});
test('repeated requests neither restart nor duplicate the warning or the sleep',()=>{
 const x=setup(),{w,c}=x;c.setWandDeskSleeping(true);assert(c.wandEnterDeepStandby());
 w.advance(.15);assert(c.wandEnterDeepStandby());assert.deepEqual(w.colors(),[0,0,0],'still in the first gap');
 w.advance(.1);assert(c.wandEnterDeepStandby());assert.deepEqual(w.colors(),[1,1,1]);
 w.advance(.151);assert(x.asleep,'sleeps on the original schedule');assert.equal(x.sleeps,1);
 assert(c.wandEnterDeepStandby());w.advance(1);assert.equal(x.sleeps,1);assert.equal(x.count(ENTERED),1);assert.deepEqual(w.colors(),[0,0,0]);
});
test('a disconnect during the warning still sleeps once and leaves no offline timers',()=>{
 const x=setup(),{w,c}=x;c.setWandDeskSleeping(true);assert(c.wandEnterDeepStandby());
 w.advance(.15);w.device.disconnect();assert(!c.connected);assert.notEqual(c.wandPowerOfflineDeepTimer,undefined);
 w.advance(.251);assert(x.asleep);assert.equal(x.sleeps,1);idle(c);
 assert.equal(c.wandPowerOfflineTimer,undefined);assert.equal(c.wandPowerOfflineDeepTimer,undefined);
 w.advance(3600);assert(x.asleep);assert.equal(x.sleeps,1);assert.deepEqual(w.colors(),[0,0,0]);
 w.edge('D1',0);assert(!x.asleep);w.edge('D1',1);w.device.connect();w.advance(3600);assert(!x.asleep);assert.equal(x.sleeps,1);
});
test('a Mac connecting during an offline warning cancels it',()=>{
 const x=setup(),{w,c}=x;w.device.disconnect();w.advance(300.05);assert(!x.asleep);assert.deepEqual(w.colors(),[1,1,1]);
 w.device.connect();idle(c);assert.equal(x.count(CANCELLED),1);
 w.advance(3600);assert(!x.asleep);assert.equal(x.sleeps,0);assert.equal(x.count(ENTERED),0);
});
test('unexpected disconnect goes dark after one minute, including interrupted update',()=>{
 const {w,c}=setup();c.WAND_UPDATING=true;w.device.disconnect();
 w.advance(59.9);assert(w.colors().some(Boolean));w.advance(.2);assert.deepEqual(w.colors(),[0,0,0]);
 assert(!w.device.awake);assert.equal(c.wandPowerOfflineTimer,undefined);
});
test('reconnecting cancels offline darkness and a reload does not add duplicate watches',()=>{
 const {w,c}=setup();const watches=c.wandPowerWatches.join(',');
 vm.runInContext(source,c);assert.equal(c.wandPowerWatches.join(','),watches);
 w.device.disconnect();w.advance(30);w.device.connect();assert.equal(c.wandPowerOfflineTimer,undefined);
 w.advance(31);assert(!c.wandPowerStandby);
});
test('upgrading a running older policy replaces its watches and Bluetooth listeners',()=>{
 const x=setup(),{w,c}=x,sizes=()=>[c.NRF['#onconnect'],c.NRF['#ondisconnect']].map(l=>[].concat(l).length);
 const watches=w.device.watchCount(),listeners=sizes(),old=c.wandPowerWatches.join(',');
 vm.runInContext('global.WAND_POWER_POLICY_VERSION=2',c);vm.runInContext(source,c);
 assert.equal(c.WAND_POWER_POLICY_VERSION,version);assert.equal(w.device.watchCount(),watches);assert.deepEqual(sizes(),listeners);
 assert.notEqual(c.wandPowerWatches.join(','),old);sleepNow(x);assert.equal(x.sleeps,1);
 w.edge('D2',0);assert(!x.asleep);assert.equal(x.wakes,1);
});

// Run the receiver's actual short probe, not a copied condition.
const receiver=fs.readFileSync(path.join(__dirname,'../receiver/Sources/main.swift'),'utf8');
const probe=receiver.match(/queue\("(if\(global\.WAND_POWER_POLICY_VERSION===\d+[^"\n]*)"\)/)[1];
test('the receiver probes for the device policy version',()=>{
 assert.equal(Number(probe.match(/VERSION===(\d+)/)[1]),version);
});
test('reconnect reuses the existing policy without retransmitting it',()=>{
 const {w,c}=setup();const watches=c.wandPowerWatches.join(',');
 for(let i=0;i<10;i++)vm.runInContext(probe,c);
 assert.equal(c.wandPowerWatches.join(','),watches);
 assert.equal(w.lines.filter(l=>l==='WAND_POWER_POLICY_NEEDED').length,0);
 assert(w.lines.filter(l=>l==='WAND_POWER_POLICY_READY').length>=10);
 vm.runInContext('global.WAND_POWER_POLICY_VERSION=0',c);vm.runInContext(probe,c);
 assert.equal(w.lines.at(-1),'WAND_POWER_POLICY_NEEDED');
});

test('an offline wand flashes, then enters button-wake standby after five minutes',()=>{
 const x=setup();x.w.device.disconnect();x.w.advance(299.9);assert(!x.asleep);
 x.w.advance(.15);assert(!x.asleep);assert.deepEqual(x.w.colors(),[1,1,1]);x.w.advance(.351);assert(x.asleep);assert.equal(x.sleeps,1);
 x.w.edge('D2',0);assert(!x.asleep);assert.equal(x.wakes,1);
});

test('all-three chord toggles manual standby once and suppresses individual controls',()=>{
 const x=setup(),{w,c}=x,read=c.digitalRead;let level=0;
 c.digitalRead=p=>PINS.includes(p)?level:read(p);
 const start=w.lines.length;
 for(const pin of PINS)w.edge(pin,0);
 w.advance(.401);assert(x.asleep);assert.equal(x.sleeps,1);
 assert(!w.lines.slice(start).some(l=>/^@(STT|MIDDLE|BOTTOM|SCROLL)/.test(l)));
 level=1;for(const pin of PINS)w.edge(pin,1);
 assert(x.asleep);assert(!c.wandChord);
 c.digitalRead=read;
 w.edge('D1',0);w.edge('D1',1);assert(x.asleep,'one button does not wake manually-off wand');
 level=0;c.digitalRead=p=>PINS.includes(p)?level:read(p);
 for(const pin of PINS)w.edge(pin,0);
 assert(!x.asleep);assert.equal(x.wakes,1);assert(!c.wandPowerManual);
 level=1;for(const pin of PINS)w.edge(pin,1);
 c.digitalRead=read;w.device.connect();w.tap('D1');assert(c.wandState().move);
});

test('an all-three chord wakes automatic sleep without immediately sleeping again',()=>{
 const x=setup(),{w,c}=x;sleepNow(x);const read=c.digitalRead;let level=0;
 c.digitalRead=p=>PINS.includes(p)?level:read(p);
 for(const pin of PINS)w.edge(pin,0);
 w.advance(1);assert(!x.asleep);assert.equal(x.wakes,1);assert.equal(x.sleeps,1);
 level=1;for(const pin of PINS)w.edge(pin,1);assert(!c.wandChord);
});
