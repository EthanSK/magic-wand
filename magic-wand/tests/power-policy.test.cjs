const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const {createWand}=require('./harness.cjs');
const source=fs.readFileSync(path.join(__dirname,'../device/wand-power-policy.js'),'utf8');
function setup(){
 const w=createWand();w.calibrate();w.loadBridge();const c=w.ctx;
 let asleep=false,wakes=0;
 c.NRF.getSecurityStatus=()=>({connected:c.connected});
 c.NRF.sleep=()=>{asleep=true;w.device.disconnect()};
 c.NRF.wake=()=>{asleep=false;wakes++};
 vm.runInContext(source,c);
 return {w,c,get asleep(){return asleep},get wakes(){return wakes}};
}
test('standby turns off radio, sensors and lights, retaining bias',()=>{
 const x=setup(),{w,c}=x,bias=JSON.stringify(c.bias);
 c.setWandDeskSleeping(true);assert(c.wandEnterDeepStandby());w.advance(.001);
 assert(x.asleep);assert(!c.connected);assert(!w.device.awake);assert.deepEqual(w.colors(),[0,0,0]);
 assert.equal(JSON.stringify(c.bias),bias);assert.equal(c.wandPowerOfflineTimer,undefined);
 w.advance(3600);assert(x.asleep);assert.deepEqual(w.colors(),[0,0,0]);
});
for(const pin of ['D1','D2','D30'])test(`${pin} wakes standby without sending a control action while disconnected`,()=>{
 const x=setup(),{w,c}=x;c.setWandDeskSleeping(true);assert(c.wandEnterDeepStandby());w.advance(.001);
 const before=w.lines.length;w.edge(pin,0);assert.equal(x.wakes,1);assert(!x.asleep);
 assert(!w.lines.slice(before).some(l=>/^@(STT|HUD|WAND|MOVE|BOTTOM)/.test(l)));
 w.edge(pin,1);assert.equal(x.wakes,1);w.device.connect();
 assert.equal(c.wandPowerOfflineTimer,undefined);assert(!c.wandPowerStandby);
 c.restoreWandCalibration({x:1,y:2,z:3});assert(c.wandState().calibrated);
});
test('a held grip refuses standby',()=>{
 for(const pin of ['D1','D2','D30']){const x=setup();x.w.edge(pin,0);assert.equal(x.c.wandEnterDeepStandby(),false);assert(!x.asleep)}

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

// Run the receiver's actual short probe, not a copied condition.
const receiver=fs.readFileSync(path.join(__dirname,'../receiver/Sources/main.swift'),'utf8');
const probe=receiver.match(/queue\("(if\(global\.WAND_POWER_POLICY_VERSION===2[^"\n]*)"\)/)[1];
test('reconnect reuses the existing policy without retransmitting it',()=>{
 const {w,c}=setup();const watches=c.wandPowerWatches.join(',');
 for(let i=0;i<10;i++)vm.runInContext(probe,c);
 assert.equal(c.wandPowerWatches.join(','),watches);
 assert.equal(w.lines.filter(l=>l==='WAND_POWER_POLICY_NEEDED').length,0);
 assert(w.lines.filter(l=>l==='WAND_POWER_POLICY_READY').length>=10);
 vm.runInContext('global.WAND_POWER_POLICY_VERSION=0',c);vm.runInContext(probe,c);
 assert.equal(w.lines.at(-1),'WAND_POWER_POLICY_NEEDED');
});

test('an offline wand enters button-wake standby after five minutes',()=>{
 const x=setup();x.w.device.disconnect();x.w.advance(299.9);assert(!x.asleep);x.w.advance(.2);assert(x.asleep);
 x.w.edge('D2',0);assert(!x.asleep);assert.equal(x.wakes,1);
});
