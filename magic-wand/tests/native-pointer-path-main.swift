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

// 1. Small motion is not swallowed (the tuned slack and curve hide it).
let slowDirect = run(filter(.direct), x: 0.5, seconds: 1), slowTuned = run(filter(.tuned), x: 0.5, seconds: 1)
precondition(abs(Double(slowDirect.x) + 0.5 * perDegree) <= 1.5 && slowDirect.y == 0, "0.5 deg/s for 1 s moves \(slowDirect)")
precondition(slowTuned.x == 0, "the tuned filter swallows the same motion: \(slowTuned)")
print("PASS: direct moves \(slowDirect.x) counts for 0.5°; tuned moves \(slowTuned.x)")

// 2. Axes and signs match the tuned path; no cross-talk.
for path in [WandPointerPath.tuned, .direct] {
    let h = run(filter(path), x: 50, seconds: 0.3), v = run(filter(path), y: 50, seconds: 0.3)
    precondition(h.x < 0 && h.y == 0 && v.y > 0 && v.x == 0, "\(path): horizontal \(h), vertical \(v)")
}
// 3. Same units and gain where the tuned curve is at full scale.
let fastDirect = run(filter(.direct), x: 100, y: 100, seconds: 0.5), fastTuned = run(filter(.tuned), x: 100, y: 100, seconds: 0.5)
precondition(abs(Double(fastDirect.x) / Double(fastTuned.x) - 1) < 0.03 && abs(Double(fastDirect.y) / Double(fastTuned.y) - 1) < 0.03,
             "shared gain at speed: \(fastDirect) vs \(fastTuned)")
precondition(abs(Double(fastDirect.x) + 50 * perDegree) < 2 && abs(Double(fastDirect.y) - 1.4 * 50 * perDegree) < 2, "86.4 counts/° with the 1.4 vertical gain")
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

// 6. Nothing is replayed: no tail after motion stops, and a reset drops the remainder.
let tail = filter(.direct); _ = run(tail, x: 30, seconds: 0.2)
precondition(run(tail, seconds: 0.5) == (0, 0), "stopping stops the direct pointer immediately")
let carry = filter(.direct); _ = run(carry, x: 0.08, seconds: 0.1)   // under one count accumulated
let afterGap = carry.sample(rawX: Int(bias[0]), rawY: Int(bias[1]), microseconds: 9615, held: false, resetState: true)!
precondition(afterGap.x == 0 && afterGap.y == 0 && run(carry, x: 0.08, seconds: 0.1) == (0, 0), "a reset after a pause or gap carries nothing over")
print("PASS: no tail or replay")

// 7. Stop-to-click keeps the tuned stop counts: one click after real travel,
// none from tremor alone, no flood while still, even though the direct
// pointer shows tremor and a small zero error as continuous counts.
func dwellClicks(useStopCounts: Bool) -> (clicks: Int, stillCounts: Int) {
    let f = filter(.direct), dwell = WandDwellClick(); dwell.follow(true)
    var now = 100.0, clicks = 0, stillCounts = 0
    for i in 0..<(Int(4 * 104)) {
        let moving = i < 31                                  // 0.3 s of a 40°/s sweep
        let tremor = moving ? 40 : 0.2 + 0.7 * sin(Double(i) * 0.9) // still: tremor plus 0.2°/s zero error
        let s = f.sample(rawX: Int((bias[0] + tremor * counts).rounded()), rawY: Int(bias[1]), microseconds: 9615, held: false, resetState: false)!
        if !moving { stillCounts += abs(s.x) }
        dwell.intent(s.intent, now: now)
        dwell.move(dx: useStopCounts ? s.stopX : s.x, dy: useStopCounts ? s.stopY : s.y, now: now, eligible: true)
        if dwell.tick(now: now) { clicks += 1 }
        now += 0.009615
    }
    return (clicks, stillCounts)
}
let stop = dwellClicks(useStopCounts: true), raw = dwellClicks(useStopCounts: false)
precondition(stop.clicks == 1, "exactly one stop-to-click after the sweep: \(stop.clicks)")
precondition(stop.stillCounts > 0, "the direct pointer still shows the zero error while held still")
precondition(raw.clicks == 0, "direct counts alone would never allow the click (\(raw.clicks))")
print("PASS: stop-to-click fires once on tuned stop counts; direct counts alone would block it")

// 8. The tuned path is unchanged and reports its own counts as stop counts.
let tuned = filter(.tuned)
for _ in 0..<52 {
    let s = tuned.sample(rawX: Int(bias[0] + 10 * counts), rawY: Int(bias[1]), microseconds: 9615, held: false, resetState: false)!
    precondition(s.stopX == s.x && s.stopY == s.y)
}
precondition(WandPointerPath.read(nil, default: .direct) == .direct && WandPointerPath.read("tuned", default: .direct) == .tuned &&
             WandPointerPath.read("smoothed", default: .tuned) == .tuned)
print("PASS: tuned path unchanged; option values parse strictly")
