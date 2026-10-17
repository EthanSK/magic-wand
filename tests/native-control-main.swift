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
let immediate=WandPointerRouter(lowDelay:0);_=immediate.bottom(down:true)
precondition(immediate.lowDelay==0)
precondition(immediate.frame(dx:4,dy:3,buttons:0,hud:false,now:10).actions==[.move(dx:4,dy:3)],"LOW immediate")
precondition(immediate.pendingCount==0 && immediate.nextDue==nil,"no LOW timer")
_=immediate.bottom(down:false)
precondition(immediate.drain(now:12).isEmpty,"release never replays motion")
precondition(immediate.frame(dx:0,dy:0,buttons:1,hud:false,now:12).buttons==1,"release click preserved")
let r=WandPointerRouter(lowDelay:0.09);precondition(r.lowDelay==0.09);_=r.bottom(down:true)
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
for i in 0...60 {let e=rest.update(x:0.3+Double(i%2)*0.03,y:0,z:0.954,gyro:1.0,now:102.3+Double(i)*0.1,buttons:false,idle:false);precondition(!e.contains(.putDown),"moving hand away from desk does not stop")}
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

precondition(WandPointerRouter().lowDelay==0)

// Rest detection uses elapsed time at the sleeping 1.6 Hz rate and tolerates
// an uncalibrated accelerometer reporting a stationary magnitude above 1 g.
let tableDirectory=URL(fileURLWithPath:NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
try FileManager.default.createDirectory(at:tableDirectory,withIntermediateDirectories:true)
defer{try? FileManager.default.removeItem(at:tableDirectory)}
let tableCache=tableDirectory.appendingPathComponent("table.json")
let table=WandRestDetection(cache:tableCache)
for i in 0...5 {
 let jitter=i%2==0 ? 0.002 : -0.002
 let e=table.update(x:0,y:0,z:1.055+jitter,gyro:0,now:1+Double(i)*0.625,buttons:false,idle:true)
 precondition(e.isEmpty,"initial idle reference must not itself stop recording")
}
precondition(table.parked && table.hasReference)
let savedTable=WandRestDetection(cache:tableCache)
precondition(savedTable.hasReference && !savedTable.parked)
savedTable.reset(keepingReference:true);precondition(savedTable.hasReference)
savedTable.pointerActivated()
var tableStops=0
for i in 0...5 {
 let e=savedTable.update(x:0,y:0,z:1.055,gyro:0,now:6+Double(i)*0.625,buttons:false,idle:false)
 tableStops+=e.contains(.putDown) ? 1:0
}
precondition(tableStops==1 && savedTable.parked,"manual HIGH returns to table within seconds at low sample rate")
var pickupEvents:[WandRestDetection.Event]=[]
for i in 0...1 {pickupEvents+=savedTable.update(x:0.08,y:0,z:1.052,gyro:1,now:10+Double(i)*0.625,buttons:false,idle:true)}
precondition(pickupEvents.contains(.pickedUp),"small pickup must rearm a later put-down")
for i in 0...40 {precondition(!savedTable.update(x:0.08+Double(i%2)*0.03,y:0,z:1.052,gyro:1.0,now:12+Double(i)*0.1,buttons:false,idle:false).contains(.putDown))}
var gentleStops=0
for i in 0...5 {gentleStops+=savedTable.update(x:0,y:0,z:1.055,gyro:0,now:18+Double(i)*0.625,buttons:false,idle:false).contains(.putDown) ? 1:0}
precondition(gentleStops==1)
print("PASS: biased gravity, low-rate table rest, persistent reference, manual mode and gentle pickup")

// A gentle set-down at a different angle has no impact and must still park.
let newAngle=WandRestDetection();newAngle.pointerActivated()
var newAngleStops=0
for i in 0...25 {
 let e=newAngle.update(x:0.13+Double(i%2)*0.002,y:0.31,z:0.998,gyro:0.05,now:200+Double(i)*0.1,buttons:false,idle:false)
 newAngleStops+=e.contains(.putDown) ? 1:0
}
precondition(newAngleStops==1 && newAngle.parked,"new table angle without impact or old reference")
let flatPickup=newAngle.update(x:0.13,y:0.31,z:1.08,gyro:0,now:203,buttons:false,idle:true)
precondition(flatPickup==[.probe],"translation wakes a sleeping probe")
precondition(newAngle.update(x:0.13,y:0.31,z:1.08,gyro:0,now:203.1,buttons:false,idle:true)==[.pickedUp])
print("PASS: gentle new-angle set-down and translation pickup")

let activeTable=WandRestDetection();activeTable.pointerActivated()
let activeSamples:[[Double]]=[[0.2052001953125, -0.08056640625, 1.0428466796875, 0.1], [0.20947265625, -0.084228515625, 1.021728515625, 0.14], [0.2020263671875, -0.0784912109375, 1.0401611328125, 0.24], [0.2130126953125, -0.0814208984375, 1.0302734375, 0.5], [0.206787109375, -0.08349609375, 1.0479736328125, 0.19], [0.2099609375, -0.0841064453125, 1.0299072265625, 0.13], [0.20849609375, -0.07421875, 1.0523681640625, 0.44], [0.2100830078125, -0.0848388671875, 1.0294189453125, 0.14], [0.207763671875, -0.083740234375, 1.0626220703125, 0.15], [0.2120361328125, -0.0848388671875, 1.0457763671875, 0.15], [0.2093505859375, -0.0830078125, 1.02099609375, 0.23], [0.20849609375, -0.0814208984375, 1.0440673828125, 0.17], [0.211669921875, -0.0814208984375, 1.0218505859375, 0.19], [0.2060546875, -0.0830078125, 1.046142578125, 0.2], [0.20654296875, -0.0814208984375, 1.0274658203125, 0.24], [0.2076416015625, -0.080322265625, 1.049560546875, 0.12], [0.208740234375, -0.083740234375, 1.0269775390625, 0.21], [0.2071533203125, -0.0830078125, 1.043701171875, 0.14]]
var activeStops=0
for i in 0...55 {let p=activeSamples[i%activeSamples.count];activeStops += activeTable.update(x:p[0],y:p[1],z:p[2],gyro:p[3],now:300+Double(i)*0.1,buttons:false,idle:false).contains(.putDown) ? 1:0}
precondition(activeStops==1,"actual active-rate desk noise must stop exactly once")
print("PASS: actual active sensor noise parks once")

let positionTest=WandPointerPosition()
precondition(positionTest.observe(CGPoint(x:100,y:100))==CGPoint(x:100,y:100))
positionTest.posted(CGPoint(x:120,y:100));positionTest.posted(CGPoint(x:140,y:100))
precondition(positionTest.observe(CGPoint(x:100,y:100))==CGPoint(x:140,y:100),"next Bluetooth delivery must not rewind to stale observation")
precondition(positionTest.observe(CGPoint(x:120,y:100))==CGPoint(x:140,y:100),"dwell click uses final issued position while OS acknowledges an intermediate point")
positionTest.posted(CGPoint(x:145,y:100))
precondition(positionTest.observe(CGPoint(x:140,y:100))==CGPoint(x:145,y:100),"resuming after click carries latest position")
precondition(positionTest.observe(CGPoint(x:145,y:100))==CGPoint(x:145,y:100))
precondition(positionTest.observe(CGPoint(x:300,y:400))==CGPoint(x:300,y:400),"physical mouse or application warp is respected immediately")
positionTest.posted(CGPoint(x:310,y:400));positionTest.reset()
precondition(positionTest.observe(CGPoint(x:20,y:30))==CGPoint(x:20,y:30),"display reconfiguration resets old coordinates")
let restartDwell=WandDwellClick();restartDwell.follow(true);restartDwell.move(dx:20,dy:0,now:1,eligible:true)
precondition(restartDwell.tick(now:1.46));precondition(!restartDwell.tick(now:2),"dwell still clicks exactly once")
restartDwell.move(dx:3,dy:0,now:2,eligible:true);precondition(!restartDwell.tick(now:2.5),"tiny restart does not repeat click")
print("PASS: stale position, intermediate acknowledgements, dwell resume, external mouse, display reset and click contract")
