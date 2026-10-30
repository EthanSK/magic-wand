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
precondition(slowDirect == (0,0), "still-hand level motion (0.5, about 0.6 deg/s) stops: \(slowDirect)")
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
precondition(abs(Double(fastDirect.x) + 50 * perDegree) < 100 * 0.008 * perDegree && abs(Double(fastDirect.y) - 1.4 * 50 * perDegree) < 1.4 * 100 * 0.008 * perDegree, "86.4 counts/° with the 1.4 vertical gain: \(fastDirect)")
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
// 5b. Sense strict gravity: a sample taken mid-jerk, mid-twist or near vertical
// never sets the roll; a clean near-1 g sample still does, at once. The Puck
// (strictGravity off) keeps its original bounds.
func upright(_ f: WandMotionFilter) -> Bool { let m = run(f, x: 50, seconds: 0.2); return m.x != 0 && m.y == 0 }
for strict in [false, true] {
    func make() -> WandMotionFilter { let f = filter(.direct); f.orientationCompensation = true; f.orientation.strictGravity = strict; f.observeGravity(x: 0, y: 0, z: 1); return f }
    let jerk = make(); jerk.observeGravity(x: 1.2, y: 0, z: 0, rotation: 5)
    let twist = make(); twist.observeGravity(x: 1, y: 0, z: 0, rotation: 120)
    let vertical = make(); vertical.observeGravity(x: 0.3, y: 0.954, z: 0, rotation: 5)
    let clean = make(); clean.observeGravity(x: 1, y: 0, z: 0, rotation: 10)
    precondition(upright(jerk) == strict && upright(vertical) == strict, "strict \(strict): 1.2 g and near-vertical samples")
    precondition(upright(twist) == strict, "strict \(strict): a fast-rotation sample")
    precondition(!upright(clean), "strict \(strict): a clean rolled sample is used immediately")
}
print("PASS: Sense gravity ignores jerks, twists and near-vertical samples")

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
precondition(steady(0.1) == 0 && steady(1.5) > 0, "still noise stops; coherent slow aiming moves")
precondition(steady(1.5) < steady(5.5) && steady(5.5) < steady(10) && steady(10) < steady(25), "restored speed curve: fine aim, medium and broad travel")
// Approved tiny-only intent confirmation never replays its confirming travel.
let fine = filter(.direct)
var firstFine:Int?
for i in 0..<104 {
    let o=fine.sample(rawX:Int(bias[0]+1.5*counts),rawY:Int(bias[1]),microseconds:9615,held:false,resetState:false)!
    if o.x != 0 && firstFine == nil {firstFine=i}
}
precondition(firstFine != nil && firstFine! < 12, "slow aiming starts after bounded confirmation and subpixel travel")
let tinyNoise=filter(.direct)
var noiseTotal=0
for i in 0..<208 {
 let sign=i%2==0 ? 1.0 : -1.0
 noiseTotal += tinyNoise.sample(rawX:Int(bias[0]+sign*0.8*counts),rawY:Int(bias[1]),microseconds:9615,held:false,resetState:false)!.x
}
precondition(abs(noiseTotal)<=2, "back-and-forth wobble cancels without drift")
print("PASS: coherent slow movement, wobble cancellation, original speed response and bounded start")

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

