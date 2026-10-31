import Foundation
import CryptoKit
setbuf(stdout, nil)
// Pure checks of the receiver's wireless Sense update. The bootloader below is a
// protocol fake written from the Adafruit nRF52 bootloader 0.6.2 source; passing
// it is not proof that the physical board's bootloader accepts an update.

// ---------- A fake legacy DFU bootloader ----------
final class FakeBootloader {
    var installedSoftDevice: UInt16 = 0x0123
    var dropPacket: Int? = nil, corruptByte: Int? = nil
    private(set) var receivedImage = Data(), activated = false, appValid = true, initPacket = Data(), expected = 0
    private var phase = "idle", receiveInit = false, prn = 0, sinceReceipt = 0, sizeNext = false, packetIndex = 0
    private var notes: [Data] = []
    func control(_ d: Data) -> [Data] {
        let b = [UInt8](d)
        switch (b[0], phase) {
        case (1, "idle"): precondition(b == [1, 4], "application image type"); phase = "sizes"; sizeNext = true
        case (2, "init") where b.count == 2 && b[1] == 0: receiveInit = true
        case (2, "init") where b.count == 2 && b[1] == 1:
            receiveInit = false
            // dfu_init_prevalidate: device type, SoftDevice list, two-byte CRC extension.
            let p = [UInt8](initPacket), count = Int(p[8]) | Int(p[9]) << 8
            let type = UInt16(p[0]) | UInt16(p[1]) << 8
            let sds = (0..<count).map { UInt16(p[10 + 2 * $0]) | UInt16(p[11 + 2 * $0]) << 8 }
            let ok = type == 0x0052 && p.count - (10 + 2 * count) == 2 && sds.contains { $0 == installedSoftDevice || $0 == 0xFFFE }
            phase = ok ? "ready" : "failed"
            return [Data([16, 2, ok ? 1 : 6])]
        case (8, "ready"): prn = Int(b[1]) | Int(b[2]) << 8
        case (3, "ready"): phase = "receiving"
        case (4, "received"):
            let crc = UInt16(initPacket[initPacket.count - 2]) | UInt16(initPacket[initPacket.count - 1]) << 8
            let good = WandSenseDFUPackage.crc16(receivedImage) == crc
            phase = good ? "valid" : "failed"
            return [Data([16, 4, good ? 1 : 5])]
        case (5, "valid"): activated = true; appValid = true; phase = "reset"
        default: preconditionFailure("unexpected control \(b) in \(phase)")
        }
        return []
    }
    func packet(_ d: Data) -> [Data] {
        if sizeNext {
            // Real 0.6.1/0.6.2 erase the application at Start, before validation.
            appValid = false; receivedImage = Data()
            sizeNext = false
            let b = [UInt8](d); precondition(b.count == 12 && b[0..<8].allSatisfy { $0 == 0 }, "application-only sizes")
            expected = Int(b[8]) | Int(b[9]) << 8 | Int(b[10]) << 16 | Int(b[11]) << 24
            phase = "init"; return [Data([16, 1, 1])]
        }
        if receiveInit { initPacket.append(d); return [] }
        precondition(phase == "receiving", "data before Receive in \(phase)")
        packetIndex += 1
        if packetIndex == dropPacket { return [] } // Lost on air.
        var data = d
        if let i = corruptByte, i >= receivedImage.count, i < receivedImage.count + data.count { data[data.startIndex + i - receivedImage.count] ^= 0xFF }
        receivedImage.append(data); sinceReceipt += 1
        var out: [Data] = []
        if receivedImage.count >= expected { phase = "received"; out.append(Data([16, 3, 1])) }
        else if prn > 0 && sinceReceipt == prn {
            sinceReceipt = 0
            let n = UInt32(receivedImage.count)
            out.append(Data([17, UInt8(n & 0xff), UInt8(n >> 8 & 0xff), UInt8(n >> 16 & 0xff), UInt8(n >> 24)]))
        }
        return out
    }
}

