import Foundation
var failures=0
func check(_ v:Bool,_ name:String){if !v{print("FAIL",name);failures+=1}}
func circle(_ sign:Double,dt:Double=0.03,turns:Double=3)->[Int32] {
 var r=WandReviewCircle(),steps:[Int32]=[],x=8.0,y=0.0,t=1.0
 for i in 1...Int(120*turns){let a=sign*Double(i)*Double.pi/60,xx=cos(a)*8,yy=sin(a)*8;t+=dt;steps.append(r.sample(dx:xx-x,dy:yy-y,now:t));x=xx;y=yy}
 return steps
}
let cw=circle(1),ccw=circle(-1)
check(cw.reduce(0,+)>12 && cw.allSatisfy{$0>=0},"clockwise is next only")
check(ccw.reduce(0,+)<(-12) && ccw.allSatisfy{$0<=0},"anticlockwise is previous only")
check(circle(1,dt:0.12).reduce(0,+)>12,"slow intended circles")
var r=WandReviewCircle(),sum:Int32=0
for i in 1...300{sum += r.sample(dx:0,dy:0.5,now:Double(i)*0.03)}
check(sum==0,"straight movement is not a review gesture")
r.reset();sum=0
for i in 1...300{sum += r.sample(dx:i%2==0 ? 0.005 : -0.005,dy:0.004,now:Double(i)*0.03)}
check(sum==0,"still-hand noise is ignored")
r.reset();var t=1.0,x=8.0,y=0.0,forward:Int32=0,back:Int32=0
for (segment,sign) in [1.0,-1.0].enumerated(){
 for i in 1...240 {let a=sign*Double(i)*Double.pi/60,xx=cos(a)*8,yy=sin(a)*8;t+=0.03;let n=r.sample(dx:xx-x,dy:yy-y,now:t);if segment==0{forward+=n}else{back+=n};x=xx;y=yy}
}
check(forward>12 && back < -12,"winding reverses within the same session")
let g=WandReviewGesture();g.beginDetents(mode:"changes",now:0)
let req=g.detents(2,now:1);check(req.map{$0.phase} == ["begin","step","step"],"reuse ordered lifecycle")
check(req.allSatisfy{$0.mode=="changes"&&$0.direction=="next"},"eyes contract")
_ = g.detents(0,now:5);check(!g.tick(now:5).contains{$0.phase=="cancel"},"idle selected session can stay alive")
let finished=g.endDetents(commit:true)
check(finished.last?.phase=="finish","long press finishes existing selection")
g.beginDetents(mode:"changes",now:5.1)
let continued=g.detents(1,now:5.2)
check(continued.map{$0.phase} == ["begin","step"] && continued.first?.id != finished.first?.id,"continuing review starts a fresh ordered set")
check(continued.allSatisfy{$0.mode=="changes"},"continuing review preserves eyes mode")
_ = g.cancel()
g.beginDetents(mode:"files",now:6);check(g.detents(-1,now:7).allSatisfy{$0.mode=="files"&&$0.direction=="previous"},"whole-file contract")
check(g.cancel().last?.phase=="cancel","focus loss cancels")
var exitGesture=WandReviewExitGesture()
exitGesture.down(now:0)
check(exitGesture.pending && !exitGesture.commitIfHeld(now:0.49),"hold freezes input before its deadline")
check(exitGesture.commitIfHeld(now:0.5),"long press commits at the deadline")
check(exitGesture.pending && !exitGesture.commitIfHeld(now:2),"one commit while still held, input remains frozen")
check(exitGesture.up(now:2) == .none && !exitGesture.pending,"release unfreezes without exit or another commit")
exitGesture.down(now:3)
check(exitGesture.up(now:3.1) == .cancel && !exitGesture.pending,"short tap cancels without staging")
exitGesture.down(now:3.2)
check(exitGesture.up(now:3.3) == .cancel,"another short tap cannot become a double-click commit")
exitGesture.down(now:4)
check(exitGesture.up(now:4.6) == .commit,"late timer still commits a qualified hold exactly once on release")
check(exitGesture.up(now:4.7) == .none,"duplicate release is inert")
exitGesture.down(now:5);exitGesture.reset()
check(!exitGesture.commitIfHeld(now:6) && !exitGesture.pending,"teardown cancels the hold")
// A quick vertical nudge is one step after rest, not one per sample.
for sign in [-1.0,1.0] {
 var n=WandReviewNavigation();var total:Int32=0
 for i in 1...5 {total+=n.sample(dx:0.03,dy:sign*0.5,now:Double(i)*0.03)}
 check(total==0,"ambiguous moving stroke waits for its endpoint")
 total+=n.sample(dx:0,dy:0,now:0.3)
 check(total==Int32(sign),"quick vertical nudge moves exactly one item")
 for i in 1...10 {total+=n.sample(dx:0,dy:0,now:0.3+Double(i)*0.03)}
 check(total==Int32(sign),"rest does not repeat the nudge")
}
var nudges=WandReviewNavigation(),noise:Int32=0
for i in 1...12 {noise+=nudges.sample(dx:0.005,dy:0.008,now:Double(i)*0.03)}
check(noise==0,"noise never becomes a nudge")
var diagonal=WandReviewNavigation(),diagonalSteps:Int32=0
for i in 1...5 {diagonalSteps+=diagonal.sample(dx:0.5,dy:0.5,now:Double(i)*0.03)}
diagonalSteps+=diagonal.sample(dx:0,dy:0,now:0.3)
check(diagonalSteps==0,"diagonal sweep is not an ambiguous up/down nudge")
for sign in [-1.0,1.0] {
 var nav=WandReviewNavigation(),px=8.0,py=0.0,total:Int32=0,time=1.0
 for i in 1...240 {let angle=sign*Double(i)*Double.pi/60,xx=cos(angle)*8,yy=sin(angle)*8;time+=0.03;total+=nav.sample(dx:xx-px,dy:yy-py,now:time);px=xx;py=yy}
 check(sign>0 ? total>12:total < -12,"hybrid navigation preserves circle direction and ratchets")
 check(nav.sample(dx:0,dy:0,now:time+0.15)==0,"circle endpoint cannot add an extra nudge")
 for i in 1...5 {_=nav.sample(dx:0,dy:0.5,now:time+0.2+Double(i)*0.03)}
 check(nav.sample(dx:0,dy:0,now:time+0.5)==1,"pause after circling permits down-one again")
}

