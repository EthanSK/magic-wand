import Cocoa

// Ethan's native Back/Forward swipes (2026-10-30): "it's just not sensitive enough when
// doing those trackpad swipes". Checks the horizontal-only gain on the real V3 held
// controller (sustained-scroll-sim.swift hands, synthetic, not recorded wand motion) and
// the real WandNativeScrollGesture transport. Events are recorded, never posted. A larger
// horizontal distance does not establish that Chrome or Codex navigates: physical
// application acceptance is separate and unverified here.

var failures:[String]=[]
func check(_ ok:Bool,_ name:String,_ detail:@autoclosure()->String=""){if !ok {failures.append(name+(detail().isEmpty ? "" : ": "+detail()))}}

var flat=WandSustainedScroll.Tuning();flat.horizontalGain=1
let shipped=WandSustainedScroll.Tuning()
check(shipped.horizontalGain==12.5 && shipped.horizontalMaxRate==3000 && shipped.maxRate==600 && shipped.horizontalGainFrom==8 && shipped.horizontalGainFull==30 && shipped.horizontalGainLevelSlope==0.364,"shipped horizontal gain")
// The first installed build (2.5x, within the shared 600 ceiling). Ethan: "maybe five times".
var previousBuild=shipped;previousBuild.horizontalGain=2.5;previousBuild.horizontalMaxRate=600
check(WandHeldScroll().sustained.tuning.horizontalGain==shipped.horizontalGain,"the receiver's held scroll uses the shipped gain")

// 1. The shared (vertical/diagonal) curve is exactly Ethan's corrected one; the horizontal
//    curve sits on or above it, is continuous, non-decreasing and bounded by 600.
func original(_ p:Double)->Double {
    let o=min(120,max(0,p)*1.6)
    guard p>120 else{return o}
    let e=min(1,(p-120)/120);return o+(600-o)*e*e
}
let curve=WandSustainedScroll()
var previous=0.0
for peak in stride(from:0.0,through:1000.0,by:0.25) {
    let v=curve.linesPerSecond(peak:peak),h=curve.horizontalLinesPerSecond(peak:peak)
    check(abs(v-original(peak))<1e-9,"shared curve unchanged at \(f(peak)) deg/s","\(v) vs \(original(peak))")
    check(h>=v && h<=3000,"horizontal rate bounded at \(f(peak))","\(h)")
    check(h>=previous && h-previous<=12.5+1e-9,"horizontal rate continuous and rising at \(f(peak))","\(previous) -> \(h)");previous=h
}
for (peak,expected) in [(0.0,0.0),(5.0,8.0),(8.0,12.8),(19.0,205.2),(30.0,600.0),(50.0,1000.0),(75.0,1500.0),(120.0,1500.0),(150.0,1875.0),(180.0,3000.0),(240.0,3000.0)] {
    check(abs(curve.horizontalLinesPerSecond(peak:peak)-expected)<1e-9,"horizontal rate at \(f(peak)) deg/s","\(curve.horizontalLinesPerSecond(peak:peak)) not \(expected)")
}
// Fivefold the previous installed curve wherever that curve had its whole gain (30 deg/s
// and up, within 20 degrees of level), including five times its 600 ceiling; fine strokes
// up to 8 deg/s are unchanged in both; the ramp between rises continuously and never falls
// below the previous build.
let before=WandSustainedScroll(tuning:previousBuild)
for peak in stride(from:0.0,through:1000.0,by:0.25) {for slope in [0.0,0.2,0.364] {
    let now=curve.horizontalLinesPerSecond(peak:peak,slope:slope),old=before.horizontalLinesPerSecond(peak:peak,slope:slope)
    if peak>=30 {check(abs(now-5*old)<1e-9,"five times the previous curve at \(f(peak)) deg/s","\(now) vs \(old)")}
    else if peak<=8 {check(now==old && now==curve.linesPerSecond(peak:peak),"fine stroke \(f(peak)) unchanged")}
    else {check(now>=old && now<=5*old+1e-9,"ramp \(f(peak)) between the previous and fivefold","\(now) vs \(old)")}
}}
// Off-level strokes fade to the shared rate exactly at the 30 degree snap boundary.
check(curve.horizontalLinesPerSecond(peak:50,slope:0.364)==1000,"20 degrees off level keeps all of the gain")
check(abs(curve.horizontalLinesPerSecond(peak:50,slope:0.4705)-540)<1e-6,"25 degrees off level keeps half of it")
check(curve.horizontalLinesPerSecond(peak:50,slope:0.577)==80 && curve.horizontalLinesPerSecond(peak:50,slope:.infinity)==80,"the snap boundary has none")
var lastSlope=1000.0
for slope in stride(from:0.0,through:1.0,by:0.001) {
    let h=curve.horizontalLinesPerSecond(peak:50,slope:slope)
    check(h<=lastSlope && lastSlope-h<=4.5,"gain fades continuously with slope \(slope)");lastSlope=h
}
var off=flat;check(WandSustainedScroll(tuning:off).horizontalLinesPerSecond(peak:60)==96,"gain 1 is the shared curve")
off.horizontalGain=0.5;check(WandSustainedScroll(tuning:off).horizontalLinesPerSecond(peak:60)==96,"a gain below 1 never weakens horizontal")