/// Runs the pure client against the fake, as WandSenseDFUTransfer does over Bluetooth.
func transfer(_ package: WandSenseDFUPackage, _ boot: FakeBootloader, interval: Int = 10) -> (activated: Bool, failure: String?) {
    var client = WandSenseLegacyDFU(image: package.image, initPacket: package.initPacket, receiptInterval: interval)
    var pending: [WandSenseLegacyDFU.Outcome] = [client.start()]
    while let outcome = pending.first {
        pending.removeFirst()
        switch outcome {
        case .failed(let why): return (false, why)
        case .activated: _ = boot.control(WandSenseLegacyDFU.activate); return (boot.activated, nil)
        case .writes(let writes):
            var notes: [Data] = []
            for write in writes {
                switch write {
                case .control(let d): notes += boot.control(d)
                case .packets(let ds): for d in ds { notes += boot.packet(d) }
                }
            }
            for n in notes { pending.append(client.receive(n)) }
            if notes.isEmpty && pending.isEmpty { return (false, "stalled: no response from the bootloader") }
        }
    }
    return (false, "ended without activation")
}

// ---------- Package fixtures ----------
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
func throwsPackage(_ body: () throws -> WandSenseDFUPackage, _ needle: String) {
    do { _ = try body(); preconditionFailure("accepted: \(needle)") }
    catch { precondition("\(error)".contains(needle), "\(error) lacks \(needle)") }
}

// The toolchain's real init packet layout (wand-sense-20261029e's .dat): type 0x52,
// revision and app version 0xFFFF..., one SoftDevice 0x0123, CRC 0x3849.
let realDat = Data([0x52, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x01, 0x00, 0x23, 0x01, 0x49, 0x38])
throwsPackage({ try WandSenseDFUPackage.make(image: image(number: 7), initPacket: realDat, manifestFields: fields(image(number: 7))) }, "CRC differs")
let seven = image(number: 7)
let package = try! WandSenseDFUPackage.make(image: seven, initPacket: dat(seven), manifestFields: fields(seven))
precondition(package.target == WandSenseImageTarget(board: "xiao-nrf52840-sense", firmwareNumber: 7) && package.softDevices == [0x0123])
precondition(package.sha256 == SHA256.hash(data: seven).map { String(format: "%02x", $0) }.joined())
throwsPackage({ try WandSenseDFUPackage.make(image: seven, initPacket: dat(seven, type: 0x0053), manifestFields: fields(seven)) }, "Adafruit")
throwsPackage({ try WandSenseDFUPackage.make(image: seven, initPacket: dat(seven), manifestFields: fields(seven, softDevices: [0x0123, 0xFFFE])) }, "manifest differs")
throwsPackage({ try WandSenseDFUPackage.make(image: seven, initPacket: dat(seven) + Data([0, 0]), manifestFields: fields(seven)) }, "layout")
let unmarked = image(number: 7, markers: 0), twice = image(number: 7, markers: 2)
throwsPackage({ try WandSenseDFUPackage.make(image: unmarked, initPacket: dat(unmarked), manifestFields: fields(unmarked)) }, "marker")
throwsPackage({ try WandSenseDFUPackage.make(image: twice, initPacket: dat(twice), manifestFields: fields(twice)) }, "marker")
// From a directory: application only, no links.
let folder = FileManager.default.temporaryDirectory.appendingPathComponent("wand-update-\(UUID().uuidString)")
try! FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
defer { try? FileManager.default.removeItem(at: folder) }
func writePackage(_ manifest: [String: Any]) {
    try! JSONSerialization.data(withJSONObject: ["manifest": manifest]).write(to: folder.appendingPathComponent("manifest.json"))
}
try! seven.write(to: folder.appendingPathComponent("wand_sense.ino.bin")); try! dat(seven).write(to: folder.appendingPathComponent("wand_sense.ino.dat"))
let app: [String: Any] = ["bin_file": "wand_sense.ino.bin", "dat_file": "wand_sense.ino.dat", "init_packet_data": fields(seven)]
writePackage(["application": app, "dfu_version": 0.5])
precondition((try? WandSenseDFUPackage.load(directory: folder)) == package, "loads the toolchain layout")
writePackage(["application": app, "softdevice_bootloader": app, "dfu_version": 0.5])
throwsPackage({ try WandSenseDFUPackage.load(directory: folder) }, "application-only")
writePackage(["application": ["bin_file": "../wand_sense.ino.bin", "dat_file": "wand_sense.ino.dat", "init_packet_data": fields(seven)], "dfu_version": 0.5])
throwsPackage({ try WandSenseDFUPackage.load(directory: folder) }, "unsafe")
try! FileManager.default.createSymbolicLink(at: folder.appendingPathComponent("link.bin"), withDestinationURL: folder.appendingPathComponent("wand_sense.ino.bin"))
writePackage(["application": ["bin_file": "link.bin", "dat_file": "wand_sense.ino.dat", "init_packet_data": fields(seven)], "dfu_version": 0.5])
throwsPackage({ try WandSenseDFUPackage.load(directory: folder) }, "missing")
print("PASS: packages are application-only, CRC-matched, single-target and link-free")

