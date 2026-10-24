const test=require('node:test');
const assert=require('node:assert/strict');
const {createWand}=require('./harness.cjs');
for(const bridge of ['readable','fragments']) for(const follow of [false,true]) {
 test(`follow change releases device drag (${bridge}, follow=${follow})`,()=>{
  const w=createWand({bridge});w.calibrate();w.loadBridge();
  w.tap();w.advance(.9);w.tap();w.advance(.05);w.edge('D1',0);w.advance(.3);
  assert(w.ctx.dragging);assert.equal(w.frames.at(-1)[2],1);
  w.ctx.setMouseFollow(follow);
  assert.equal(w.frames.at(-1)[2],0,'cancelled drag sends up before forgetting its state');
  assert.equal(w.ctx.sentButtons,0);
  w.edge('D1',1);w.advance(.4);
  w.ctx.moveX=5;w.ctx.pump();
  assert.equal(w.frames.at(-1)[2],0,'later motion cannot replay the old down');
 });
}
