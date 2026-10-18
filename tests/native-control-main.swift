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

let heldScroll=WandPointerRouter();_=heldScroll.bottom(down:true)
var loopX=80.0,loopY=0.0
for i in 1...105 {
 let a=Double(i)/35*2*Double.pi,nx=80*cos(a),ny=80*sin(a)
 _=heldScroll.frame(dx:Int((nx-loopX).rounded()),dy:Int(((ny-loopY)*1.4).rounded()),buttons:0,hud:false,now:10+Double(i)/35)
 loopX=nx;loopY=ny
}
precondition(heldScroll.circle.active)
precondition(heldScroll.tick(now:16).isEmpty,"pause keeps held scrolling")
for i in 0..<100 {precondition(!heldScroll.frame(dx:8,dy:0,buttons:0,hud:false,now:17+Double(i)/35).actions.contains{if case .move = $0{return true};return false},"straight motion cannot move pointer after scroll recognition")}
precondition(heldScroll.circle.active)
precondition(heldScroll.bottom(down:false)==[.circleLight(false)])
precondition(heldScroll.frame(dx:0,dy:0,buttons:1,hud:false,now:21).buttons==0,"scroll release never clicks")
precondition(heldScroll.frame(dx:4,dy:0,buttons:0,hud:false,now:22).actions==[.move(dx:4,dy:0)])
print("PASS: held scrolling survives pause and straight motion until release")

let center=WandRecenterGesture()
precondition(!center.edge(down:true,now:1));precondition(!center.edge(down:false,now:1.08))
precondition(!center.edge(down:true,now:1.2));precondition(center.edge(down:false,now:1.28))
precondition(!center.edge(down:true,now:2));precondition(!center.edge(down:false,now:2.08))
precondition(!center.edge(down:true,now:2.2));precondition(!center.edge(down:false,now:2.5),"held second press must remain a drag")
precondition(!center.edge(down:true,now:3));precondition(!center.edge(down:false,now:3.08))
precondition(!center.edge(down:true,now:3.2,eligible:false));precondition(!center.edge(down:false,now:3.28),"other modes cancel double tap")
print("PASS: short double tap recenters; held second press and other modes do not")

// The first sharp upward cue arms scrolling; only the slow downward return scrolls.
let flick=WandFlickScroll()
var now=100.0
func sampleFlick(_ x:Double,_ y:Double,_ eligible:Bool=true)->WandFlickScroll.Result {
 now+=0.01;return flick.sample(x:x,y:y,dt:0.01,now:now,eligible:eligible)
}
for _ in 0..<100 {precondition(!sampleFlick(2,-3).consumesPointer)}
for _ in 0..<6 {let r=sampleFlick(1,-100);precondition(r.consumesPointer && r.lines==0)}
let firstReturn=sampleFlick(0,12)
precondition(firstReturn.lines==1,"first deliberate slow return scrolls immediately")
var flickLines:Int32=firstReturn.lines
for _ in 0..<80 {let r=sampleFlick(0,12);precondition(r.consumesPointer);flickLines+=r.lines}
precondition(flickLines>10,"first slow return scrolls up without repeated flicks")
for _ in 0..<30 {_=sampleFlick(0,0)}
precondition(!flick.active,"stationary return ends capture")
flick.reset();_=sampleFlick(0,-70);precondition(!sampleFlick(0,0).consumesPointer,"one-sample click jolt must not scroll")
for _ in 0..<10 {_=sampleFlick(0,-100)}
precondition(!sampleFlick(0,10,false).consumesPointer && !flick.active,"Bottom hold, HUD and disabled option cancel immediately")
flick.reset();for _ in 0..<80 {precondition(!sampleFlick(0,15).consumesPointer,"slow pointing alone never starts scrolling")}
for _ in 0..<8 {_=sampleFlick(0,-100)}
precondition(!sampleFlick(80,0).consumesPointer,"sideways pointing cancels")
flick.reset();for _ in 0..<8 {_=sampleFlick(0,-100)}
precondition(!sampleFlick(0,80).consumesPointer,"fast down movement is not a slow return")
let optionURL=URL(fileURLWithPath:NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString+".json")
let settings=WandUserOptions(url:optionURL)
precondition(!settings.enabled("flickScroll"))
try settings.set("orientationCompensation",true);try settings.set("flickScroll",true)
precondition(settings.enabled("flickScroll") && settings.enabled("orientationCompensation"))
try settings.set("flickScroll",false)
precondition(!settings.enabled("flickScroll") && settings.enabled("orientationCompensation"))
try FileManager.default.removeItem(at:optionURL)
print("PASS: optional first-flick scrolling, noise rejection, cancellation and persisted options")

