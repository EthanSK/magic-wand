import Foundation
// Ethan (2026-10-30): "when I'm doing it slowly clockwise, sometimes it jumps
// back instead of forth". Synthetic analogue of the private slow reference:
// slow clockwise loops (screen y down, so +turn is clockwise = next) that stop
// at a slow point, nudge ~0.25° and wobble ~0.2° before carrying on.
var t=0.0
var c=WandReviewCircle()
var steps:[(t:Double,s:Int32)]=[]
func feed(_ dx:Double,_ dy:Double,dt:Double=0.03) {t+=dt;let s=c.sample(dx:dx,dy:dy,now:t);if s != 0 {steps.append((t,s))}}
/// Loops of `radius` degrees, `seconds` per loop, sign +1 clockwise; 33 Hz packets.
var angle = -Double.pi/2
func loops(_ count:Double,radius:Double,seconds:Double,sign:Double) {
    let packets=Int(count*seconds/0.03),da=sign*2*Double.pi*0.03/seconds
    for _ in 0..<packets {
        let a0=angle,a1=angle+da;angle=a1
        feed(radius*(cos(a1)-cos(a0)),radius*(sin(a1)-sin(a0)))
    }
}
func still(_ seconds:Double) {for _ in 0..<Int(seconds/0.03) {feed(0,0)}}
func count(_ from:Double,_ sign:Int32)->Int {steps.filter{$0.t>=from && $0.s==sign}.count}

// 1. Slow clockwise, a near-stop, a nudge and sub-degree wobble, then clockwise again.
loops(2,radius:3,seconds:2.5,sign:1)
let beforeStop=steps.count
still(0.45)
for (dx,dy) in [(0.02,0.25),(0.03,0.025),(0.05,-0.012),(0.045,0.025),(0.01,0.03),(0.001,-0.008),(0,0),(-0.001,-0.02)] {feed(dx,dy)}
still(0.2)
let wobble=Array(steps.dropFirst(beforeStop))
precondition(!wobble.contains{$0.s<0},"a near-stop wobble mid-clockwise must not step previous: \(wobble)")
let resumeAt=t
loops(1.5,radius:3,seconds:2.5,sign:1)
precondition(count(resumeAt,1)>=4 && count(resumeAt,-1)==0,"slow clockwise keeps stepping next after the stop")
precondition(steps.prefix(beforeStop).allSatisfy{$0.s>0} && beforeStop>=6,"slow clockwise steps next")

// 2. A real reversal after the same kind of stop still steps previous promptly.
still(0.45)
let reverseAt=t
loops(1.5,radius:3,seconds:2.5,sign:-1)
let firstBack=steps.first{$0.t>=reverseAt && $0.s<0}
precondition(firstBack != nil && firstBack!.t-reverseAt<=1.2,"an intentional anticlockwise circle after a pause reverses within a quarter or so")
precondition(count(reverseAt,-1)>=4 && count(reverseAt,1)==0,"and keeps stepping previous")

// 3. Smaller, faster circles after a pause still count: the step rules already
// accept half the last gesture's size, and a pause must not change that.
still(0.45)
let smallAt=t
loops(3,radius:1.8,seconds:0.9,sign:-1)
precondition(count(smallAt,-1)>=9 && count(smallAt,1)==0,"smaller faster loops keep counting after a pause")

// 4. After a stop, wobble-sized "circles" against the known circle never step back.
still(0.45)
let tinyAt=t
loops(1,radius:0.15,seconds:0.8,sign:1)
still(0.45)
precondition(count(tinyAt,1)==0,"a 0.15 degree wobble loop is noise next to a 1.8 degree circle")
print("PASS: slow clockwise stop/wobble never steps back; real reversals and small loops still count")
