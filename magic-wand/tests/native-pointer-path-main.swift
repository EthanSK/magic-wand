import Foundation
setbuf(stdout, nil)
// Direct Sense pointer baseline versus the unchanged tuned filter. Pure maths:
// no native input, transport or hardware.
let counts = 1 / 0.00875                       // Puck counts per deg/s (Sense units)
let bias = [289.3, -47.9]                      // pointer-horizontal (Puck z) and vertical (Puck x) zero
let config = [bias[0], bias[1], 86.4 * 1.1725, 1.4, 0.35, 2, 18, 1.0 / 3, 0.2, 0.35, 1, -1, 1]
func filter(_ path: WandPointerPath) -> WandMotionFilter {
    let f = WandMotionFilter(); precondition(f.configure(config)); f.path = path; return f
}
/// Constant rates (deg/s) on the two pointer axes for `seconds` at 104 Hz.
func run(_ f: WandMotionFilter, x: Double = 0, y: Double = 0, seconds: Double, held: Bool = false) -> (x: Int, y: Int) {
    var total = (x: 0, y: 0)
    for _ in 0..<Int((seconds * 104).rounded()) {
        let s = f.sample(rawX: Int((bias[0] + x * counts).rounded()), rawY: Int((bias[1] + y * counts).rounded()),
                         microseconds: 9615, held: held, resetState: false)!
        total.x += s.x; total.y += s.y
    }
    return total
}
let perDegree = 86.4 * 1.1725 / 134 * counts   // counts per true degree at full speed = 86.4

// 1. Ethan restored quiet tiny-motion stopping while keeping normal direct movement.
let slowDirect = run(filter(.direct), x: 0.5, seconds: 1), slowTuned = run(filter(.tuned), x: 0.5, seconds: 1)
precondition(slowDirect == (0,0), "tiny motion stops for clicking: \(slowDirect)")
precondition(slowTuned.x == 0, "the tuned filter swallows the same motion: \(slowTuned)")
print("PASS: tiny motion stops on both paths")
let immediate=filter(.direct).sample(rawX:Int(bias[0]+30*counts),rawY:Int(bias[1]),microseconds:9615,held:false,resetState:false)!
precondition(immediate.x != 0,"normal direct movement starts on its first sample")

// 2. Axes and signs match the tuned path; no cross-talk.
for path in [WandPointerPath.tuned, .direct] {
    let h = run(filter(path), x: 50, seconds: 0.3), v = run(filter(path), y: 50, seconds: 0.3)
    precondition(h.x < 0 && h.y == 0 && v.y > 0 && v.x == 0, "\(path): horizontal \(h), vertical \(v)")
}
// 3. Same units and gain where the tuned curve is at full scale. The ~8 ms
// smoothing delays travel but never loses it: include the brief settle.
func settled(_ f: WandMotionFilter, x: Double = 0, y: Double = 0, seconds: Double) -> (x: Int, y: Int) {
    let a = run(f, x: x, y: y, seconds: seconds), b = run(f, seconds: 0.1); return (a.x + b.x, a.y + b.y)
}
let fastDirect = settled(filter(.direct), x: 100, y: 100, seconds: 0.5), fastTuned = settled(filter(.tuned), x: 100, y: 100, seconds: 0.5)
precondition(abs(Double(fastDirect.x) / Double(fastTuned.x) - 1) < 0.03 && abs(Double(fastDirect.y) / Double(fastTuned.y) - 1) < 0.03,
             "shared gain at speed: \(fastDirect) vs \(fastTuned)")
// Within the stop knee's share of the decaying tail (under 4 deg/s, ~10 ms).
precondition(abs(Double(fastDirect.x) + 50 * perDegree) < 6 && abs(Double(fastDirect.y) - 1.4 * 50 * perDegree) < 8, "86.4 counts/° with the 1.4 vertical gain: \(fastDirect)")
// 4. Held LOW precision keeps its one-third gain.
let heldDirect = run(filter(.direct), x: 20, seconds: 0.5, held: true), freeDirect = run(filter(.direct), x: 20, seconds: 0.5)
precondition(abs(Double(heldDirect.x) * 3 - Double(freeDirect.x)) <= 3, "held \(heldDirect.x) is a third of \(freeDirect.x)")
print("PASS: signs, axes, shared gain, vertical gain and held LOW")

// 5. Rotation-independent controls project both paths identically.
for path in [WandPointerPath.tuned, .direct] {
    let f = filter(path); f.orientationCompensation = true; f.observeGravity(x: 1, y: 0, z: 0) // rolled 90°
    let rolled = run(f, x: 50, seconds: 0.3)
    precondition(rolled.x == 0 && rolled.y != 0, "\(path) rolled 90°: \(rolled)")
}
print("PASS: gravity projection shared")