// 7b. Ethan: "another tab will slide in and my mouse will still be over the
// close button but it won't send a click again ... 300 milliseconds". The
// first stop-to-click is the unchanged 111 signal; while the pointer stays
// settled and samples stay fresh it repeats every 300 ms, timed from each
// click, with no catch-up burst. Pure state only: nothing is clicked here.
do {
    func settled(_ d: WandDwellClick, from start: Double) -> Double {
        d.follow(true); var t = start
        for _ in 0..<5 { d.move(dx: 4, dy: 0, now: t, eligible: true); t += 0.01 } // 20 counts of travel
        return t
    }
    func run(_ d: WandDwellClick, until end: Double, from t0: Double, sample: (Double) -> (dx: Int, eligible: Bool)? = { _ in (0, true) }) -> [Double] {
        var t = t0, clicks: [Double] = []
        while t < end {
            if let due = d.nextDue, due <= t, d.tick(now: due) { clicks.append(due) }
            if let s = sample(t) { d.move(dx: s.dx, dy: 0, now: t, eligible: s.eligible) }
            t += 0.0096
        }
        return clicks
    }
    let d = WandDwellClick(repeatInterval: 0.3)
    let start = settled(d, from: 10)
    let clicks = run(d, until: start + 1.2, from: start)
    precondition(clicks.count == 4, "first click then repeats while settled: \(clicks.map { $0 - start })")
    precondition(abs(clicks[0] - (start - 0.01 + 0.2)) < 0.02, "the first click keeps the 111 timing")
    for i in 1..<clicks.count { precondition(abs(clicks[i] - clicks[i - 1] - 0.3) < 0.011, "repeats every 300 ms from the actual click") }

    let moved = WandDwellClick(repeatInterval: 0.3)
    let s2 = settled(moved, from: 20)
    let afterMove = run(moved, until: s2 + 1.2, from: s2) { t in (t > s2 + 0.3 && t < s2 + 0.32) ? (1, true) : (0, true) }
    precondition(afterMove.count == 1, "movement ends the repeats: \(afterMove.count)")

    let hud = WandDwellClick(repeatInterval: 0.3)
    let s3 = settled(hud, from: 30)
    let hidden = run(hud, until: s3 + 1.2, from: s3) { t in (0, t < s3 + 0.3) }
    precondition(hidden.count == 1, "an ineligible sample (HUD, button, scroll) ends the repeats")

    let stale = WandDwellClick(repeatInterval: 0.3)
    let s4 = settled(stale, from: 40)
    let lost = run(stale, until: s4 + 1.2, from: s4) { t in t < s4 + 0.25 ? (0, true) : nil }
    precondition(lost.count == 1 && !stale.repeating, "stale telemetry stops the repeats: \(lost.count)")

    let late = WandDwellClick(repeatInterval: 0.3)
    let s5 = settled(late, from: 50)
    _ = run(late, until: s5 + 0.25, from: s5)
    for t in stride(from: s5 + 0.25, to: s5 + 1.5, by: 0.01) { late.move(dx: 0, dy: 0, now: t, eligible: true) } // timer starved
    precondition(late.tick(now: s5 + 1.5) && !late.tick(now: s5 + 1.5), "a late timer clicks once, never a burst")
    precondition(abs((late.nextDue ?? 0) - (s5 + 1.8)) < 1e-9, "the next repeat is timed from the actual click")

    let intent = WandDwellClick(repeatInterval: 0.3)
    let s6 = settled(intent, from: 60)
    _ = run(intent, until: s6 + 0.25, from: s6)
    intent.intent(true, now: s6 + 0.26)
    precondition(!intent.repeating, "deliberate motion intent ends the repeats")

    let shot = WandDwellClick()
    let s7 = settled(shot, from: 70)
    precondition(run(shot, until: s7 + 1.2, from: s7).count == 1, "screenshot settling never repeats")
    print("PASS: settled stop-to-click repeats every 300 ms and stops on movement, HUD, stale input and intent")
}

// 7a. Coherent fine aiming, then settling: the pointer visibly creeps toward
// the target, and the old (111) tuned stop signal still clicks once after the
// hand settles, never during the deliberate slow approach.
do {
    let f = filter(.direct), dwell = WandDwellClick(); dwell.follow(true)
    var now = 100.0, clickTimes: [Double] = [], aimCounts = 0, settledCounts = 0, lastAim = 0.0
    for i in 0..<Int(4 * 104) {
        let phase = i < 31 ? 40.0 : (i < 31 + 156 ? 1.5 : 0.2 + 0.7 * sin(Double(i) * 0.9))
        let s = f.sample(rawX: Int((bias[0] + phase * counts).rounded()), rawY: Int(bias[1]), microseconds: 9615, held: false, resetState: false)!
        if i >= 31 && i < 31 + 156 { aimCounts += abs(s.x); if s.x != 0 { lastAim = now } }
        if i > 31 + 156 + 20 { settledCounts += abs(s.x) + abs(s.y) }
        if let due = dwell.nextDue, due <= now, dwell.tick(now: due) { clickTimes.append(due) }
        dwell.intent(s.intent, now: now)
        dwell.move(dx: s.stopX, dy: s.stopY, now: now, eligible: true)
        now += 0.009615
    }
    precondition(aimCounts >= 3, "coherent 1.5-unit fine aiming visibly moves the pointer: \(aimCounts)")
    precondition(settledCounts == 0, "settled tremor and zero error never move it")
    precondition(clickTimes.count == 1, "one stop-to-click for the whole approach: \(clickTimes)")
    precondition(clickTimes[0] > lastAim + 0.15, "the click follows the settle, never the slow approach")
    print("PASS: coherent fine aiming then settling clicks once with the 111 stop signal (last aim \(lastAim - 100), click \(clickTimes[0] - 100))")
}

// 8. The tuned path is unchanged and reports its own counts as stop counts.
let tuned = filter(.tuned)
for _ in 0..<52 {
    let s = tuned.sample(rawX: Int(bias[0] + 10 * counts), rawY: Int(bias[1]), microseconds: 9615, held: false, resetState: false)!
    precondition(s.stopX == s.x && s.stopY == s.y)
}
precondition(WandPointerPath.read(nil, default: .direct) == .direct && WandPointerPath.read("tuned", default: .direct) == .tuned &&
             WandPointerPath.read("smoothed", default: .tuned) == .tuned)
print("PASS: tuned path unchanged; option values parse strictly")
