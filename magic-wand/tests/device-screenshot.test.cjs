// Ethan's screenshot mode on the wand: the receiver's exact REPL commands give
// HIGH raw motion with mouse follow off and take the mouse button away from the legacy
// follow/click callback, while every edge is still reported. Readable and
// fragment-loaded bridges both run the same checks.
const test=require('node:test'),assert=require('node:assert/strict');
const {createWand}=require('./harness.cjs');
const ENTER='global.wandShot=1;setMouseFollow(moveLatched);wakeGyro();';
const EXIT='global.wandShot=0;sleepGyro();';
const turn={x:0,y:0,z:-1340};
for(const bridge of ['readable','fragments']) {
 test(`screenshot motion and the mouse button ownership leave follow untouched (${bridge})`,()=>{
  const w=createWand({bridge});w.calibrate();w.ctx.wandRawPointer=true;w.loadBridge();const c=w.ctx;
  c.setMouseFollow(false);w.advance(1.2);assert(!c.gyroAwake);
  w.device.evaluate(ENTER);w.advance(0.2);w.lines.length=0;w.frames.length=0;
  for(let i=0;i<10;i++)w.paced(0.01,turn);
  const raw=w.lines.filter(l=>l.startsWith('@RAW '));
  assert(raw.length>=8,'screenshot mode streams raw motion with follow off');
  assert(raw.every(l=>(+l.split(',')[3]&4)===4),'follow-off flag stays set; the receiver owns the meaning');
  assert(!c.moveLatched,'entering never turns ordinary mouse mode on');
  w.lines.length=0;w.tap();w.advance(0.4);w.edge('D1',0);w.advance(0.5);w.edge('D1',1);w.advance(0.4);
  assert.deepEqual(w.lines.filter(l=>l.startsWith('@BOTTOM ')),['@BOTTOM 1','@BOTTOM 0','@BOTTOM 1','@BOTTOM 0'],'every Bottom edge is still reported');
  assert(!c.moveLatched && !c.dragging && c.moveGestureMode===undefined,'taps and holds never toggle follow or start a device drag');
  assert(!w.frames.some(f=>f[2]!==0),'no legacy click or drag frame');
  assert(!w.lines.some(l=>l==='@FOLLOW 1'),'no follow report');
  c.setHUDOpen(true);c.setHUDOpen(false);w.advance(1.2);
  assert(c.gyroAwake,'closing the HUD cannot power down screenshot motion');
  w.edge('D1',0);w.device.evaluate(EXIT);w.edge('D1',1);w.advance(1.2);
  assert(!c.moveLatched && !w.frames.some(f=>f[2]!==0),'a press held across exit releases without a legacy toggle or click');
  assert(!c.gyroAwake,'exit with follow off returns to low-power sensing');
  w.lines.length=0;for(let i=0;i<5;i++)w.paced(0.01,turn);
  assert(!w.lines.some(l=>l.startsWith('@RAW ')),'no motion after exit');
  w.tap();assert(c.moveLatched,'ordinary mouse button behaviour returns after exit');
 });
 test(`triple-click start restores the pre-click follow choice (${bridge})`,()=>{
  for(const before of [false,true]) {
   const w=createWand({bridge});w.calibrate();w.ctx.wandRawPointer=true;w.loadBridge();const c=w.ctx;
   c.setMouseFollow(before);w.advance(1.2);w.frames.length=0;
   w.tap();w.advance(0.1);w.tap();w.advance(0.1);w.edge('D1',0);
   w.device.evaluate('global.wandShot=1;setMouseFollow('+before+');wakeGyro();');
   w.advance(0.4);w.edge('D1',1);w.advance(0.4);
   assert.equal(c.moveLatched,before,'follow returns to the choice before the three clicks');
   assert(!c.dragging && !w.frames.some(f=>f[2]!==0),'the held third press never becomes a device drag or click');
   w.device.evaluate(EXIT);w.advance(1.2);assert.equal(c.moveLatched,before);assert.equal(c.gyroAwake,before);
  }
 });
}
