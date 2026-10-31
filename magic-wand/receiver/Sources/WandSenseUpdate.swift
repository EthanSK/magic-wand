import Foundation
import CryptoKit
import CoreBluetooth
import Darwin

// Wireless application updates for the original Seeed XIAO nRF52840 Sense.
//
// Ethan, 2026-10-30: "Is this firmware also gonna add wireless updates? And is
// fully reviewed so it'll work, so I never have to plug it in again?"
//
// Shape (see device/sense/wand_sense/wand_update.h for the board side):
//   1. Preflight, entirely on the Mac, before the wand is touched: the package
//      is an application-only Adafruit/Nordic legacy DFU package for this board,
//      its CRC and SHA-256 match, the image names its own target and number,
//      it fits our conservative application-size cap, and the board reports a reviewed
//      bootloader, SoftDevice, updater and provisioned key. Anything unknown
//      blocks the update; the current firmware keeps running.
//   2. The receiver proves it holds the board's key (HMAC over a one-time board
//      nonce and this exact image); only then does the board hand over to its
//      bootloader. There is no open DFU service on the application.
//   3. The transfer reconnects to the same peripheral identifier (the
//      bootloader keeps the board's address), never to a device found by name.
//   4. After the board restarts, the receiver checks the reported firmware
//      number and update result, then clears the board's pending record.
// Reviewed bootloaders 0.6.1 and 0.6.2 use single-bank BLE DFU. Start DFU
// erases the current application, before the image/CRC has arrived. A failed
// transfer may leave no runnable application and require USB recovery; reset
// cannot restore overwritten bytes. Every request must explicitly accept that
// through acceptUSBRecovery, in addition to any required first-trial approval.
//
// Not proven on hardware yet: the physical board's bootloader version, its
// wireless DFU, and macOS reusing the peripheral identifier for the
// bootloader. USB remains the recovery path.

// ---------- Board-reported support ----------
struct WandSenseUpdateSupport: Equatable {
    var firmwareNumber: Int?
    var bootloader: String?
    var softDevice: Int?
    var codeStart: UInt32?
    var bootloaderStart: UInt32?
    var updater = 0
    var keyProvisioned = false
    var result = "none"
    var pendingTarget: Int?
    static let none = WandSenseUpdateSupport()

    /// Optional identity fields from firmware 6 on; older firmware reports none.
    static func parse(_ v: [String: Any]) -> WandSenseUpdateSupport {
        func int(_ key: String) -> Int? {
            guard let n = v[key] as? NSNumber, CFGetTypeID(n) != CFBooleanGetTypeID(), n.doubleValue == Double(n.intValue) else { return nil }
            return n.intValue
        }
        var s = WandSenseUpdateSupport()
        s.pendingTarget = int("updateTarget").flatMap { (1...999_999).contains($0) ? $0 : nil }
        s.firmwareNumber = int("firmwareNumber").flatMap { (1...999_999).contains($0) ? $0 : nil }
        if let text = v["bootloader"] as? String, text.count <= 15, text.split(separator: ".").count == 3,
           text.split(separator: ".").allSatisfy({ Int($0) != nil }) { s.bootloader = text }
        s.softDevice = int("softDevice").flatMap { (0...0xFFFF).contains($0) ? $0 : nil }
        s.codeStart = int("codeStart").flatMap { $0 > 0 && $0 <= 0x100000 ? UInt32($0) : nil }
        s.bootloaderStart = int("bootloaderStart").flatMap { $0 > 0 && $0 <= 0x100000 ? UInt32($0) : nil }
        s.updater = int("updater").map { max(0, min(255, $0)) } ?? 0
        s.keyProvisioned = v["updateKey"] as? Bool ?? false
        if let result = v["update"] as? String, ["none", "installed", "not-installed"].contains(result) { s.result = result }
        else if s.updater > 0 { s.result = "unknown" } // Never turn an unrecognised result into permission to update.
        return s
    }
}

// ---------- Board replies ----------
enum WandSenseUpdateReply: Equatable {
    case challenge(String), go, refused(String), verified, keySaved, keyRemoved
    static func parse(_ body: Substring) -> WandSenseUpdateReply? {
        let f = body.split(separator: " ", omittingEmptySubsequences: true)
        switch (f.first, f.count) {
        case ("C", 2) where f[1].count == 32 && f[1].allSatisfy({ $0.isHexDigit && !$0.isUppercase }): return .challenge(String(f[1]))
        case ("GO", 1): return .go
        case ("NO", 2) where f[1].count <= 16: return .refused(String(f[1]))
        case ("V", 2) where f[1] == "ok": return .verified
        case ("KEY", 2) where f[1] == "saved": return .keySaved
        case ("KEY", 2) where f[1] == "removed": return .keyRemoved
        default: return nil
        }
    }
}

