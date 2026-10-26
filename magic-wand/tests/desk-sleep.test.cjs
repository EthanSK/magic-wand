const test=require('node:test'),assert=require('node:assert/strict');
const {createWand}=require('./harness.cjs');
for(const bridge of ['readable','fragments']) {
 test(`desk sleep darkens all modes, keeps pickup sensing and restores lights (${bridge})`,()=>{
  const w=createWand({bridge});w.calibrate();w.loadBridge();const c=w.ctx;
  c.WAND_UPDATING=false;c.wandMotionReady=true;
  c.setMouseFollow(true);c.setHUDOpen(true);c.setWandReviewTracking(true);c.setWandRecording(true);
  c.setWandDeskSleeping(true);assert.equal(c.hudTimer,undefined);assert(c.wandDeskSleeping);assert(!c.gyroAwake);
  assert.deepEqual(w.colors(),[0,0,0]);assert.equal(w.device.sampleRate,1.6);
  assert(c.moveLatched);assert(c.hudOpen);assert(c.wandReviewTracking);assert(c.wandRecording);
  // Background HUD updates must not wake a parked wand or light it up.
  c.setHUDOpen(true);c.updateLights();w.advance(3);assert.deepEqual(w.colors(),[0,0,0]);assert(!c.gyroAwake);
  c.setWandDeskSleeping(false);assert.notEqual(c.hudTimer,undefined);assert(c.gyroAwake);assert.deepEqual(w.colors(),[1,0,0],'waking while recording shows red, not mouse blue');
  c.setMouseFollow(false);c.setHUDOpen(false);c.setWandReviewTracking(false);
  c.setWandDeskSleeping(true);assert.deepEqual(w.colors(),[0,0,0]);
  c.setWandDeskSleeping(false);assert(c.wandRecording);assert.deepEqual(w.colors(),[1,0,0]);
 });
 test(`physical button wakes sleeping wand and update state stays visible (${bridge})`,()=>{
  const w=createWand({bridge});w.calibrate();w.loadBridge();const c=w.ctx;
  c.WAND_UPDATING=false;c.wandMotionReady=true;c.setWandDeskSleeping(true);
  w.edge('D1',0);assert(!c.wandDeskSleeping);c.setWandDeskSleeping(true);assert(!c.wandDeskSleeping,'never sleep while a grip switch is held');
  w.edge('D1',1);w.advance(.5);c.setWandDeskSleeping(true);
  c.WAND_UPDATING=true;c.updateLights();assert.deepEqual(w.colors(),[.45,.45,.45]);
  c.WAND_UPDATING=false;c.updateLights();assert.deepEqual(w.colors(),[0,0,0]);
 });
}