// 2. Vertical and diagonal hands are identical to the shared curve: the same velocity after
//    every reading and the same wheel lines at every tick.
var compared=0
let diagonal35=35*Double.pi/180,diagonal45=Double.pi/4
for (index,parts) in [[stroke(1.5,0.4)],[stroke(5,0.3)],[stroke(9,0.25)],[stroke(16,0.3)],[stroke(30,0.2)],
                      [stroke(6,0.25),.rest(0.8),stroke(-8,0.3)],[stroke(5,0.25),stroke(-6,0.3)],
                      [stroke(3,0.4),.rest(0.6),stroke(16,0.3)],
                      [.stroke(p:10*sin(diagonal45),s:10*cos(diagonal45),seconds:0.3)],
                      [.stroke(p:-8*sin(diagonal35),s:8*cos(diagonal35),seconds:0.25)],
                      [.stroke(p:6*sin(diagonal35),s:-6*cos(diagonal35),seconds:0.3),.rest(0.6),.stroke(p:-6*sin(diagonal45),s:6*cos(diagonal45),seconds:0.3)]].enumerated() {
    let hand=Hand(parts:[.rest(0.2)]+parts+[.rest(1.0)])
    let now=WandSustainedScroll(tuning:shipped),before=WandSustainedScroll(tuning:flat)
    var rng=Rng(state:UInt64(index+31)),time=0.0
    while time<hand.duration {
        let dt=0.0088+0.0017*rng.unit(),intent=hand.intent(at:time)
        let x=intent.s+2*sin(2*Double.pi*9*time)+0.5*rng.gauss(),y=intent.p+2*sin(2*Double.pi*10.5*time+1)+0.5*rng.gauss()
        now.sample(x:x,y:y,dt:dt,now:time);before.sample(x:x,y:y,dt:dt,now:time)
        check(now.velocityX==before.velocityX && now.velocityY==before.velocityY,"vertical/diagonal hand \(index) keeps its speed","\(now.velocityX),\(now.velocityY) vs \(before.velocityX),\(before.velocityY) at \(f(time))")
        check(now.tick(now:time)==before.tick(now:time),"vertical/diagonal hand \(index) posts the same lines");compared+=1
        time+=dt
    }
}
check(compared>1500,"enough vertical and diagonal readings compared","\(compared)")

