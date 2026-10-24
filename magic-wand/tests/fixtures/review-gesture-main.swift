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
let north = -Double.pi/2, east = 0.0, west = Double.pi
let poses=[0.0,0.5,2.4,4.4] // radians: the same gestures from arbitrary hand poses
func name(_ s:[Int32])->String{s.map{$0>0 ? "+":"-"}.joined()}

// 1. Quarter arcs and their reversals, at three sizes and any pose.
for r in [0.15,1.0,8.0] {
    for pose in poses {
        let tag="r\(r) pose \(pose)"
        var f=Feed(angle:pose,start:(0,-r));f.arc((0,0),r,north,east);f.hold(0.6)
        check(f.steps==[1],"north->east is one NEXT \(tag) got \(name(f.steps))")
        var g=Feed(angle:pose,start:(r,0));g.arc((0,0),r,east,north);g.hold(0.6)
        check(g.steps==[-1],"east->north is one PREVIOUS \(tag) got \(name(g.steps))")
        var w=Feed(angle:pose,start:(0,-r));w.arc((0,0),r,north,-Double.pi);w.hold(0.6)
        check(w.steps==[-1],"north->west is one PREVIOUS \(tag) got \(name(w.steps))")
        var back=Feed(angle:pose,start:(0,-r))
        back.arc((0,0),r,north,east);back.arc((0,0),r,east,north);back.arc((0,0),r,north,east);back.hold(0.6)
        check(back.steps==[1,-1,1],"the same arc straight back is PREVIOUS, then NEXT again \(tag) got \(name(back.steps))")
        var paused=Feed(angle:pose,start:(0,-r))
        paused.arc((0,0),r,north,east);paused.hold(0.8);paused.arc((0,0),r,east,north);paused.hold(0.6)
        check(paused.steps==[1,-1],"a reverse quarter after a pause is PREVIOUS \(tag) got \(name(paused.steps))")
    }
}
// The step lands during the arc, once most of the quarter has turned; never after it.
for (r,n,d) in [(0.15,8,0.3),(1.0,30,0.9),(8.0,80,3.0)] {
    var f=Feed(start:(0,-r));let begin=f.t;f.arc((0,0),r,north,east,packets:n,seconds:d);let end=f.t;f.hold(0.6)
    check(f.steps==[1] && f.times[0]>begin+0.45*d && f.times[0]<=end+1e-9,"quarter step timing r\(r) n\(n) at \(f.times.first.map{($0-begin)/d} ?? -1)")
}

// 2. Straight about-faces are not winding: nods, rebounds and turnaround hooks.
for a in [0.3,1.0,4.0] {
    for pose in poses {
        var nod=Feed(angle:pose)
        for _ in 0..<3 {nod.line((0,0),(0,-a));nod.line((0,-a),(0,0))}
        nod.hold(0.6)
        check(nod.steps.isEmpty,"straight up/down is not a review gesture a\(a) pose \(pose) got \(name(nod.steps))")
        var hook=Feed(angle:pose)
        hook.line((0,0),(0,-a));hook.line((0,-a),(a*0.1,-a*0.97),packets:3,seconds:0.06);hook.line((a*0.1,-a*0.97),(0,0));hook.hold(0.6)
        check(hook.steps.isEmpty,"a small hook at a turnaround is not a corner a\(a) pose \(pose) got \(name(hook.steps))")
    }
}

