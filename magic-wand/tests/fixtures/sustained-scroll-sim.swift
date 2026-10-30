import Foundation

// Shared Control V3 hand-motion simulator for held-scroll tests. Units match the
// receiver: screen-corrected angular rates in degrees per second, device sample
// intervals in seconds and receiver uptime for arrival. The hand model (minimum-jerk
// strokes, tremor, slow drift, sensor noise, recoil, uneven sampling and Bluetooth
// gaps) is synthetic. It is regression evidence for the controller, not recorded
// wand motion.

/// Native wheel lines per degree, matching WandHeldScroll's default.
let gain=1.6

struct Rng {
    var state:UInt64
    mutating func unit()->Double {
        state &+= 0x9E3779B97F4A7C15
        var z=state
        z=(z^(z>>30)) &* 0xBF58476D1CE4E5B9
        z=(z^(z>>27)) &* 0x94D049BB133111EB
        z^=z>>31
        return Double(z>>11)/9007199254740992.0
    }
    mutating func gauss()->Double {let u=max(1e-12,unit()),v=unit();return sqrt(-2*log(u))*cos(2*Double.pi*v)}
}

/// Intentional motion on the scenario's primary (p) and secondary (s) axes.
enum Part {
    case rest(Double)
    /// Minimum-jerk displacement in degrees over seconds.
    case stroke(p:Double,s:Double,seconds:Double)
    /// Constant rate in degrees per second.
    case creep(p:Double,s:Double,seconds:Double)
    var seconds:Double {
        switch self {case .rest(let d):return d;case .stroke(_,_,let d):return d;case .creep(_,_,let d):return d}
    }
}
func stroke(_ p:Double,_ seconds:Double)->Part {.stroke(p:p,s:0,seconds:seconds)}

struct Hand {
    var parts:[Part]
    /// Degrees per second: 8-11.5 Hz physiological tremor, slow wander and sensor noise.
    var tremor=2.0,drift=1.0,noise=0.5
    var duration:Double {parts.reduce(0){$0+$1.seconds}}
    func start(of index:Int)->Double {parts.prefix(index).reduce(0){$0+$1.seconds}}
    func intent(at t:Double)->(p:Double,s:Double) {
        var start=0.0
        for part in parts {
            if t<start+part.seconds {
                switch part {
                case .rest:return (0,0)
                case .stroke(let p,let s,let d):let u=(t-start)/d,k=30*u*u*(1-u)*(1-u)/d;return (p*k,s*k)
                case .creep(let p,let s,_):return (p,s)
                }
            }
            start+=part.seconds
        }
        return (0,0)
    }
}

struct Delivery {
    /// Device time of the first raw sample after the press. Follow-mode holds report
    /// nothing until the 220 ms hold decision; a hold from mouse-off starts after the
    /// 70 ms switch settle.
    var first=0.22
    var dt=0.0088...0.0105
    var latency=0.015
    /// Bluetooth delivers notifications in batches; zero means immediately.
    var burst=0.0
    /// Device-time windows whose samples are never delivered.
    var lost:[ClosedRange<Double>]=[]
    /// Device-time windows whose samples arrive together at the window end.
    var stalled:[ClosedRange<Double>]=[]
}

struct Trace {
    var ticks:[(t:Double,p:Int32,s:Int32)]=[]
    var dropClick=false,afterRelease:(Int32,Int32)=(0,0)
    func lines(_ a:Double,_ b:Double)->(p:Double,s:Double) {
        var p=0.0,s=0.0
        for tick in ticks where tick.t>=a && tick.t<b {p+=Double(tick.p);s+=Double(tick.s)}
        return (p,s)
    }
    func rate(_ a:Double,_ b:Double)->(p:Double,s:Double) {let l=lines(a,b);return (l.p/(b-a),l.s/(b-a))}
    func first(_ test:(Int32,Int32)->Bool,after a:Double=0)->Double? {ticks.first{$0.t>=a && test($0.p,$0.s)}?.t}
    var total:(p:Double,s:Double) {lines(-1,1e9)}
}