let scrollV2=WandHeldScroll()
scrollV2.begin(now:200)
precondition(scrollV2.active && scrollV2.consumes(buttons:0))
var up:Int32=0,down:Int32=0
for _ in 0..<50 {up += scrollV2.sample(y:-20,dt:0.01)}
for _ in 0..<50 {down += scrollV2.sample(y:20,dt:0.01)}
precondition(up == -16 && down == -16,"starting direction holds through the initial return")
precondition(scrollV2.end(now:201))
precondition(!scrollV2.active && scrollV2.sample(y:50,dt:0.01)==0,"release stops immediately")
precondition(!scrollV2.consumes(buttons:0),"interleaved raw reports cannot clear pending click suppression")
precondition(scrollV2.consumes(buttons:1) && scrollV2.consumes(buttons:0),"old release click swallowed in order")
precondition(!scrollV2.consumes(buttons:1),"later click remains valid")
scrollV2.begin(now:202);precondition(!scrollV2.end(now:202.08))
precondition(!scrollV2.consumes(buttons:1),"a short tap keeps existing mouse behavior")
scrollV2.begin(now:203);precondition(scrollV2.end(now:203.3))
precondition(scrollV2.consumes(buttons:1),"stationary hold must not click on release")
scrollV2.begin(now:204);scrollV2.reset();precondition(!scrollV2.active)
for value:Any in [0,3,-1,1.5,true,"2"] {precondition(WandControlVersion.read(value) == .pointerV1)}
precondition(WandControlVersion.read(2) == .scrollV2)
print("PASS: V2 held scroll, unchanged short taps, ordered click suppression, no stale movement, version fallback")

let contextual=WandHeldScroll()
contextual.begin(now:300,scrollable:false)
precondition(!contextual.startDrag(now:300.1),"short taps never generate a native drag")
precondition(contextual.startDrag(now:300.23) && contextual.dragging)
precondition(!contextual.startDrag(now:300.3),"mouse down emitted once")
precondition(contextual.sample(y:20,dt:0.01,now:300.3)==0,"drag target never scrolls")
contextual.setTarget(scrollable:true);precondition(!contextual.scrollable,"late hit test cannot change an active drag")
_=contextual.end(now:301)
contextual.begin(now:302,scrollable:true)
precondition(!contextual.startDrag(now:302.4),"scroll target never starts dragging")
precondition(contextual.sample(y:-20,dt:0.01,now:302.1)==0,"existing tap cutoff retained")
var lines:Int32=0
for i in 0..<10 {lines+=contextual.sample(y:-20,dt:0.01,now:302.23+Double(i)*0.01)}
precondition(lines<0)
print("PASS: context selection preserves short taps and emits one drag down only for non-scroll targets")


// Start up or down, then continue around rough circles in either direction.
// Winding does not change page direction, and sideways arcs keep scrolling.
for direction in [-1.0,1.0] {
 for winding in [-1.0,1.0] {
  let held=WandHeldScroll();held.begin(now:400)
  for i in 0..<35 {_=held.sample(x:0,y:direction*20,dt:0.01,now:400.23+Double(i)*0.01)}
  var circularLines:Int32=0,wrongWay=0,sidewaysLines:Int32=0
  for i in 0..<250 {
   let angle=Double(i)*0.01*2*Double.pi
   let speed=20.0*(1+0.25*sin(angle*3))
   let x=winding*speed*sin(angle),y=direction*speed*cos(angle)
   let lines=held.sample(x:x,y:y,dt:0.01,now:400.58+Double(i)*0.01)
   if Double(lines)*direction<0 {wrongWay+=1}
   if held.circular {circularLines+=lines;if abs(sin(angle))>0.9 {sidewaysLines+=lines}}
  }
  precondition(held.circular && Double(circularLines)*direction>40)
  precondition(wrongWay==0 && Double(sidewaysLines)*direction>0,"circle continuation keeps initial direction, including sideways arcs")
  _=held.sample(x:0,y:0,dt:0.01,now:404)
  precondition(held.circular && held.sample(x:direction*20,y:0,dt:0.05,now:404.1)*Int32(direction)>0,"pause keeps circle continuation until release")
  _=held.end(now:405)
  precondition(held.sample(x:20,y:20,dt:0.01,now:405.1)==0 && !held.circular)
 }
}
let straight=WandHeldScroll();straight.begin(now:500)
var straightForward:Int32=0,straightReverse:Int32=0
for i in 0..<60 {straightForward+=straight.sample(x:0,y:20,dt:0.01,now:500.23+Double(i)*0.01)}
for i in 0..<60 {straightReverse+=straight.sample(x:0,y:-20,dt:0.01,now:500.83+Double(i)*0.01)}
precondition(!straight.circular && straightForward>0 && straightReverse>0,"before circle recognition the return retains the starting direction")
let sideways=WandHeldScroll();sideways.begin(now:600)
for i in 0..<100 {precondition(sideways.sample(x:20,y:0,dt:0.01,now:600.23+Double(i)*0.01)==0)}
precondition(!sideways.circular,"sideways movement alone cannot choose a scroll direction")
print("PASS: up/down start, both rough circle windings, sideways arcs, pause/release, direction latch and no sideways-only start")