// ---------- Transfer against the fake bootloader ----------
let boot = FakeBootloader()
let ok = transfer(package, boot)
precondition(ok.activated && ok.failure == nil && boot.receivedImage == seven, "complete image, then activation: \(String(describing: ok.failure))")
for interval in [1, 7, 100] { precondition(transfer(package, FakeBootloader(), interval: interval).activated, "receipt interval \(interval)") }
let corrupted = FakeBootloader(); corrupted.corruptByte = 70_000
let bad = transfer(package, corrupted)
precondition(!bad.activated && !corrupted.activated && bad.failure?.contains("status 5") == true, "a CRC failure never activates")
let lossy = FakeBootloader(); lossy.dropPacket = 25
let lost = transfer(package, lossy)
// A missing receipt stalls the client (the Bluetooth runner then times out); a short count fails at once. Neither activates.
precondition(!lost.activated && !lossy.activated && (lost.failure?.contains("stalled") == true || lost.failure?.contains("received") == true), "a lost packet never activates: \(String(describing: lost.failure))")
let otherSD = FakeBootloader(); otherSD.installedSoftDevice = 0x0100
precondition(!transfer(package, otherSD).activated, "the bootloader's own SoftDevice check refuses")
var early = WandSenseLegacyDFU(image: seven, initPacket: dat(seven))
precondition(early.receive(Data([16, 1, 1])) == .failed("out-of-order response 1"), "no response before start")
print("PASS: legacy DFU completes, and CRC, packet-loss and SoftDevice failures never activate")