// ---------- Reviewed bootloaders ----------
/// Fail closed: only versions whose source was reviewed may receive an update,
/// and an unproven one needs an explicit first-trial request (USB at hand).
enum WandSenseBootloaderPolicy {
    struct Entry: Equatable { let reservedBytes: UInt32; let physicallyProven: Bool }
    /// Official 0.6.1/0.6.2 source: 40 KB reserved data, GPREGRET 0xB1,
    /// single-bank app updates, device 0x0052, SoftDevice list and CRC16.
    /// Seeed's file labelled 0.6.2 embeds 0.6.1; hardware reports 0.6.1 too.
    /// Source review does not prove a completed physical BLE transfer.
    static let reviewed: [String: Entry] = [
        "0.6.1": Entry(reservedBytes: 10 * 4096, physicallyProven: false),
        "0.6.2": Entry(reservedBytes: 10 * 4096, physicallyProven: false)
    ]
    /// s140 7.3.0, the SoftDevice the Sense board package targets (sd_fwid 0x0123).
    static let softDevices: Set<Int> = [0x0123]
    static let pageSize: UInt32 = 4096

    /// Historical name: our conservative half-size cap, matching wandBankedLimit().
    /// The bootloader itself is single-bank; this cap does not preserve an old app.
    static func bankedLimit(codeStart: UInt32, bootloaderStart: UInt32, reserved: UInt32) -> UInt32 {
        guard bootloaderStart > codeStart, bootloaderStart - codeStart > reserved else { return 0 }
        let full = bootloaderStart - codeStart - reserved
        return (full - full % (2 * pageSize)) / 2
    }
}

// ---------- Package ----------
enum WandSenseUpdateError: Error, Equatable, CustomStringConvertible {
    case package(String)
    var description: String { if case .package(let s) = self { return s }; return "package" }
}

/// The image's own statement of what it is, compiled into the firmware as
/// WAND_IMAGE_MARKER: "WANDIMG1;<board>;<firmware number>".
struct WandSenseImageTarget: Equatable {
    static let prefix = Data("WANDIMG1;".utf8)
    static let board = "xiao-nrf52840-sense"
    let board: String
    let firmwareNumber: Int
    static func find(in image: Data) -> WandSenseImageTarget? {
        var found: [WandSenseImageTarget] = []
        var markerCount = 0
        var start = image.startIndex
        while let range = image.range(of: prefix, in: start..<image.endIndex) {
            markerCount += 1
            let end = image[range.lowerBound...].firstIndex(of: 0) ?? image.endIndex
            if end - range.lowerBound <= 64, let text = String(data: image[range.lowerBound..<end], encoding: .ascii) {
                let f = text.split(separator: ";", omittingEmptySubsequences: false)
                if f.count == 3, f[2].allSatisfy({ $0.isASCII && $0.isNumber }), let n = Int(f[2]), (1...999_999).contains(n) { found.append(.init(board: String(f[1]), firmwareNumber: n)) }
            }
            start = range.upperBound
        }
        return markerCount == 1 && found.count == 1 ? found[0] : nil // Exactly one, or it is ambiguous.
    }
}

/// An application-only package from the board toolchain's
/// `adafruit-nrfutil dfu genpkg --dev-type 0x0052 --sd-req 0x0123 --application`,
/// unzipped into a private directory: manifest.json, the .dat init packet and
/// the .bin image.
struct WandSenseDFUPackage: Equatable {
    static let deviceType: UInt16 = 0x0052
    static let anySoftDevice: UInt16 = 0xFFFE
    let image: Data
    let initPacket: Data
    let crc16: UInt16
    let softDevices: [UInt16]
    let sha256: String
    let target: WandSenseImageTarget

    static func crc16(_ data: Data) -> UInt16 {
        var crc: UInt16 = 0xFFFF
        for byte in data {
            var x = UInt8(crc >> 8) ^ byte
            x ^= x >> 4
            crc = (crc << 8) ^ (UInt16(x) << 12) ^ (UInt16(x) << 5) ^ UInt16(x)
        }
        return crc
    }

    static func load(directory: URL) throws -> WandSenseDFUPackage {
        func read(_ name: String, limit: Int) throws -> Data {
            guard !name.contains("/"), !name.hasPrefix(".") else { throw WandSenseUpdateError.package("unsafe file name \(name)") }
            let url = directory.appendingPathComponent(name)
            let values = try? url.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey, .fileSizeKey])
            guard values?.isRegularFile == true, values?.isSymbolicLink != true, let size = values?.fileSize, size > 0, size <= limit,
                  let data = try? Data(contentsOf: url) else { throw WandSenseUpdateError.package("missing or oversized \(name)") }
            return data
        }
        let manifestData = try read("manifest.json", limit: 4096)
        guard let root = (try? JSONSerialization.jsonObject(with: manifestData)) as? [String: Any],
              let manifest = root["manifest"] as? [String: Any] else { throw WandSenseUpdateError.package("unreadable manifest") }
        // Application only: never a SoftDevice or bootloader image.
        guard Set(manifest.keys).subtracting(["dfu_version"]) == ["application"],
              let app = manifest["application"] as? [String: Any],
              let binName = app["bin_file"] as? String, let datName = app["dat_file"] as? String,
              let fields = app["init_packet_data"] as? [String: Any] else { throw WandSenseUpdateError.package("not an application-only package") }
        let image = try read(binName, limit: 1_048_576)
        let initPacket = try read(datName, limit: 64)
        return try make(image: image, initPacket: initPacket, manifestFields: fields)
    }

    static func make(image: Data, initPacket dat: Data, manifestFields fields: [String: Any]) throws -> WandSenseDFUPackage {
        let b = [UInt8](dat)
        func u16(_ i: Int) -> UInt16 { UInt16(b[i]) | UInt16(b[i + 1]) << 8 }
        guard b.count >= 12 else { throw WandSenseUpdateError.package("short init packet") }
        let type = u16(0), count = Int(u16(8))
        // dfu_init_packet_t, then exactly one 16-bit CRC: the 0.6.2 bootloader's extension.
        guard count >= 1, count <= 8, b.count == 10 + 2 * count + 2 else { throw WandSenseUpdateError.package("unexpected init packet layout") }
        let softDevices = (0..<count).map { u16(10 + 2 * $0) }
        let crc = u16(10 + 2 * count)
        guard type == deviceType else { throw WandSenseUpdateError.package("not an Adafruit nRF52 package") }
        guard crc16(image) == crc else { throw WandSenseUpdateError.package("image CRC differs from its init packet") }
        func number(_ key: String) -> Int? { (fields[key] as? NSNumber)?.intValue }
        guard number("device_type") == Int(type), number("firmware_crc16") == Int(crc),
              (fields["softdevice_req"] as? [NSNumber])?.map({ UInt16(truncatingIfNeeded: $0.intValue) }) == softDevices
        else { throw WandSenseUpdateError.package("manifest differs from its init packet") }
        guard let target = WandSenseImageTarget.find(in: image) else { throw WandSenseUpdateError.package("image has no single target marker") }
        let digest = SHA256.hash(data: image).map { String(format: "%02x", $0) }.joined()
        return .init(image: image, initPacket: dat, crc16: crc, softDevices: softDevices, sha256: digest, target: target)
    }
}

