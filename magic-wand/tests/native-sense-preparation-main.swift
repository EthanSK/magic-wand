import Foundation
import CryptoKit
var logs: [String] = []
func log(_ values: Any...) { logs.append(values.map { String(describing: $0) }.joined(separator: " ")) }
final class WandSenseLink {
    enum Transport { case usb, bluetooth }
    var active: Transport? = .bluetooth
    var commands: [String] = []
    func send(_ command: String) { commands.append(command) }
    func prepareUpdate(_ package: WandSenseDFUPackage) -> WandSenseDFUTransfer? { nil }
    func finishUpdate() {}
}
final class WandReceiver {
    let support: URL
    var senseUpdate = WandSenseUpdateSession(), senseInfo: WandSenseInfo? = info()
    var isSense = true, senseTransport: WandSenseLink.Transport? = .bluetooth
    var senseLink: WandSenseLink? = WandSenseLink(), senseSessionNumber = 1
    var senseUpdateRefusal: String?
    init(_ support: URL) { self.support = support }
    func status() {}
}
func image(number: Int, board: String = WandSenseImageTarget.board, size: Int = 132_472, markers: Int = 1) -> Data {
    var d = Data((0..<size).map { UInt8(truncatingIfNeeded: $0 &* 31 &+ 7) })
    for i in 0..<markers {
        let marker = Data("WANDIMG1;\(board);\(number)\u{0}".utf8)
        d.replaceSubrange((4096 + i * 512)..<(4096 + i * 512 + marker.count), with: marker)
    }
    return d
}
func dat(_ image: Data, softDevices: [UInt16] = [0x0123], type: UInt16 = 0x0052) -> Data {
    var b: [UInt8] = [UInt8(type & 0xff), UInt8(type >> 8), 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, UInt8(softDevices.count), 0]
    for sd in softDevices { b += [UInt8(sd & 0xff), UInt8(sd >> 8)] }
    let crc = WandSenseDFUPackage.crc16(image)
    return Data(b + [UInt8(crc & 0xff), UInt8(crc >> 8)])
}
func fields(_ image: Data, softDevices: [Int] = [0x0123]) -> [String: Any] {
    ["application_version": 4294967295, "device_revision": 65535, "device_type": 82, "firmware_crc16": Int(WandSenseDFUPackage.crc16(image)), "softdevice_req": softDevices]
}
func info(_ extra: [String: Any] = [:], firmware: String = "wand-sense-6") -> WandSenseInfo {
    var v: [String: Any] = ["protocol": "wand-sense-1", "firmware": firmware, "id": "1a2b3c4d5e6f7081", "imu": true, "gyroDpsPerLsb": 0.0175,
                            "accelGPerLsb": 0.000122, "odr": 104, "merge": true, "wake": false, "firmwareNumber": 6, "bootloader": "0.6.2",
                            "softDevice": 291, "codeStart": 0x27000, "bootloaderStart": 0xF4000, "updater": 1, "updateKey": true, "update": "none"]
    for (k, x) in extra { v[k] = x }
    v = v.filter { !($0.value is NSNull) }
    return WandSenseInfo.parse(String(data: try! JSONSerialization.data(withJSONObject: v), encoding: .utf8)!)!
}

