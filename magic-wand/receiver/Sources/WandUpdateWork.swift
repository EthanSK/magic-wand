// Read the agent's bounded update-work lease; it prevents automatic deep sleep
// while changes are prepared, without changing mouse input or manual shutdown.
import Foundation
import Darwin

struct WandUpdateWork {
    static let fileName = "update-work.json"
    static let maximumSeconds = 1800.0
    private(set) var expiresAt = 0.0

    func active(at now: Double) -> Bool { now.isFinite && now < expiresAt }

    /// A lease survives a receiver restart, but never keeps an abandoned wand
    /// awake indefinitely. Agents renew it only while actually working and
    /// clear it when done. Missing, expired or unsafe files mean normal sleep.
    static func read(from url: URL, now: Double) -> Double {
        let fd = open(url.path, O_RDONLY | O_NOFOLLOW | O_NONBLOCK)
        guard fd >= 0 else { return 0 }
        defer { close(fd) }
        var info = stat()
        guard fstat(fd, &info) == 0, info.st_uid == geteuid(),
              info.st_mode & S_IFMT == S_IFREG, info.st_mode & 0o077 == 0,
              info.st_size > 0, info.st_size <= 256 else { return 0 }
        var bytes = [UInt8](repeating: 0, count: Int(info.st_size))
        guard Darwin.read(fd, &bytes, bytes.count) == bytes.count,
              let value = try? JSONSerialization.jsonObject(with: Data(bytes)) as? [String: Any],
              value.count == 2,
              let version = value["version"] as? NSNumber,
              CFGetTypeID(version) != CFBooleanGetTypeID(), version == 1,
              let expiry = value["expiresAt"] as? NSNumber,
              CFGetTypeID(expiry) != CFBooleanGetTypeID() else { return 0 }
        let until = expiry.doubleValue
        guard now.isFinite, until.isFinite, until > now,
              until - now <= maximumSeconds else { return 0 }
        return until
    }

    @discardableResult mutating func refresh(from url: URL, now: Double) -> Bool {
        let value = Self.read(from: url, now: now)
        guard value != expiresAt else { return false }
        expiresAt = value
        return true
    }
}
