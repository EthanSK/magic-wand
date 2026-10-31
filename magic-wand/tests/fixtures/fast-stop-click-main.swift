import Foundation
func expect(_ condition:@autoclosure ()->Bool,_ text:String){if !condition(){print("FAIL: "+text);exit(1)}}
func brisk()->WandDwellClick {
 let d=WandDwellClick(fastStops:true);d.follow(true);d.move(dx:0,dy:0,now:0,eligible:true)
 for i in 1...8 {d.move(dx:6,dy:0,now:Double(i)*0.01,eligible:true)}
 return d
}
func quiet(_ d:WandDwellClick,from:Double){for i in 0..<3{d.move(dx:0,dy:0,now:from+Double(i)*0.01,eligible:true)}}
let fast=brisk();quiet(fast,from:0.09)
expect(fast.tick(now:0.111),"a brisk 48-point move clicks on a confirmed stop, before200ms")
expect(fast.lastClickWasFast,"the early click is identified")
expect(!fast.tick(now:0.4),"a fast stop is still a single click")
let short=WandDwellClick(fastStops:true);short.follow(true);short.move(dx:0,dy:0,now:0,eligible:true)
for i in 1...3{short.move(dx:6,dy:0,now:Double(i)*0.01,eligible:true)}
quiet(short,from:0.04);expect(!short.tick(now:0.061),"short nudges retain the precision pause");expect(short.tick(now:0.231),"short nudge still clicks after the old pause")
let precision=WandDwellClick(fastStops:true);precision.follow(true);precision.move(dx:0,dy:0,now:0,eligible:true)
for i in 1...20{precision.move(dx:1,dy:0,now:Double(i)*0.02,eligible:true)}
quiet(precision,from:0.41);expect(!precision.tick(now:0.44),"slow deliberate aiming is not accelerated");expect(precision.tick(now:0.601),"precision keeps200ms")
let approach=brisk();for i in 9...15{approach.move(dx:1,dy:0,now:Double(i)*0.01,eligible:true)}
quiet(approach,from:0.16);expect(!approach.tick(now:0.181),"slowing into the target opts back into precision");expect(approach.tick(now:0.351),"slow final approach still gets its normal click")
let one=brisk();one.move(dx:0,dy:0,now:0.09,eligible:true);expect(!one.tick(now:0.091),"one zero frame during motion is not a stop")
one.move(dx:6,dy:0,now:0.10,eligible:true);expect(!one.tick(now:0.111),"continuing the sweep cancels a possible stop")
let batched=brisk();for i in 0..<8{batched.move(dx:0,dy:0,now:0.09+Double(i)*0.0001,eligible:true)}
expect(!batched.tick(now:0.091),"many burst-delivered zero frames do not fake elapsed quiet time")
let gap=brisk();quiet(gap,from:0.18);expect(!gap.tick(now:0.201),"a missing-data gap is not immediate-stop evidence")
let lost=brisk();quiet(lost,from:0.09);expect(!lost.tick(now:0.2),"a stale accelerated timer cannot replay its click")
let gated=brisk();gated.move(dx:0,dy:0,now:0.09,eligible:false);quiet(gated,from:0.10);expect(!gated.tick(now:0.131),"a held/HUD/paused lane clears quick-click eligibility")
let noCursor=WandDwellClick(fastStops:true);noCursor.follow(true);noCursor.move(dx:0,dy:0,now:0,eligible:true)
for i in 1...8{noCursor.move(dx:6,dy:0,now:Double(i)*0.01,eligible:true,pointerX:0,pointerY:0)}
quiet(noCursor,from:0.09);expect(!noCursor.tick(now:0.111),"unshown movement cannot qualify as a pointer sweep")
let old=WandDwellClick();old.follow(true);old.move(dx:0,dy:0,now:0,eligible:true)
for i in 1...8{old.move(dx:6,dy:0,now:Double(i)*0.01,eligible:true)}
quiet(old,from:0.09);expect(!old.tick(now:0.111),"other users of DwellClick keep the old timing");expect(old.tick(now:0.281),"default timing remains200ms")
let release=brisk();release.reset();release.requireFreshFastGesture()
for i in 9...18 {release.move(dx:8,dy:0,now:Double(i)*0.01,eligible:true)}
quiet(release,from:0.19);expect(!release.tick(now:0.211),"release recoil must not earn an accelerated click")
for i in 22...30 {release.move(dx:6,dy:0,now:Double(i)*0.01,eligible:true)}
quiet(release,from:0.31);expect(release.tick(now:0.331),"a fresh intentional move after settling can click quickly")
print("PASS: clear fast stops, preserved precision, short moves, single-frame/burst/gap/stale safety, lane cancellation and actual cursor travel")

// Exercise the live call order, including the filter's motion-intent heartbeat.
// A longer brisk move activates intent after250 ms; it must not erase the
// actual cursor travel that qualifies a quick stop.
func liveStop(briskFrames:Int,approachFrames:Int=0,rate:Double=40)->(delay:Double,fast:Bool,count:Int) {
 let f=WandMotionFilter();f.path = .direct
 expect(f.configure([0,0,86.4*1.3,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,1]),"live filter configuration")
 let d=WandDwellClick(fastStops:true);d.follow(true)
 let dt=0.009615,stop=Double(briskFrames+approachFrames)*dt
 var count=0,delay=Double.infinity,fast=false,intentSeen=false
 for i in 0..<(briskFrames+approachFrames+45) {
  let rateNow=i<briskFrames ? rate : (i<briskFrames+approachFrames ? 3.0:0.0)
  let sample=f.sample(rawX:Int((rateNow/0.00875).rounded()),rawY:0,microseconds:9615,held:false,resetState:false)!
  let now=Double(i)*dt;intentSeen = intentSeen || sample.intent
  d.intent(sample.intent,now:now)
  d.move(dx:sample.stopX,dy:sample.stopY,now:now,eligible:true,pointerX:sample.x,pointerY:sample.y)
  if d.tick(now:now) {count+=1;delay=now-stop;fast=d.lastClickWasFast}
 }
 expect(intentSeen,"the sequence exercised the real motion intent signal")
 return (delay,fast,count)
}
let liveFast=liveStop(briskFrames:42)
expect(liveFast.fast && liveFast.delay<0.12 && liveFast.count==1,"long brisk live-pipeline move must click quickly once, including intent heartbeat; got \(liveFast)")
let livePrecise=liveStop(briskFrames:42,rate:3)
expect(!livePrecise.fast && livePrecise.delay>=0.18 && livePrecise.count==1,"slow live-pipeline motion keeps the precision wait; got \(livePrecise)")
let liveApproach=liveStop(briskFrames:42,approachFrames:30)
expect(!liveApproach.fast && liveApproach.delay>=0.18 && liveApproach.count==1,"slowing into a target cancels acceleration in the live pipeline; got \(liveApproach)")
print("PASS: live motion intent preserves brisk-stop evidence and slow precision timing")
