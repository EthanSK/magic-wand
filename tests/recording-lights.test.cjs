const test=require('node:test'),assert=require('node:assert/strict');
const {createWand}=require('./harness.cjs');
test('recording never flashes mouse blue, cancels legacy timers and preserves mode priority',()=>{
 const w=createWand({bridge:'fragments'});w.calibrate();const c=w.ctx;c.wandRecordingBlinkTimer=c.setInterval(()=>{c.wandRecordingBlinkRed=true;},350);w.loadBridge();assert.equal(c.wandRecordingBlinkTimer,undefined);
 Object.assign(c,{connected:true,WAND_UPDATING:false,wandMotionReady:true,calibrationLit:false,moveLatched:true,hudOpen:false,scrollHeld:false,wandRecording:true});c.updateLights();
 assert.deepEqual(w.colors(),[0,0,1]);w.advance(.36);assert.deepEqual(w.colors(),[0,0,1]);w.advance(.35);assert.deepEqual(w.colors(),[0,0,1]);
 c.wandRecording=false;c.updateLights();w.advance(.4);assert.deepEqual(w.colors(),[0,0,1]);assert.equal(c.wandRecordingBlinkTimer,undefined);
 c.moveLatched=false;c.wandRecording=true;c.updateLights();w.advance(.4);assert.deepEqual(w.colors(),[1,0,0]);assert.equal(c.wandRecordingBlinkTimer,undefined);
 c.hudOpen=true;c.updateLights();assert.deepEqual(w.colors(),[1,.2,0]);
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
