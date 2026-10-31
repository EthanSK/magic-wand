// Ethan, 2026-10-31: "it's jumping around ... if I stop moving it to click,
// then that's when it happens." A passive capture showed macOS reporting the
// wand's own positions up to 0.37 s late; the old 0.25 s memory treated them
// as another mouse and moved the pointer back (often to the click spot).
// Real WandPointerOrigin, real call order: moved() for every posted wand move,
// begin() for a recenter warp, origin() for each receive batch and every
// stop-to-click press. Shapes and timings follow the capture; the private
// capture itself is not committed. Positions are screen points; times are
// seconds since startup.
import Foundation
var failures=0
func expect(_ ok:Bool,_ name:String,_ detail:@autoclosure ()->String=""){
    print((ok ? "ok   ":"FAIL ")+name+(ok ? "":"  "+detail()));if !ok {failures+=1}
}
func p(_ x:Double,_ y:Double)->CGPoint{CGPoint(x:x,y:y)}
/// A wand sweep of `steps` posts, `dt` apart, each `step` long, from `start`.
@discardableResult
func sweep(_ o:inout WandPointerOrigin,from start:CGPoint,step:CGPoint,steps:Int,t0:Double,dt:Double=0.0096)->[(CGPoint,Double)] {
    var at=start,out:[(CGPoint,Double)]=[]
    for k in 0..<steps {
        let t=t0+Double(k)*dt,next=CGPoint(x:at.x+step.x,y:at.y+step.y)
        o.moved(from:at,to:next,now:t);out.append((next,t));at=next
    }
    return out
}

// 1. Root's reproduction: macOS reports 120 at 0.31 s, 0.31 s after it was posted.
do {
    var o=WandPointerOrigin()
    o.moved(from:p(100,100),to:p(120,100),now:0)
    o.moved(from:p(120,100),to:p(140,100),now:0.1)
    o.moved(from:p(140,100),to:p(160,100),now:0.2)
    let got=o.origin(system:p(120,100),now:0.31)
    expect(got==p(160,100),"lagging own report older than 0.25 s continues from the newest point",String(describing:got))
}

// 2. The captured case (t=1186363.2443): the shown cursor had swept left to
//    1438,534; macOS reported 2095,551, posted 0.314 s earlier. The old code
//    started the next -19 px move there: a 657 px jump back.
do {
    var o=WandPointerOrigin()
    let path=sweep(&o,from:p(2114,551),step:p(-10.0,-0.25),steps:68,t0:0)
    let lagging=path.min{abs($0.1-(path.last!.1-0.314))<abs($1.1-(path.last!.1-0.314))}!.0
    let got=o.origin(system:lagging,now:path.last!.1+0.0096)
    expect(got==path.last!.0,"captured 0.31 s lag continues from the shown point, not \(lagging)",String(describing:got))
}

// 3. After a stop-to-click the click spot is reported late (captured 0.37 s):
//    the next move and the next press start from the newest point, never the click spot.
do {
    var o=WandPointerOrigin()
    let clickSpot=p(2925,573)
    sweep(&o,from:p(2800,573),step:p(5,0),steps:25,t0:0)            // arrive and stop
    let click=o.origin(system:clickSpot,now:0.45)                       // the quick click presses here
    expect(click==clickSpot,"the click presses at the shown stop point")
    let away=sweep(&o,from:clickSpot,step:p(-20,-1),steps:20,t0:0.55)  // move off briskly
    var bad:[CGPoint]=[]
    for (k,report) in [clickSpot,p(2905,572),away[3].0,clickSpot].enumerated() {
        let got=o.origin(system:report,now:away.last!.1+0.01+Double(k)*0.01)
        if got != away.last!.0 {bad.append(got)}
    }
    expect(bad.isEmpty,"late reports of the click spot never move the pointer back to it",String(describing:bad))
}

// 4. No ping-pong: successive late reports from different parts of the history
//    (the captured flicking pattern) all resolve to the newest point.
do {
    var o=WandPointerOrigin()
    let a=sweep(&o,from:p(2095,551),step:p(-10,0),steps:40,t0:0)
    var seen=Set<String>()
    for (k,index) in [0,30,5,35,2,39].enumerated() {
        seen.insert("\(o.origin(system:a[index].0,now:0.4+Double(k)*0.012))")
    }
    expect(seen==["\(a.last!.0)"],"alternating late reports never alternate the origin",seen.joined(separator:" "))
}

