import Foundation
setbuf(stdout, nil)
// Inert click-lane regressions (receiver191 candidate). Pure maths with the real
// WandMotionFilter and WandDwellClick in the live handleRaw call order; no native
// input, transport or hardware. Ethan (2026-11-01): "if I've moved the wand just
// a little bit, it should kick again sooner. It waits too long" and "the fast
// click thing doesn't even happen as much as it did before".
let config=[0,0,86.4*1.1725,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,1]
/// Phases of constant pointer rates (filter units/s, 134 counts each) at 104 Hz.
/// Returns click times relative to the end of phase `from` and the fast flag.
func exercise(_ phases:[(Double,Double,Double)],from:Int=0)->[(Double,Bool)] {
 let f=WandMotionFilter();precondition(f.configure(config));f.path = .direct
 let d=WandDwellClick(fastStops:true);d.follow(true)
 var now=10.0,clicks:[(Double,Bool)]=[]
 let origin=10.0+phases.prefix(from+1).reduce(0.0){$0+Double(Int($1.2*104))*0.009615}
 for (x,y,duration) in phases {
  for _ in 0..<Int(duration*104) {
   let s=f.sample(rawX:Int((x*134).rounded()),rawY:Int((y*134).rounded()),microseconds:9615,held:false,resetState:false)!
   d.intent(s.intent,now:now) // the ordinary path in isolation: no rest flag, no settled clicks
   d.move(dx:s.stopX,dy:s.stopY,now:now,eligible:true,pointerX:s.x,pointerY:s.y,sampleSeconds:0.009615,pointerQuiet:s.quietForClick,fineMove:s.fineMoving)
   if d.tick(now:now) {clicks.append((now-origin,d.lastClickWasFast));f.holdAfterAutomaticClick()}
   now+=0.009615
  }
 }
 return clicks
}

// 1. A small visible target move, then slow coherent residual drift with no
// visible step. Receiver186-190 restarted the pause on every such reading and
// never clicked; the pause now ends one interval after the last visible step.
for drift in [0.02,0.04] {
 let c=exercise([(0,0,0.3),(0.7,0,0.25),(drift,0,1.5)],from:1)
 print("small move then invisible drift",drift,c)
 precondition(c.count==1 && !c[0].1 && c[0].0<=0.45,"a visibly stopped small move clicks within two pause intervals: \(c)")
}

// 2. A brisk sweep that settles into a coherent sub-pixel tail. Invisible
// readings now count as quiet for the brisk-stop click; previously no click.
let brisk=exercise([(0,0,0.3),(50,0,0.25),(0.04,0,0.6)],from:1)
print("brisk then sub-pixel tail",brisk)
precondition(brisk.count==1 && brisk[0].1 && brisk[0].0<=0.08,"a brisk stop clicks quickly despite an invisible tail: \(brisk)")

// 3. Continuous slow aiming still never clicks mid-aim (about 3 px/s and up).
for rate in [0.08,0.15,0.3,0.7,1.5] {
 let c=exercise([(rate,0,3)])
 precondition(c.isEmpty,"continuous slow aiming at \(rate) must not click: \(c)")
}
// The original repeated small targets and fast-then-fine sequence keep their clicks.
let precise=exercise([(0,0,0.3),(0.7,0,0.25),(0,0,0.35),(-0.7,0,0.25),(0,0,0.35)])
precondition(precise.count==2 && precise.allSatisfy{!$0.1},"precise alternating targets: \(precise)")
let fastThenFine=exercise([(0,0,0.3),(50,0,0.25),(0,0,0.3),(0.7,0,0.25),(0,0,0.35)])
precondition(fastThenFine.count==2 && fastThenFine[0].1 && !fastThenFine[1].1,"fast then fine: \(fastThenFine)")
print("PASS: visible stops click sooner; continuous slow aiming and fine targets are preserved")

// 4. On the direct path a visible pointer step can carry zero tuned stop
// counts. The precision pause must count from the last visible step, never
// clicking while the pointer is still visibly moving.
let d=WandDwellClick(fastStops:true);d.follow(true)
var t=20.0,clicked:[Double]=[]
d.move(dx:12,dy:0,now:t,eligible:true,pointerX:12,pointerY:0,sampleSeconds:0.009615,pointerQuiet:false)
for i in 1...120 {
 t+=0.009615
 let step=i<=60 && i%10==0 // a 1 px visible step every ~96 ms for ~0.6 s
 d.move(dx:0,dy:0,now:t,eligible:true,pointerX:step ? 1:0,pointerY:0,sampleSeconds:0.009615,pointerQuiet:!step)
 if d.tick(now:t) {clicked.append(t)}
}
let lastStep=20.0+0.009615*60
print("visible steps with zero stop counts",clicked.map{$0-lastStep})
precondition(clicked.count==1 && clicked[0]>=lastStep+0.199 && clicked[0]<=lastStep+0.21,"click 200 ms after the last visible step: \(clicked.map{$0-lastStep})")

// 5. Tuned/Puck call shape is unchanged: 12 counts of travel, then 200 ms.
let tuned=WandDwellClick(fastStops:true);tuned.follow(true)
tuned.move(dx:12,dy:0,now:30,eligible:true,pointerX:12,pointerY:0,sampleSeconds:0.009615,pointerQuiet:false)
precondition(!tuned.tick(now:30.199) && tuned.tick(now:30.2),"ordinary 200 ms pause after travel")
print("PASS: the precision pause starts at the last visible step; tuned timing unchanged")
