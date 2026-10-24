const fs=require('node:fs'),assert=require('node:assert/strict');
const {createWand}=require('./harness.cjs');
const source=fs.readFileSync(require('node:path').join(__dirname,'../device/wand-mode-bridge.js'),'utf8');
function fresh(){const w=createWand({bridge:false});w.calibrate();w.device.evaluate(source);return w;}
function turn(w,seconds){for(let i=0;i<Math.round(seconds*w.ctx.CONFIG.sampleRate);i++)w.motion({x:1340,y:0,z:1340});}
const moved=w=>w.frames.some(f=>f[0]||f[1]);

const w=fresh();w.tap();w.advance(.9);
assert(w.ctx.moveLatched,'tap enters HIGH');
w.frames.length=0;w.edge('D1',0);w.advance(.3);turn(w,.2);
assert(moved(w),'plain LOW hold moves');
assert(w.frames.every(f=>f[2]===0),'LOW positioning never selects text');
w.frames.length=0;w.edge('D1',1);
assert(w.ctx.moveLatched,'HIGH remains armed after LOW release');
assert.deepEqual(w.frames.map(f=>f[2]),[1,0],'one complete click on release');
assert(w.frames.every(f=>!f[0]&&!f[1]),'click is stationary');
w.frames.length=0;turn(w,.25);assert(!moved(w),'HIGH stays fixed during the 300 ms pause');
turn(w,.15);assert(moved(w),'HIGH resumes just after 300 ms');

const idle=fresh();idle.edge('D1',0);idle.advance(.3);turn(idle,.2);idle.frames.length=0;idle.edge('D1',1);
assert(!idle.ctx.moveLatched,'LOW from off returns to off');
assert.deepEqual(idle.frames.map(f=>f[2]),[1,0],'LOW from off clicks once');
idle.frames.length=0;turn(idle,1.2);assert(!moved(idle),'no delayed HIGH entry from off');

// A deliberate new gesture overrides the wait; there is no resume timer that
// could later reopen a mode after the user switches or disconnects.
w.frames.length=0;w.edge('D1',0);w.advance(.3);w.edge('D1',1);w.advance(.1);
w.tap();assert(!w.ctx.moveLatched,'single tap during pause exits');
w.advance(1.1);assert(!w.ctx.moveLatched,'no delayed resurrection after exit');
w.tap();w.advance(.9);w.edge('D1',0);w.advance(.3);w.edge('D1',1);
w.tap('D2');w.ctx.setHUDOpen(true);assert(w.ctx.hudOpen&&w.ctx.moveLatched,'HUD leaves HIGH armed');
w.advance(1.1);assert(w.ctx.hudOpen&&w.ctx.moveLatched,'HUD and HIGH remain independent');

const drag=fresh();drag.tap();drag.advance(.9);drag.tap();drag.advance(.05);drag.edge('D1',0);drag.advance(.3);
assert(drag.ctx.dragging,'tap then hold remains a real drag');
drag.edge('D1',1);assert(!drag.ctx.dragging&&drag.ctx.moveLatched,'real drag drops and restores prior HIGH');
drag.frames.length=0;turn(drag,.25);assert(!moved(drag),'real drag has a 300 ms drop pause');
turn(drag,.15);assert(moved(drag),'real drag resumes HIGH after 300 ms');
console.log('PASS: LOW release clicks once, HIGH pauses 300 ms and resumes only when previously active; no selection, delayed mode resurrection, or real-drag regression.');
