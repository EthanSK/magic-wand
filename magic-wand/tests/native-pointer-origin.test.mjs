import {fileURLToPath as wandSourcePath} from 'node:url';
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';

// Ethan, 2026-10-30: "it's jumping back to its original position way more
// now". A captured posted-cursor trace showed rapid separate receiveText
// batches reading the system cursor before the wand's own earlier moves had
// landed: 2103,746 -> 2113,737 -> 2134,719, then a +9,-8 move landing at
// 2112,738 (the stale 2103,746 plus +9,-8). The receiver's real origin and
// posting methods run here against an inert event stub; nothing is posted.
test('separate rapid batches continue from the wand\'s own last move, never a stale cursor',{skip:process.platform!=='darwin'},()=>{
 const source=readFileSync(new URL('../receiver/Sources/main.swift',import.meta.url),'utf8');
 function method(name){const a=source.indexOf('    func '+name+'(');assert(a>=0,name);let b=source.indexOf('{',a)+1,depth=1;while(depth){if(source[b]==='{')depth++;if(source[b]==='}')depth--;b++;}return source.slice(a,b);}
 const receive=method('receiveText');
 assert(receive.includes('deliveryPoint=currentPointerOrigin()'),'each batch starts from the tracked origin');
 assert.equal(source.split('CGEvent(source:nil)?.location').length-1,1,'only the origin helper reads the system cursor');
 assert(!/CGEvent\(source: nil\)\?\.location/.test(source),'no other spelling bypasses the helper');
 assert(method('postPointerMove').includes('pointerOrigin.moved(from:point,to:newPoint'),'every posted move is remembered');
 assert(method('recenterPointer').includes('pointerOrigin.begin(at:point'),'a recenter still wins until macOS reports it');
 const code=`import Foundation
func log(_ v:Any...) {}
enum Tap {case cghidEventTap}
final class Posted {let to:CGPoint;init(to:CGPoint){self.to=to};func post(tap:Tap){Harness.landed.append(to)}}
final class CGEvent {static var system=CGPoint.zero;var location:CGPoint {CGEvent.system};init?(source:Int?){}}
final class Harness {
 static var landed:[CGPoint]=[]
 var actionPause=WandActionPause();let screenshot=WandScreenshotGesture()
 var recordingPointerPaused=false,hudSession=false,middleHeld=false,hudEntryPress=false,pointerInHUD=false
 var buttons=0,pointerTravel=0.0,movementCount=0,pointerDisplays=[CGRect(x:0,y:0,width:3000,height:2000)]
 var pointerOrigin=WandPointerOrigin(),deliveryPoint:CGPoint?
 static func mouseMovementEvent(buttons:Int,from:CGPoint,to:CGPoint)->Posted? {Posted(to:to)}
 ${method('currentPointerOrigin')}
 ${method('postPointerMove')}
 /// One receiveText batch, as the receiver runs it: the origin is chosen
 /// once, then each move carries the delivered point within the batch.
 func batch(_ moves:[(Int,Int)]) {
  deliveryPoint=currentPointerOrigin();defer {deliveryPoint=nil}
  for (dx,dy) in moves {deliveryPoint=postPointerMove(dx:dx,dy:dy,from:deliveryPoint!)}
 }
}
func p(_ x:Double,_ y:Double)->CGPoint {CGPoint(x:x,y:y)}
// The first captured sequence. macOS keeps reporting the pre-move origin.
let h=Harness();CGEvent.system=p(2103,746)
h.batch([(10,-9)]);h.batch([(21,-18)]);h.batch([(9,-8)])
precondition(Harness.landed==[p(2113,737),p(2134,719),p(2143,711)],"\\(Harness.landed)")
precondition(!Harness.landed.contains(p(2112,738)),"the captured jump back to 2112,738 never happens")
// macOS catches up part way: an intermediate own point is still lag.
CGEvent.system=p(2134,719);Harness.landed=[];h.batch([(1,1)])
precondition(Harness.landed==[p(2144,712)],"a partly caught-up cursor is still our own lag")
// The second captured reversal: stale 1757,568 after reaching 1744,531.
let r=Harness();CGEvent.system=p(1757,568);Harness.landed=[]
r.batch([(-13,-37)]);r.batch([(-1,-7)])
precondition(Harness.landed==[p(1744,531),p(1743,524)] && !Harness.landed.contains(p(1756,561)),"\\(Harness.landed)")
// A physical mouse moving the cursor elsewhere is adopted at once.
CGEvent.system=p(500,500);Harness.landed=[];r.batch([(2,0)])
precondition(Harness.landed==[p(502,500)],"external movement is handed over immediately")
// Long idle: an old own point is no longer lag; the system is trusted.
let idle=Harness();CGEvent.system=p(100,100);idle.batch([(5,0)])
RunLoop.main.run(until:Date().addingTimeInterval(WandPointerOrigin.horizon+0.05))
Harness.landed=[];idle.batch([(1,0)])
precondition(Harness.landed==[p(101,100)],"after the horizon the real cursor wins")
// Nothing is buffered or replayed: one event per move, never more.
let count=Harness();CGEvent.system=p(10,10);Harness.landed=[];count.batch([(1,0),(1,0)]);count.batch([(1,0)])
precondition(Harness.landed==[p(11,10),p(12,10),p(13,10)])
print("PASS: stale cursor reads never move the pointer back")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-pointer-origin-'));
 try {
  writeFileSync(join(dir,'main.swift'),code);
  const S=f=>new URL('../receiver/Sources/'+f,import.meta.url).pathname;
  const built=spawnSync('swiftc',['-Onone',S('WandActionPause.swift'),S('WandPointerControl.swift'),join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});
  assert.equal(built.status,0,built.stderr);
  const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});
  assert.equal(run.status,0,run.stdout+run.stderr);
  assert.match(run.stdout,/PASS/);
 } finally {rmSync(dir,{recursive:true,force:true});}
});
