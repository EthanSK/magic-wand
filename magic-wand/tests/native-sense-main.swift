import Foundation
import CryptoKit
setbuf(stdout, nil)
// Arguments: component root and repository root. Pure checks and an in-process
// JavaScriptCore program; no transport, hardware or native input.
let root = URL(fileURLWithPath: CommandLine.arguments[1]), repo = URL(fileURLWithPath: CommandLine.arguments[2])
func text(_ url: URL) -> String { try! String(contentsOf: url, encoding: .utf8) }

// Identity and frames
let identity = WandSenseLine.parse(#"I{"protocol":"wand-sense-1","firmware":"wand-sense-20261029a","id":"0123456789ABCDEF","imu":true,"gyroDpsPerLsb":0.00875,"accelGPerLsb":0.000122,"odr":104,"wake":false}"#)
guard case .info(let info)? = identity else { fatalError("identity") }
precondition(info.id == "0123456789abcdef")
precondition(WandSenseLine.parse(#"I{"protocol":"wand-v1","id":"0123456789abcdef"}"#) == nil, "other firmware rejected")
precondition(WandSenseLine.parse(#"{"sensor":"hand","ax":0}"#) == nil, "Control Hand packets rejected")
guard case .frame(let f)? = WandSenseLine.parse("S7,1000,5,1,0,2,3,10,20,8196,1000,-1000,0") else { fatalError("frame") }
precondition(f.seq == 7 && f.wire == 5 && f.presses == [1, 0, 2] && f.accel == [10, 20, 8196] && f.gyro == [1000, -1000, 0])
guard case .frame(let quiet)? = WandSenseLine.parse("S8,2000,0,1,0,2,0,0,0,0,0,0,0") else { fatalError("quiet frame") }
precondition(quiet.accel == nil && quiet.gyro == nil)
precondition(WandSenseLine.parse("S8,2000,9,1,0,2,0,0,0,0,0,0,0") == nil && WandSenseLine.parse("S1,2,3") == nil)
precondition(WandSenseLine.parse("V3912,1") == .battery(millivolts: 3912, charging: true))
guard case .frame(let run)? = WandSenseLine.parse("S9,100000,0,1,0,2,3,0,0,8196,500,0,0,4,71155") else { fatalError("merged frame") }
precondition(run.count == 4 && run.firstMicros == 71155 && run.gyro == [500, 0, 0])
guard case .frame(let one)? = WandSenseLine.parse("S10,109615,0,1,0,2,3,0,0,8196,500,0,0,1,109615") else { fatalError("single frame") }
precondition(one.count == 1 && one.firstMicros == nil)
precondition(WandSenseLine.parse("S9,100000,0,1,0,2,3,0,0,8196,500,0,0,0,71155") == nil, "zero-reading count rejected")
precondition(WandSenseReplay.times(last: 20, frame: run, after: 19.9, allowHistory: false) == [20], "a recovered button edge fences historical motion")
let spread = WandSenseReplay.times(last: 20.0, frame: run, after: 19.9)
precondition(spread.count == 4 && abs(spread[0] - 19.971155) < 1e-6 && spread[3] == 20.0, "merged run keeps its real spacing: \(spread)")
precondition(WandSenseReplay.times(last: 20.0, frame: run, after: 19.99).first! > 19.99, "never before the previous reading")
precondition(WandSenseReplay.times(last: 20.0, frame: one, after: 19.9) == [20.0])
print("PASS: identity, frame and battery parsing; other devices rejected")

// Ethan's assembled wiring: D8 Bottom, D9 Top, D10 Middle.
precondition(WandSenseButtons.logical(1) == WandSenseButtons.bottom)
precondition(WandSenseButtons.logical(2) == WandSenseButtons.top)
precondition(WandSenseButtons.logical(4) == WandSenseButtons.middle)
precondition(WandSenseButtons.logical(7) == 7)
print("PASS: D8 Bottom, D9 Top, D10 Middle")

// Axes and units
precondition(WandSenseAxes(text: ["-y", "+x", "+z"]) == .standard)
precondition(WandSenseAxes(text: ["+y", "+x", "+z"]) == nil, "mirror rejected")
precondition(WandSenseAxes(text: ["+x", "+x", "+z"]) == nil, "duplicate axis rejected")
// Same LSM6DS3TR-C as the Puck: one Puck count is 8.75 mdps (114.29 per deg/s).
let g = WandSenseUnits.gyro([1000, 0, 0], info: info, axes: .standard)
precondition(g == [0, 1000, 0], "a 245 dps Sense count is exactly one Puck count: \(g)")
guard case .info(var wide)? = identity else { fatalError() }
wide = WandSenseInfo(firmware: wide.firmware, id: wide.id, gyroDpsPerLsb: 0.0175, accelGPerLsb: 0.000122, odr: 104, wake: false)
precondition(WandSenseUnits.gyro([0, 32767, 0], info: wide, axes: .standard)[0] == -65534, "500 dps range keeps headroom above the Puck's 286.7 dps clip")
let legacy = WandSenseUnits.migrateLegacyZero(WandCalibration(x: 339.16, y: 252.41, z: -56.09))
precondition(abs(legacy.x - 289.26) < 0.05 && abs(legacy.z + 47.84) < 0.05, "134-per-dps zero converted to Puck counts: \(legacy)")
precondition(WandSenseTuning.defaultPointerGain * 86.4 * WandSenseUnits.gyroCountsPerDps / 134 > 107.9, "25% above the installed Sense build's 86.4 counts per degree")
precondition(WandSenseUnits.accel([0, 0, 8196], info: info, axes: .standard) == [0, 0, 8191])
print("PASS: rotation-only axis map, Puck units and saturation")

// Clock: a burst keeps its real spacing, never in the future, survives wrap.
var clock = WandSenseClock()
let a = clock.align(micros: 1_000_000, arrival: 50.010)
let b = clock.align(micros: 1_009_615, arrival: 50.030)
let c = clock.align(micros: 1_019_230, arrival: 50.030)
precondition(abs(a - 50.010) < 1e-9 && abs((c - b) - 0.009615) < 1e-6 && c <= 50.030, "\(a) \(b) \(c)")
var wrap = WandSenseClock()
let w0 = wrap.align(micros: UInt32.max - 4_000, arrival: 10), w1 = wrap.align(micros: 5_615, arrival: 10.0097)
precondition(abs((w1 - w0) - 0.009616) < 1e-5, "micros wrap")
print("PASS: device-time alignment without waiting")

// Session safety
func frame(_ seq: UInt32, _ wire: Int, _ presses: [UInt32]) -> WandSenseFrame {
    .init(seq: seq, micros: seq * 9615, wire: wire, presses: presses, accel: nil, gyro: nil)
}
var s = WandSenseSession()
precondition(s.accept(frame(1, 1, [4, 0, 0]), arrival: 1) == [.init(mask: 0, synthetic: false)], "held at start is masked")
precondition(s.accept(frame(1, 1, [4, 0, 0]), arrival: 1.01) == nil, "duplicate rejected")
precondition(s.accept(frame(2, 1, [4, 0, 0]), arrival: 1.02) == [.init(mask: 0, synthetic: false)])
precondition(s.accept(frame(3, 0, [4, 0, 0]), arrival: 1.03) == [.init(mask: 0, synthetic: false)], "masked release never acts")
precondition(s.accept(frame(4, 1, [5, 0, 0]), arrival: 1.04) == [.init(mask: 1, synthetic: false)], "next press is real")
precondition(s.accept(frame(5, 0, [5, 0, 0]), arrival: 1.05) == [.init(mask: 0, synthetic: false)])
// A whole press between two live frames is restored once, as a short press.
precondition(s.accept(frame(6, 0, [5, 1, 0]), arrival: 1.10) == [.init(mask: 4, synthetic: true), .init(mask: 0, synthetic: false)])
// After a gap it is dropped, never replayed late.
precondition(s.accept(frame(7, 0, [5, 2, 0]), arrival: 3.0) == [.init(mask: 0, synthetic: false)] && s.droppedPresses == 1)
precondition(s.accept(frame(1, 0, [5, 2, 0]), arrival: 3.01) == nil, "older sequence rejected")
s.reset()
precondition(s.accept(frame(1, 0, [9, 9, 9]), arrival: 4) == [.init(mask: 0, synthetic: false)], "a new session replays no counters")
print("PASS: startup hold masked, duplicates rejected, missed short press restored only while live")

// Lights
precondition(WandSenseLight.rgb(0.45, 0.45, 0.45) == WandSenseLight.orange)
precondition(WandSenseLight.rgb(1, 1, 1) == (255, 255, 255) && WandSenseLight.rgb(0, 0, 0) == (0, 0, 0))
precondition(WandSenseLight.rgb(1, 0, 0) == (255, 0, 0) && WandSenseLight.rgb(0, 0, 1) == (0, 0, 255))
precondition(WandSenseCommand.light(WandSenseLight.rgb(1, 0.2, 0)) == "Lff3300")
let packet = WandSenseDashboard.packet(f, info: info)
precondition((packet["buttons"] as! [String: Bool]) == ["thumb": true, "index": false, "middle": true])
precondition(JSONSerialization.isValidJSONObject(packet))
print("PASS: Puck light meanings on the RGB LED; dashboard keeps wand-v1 keys")

// The canonical program in JavaScriptCore.
let bridge = text(root.appendingPathComponent("device/generated/wand-mode-bridge.compact.js"))
let sources = WandVirtualPuck.Sources(shim: text(repo.appendingPathComponent("docs/sim/espruino.js")),
    host: text(root.appendingPathComponent("device/sense/wand-sense-host.js")),
    base: text(root.appendingPathComponent("device/wand-mouse-prototype.js")), bridge: bridge,
    power: text(root.appendingPathComponent("device/generated/wand-power-policy.compact.js")))
let runtime = text(root.appendingPathComponent("device/generated/wand-runtime-version.txt")).trimmingCharacters(in: .whitespacesAndNewlines)
let revision = SHA256.hash(data: Data(bridge.utf8)).map { String(format: "%02x", $0) }.joined()
guard let puck = WandVirtualPuck(sources: sources) else { fatalError("JavaScriptCore") }
var lines: [String] = [], lights: [[Double]] = [], sensor: [Int] = [], sleeps = 0, logs: [String] = []
puck.onText = { lines += $0.split(separator: "\n").map(String.init) }
puck.onLight = { lights.append([$0, $1, $2]) }
puck.onSensor = { sensor.append($0) }
puck.onSleep = { sleeps += 1 }
puck.onLog = { logs.append($0) }
func spin(_ seconds: Double) { RunLoop.main.run(until: Date().addingTimeInterval(seconds)) }
precondition(puck.boot(sources, zero: #"{"x":0,"y":0,"z":0}"#, runtime: runtime, revision: revision), logs.joined(separator: "\n"))
precondition(sensor.last == 1, "connected and calibrated: desk accelerometer only")
puck.send("\u{03}\u{03}\n\u{10}global.WAND_UPDATING=true;if(typeof loadingLight==='function')loadingLight();")
puck.send("if(global.WAND_RUNTIME_VERSION===\"" + runtime + "\"){if(!global.wandBridgeOriginalSend)global.wandBridgeOriginalSend=mouse.send;mouse.send=function(x,y,b,cb){Bluetooth.println(\"@WAND \"+x+\",\"+y+\",\"+b);if(cb)cb();};if(!connected)onConnect();print(\"WAND_BRIDGE_READY\");}else print(\"WAND_NEEDS_CONFIG\");")
puck.send("if(global.WAND_BRIDGE_REVISION==='" + revision + "'&&global.wandMotionReady!==false)print('WAND_MODE_ROUTING_READY');else print('WAND_PATCH_NEEDED');")
spin(0.3)
precondition(lines.contains("WAND_BRIDGE_READY") && lines.contains("WAND_MODE_ROUTING_READY"), lines.joined(separator: "\n"))
precondition(lights.contains(where: { $0 == [0.45, 0.45, 0.45] }), "loading blinks the established orange")
puck.send("global.wandShot=0;global.wandRawPointer=true;global.wandRawBias=undefined;global.wandRawActive=false;global.WAND_UPDATING=false;setHUDOpen(false);updateLights();")
spin(0.05)
precondition(lights.last == [0, 0, 0], "ready idle is dark")
var t = ProcessInfo.processInfo.systemUptime
func deliver(_ mask: Int, gyro: [Int]? = [0, 0, 0]) { t = max(t + 1 / 104, ProcessInfo.processInfo.systemUptime); puck.deliver(time: t, mask: mask, accel: [0, 0, 8192], gyro: gyro) }
lines.removeAll()
deliver(1); spin(0.03); deliver(0); spin(0.05)
precondition(lines.contains("@BOTTOM 1") && lines.contains("@BOTTOM 0"), lines.joined(separator: "\n"))
precondition(sensor.last == 2, "follow wakes the gyro at 104 Hz")
lines.removeAll()
spin(0.15)
for _ in 0..<12 { deliver(0, gyro: [0, 0, -4020]); spin(0.0096) }
spin(0.02)
precondition(lines.filter { $0.hasPrefix("@RAW ") }.count >= 8, lines.joined(separator: "\n"))
lines.removeAll()
deliver(1); deliver(3); deliver(7); spin(0.5)
precondition(sleeps == 1 && lines.contains("WAND_POWER_STANDBY_ENTERED"), "all three request button-wake sleep")
precondition(lights.contains(where: { $0 == [1, 1, 1] }), "all-colours warning")
let afterLights = lights.count
puck.teardown(); spin(0.3)
deliver(0); puck.send("print('late')"); spin(0.05)
precondition(lights.count == afterLights && !lines.contains("late"), "teardown leaves no timers or output")
precondition(logs.isEmpty, logs.joined(separator: "\n"))
print("PASS: canonical Puck program boots, hands shake, routes Sense buttons and motion, sleeps and tears down")
