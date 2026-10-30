import Foundation
import Darwin

/// Ethan's debug pause: "temporarily turn off how it's sending things just so I
/// can debug it without it actually affecting doing real stuff." While paused the
/// receiver keeps reading the wand (dashboard telemetry, lights, power, calibration,
/// desk sleep) but sends no pointer, click, drag, scroll, dwell click, HUD, review,
/// screenshot, recentre or dictation action. An ongoing recording is never stopped.
/// Memory only: a receiver restart clears it; status.json reports the actual state.
struct WandActionPause {
    /// One lane per custom button. Previously the cases were bottom, middle and top.
    enum Lane: CaseIterable { case mouseButton, hudButton, speechButton }
    private(set) var paused = false
    private(set) var since: Date?
    /// The last dashboard request this receiver applied, echoed in status.json
    /// so the dashboard confirms the receiver's state instead of assuming it.
    private(set) var lastRequest: String?
    private var settling: Set<Lane> = []

    @discardableResult mutating func pause(at date: Date = Date()) -> Bool {
        guard !paused else { return false }
        paused = true; since = date; settling = []
        return true
    }
    @discardableResult mutating func resume() -> Bool {
        guard paused else { return false }
        paused = false; since = nil; settling = Set(Lane.allCases)
        return true
    }
    mutating func acknowledge(_ request: String) { lastRequest = request }

    /// One reported button edge. Nothing acts while paused. After resume, the
    /// first edge of each lane decides: a press is fresh input; a release ends a
    /// press from the paused interval and is swallowed, so it is never replayed.
    mutating func admit(_ lane: Lane, down: Bool) -> Bool {
        guard !paused else { return false }
        guard settling.remove(lane) != nil else { return true }
        return down
    }
}

/// The dashboard's private request: a same-user file in the receiver's own
/// support directory, written atomically by the read-only dashboard server.
/// It carries no code; only {"version":1,"paused":bool,"id":"<32 hex>"}.
struct WandActionPauseRequest: Equatable {
    static let fileName = "actions-pause.request"
    let paused: Bool
    let id: String

    static func parse(_ data: Data) -> WandActionPauseRequest? {
        guard data.count <= 256, let value = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
              value.count == 3, let version = value["version"] as? NSNumber, !isBoolean(version), version == 1,
              let paused = value["paused"] as? NSNumber, isBoolean(paused),
              let id = value["id"] as? String, id.count == 32, id.allSatisfy({ $0.isHexDigit && !$0.isUppercase }) else { return nil }
        return .init(paused: paused.boolValue, id: id)
    }

    /// Read and remove one pending request. Only a private, same-user regular
    /// file is accepted; links, shared permissions and oversized files are not.
    /// Returns nil when there is no request; any file found is consumed.
    static func take(at path: String) -> WandActionPauseRequest? {
        let fd = open(path, O_RDONLY | O_NOFOLLOW | O_NONBLOCK)
        guard fd >= 0 else { if errno == ELOOP { unlink(path) }; return nil }
        defer { close(fd) }
        unlink(path)
        var info = stat()
        guard fstat(fd, &info) == 0, info.st_uid == geteuid(), info.st_mode & S_IFMT == S_IFREG,
              info.st_mode & 0o077 == 0, info.st_size > 0, info.st_size <= 256 else { return nil }
        var bytes = [UInt8](repeating: 0, count: Int(info.st_size))
        guard read(fd, &bytes, bytes.count) == bytes.count else { return nil }
        return parse(Data(bytes))
    }

    private static func isBoolean(_ number: NSNumber) -> Bool { CFGetTypeID(number) == CFBooleanGetTypeID() }
}