let root = FileManager.default.temporaryDirectory.appendingPathComponent("sense-preparation-\(UUID().uuidString)")
try! FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
defer { try? FileManager.default.removeItem(at: root) }
let seven = image(number: 7)
let package = try! WandSenseDFUPackage.make(image: seven, initPacket: dat(seven), manifestFields: fields(seven))
try! seven.write(to: root.appendingPathComponent("app.bin")); try! dat(seven).write(to: root.appendingPathComponent("app.dat"))
let manifest: [String: Any] = ["manifest": ["application": ["bin_file": "app.bin", "dat_file": "app.dat", "init_packet_data": fields(seven)]]]
try! JSONSerialization.data(withJSONObject: manifest).write(to: root.appendingPathComponent("manifest.json"))
_ = try! WandSenseUpdateKeyStore(folder: root).create(info().id)
func request(_ receiver: WandReceiver, id: String = String(repeating: "a", count: 32)) {
    let json: [String: Any] = ["version": 1, "id": id, "package": root.path, "sha256": package.sha256, "firmware": 7, "firstTrial": true, "acceptUSBRecovery": true]
    let path = receiver.firmwareUpdateRequestPath
    FileManager.default.createFile(atPath: path, contents: try! JSONSerialization.data(withJSONObject: json), attributes: [.posixPermissions: 0o600])
    receiver.readFirmwareUpdateRequest()
}
final class Harness {
    let receiver = WandReceiver(root)
    var work: [() -> Void] = [], main: [() -> Void] = []
    var tick = 1000.0
    init() {
        receiver.senseUpdate.preparation = WandSenseUpdatePreparation(work: { self.work.append($0) }, deliver: { self.main.append($0) }, clock: { self.tick += 25; return self.tick })
        receiver.senseUpdateBattery(millivolts: 3900, charging: false)
    }
    func complete() { precondition(work.count == 1); work.removeFirst()(); precondition(main.count == 1); main.removeFirst()() }
    func noChallenge() { precondition(receiver.senseLink?.commands.isEmpty == true) }
}
// Actual receiver extension: disk/key operations have not run when main returns.
let good = Harness(); request(good.receiver)
precondition(good.work.count == 1 && good.main.isEmpty && good.receiver.senseUpdate.flow.state == .preparing)
good.noChallenge()
request(good.receiver, id: String(repeating: "b", count: 32))
precondition(good.work.count == 1, "overlapping request must not queue another load")
// Main-loop telemetry can continue while the deliberately suspended worker waits.
good.receiver.senseUpdateBattery(millivolts: 3850, charging: true)
good.complete()
precondition(good.receiver.senseLink?.commands == ["UC"] && good.receiver.senseUpdate.flow.state == .challenging)
precondition(logs.contains { $0.contains("SENSE_UPDATE_PREPARE_START") && $0.contains("monotonicMS") })
precondition(logs.contains { $0.contains("SENSE_UPDATE_PREPARE_END") && $0.contains("workMS 25.0") })
print("PASS: preparation returns before disk work, blocks overlap, logs monotonic phases and challenges after delivery")

let disconnected = Harness(); request(disconnected.receiver)
disconnected.receiver.senseUpdateConnectionLost()
precondition(disconnected.receiver.senseUpdate.preparation.busy, "cancel holds slot until worker finishes")
request(disconnected.receiver, id: String(repeating: "c", count: 32))
precondition(disconnected.work.count == 1)
disconnected.complete(); disconnected.noChallenge()
precondition(disconnected.receiver.senseUpdate.flow.state == .failed && !disconnected.receiver.senseUpdate.preparation.busy)
print("PASS: disconnect cancels completion and prevents overlapping stale loads")

for mutation in 0..<7 {
    let h = Harness(); request(h.receiver)
    switch mutation {
    case 0: h.receiver.senseSessionNumber += 1 // same board, new session
    case 1: h.receiver.senseInfo = info(["id": "ffffffffffffffff"])
    case 2: h.receiver.senseTransport = .usb
    case 3: h.receiver.senseLink?.active = .usb
    case 4: h.receiver.senseLink = WandSenseLink()
    case 5: h.receiver.senseInfo?.update.keyProvisioned = false
    default: _ = h.receiver.senseUpdate.setup.begin(boardID: info().id, provision: "K-not-a-real-key")
    }
    h.complete(); h.noChallenge()
    precondition(h.receiver.senseUpdate.flow.state == .failed, "changed session/key/transport must fail")
}
print("PASS: same-board reconnect, wrong board, transport, link and key changes cannot authorize")
let low = Harness(); request(low.receiver); low.receiver.senseUpdateBattery(millivolts: 3400, charging: false); low.complete(); low.noChallenge()
precondition(low.receiver.senseUpdate.flow.state == .failed)
let changed = Harness(); request(changed.receiver); changed.receiver.senseUpdate.requestID = "newer-request"; changed.complete(); changed.noChallenge()
let missingKey = Harness()
try! FileManager.default.removeItem(at: WandSenseUpdateKeyStore(folder: root).url(info().id))
request(missingKey.receiver); missingKey.complete(); missingKey.noChallenge()
precondition(missingKey.receiver.senseUpdate.flow.state == .failed)
print("PASS: completion checks fresh battery, request identity and missing key")

let realWorker = WandSenseUpdatePreparation()
let release = DispatchSemaphore(value: 0)
var delivered = false, mainTurn = false
precondition(realWorker.start(load: {
    precondition(!Thread.isMainThread, "disk/key preparation must run away from main")
    precondition(release.wait(timeout: .now() + 2) == .success, "main must remain able to run while work waits")
    return .init(package: package, key: SymmetricKey(size: .bits256))
}, complete: { result, _, valid in
    precondition(Thread.isMainThread && valid && mainTurn)
    if case .failure = result { preconditionFailure("unexpected worker failure") }
    delivered = true
}))
DispatchQueue.main.async { mainTurn = true; release.signal() }
let deadline = Date().addingTimeInterval(3)
while !delivered && Date() < deadline { _ = RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.01)) }
precondition(delivered && !realWorker.busy)
print("PASS: production worker runs off-main and returns on-main while main-loop work continues")
