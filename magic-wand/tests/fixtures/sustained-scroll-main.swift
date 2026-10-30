import Foundation

// Control V3 held-scroll motion profiles, run through sustained-scroll-sim.swift on the
// actual WandHeldScroll controller. The hand motion is synthetic: these checks are
// deterministic regression evidence, not physical acceptance of the wand's feel.

var failures:[String]=[]
func check(_ ok:Bool,_ name:String,_ detail:@autoclosure()->String=""){if !ok {failures.append(name+(detail().isEmpty ? "" : ": "+detail()))}}

/// Held still after the stroke: one representative speed, on one axis, in one direction.
func expectSustained(_ trace:Trace,_ name:String,from a:Double,to b:Double,_ range:ClosedRange<Double>,sign:Double) {
    let mid=(a+b)/2,early=trace.rate(a,mid),late=trace.rate(mid,b)
    check(range.contains(sign*early.p),name+" representative speed","\(f(sign*early.p)) not in \(f(range.lowerBound))...\(f(range.upperBound))")
    // Whole wheel lines: allow one line of rounding between the halves, else 12%.
    let earlyLines=trace.lines(a,mid).p,lateLines=trace.lines(mid,b).p
    check(abs(earlyLines-lateLines)<=max(1,0.12*max(abs(earlyLines),abs(lateLines))),name+" stable while still","\(f(early.p)) then \(f(late.p))")
    check(trace.lines(a,b).s==0,name+" no other-axis lines while still","\(trace.lines(a,b).s)")
}

