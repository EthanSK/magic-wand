// Cross-language reference: run the actual accepted Puck filter at exact sample
// intervals, then compare the Mac implementation against its output.
const {createWand}=require('./harness.cjs');
const w=createWand();w.calibrate();w.loadBridge();w.ctx.wandBridgeOriginalSend=w.ctx.mouse.send;
w.tap();w.advance(.8);
const rows=[];let seed=1234567;
for(let i=0;i<2400;i++){
 const reset=i%200===0,held=Math.floor(i/200)%2===1;
 if(reset){
  w.ctx.wandSlackX=w.ctx.wandSlackY=w.ctx.fractionX=w.ctx.fractionY=w.ctx.filteredX=w.ctx.filteredY=0;
  w.edge('D1',held?0:1);w.advance(.31);
  w.ctx.moveLatched=true;w.ctx.moveGestureMode=undefined;w.ctx.dragging=false;w.ctx.tapPending=false;
  w.ctx.wandPointerPauseUntil=0;w.ctx.wandSettleUntil=0;w.ctx.wandMotionReadyAt=0;
  w.ctx.wandSlackX=w.ctx.wandSlackY=w.ctx.fractionX=w.ctx.fractionY=w.ctx.filteredX=w.ctx.filteredY=0;
 }
 seed=(Math.imul(seed,1664525)+1013904223)>>>0;
 const us=[9615,10000,15000,25000,50000][i%5];
 const mag=i%200<60?.3:i%200<100?.6:i%200<160?4:80;
 const x=Math.round(Math.cos(i*.061)*mag*134),y=Math.round(Math.sin(i*.061)*mag*134);
 w.ctx.lastTime=w.now;w.frames.length=0;
 w.paced(us/1e6,{z:x,x:y,y:0});
 rows.push([us,x,y,held?1:0,reset?1:0,w.frames.reduce((n,f)=>n+f[0],0),w.frames.reduce((n,f)=>n+f[1],0),w.ctx.wandIntentActive?1:0]);
}
process.stdout.write(JSON.stringify(rows));