// ---------- Preflight ----------
struct WandSenseUpdateCheck: Equatable {
    var batteryMillivolts: Int?
    var charging = false
    var overBluetooth = false
    var expectedSHA256: String
    var expectedFirmware: Int
    var allowFirstTrial = false
    var acceptUSBRecovery = false
}

enum WandSenseUpdatePreflight {
    static let minimumMillivolts = 3600 // Same floor as the board.

    /// Every reason the update must not start. Empty means ready.
    static func blockers(_ info: WandSenseInfo, _ package: WandSenseDFUPackage, _ check: WandSenseUpdateCheck) -> [String] {
        var out: [String] = []
        let s = info.update
        if s.updater != 1 { out.append("This firmware has no supported wireless updater. Install wand-sense-6 over USB once.") }
        if !s.keyProvisioned { out.append("The board has no update key. Provision it over USB.") }
        if !check.overBluetooth { out.append("The wand must be connected over Bluetooth.") }
        if package.sha256 != check.expectedSHA256.lowercased() { out.append("The package SHA-256 differs from the requested image.") }
        if package.target.board != WandSenseImageTarget.board { out.append("The image targets \(package.target.board).") }
        if package.target.firmwareNumber != check.expectedFirmware { out.append("The image is firmware \(package.target.firmwareNumber), not \(check.expectedFirmware).") }
        if let current = s.firmwareNumber { if package.target.firmwareNumber <= current { out.append("The image is not newer than the installed firmware \(current).") } }
        else { out.append("The board does not report a numeric firmware version.") }
        if let sd = s.softDevice {
            if !WandSenseBootloaderPolicy.softDevices.contains(sd) { out.append(String(format: "Unreviewed SoftDevice 0x%04x.", sd)) }
            if !package.softDevices.contains(UInt16(sd)) && !package.softDevices.contains(WandSenseDFUPackage.anySoftDevice) {
                out.append("The package does not accept the board's SoftDevice.")
            }
        } else { out.append("The board does not report its SoftDevice.") }
        if let version = s.bootloader, let entry = WandSenseBootloaderPolicy.reviewed[version] {
            if !check.acceptUSBRecovery {
                out.append("This single-bank bootloader overwrites the current application. Set acceptUSBRecovery only after accepting USB recovery if the transfer fails.")
            }
            if !entry.physicallyProven && !check.allowFirstTrial {
                out.append("Bootloader \(version) is reviewed but not yet proven on this board; a first trial needs USB at hand.")
            }
            if let code = s.codeStart, let loader = s.bootloaderStart {
                let limit = WandSenseBootloaderPolicy.bankedLimit(codeStart: code, bootloaderStart: loader, reserved: entry.reservedBytes)
                if limit == 0 { out.append("The board reports an impossible memory layout.") }
                else if code != 0x27000 || loader != 0xF4000 { out.append("Unreviewed memory layout for this bootloader.") }
                else if package.image.count > Int(limit) { out.append("The image (\(package.image.count) bytes) exceeds the conservative application limit (\(limit) bytes).") }
            } else { out.append("The board does not report its memory layout.") }
        } else { out.append("Unreviewed bootloader \(s.bootloader ?? "unknown").") }
        if s.result != "none" { out.append("The board still has an unconfirmed update result (\(s.result)).") }
        if let mv = check.batteryMillivolts { if mv < minimumMillivolts && !check.charging { out.append("The battery is too low (\(mv) mV).") } }
        else { out.append("The battery has not been measured yet.") }
        return out
    }
}