// 3. Short deliberate horizontal swipes, Back and Forward, through the held controller and
//    its 20 ms timer: same first-line time or earlier (never later), nothing before the
//    220 ms hold decision, nothing vertical, nothing after release, no backlog burst.
func run(_ tuning:WandSustainedScroll.Tuning,_ hand:Hand,_ delivery:Delivery,sign:Double,seed:UInt64,release:Double?=nil,axis:Axis = .horizontal)->Trace {
    simulationTuning=tuning;return simulate(hand,delivery,axis:axis,sign:sign,seed:seed,release:release)
}
var mouseOff=Delivery();mouseOff.first=0.07
let swipes:[(String,Hand,Delivery,Double)]=[
    ("quick 5 deg/180 ms, release 500 ms",Hand(parts:[.rest(0.05),stroke(5,0.18),.rest(0.5)]),mouseOff,0.5),
    ("8 deg/250 ms, release 600 ms",Hand(parts:[.rest(0.05),stroke(8,0.25),.rest(0.5)]),mouseOff,0.6),
    ("12 deg/300 ms, release 900 ms",Hand(parts:[.rest(0.05),stroke(12,0.3),.rest(0.8)]),mouseOff,0.9),
    ("follow mode 8 deg/250 ms, release 800 ms",Hand(parts:[.rest(0.25),stroke(8,0.25),.rest(0.5)]),Delivery(),0.8),
]
var table:[String]=[]
for (name,hand,delivery,release) in swipes {
    var before=[Double](),after=[Double]()
    for sign in [1.0,-1.0] {for seed:UInt64 in 1...5 {
        let label="\(name) \(sign>0 ? "Forward":"Back") seed \(seed)"
        let base=run(flat,hand,delivery,sign:sign,seed:seed,release:release)
        let boosted=run(shipped,hand,delivery,sign:sign,seed:seed,release:release)
        let firstBase=base.first({p,s in p != 0 || s != 0}) ?? 99,firstBoosted=boosted.first({p,s in p != 0 || s != 0}) ?? 99
        check(firstBoosted<=firstBase && firstBoosted>=0.22,label+" first line no later, never before the hold decision","\(f(firstBoosted*1000)) vs \(f(firstBase*1000)) ms")
        check(boosted.total.s==0 && base.total.s==0,label+" horizontal only","\(boosted.total.s)")
        check(boosted.ticks.allSatisfy{Double($0.p)*sign>=0},label+" never the wrong way")
        // At most 50 ms at the horizontal ceiling, as the shared timer already allows.
        check(boosted.ticks.allSatisfy{abs($0.p)<=151},label+" no backlog burst")
        let old=run(previousBuild,hand,delivery,sign:sign,seed:seed,release:release)
        let fold=boosted.total.p/old.total.p
        check(fold>=4.6 && fold<=5.2,label+" five times the previous build","\(f(sign*old.total.p)) -> \(f(sign*boosted.total.p)) lines")
        let firstOld=old.first({p,s in p != 0 || s != 0}) ?? 99
        check(firstBoosted<=firstOld,label+" first line no later than the previous build")
        check(boosted.dropClick && boosted.afterRelease==(0,0),label+" release stops at once")
        let ratio=sign*boosted.total.p/(sign*base.total.p)
        check(ratio>=10 && ratio<=13,label+" distance gain","\(f(sign*base.total.p)) -> \(f(sign*boosted.total.p)) lines")
        before.append(sign*base.total.p);after.append(sign*boosted.total.p)
    }}
    let mean={(a:[Double]) in a.reduce(0,+)/Double(a.count)}
    table.append("\(name): \(Int(mean(before)*10)) -> \(Int(mean(after)*10)) points (\(Int(before.min()!*10))-\(Int(before.max()!*10)) -> \(Int(after.min()!*10))-\(Int(after.max()!*10)))")
}
// A fine, slow horizontal stroke keeps (almost exactly) the ordinary mapping.
for seed:UInt64 in 1...5 {
    let hand=Hand(parts:[.rest(0.3),stroke(1.5,0.4),.rest(1.0)])
    let base=run(flat,hand,Delivery(),sign:1,seed:seed),boosted=run(shipped,hand,Delivery(),sign:1,seed:seed)
    check(boosted.total.p<=base.total.p*1.15+1,"fine horizontal stroke seed \(seed) stays fine","\(base.total.p) -> \(boosted.total.p)")
}
// A sloppy swipe 22 degrees off level stays horizontal-only and keeps most of the gain.
for seed:UInt64 in 1...5 {
    let a=22*Double.pi/180
    let hand=Hand(parts:[.rest(0.3),.stroke(p:8*cos(a),s:8*sin(a),seconds:0.25),.rest(0.8)])
    let base=run(flat,hand,Delivery(),sign:-1,seed:seed),boosted=run(shipped,hand,Delivery(),sign:-1,seed:seed)
    check(boosted.total.s==0,"sloppy swipe seed \(seed) horizontal only")
    check(boosted.total.p/base.total.p>=7,"sloppy swipe seed \(seed) keeps most of the gain","\(base.total.p) -> \(boosted.total.p)")
}
// Diagonal held scrolling is untouched, tick for tick.
for seed:UInt64 in 1...5 {
    let hand=Hand(parts:[.rest(0.3),.stroke(p:6*sin(diagonal45),s:6*cos(diagonal45),seconds:0.3),.rest(1.2)])
    let base=run(flat,hand,Delivery(),sign:1,seed:seed,axis:.vertical),boosted=run(shipped,hand,Delivery(),sign:1,seed:seed,axis:.vertical)
    check(base.ticks.count==boosted.ticks.count && zip(base.ticks,boosted.ticks).allSatisfy{$0.p==$1.p && $0.s==$1.s},"diagonal held seed \(seed) identical")
    check(boosted.total.p>0 && boosted.total.s>0,"diagonal held seed \(seed) both axes")
}