// 3. Single corners, and what a return after them may and may not do.
for a in [0.3,1.0,4.0] {
    for pose in poses {
        let tag="a\(a) pose \(pose)"
        var right=Feed(angle:pose);right.line((0,0),(0,-a));right.line((0,-a),(a,-a));right.hold(0.6)
        check(right.steps==[1],"up then right is one NEXT \(tag) got \(name(right.steps))")
        var left=Feed(angle:pose);left.line((0,0),(0,-a));left.line((0,-a),(-a,-a));left.hold(0.6)
        check(left.steps==[-1],"up then left is one PREVIOUS \(tag) got \(name(left.steps))")
        var straightBack=Feed(angle:pose)
        straightBack.line((0,0),(0,-a));straightBack.line((0,-a),(a,-a));straightBack.line((a,-a),(0,-a));straightBack.hold(0.6)
        check(straightBack.steps==[1],"a straight return along the last leg adds nothing \(tag) got \(name(straightBack.steps))")
        var diagonal=Feed(angle:pose)
        diagonal.line((0,0),(0,-a));diagonal.line((0,-a),(a,-a));diagonal.line((a,-a),(0,0));diagonal.hold(0.6)
        check(diagonal.steps==[1],"a straight diagonal reset to the start adds nothing \(tag) got \(name(diagonal.steps))")
        var retrace=Feed(angle:pose)
        retrace.line((0,0),(0,-a));retrace.line((0,-a),(a,-a));retrace.line((a,-a),(0,-a));retrace.line((0,-a),(0,0));retrace.hold(0.6)
        check(retrace.steps==[1,-1],"retracing both legs is the reverse corner: NEXT then PREVIOUS \(tag) got \(name(retrace.steps))")
    }
}

// 4. Loops, squares and diamonds: four evenly spaced steps per revolution.
for r in [0.15,1.0,8.0,32.0] {
    for sign in [1.0,-1.0] {
        for (packets,seconds) in [(36,1.2),(120,3.0)] {
            var f=Feed(start:(r,0))
            for _ in 0..<3 {f.arc((0,0),r,0,sign*2*Double.pi,packets:packets,seconds:seconds)}
            f.hold(0.6)
            check(f.steps==Array(repeating:Int32(sign),count:12),"three loops are twelve steps r\(r) sign \(sign) packets \(packets) got \(f.steps.count) \(name(f.steps))")
            let angles=f.points.map{atan2($0.1,$0.0)}
            var even=true
            for i in 1..<angles.count {var d=(angles[i]-angles[i-1])*sign;while d<0 {d+=2*Double.pi};if abs(d-Double.pi/2)>0.35 {even=false}}
            check(even,"loop steps are a quarter-turn apart r\(r) sign \(sign) packets \(packets)")
        }
    }
}
for a in [0.3,2.0] {
    for sign in [1.0,-1.0] {
        for perEdge in [1,6] {
            let square:[(Double,Double)]=[(0,-a),(sign*a,-a),(sign*a,0),(0,0)]
            var s=Feed(),p=(0.0,0.0)
            for _ in 0..<2 {for q in square {s.line(p,q,packets:perEdge,seconds:0.25);p=q}}
            s.hold(0.6)
            check(s.steps==Array(repeating:Int32(sign),count:7),"two square loops from a corner are seven corners a\(a) sign \(sign) per edge \(perEdge) got \(name(s.steps))")
            let diamond:[(Double,Double)]=[(sign*a,a),(0,2*a),(-sign*a,a),(0,0)]
            var d=Feed();p=(0,0)
            for _ in 0..<2 {for q in diamond {d.line(p,q,packets:perEdge,seconds:0.25);p=q}}
            d.hold(0.6)
            check(d.steps==Array(repeating:Int32(sign),count:7),"two diamond loops from a vertex are seven corners a\(a) sign \(sign) per edge \(perEdge) got \(name(d.steps))")
        }
    }
}

// 5. Slow and sparse intentional motion: no minimum speed.
for sign in [1.0,-1.0] {
    var slow=Feed(start:(0,-0.15));slow.arc((0,0),0.15,north,north+sign*Double.pi/2,packets:130,seconds:3.9);slow.hold(0.6)
    check(slow.steps==[Int32(sign)],"a 0.15-degree quarter over four seconds is one step sign \(sign) got \(name(slow.steps))")
    var sparse=Feed(start:(0,-0.3));sparse.arc((0,0),0.3,north,north+sign*Double.pi/2,packets:8,seconds:3);sparse.hold(0.6)
    check(sparse.steps==[Int32(sign)],"eight packets over three seconds are one step sign \(sign) got \(name(sparse.steps))")
    var crawl=Feed(start:(0.5,0));crawl.arc((0,0),0.5,0,sign*2*Double.pi,packets:400,seconds:12);crawl.hold(0.6)
    check(crawl.steps==Array(repeating:Int32(sign),count:4),"a twelve-second loop is four steps sign \(sign) got \(name(crawl.steps))")
}