// ---------- Authorization ----------
enum WandSenseUpdateAuth {
    static let domain = "wand-sense-update-1"
    static func message(boardID: String, nonce: String, firmware: Int, size: Int, crc: UInt16) -> String {
        "\(domain)|\(boardID)|\(nonce)|\(firmware)|\(size)|\(String(format: "%04x", crc))"
    }
    static func authorize(key: SymmetricKey, boardID: String, nonce: String, package: WandSenseDFUPackage) -> String {
        let text = message(boardID: boardID, nonce: nonce, firmware: package.target.firmwareNumber, size: package.image.count, crc: package.crc16)
        let tag = HMAC<SHA256>.authenticationCode(for: Data(text.utf8), using: key).map { String(format: "%02x", $0) }.joined()
        return "UA\(package.target.firmwareNumber),\(package.image.count),\(String(format: "%04x", package.crc16)),\(tag)"
    }
    static let challenge = "UC", confirm = "UV"
    /// USB only; the board refuses it over Bluetooth.
    static func provision(_ key: SymmetricKey) -> String { "K" + key.withUnsafeBytes { $0.map { String(format: "%02x", $0) }.joined() } }
}

/// One private key per board, in the receiver's support folder (0600). Never
/// published, logged or sent over Bluetooth.
struct WandSenseUpdateKeyStore {
    let folder: URL
    func url(_ boardID: String) -> URL { folder.appendingPathComponent("sense-update-key-\(boardID).bin") }
    func load(_ boardID: String) -> SymmetricKey? {
        guard boardID.count == 16, boardID.allSatisfy({ $0.isHexDigit }) else { return nil }
        let path = url(boardID).path
        let fd = open(path, O_RDONLY | O_NOFOLLOW)
        guard fd >= 0 else { return nil }
        defer { close(fd) }
        var info = stat()
        guard fstat(fd, &info) == 0, info.st_uid == geteuid(), info.st_mode & S_IFMT == S_IFREG, info.st_mode & 0o077 == 0, info.st_size == 32 else { return nil }
        var bytes = [UInt8](repeating: 0, count: 32)
        guard read(fd, &bytes, 32) == 32 else { return nil }
        return SymmetricKey(data: bytes)
    }
    /// A new random key, written privately before it is ever sent to a board.
    /// Created exclusively at 0600, so it is never briefly readable and an
    /// existing key is never replaced.
    func create(_ boardID: String) throws -> SymmetricKey {
        guard boardID.count == 16, boardID.allSatisfy({ $0.isHexDigit }) else { throw CocoaError(.fileWriteInvalidFileName) }
        let key = SymmetricKey(size: .bits256)
        let fd = open(url(boardID).path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0o600)
        guard fd >= 0 else { throw CocoaError(.fileWriteFileExists) }
        let written = key.withUnsafeBytes { write(fd, $0.baseAddress, 32) }
        let synced = fsync(fd) == 0
        close(fd)
        guard written == 32, synced else { unlink(url(boardID).path); throw CocoaError(.fileWriteUnknown) }
        return key
    }
}

// ---------- Legacy DFU (Nordic SDK 11, the Adafruit bootloader's BLE transport) ----------
/// Pure protocol client: emits writes, consumes control-point notifications.
/// Every response is checked; any surprise fails without claiming activation.
/// Single-bank writes may already have erased the previous application.
struct WandSenseLegacyDFU {
    static let service = CBUUID(string: "00001530-1212-EFDE-1523-785FEABCD123")
    static let control = CBUUID(string: "00001531-1212-EFDE-1523-785FEABCD123")
    static let packet = CBUUID(string: "00001532-1212-EFDE-1523-785FEABCD123")
    enum Write: Equatable { case control(Data), packets([Data]) }
    enum Outcome: Equatable { case writes([Write]), activated, failed(String) }
    private enum Phase { case idle, starting, initializing, streaming, validating, done }
    private enum Op { static let start: UInt8 = 1, initialize: UInt8 = 2, receive: UInt8 = 3, validate: UInt8 = 4, activate: UInt8 = 5, receipts: UInt8 = 8, response: UInt8 = 16, receipt: UInt8 = 17 }
    private static let applicationImage: UInt8 = 4, success: UInt8 = 1

    let image: Data, initPacket: Data, receiptInterval: Int, chunk: Int
    private var phase = Phase.idle, sent = 0
    private(set) var acknowledged = 0
    init(image: Data, initPacket: Data, receiptInterval: Int = 10, chunk: Int = 20) {
        self.image = image; self.initPacket = initPacket
        self.receiptInterval = max(1, min(100, receiptInterval)); self.chunk = max(1, min(244, chunk))
    }
    var progress: Double { image.isEmpty ? 0 : Double(acknowledged) / Double(image.count) }

    mutating func start() -> Outcome {
        guard phase == .idle else { return .failed("already started") }
        phase = .starting
        var sizes = Data(count: 8)
        var app = UInt32(image.count).littleEndian
        sizes.append(Data(bytes: &app, count: 4)) // softdevice 0, bootloader 0, application
        return .writes([.control(Data([Op.start, Self.applicationImage])), .packets([sizes])])
    }

