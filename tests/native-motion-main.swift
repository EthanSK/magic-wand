import Foundation
let filter=WandMotionFilter()
let config:[Double]=[0,0,86.4,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,-1]
precondition(filter.configure(config))
precondition(!filter.configure([Double.nan]))
precondition(filter.sample(rawX:40000,rawY:0,microseconds:10000,held:false,resetState:false)==nil)
let rows=try JSONDecoder().decode([[Int]].self,from:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1])))
var totalX=0,totalY=0,expectedX=0,expectedY=0
for (index,r) in rows.enumerated(){
 let s=filter.sample(rawX:r[1],rawY:r[2],microseconds:r[0],held:r[3]==1,resetState:r[4]==1)!
 precondition(abs(s.x-r[5])<=1 && abs(s.y-r[6])<=1,"sample \(index) got \(s.x),\(s.y), expected \(r[5]),\(r[6])")
 precondition(s.intent == (r[7]==1),"intent \(index)")
 totalX+=s.x;totalY+=s.y;expectedX+=r[5];expectedY+=r[6]
}
precondition(abs(totalX-expectedX)<=2 && abs(totalY-expectedY)<=2)
print("PASS: \(rows.count) native motion samples match device filter, signs, precision gain and intent")

// Roll transforms angular rates before the existing filter, so gain and LOW
// sensitivity remain identical at quarter turns as well as intermediate rolls.
for angle in [0.0,Double.pi/6,Double.pi/2,Double.pi,Double.pi*1.5] {
    let reference=WandMotionFilter(),rotated=WandMotionFilter()
    precondition(reference.configure(config) && rotated.configure(config))
    rotated.orientationCompensation=true
    let c=cos(angle),s=sin(angle)
    rotated.observeGravity(x:s,y:0,z:c)
    var aX=0,aY=0,bX=0,bY=0
    for index in 0..<160 {
        let x=index<80 ? 1608.0:0,y=index<80 ? 0:1072.0
        let a=reference.sample(rawX:Int(x),rawY:Int(y),microseconds:20000,held:index>100,resetState:false)!
        let b=rotated.sample(rawX:Int((x*c-y*s).rounded()),rawY:Int((x*s+y*c).rounded()),microseconds:20000,held:index>100,resetState:false)!
        aX+=a.x;aY+=a.y;bX+=b.x;bY+=b.y
    }
    precondition(abs(aX-bX)<=2 && abs(aY-bY)<=2,"roll invariance \(angle): \(aX),\(aY) vs \(bX),\(bY)")
}
let guarded=WandMotionFilter(),plain=WandMotionFilter()
precondition(guarded.configure(config) && plain.configure(config))
guarded.observeGravity(x:1,y:0,z:0)
// Disabled flag ignores even a valid 90-degree gravity observation.
for _ in 0..<20 {
    let a=guarded.sample(rawX:1608,rawY:1072,microseconds:20000,held:false,resetState:false)!
    let b=plain.sample(rawX:1608,rawY:1072,microseconds:20000,held:false,resetState:false)!
    precondition(a.x==b.x && a.y==b.y)
}
guarded.orientationCompensation=true;guarded.reset()
for gravity in [(0.0,1.0,0.0),(Double.nan,0.0,1.0),(5.0,0.0,0.0)] {
    guarded.observeGravity(x:gravity.0,y:gravity.1,z:gravity.2)
}
let stable=WandMotionFilter();precondition(stable.configure(config));stable.orientationCompensation=true
stable.observeGravity(x:1,y:0,z:0)
for _ in 0..<50 {
    let a=guarded.sample(rawX:0,rawY:1608,microseconds:20000,held:false,resetState:false)!
    let b=stable.sample(rawX:0,rawY:1608,microseconds:20000,held:false,resetState:false)!
    precondition(a.x==b.x && a.y==b.y,"invalid gravity must retain previous usable basis")
}
for index in 0..<100 {
    stable.reset();stable.observeGravity(x:sin(Double(index)),y:0,z:cos(Double(index)))
    let a=stable.sample(rawX:0,rawY:0,microseconds:20000,held:false,resetState:false)!
    precondition(a.x==0 && a.y==0,"gravity changes alone cannot move cursor")
}
print("PASS: roll invariance, flag-off equivalence, gravity guards and stationary cursor")