// ---------- Preflight ----------
func info(_ extra: [String: Any] = [:], firmware: String = "wand-sense-6") -> WandSenseInfo {
    var v: [String: Any] = ["protocol": "wand-sense-1", "firmware": firmware, "id": "1a2b3c4d5e6f7081", "imu": true, "gyroDpsPerLsb": 0.0175,
                            "accelGPerLsb": 0.000122, "odr": 104, "merge": true, "wake": false, "firmwareNumber": 6, "bootloader": "0.6.2",
                            "softDevice": 291, "codeStart": 0x27000, "bootloaderStart": 0xF4000, "updater": 1, "updateKey": true, "update": "none"]
    for (k, x) in extra { v[k] = x }
    v = v.filter { !($0.value is NSNull) }
    return WandSenseInfo.parse(String(data: try! JSONSerialization.data(withJSONObject: v), encoding: .utf8)!)!
}
let check = WandSenseUpdateCheck(batteryMillivolts: 3900, charging: false, overBluetooth: true, expectedSHA256: package.sha256, expectedFirmware: 7, allowFirstTrial: true, acceptUSBRecovery: true)
precondition(WandSenseUpdatePreflight.blockers(info(), package, check).isEmpty, "\(WandSenseUpdatePreflight.blockers(info(), package, check))")
func blocked(_ i: WandSenseInfo, _ c: WandSenseUpdateCheck = check, _ p: WandSenseDFUPackage = package, needle: String) {
    let b = WandSenseUpdatePreflight.blockers(i, p, c)
    precondition(b.contains { $0.contains(needle) }, "expected \(needle) in \(b)")
}
// The installed firmware E reports none of the update fields.
let legacy = WandSenseInfo.parse("{\"protocol\":\"wand-sense-1\",\"firmware\":\"wand-sense-20261029e\",\"id\":\"1a2b3c4d5e6f7081\",\"imu\":true,\"gyroDpsPerLsb\":0.0175,\"accelGPerLsb\":0.000122,\"odr\":104,\"merge\":true,\"wake\":false}")!
precondition(legacy.update == .none)
blocked(legacy, needle: "over USB once")
blocked(info(["updateKey": false]), needle: "update key")
var usb = check; usb.overBluetooth = false; blocked(info(), usb, needle: "Bluetooth")
var otherHash = check; otherHash.expectedSHA256 = String(repeating: "0", count: 64); blocked(info(), otherHash, needle: "SHA-256")
var otherNumber = check; otherNumber.expectedFirmware = 8; blocked(info(), otherNumber, needle: "not 8")
blocked(info(["firmwareNumber": 7]), needle: "not newer")
blocked(info(["softDevice": 0x0100]), needle: "SoftDevice")
blocked(info(["bootloader": "0.9.2"]), needle: "Unreviewed bootloader 0.9.2")
blocked(info(["bootloader": NSNull()]), needle: "Unreviewed bootloader unknown")
var careful = check; careful.allowFirstTrial = false; blocked(info(), careful, needle: "not yet proven")
blocked(info(["bootloaderStart": 0x27000]), needle: "impossible")
blocked(info(["codeStart": NSNull()]), needle: "memory layout")
let big = image(number: 7, size: 397_313), bigPackage = try! WandSenseDFUPackage.make(image: big, initPacket: dat(big), manifestFields: fields(big))
var bigCheck = check; bigCheck.expectedSHA256 = bigPackage.sha256; blocked(info(), bigCheck, bigPackage, needle: "conservative application limit (397312")
var low = check; low.batteryMillivolts = 3500; blocked(info(), low, needle: "battery is too low")
low.charging = true; precondition(WandSenseUpdatePreflight.blockers(info(), package, low).isEmpty, "charging allows a low battery")
var unmeasured = check; unmeasured.batteryMillivolts = nil; blocked(info(), unmeasured, needle: "not been measured")
blocked(info(["update": "installed"]), needle: "unconfirmed")
precondition(WandSenseBootloaderPolicy.bankedLimit(codeStart: 0x27000, bootloaderStart: 0xF4000, reserved: 40960) == 397_312)
print("PASS: preflight fails closed for old firmware, keys, transport, image, version, SoftDevice, bootloader, size and battery")

