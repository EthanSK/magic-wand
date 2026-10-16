const fs=require('node:fs'),assert=require('node:assert/strict');
const {createWand}=require('./harness.cjs');
const source=fs.readFileSync(require('node:path').join(__dirname,'../device/wand-mode-bridge.js'),'utf8');
function fresh(low=false){
 const w=createWand({bridge:false});w.calibrate();w.device.evaluate(source);
 w.tap();w.advance(.9);if(low){w.edge('D1',0);w.advance(.3);}w.advance(.12);
 rate(w,0,0,.2);w.frames.length=0;return w;
}
const counts=w=>[0,1].map(a=>w.frames.reduce((s,f)=>s+f[a],0));
const moving=w=>w.frames.filter(f=>f[0]||f[1]);
function rate(w,x,y,seconds,hz=104){for(let i=0;i<Math.round(seconds*hz);i++)w.paced(1/hz,{z:x*134,x:y*134,y:0});}
function tremor(w,seconds,hz){
 let px=0,py=0;const dt=1/hz;
 for(let i=1;i<=Math.round(seconds*hz);i++){
  const t=i*dt,x=.08*Math.sin(2*Math.PI*10*t)+.02*Math.sin(2*Math.PI*17*t),y=.07*Math.sin(2*Math.PI*8*t);
  w.paced(dt,{z:(x-px)/dt*134,x:(y-py)/dt*134,y:0});px=x;py=y;
 }
}
for(const low of [false,true])for(const hz of [35,104]){
 const w=fresh(low);tremor(w,3,hz);
 assert.equal(moving(w).length,0,`tremor locked low=${low}, hz=${hz}`);
 assert.equal(w.ctx.fractionX,0);assert.equal(w.ctx.fractionY,0);
 rate(w,0,0,1,hz);w.frames.length=0;rate(w,10,0,.3,hz);
 const after=counts(w),clean=fresh(low);rate(clean,10,0,.3,hz);
 assert(Math.abs(after[0]-counts(clean)[0])<=1,'rejected wobble is never replayed');
 const drift=fresh(low);rate(drift,.3,.3,5,hz);
 assert.equal(moving(drift).length,0,'quiet residual drift is rejected from rest');
 rate(drift,30,0,.3,hz);rate(drift,0,0,.2,hz);drift.frames.length=0;
 rate(drift,.3,.3,3,hz);
 assert.equal(moving(drift).length,0,'drift cannot keep pushing after a sweep');
 const slow=fresh(low);rate(slow,1.5,0,1,hz);assert(Math.abs(counts(slow)[0])>3,'intentional slow move escapes');
 const small=fresh(low);rate(small,3,0,.5/3,hz);assert(Math.abs(counts(small)[0])>=2,'small deliberate movement is retained');
 const diagonal=fresh(low);rate(diagonal,6,3,1,hz);const [x,y]=counts(diagonal);
 assert(x&&y&&Math.abs(Math.abs(y/x)-.7)<.07,'shallow diagonals preserve axis ratio');
 const reverse=fresh(low);rate(reverse,10,0,.1,hz);rate(reverse,0,0,.8,hz);rate(reverse,-10,0,.1,hz);
 assert(Math.abs(counts(reverse)[0])<=3,'paused reversal stays balanced');
 const circle=fresh(low);let cx=3,cy=0;
 for(let i=1;i<=hz*2;i++){
  const angle=i/(hz*2)*2*Math.PI,nx=3*Math.cos(angle),ny=3*Math.sin(angle);
  circle.paced(1/hz,{z:(nx-cx)*hz*134,x:(ny-cy)*hz*134,y:0});cx=nx;cy=ny;
 }
 for(const axis of [0,1]){
  assert(circle.frames.some(f=>f[axis]>0)&&circle.frames.some(f=>f[axis]<0),'curves retain both directions on each axis');
  assert(Math.abs(counts(circle)[axis])<=(low?8:25),'closed curve stays within angular-tolerance displacement');
 }
 circle.ctx.restoreWandCalibration({x:0,y:0,z:0});
 assert.equal(circle.ctx.wandSlackX,0);assert.equal(circle.ctx.wandSlackY,0);
 assert.equal(circle.ctx.fractionX,0);assert.equal(circle.ctx.fractionY,0);
}
const frozen=fresh();frozen.edge('D1',0);frozen.advance(.3);rate(frozen,20,0,.2);frozen.edge('D1',1);frozen.frames.length=0;
tremor(frozen,.25,35);assert.equal(moving(frozen).length,0,'release click freeze rejects jitter');
rate(frozen,0,0,.2);tremor(frozen,2,35);assert.equal(moving(frozen).length,0,'HIGH resume stays still until intentional movement');
rate(frozen,10,0,.3);assert(moving(frozen).length>0,'HIGH intentional movement resumes');
console.log('PASS: radial tremor/drift rejection at 35/104Hz in HIGH/LOW, no noise replay, drift after sweep, slow/fine aiming, diagonals, reversal and 300 ms release freeze.');
