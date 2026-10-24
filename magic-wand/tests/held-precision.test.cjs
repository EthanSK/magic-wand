const fs=require('node:fs');
const assert=require('node:assert/strict');
const {createWand}=require('./harness.cjs');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../device/wand-mode-bridge.js'),'utf8');

function prepare(mode) {
  const w=createWand({bridge:false});
  w.calibrate(); w.device.evaluate(source);
  if(mode==='entry') w.edge('D1',0);
  else {
    w.tap();w.advance(1);
    if(mode==='clutch')w.edge('D1',0);
    if(mode==='drag'){w.tap();w.advance(.05);w.edge('D1',0);}
  }
  w.advance(.3);
  if(mode==='drag')assert(w.ctx.dragging);
  return w;
}
function measure(w,speed) {
  const gyro={x:134*speed,y:0,z:134*speed};
  // Let every mode enter an identical steady motion before counting movement.
  for(let i=0;i<30;i++)w.motion(gyro);
  w.frames.length=0;
  w.ctx.moveX=0;w.ctx.moveY=0;w.ctx.fractionX=0;w.ctx.fractionY=0;
  for(let i=0;i<60;i++)w.motion(gyro);
  w.advance(.05);
  return [0,1].map((axis)=>w.frames.reduce((sum,f)=>sum+f[axis],0));
}
for(const speed of [1.5,8,30,-30]){
  const normal=measure(prepare('follow'),speed);
  assert(normal.every(n=>Math.abs(n)>3),'normal follow produces both axes');
  for(const mode of ['entry','clutch','drag']) {
    const held=prepare(mode);
    const result=measure(held,speed);
    for(let axis=0;axis<2;axis++)assert(Math.abs(result[axis]-normal[axis]/3)<=2,
      `${mode}, ${speed}deg/s, axis${axis}: ${result[axis]} vs ${normal[axis]}/3`);
    held.edge('D1',1);
    assert.equal(held.ctx.moveLatched,mode!=='entry',`${mode} release restores HIGH after LOW or actual dragging`);
    assert(!held.ctx.dragging,`${mode} release does not leave a button held`);
  }
}
// Releasing a short entry tap must restore full follow speed immediately.
const released=prepare('entry');
released.ctx.wandMomentaryStarted=released.now-.06;
released.edge('D1',1);assert(released.ctx.moveLatched);
const full=measure(prepare('follow'),30),restored=measure(released,30);
for(let i=0;i<2;i++)assert(Math.abs(full[i]-restored[i])<=2,'released follow uses full gain');
console.log('PASS: one-third held gain on both axes, fine/medium/fast/reverse motion, all three hold gestures; release restores normal follow and releases dragging.');