    mutating func receive(_ value: Data) -> Outcome {
        let b = [UInt8](value)
        guard let op = b.first else { return fail("empty notification") }
        if op == Op.receipt {
            guard phase == .streaming, b.count == 5 else { return fail("unexpected receipt") }
            let bytes = Int(UInt32(b[1]) | UInt32(b[2]) << 8 | UInt32(b[3]) << 16 | UInt32(b[4]) << 24)
            guard bytes == sent else { return fail("the board received \(bytes) bytes, not \(sent)") }
            acknowledged = bytes
            return sent < image.count ? .writes([.packets(nextBurst())]) : .writes([])
        }
        guard op == Op.response, b.count == 3 else { return fail("unexpected notification") }
        let procedure = b[1], status = b[2]
        guard status == Self.success else { return fail("procedure \(procedure) failed with status \(status)") }
        switch (phase, procedure) {
        case (.starting, Op.start):
            phase = .initializing
            return .writes([.control(Data([Op.initialize, 0])), .packets(chunks(initPacket)), .control(Data([Op.initialize, 1]))])
        case (.initializing, Op.initialize):
            phase = .streaming
            let n = UInt16(receiptInterval)
            return .writes([.control(Data([Op.receipts, UInt8(n & 0xff), UInt8(n >> 8)])), .control(Data([Op.receive])), .packets(nextBurst())])
        case (.streaming, Op.receive):
            guard sent == image.count else { return fail("image response before every byte was sent") }
            acknowledged = sent; phase = .validating
            return .writes([.control(Data([Op.validate]))])
        case (.validating, Op.validate):
            phase = .done
            return .activated // The caller then writes Activate and expects the board to restart.
        default: return fail("out-of-order response \(procedure)")
        }
    }
    static let activate = Data([5])

    private mutating func fail(_ reason: String) -> Outcome { phase = .done; return .failed(reason) }
    private func chunks(_ data: Data) -> [Data] {
        stride(from: 0, to: data.count, by: chunk).map { data.subdata(in: data.startIndex + $0 ..< data.startIndex + min(data.count, $0 + chunk)) }
    }
    private mutating func nextBurst() -> [Data] {
        var out: [Data] = []
        while out.count < receiptInterval && sent < image.count {
            let end = min(image.count, sent + chunk)
            out.append(image.subdata(in: image.startIndex + sent ..< image.startIndex + end)); sent = end
        }
        return out
    }
}

// ---------- Request ----------
/// Root's install workflow asks for an update with a private, same-user file
/// in the receiver's support folder, the same mechanism as guide.request.
/// `{"version":1,"id":"<32 hex>","package":"<absolute directory>","sha256":"<64 hex>","firmware":7,"firstTrial":true,"acceptUSBRecovery":true}`
/// acceptUSBRecovery defaults to false for an older six-field request.
/// The workflow owns the Agent Flow idle check and Ethan's heads-up before writing it.
struct WandSenseUpdateRequest: Equatable {
    static let fileName = "firmware-update.request"
    let id: String, package: URL, sha256: String, firmware: Int, firstTrial: Bool
    var acceptUSBRecovery = false
    static func parse(_ data: Data) -> WandSenseUpdateRequest? {
        guard data.count <= 1024, let v = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
              (v.count == 6 || v.count == 7), Set(v.keys).isSubset(of: ["version", "id", "package", "sha256", "firmware", "firstTrial", "acceptUSBRecovery"]),
              let version = v["version"] as? NSNumber, CFGetTypeID(version) != CFBooleanGetTypeID(), version == 1,
              let id = v["id"] as? String, id.count == 32, id.allSatisfy({ $0.isHexDigit && !$0.isUppercase }),
              let path = v["package"] as? String, path.hasPrefix("/"), !path.contains("/../"),
              let sha = v["sha256"] as? String, sha.count == 64, sha.allSatisfy({ $0.isHexDigit && !$0.isUppercase }),
              let firmware = v["firmware"] as? NSNumber, CFGetTypeID(firmware) != CFBooleanGetTypeID(), firmware.doubleValue == Double(firmware.intValue), (1...999_999).contains(firmware.intValue),
              let trial = v["firstTrial"] as? NSNumber, CFGetTypeID(trial) == CFBooleanGetTypeID() else { return nil }
        var accepted = false
        if let value = v["acceptUSBRecovery"] {
            guard let n = value as? NSNumber, CFGetTypeID(n) == CFBooleanGetTypeID() else { return nil }
            accepted = n.boolValue
        }
        return .init(id: id, package: URL(fileURLWithPath: path, isDirectory: true), sha256: sha, firmware: firmware.intValue,
                     firstTrial: trial.boolValue, acceptUSBRecovery: accepted)
    }
    static func take(at path: String) -> WandSenseUpdateRequest? {
        takeData(at: path).flatMap(parse)
    }
    static func takeData(at path: String) -> Data? {
        let fd = open(path, O_RDONLY | O_NOFOLLOW | O_NONBLOCK)
        guard fd >= 0 else { if errno == ELOOP { unlink(path) }; return nil }
        defer { close(fd) }
        unlink(path)
        var info = stat()
        guard fstat(fd, &info) == 0, info.st_uid == geteuid(), info.st_mode & S_IFMT == S_IFREG,
              info.st_mode & 0o077 == 0, info.st_size > 0, info.st_size <= 1024 else { return nil }
        var bytes = [UInt8](repeating: 0, count: Int(info.st_size))
        guard read(fd, &bytes, bytes.count) == bytes.count else { return nil }
        return Data(bytes)
    }
}