// 5. Recenter (double press): the warp lands at the centre; moves posted just
//    before it can still be reported after it (captured t=1186331.53).
do {
    var o=WandPointerOrigin()
    let before=sweep(&o,from:p(2000,700),step:p(6,1),steps:20,t0:0)
    let centre=p(1720,720)
    o.begin(at:centre,now:0.2)
    expect(o.origin(system:before.last!.0,now:0.205)==centre,"during the settle window the centre wins")
    expect(o.origin(system:centre,now:0.21)==centre,"macOS reports the centre: the settle window ends")
    let after=sweep(&o,from:centre,step:p(4,1),steps:4,t0:0.215)
    let got=o.origin(system:before[18].0,now:0.26)
    expect(got==after.last!.0,"a queued pre-recenter move reported afterwards is lag, not a new position",String(describing:got))
    var physical=WandPointerOrigin()
    sweep(&physical,from:p(10,10),step:p(1,0),steps:3,t0:0)
    physical.begin(at:centre,now:1)
    expect(physical.origin(system:p(400,400),now:1.1)==centre,"a pre-warp foreign report during the settle keeps the centre (unchanged)")
}

// 6. Large and negative coordinates (displays left of and above the main one).
do {
    var o=WandPointerOrigin()
    let a=sweep(&o,from:p(-2550,-1430),step:p(9,7),steps:45,t0:0)
    let got=o.origin(system:a[2].0,now:0.75)
    expect(got==a.last!.0,"negative-coordinate lag continues from the newest point",String(describing:got))
    var wide=WandPointerOrigin()
    let b=sweep(&wide,from:p(7600,2100),step:p(-12,0),steps:45,t0:0)
    expect(wide.origin(system:b[0].0,now:0.8)==b.last!.0,"large-coordinate lag continues from the newest point")
}

// 7. A genuinely foreign position (unobserved physical mouse, another app's warp)
//    is still adopted at once, and the wand continues from it.
do {
    var o=WandPointerOrigin()
    sweep(&o,from:p(500,500),step:p(3,0),steps:10,t0:0)
    let foreign=p(1200,900)
    expect(o.origin(system:foreign,now:0.2)==foreign,"a non-wand position is adopted immediately")
    o.moved(from:foreign,to:p(1205,900),now:0.21)
    expect(o.origin(system:foreign,now:0.22)==p(1205,900),"lag after the handover continues from the new path")
}

// 8. Idle: after a real pause the system cursor is trusted again.
do {
    var o=WandPointerOrigin()
    let a=sweep(&o,from:p(100,100),step:p(2,0),steps:10,t0:0)
    expect(o.origin(system:a[1].0,now:a.last!.1+1.5)==a.last!.0,"a 1.5 s stall: a late own report is still lag")
    expect(o.origin(system:a[1].0,now:a.last!.1+WandPointerOrigin.horizon+0.1)==a[1].0,"after the idle time the system position is trusted")
}

// 9. Physical mouse handover, including moving back onto the wand's old path.
do {
    var o=WandPointerOrigin()
    let a=sweep(&o,from:p(300,300),step:p(10,0),steps:30,t0:0)
    o.externalMovement(at:a.last!.1+0.4,now:a.last!.1+0.41)      // the real mouse moves
    let backtrack=a[12].0                                          // exactly onto an old wand point
    expect(o.origin(system:backtrack,now:a.last!.1+0.42)==backtrack,"a physical mouse on the wand's old path is followed, not mistaken for lag")
    o.moved(from:backtrack,to:p(backtrack.x+4,backtrack.y),now:a.last!.1+0.45)
    expect(o.origin(system:backtrack,now:a.last!.1+0.46)==p(backtrack.x+4,backtrack.y),"the wand then continues from where the mouse left it")
}
// 10. Stale ordering: a late notification of mouse input older than the
//     wand's newest move does not discard that move.
do {
    var o=WandPointerOrigin()
    let a=sweep(&o,from:p(600,600),step:p(-8,0),steps:20,t0:10)
    o.externalMovement(at:a[5].1,now:a.last!.1+0.02)
    expect(o.origin(system:a[3].0,now:a.last!.1+0.03)==a.last!.0,"older external input cannot rewind the wand's newest move")
    o.externalMovement(at:28471.5,now:a.last!.1+0.04)           // a timestamp on another clock
    expect(o.origin(system:p(10,10),now:a.last!.1+0.05)==p(10,10) && o.count==0,"an implausible timestamp is treated as new input")
}
// 11. Bounded history during a long continuous stream, and its documented limit.
do {
    var o=WandPointerOrigin()
    let a=sweep(&o,from:p(0,0),step:p(1,1),steps:5000,t0:0,dt:0.0096)
    expect(o.count<=WandPointerOrigin.maximumTrail,"history stays bounded (\(o.count) ≤ \(WandPointerOrigin.maximumTrail))")
    expect(o.origin(system:a[a.count-900].0,now:a.last!.1+0.01)==a.last!.0,"a report 900 moves (8.6 s) late is still lag")
    expect(o.origin(system:a[10].0,now:a.last!.1+0.02)==a[10].0,"beyond the bound the system is trusted (documented limit)")
}
print(failures==0 ? "PASS origin scenarios":"\(failures) FAILED")
exit(failures==0 ? 0:1)