// 4. Reversals keep their timing and direction; the return leg is boosted too.
for (name,parts,turn) in [("reverse while moving",[Part.rest(0.3),stroke(5,0.25),stroke(-6,0.3),.rest(1.2)],0.55),
                          ("reverse after pause",[Part.rest(0.3),stroke(5,0.3),.rest(0.6),stroke(-5,0.3),.rest(1.2)],1.2)] {
    for sign in [1.0,-1.0] {for seed:UInt64 in 1...5 {
        let label="\(name) \(sign>0 ? "+":"-") seed \(seed)"
        let hand=Hand(parts:parts)
        let base=run(flat,hand,Delivery(),sign:sign,seed:seed),boosted=run(shipped,hand,Delivery(),sign:sign,seed:seed)
        let rb=base.first({p,_ in Double(p)*sign<0},after:turn) ?? 99,rs=boosted.first({p,_ in Double(p)*sign<0},after:turn) ?? 99
        check(rs<=rb+0.02 && rs<=turn+0.25,label+" reverses as promptly","\(f((rs-turn)*1000)) vs \(f((rb-turn)*1000)) ms")
        check(boosted.ticks.allSatisfy{$0.t<rs+0.1 || Double($0.p)*sign<=0},label+" no old-direction lines after reversing")
        check(boosted.total.s==0,label+" horizontal only")
        let a=hand.duration-0.8,b=hand.duration
        check(-sign*boosted.lines(a,b).p>=9*(-sign*base.lines(a,b).p),label+" return leg boosted","\(base.lines(a,b).p) -> \(boosted.lines(a,b).p)")
    }}
}