// Explicitly acknowledge one observed result; this never starts a transfer.
// Same private-file permissions as firmware-update.request. The caller must
// name the board, running firmware and exact pending target it observed.
struct WandSenseUpdateReconcileRequest: Equatable {
    static let fileName = "firmware-update-reconcile.request"
    let id: String, boardID: String
    let running: Int, target: Int
    static func parse(_ data: Data) -> Self? {
        guard data.count <= 1024, let v = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any], v.count == 5,
              let version = v["version"] as? NSNumber, CFGetTypeID(version) != CFBooleanGetTypeID(), version == 1,
              let id = v["id"] as? String, id.count == 32, id.allSatisfy({ $0.isHexDigit && !$0.isUppercase }),
              let board = v["boardID"] as? String, board.count == 16, board.allSatisfy({ $0.isHexDigit && !$0.isUppercase }),
              let running = v["running"] as? NSNumber, CFGetTypeID(running) != CFBooleanGetTypeID(), running.doubleValue == Double(running.intValue), (1...999_999).contains(running.intValue),
              let target = v["target"] as? NSNumber, CFGetTypeID(target) != CFBooleanGetTypeID(), target.doubleValue == Double(target.intValue), (1...999_999).contains(target.intValue) else { return nil }
        return .init(id: id, boardID: board, running: running.intValue, target: target.intValue)
    }
    static func take(at path: String) -> Self? { WandSenseUpdateRequest.takeData(at: path).flatMap(parse) }
    func matches(_ info: WandSenseInfo) -> Bool {
        info.id == boardID && info.update.firmwareNumber == running && info.update.pendingTarget == target && info.update.result == (running == target ? "installed" : "not-installed")
    }
}

// The initial identity does not establish a firmware control session. Always
// send H first, then USB provisioning; success is recorded only after KEY saved.
struct WandSenseUpdateSetup {
    private(set) var keyBoardID: String?
    mutating func begin(boardID: String, provision: String?) -> [String] {
        keyBoardID = provision == nil ? nil : boardID
        return [WandSenseCommand.heartbeat] + (provision.map { [$0] } ?? [])
    }
    mutating func keySaved(boardID: String) -> Bool {
        guard keyBoardID == boardID else { return false }
        keyBoardID = nil; return true
    }
    mutating func reset() { keyBoardID = nil }
}

// ---------- Background preparation ----------
/// Owns one disk/key read at a time. State is main-thread confined; the worker
/// receives immutable inputs and delivers only its result back to the main queue.
final class WandSenseUpdatePreparation {
    struct Prepared { let package: WandSenseDFUPackage; let key: SymmetricKey }
    struct Timing { let startedMS: Double; let endedMS: Double }
    typealias Enqueue = (@escaping () -> Void) -> Void
    private let work: Enqueue, deliver: Enqueue
    private let clock: () -> Double
    private var active: UUID?
    private var cancelled = false
    var busy: Bool { active != nil }

    init(work: @escaping Enqueue = { job in DispatchQueue.global(qos: .userInitiated).async(execute: DispatchWorkItem(block: job)) },
         deliver: @escaping Enqueue = { job in DispatchQueue.main.async(execute: job) },
         clock: @escaping () -> Double = { ProcessInfo.processInfo.systemUptime * 1000 }) {
        self.work = work; self.deliver = deliver; self.clock = clock
    }
    /// Cancellation keeps the slot occupied until the old worker returns, so
    /// reconnects cannot accumulate overlapping disk reads or reuse old results.
    func cancel() { if active != nil { cancelled = true } }
    @discardableResult
    func start(load: @escaping () throws -> Prepared,
               complete: @escaping (Result<Prepared, Error>, Timing, Bool) -> Void) -> Bool {
        guard active == nil else { return false }
        let token = UUID(); active = token; cancelled = false
        work { [self] in
            let start = clock()
            let result = Result { try load() }
            let timing = Timing(startedMS: start, endedMS: clock())
            deliver { [self] in
                guard active == token else { return }
                let valid = !cancelled
                active = nil; cancelled = false
                complete(result, timing, valid)
            }
        }
        return true
    }
}

// ---------- Flow ----------
/// The whole update as a pure state machine; WandReceiverSenseUpdate.swift
/// performs its effects. Each state has one way forward and fails closed.
struct WandSenseUpdateFlow: Equatable {
    enum State: String { case idle, preparing, challenging, authorizing, handingOver, transferring, restarting, verifying, reconciling, done, failed }
    enum Effect: Equatable { case send(String), beginTransfer, report }
    private(set) var state = State.idle
    private(set) var detail = ""
    private(set) var target = 0
    private var boardID = ""
    private var reconciliationInstalled = false

    var busy: Bool { ![.idle, .done, .failed].contains(state) }

