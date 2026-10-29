import Foundation

// Sense wire protocol "wand-sense-1" (device/sense/wand_sense/wand_sense.ino).
// Pure parsing and state; no transport, timers or native input here.
//
// Device lines (each preceded by a newline for framing recovery):
//   I{json}  identity: protocol, firmware, id, gyroDpsPerLsb, accelGPerLsb, odr, wake
//   S seq,us,buttons,pressD8,pressD9,pressD10,imuFlags,ax,ay,az,gx,gy,gz
//   V millivolts,charging
//   E text   firmware event (logged only)
// Host commands: ? identity, H heartbeat, Lrrggbb light, M0/M1/M2 sensor, Z sleep, X end.
//
// Wire channel names stay the dashboard's legacy wand-v1 keys: thumb=D8,
// index=D9, middle=D10. They do NOT name fingers. Ethan's assembled wand:
// D8 = middle finger = Bottom (mouse), D9 = thumb = Top (speech),
// D10 = index finger = Middle (HUD/review). User-corrected — 2026-10-29.

struct WandSenseInfo: Equatable {
    static let protocolName = "wand-sense-1"
    let firmware: String
    let id: String
    let gyroDpsPerLsb: Double
    let accelGPerLsb: Double
    let odr: Double
    let wake: Bool
    /// False when the board's built-in IMU did not start: buttons still work,
    /// pointing does not. The receiver reports it instead of implying motion.
    var motion = true
    static func parse(_ json: String) -> WandSenseInfo? {
        guard json.utf8.count <= 512, let data = json.data(using: .utf8),
              let v = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
              v["protocol"] as? String == protocolName,
              let firmware = v["firmware"] as? String, firmware.count <= 48,
              let id = v["id"] as? String, id.count == 16, id.allSatisfy({ $0.isHexDigit }),
              let gyro = (v["gyroDpsPerLsb"] as? NSNumber)?.doubleValue, gyro > 0, gyro < 1,
              let accel = (v["accelGPerLsb"] as? NSNumber)?.doubleValue, accel > 0, accel < 0.01 else { return nil }
        let odr = (v["odr"] as? NSNumber)?.doubleValue ?? 104
        var info = WandSenseInfo(firmware: firmware, id: id.lowercased(), gyroDpsPerLsb: gyro, accelGPerLsb: accel,
                                 odr: odr, wake: v["wake"] as? Bool ?? false)
        info.motion = v["imu"] as? Bool ?? false
        return info
    }
}

struct WandSenseFrame: Equatable {
    let seq: UInt32
    let micros: UInt32
    /// Physical channels: bit0 D8, bit1 D9, bit2 D10 (pressed = 1).
    let wire: Int
    let presses: [UInt32]
    let accel: [Int]?
    let gyro: [Int]?
    static func parse(_ body: Substring) -> WandSenseFrame? {
        let f = body.split(separator: ",", omittingEmptySubsequences: false)
        guard f.count == 13, let seq = UInt32(f[0]), let us = UInt32(f[1]), let wire = Int(f[2]), (0...7).contains(wire),
              let p0 = UInt32(f[3]), let p1 = UInt32(f[4]), let p2 = UInt32(f[5]), let flags = Int(f[6]), (0...3).contains(flags) else { return nil }
        let axes = f[7...12].compactMap { Int($0) }
        guard axes.count == 6, axes.allSatisfy({ (-32768...32767).contains($0) }) else { return nil }
        return .init(seq: seq, micros: us, wire: wire, presses: [p0, p1, p2],
                     accel: flags & 1 != 0 ? Array(axes[0...2]) : nil, gyro: flags & 2 != 0 ? Array(axes[3...5]) : nil)
    }
}

enum WandSenseLine: Equatable {
    case info(WandSenseInfo), frame(WandSenseFrame), battery(millivolts: Int, charging: Bool), event(String)
    static func parse(_ raw: String) -> WandSenseLine? {
        let line = raw.trimmingCharacters(in: CharacterSet(charactersIn: "\r\n "))
        guard let head = line.first, line.utf8.count <= 600 else { return nil }
        let body = line.dropFirst()
        switch head {
        case "I": return WandSenseInfo.parse(String(body)).map { .info($0) }
        case "S": return WandSenseFrame.parse(body).map { .frame($0) }
        case "V":
            let f = body.split(separator: ",")
            guard f.count == 2, let mv = Int(f[0]), (0...6000).contains(mv), f[1] == "0" || f[1] == "1" else { return nil }
            return .battery(millivolts: mv, charging: f[1] == "1")
        case "E": return .event(String(body.prefix(80)))
        default: return nil
        }
    }
}

enum WandSenseCommand {
    static let identify = "?", heartbeat = "H", sleep = "Z", end = "X"
    static func sensor(_ mode: Int) -> String { "M" + String(max(0, min(2, mode))) }
    static func light(_ rgb: (UInt8, UInt8, UInt8)) -> String { String(format: "L%02x%02x%02x", rgb.0, rgb.1, rgb.2) }
}