enum Axis {case vertical,horizontal}
/// Sustained-scroll tuning for every simulated hold. The production default includes
/// the horizontal-only gain; axis-symmetric profiles set horizontalGain=1 to check the
/// shared stroke classifier on both axes against the one shared curve.
var simulationTuning=WandSustainedScroll.Tuning()
/// Runs one hold on the real WandHeldScroll and a 20 ms continuation timer, as the
/// receiver does. Every delivered sample renews the held lease, like its button bit.
func simulate(_ hand:Hand,_ delivery:Delivery=Delivery(),axis:Axis,sign:Double,seed:UInt64,release:Double?=nil)->Trace {
    var rng=Rng(state:seed &* 0x2545F4914F6CDD1D &+ 7)
    let f1=8+3*rng.unit(),f2=9.5+2*rng.unit(),fd=0.25+0.3*rng.unit()
    let phase=(0..<6).map{_ in 2*Double.pi*rng.unit()}
    let end=release ?? hand.duration
    var samples:[(arrive:Double,dt:Double,x:Double,y:Double)]=[]
    var t=delivery.first
    while t<end {
        let dt=delivery.dt.lowerBound+(delivery.dt.upperBound-delivery.dt.lowerBound)*rng.unit()
        let intent=hand.intent(at:t)
        func wobble(_ a:Int)->Double {
            let tremor=hand.tremor*(sin(2*Double.pi*f1*t+phase[a])+0.5*sin(2*Double.pi*f2*t+phase[a+2]))
            return tremor+hand.drift*sin(2*Double.pi*fd*t+phase[a+4])+hand.noise*rng.gauss()
        }
        let p=sign*intent.p+wobble(0),s=intent.s+wobble(1)
        var arrive=t+delivery.latency
        if let stall=delivery.stalled.first(where:{$0.contains(t)}) {arrive=stall.upperBound+delivery.latency}
        if delivery.burst>0 {arrive=(arrive/delivery.burst).rounded(.up)*delivery.burst}
        if !delivery.lost.contains(where:{$0.contains(t)}) {
            samples.append(axis == .vertical ? (arrive,dt,s,p) : (arrive,dt,p,s))
        }
        t+=dt
    }
    let hold=WandHeldScroll(sustainedTuning:simulationTuning);hold.begin(now:0,sustain:true)
    var trace=Trace(),tick=0.02,index=0
    while true {
        if index<samples.count && samples[index].arrive<=tick {
            let sample=samples[index];index+=1
            if sample.arrive<end {hold.confirmHeld(now:sample.arrive);_=hold.sample(x:sample.x,y:sample.y,dt:sample.dt,now:sample.arrive)}
            continue
        }
        if tick>=end {break}
        let r=hold.continuation(now:tick)
        trace.ticks.append(axis == .vertical ? (tick,r.y,r.x) : (tick,r.x,r.y))
        tick+=0.02
    }
    precondition(!hold.circular,"V3 never runs the circle classifier")
    if let release {trace.dropClick=hold.end(now:release);let r=hold.continuation(now:release+0.02);trace.afterRelease=(r.x,r.y)}
    return trace
}

/// A stroke's representative speed lies between its mean and its peak; it never
/// collapses to the onset or deceleration speed. Lines per second on the wheel.
func representative(_ amplitude:Double,_ seconds:Double,low:Double=0.55,high:Double=1.1)->ClosedRange<Double> {
    let peak=1.875*abs(amplitude)/seconds
    return max(abs(amplitude)/seconds,low*peak)*gain...high*peak*gain
}
func near(_ a:Double,_ b:Double,_ share:Double)->Bool {abs(a-b)<=share*max(abs(a),abs(b))}
func f(_ v:Double)->String {String(format:"%.1f",v)}

let variants:[(Axis,Double)]=[(.vertical,1),(.vertical,-1),(.horizontal,1),(.horizontal,-1)]
let seeds:[UInt64]=[1,2,3,4,5]
func each(_ body:(Axis,Double,UInt64,String)->Void) {
    for (axis,sign) in variants {for seed in seeds {body(axis,sign,seed,"\(axis) \(sign>0 ? "+":"-") seed \(seed)")}}
}