    mutating func prepare(boardID: String, target: Int) -> [Effect] {
        guard !busy else { return [] }
        self.boardID = boardID; self.target = target; state = .preparing; detail = ""
        return [.report]
    }
    mutating func prepared(boardID: String, target: Int) -> [Effect] {
        guard state == .preparing, self.boardID == boardID, self.target == target else { return [] }
        state = .challenging
        return [.send(WandSenseUpdateAuth.challenge), .report]
    }
    mutating func preparationFailed(_ reason: String) -> [Effect] {
        guard state == .preparing else { return [] }
        return fail(reason)
    }
    /// Preflight already passed for this board and package.
    mutating func begin(boardID: String, target: Int) -> [Effect] {
        guard !busy else { return [] }
        self.boardID = boardID; self.target = target; reconciliationInstalled = false; state = .challenging; detail = ""
        return [.send(WandSenseUpdateAuth.challenge), .report]
    }
    mutating func reply(_ reply: WandSenseUpdateReply, authorize: (String) -> String) -> [Effect] {
        switch (state, reply) {
        case (.challenging, .challenge(let nonce)):
            state = .authorizing
            return [.send(authorize(nonce)), .report]
        case (.authorizing, .go):
            state = .handingOver
            return [.beginTransfer, .report]
        case (.challenging, .refused(let why)), (.authorizing, .refused(let why)):
            return fail("The wand refused the update: \(why). Its current firmware keeps running.")
        case (.reconciling, .refused(let why)), (.verifying, .refused(let why)):
            return fail(detail + " The wand refused confirmation: \(why). Its result is still unconfirmed.")
        default: return []
        }
    }
    mutating func transferStarted() -> [Effect] { guard state == .handingOver else { return [] }; state = .transferring; return [.report] }
    mutating func transferEnded(_ error: String?) -> [Effect] {
        guard state == .handingOver || state == .transferring else { return [] }
        if let error { return fail("Transfer failed: \(error). The application may be incomplete; resetting cannot restore overwritten firmware. Use the checked USB application-recovery package if the wand cannot start.") }
        state = .restarting; return [.report]
    }
    /// The next identity after the transfer decides the result.
    mutating func identity(_ info: WandSenseInfo) -> [Effect] {
        guard (state == .restarting || state == .verifying), info.id == boardID else { return [] }
        // If V ok was lost during a reconnect, a fresh same-board identity
        // confirms the durable clear. Otherwise send UV again after H.
        if state == .verifying, info.update.firmwareNumber == target, info.update.result == "none" {
            return verified(boardID: info.id)
        }
        guard info.update.firmwareNumber == target, info.update.result == "installed" else {
            return fail("The wand restarted with firmware \(info.update.firmwareNumber.map(String.init) ?? info.firmware), not \(target); the update was not installed.")
        }
        state = .verifying
        return [.send(WandSenseUpdateAuth.confirm), .report]
    }
    mutating func reconcile(_ request: WandSenseUpdateReconcileRequest, info: WandSenseInfo) -> [Effect] {
        guard !busy, request.matches(info) else { return [] }
        reconciliationInstalled = request.running == request.target
        if reconciliationInstalled {
            detail = "Firmware \(request.target) is running; awaiting confirmation."
        } else if state != .failed || boardID != info.id || target != request.target {
            detail = "Firmware \(request.target) was not installed; firmware \(request.running) keeps running."
        }
        boardID = info.id; target = request.target; state = .reconciling
        return [.send(reconciliationInstalled ? WandSenseUpdateAuth.confirm : "UR\(request.running),\(request.target)"), .report]
    }
    mutating func verified(boardID: String) -> [Effect] {
        guard boardID == self.boardID else { return [] }
        switch state {
        case .verifying: state = .done; detail = "Firmware \(target) installed and confirmed."
        case .reconciling:
            if reconciliationInstalled { state = .done; detail = "Firmware \(target) installed and confirmed." }
            else { state = .failed; detail += " Failed attempt acknowledged; retry is available." }
        default: return []
        }
        return [.report]
    }
    mutating func connectionLost() -> [Effect] {
        // Losing the link is expected once the board hands over.
        if state == .reconciling { return fail(detail + " Acknowledgement was interrupted; the update result is still unconfirmed.") }
        guard state == .preparing || state == .challenging || state == .authorizing else { return [] }
        return fail("The wand disconnected before authorizing the update. Its current firmware keeps running.")
    }
    mutating func timedOut() -> [Effect] {
        switch state {
        case .preparing: return fail("Preparing the update timed out. Its current firmware keeps running.")
        case .challenging, .authorizing: return fail("The wand did not answer the update request. Its current firmware keeps running.")
        case .reconciling: return fail(detail + " The wand did not acknowledge clearing the update result.")
        case .restarting, .verifying: return fail("The wand did not reconnect after the transfer. Check the light; reset the wand or use USB recovery if it stays in updater mode.")
        default: return []
        }
    }
    private mutating func fail(_ text: String) -> [Effect] { state = .failed; detail = text; return [.report] }
}

// ---------- CoreBluetooth transfer ----------
/// Connects to the exact peripheral that handed over (same identifier) and
/// runs WandSenseLegacyDFU. Never scans for or accepts a device by name.
final class WandSenseDFUTransfer: NSObject, CBPeripheralDelegate {
    let peripheralID: UUID
    private let central: CBCentralManager
    private var protocolClient: WandSenseLegacyDFU
    private var peripheral: CBPeripheral?, control: CBCharacteristic?, packet: CBCharacteristic?
    private var queue: [Data] = [], afterQueue: [WandSenseLegacyDFU.Write] = []
    private var timer: Timer?, finished = false, activating = false, awaitingControl = false
    var onStarted: (() -> Void)?
    var onFinish: ((String?) -> Void)?
    var onLog: ((String) -> Void)?
    static let connectSeconds = 30.0, transferSeconds = 240.0