// ---------- Authorization (the same vector as the firmware's Node test) ----------
let key = SymmetricKey(data: Data((0..<32).map { UInt8($0) }))
let message = WandSenseUpdateAuth.message(boardID: "1a2b3c4d5e6f7081", nonce: "00112233445566778899aabbccddeeff", firmware: 7, size: 132472, crc: 0x3849)
precondition(message == "wand-sense-update-1|1a2b3c4d5e6f7081|00112233445566778899aabbccddeeff|7|132472|3849")
print("TAG " + HMAC<SHA256>.authenticationCode(for: Data(message.utf8), using: key).map { String(format: "%02x", $0) }.joined())
let command = WandSenseUpdateAuth.authorize(key: key, boardID: "1a2b3c4d5e6f7081", nonce: "00112233445566778899aabbccddeeff", package: package)
precondition(command.hasPrefix("UA7,132472,\(String(format: "%04x", package.crc16)),") && command.count <= 111, "fits the board's line buffer")
precondition(WandSenseUpdateAuth.provision(key) == "K" + (0..<32).map { String(format: "%02x", $0) }.joined())
let keys = WandSenseUpdateKeyStore(folder: folder)
let created = try! keys.create("1a2b3c4d5e6f7081")
precondition(keys.load("1a2b3c4d5e6f7081") == created, "a saved key loads back")
precondition((try? keys.create("1a2b3c4d5e6f7081")) == nil, "an existing key is never overwritten")
chmod(keys.url("1a2b3c4d5e6f7081").path, 0o644)
precondition(keys.load("1a2b3c4d5e6f7081") == nil, "a readable-by-others key is refused")

// ---------- Board replies and requests ----------
precondition(WandSenseLine.parse("U C 00112233445566778899aabbccddeeff") == .update(.challenge("00112233445566778899aabbccddeeff")))
precondition(WandSenseLine.parse("U GO") == .update(.go) && WandSenseLine.parse("U NO auth") == .update(.refused("auth")))
precondition(WandSenseLine.parse("U V ok") == .update(.verified) && WandSenseLine.parse("U KEY saved") == .update(.keySaved))
precondition(WandSenseLine.parse("U C 0011") == nil && WandSenseLine.parse("U MAYBE") == nil)
let requestJSON = "{\"version\":1,\"id\":\"\(String(repeating: "a", count: 32))\",\"package\":\"/opt/wand-update/p\",\"sha256\":\"\(package.sha256)\",\"firmware\":7,\"firstTrial\":false}"
precondition(WandSenseUpdateRequest.parse(Data(requestJSON.utf8))?.firmware == 7)
for bad in [requestJSON.replacingOccurrences(of: "\"firstTrial\":false", with: "\"firstTrial\":0"),
            requestJSON.replacingOccurrences(of: "/opt/wand-update/p", with: "relative/p"),
            requestJSON.replacingOccurrences(of: "\"firmware\":7", with: "\"firmware\":true"),
            requestJSON.replacingOccurrences(of: "}", with: ",\"extra\":1}")] {
    precondition(WandSenseUpdateRequest.parse(Data(bad.utf8)) == nil, bad)
}
let requestPath = folder.appendingPathComponent("firmware-update.request").path
FileManager.default.createFile(atPath: requestPath, contents: Data(requestJSON.utf8), attributes: [.posixPermissions: 0o644])
precondition(WandSenseUpdateRequest.take(at: requestPath) == nil && !FileManager.default.fileExists(atPath: requestPath), "shared files are consumed and refused")
FileManager.default.createFile(atPath: requestPath, contents: Data(requestJSON.utf8), attributes: [.posixPermissions: 0o600])
precondition(WandSenseUpdateRequest.take(at: requestPath) != nil, "a private request is accepted once")
print("PASS: authorization, key store, replies and requests")

