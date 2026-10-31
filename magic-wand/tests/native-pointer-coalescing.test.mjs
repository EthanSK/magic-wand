// Verify that the withdrawn coalescing path stays removed and native moves keep their order.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';

// Regress the withdrawn delta-combining experiment against real receiver methods.
// Accepted movements must remain separate, including back-and-forth strokes in
// one receive turn. Inert native events preserve order, drag state and bounds.
test('accepted movements stay separate through burst, drag, reversal and click',{skip:process.platform!=='darwin'},()=>{
 const source=readFileSync(new URL('../receiver/Sources/main.swift',import.meta.url),'utf8');
 function method(name){const a=source.indexOf('    func '+name+'(');assert(a>=0,name);let b=source.indexOf('{',a)+1,depth=1;while(depth){if(source[b]==='{')depth++;if(source[b]==='}')depth--;b++;}return source.slice(a,b);}
 const receive=method('receiveText');
 assert(receive.includes('deliveryPoint=currentPointerOrigin()') && receive.includes('defer {deliveryPoint=nil}'));
 assert(!/pendingMove|moveCoalescing|flushPendingMove/.test(source),'no combining queue survives');
 const code=`import Foundation
import CoreGraphics
func log(_ v:Any...) {}
enum Tap {case cghidEventTap}
struct Posted:Equatable {let kind:String,at:CGPoint,dx:Int,dy:Int}
final class Event {
 let p:Posted;var flags=CGEventFlags()
 init(_ p:Posted){self.p=p}
 func post(tap:Tap){Harness.posted.append(p)}
 func getIntegerValueField(_ f:CGEventField)->Int64 {1}
}
final class CGEvent {static var system=CGPoint.zero;var location:CGPoint {CGEvent.system};init?(source:Int?){}}
final class Harness {
 static var posted:[Posted]=[]
 var actionPause=WandActionPause();let screenshot=WandScreenshotGesture()
 var recordingPointerPaused=false,hudSession=false,hudButtonHeld=false,hudEntryPress=false,pointerInHUD=false
 var buttons=0,pointerTravel=0.0,movementCount=0,pointerEventsPosted=0
 var pointerDisplays=[CGRect(x:0,y:0,width:1000,height:800),CGRect(x:1000,y:-300,width:600,height:400)]
 var pointerOrigin=WandPointerOrigin(),deliveryPoint:CGPoint?
 static func mouseMovementEvent(buttons:Int,from:CGPoint,to:CGPoint)->Event? {
  Event(Posted(kind:buttons & 1 != 0 ? "drag":"move",at:to,dx:Int((to.x-from.x).rounded()),dy:Int((to.y-from.y).rounded())))
 }
 static func mouseButtonEvent(button:CGMouseButton,down:Bool,at point:CGPoint)->Event? {Event(Posted(kind:down ? "down":"up",at:point,dx:0,dy:0))}
 ${method('currentPointerOrigin')}
 ${method('postPointerMove')}
 ${method('transition')}
 /// One receive turn exactly as receiveText wraps it (pinned above).
 func turn(_ body:()->Void){
  deliveryPoint=currentPointerOrigin()
  defer {deliveryPoint=nil}
  body()
 }
 func move(_ dx:Int,_ dy:Int){deliveryPoint=postPointerMove(dx:dx,dy:dy,from:deliveryPoint!)}
}
func p(_ x:Double,_ y:Double)->CGPoint {CGPoint(x:x,y:y)}
// 1. A burst retains every accepted step, instead of a single large jump.
let h=Harness();CGEvent.system=p(100,100)
h.turn {for (dx,dy) in [(5,1),(7,2),(9,2),(6,1),(3,0),(1,0)] {h.move(dx,dy)}}
precondition(Harness.posted.map{$0.at}==[p(105,101),p(112,103),p(121,105),p(127,106),p(130,106),p(131,106)],"\\(Harness.posted)")
precondition(h.movementCount==6 && h.pointerEventsPosted==6 && h.pointerTravel==37,"every reading is still counted")
// macOS reporting the turn's start late is the wand's own lag (receiver 172).
CGEvent.system=p(100,100)
precondition(h.currentPointerOrigin()==p(131,106),"a late report of the turn start never rewinds the pointer")
// 2. A press inside a turn: motion before it lands first, the drag after it
//    stays a drag, and the release follows the drag. Exact order and places.
let d=Harness();CGEvent.system=p(200,200);Harness.posted=[]
d.turn {
 d.move(4,0);d.move(4,0)
 d.transition(to:1,at:d.deliveryPoint!)
 d.move(0,6);d.move(0,6)
 d.transition(to:0,at:d.deliveryPoint!)
 d.move(3,0)
}
precondition(Harness.posted.map{$0.kind}==["move","move","down","drag","drag","up","move"] &&
 Harness.posted.map{$0.at}==[p(204,200),p(208,200),p(208,200),p(208,206),p(208,212),p(208,212),p(211,212)],"\\(Harness.posted)")
// 3. Display edges: each reading is clamped where it happens, as before.
//    Pushing out then back lands 5 px inside, not at the edge, and never
//    passes through the gap beside the second display.
let e=Harness();CGEvent.system=p(990,700);Harness.posted=[]
e.turn {e.move(30,0);e.move(-5,0)}
precondition(Harness.posted.map{$0.at}==[p(999,700),p(994,700)],"sequential edge clamping is preserved: \\(Harness.posted)")
let g=Harness();CGEvent.system=p(995,10);Harness.posted=[]
g.turn {g.move(20,-200);g.move(0,-50)}
precondition(Harness.posted.count==2 && Harness.posted.allSatisfy{event in g.pointerDisplays.contains{$0.contains(event.at)}},"each move ends on a real display: \\(Harness.posted)")
// 4. A reversal in one turn remains two real movements, never netted to zero.
let z=Harness();CGEvent.system=p(300,300);Harness.posted=[]
z.turn {z.move(5,0);z.move(-5,0)}
precondition(Harness.posted.map{$0.at}==[p(305,300),p(300,300)] && z.movementCount==2,"both directions survive")
// 5. A held HUD button still freezes the pointer; nothing is queued for later.
let u=Harness();CGEvent.system=p(400,400);Harness.posted=[];u.hudSession=true;u.hudButtonHeld=true
u.turn {u.move(30,0);u.move(30,0)}
u.hudButtonHeld=false
u.turn {u.move(2,0)}
precondition(Harness.posted==[Posted(kind:"move",at:p(402,400),dx:2,dy:0)],"held HUD motion is dropped, never replayed: \\(Harness.posted)")
// 6. A stop-to-click after the turn presses where the combined move ended.
let c=Harness();CGEvent.system=p(500,500);Harness.posted=[]
c.turn {c.move(10,0);c.move(10,0)}
CGEvent.system=p(500,500)
let press=c.currentPointerOrigin();c.transition(to:1,at:press);c.transition(to:0,at:press)
precondition(Harness.posted.map{$0.at}==[p(510,500),p(520,500),p(520,500),p(520,500)] && Harness.posted.map{$0.kind}==["move","move","down","up"],"\\(Harness.posted)")
// 7. Outside a receive turn (timer-driven motion) each move is shown at once.
let o=Harness();CGEvent.system=p(50,50);Harness.posted=[]
o.deliveryPoint=o.currentPointerOrigin()
o.move(1,0);o.move(1,0)
precondition(Harness.posted.count==2,"no combining outside a receive turn")
print("PASS: separate motion keeps destination, order, clamping, HUD and click placement")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-pointer-coalescing-'));
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
