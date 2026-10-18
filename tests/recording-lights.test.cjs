const test=require('node:test'),assert=require('node:assert/strict');
const {createWand}=require('./harness.cjs');
test('recording in mouse mode alternates blue/red and cancels cleanly on mode change',()=>{
 const w=createWand({bridge:'fragments'});w.calibrate();w.loadBridge();const c=w.ctx;
 Object.assign(c,{connected:true,WAND_UPDATING:false,wandMotionReady:true,calibrationLit:false,moveLatched:true,hudOpen:false,scrollHeld:false,wandRecording:true});c.updateLights();
 assert.deepEqual(w.colors(),[0,0,1]);w.advance(.36);assert.deepEqual(w.colors(),[1,0,0]);w.advance(.35);assert.deepEqual(w.colors(),[0,0,1]);
 c.wandRecording=false;c.updateLights();w.advance(.4);assert.deepEqual(w.colors(),[0,0,1]);assert.equal(c.wandRecordingBlinkTimer,undefined);
 c.moveLatched=false;c.wandRecording=true;c.updateLights();w.advance(.4);assert.deepEqual(w.colors(),[1,0,0]);assert.equal(c.wandRecordingBlinkTimer,undefined);
 c.hudOpen=true;c.updateLights();assert.deepEqual(w.colors(),[1,.2,0]);
 c.hudOpen=false;c.moveLatched=true;c.updateLights();c.connected=false;c.updateLights();assert.equal(c.wandRecordingBlinkTimer,undefined);
});