// 6. Repeated isolated flicks from different poses, with rests between them.
do {
    var f=Feed(start:(0,-1))
    f.arc((0,0),1,north,east,packets:8,seconds:0.2);f.hold(0.6)
    f.arc((1,1),1,north,east,packets:8,seconds:0.2);f.hold(0.6)       // continues from where the wand stopped
    f.arc((1.5,3.5),1.5,-2.0,-2.0+Double.pi/2,packets:8,seconds:0.2);f.hold(0.6)
    check(f.steps==[1,1,1],"three separate clockwise flicks are three NEXT got \(name(f.steps))")
    f.arc((2.1,4.6),1,-0.4,-0.4-Double.pi/2,packets:8,seconds:0.2);f.hold(0.6)
    check(f.steps==[1,1,1,-1],"an anticlockwise flick afterwards is one PREVIOUS got \(name(f.steps))")
    var r=Feed(start:(0,-1))
    for _ in 0..<3 {r.arc((0,0),1,north,east,packets:8,seconds:0.2);r.arc((0,0),1,east,north,packets:8,seconds:0.2)}
    r.hold(0.6)
    check(r.steps==[1,-1,1,-1,1,-1],"flick and immediate curved return, three times got \(name(r.steps))")
}

// 7. Bluetooth bunching changes timing only, not the count.
do {
    var f=Feed(start:(0,-1))
    for i in 1...24 {let a=north+Double.pi/2*Double(i)/24;f.packet((cos(a),sin(a)),dt:0.09,sameTime:i%3 != 0)}
    f.hold(0.6)
    check(f.steps==[1],"bunched packets give the same single step got \(name(f.steps))")
}

// 8. Noise: still tremor, straight jittery strokes and wobble after a loop.
struct LCG {var s:UInt64;mutating func next()->Double{s=s&*6364136223846793005&+1442695040888963407;return Double(s>>11)/Double(1<<53)-0.5}}
do {
    var rng=LCG(s:7),f=Feed()
    for _ in 0..<330 {f.packet((0.03*rng.next(),0.03*rng.next()))}
    check(f.steps.isEmpty,"ten seconds of still tremor got \(name(f.steps))")
    var line=Feed()
    for i in 1...200 {line.packet((Double(i)*0.01+0.02*rng.next(),0.02*rng.next()))}
    line.hold(0.6)
    check(line.steps.isEmpty,"a jittery straight stroke got \(name(line.steps))")
    var after=Feed(start:(1,0));after.arc((0,0),1,0,2*Double.pi,packets:60,seconds:1.5)
    let loop=after.steps.count
    for _ in 0..<300 {after.packet((1+0.025*rng.next(),0.025*rng.next()))}
    check(loop==4 && after.steps.count==4,"wobble after a loop adds nothing got \(name(after.steps))")
}

