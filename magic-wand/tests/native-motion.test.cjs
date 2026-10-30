const test=require('node:test'),assert=require('node:assert/strict');
const {spawnSync}=require('node:child_process');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {createWand}=require('./harness.cjs');
test('native pointer transport opts in, retains fallback and survives bridge reload',()=>{
 const w=createWand();w.calibrate();w.ctx.wandRawPointer=true;w.loadBridge();w.tap();w.advance(.8);
 w.ctx.wandRawPointer=true;w.frames.length=0;w.lines.length=0;
 for(let i=0;i<30;i++)w.paced(.01,{z:1200,x:-800,y:0});
 assert(w.lines.some(l=>l.startsWith('@ZERO ')));
 assert(w.lines.filter(l=>l.startsWith('@RAW ')).length>=25);
 assert.equal(w.frames.length,0);
 w.ctx.wandRawPointer=false;w.loadBridge();w.paced(.01,{z:1200,x:-800,y:0});
 assert(w.frames.length>0,'legacy receiver retains filtered pointer reports');
 w.ctx.wandRawPointer=true;w.loadBridge();w.frames.length=0;w.lines.length=0;
 for(let i=0;i<10;i++)w.paced(.01,{z:1200,x:-800,y:0});
 assert.equal(w.lines.filter(l=>l.startsWith('@RAW ')).length,10,'reload must leave one sensor listener');
 w.edge('D1',0);w.edge('D2',0);w.lines.length=0;
 for(let i=0;i<20;i++)w.paced(.01,{z:1200,x:-800,y:0});
 assert(!w.lines.some(l=>l.startsWith('@RAW ')),'scroll chord must keep its own route');
});
test('native filter matches actual device math without future samples',{skip:process.platform!=='darwin'},()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'wand-filter-'));
 try{
  const trace=spawnSync(process.execPath,[path.join(__dirname,'motion-trace.cjs')],{encoding:'utf8'});
  assert.equal(trace.status,0,trace.stderr);fs.writeFileSync(path.join(dir,'trace.json'),trace.stdout);
  fs.copyFileSync(path.join(__dirname,'native-motion-main.swift'),path.join(dir,'main.swift'));
  const build=spawnSync('swiftc',['-O',path.join(__dirname,'../receiver/Sources/WandPointerControl.swift'),path.join(dir,'main.swift'),'-o',path.join(dir,'test')],{encoding:'utf8'});
  assert.equal(build.status,0,build.stderr);
  const run=spawnSync(path.join(dir,'test'),[path.join(dir,'trace.json')],{encoding:'utf8'});
  assert.equal(run.status,0,run.stdout+run.stderr);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});

test('native upload frees the old callback in an earlier complete statement',()=>{
 const {read}=require('./harness.cjs');
 const lines=read('device/generated/wand-mode-bridge.compact.js').split('\n');
 const free=lines.findIndex(l=>l.includes('delete global.wandPointerSlack'));
 const replacement=lines.findIndex(l=>l.includes("Bluetooth.println('@RAW "));
 assert(free>=0 && replacement>free,'free old function before parsing its replacement');
 assert(!lines[free].includes("Bluetooth.println('@RAW "));
});

test('HUD-only raw motion is available without enabling the mouse',()=>{
 const w=createWand();w.calibrate();w.ctx.wandRawPointer=true;w.loadBridge();
 w.ctx.setMouseFollow(false);w.ctx.setHUDOpen(true);w.advance(.3);w.lines.length=0;w.frames.length=0;
 for(let i=0;i<30;i++)w.paced(.01,{z:1200,x:-800,y:0});
 const raw=w.lines.filter(l=>l.startsWith('@RAW '));assert(raw.length>=25);
 assert(raw.every(l=>(Number(l.split(',').at(-1))&4)!==0));assert.equal(w.ctx.wandState().move,false);
 assert(!w.lines.some(l=>l.startsWith('@WAND ')&&!l.includes('@WAND 0,0,0')));
});