// ---------- Flow ----------
var flow = WandSenseUpdateFlow()
let sign: (String) -> String = { "UA-\($0)" }
precondition(flow.begin(boardID: "1a2b3c4d5e6f7081", target: 7) == [.send("UC"), .report] && flow.busy)
precondition(flow.begin(boardID: "1a2b3c4d5e6f7081", target: 7).isEmpty, "one update at a time")
precondition(flow.reply(.go, authorize: sign).isEmpty, "GO before authorization is ignored")
precondition(flow.reply(.challenge("n1"), authorize: sign) == [.send("UA-n1"), .report])
precondition(flow.connectionLost() == [.report] && flow.state == .failed, "losing the link before GO fails safely")
flow = WandSenseUpdateFlow(); _ = flow.begin(boardID: "1a2b3c4d5e6f7081", target: 7); _ = flow.reply(.challenge("n1"), authorize: sign)
precondition(flow.reply(.go, authorize: sign) == [.beginTransfer, .report])
precondition(flow.connectionLost().isEmpty && flow.state == .handingOver, "the handoff disconnect is expected")
_ = flow.transferStarted(); precondition(flow.transferEnded(nil) == [.report] && flow.state == .restarting)
precondition(flow.identity(info(["firmwareNumber": 7, "update": "installed"], firmware: "wand-sense-7")) == [.send("UV"), .report])
precondition(flow.verified(boardID: "1a2b3c4d5e6f7081") == [.report] && flow.state == .done && !flow.busy)
// The board restarted on the old firmware: reported, never claimed.
flow = WandSenseUpdateFlow(); _ = flow.begin(boardID: "1a2b3c4d5e6f7081", target: 7); _ = flow.reply(.challenge("n"), authorize: sign); _ = flow.reply(.go, authorize: sign); _ = flow.transferEnded(nil)
var other = info(["firmwareNumber": 7, "update": "installed"]); other = WandSenseInfo(firmware: other.firmware, id: "ffffffffffffffff", gyroDpsPerLsb: 0.0175, accelGPerLsb: 0.000122, odr: 104, wake: false)
precondition(flow.identity(other).isEmpty, "another board never confirms")
_ = flow.identity(info(["update": "not-installed"]))
precondition(flow.state == .failed && flow.detail.contains("not installed"))
flow = WandSenseUpdateFlow(); _ = flow.begin(boardID: "1a2b3c4d5e6f7081", target: 7); _ = flow.reply(.challenge("n"), authorize: sign); _ = flow.reply(.go, authorize: sign)
_ = flow.transferEnded("the updater did not accept a connection")
precondition(flow.state == .failed && flow.detail.contains("resetting cannot restore") && flow.detail.contains("USB"))
flow = WandSenseUpdateFlow(); _ = flow.begin(boardID: "1a2b3c4d5e6f7081", target: 7)
_ = flow.reply(.refused("battery"), authorize: sign); precondition(flow.state == .failed && flow.detail.contains("battery"))
flow = WandSenseUpdateFlow(); _ = flow.begin(boardID: "1a2b3c4d5e6f7081", target: 7)
_ = flow.timedOut(); precondition(flow.state == .failed && flow.detail.contains("keeps running"))
print("PASS: the update flow confirms only the exact board at the new version and fails closed")

// ---------- Session and explicit failed-result reconciliation ----------
var setup = WandSenseUpdateSetup()
var fakeSession = false, fakeSaved = false
let provisionCommands = setup.begin(boardID: "1a2b3c4d5e6f7081", provision: "K-test-key")
for c in provisionCommands {
    if c == "H" { fakeSession = true }
    if c.hasPrefix("K"), fakeSession { fakeSaved = true }
}
precondition(provisionCommands == ["H", "K-test-key"] && fakeSaved, "H establishes the firmware session before K")
precondition(!setup.keySaved(boardID: "ffffffffffffffff"), "another board cannot acknowledge provisioning")
precondition(setup.keySaved(boardID: "1a2b3c4d5e6f7081") && setup.keyBoardID == nil)
precondition(!setup.keySaved(boardID: "1a2b3c4d5e6f7081"), "unsolicited key acknowledgements are ignored")
_ = setup.begin(boardID: "1a2b3c4d5e6f7081", provision: "K-test-key"); setup.reset()
precondition(!setup.keySaved(boardID: "1a2b3c4d5e6f7081"), "an old session cannot finish provisioning")