    init(central: CBCentralManager, peripheralID: UUID, package: WandSenseDFUPackage) {
        self.central = central; self.peripheralID = peripheralID
        self.protocolClient = WandSenseLegacyDFU(image: package.image, initPacket: package.initPacket)
    }
    func owns(_ p: CBPeripheral) -> Bool { p.identifier == peripheralID }

    func start() {
        guard let p = central.retrievePeripherals(withIdentifiers: [peripheralID]).first else { finish("the updater was not found by its Bluetooth identity"); return }
        peripheral = p; p.delegate = self
        timer = WandRunLoop.commonTimer(interval: Self.connectSeconds, repeats: false) { [weak self] _ in self?.finish("the updater did not accept a connection") }
        central.connect(p); onLog?("SENSE_UPDATE_CONNECTING")
    }
    // Forwarded by WandSenseLink while the transfer owns the central.
    func didConnect(_ p: CBPeripheral) { guard owns(p) else { return }; p.discoverServices([WandSenseLegacyDFU.service]) }
    func didFailToConnect(_ p: CBPeripheral) { guard owns(p) else { return }; finish("the updater connection failed") }
    func didDisconnect(_ p: CBPeripheral) {
        guard owns(p) else { return }
        // After Activate the bootloader validates, swaps banks and restarts.
        finish(activating ? nil : "the updater disconnected during the transfer")
    }

    func peripheral(_ p: CBPeripheral, didDiscoverServices error: Error?) {
        guard error == nil, let s = p.services?.first(where: { $0.uuid == WandSenseLegacyDFU.service }) else { finish("no updater service on this board"); return }
        p.discoverCharacteristics([WandSenseLegacyDFU.control, WandSenseLegacyDFU.packet], for: s)
    }
    func peripheral(_ p: CBPeripheral, didDiscoverCharacteristicsFor s: CBService, error: Error?) {
        control = s.characteristics?.first { $0.uuid == WandSenseLegacyDFU.control }
        packet = s.characteristics?.first { $0.uuid == WandSenseLegacyDFU.packet }
        guard error == nil, let control, packet != nil else { finish("the updater service is incomplete"); return }
        p.setNotifyValue(true, for: control)
    }
    func peripheral(_ p: CBPeripheral, didUpdateNotificationStateFor c: CBCharacteristic, error: Error?) {
        guard error == nil, c.isNotifying else { finish("the updater refused notifications"); return }
        timer?.invalidate()
        timer = WandRunLoop.commonTimer(interval: Self.transferSeconds, repeats: false) { [weak self] _ in self?.finish("the transfer took too long") }
        onStarted?(); onLog?("SENSE_UPDATE_TRANSFER_STARTED")
        perform(protocolClient.start())
    }
    func peripheral(_ p: CBPeripheral, didUpdateValueFor c: CBCharacteristic, error: Error?) {
        guard c.uuid == WandSenseLegacyDFU.control, error == nil, let value = c.value else { return }
        perform(protocolClient.receive(value))
    }
    func peripheral(_ p: CBPeripheral, didWriteValueFor c: CBCharacteristic, error: Error?) {
        guard p === peripheral, !finished, c.uuid == WandSenseLegacyDFU.control else { return }
        if error != nil { finish(activating ? "the activation write failed" : "a control write failed"); return }
        if activating { return } // Activate normally reboots before another notification.
        awaitingControl = false; drain()
    }
    func peripheralIsReady(toSendWriteWithoutResponse p: CBPeripheral) { drain() }

    private func perform(_ outcome: WandSenseLegacyDFU.Outcome) {
        switch outcome {
        case .failed(let reason): finish(reason)
        case .activated:
            guard let p = peripheral, let control else { return }
            activating = true; onLog?("SENSE_UPDATE_VALIDATED")
            p.writeValue(WandSenseLegacyDFU.activate, for: control, type: .withResponse)
        case .writes(let writes):
            afterQueue.append(contentsOf: writes); drain()
        }
    }
    /// Strict order: each control write is acknowledged before anything after
    /// it is sent, and packets go only when the link can take them.
    private func drain() {
        guard let p = peripheral, let control, let packet, !finished, !awaitingControl else { return }
        while true {
            while let next = queue.first {
                guard p.canSendWriteWithoutResponse else { return }
                p.writeValue(next, for: packet, type: .withoutResponse); queue.removeFirst()
            }
            guard !afterQueue.isEmpty else { return }
            switch afterQueue.removeFirst() {
            case .control(let data): awaitingControl = true; p.writeValue(data, for: control, type: .withResponse); return
            case .packets(let data): queue.append(contentsOf: data)
            }
        }
    }
    func finish(_ error: String?) {
        guard !finished else { return }
        finished = true; timer?.invalidate(); timer = nil
        if error != nil, let p = peripheral { central.cancelPeripheralConnection(p) }
        onLog?(error.map { "SENSE_UPDATE_TRANSFER_FAILED \($0)" } ?? "SENSE_UPDATE_TRANSFER_DONE")
        onFinish?(error)
    }
}