// Tiny loops are quantised like @NAV and tested through the actual hybrid router.
for radius in [0.15,0.3,0.6,8.0] {
 for sign in [-1.0,1.0] {
  for samples in [24,40,80] {
   var nav=WandReviewNavigation(),total:Int32=0
   var px=radius,py=0.0,time=10.0
   for i in 1...samples*4 {
    let a=sign*Double(i)*2*Double.pi/Double(samples)
    let xx=(cos(a)*radius*1000).rounded()/1000,yy=(sin(a)*radius*1000).rounded()/1000
    time+=1.0/Double(samples)
    total+=nav.sample(dx:xx-px,dy:yy-py,now:time);px=xx;py=yy
   }
   check(Double(total)*sign>=2,"micro review circle radius \(radius), samples \(samples), winding \(sign)")
   check(nav.sample(dx:0,dy:0,now:time+0.15)==0,"tiny circle cannot finish with an extra nudge")
  }
 }
}
// Bounded jitter, straight creep and alternating switch impulses are not loops.
for pattern in 0...2 {
 var nav=WandReviewNavigation(),total:Int32=0,px=0.0,py=0.0
 for i in 1...2000 {
  let xx=pattern==0 ? 0.025*sin(Double(i)*0.71) : (pattern==1 ? Double(i)*0.004 : (i%2==0 ? 0.045:-0.045))
  let yy=pattern==0 ? 0.025*cos(Double(i)*0.93) : (pattern==1 ? Double(i)*0.002 : (i%2==0 ? 0.015:-0.015))
  total+=nav.sample(dx:xx-px,dy:yy-py,now:20+Double(i)*0.03);px=xx;py=yy
 }
 check(total==0,"jitter or straight creep does not produce review steps \(pattern)")
}
// A valid circle must not lend its gain to later stationary wobble.
var afterCircle=WandReviewNavigation(),cx=8.0,cy=0.0,ct=100.0
for i in 1...160 {let a=Double(i)*Double.pi/40,xx=8*cos(a),yy=8*sin(a);ct+=0.025;_=afterCircle.sample(dx:xx-cx,dy:yy-cy,now:ct);cx=xx;cy=yy}
var afterNoise:Int32=0;cx=0.025;cy=0
for i in 1...1000 {let a=Double(i)*0.5,xx=0.025*cos(a),yy=0.025*sin(a);ct+=0.025;afterNoise+=afterCircle.sample(dx:xx-cx,dy:yy-cy,now:ct);cx=xx;cy=yy}
check(afterNoise==0,"small wobble after a real circle cannot inherit amplified gain")
// Ordinary circles retain their prior ratchet count, without an overall gain change.
check(circle(1).reduce(0,+)==20,"normal eight-degree review circles retain their measured 20 ratchets")
for radius in [0.1,0.2,0.4] {
 for sign in [-1.0,1.0] {
  let held=WandHeldScroll();held.begin(now:30)
  var time=30.23,total:Int32=0
  for _ in 0..<15 {time+=0.02;total+=held.sample(y:sign*1.2,dt:0.02,now:time)}
  for i in 1...300 {
   let a=Double(i)*2*Double.pi/25
   time+=0.02
   total+=held.sample(x:radius*4*Double.pi*sin(a),y:sign*radius*4*Double.pi*cos(a),dt:0.02,now:time)
  }
  check(held.circular && Double(total)*sign>0,"held micro circle radius \(radius), direction \(sign)")
  _=held.end(now:time+0.02)
  check(held.sample(x:1,y:1,dt:0.02)==0,"release stops tiny-circle scroll")
 }
}
let quiet=WandHeldScroll();quiet.begin(now:50)
var quietOutput:Int32=0
for i in 1...2000 {quietOutput+=quiet.sample(x:0.8*sin(Double(i)),y:0.8*cos(Double(i)),dt:0.02,now:50.3+Double(i)*0.02)}
check(quietOutput==0 && !quiet.circular,"quiet calibrated gyro noise does not scroll")
if failures>0{exit(1)};print("PASS existing controls and micro circles")
