import Foundation
import Darwin

/// Temporary, opt-in local evidence for Ethan's review "corners" / "single flicks".
/// The input callback only copies numbers into a bounded buffer. Configuration,
/// JSON encoding, rotation and disk access run on the utility queue, never there.
final class WandReviewTrace {
    private struct Configuration: Decodable { let enabled: Bool; let captureUntil: Double?; let deleteAfter: Double? }
    struct Metrics: Codable {
        var event: String
        var active: Bool
        var turn: Double
        var effective: Double
        var scale: Double
        var segment: Double
        var pending: Int
        var direction: Int
        var runSteps: Int
        var credit: Double
        var sideways: Double
    }
    struct Frame: Codable {
        var schema = 1
        var kind: String
        var t: Double
        var sequence: UInt64 = 0
        var run: String?
        var build: String?
        var wallTime: Double?
        var reason: String?
        var mode: String?
        var rawX: Double?
        var rawY: Double?
        var x: Double?
        var y: Double?
        var dx: Double?
        var dy: Double?
        var eligible: Bool?
        var axisGestures: Bool?
        var step: Int?
        var phase: String?
        var direction: String?
        var metrics: Metrics?
        var dropped: UInt64?
    }
    private let lock = NSLock()
    private let queue = DispatchQueue(label: "wand.review-trace", qos: .utility)
    private var timer: DispatchSourceTimer?
    private var pending: [Frame] = []
    private var captureEnabled = false
    private var captureUntil = 0.0, deleteAfter = 0.0
    private let wallClock: () -> Double
    private var dropped: UInt64 = 0
    private var totalDropped: UInt64 = 0
    private var sequence: UInt64 = 0
    private var diskError = false
    private let bufferLimit = 512
    private let directory: URL, configuration: URL
    private let maximumBytes: Int, fileCount: Int, build: String
    private let run = UUID().uuidString
    private var file: FileHandle?
    private var size = 0
    private var lastConfigurationCheck = -Double.infinity
    private let encoder = JSONEncoder()

