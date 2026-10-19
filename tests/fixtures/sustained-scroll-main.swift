import Foundation
for (x,y) in [(20.0,0.0),(-20.0,0.0),(0.0,20.0),(0.0,-20.0),(20.0,20.0)] {
 let h=WandHeldScroll();h.begin(now:0,sustain:true)
 precondition(h.continuation(now:0.2)==(0,0))
 _=h.sample(x:x,y:y,dt:0.01,now:0.23)
 var sx:Int32=0,sy:Int32=0
 for i in 1...50 {let now=0.23+Double(i)*0.02;h.confirmHeld(now:now);_=h.sample(x:0,y:0,dt:0.02,now:now);let r=h.continuation(now:now);sx+=r.x;sy+=r.y}
 precondition((x==0 ? sx==0 : Double(sx)*x>0) && (y==0 ? sy==0 : Double(sy)*y>0),"all directions, including diagonals")
 precondition(abs(Double(sx)-x*1.6)<3 && abs(Double(sy)-y*1.6)<3,"initial drag rate continues while still")
 _=h.continuation(now:1.25)
 _=h.sample(x:-x,y:-y,dt:0.01,now:1.26)
 var rx:Int32=0,ry:Int32=0
 for i in 1...20 {let now=1.26+Double(i)*0.02;h.confirmHeld(now:now);let r=h.continuation(now:now);rx+=r.x;ry+=r.y}
 precondition((x==0 ? rx==0 : Double(rx)*x<0) && (y==0 ? ry==0 : Double(ry)*y<0),"same hold reverses without circling")
 precondition(!h.circular)
 _=h.end(now:1.7);precondition(h.continuation(now:1.72)==(0,0),"release immediately cancels continuation")
 h.begin(now:2,sustain:true);h.confirmHeld(now:2.3)
 precondition(h.continuation(now:2.3)==(0,0),"next hold cannot inherit speed")
 _=h.sample(x:x,y:y,dt:0.01,now:2.31)
 precondition(h.continuation(now:3.2)==(0,0),"lost telemetry cannot keep scrolling")
}
let noise=WandHeldScroll();noise.begin(now:0,sustain:true)
for i in 1...100 {let t=Double(i)*0.01;noise.confirmHeld(now:t);_=noise.sample(x:0.5,y:-0.5,dt:0.01,now:t);precondition(noise.continuation(now:t)==(0,0))}
let drag=WandHeldScroll();drag.begin(now:0,scrollable:false,sustain:true);precondition(drag.startDrag(now:0.3));precondition(drag.continuation(now:0.3)==(0,0))
let fast=WandSustainedScroll();fast.sample(x:10000,y:0,dt:0.01);precondition(fast.velocityX==120);precondition(fast.tick(now:100).x<=6,"late timer cannot replay a backlog")
precondition(WandControlVersion.read(3) == .sustainedV3)
print("PASS: four directions, diagonal scrolling, initial speed at rest, in-hold reversals, release, telemetry loss, fresh holds, quiet noise, explicit drag, bounded timers")
