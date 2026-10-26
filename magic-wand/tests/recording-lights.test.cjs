const test=require('node:test'),assert=require('node:assert/strict');
const {createWand}=require('./harness.cjs');
test('recording red replaces mouse blue steadily, cancels legacy timers and preserves other priorities',()=>{
 const w=createWand({bridge:'fragments'});w.calibrate();const c=w.ctx;c.wandRecordingBlinkTimer=c.setInterval(()=>{c.wandRecordingBlinkRed=true;},350);w.loadBridge();assert.equal(c.wandRecordingBlinkTimer,undefined);
 Object.assign(c,{connected:true,WAND_UPDATING:false,wandMotionReady:true,calibrationLit:false,moveLatched:true,hudOpen:false,scrollHeld:false,wandRecording:true});c.updateLights();
 assert.deepEqual(w.colors(),[1,0,0]);w.advance(.36);assert.deepEqual(w.colors(),[1,0,0]);w.advance(.35);assert.deepEqual(w.colors(),[1,0,0]);
 c.wandRecording=false;c.updateLights();w.advance(.4);assert.deepEqual(w.colors(),[0,0,1]);assert.equal(c.wandRecordingBlinkTimer,undefined);
 c.moveLatched=false;c.wandRecording=true;c.updateLights();w.advance(.4);assert.deepEqual(w.colors(),[1,0,0]);assert.equal(c.wandRecordingBlinkTimer,undefined);
 c.hudOpen=true;c.updateLights();assert.deepEqual(w.colors(),[1,.2,0]);
 c.moveLatched=true;c.updateLights();assert.deepEqual(w.colors(),[1,0,0],'recording with mouse and HUD is red');c.moveLatched=false;
 c.scrollHeld=true;c.updateLights();assert.deepEqual(w.colors(),[0,1,1],'scroll keeps priority');c.scrollHeld=false;
 c.hudOpen=false;c.moveLatched=true;c.updateLights();c.connected=false;c.updateLights();assert.equal(c.wandRecordingBlinkTimer,undefined);
});
test('red is exclusive to recording; unavailable and calibration states use orange',()=>{
 const w=createWand({bridge:'readable'});w.calibrate();w.loadBridge();const c=w.ctx;
 Object.assign(c,{connected:true,WAND_UPDATING:false,wandMotionReady:true,calibrationLit:false,moveLatched:false,hudOpen:false,scrollHeld:false,wandRecording:false});
 for(const [key,value] of [['WAND_UPDATING',true],['calibrationLit',true],['connected',false],['wandMotionReady',false]]) {
  const previous=c[key];c[key]=value;c.updateLights();assert.deepEqual(w.colors(),[.45,.45,.45],key);c[key]=previous;
 }
 c.updateLights();assert.deepEqual(w.colors(),[0,0,0]);c.wandRecording=true;c.updateLights();assert.deepEqual(w.colors(),[1,0,0]);
});

test('review keeps gyro telemetry alive without owning mouse or speech',()=>{
 const w=createWand({bridge:'readable'});w.calibrate();w.loadBridge();const c=w.ctx;
 c.setMouseFollow(false);c.setWandReviewTracking(true);w.advance(1.2);
 assert(c.gyroAwake);assert(!c.moveLatched);assert(!c.hudOpen);
 w.lines.length=0;for(let i=0;i<20;i++)w.motion({x:1340,y:0,z:1340});
 assert(w.lines.some(x=>x.startsWith('@NAV ')));
 c.setMouseFollow(true);c.setHUDOpen(true);assert(c.moveLatched);
 c.setHUDOpen(false);assert(c.moveLatched);assert(c.wandReviewTracking);
 c.setWandRecording(true);assert(c.moveLatched);assert(c.wandReviewTracking);
 c.setWandReviewTracking(false);assert(c.moveLatched);assert(c.wandRecording);
});