var interrupted = WandSenseUpdateFlow()
_ = interrupted.begin(boardID: "1a2b3c4d5e6f7081", target: 7)
_ = interrupted.reply(.challenge("n"), authorize: sign); _ = interrupted.reply(.go, authorize: sign)
_ = interrupted.transferEnded(nil)
let installedInfo = info(["firmwareNumber": 7, "update": "installed"], firmware: "wand-sense-7")
let confirmation = interrupted.identity(installedInfo)
fakeSession = false
for c in setup.begin(boardID: installedInfo.id, provision: nil) + confirmation.compactMap({ if case .send(let c) = $0 { return c }; return nil }) {
    if c == "H" { fakeSession = true }
    if c == "UV" { precondition(fakeSession, "confirmation follows H") }
}
precondition(interrupted.verified(boardID: "ffffffffffffffff").isEmpty)
_ = interrupted.connectionLost()
_ = interrupted.identity(info(["firmwareNumber": 7, "update": "none"], firmware: "wand-sense-7"))
precondition(interrupted.state == .done, "fresh identity recovers a lost confirmation acknowledgement")

let failedInfo = info(["update": "not-installed", "updateTarget": 7])
let reconcile = WandSenseUpdateReconcileRequest(id: String(repeating: "c", count: 32), boardID: failedInfo.id, running: 6, target: 7)
precondition(reconcile.matches(failedInfo))
precondition(!reconcile.matches(info(["id": "ffffffffffffffff", "update": "not-installed", "updateTarget": 7])))
precondition(!reconcile.matches(info(["update": "not-installed", "updateTarget": 8])), "newer pending result cannot be cleared")
var failedFlow = WandSenseUpdateFlow()
_ = failedFlow.begin(boardID: failedInfo.id, target: 7)
_ = failedFlow.reply(.challenge("n"), authorize: sign); _ = failedFlow.reply(.go, authorize: sign)
_ = failedFlow.transferEnded("packet loss")
let failureDetail = failedFlow.detail
precondition(failedFlow.identity(failedInfo).isEmpty, "reconnect never auto-clears or flashes")
precondition(failedFlow.reconcile(reconcile, info: failedInfo) == [.send("UR6,7"), .report])
precondition(failedFlow.state == .reconciling && failedFlow.detail == failureDetail)
precondition(failedFlow.begin(boardID: failedInfo.id, target: 7).isEmpty, "wait for acknowledgement")
precondition(failedFlow.verified(boardID: "ffffffffffffffff").isEmpty)
_ = failedFlow.verified(boardID: failedInfo.id)
precondition(failedFlow.state == .failed && failedFlow.detail.contains("packet loss") && failedFlow.detail.contains("retry"), "acknowledgement retains failure")
precondition(failedFlow.begin(boardID: failedInfo.id, target: 7) == [.send("UC"), .report], "a later explicit request retries")
let reconcileJSON = "{\"version\":1,\"id\":\"\(reconcile.id)\",\"boardID\":\"\(reconcile.boardID)\",\"running\":6,\"target\":7}"
precondition(WandSenseUpdateReconcileRequest.parse(Data(reconcileJSON.utf8)) == reconcile)
for bad in [reconcileJSON.replacingOccurrences(of: "\"running\":6", with: "\"running\":true"), reconcileJSON.replacingOccurrences(of: "\"target\":7", with: "\"target\":7.5"), reconcileJSON.replacingOccurrences(of: "}", with: ",\"extra\":0}")] {
    precondition(WandSenseUpdateReconcileRequest.parse(Data(bad.utf8)) == nil)
}
print("PASS: session ordering and explicit reconciliation preserve failures and permit a later retry")

var refusedReconcile = WandSenseUpdateFlow()
_ = refusedReconcile.reconcile(reconcile, info: failedInfo)
_ = refusedReconcile.reply(.refused("storage"), authorize: sign)
precondition(refusedReconcile.state == .failed && refusedReconcile.detail.contains("storage") && refusedReconcile.detail.contains("unconfirmed"))

