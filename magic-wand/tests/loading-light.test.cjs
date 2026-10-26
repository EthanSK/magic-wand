const test=require('node:test'),assert=require('node:assert/strict');
const {createWand}=require('./harness.cjs');
for(const bridge of [false,'readable','fragments']) {
 test(`loading blinks orange without duplicate timers, then stays steady when ready (${bridge||'base'})`,()=>{
  const w=createWand({bridge});w.calibrate();if(bridge)w.loadBridge();const c=w.ctx;
  c.WAND_UPDATING=true;c.updateLights();const seen=[];
  for(let n=0;n<12;n++){seen.push(w.colors());w.advance(.1);}
  assert(seen.some(v=>v.every(x=>x===0)), 'loading has an off phase');
  assert(seen.some(v=>v.every(x=>x===.45)), 'loading uses the established orange LED levels');
  const timers=w.timers.size;for(let n=0;n<8;n++)c.updateLights();assert(w.timers.size<=timers,'repeated updates cannot multiply timers');
  c.WAND_UPDATING=false;c.updateLights();const normal=w.colors();
  for(let n=0;n<12;n++){w.advance(.1);assert.deepEqual(w.colors(),normal,'ready mode must not retain a loading blink');}
 });
}