// 9. Device-model traces: 104 Hz rates through the firmware's 1.2 deg/s radial dead
// zone, 30 ms NAV reports rounded to 0.001 degree, 9 Hz tremor and roll jitter.
func device(_ path:(Double)->(Double,Double),seconds:Double,seed:UInt64,tremor:Double)->[(Double,Double,Double)] {
    var rng=LCG(s:seed),hx=0.0,hy=0.0,last=path(0),time=0.0,next=0.03,reported=(0.0,0.0),out:[(Double,Double,Double)]=[]
    let phase=Double(seed%7)
    while time<seconds+0.6 {
        time+=1/104.0
        let p=path(min(time,seconds))
        let q=(p.0+tremor*sin(2*Double.pi*9.3*time+phase),p.1+tremor*0.8*sin(2*Double.pi*10.5*time))
        var vx=(q.0-last.0)*104+0.35*rng.next(),vy=(q.1-last.1)*104+0.35*rng.next();last=q
        let m=hypot(vx,vy),keep=m<=1.2 ? 0:(m-1.2)/m;vx*=keep;vy*=keep;hx+=vx/104;hy+=vy/104
        if time>=next {
            next+=0.03
            let rx=(hx*1000).rounded()/1000,ry=(hy*1000).rounded()/1000,roll=0.05*rng.next()
            let dx=rx-reported.0,dy=ry-reported.1;reported=(rx,ry)
            out.append((dx*cos(roll)-dy*sin(roll),dx*sin(roll)+dy*cos(roll),time))
        }
    }
    return out
}
func smooth(_ u:Double)->Double {let t=max(0,min(1,u));return t*t*t*(10-15*t+6*t*t)}
func play(_ packets:[(Double,Double,Double)])->[Int32] {
    var nav=WandReviewNavigation(),out:[Int32]=[]
    for p in packets {let s=nav.sample(dx:p.0,dy:p.1,now:100+p.2);if s != 0 {out.append(s)}}
    return out
}
for (tremor,seed) in [(0.0,1 as UInt64),(0.02,3),(0.04,5)] {
    let tag="tremor \(tremor)"
    let hold=0.4
    let flick=play(device({t in let a=north+Double.pi/2*smooth((t-hold)/0.25);return (cos(a),sin(a))},seconds:hold+0.25,seed:seed,tremor:tremor))
    check(flick==[1],"device flick north->east \(tag) got \(name(flick))")
    let flickBack=play(device({t in let u=t<hold+0.25 ? smooth((t-hold)/0.25):1-smooth((t-hold-0.25)/0.25);let a=north+Double.pi/2*u;return (cos(a),sin(a))},seconds:hold+0.5,seed:seed,tremor:tremor))
    check(flickBack==[1,-1],"device flick and curved return \(tag) got \(name(flickBack))")
    let nod=play(device({t in let u=t<hold ? 0:sin(Double.pi*min(1,(t-hold)/0.4));return (0,-1.5*u)},seconds:hold+0.4,seed:seed,tremor:tremor))
    check(nod.isEmpty,"device nod \(tag) got \(name(nod))")
    let loops=play(device({t in let a=2*Double.pi*2*max(0,t-hold)/2.4;return (cos(a),sin(a))},seconds:hold+2.4,seed:seed,tremor:tremor))
    check(loops==Array(repeating:1,count:8),"device two loops \(tag) got \(name(loops))")
    let corner=play(device({t in let u=smooth((t-hold)/0.2),v=smooth((t-hold-0.2)/0.2),w=smooth((t-hold-0.4)/0.25);return (1.2*v-1.2*w,-1.2*u+1.2*w)},seconds:hold+0.65,seed:seed,tremor:tremor))
    check(corner==[1],"device corner then straight diagonal reset \(tag) got \(name(corner))")
}

// 10. Diagnostics and options.
do {
    var n=WandReviewNavigation()
    check(!n.useAxisGestures,"the nod/shake option stays off by default")
    var rng=LCG(s:11)
    for i in 1...120 {_=n.sample(dx:0.02*rng.next(),dy:0.02*rng.next(),now:Double(i)*0.03)}
    let learned=n.snapshot.noise
    n.reset()
    check(n.snapshot.noise==learned && learned>0,"reset keeps the learned hand noise")
    var seeded=WandReviewNavigation();seeded.restoreNoise(jitter:0.01,wobble:0.004)
    check(abs(seeded.snapshot.jitter-0.01)<1e-12 && abs(seeded.snapshot.wobble-0.004)<1e-12,"replay can seed learned noise")
    let s=n.snapshot
    _=(s.event.rawValue,s.active,s.turn,s.effective,s.scale,s.segment,s.pending,s.direction,s.runSteps,s.credit,s.sideways,s.paused)
}

if failures>0 {exit(1)}
print("PASS review gestures: reversible quarters, corners, loops, slow, sparse, poses, noise and device-model traces")