// Unknown protocol/result fields never become update permission.
blocked(info(["updater": 2]), needle: "supported wireless updater")
blocked(info(["update": "unrecognised"]), needle: "unconfirmed")
blocked(info(["update": NSNull()]), needle: "unconfirmed")
let duplicateMalformed = seven + Data("WANDIMG1;bad-marker\u{0}".utf8)
throwsPackage({ try WandSenseDFUPackage.make(image: duplicateMalformed, initPacket: dat(duplicateMalformed), manifestFields: fields(duplicateMalformed)) }, "marker")
for number in [0, 1_000_000] {
    let invalidImage = image(number: number)
    throwsPackage({ try WandSenseDFUPackage.make(image: invalidImage, initPacket: dat(invalidImage), manifestFields: fields(invalidImage)) }, "marker")
}
for badNumber in ["7.5", "1000000"] {
    precondition(WandSenseUpdateRequest.parse(Data(requestJSON.replacingOccurrences(of: "\"firmware\":7", with: "\"firmware\":\(badNumber)").utf8)) == nil)
}

// A receiver restart loses its in-memory flow, but must not strand a genuine
// successful board result. Explicit acknowledgement still matches all fields.
let orphanedInstall = info(["firmwareNumber": 7, "update": "installed", "updateTarget": 7], firmware: "wand-sense-7")
let acknowledgeInstall = WandSenseUpdateReconcileRequest(id: String(repeating: "d", count: 32), boardID: orphanedInstall.id, running: 7, target: 7)
var orphanedFlow = WandSenseUpdateFlow()
precondition(orphanedFlow.identity(orphanedInstall).isEmpty, "reconnect alone does not acknowledge an earlier session's result")
precondition(orphanedFlow.reconcile(acknowledgeInstall, info: orphanedInstall) == [.send("UV"), .report])
precondition(orphanedFlow.state == .reconciling)
precondition(orphanedFlow.verified(boardID: "ffffffffffffffff").isEmpty)
_ = orphanedFlow.verified(boardID: orphanedInstall.id)
precondition(orphanedFlow.state == .done && orphanedFlow.detail.contains("installed and confirmed"))
precondition(!acknowledgeInstall.matches(info(["firmwareNumber": 7, "update": "not-installed", "updateTarget": 7])))

for version in ["0.6.1", "0.6.2"] {
    precondition(WandSenseBootloaderPolicy.reviewed[version]?.physicallyProven == false)
    precondition(WandSenseUpdatePreflight.blockers(info(["bootloader": version]), package, check).isEmpty)
    var noRecovery = check; noRecovery.acceptUSBRecovery = false
    blocked(info(["bootloader": version]), noRecovery, needle: "acceptUSBRecovery")
    var noTrial = check; noTrial.allowFirstTrial = false
    blocked(info(["bootloader": version]), noTrial, needle: "not yet proven")
}
blocked(info(["bootloader": "0.6.0"]), needle: "Unreviewed bootloader")
blocked(info(["bootloader": "0.6.3"]), needle: "Unreviewed bootloader")
blocked(info(["codeStart": 0x26000]), needle: "Unreviewed memory layout")
let acceptedRequest = requestJSON.replacingOccurrences(of: "}", with: ",\"acceptUSBRecovery\":true}")
precondition(WandSenseUpdateRequest.parse(Data(requestJSON.utf8))?.acceptUSBRecovery == false)
precondition(WandSenseUpdateRequest.parse(Data(acceptedRequest.utf8))?.acceptUSBRecovery == true)
for wrong in ["1", "0", "\"true\"", "null"] {
    let bad = requestJSON.replacingOccurrences(of: "}", with: ",\"acceptUSBRecovery\":\(wrong)}")
    precondition(WandSenseUpdateRequest.parse(Data(bad.utf8)) == nil)
}
precondition(!corrupted.appValid && !lossy.appValid, "single-bank failures do not preserve an old app")
print("PASS: reviewed single-bank versions require first trial and explicit USB recovery acceptance")