// 6. Nothing is replayed: only the ~8 ms smoothing's own tail after motion
// stops, then nothing; a reset drops the remainder.
let tail = filter(.direct); _ = run(tail, x: 30, seconds: 0.2)
let afterStop = (0..<3).map { _ in tail.sample(rawX: Int(bias[0]), rawY: Int(bias[1]), microseconds: 9615, held: false, resetState: false)!.x }
precondition(abs(afterStop.reduce(0, +)) <= Int(30 * 0.008 * perDegree) + 2, "the stop tail is the smoothing delay only: \(afterStop)")
precondition(run(tail, seconds: 0.5) == (0, 0), "after the smoothing settles the direct pointer is still")
let carry = filter(.direct); _ = run(carry, x: 0.08, seconds: 0.1)   // under one count accumulated
let afterGap = carry.sample(rawX: Int(bias[0]), rawY: Int(bias[1]), microseconds: 9615, held: false, resetState: true)!
precondition(afterGap.x == 0 && afterGap.y == 0 && run(carry, x: 0.08, seconds: 0.1) == (0, 0), "a reset after a pause or gap carries nothing over")
print("PASS: no tail or replay")

// 6b. Ethan's approved ~8 ms causal smoothing: a 20 deg/s step reaches about
// 70% on its first reading and over 95% within three, with no overshoot.
let stepFilter = filter(.direct)
let response = (0..<6).map { _ in Double(-stepFilter.sample(rawX: Int(bias[0] + 20 * counts), rawY: Int(bias[1]), microseconds: 9615, held: false, resetState: false)!.x) }
let full = 20 * 0.009615 * perDegree
precondition(response[0] > 0.55 * full && response[0] < 0.8 * full, "first reading responds at once: \(response[0]) of \(full)")
precondition(response[2] > 0.93 * full && response.allSatisfy { $0 <= full + 1 }, "settles within three readings, no overshoot: \(response)")
// 6c. Continuous tiny-motion stop. CONFIG fineSpeed is 2 in the program's
// 134-count units, about 2.34 true deg/s on the Sense: still at or below it,
// part gain up to twice it, then full gain.
func steady(_ rate: Double) -> Double { Double(-run(filter(.direct), x: rate, seconds: 1).x) / (rate * perDegree) }
precondition(steady(2.3) == 0 && steady(1.5) == 0, "at or below the slow-speed boundary the pointer stops")
precondition(steady(3.5) > 0.3 && steady(3.5) < 0.7 && steady(5.5) > 0.9 && steady(10) > 0.95, "no on/off jump: \(steady(3.5)), \(steady(5.5)), \(steady(10))")
// 6d. A long gap is skipped, never caught up: one late reading moves at most 25 ms.
let gapFilter = filter(.direct); _ = run(gapFilter, x: 40, seconds: 0.2)
let late = gapFilter.sample(rawX: Int(bias[0] + 40 * counts), rawY: Int(bias[1]), microseconds: 50000, held: false, resetState: false)!
precondition(Double(abs(late.x)) <= 40 * 0.025 * perDegree + 1, "a 50 ms gap is not replayed: \(late.x)")
precondition(abs(WandMotionFilter.directSmoothing - 0.008) < 1e-9, "the approved smoothing stays about 8 ms")
print("PASS: approved 8 ms smoothing, continuous stop and bounded late step")

// 7. Stop-to-click keeps the tuned stop counts: one click after real travel,
// none from tremor alone, no flood while still, even though the direct
// pointer shows tremor and a small zero error as continuous counts.
func dwellClicks(useStopCounts: Bool) -> (clicks: Int, stillCounts: Int, settledCounts:Int) {
    let f = filter(.direct), dwell = WandDwellClick(); dwell.follow(true)
    var now = 100.0, clicks = 0, stillCounts = 0, settledCounts=0
    for i in 0..<(Int(4 * 104)) {
        let moving = i < 31                                  // 0.3 s of a 40°/s sweep
        let tremor = moving ? 40 : 0.2 + 0.7 * sin(Double(i) * 0.9) // still: tremor plus 0.2°/s zero error
        let s = f.sample(rawX: Int((bias[0] + tremor * counts).rounded()), rawY: Int(bias[1]), microseconds: 9615, held: false, resetState: false)!
        if !moving { stillCounts += abs(s.x) };if i>52 {settledCounts+=abs(s.x)+abs(s.y)}
        dwell.intent(s.intent, now: now)
        dwell.move(dx: useStopCounts ? s.stopX : s.x, dy: useStopCounts ? s.stopY : s.y, now: now, eligible: true)
        if dwell.tick(now: now) { clicks += 1 }
        now += 0.009615
    }
    return (clicks, stillCounts,settledCounts)
}
let stop = dwellClicks(useStopCounts: true), raw = dwellClicks(useStopCounts: false)
precondition(stop.clicks == 1, "exactly one stop-to-click after the sweep: \(stop.clicks)")
precondition(stop.settledCounts == 0,"settled tiny motion must not move the pointer")
precondition(raw.clicks == 1,"quiet-motion stopping permits one click on direct counts too (\(raw.clicks))")
print("PASS: stop-to-click fires once; tiny motion cannot keep moving the pointer")

// 8. The tuned path is unchanged and reports its own counts as stop counts.
let tuned = filter(.tuned)
for _ in 0..<52 {
    let s = tuned.sample(rawX: Int(bias[0] + 10 * counts), rawY: Int(bias[1]), microseconds: 9615, held: false, resetState: false)!
    precondition(s.stopX == s.x && s.stopY == s.y)
}
precondition(WandPointerPath.read(nil, default: .direct) == .direct && WandPointerPath.read("tuned", default: .direct) == .tuned &&
             WandPointerPath.read("smoothed", default: .tuned) == .tuned)
print("PASS: tuned path unchanged; option values parse strictly")
