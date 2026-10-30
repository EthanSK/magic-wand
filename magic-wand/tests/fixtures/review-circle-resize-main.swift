import Foundation
// Review gesture contract for the default classifier (WandReviewNavigation).
// Post-NAV inputs: these are the angular deltas the receiver passes on, in degrees,
// with screen y pointing down (clockwise = next = +1). Ethan's contract:
// north->east NEXT; east->north (including the same arc straight back) PREVIOUS;
// north->west PREVIOUS; one step per rough corner; four per loop at any radius;
// a straight up/down about-face is not winding. Device-model traces at the end
// are synthetic (dead zone, quantisation, tremor), not captures of Ethan's hand.
var failures=0
func check(_ ok:Bool,_ name:String){if !ok {print("FAIL",name);failures+=1}}

struct Feed {
    var nav=WandReviewNavigation()
    var t=1.0,x=0.0,y=0.0
    var steps:[Int32]=[],times:[Double]=[],points:[(Double,Double)]=[]
    // Every path is drawn in a rotated frame: the wand may start from any pose.
    var angle=0.0
    init(angle:Double=0,start:(Double,Double)=(0,0)){
        self.angle=angle;let p=rotate(start);x=p.0;y=p.1
        // A short still lead-in, as the receiver streams NAV while review is selected.
        hold(0.3)
    }
    func rotate(_ p:(Double,Double))->(Double,Double){(p.0*cos(angle)-p.1*sin(angle),p.0*sin(angle)+p.1*cos(angle))}
    mutating func packet(_ p:(Double,Double),dt:Double=0.03,sameTime:Bool=false){
        let q=rotate(p)
        if !sameTime {t+=dt}
        let s=nav.sample(dx:q.0-x,dy:q.1-y,now:t);x=q.0;y=q.1
        if s != 0 {for _ in 0..<abs(Int(s)) {steps.append(s>0 ? 1:-1);times.append(t);points.append(p)}}
    }
    mutating func hold(_ seconds:Double){let n=Int((seconds/0.03).rounded());for _ in 0..<max(1,n) {t+=0.03;let s=nav.sample(dx:0,dy:0,now:t);if s != 0 {steps.append(s);times.append(t);points.append((Double.nan,Double.nan))}}}
    /// Arc about `c` from angle a0 to a1 (radians, screen coordinates) in n packets over d seconds.
    mutating func arc(_ c:(Double,Double),_ r:Double,_ a0:Double,_ a1:Double,packets n:Int=30,seconds d:Double=0.9){
        for i in 1...n {let a=a0+(a1-a0)*Double(i)/Double(n);packet((c.0+r*cos(a),c.1+r*sin(a)),dt:d/Double(n))}
    }
    mutating func line(_ from:(Double,Double),_ to:(Double,Double),packets n:Int=12,seconds d:Double=0.3){
        for i in 1...n {let f=Double(i)/Double(n);packet((from.0+(to.0-from.0)*f,from.1+(to.1-from.1)*f),dt:d/Double(n))}
    }
}

for sign in [1.0,-1.0] {for radius in [0.5,1.0,2.0,8.0] {
 var f=Feed(start:(8,0));f.arc((0,0),8,0,sign*2*Double.pi,packets:240,seconds:7.2);f.hold(0.8)
 var before=f.steps.count
 for loop in 0..<3 {
  f.arc((8-radius,0),radius,-sign*Double(loop)*2*Double.pi,-sign*Double(loop+1)*2*Double.pi,packets:240,seconds:7.2)
  let emitted=Array(f.steps.dropFirst(before));print("resize",sign,radius,"loop",loop,emitted);before=f.steps.count
  if loop>=1 {check(emitted==Array(repeating:Int32(-sign),count:4),"smaller circle must recover after size evidence")}
 }
}}
if failures>0 {exit(1)}
print("PASS: smaller circles relearn size and retain their real direction")