// A first U-turn may be left or right. Later opposite winding reverses the
// mapped scroll direction without another press, then reversing again restores it.
for initialDirection in [-1.0,1.0] {
 for initialWinding in [-1.0,1.0] {
  for ovalWidth in [0.65,1.0,1.8] {
   let gesture=WandHeldScroll();gesture.begin(now:700)
   var timestamp=700.23,angle=0.0
   for _ in 0..<40 {timestamp+=0.01;_=gesture.sample(y:initialDirection*20,dt:0.01,now:timestamp)}
   func circleRun(_ direction:Double)->[Int32] {
    var outputs:[Int32]=[]
    for i in 0..<150 {
     angle+=direction*2*Double.pi*0.01
     let speed=20*(1+0.2*sin(angle*3))
     timestamp+=0.01
     let line=gesture.sample(x:direction*initialWinding*ovalWidth*speed*sin(angle),y:direction*initialDirection*speed*cos(angle),dt:0.01,now:timestamp)
     if i>60 {outputs.append(line)}
    }
    return outputs
   }
   let first=circleRun(1)
   precondition(gesture.circular && first.reduce(0,+)*Int32(initialDirection)>0)
   let baseHeading=atan2(initialDirection*20*cos(angle),initialWinding*ovalWidth*20*sin(angle))
   for i in 0..<20 {
    timestamp+=0.01
    let heading=baseHeading+(i%2==0 ? 0.08:-0.08)
    let wobble=gesture.sample(x:20*cos(heading),y:20*sin(heading),dt:0.01,now:timestamp)
    precondition(Double(wobble)*initialDirection>=0,"alternating small wobbles must not reverse scrolling")
   }
   let reversed=circleRun(-1)
   precondition(reversed.reduce(0,+)*Int32(initialDirection)<0,"reverse circle must reverse scrolling without release")
   precondition(reversed.allSatisfy{Double($0)*initialDirection<=0},"confirmed reverse stays consistent")
   let restored=circleRun(1)
   precondition(restored.reduce(0,+)*Int32(initialDirection)>0,"reverse again restores initial direction")
   _=gesture.end(now:timestamp+0.01)
   precondition(gesture.sample(x:20,y:20,dt:0.01)==0)
  }
 }
}
print("PASS: both initial U-turn sides, up/down starts, rough oval reversal and reversal back without release")


// The first U can have a flat bottom, a pause or a tiny corner. None is a
// command to reverse scrolling before winding has been established.
for handoverDirection in [-1.0,1.0] {
 for side in [-1.0,1.0] {
  for paused in [false,true] {
   let handover=WandHeldScroll();handover.begin(now:900)
   var handoverTime=900.23
   for _ in 0..<40 {handoverTime+=0.01;_=handover.sample(x:0,y:handoverDirection*20,dt:0.01,now:handoverTime)}
   if paused {handoverTime+=0.5;_=handover.sample(x:0,y:0,dt:0.01,now:handoverTime)}
   var returningLines:Int32=0
   for _ in 0..<20 {handoverTime+=0.01;let l=handover.sample(x:side*20,y:0,dt:0.01,now:handoverTime);precondition(Double(l)*handoverDirection>=0,"flat U bottom cannot reverse")}
   for _ in 0..<40 {handoverTime+=0.01;let l=handover.sample(x:0,y:-handoverDirection*20,dt:0.01,now:handoverTime);returningLines+=l;precondition(Double(l)*handoverDirection>=0,"returning U leg must retain starting direction before circle recognition")}
   precondition(Double(returningLines)*handoverDirection>0)
  }
 }
}
print("PASS: flat and paused U transitions retain the first direction before circle recognition")


let steadyArc=WandHeldScroll();steadyArc.begin(now:1000)
for i in 0..<40 {_=steadyArc.sample(y:20,dt:0.01,now:1000.23+Double(i)*0.01)}
var arcBins=[Int32](repeating:0,count:4)
for i in 0..<100 {
 let angle=Double(i)*Double.pi/100
 arcBins[i/25]+=steadyArc.sample(x:20*sin(angle),y:20*cos(angle),dt:0.01,now:1000.63+Double(i)*0.01)
}
precondition(steadyArc.circular && arcBins.allSatisfy{(7...9).contains(Int($0))},"same speed must keep the same wheel rate before, during and after circle recognition")
print("PASS: constant-speed U-turn has no sign or gain discontinuity at recognition")
