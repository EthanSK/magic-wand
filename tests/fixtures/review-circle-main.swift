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
check(g.endDetents(commit:true).last?.phase=="finish","exit finishes existing selection")
g.beginDetents(mode:"files",now:6);check(g.detents(-1,now:7).allSatisfy{$0.mode=="files"&&$0.direction=="previous"},"whole-file contract")
check(g.cancel().last?.phase=="cancel","focus loss cancels")
if failures>0{exit(1)};print("PASS independent circles and Better Git lifecycle")