// 5. A faster same-direction horizontal restroke never dips the wheel speed on its way up.
do {
    let hand=Hand(parts:[.rest(0.3),stroke(3,0.4),.rest(1.0),stroke(6,0.25),.rest(1.0)])
    for seed:UInt64 in 1...5 {
        let s=WandSustainedScroll(tuning:shipped);var rng=Rng(state:seed),time=0.0,established=0.0,lowest=Double.infinity,final=0.0
        while time<hand.duration {
            let dt=0.0088+0.0017*rng.unit(),intent=hand.intent(at:time)
            s.sample(x:intent.p+2*sin(2*Double.pi*9*time)+0.5*rng.gauss(),y:2*sin(2*Double.pi*10.5*time+1)+0.5*rng.gauss(),dt:dt,now:time)
            if time<1.65 {established=s.velocityX} else {lowest=min(lowest,s.velocityX)}
            final=s.velocityX;time+=dt
        }
        check(established>0 && lowest>=0.98*established && final>1.5*established,"faster horizontal restroke seed \(seed) no dip","\(f(established)) lowest \(f(lowest)) final \(f(final))")
    }
}

// 6. The real native transport: every timer tick with lines becomes exactly one precise
//    event in the same call, ten points per line, phases began/changed then ended, no
//    momentum, fixed anchor. Lost telemetry cancels instead.
for (cancel,phase) in [(false,NSEvent.Phase.ended),(true,.cancelled)] {
    let hold=WandHeldScroll();hold.begin(now:0,sustain:true)
    var gesture=WandNativeScrollGesture(),events:[NSEvent]=[],ticks:[Int32]=[]
    let anchor=CGPoint(x:400,y:300),hand=Hand(parts:[.rest(0.05),stroke(-8,0.25),.rest(0.5)],tremor:0,drift:0,noise:0)
    var t=0.0,tick=0.02
    while tick<0.6 {
        while t+0.01<=tick {t+=0.01;hold.confirmHeld(now:t);_=hold.sample(x:hand.intent(at:t).p,y:0,dt:0.01,now:t)}
        let r=hold.continuation(now:tick)
        if r.x != 0 || r.y != 0 {
            ticks.append(r.x)
            let point=events.isEmpty ? anchor : CGPoint(x:anchor.x+tick*100,y:anchor.y)
            if let e=gesture.update(x:r.x,y:r.y,at:point) {events.append(NSEvent(cgEvent:e)!);check(e.location==anchor,"anchored")}
        }
        tick+=0.02
    }
    check(events.count==ticks.count && !ticks.isEmpty,"one event per tick, none queued","\(events.count) vs \(ticks.count)")
    check(zip(events,ticks).allSatisfy{$0.scrollingDeltaX==CGFloat($1)*10 && $0.scrollingDeltaY==0},"ten points per line, horizontal only")
    check(events.allSatisfy{$0.hasPreciseScrollingDeltas && $0.momentumPhase.isEmpty},"precise and no momentum")
    check(events.first?.phase == .began && events.dropFirst().allSatisfy{$0.phase == .changed},"began then changed")
    _=hold.end(now:0.6)
    let end=NSEvent(cgEvent:gesture.finish(cancelled:cancel)!)!
    check(end.phase==phase && end.scrollingDeltaX==0 && end.scrollingDeltaY==0,"release ends, lost telemetry cancels")
    check(gesture.finish(cancelled:true)==nil && hold.continuation(now:0.62)==(0,0),"nothing after the end")
    if !cancel {table.append("native Back swipe 8 deg/250 ms, no tremor: \(events.count) events, \(Int(events.reduce(0){$0+$1.scrollingDeltaX})) points before .ended")}
}
simulationTuning=shipped

for line in table {print(line)}
if failures.isEmpty {
    print("PASS: horizontal swipe gain - shared curve unchanged, bounded continuous horizontal curve, identical vertical/diagonal, short swipes Back/Forward boosted with no later first line, fine/sloppy/diagonal, reversals, no dip, native one-event-per-tick transport with end/cancel")
} else {
    var groups:[String:Int]=[:]
    for failure in failures {groups[String(failure.split(separator:":").first ?? ""),default:0]+=1}
    for (name,count) in groups.sorted(by:{$0.key<$1.key}) {print("FAIL \(count)x \(name)")}
    for failure in failures.prefix(12) {print("  "+failure)}
    exit(1)
}
