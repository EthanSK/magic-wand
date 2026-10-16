import Foundation
import Darwin
setbuf(stdout,nil)
let fixtures=try! JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1]))) as! [String:[[Double]]]
for (name,points) in fixtures.sorted(by:{$0.key<$1.key}) {
 let c=WandCircularScroll();var lines:Int32=0,hits=0
 for p in points {let r=c.update(dx:p[0],dy:p[1],now:p[2],eligible:true);lines+=r.lines;if r.consumesPointer {hits+=1}}
 print(name,lines,hits)
 if name.contains("cw") {precondition(name.contains("ccw") ? lines>0 : lines<0,name)}
 else {precondition(lines==0,name)}
}
let r=WandPointerRouter();_=r.bottom(down:true)
precondition(r.frame(dx:4,dy:3,buttons:0,hud:false,now:10).actions.isEmpty)
precondition(r.drain(now:10.08).isEmpty)
precondition(r.drain(now:10.10)==[.move(dx:4,dy:3)])
_=r.frame(dx:0,dy:-50,buttons:0,hud:false,now:11);_=r.bottom(down:false)
precondition(r.drain(now:12).isEmpty,"release jolt discarded")
precondition(r.frame(dx:8,dy:0,buttons:0,hud:false,now:12).actions==[.move(dx:8,dy:0)],"HIGH immediate")
_=r.bottom(down:true)
precondition(r.frame(dx:8,dy:0,buttons:1,hud:false,now:13).actions==[.move(dx:8,dy:0)],"actual drag immediate")
let d=WandDwellClick();d.follow(true);precondition(!d.tick(now:20),"entry never clicks")
d.move(dx:20,dy:0,now:20,eligible:true);precondition(!d.tick(now:20.4));precondition(d.tick(now:20.46));precondition(!d.tick(now:30),"one click while still")
d.move(dx:1,dy:0,now:30,eligible:true);precondition(!d.tick(now:31),"jitter does not rearm")
d.move(dx:20,dy:0,now:32,eligible:true);d.follow(false);precondition(!d.tick(now:40),"exit cancels")
d.follow(true);d.move(dx:20,dy:0,now:41,eligible:false);precondition(!d.tick(now:42),"LOW/drag/HUD excludes dwell")
let rest=WandRestDetection()
for i in 0...20 {_=rest.update(x:0,y:0,z:1,gyro:0,now:100+Double(i)*0.1,buttons:false,idle:true)}
precondition(rest.parked)
precondition(rest.update(x:0.3,y:0,z:0.954,gyro:5,now:102.1,buttons:false,idle:true)==[.probe])
precondition(rest.update(x:0.3,y:0,z:0.954,gyro:5,now:102.2,buttons:false,idle:true)==[.pickedUp])
for i in 0...60 {let e=rest.update(x:0.3,y:0,z:0.954,gyro:0.05,now:102.3+Double(i)*0.1,buttons:false,idle:false);precondition(!e.contains(.putDown),"still hand away from desk does not stop")}
var put=0
for i in 0...30 {let e=rest.update(x:0,y:0,z:1,gyro:0.01,now:109+Double(i)*0.1,buttons:false,idle:false);if e.contains(.putDown){put+=1}}
precondition(put==1 && rest.parked,"set-down exactly once")
print("PASS: independent rough traces, LOW buffer, HIGH dwell, pickup and set-down")

let review=WandReviewGesture()
_=review.button(down:true,now:200)
precondition(review.motion(y:2,now:200.1).isEmpty)
let step=review.motion(y:11,now:200.3)
precondition(step.map{$0.phase}==["begin","step"] && step.allSatisfy{$0.direction=="next"})
let reverse=review.motion(y:0,now:200.4);precondition(reverse.last?.direction=="previous")
let drop=review.button(down:false,now:200.5);precondition(drop.map{$0.phase}==["finish"])
_=review.button(down:true,now:201);_=review.button(down:false,now:201.05)
_=review.button(down:true,now:201.2);_=review.button(down:false,now:201.25);precondition(review.files)
_=review.button(down:true,now:202);_=review.motion(y:0,now:202.1);let fileStep=review.motion(y:9,now:202.4);precondition(fileStep.allSatisfy{$0.mode=="files"})
precondition(review.cancel().map{$0.phase}==["cancel"])
print("PASS: review directions, ordered lifecycle, double-tap file toggle and cancellation")

let intentDwell=WandDwellClick();intentDwell.follow(true);intentDwell.move(dx:20,dy:0,now:10,eligible:true)
intentDwell.intent(true,now:10.3)
precondition(!intentDwell.tick(now:10.5),"active subpixel motion prevents dwell")
intentDwell.intent(true,now:10.7);precondition(!intentDwell.tick(now:11.0))
intentDwell.intent(false,now:11.1);precondition(!intentDwell.tick(now:11.4));precondition(intentDwell.tick(now:11.56))
let stale=WandDwellClick();stale.follow(true);stale.move(dx:20,dy:0,now:10,eligible:true);stale.intent(true,now:10.2)
precondition(stale.tick(now:10.81),"lost intent heartbeat expires")
print("PASS: active subpixel motion, confirmed rest and bounded stale intent")

let quietDwell=WandDwellClick();quietDwell.follow(true);quietDwell.move(dx:20,dy:0,now:1,eligible:true);quietDwell.intent(false,now:1.3);quietDwell.intent(false,now:1.4);precondition(quietDwell.tick(now:1.46),"quiet heartbeats must not postpone dwell")