/// Wire channel to canonical control. Logical mask: Bottom 1, Middle 2, Top 4,
/// the Puck's own @IMU mask (D1 MOVE, D2 HUD, D30 STT).
enum WandSenseButtons {
    static let bottom = 1, middle = 2, top = 4
    /// D8 Bottom, D9 Top, D10 Middle (Ethan's assembled wiring).
    static let wireToLogical = [bottom, top, middle]
    static func logical(_ wire: Int) -> Int {
        (0..<3).reduce(0) { wire & (1 << $1) != 0 ? $0 | wireToLogical[$1] : $0 }
    }
}

/// Sense IMU axes into the Puck's body frame (x right, y toward the tip, z up),
/// so the unchanged Puck CONFIG, gains, calibration and gravity logic apply.
/// Each entry names the Sense axis and sign for Puck x, y and z.
struct WandSenseAxes: Equatable {
    /// Unverified default: board along the shaft, USB toward the tip, parts up.
    /// Check physically and set "axes" in device.json if the pointer is rotated.
    static let standard = WandSenseAxes(map: [(1, -1), (0, 1), (2, 1)])!
    let map: [(axis: Int, sign: Int)]
    static func == (a: WandSenseAxes, b: WandSenseAxes) -> Bool { a.signature == b.signature }
    init?(map: [(Int, Int)]) {
        guard map.count == 3, Set(map.map { $0.0 }) == [0, 1, 2], map.allSatisfy({ abs($0.1) == 1 }) else { return nil }
        // A rotation, not a mirror: x = y × z must hold for the Puck frame.
        var m = [[Int]](repeating: [0, 0, 0], count: 3)
        for (row, entry) in map.enumerated() { m[row][entry.0] = entry.1 }
        let det = m[0][0]*(m[1][1]*m[2][2]-m[1][2]*m[2][1]) - m[0][1]*(m[1][0]*m[2][2]-m[1][2]*m[2][0]) + m[0][2]*(m[1][0]*m[2][1]-m[1][1]*m[2][0])
        guard det == 1 else { return nil }
        self.map = map.map { (axis: $0.0, sign: $0.1) }
    }
    /// ["-y", "+x", "+z"] style text from device.json.
    init?(text: [String]) {
        var entries: [(Int, Int)] = []
        for t in text {
            guard t.count == 2, let s = t.first, s == "+" || s == "-", let a = "xyz".firstIndex(of: t.last!) else { return nil }
            entries.append(("xyz".distance(from: "xyz".startIndex, to: a), s == "+" ? 1 : -1))
        }
        self.init(map: entries)
    }
    var signature: String { map.map { ($0.sign > 0 ? "p" : "n") + ["x", "y", "z"][$0.axis] }.joined() }
    func apply(_ v: [Double]) -> [Double] { map.map { Double($0.sign) * v[$0.axis] } }
}

/// Converts physical Sense readings to the Puck's documented units:
/// 8192 per g and 134 per degree/second, saturating like its int16 sensor.
enum WandSenseUnits {
    static func puck(_ value: Double, scale: Double) -> Int {
        guard value.isFinite else { return 0 }
        return Int(max(-32767, min(32767, (value * scale).rounded())))
    }
    static func accel(_ raw: [Int], info: WandSenseInfo, axes: WandSenseAxes) -> [Int] {
        axes.apply(raw.map { Double($0) * info.accelGPerLsb }).map { puck($0, scale: 8192) }
    }
    static func gyro(_ raw: [Int], info: WandSenseInfo, axes: WandSenseAxes) -> [Int] {
        axes.apply(raw.map { Double($0) * info.gyroDpsPerLsb }).map { puck($0, scale: 134) }
    }
}

/// Device reading time on the host's uptime clock. Uses the least-delayed
/// arrival as the offset, so a burst of readings keeps its real spacing.
/// It never waits for later data and never returns a future time.
struct WandSenseClock {
    private var offset: Double?, last: Double = -.infinity, lastArrival = 0.0
    private var high: UInt64 = 0, previous: UInt32?
    mutating func reset() { self = WandSenseClock() }
    mutating func align(micros: UInt32, arrival: Double) -> Double {
        if let p = previous, micros < p, p - micros > 0x8000_0000 { high += 1 << 32 }
        previous = micros
        let device = Double(high + UInt64(micros)) / 1_000_000
        let candidate = arrival - device
        if let o = offset, candidate >= o {
            // Allow 500 ppm crystal drift so the offset cannot become stale.
            offset = o + min(candidate - o, max(0, arrival - lastArrival) * 0.0005)
        } else { offset = candidate }
        lastArrival = arrival
        var t = device + (offset ?? candidate)
        t = min(t, arrival); t = max(t, last)
        last = t
        return t
    }
}

