import Foundation
func filter()->WandMotionFilter {let f=WandMotionFilter();precondition(f.configure([0,0,100,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,1]));f.path = .direct;return f}
let normal=filter(),shot=filter(),beforeClick=filter();normal.holdAfterAutomaticClick();shot.holdAfterAutomaticClick()
var a=0,b=0,c=0
for n in 0..<208 {let q=Double(n)*2*Double.pi/26;let x=Int(0.6*sin(q)*134),y=Int(0.5*cos(q)*134)
let p=normal.sample(rawX:x,rawY:y,microseconds:9615,held:false,resetState:false)!
let s=shot.sample(rawX:x,rawY:y,microseconds:9615,held:false,resetState:false,applyStillness:false)!
let fresh=beforeClick.sample(rawX:x,rawY:y,microseconds:9615,held:false,resetState:false)!
a+=abs(p.x)+abs(p.y);b+=abs(s.x)+abs(s.y);c+=abs(fresh.x)+abs(fresh.y)}
precondition(a==0 && b>10,"screenshot bypasses ordinary rest output gate")
precondition(c<=2 && beforeClick.restingAfterClick,"balanced noise settles before any click, after initial evidence")
precondition(!shot.restingAfterClick,"screenshot does not inherit or arm rest")
print("PASS: native screenshot input bypasses rest; normal resting pointer stays fixed")

for step in [0.009615,0.01923,0.025,0.030,0.033333,0.050] {
 var s=WandPostClickStillness();s.arm();var elapsed=0.0,allowed=false
 while elapsed<0.061 {
  elapsed+=step
  allowed=s.permits(x:0.7,y:0,seconds:step,fastSpeed:2)
  if allowed {break}
 }
 precondition(allowed && elapsed<=0.060001,"tiny restart exceeded60ms at cadence \(step): \(elapsed)")
}
print("PASS: tiny restart stays within60ms across normal and merged report cadences")
