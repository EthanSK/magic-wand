import Foundation
import CryptoKit
setbuf(stdout, nil)
// Arguments: component root, repository root. The receiver's own senseLine
// (inserted by the test) routes synthetic Sense frames into the canonical
// program in JavaScriptCore. Its @RAW output goes through the real pointer
// filter. No transport, hardware or native input.
let root = URL(fileURLWithPath: CommandLine.arguments[1]), repo = URL(fileURLWithPath: CommandLine.arguments[2])
func text(_ url: URL) -> String { try! String(contentsOf: url, encoding: .utf8) }
func log(_ values: Any...) {}
func spin(_ seconds: Double) { RunLoop.main.run(until: Date().addingTimeInterval(seconds)) }
var clock: Double { ProcessInfo.processInfo.systemUptime }
func until(_ t: Double) { while clock < t { RunLoop.main.run(until: Date().addingTimeInterval(min(0.002, max(0.0002, t - clock)))) } }

let info: WandSenseInfo = {
    guard case .info(let value)? = WandSenseLine.parse(#"I{"protocol":"wand-sense-1","firmware":"wand-sense-test","id":"0123456789ABCDEF","imu":true,"gyroDpsPerLsb":0.00875,"accelGPerLsb":0.000122,"odr":104,"wake":false}"#) else { fatalError("identity") }
    return value
}()
let bridge = text(root.appendingPathComponent("device/generated/wand-mode-bridge.compact.js"))
let sources = WandVirtualPuck.Sources(shim: text(repo.appendingPathComponent("docs/sim/espruino.js")),
    host: text(root.appendingPathComponent("device/sense/wand-sense-host.js")),
    base: text(root.appendingPathComponent("device/wand-mouse-prototype.js")), bridge: bridge,
    power: text(root.appendingPathComponent("device/generated/wand-power-policy.compact.js")))
let runtime = text(root.appendingPathComponent("device/generated/wand-runtime-version.txt")).trimmingCharacters(in: .whitespacesAndNewlines)
let revision = SHA256.hash(data: Data(bridge.utf8)).map { String(format: "%02x", $0) }.joined()

// Receiver state the extracted senseLine reads. Gesture state changes only when
// the program's output is handled on a later turn, as in the receiver.
final class Flag { var active = false }
final class Router { var mouseButtonHeld = false }
final class Shot { var ownsPointer = false }
final class Dwell { var following = false }
final class Pause { var paused = false }
final class Recording { var isRecording = false }
struct PathName { var rawValue = "direct" }
final class PathHolder { var path = PathName() }
struct Settings { var senseAxes = WandSenseAxes.standard }
final class Dashboard { func packet(_ v: [String: Any]) {} }
enum Transport: String { case bluetooth = "Bluetooth" }
final class Receiver {
    var senseVirtual: WandVirtualPuck?
    var senseInfo: WandSenseInfo?
    let senseDashboard = Dashboard()
    var senseTransport: Transport? = .bluetooth
    var senseSessionNumber = 1, movementCount = 0, pointerTravel = 0.0
    let dwell = Dwell(), actionPause = Pause(), recording = Recording(), motionFilter = PathHolder()
    var hudSession = false, scrollActive = false
    var senseStaleReadings = 0
    var senseSession = WandSenseSession(), senseClock = WandSenseClock()
    let deviceSettings = Settings()
    let heldScroll = Flag(), pointerRouter = Router(), screenshot = Shot()
    var senseLastReading = -Double.infinity
    var senseMouseButtonTimer = WandSenseMouseButtonTimer()
    func senseUpdateReply(_ reply: WandSenseUpdateReply) {}
    func senseUpdateBattery(millivolts: Int, charging: Bool) {}
/*SENSE_LINE*/
}

/// One receiver + program. Output lines are handled when the program flushes them
/// (the next main-queue turn): @BOTTOM 1 starts the host hold, @BOTTOM 0 ends it and
/// sends the completed-scroll follow command, and @RAW drives the real filter.
final class Rig {
    let r = Receiver(), filter = WandMotionFilter()
    let puck: WandVirtualPuck
    var lines: [String] = []
    /// Posted |x|+|y| per @RAW line, in output order, with its flags.
    var raws: [(index: Int, counts: Int, flags: Int, rawX: Int)] = []
    private var seq: UInt32 = 0, presses: UInt32 = 0, wire = 0
    private let t0 = clock
    init() {
        guard let p = WandVirtualPuck(sources: sources) else { fatalError("JavaScriptCore") }
        puck = p
        filter.path = .direct
        p.onText = { [unowned self] chunk in
            for line in chunk.split(separator: "\n").map(String.init) {
                self.lines.append(line)
                if line == "@BOTTOM 1" { self.r.heldScroll.active = true }
                if line == "@BOTTOM 0" && self.r.heldScroll.active {
                    self.r.heldScroll.active = false
                    self.puck.send("global.wandPointerPauseUntil=0;setMouseFollow(true);") // restoreMouseAfterScroll
                }
                if let m = line.range(of: "@ZERO "), let d = String(line[m.upperBound...]).data(using: .utf8),
                   let v = try? JSONDecoder().decode([Double].self, from: d) { precondition(self.filter.configure(v), line) }
                if let m = line.range(of: "@RAW ") {
                    let v = line[m.upperBound...].split(separator: ",").compactMap { Int($0) }
                    precondition(v.count == 4, line)
                    let s = self.filter.sample(rawX: v[1], rawY: v[2], microseconds: v[0], held: v[3] & 1 != 0, resetState: v[3] & 2 != 0)
                    self.raws.append((self.lines.count - 1, v[3] & 1 != 0 ? 0 : abs(s?.x ?? 0) + abs(s?.y ?? 0), v[3], v[1]))
                }
            }
        }
        precondition(p.boot(sources, zero: #"{"x":0,"y":0,"z":0}"#, runtime: runtime, revision: revision, pointerGain: 1.52425))
        p.send("if(global.WAND_RUNTIME_VERSION===\"" + runtime + "\"){if(!global.wandBridgeOriginalSend)global.wandBridgeOriginalSend=mouse.send;mouse.send=function(x,y,b,cb){Bluetooth.println(\"@WAND \"+x+\",\"+y+\",\"+b);if(cb)cb();};if(!connected)onConnect();print(\"WAND_BRIDGE_READY\");}else print(\"WAND_NEEDS_CONFIG\");")
        p.send("if(global.WAND_BRIDGE_REVISION==='" + revision + "'&&global.wandMotionReady!==false)print('WAND_MODE_ROUTING_READY');else print('WAND_PATCH_NEEDED');")
        spin(0.2)
        precondition(lines.contains("WAND_MODE_ROUTING_READY"), lines.joined(separator: "\n"))
        p.send("global.wandShot=0;global.wandRawPointer=true;global.wandRawBias=undefined;global.wandRawActive=false;global.WAND_UPDATING=false;setHUDOpen(false);updateLights();")
        p.send("global.wandHostHeldScroll=true;global.wandDoubleClickSeconds=0.3;")
        r.senseVirtual = p; r.senseInfo = info
    }
    /// One frame whose last reading is at device time `t` (host clock). `gz`: deg/s
    /// about the board's z axis (pointer x). `span` > 0 makes a merged run.
    func send(wire w: Int, gz: Double, at t: Double, count: Int = 1, span: Double = 0, arrival: Double? = nil) {
        if w & 1 != 0 && wire & 1 == 0 { presses += 1 }
        wire = w; seq += 1
        let us = UInt32(((t - t0) + 1) * 1_000_000), g = Int((gz / 0.00875).rounded())
        var body = "S\(seq),\(us),\(w),\(presses),0,0,3,0,0,8197,0,0,\(g)"
        if count > 1 { body += ",\(count),\(us &- UInt32(span * 1_000_000))" }
        guard case .frame(let f)? = WandSenseLine.parse(body) else { fatalError(body) }
        r.senseLine(.frame(f), arrival ?? clock)
    }
    /// On-time frames every 1/104 s for `seconds`; returns the last reading time.
    @discardableResult func paced(wire w: Int, gz: Double, seconds: Double, from start: Double) -> Double {
        var t = start
        for k in 1...max(1, Int((seconds * 104).rounded())) { t = start + Double(k) / 104; until(t + 0.001); send(wire: w, gz: gz, at: t) }
        return t
    }
    /// Idle, a tap that turns follow on, then a fast held stroke of 0.35 s.
    func heldStroke() -> Double {
        var t = paced(wire: 0, gz: 0, seconds: 0.1, from: clock)
        t = paced(wire: 1, gz: 0, seconds: 0.03, from: t)
        t = paced(wire: 0, gz: 0, seconds: 0.45, from: t)
        precondition(lines.contains("@BOTTOM 0") && !r.heldScroll.active, "tap handled")
        r.dwell.following = true
        r.heldScroll.active = false
        t = paced(wire: 1, gz: -120, seconds: 0.35, from: t)
        precondition(r.heldScroll.active && raws.contains { $0.flags & 1 != 0 }, "host-held stroke streams held @RAW: \(lines.suffix(5))")
        return t
    }
    func rawsAfter(_ index: Int) -> [(index: Int, counts: Int, flags: Int, rawX: Int)] { raws.filter { $0.index >= index } }
}

func json(_ v: [String: Any]) -> String { String(data: try! JSONSerialization.data(withJSONObject: v, options: [.sortedKeys]), encoding: .utf8)! }

// 1. Pure policy: the change is confined to frames that show the physical release
//    while the host still holds a gesture.
var differs: [String] = []
for bits in 0..<64 {
    let b = (0..<6).map { bits & (1 << $0) != 0 }
    let fixed = WandSensePointerFrames.pointerOwns(following: b[0], hudSession: b[1], scrollActive: b[2], hostHolding: b[3], frameMouseButtonDown: b[4], screenshot: b[5])
    let original = b[0] && !b[1] && !b[2] && !b[3] && !b[5]
    if fixed != original { differs.append("\(b.map { $0 ? 1 : 0 })") }
}
precondition(differs == ["[1, 0, 0, 1, 0, 0]"], "only following + host holding + frame released changes: \(differs)")
print("PASS: frame policy differs only for a released frame during a host-held gesture; HUD, chord scroll and screenshot keep history")

// 2. A merged run that contains the release (radio stall during the stroke's end).
do {
    let g = Rig()
    let t = g.heldStroke()
    // Held merged frame: history kept and every reading still reaches the scroll.
    until(t + 0.04 + 0.001)
    let heldMark = g.lines.count
    g.send(wire: 1, gz: -120, at: t + 0.04, count: 4, span: 0.03); spin(0.01)
    let heldReplayed = g.rawsAfter(heldMark).filter { $0.flags & 1 != 0 }.count
    let releaseT = t + 0.04 + 0.6
    until(releaseT + 0.003)
    let mark = g.lines.count, staleBefore = g.r.senseStaleReadings
    g.send(wire: 0, gz: -80, at: releaseT, count: 60, span: 0.58)
    let alignedRelease = g.r.senseLastReading
    spin(0.01)
    guard let edge = g.lines[mark...].firstIndex(of: "@BOTTOM 0") else { fatalError("release delivered: \(g.lines[mark...])") }
    let obsolete = g.rawsAfter(edge)
    // Fresh readings delivered on time after the release has been handled.
    var firstFresh: Double?, firstFreshFlags = -1, freshCounts = 0
    for k in 1...25 {
        let tk = releaseT + Double(k) / 104
        until(tk + 0.002)
        let before = g.raws.count
        g.send(wire: 0, gz: -20, at: tk); spin(0.002)
        let new = g.raws[before...]
        if firstFresh == nil, let first = new.first { firstFresh = g.r.senseLastReading - alignedRelease; firstFreshFlags = first.flags }
        freshCounts += new.map { $0.counts }.reduce(0, +)
    }
    print("RESULT merged " + json(["heldReplayed": heldReplayed, "obsoleteRaw": obsolete.count,
        "obsoleteCounts": obsolete.map { $0.counts }.reduce(0, +), "staleDropped": g.r.senseStaleReadings - staleBefore,
        "firstFreshMs": (firstFresh ?? -1) * 1000, "firstFreshFlags": firstFreshFlags, "freshCounts": freshCounts]))
}

// 3. A stall ends with the release and 50 post-release readings in one batch.
do {
    let g = Rig()
    let t = g.heldStroke()
    let releaseT = t + 1.0 / 104
    until(releaseT + 0.5)
    let arrival = clock, mark = g.lines.count, staleBefore = g.r.senseStaleReadings
    g.send(wire: 0, gz: -120, at: releaseT, arrival: arrival)
    let alignedRelease = g.r.senseLastReading
    var aligned: [Double] = []
    for k in 1...50 { g.send(wire: 0, gz: -20, at: releaseT + Double(k) / 104, arrival: arrival); aligned.append(g.r.senseLastReading) }
    spin(0.01)
    guard let edge = g.lines[mark...].firstIndex(of: "@BOTTOM 0") else { fatalError("release delivered") }
    let batch = g.rawsAfter(edge)
    // The program's clutch release pauses pointing 0.3 s until the receiver clears it.
    let pastPause = aligned.filter { $0 >= alignedRelease + 0.3 }
    let fresh = pastPause.filter { arrival - $0 <= WandSenseStaleness.limit }
    let stale = ([alignedRelease] + aligned).filter { arrival - $0 > WandSenseStaleness.limit }.count
    print("RESULT batch " + json(["batchRaw": batch.count, "batchCounts": batch.map { $0.counts }.reduce(0, +),
        "expectedAllPastPause": pastPause.count, "expectedFreshPastPause": fresh.count,
        "staleDropped": g.r.senseStaleReadings - staleBefore, "expectedStale": stale]))
}
print("DONE")