// 1. Press, then a deliberate stroke, then hold still. Follow mode hides the first 220 ms.
each {axis,sign,seed,label in
    let hand=Hand(parts:[.rest(0.35),stroke(5,0.3),.rest(2.4)])
    let trace=simulate(hand,axis:axis,sign:sign,seed:seed)
    let name="stroke then still ("+label+")"
    expectSustained(trace,name,from:0.85,to:3.05,representative(5,0.3),sign:sign)
    check(trace.ticks.allSatisfy{Double($0.p)*sign>=0},name+" never scrolls the wrong way")
    check(trace.total.s==0,name+" single axis","\(trace.total.s)")
    let start=trace.first({p,_ in p != 0}) ?? 99
    check(start<=0.35+0.2,name+" responds during the stroke","first line \(f(start*1000)) ms")
}
// 2. Slow onset, main stroke, deceleration: the main stroke sets the speed.
each {axis,sign,seed,label in
    let hand=Hand(parts:[.rest(0.3),.creep(p:3,s:0,seconds:0.25),stroke(6,0.3),.rest(2.0)])
    let trace=simulate(hand,axis:axis,sign:sign,seed:seed)
    expectSustained(trace,"slow onset ("+label+")",from:1.05,to:2.85,representative(6,0.3),sign:sign)
}
// 3. Press and drag at once from mouse-off: samples before the 220 ms decision count,
//    but nothing scrolls until the hold is qualified.
each {axis,sign,seed,label in
    var delivery=Delivery();delivery.first=0.07
    let hand=Hand(parts:[.rest(0.03),stroke(5,0.3),.rest(2.0)])
    let trace=simulate(hand,delivery,axis:axis,sign:sign,seed:seed)
    let name="press and drag ("+label+")"
    check(trace.lines(0,0.22).p==0 && trace.lines(0,0.22).s==0,name+" waits for the hold decision")
    let start=trace.first({p,_ in p != 0}) ?? 99
    check(start<=0.3,name+" starts at the hold decision","first line \(f(start*1000)) ms")
    expectSustained(trace,name,from:0.6,to:2.33,representative(5,0.3),sign:sign)
}
// 4. The small opposite bounce at the end of a stroke is not a reversal.
for (share,seconds) in [(0.2,0.15),(0.3,0.18)] {
    each {axis,sign,seed,label in
        let hand=Hand(parts:[.rest(0.3),stroke(6,0.3),stroke(-6*share,seconds),.rest(2.0)])
        let trace=simulate(hand,axis:axis,sign:sign,seed:seed)
        let name="recoil \(Int(share*100))% ("+label+")"
        check(trace.ticks.allSatisfy{Double($0.p)*sign>=0},name+" never reverses")
        expectSustained(trace,name,from:1.0,to:2.75,representative(6,0.3),sign:sign)
    }
}
// 5. Reverse after a pause, without releasing.
each {axis,sign,seed,label in
    let hand=Hand(parts:[.rest(0.3),stroke(5,0.3),.rest(1.0),stroke(-5,0.3),.rest(1.5)])
    let trace=simulate(hand,axis:axis,sign:sign,seed:seed)
    let name="reverse after pause ("+label+")"
    expectSustained(trace,name+" before",from:0.8,to:1.55,representative(5,0.3),sign:sign)
    let reverse=trace.first({p,_ in Double(p)*sign<0},after:1.6) ?? 99
    check(reverse<=1.6+0.2,name+" reverses promptly","\(f((reverse-1.6)*1000)) ms")
    check(trace.ticks.allSatisfy{$0.t<reverse+0.1 || Double($0.p)*sign<=0},name+" no old-direction lines after reversing")
    expectSustained(trace,name+" after",from:2.1,to:3.4,representative(5,0.3),sign:-sign)
}
// 6. Reverse while still moving: down then straight back up.
each {axis,sign,seed,label in
    let hand=Hand(parts:[.rest(0.3),stroke(5,0.25),stroke(-6,0.3),.rest(1.5)])
    let trace=simulate(hand,axis:axis,sign:sign,seed:seed)
    let name="reverse while moving ("+label+")"
    let reverse=trace.first({p,_ in Double(p)*sign<0},after:0.55) ?? 99
    check(reverse<=0.55+0.25,name+" reverses during the return stroke","\(f((reverse-0.55)*1000)) ms")
    check(trace.ticks.allSatisfy{$0.t<reverse+0.1 || Double($0.p)*sign<=0},name+" no old-direction lines after reversing")
    expectSustained(trace,name,from:1.1,to:2.35,representative(6,0.3),sign:-sign)
}
// 7. A faster stroke in the same direction speeds up without first slowing down.
each {axis,sign,seed,label in
    let hand=Hand(parts:[.rest(0.3),stroke(3,0.4),.rest(1.0),stroke(6,0.25),.rest(1.5)])
    let trace=simulate(hand,axis:axis,sign:sign,seed:seed)
    let name="faster restroke ("+label+")"
    expectSustained(trace,name+" before",from:0.9,to:1.65,representative(3,0.4),sign:sign)
    let before=sign*trace.rate(0.9,1.65).p
    for a in stride(from:1.7,to:2.1,by:0.1) {
        check(sign*trace.rate(a,a+0.1).p>=0.8*before,name+" no dip","\(f(sign*trace.rate(a,a+0.1).p)) at \(f(a)) after \(f(before))")
    }
    expectSustained(trace,name+" after",from:2.2,to:3.45,representative(6,0.25),sign:sign)
}
// 8. A slower stroke in the same direction slows the scroll.
each {axis,sign,seed,label in
    let hand=Hand(parts:[.rest(0.3),stroke(6,0.25),.rest(1.0),stroke(2.5,0.35),.rest(1.5)])
    let trace=simulate(hand,axis:axis,sign:sign,seed:seed)
    let name="slower restroke ("+label+")"
    expectSustained(trace,name+" before",from:0.8,to:1.5,representative(6,0.25),sign:sign)
    expectSustained(trace,name+" after",from:2.2,to:3.4,representative(2.5,0.35),sign:sign)
}
// 9. A stroke on the other axis switches axis in the same hold.
each {axis,sign,seed,label in
    let hand=Hand(parts:[.rest(0.3),stroke(5,0.3),.rest(0.8),.stroke(p:0,s:5,seconds:0.3),.rest(1.5)])
    let trace=simulate(hand,axis:axis,sign:sign,seed:seed)
    let name="axis change ("+label+")"
    check(trace.lines(0,1.4).s==0,name+" first stroke uses one axis")
    let late=trace.rate(1.9,3.2)
    check(late.p==0,name+" old axis stops","\(f(late.p))")
    check(representative(5,0.3).contains(late.s),name+" new axis speed","\(f(late.s))")
}
// 10. A sloppy stroke 22 degrees off the axis still scrolls only that axis, at full speed.
each {axis,sign,seed,label in
    let a=22*Double.pi/180
    let hand=Hand(parts:[.rest(0.3),.stroke(p:5*cos(a),s:5*sin(a),seconds:0.3),.rest(2.0)])
    let trace=simulate(hand,axis:axis,sign:sign,seed:seed)
    let name="sloppy stroke ("+label+")"
    check(trace.total.s==0,name+" no other-axis lines","\(trace.total.s)")
    expectSustained(trace,name,from:0.8,to:2.6,representative(5,0.3),sign:sign)
}
// 11. A clear diagonal keeps both axes.
for seed in seeds {
    let hand=Hand(parts:[.rest(0.3),.stroke(p:5*cos(Double.pi/4),s:5*sin(Double.pi/4),seconds:0.3),.rest(2.0)])
    let trace=simulate(hand,axis:.vertical,sign:1,seed:seed)
    let r=trace.rate(0.8,2.6),speed=hypot(r.p,r.s)
    check(r.p>0 && r.s>0 && near(r.p,r.s,0.3),"diagonal seed \(seed) both axes","\(f(r.p)),\(f(r.s))")
    check(representative(5,0.3).contains(speed),"diagonal seed \(seed) speed","\(f(speed))")
}
// 12. Holding still never starts a scroll, even with a shaky hand.
for (tremor,drift) in [(2.0,1.0),(3.5,2.0)] {
    each {axis,sign,seed,label in
        let trace=simulate(Hand(parts:[.rest(3.0)],tremor:tremor,drift:drift),axis:axis,sign:sign,seed:seed)
        check(trace.total.p==0 && trace.total.s==0,"still hold tremor \(tremor) ("+label+")","\(trace.total)")
    }
}
// 13. A short tap with motion scrolls nothing and keeps its tap meaning.
each {axis,sign,seed,label in
    var delivery=Delivery();delivery.first=0.07
    let trace=simulate(Hand(parts:[stroke(3,0.12),.rest(0.1)]),delivery,axis:axis,sign:sign,seed:seed,release:0.18)
    check(trace.total.p==0 && trace.total.s==0 && !trace.dropClick,"short tap ("+label+")")
}
// 14. A stalled Bluetooth batch while still does not change the scroll.
each {axis,sign,seed,label in
    var delivery=Delivery();delivery.stalled=[1.4...1.685]
    let trace=simulate(Hand(parts:[.rest(0.35),stroke(5,0.3),.rest(2.4)]),delivery,axis:axis,sign:sign,seed:seed)
    expectSustained(trace,"stall while still ("+label+")",from:0.85,to:3.05,representative(5,0.3),sign:sign)
}
// 15. Samples lost in the middle of a stroke: still the stroke's direction and a usable speed.
each {axis,sign,seed,label in
    var delivery=Delivery();delivery.lost=[0.45...0.53]
    let trace=simulate(Hand(parts:[.rest(0.35),stroke(5,0.3),.rest(2.4)]),delivery,axis:axis,sign:sign,seed:seed)
    expectSustained(trace,"lost stroke samples ("+label+")",from:0.85,to:3.05,representative(5,0.3,low:0.45),sign:sign)
}
// 16. Batched arrival matches immediate arrival.
each {axis,sign,seed,label in
    var delivery=Delivery();delivery.burst=0.045
    let hand=Hand(parts:[.rest(0.35),stroke(5,0.3),.rest(2.4)])
    let batched=simulate(hand,delivery,axis:axis,sign:sign,seed:seed),direct=simulate(hand,axis:axis,sign:sign,seed:seed)
    expectSustained(batched,"batched arrival ("+label+")",from:0.85,to:3.05,representative(5,0.3),sign:sign)
    check(near(batched.rate(0.85,3.05).p,direct.rate(0.85,3.05).p,0.12),"batched arrival ("+label+") matches direct")
}
// 17. A slow follow-through after the stroke does not lower the speed it set.
each {axis,sign,seed,label in
    let hand=Hand(parts:[.rest(0.3),stroke(6,0.3),.creep(p:4,s:0,seconds:0.5),.rest(1.5)])
    let trace=simulate(hand,axis:axis,sign:sign,seed:seed)
    expectSustained(trace,"follow-through ("+label+")",from:1.25,to:2.6,representative(6,0.3),sign:sign)
}
// 18. A one-sample knock while scrolling is not a stroke.
each {axis,sign,seed,label in
    let hand=Hand(parts:[.rest(0.3),stroke(5,0.3),.rest(0.8),stroke(-0.8,0.012),.rest(1.2)])
    let trace=simulate(hand,axis:axis,sign:sign,seed:seed)
    check(trace.ticks.allSatisfy{Double($0.p)*sign>=0},"knock ("+label+") never reverses")
    expectSustained(trace,"knock ("+label+")",from:0.8,to:2.6,representative(5,0.3),sign:sign)
}
// 19. Uneven device intervals, up to the 50 ms cap.
each {axis,sign,seed,label in
    var delivery=Delivery();delivery.dt=0.006...0.05
    let trace=simulate(Hand(parts:[.rest(0.35),stroke(5,0.3),.rest(2.4)]),delivery,axis:axis,sign:sign,seed:seed)
    expectSustained(trace,"uneven intervals ("+label+")",from:0.85,to:3.05,representative(5,0.3,low:0.45),sign:sign)
}
// 20. A shaky hand still produces one steady speed after the stroke.
each {axis,sign,seed,label in
    let trace=simulate(Hand(parts:[.rest(0.35),stroke(5,0.3),.rest(3.4)],tremor:3.5,drift:2),axis:axis,sign:sign,seed:seed)
    let name="shaky hand ("+label+")"
    expectSustained(trace,name,from:0.85,to:4.05,representative(5,0.3),sign:sign)
    check(trace.ticks.allSatisfy{Double($0.p)*sign>=0},name+" never scrolls the wrong way")
}
// 21. Release stops at once and drops the endpoint click; another hold starts from rest;
//     lost telemetry stops.
each {axis,sign,seed,label in
    let trace=simulate(Hand(parts:[.rest(0.35),stroke(5,0.3),.rest(1.0)]),axis:axis,sign:sign,seed:seed,release:1.5)
    check(trace.dropClick && trace.afterRelease==(0,0),"release ("+label+") stops and drops the click")
}
do {
    let h=WandHeldScroll();h.begin(now:0,sustain:true)
    for i in 0..<40 {let t=0.22+Double(i)*0.01;h.confirmHeld(now:t);_=h.sample(x:0,y:30,dt:0.01,now:t);_=h.continuation(now:t)}
    check(h.sustained.started,"a held stroke starts the scroll")
    _=h.end(now:0.7);h.begin(now:2,sustain:true);h.confirmHeld(now:2.3)
    check(h.continuation(now:2.3)==(0,0),"next hold cannot inherit speed")
    // Samples alone, without a fresh held-button confirmation, never extend the lease.
    for i in 0..<40 {_=h.sample(x:0,y:30,dt:0.01,now:2.3+Double(i)*0.01)}
    check(h.continuation(now:3.2)==(0,0),"lost telemetry cannot keep scrolling")
}
let quiet=WandHeldScroll();quiet.begin(now:0,sustain:true)
for i in 1...100 {let t=Double(i)*0.01;quiet.confirmHeld(now:t);_=quiet.sample(x:0.5,y:-0.5,dt:0.01,now:t);check(quiet.continuation(now:t)==(0,0),"quiet noise")}
let drag=WandHeldScroll();drag.begin(now:0,scrollable:false,sustain:true);precondition(drag.startDrag(now:0.3));check(drag.continuation(now:0.3)==(0,0),"explicit drag never scrolls")
// 22. Ethan's "much faster ... huge scroll" range (2026-10-30). Ordinary strokes keep
//     the original 1.6 lines per degree; faster strokes rise well above the old flat
//     120 lines per second, to a bounded 600.
let curve=WandSustainedScroll()
for peak in stride(from:0.0,through:60.0,by:2.5) {
    check(abs(curve.linesPerSecond(peak:peak)-peak*gain)<1e-9,"ordinary stroke \(f(peak)) deg/s keeps its speed","\(f(curve.linesPerSecond(peak:peak)))")
}
var previous=0.0
for peak in stride(from:0.0,through:400.0,by:0.5) {
    let rate=curve.linesPerSecond(peak:peak)
    check(rate>=previous && rate<=600,"speed curve rises continuously to its bound","\(f(rate)) at \(f(peak))");previous=rate
}
check(curve.linesPerSecond(peak:75)>=150,"a stroke at the old cap speed is faster","\(f(curve.linesPerSecond(peak:75)))")
check(curve.linesPerSecond(peak:100)>=2*120,"a fast stroke is at least twice the old maximum","\(f(curve.linesPerSecond(peak:100)))")
check(curve.linesPerSecond(peak:150)==600 && curve.linesPerSecond(peak:1e6)==600,"the fastest strokes are bounded at 600 lines per second")
let fast=WandSustainedScroll()
for _ in 0..<6 {fast.sample(x:2000,y:0,dt:0.01)}
check(fast.velocityX==600 && fast.velocityY==0,"fast strokes cap at 600 lines per second","\(fast.velocityX)")
// A late timer pays at most 50 ms at the cap, plus the new direction's first line.
check(fast.tick(now:100).x<=31,"late timer cannot replay a backlog")
// 23. A big flick through the whole held controller: far faster than the old cap,
//     then still reversible in the same hold and stopped at once by release.
each {axis,sign,seed,label in
    let hand=Hand(parts:[.rest(0.35),stroke(14,0.2),.rest(1.2),stroke(-5,0.3),.rest(1.2)])
    let trace=simulate(hand,axis:axis,sign:sign,seed:seed,release:3.2)
    let name="big flick ("+label+")"
    let big=sign*trace.rate(0.75,1.5).p
    check(big>=2*120 && big<=600,name+" scrolls at least twice the old maximum, within the bound","\(f(big)) lines/s")
    check(trace.lines(0.75,1.5).s==0,name+" single axis")
    let reverse=trace.first({p,_ in Double(p)*sign<0},after:1.75) ?? 99
    check(reverse<=1.75+0.25,name+" still reverses promptly","\(f((reverse-1.75)*1000)) ms")
    expectSustained(trace,name+" ordinary reverse speed",from:2.3,to:3.15,representative(5,0.3),sign:-sign)
    check(trace.dropClick && trace.afterRelease==(0,0),name+" release stops at once")
}
precondition(WandControlVersion.read(3) == .sustainedV3)

if failures.isEmpty {
    print("PASS: V3 motion profiles - stroke then still, slow onset, press and drag, recoil, reversal after a pause and while moving, faster and slower restrokes, axis change, sloppy and diagonal strokes, still and shaky holds, taps, stalls, lost samples, batching, follow-through, knocks, uneven intervals, release, fresh holds, telemetry loss, faster huge-scroll range")
} else {
    var groups:[String:Int]=[:]
    for failure in failures {
        var key=String(failure.prefix{$0 != ":"})
        if let open=key.firstIndex(of:"("),let close=key[open...].firstIndex(of:")") {key.removeSubrange(open...close)}
        groups[key.replacingOccurrences(of:"  ",with:" "),default:0]+=1
    }
    for key in groups.keys.sorted() {print("FAIL \(groups[key]!)x \(key)")}
    for failure in failures.prefix(40) {print("  "+failure)}
    exit(1)
}
