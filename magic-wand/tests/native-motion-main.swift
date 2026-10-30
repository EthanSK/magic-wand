import Foundation
let filter=WandMotionFilter()
let config:[Double]=[0,0,86.4,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,-1]
precondition(filter.configure(config))
precondition(!filter.configure([Double.nan]))
// ±65535 Puck counts: the Sense's 500 deg/s range; a Puck never exceeds int16.
precondition(filter.sample(rawX:70000,rawY:0,microseconds:10000,held:false,resetState:false)==nil)
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

// Static world-space movement must retain the chosen gains as the grip rolls
// and the tip rises, including nonzero bias and the nonlinear speed curve.
do {
let config:[Double]=[83,-57,86.4,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,-1]
func counts(roll:Double,h:Double,v:Double,held:Bool,pitch:Double=0)->(Int,Int) {
 let f=WandMotionFilter();precondition(f.configure(config));f.orientationCompensation=true
 // Rotate physical gyro and gravity vectors about the wand's Y shaft.
 let c=cos(roll),s=sin(roll),p=cos(pitch)
 f.observeGravity(x:-s*p,y:sin(pitch),z:c*p)
 var x=0,y=0
 for _ in 0..<120 {
  let bodyZ=h*p*c+v*s,bodyX=v*c-h*p*s
  let r=f.sample(rawX:Int((bodyZ*134+config[0]).rounded()),rawY:Int((bodyX*134+config[1]).rounded()),microseconds:10000,held:held,resetState:false)!
  x+=r.x;y+=r.y
 }
 return (x,y)
}
var cases=0,maxError=0
for degrees in stride(from:0,through:345,by:15) {
 for pitch in [-60.0,0,60] {
  for held in [false,true] {
   for speed in [0.8,3,20] {
    for direction in [0.0,Double.pi/4,Double.pi/2] {
     let h=speed*cos(direction),v=speed*sin(direction)
     let a=counts(roll:0,h:h,v:v,held:held)
     let b=counts(roll:Double(degrees)*Double.pi/180,h:h,v:v,held:held,pitch:pitch*Double.pi/180)
     let error=max(abs(a.0-b.0),abs(a.1-b.1));maxError=max(maxError,error);cases+=1
     precondition(error<=2,"roll \(degrees), pitch \(pitch), held \(held), speed \(speed): \(a) != \(b)")
    }
   }
  }
 }
}
let highX=counts(roll:0,h:20,v:0,held:false).0
let highY=counts(roll:0,h:0,v:20,held:false).1
let lowX=counts(roll:0,h:20,v:0,held:true).0
precondition(abs(Double(highY)/Double(highX)-1.4)<0.002)
precondition(abs(Double(lowX)/Double(highX)-1.0/3)<0.002)
print("PASS \(cases) static-angle/speed/direction cases; max accumulated difference \(maxError) pointer counts")
print("Vertical/horizontal ratio:",Double(highY)/Double(highX),"held/high:",Double(lowX)/Double(highX))
// Above 60 degrees the correction is bounded; do not amplify pole noise without limit.
let pole=counts(roll:0,h:20,v:0,held:false,pitch:80*Double.pi/180)
precondition(abs(pole.0)<abs(highX),"near-vertical correction must stay bounded")
print("PASS: sensitivity stays bounded near vertical")
}

// Every angular route uses the very same basis as native pointer movement.
for signs in [(-1.0,-1.0),(-1.0,1.0),(1.0,-1.0),(1.0,1.0)] {
 for roll in [0.0,0.7,Double.pi/2,Double.pi,Double.pi*1.5] {
  for elevation in [0.0,0.4,Double.pi/3] {
   let f=WandMotionFilter();var c=config;c[11]=signs.0;c[12]=signs.1
   precondition(f.configure(c));f.orientationCompensation=true
   f.observeGravity(x:sin(roll)*cos(elevation),y:sin(elevation),z:cos(roll)*cos(elevation))
   for gain in [1.0,1.4] {
    var stream=WandAngularStream();let desired=(x:3.0,y:2.0)
    let a=desired.x*cos(elevation),b=desired.y
    let bodyX=a*cos(roll)-b*sin(roll),bodyY=a*sin(roll)+b*cos(roll)
    var rawX=0.0,rawY=0.0
    for _ in 0..<5 {rawX+=bodyX*signs.0*gain;rawY+=bodyY*signs.1}
    let got=stream.update(x:rawX,y:rawY,using:f,horizontalGain:gain)
    precondition(abs(got.x-15*signs.0*gain)<0.00001 && abs(got.y-10*signs.1)<0.00001,"angular stream invariance")
    f.observeGravity(x:sin(roll+0.2)*cos(elevation),y:sin(elevation),z:cos(roll+0.2)*cos(elevation))
    let still=stream.update(x:rawX,y:rawY,using:f,horizontalGain:gain)
    precondition(still.x==got.x && still.y==got.y,"changing wrist angle must not rotate accumulated travel")
    stream.reset();let zero=stream.update(x:0,y:0,using:f,horizontalGain:gain)
    precondition(zero.x==0 && zero.y==0)
    f.observeGravity(x:sin(roll)*cos(elevation),y:sin(elevation),z:cos(roll)*cos(elevation))
   }
  }
 }
}
print("PASS: shared HUD, operation and two-axis scroll transforms preserve gains, signs and stationary totals")

for speed in [0.0,0.2,1,3,10,20,80] {
 let high=WandMotionFilter(),low=WandMotionFilter()
 precondition(high.configure(config) && low.configure(config))
 var counts=0,precise=0.0,lowHigh=0.0,lowCounts=0
 for i in 0..<200 {
  let a=high.sample(rawX:Int(speed*134),rawY:0,microseconds:10000,held:false,resetState:i==0)!
  let b=low.sample(rawX:Int(speed*134),rawY:0,microseconds:10000,held:true,resetState:i==0)!
  counts+=a.x;precise+=a.highX;lowHigh+=b.highX;lowCounts+=b.x
 }
 precondition(abs(Double(counts)-precise)<1.00001)
 precondition(abs(precise-lowHigh)<0.000001,"HUD-button HIGH must not inherit mouse-button LOW")
 precondition(abs(Double(lowCounts)*3-precise)<3.00001)
}
print("PASS: shared unrounded HIGH output and unchanged LOW pointer gain")