    init(directory: URL, configuration: URL, build: String, maximumBytes: Int = 2 * 1024 * 1024, fileCount: Int = 4, wallClock: @escaping () -> Double = { Date().timeIntervalSince1970 }) {
        self.directory = directory; self.configuration = configuration; self.build = build
        self.wallClock = wallClock
        self.maximumBytes = max(1024, maximumBytes); self.fileCount = max(1, min(8, fileCount))
        pending.reserveCapacity(bufferLimit)
        let timer = DispatchSource.makeTimerSource(queue: queue)
        timer.schedule(deadline: .now(), repeating: .seconds(1), leeway: .milliseconds(100))
        timer.setEventHandler { [weak self] in self?.drain() }
        self.timer = timer; timer.resume()
    }
    var enabled: Bool { lock.lock(); defer { lock.unlock() }; return captureEnabled }
    var status: [String: Any] {
        lock.lock(); defer { lock.unlock() }
        return ["enabled": captureEnabled, "buffered": pending.count, "dropped": totalDropped,
                "diskError": diskError, "maximumFiles": fileCount, "maximumFileBytes": maximumBytes,
                "captureUntil": captureUntil, "deleteAfter": deleteAfter]
    }
    func record(_ frame: Frame) {
        lock.lock(); defer { lock.unlock() }
        guard captureEnabled, wallClock() < captureUntil else { return }
        guard pending.count < bufferLimit else { dropped += 1; totalDropped += 1; return }
        var frame = frame; sequence += 1; frame.sequence = sequence
        pending.append(frame)
    }
    func boundary(_ reason: String, mode: String? = nil, now: Double = ProcessInfo.processInfo.systemUptime) {
        record(Frame(kind: "boundary", t: now, reason: reason, mode: mode))
    }
    private func trusted(_ path: URL, directory: Bool) -> Bool {
        var s = stat()
        guard lstat(path.path, &s) == 0, s.st_uid == geteuid(), s.st_mode & 0o022 == 0 else { return false }
        return s.st_mode & S_IFMT == (directory ? S_IFDIR : S_IFREG) && (!directory || s.st_mode & 0o077 == 0)
    }
    private func reloadConfiguration(now: Double) -> Frame? {
        guard now - lastConfigurationCheck >= 0.5 else { return nil }
        lastConfigurationCheck = now
        var wanted = false
        let wall = wallClock()
        var end = 0.0, deletion = 0.0
        if trusted(configuration, directory: false),
           ((try? configuration.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? Int.max) <= 1024,
           let data = try? Data(contentsOf: configuration),
           let json = try? JSONDecoder().decode(Configuration.self, from: data) {
            // A persistent deadline is required: the old {enabled:true} switch
            // must not silently renew indefinite capture after a restart.
            if let until = json.captureUntil, let after = json.deleteAfter,
               until.isFinite, after.isFinite, after >= until {
                end = until; deletion = after
                wanted = json.enabled && wall < until
            }
        }
        lock.lock(); let changed = wanted != captureEnabled; captureEnabled = wanted
        captureUntil = end; deleteAfter = deletion; lock.unlock()
        if deletion > 0 && wall >= deletion { purgeTemporaryFiles() }
        if changed {
            timer?.schedule(deadline: .now() + (wanted ? 0.25 : 1),
                            repeating: wanted ? .milliseconds(250) : .seconds(1), leeway: .milliseconds(50))
            return Frame(kind: "capture", t: now, run: run, build: build,
                         wallTime: Date().timeIntervalSince1970, reason: wanted ? "enabled" : "disabled")
        }
        return nil
    }
    private func traceURL(_ index: Int) -> URL {
        directory.appendingPathComponent(index == 0 ? "trace.jsonl" : "trace.\(index).jsonl")
    }
    private func purgeTemporaryFiles() {
        try? file?.close(); file = nil; size = 0
        guard trusted(directory, directory: true) else { return }
        // Never enumerate or remove reference libraries or neighbouring files.
        for index in 0..<8 {
            let path = traceURL(index)
            guard trusted(path, directory: false) else { continue }
            do { try FileManager.default.removeItem(at: path) }
            catch { lock.lock(); diskError = true; lock.unlock() }
        }
    }
    private func ensureFile() throws {
        if file != nil { return }
        if !FileManager.default.fileExists(atPath: directory.path) {
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false,
                                                   attributes: [.posixPermissions: 0o700])
        }
        guard trusted(directory, directory: true) else { throw CocoaError(.fileWriteNoPermission) }
        let url = traceURL(0)
        // O_NOFOLLOW also closes the check/open race for the trace itself.
        let fd = open(url.path, O_WRONLY | O_CREAT | O_APPEND | O_NOFOLLOW, 0o600)
        guard fd >= 0 else { throw CocoaError(.fileWriteUnknown) }
        var s = stat()
        guard fstat(fd, &s) == 0, s.st_uid == geteuid(), s.st_mode & S_IFMT == S_IFREG,
              s.st_mode & 0o077 == 0 else { close(fd); throw CocoaError(.fileWriteNoPermission) }
        file = FileHandle(fileDescriptor: fd, closeOnDealloc: true); size = Int(s.st_size)
    }
    private func rotate() throws {
        try? file?.close(); file = nil
        let manager = FileManager.default
        if manager.fileExists(atPath: traceURL(fileCount - 1).path) { try manager.removeItem(at: traceURL(fileCount - 1)) }
        if fileCount > 1 {
            for index in stride(from: fileCount - 2, through: 0, by: -1) {
                let from = traceURL(index)
                if manager.fileExists(atPath: from.path) { try manager.moveItem(at: from, to: traceURL(index + 1)) }
            }
        }
        try ensureFile()
    }
    private func append(_ frame: Frame) {
        do {
            var data = try encoder.encode(frame); data.append(0x0a)
            guard data.count <= maximumBytes else { return }
            try ensureFile()
            if size + data.count > maximumBytes { try rotate() }
            try file?.write(contentsOf: data); size += data.count
        } catch {
            try? file?.close(); file = nil
            lock.lock(); diskError = true; lock.unlock()
        }
    }
    private func drain(force: Bool = false) {
        let now = ProcessInfo.processInfo.systemUptime
        if force { lastConfigurationCheck = -Double.infinity }
        let change = reloadConfiguration(now: now)
        lock.lock()
        let batch = pending; pending.removeAll(keepingCapacity: true)
        let lost = dropped; dropped = 0
        lock.unlock()
        // A Mac waking after deletion must not recreate expired files from
        // its queued pre-sleep frames or from the disabled boundary marker.
        if deleteAfter > 0 && wallClock() < deleteAfter {
            if let change, change.reason == "enabled" { append(change) }
            for frame in batch { append(frame) }
            if lost > 0 { append(Frame(kind: "gap", t: now, reason: "capture buffer full", dropped: lost)) }
            if let change, change.reason == "disabled" { append(change) }
        }
        if !enabled { try? file?.close(); file = nil }
    }
    /// Used by the isolated diagnostic tests, never by the motion callback.
    func synchronize() { queue.sync { drain(force: true) } }
    deinit { timer?.cancel(); try? file?.close() }
}