/// One host session's input safety. New sessions start with every held
/// button masked until it is physically released, so startup or reconnect
/// while held never presses, clicks or replays. Duplicate or old frames are
/// rejected. A press seen only in the board counter is restored as one short
/// press, and only inside continuous live telemetry.
struct WandSenseSession {
    struct Step: Equatable { let mask: Int; let synthetic: Bool }
    private var lastSeq: UInt32?, lastArrival: Double?, lastPresses: [UInt32]?
    private var masked = 0, lastWire = 0
    private(set) var rejected = 0, restoredPresses = 0, droppedPresses = 0
    mutating func reset() { self = WandSenseSession() }
    static let liveGap = 0.25
    mutating func accept(_ f: WandSenseFrame, arrival: Double) -> [Step]? {
        if let s = lastSeq {
            let delta = f.seq &- s
            guard delta != 0, delta < 0x8000_0000 else { rejected += 1; return nil }
        }
        let first = lastSeq == nil
        let live = lastArrival.map { arrival - $0 <= Self.liveGap } ?? false
        lastSeq = f.seq; lastArrival = arrival
        var steps: [Step] = []
        if first { masked = f.wire }
        masked &= f.wire // A release always unmasks that channel.
        if let before = lastPresses, !first {
            for channel in 0..<3 {
                let bit = 1 << channel, gained = f.presses[channel] &- before[channel]
                guard gained > 0, gained < 0x8000_0000 else { continue }
                // Seen as an edge already: it was up and is now down.
                let seen = lastWire & bit == 0 && f.wire & bit != 0
                let missing = Int(gained) - (seen ? 1 : 0)
                guard missing > 0, masked & bit == 0, f.wire & bit == 0 else { continue }
                if missing == 1 && live && lastWire & bit == 0 {
                    steps.append(.init(mask: WandSenseButtons.logical((lastWire & ~masked) | bit), synthetic: true))
                    restoredPresses += 1
                } else { droppedPresses += missing }
            }
        }
        lastPresses = f.presses; lastWire = f.wire
        steps.append(.init(mask: WandSenseButtons.logical(f.wire & ~masked), synthetic: false))
        return steps
    }
}

/// Puck light levels to the Sense RGB LED. Same meanings, Sense colours:
/// equal partial levels are the established orange (update, calibration,
/// disconnected); all full is the all-colours sleep warning.
enum WandSenseLight {
    static let orange: (UInt8, UInt8, UInt8) = (255, 80, 0)
    static func rgb(_ r: Double, _ g: Double, _ b: Double) -> (UInt8, UInt8, UInt8) {
        let v = [r, g, b].map { $0.isFinite ? max(0, min(1, $0)) : 0 }
        if v[0] == v[1] && v[1] == v[2] {
            if v[0] == 0 { return (0, 0, 0) }
            if v[0] >= 1 { return (255, 255, 255) }
            return orange
        }
        let c = v.map { UInt8(($0 * 255).rounded()) }
        return (c[0], c[1], c[2])
    }
}

/// The dashboard's existing wand-v1 packet, from the receiver's own data.
enum WandSenseDashboard {
    static func packet(_ f: WandSenseFrame, info: WandSenseInfo) -> [String: Any] {
        var imu: Any = NSNull()
        if let a = f.accel {
            let g = f.gyro ?? [0, 0, 0]
            imu = ["ax": Double(a[0]) * info.accelGPerLsb, "ay": Double(a[1]) * info.accelGPerLsb, "az": Double(a[2]) * info.accelGPerLsb,
                   "gx": Double(g[0]) * info.gyroDpsPerLsb, "gy": Double(g[1]) * info.gyroDpsPerLsb, "gz": Double(g[2]) * info.gyroDpsPerLsb]
        }
        return ["schema": 1, "sensor": "wand", "seq": Int(f.seq), "ms": Int(f.micros / 1000),
                "buttons": ["thumb": f.wire & 1 != 0, "index": f.wire & 2 != 0, "middle": f.wire & 4 != 0],
                "presses": ["thumb": Int(f.presses[0]), "index": Int(f.presses[1]), "middle": Int(f.presses[2])],
                "imu": imu, "firmware": info.firmware.filter { $0.isLetter || $0.isNumber }]
    }
}

/// Streaming newline framer with a bounded line length.
struct WandSenseFramer {
    private var buffer = [UInt8](), dropping = false
    mutating func reset() { buffer.removeAll(keepingCapacity: true); dropping = false }
    mutating func feed(_ bytes: UnsafeRawBufferPointer, _ line: (String) -> Void) {
        for byte in bytes {
            if byte == 10 {
                if !dropping && !buffer.isEmpty, let text = String(bytes: buffer, encoding: .utf8) { line(text) }
                buffer.removeAll(keepingCapacity: true); dropping = false
            } else if !dropping {
                buffer.append(byte)
                if buffer.count > 600 { buffer.removeAll(keepingCapacity: true); dropping = true }
            }
        }
    }
    mutating func feed(_ data: Data, _ line: (String) -> Void) { data.withUnsafeBytes { feed($0, line) } }
}
