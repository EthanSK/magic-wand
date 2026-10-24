import Foundation
import Darwin

/// Same-user local datagrams. Never impersonates an ordinary mouse source.
final class WandControlTransport {
    private let agenticPath: String
    private let speechPath: String
    private var gestureID: String?
    private var sequence = 0
    private var lastGestureID: String?
    private var speechPressed = false

    init(agenticPath: String = "/Library/Application Support/org.pqrs/tmp/user/\(geteuid())/user_command_receiver.sock",
         speechPath: String = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/VoiceInkPlusPlus/MouseInput/p.sock").path) {
        self.agenticPath = agenticPath
        self.speechPath = speechPath
    }

    @discardableResult
    private func send(_ object: [String: Any], path: String, limit: Int) -> Bool {
        var metadata = stat()
        guard lstat(path, &metadata) == 0, metadata.st_uid == geteuid(),
              metadata.st_mode & S_IFMT == S_IFSOCK, metadata.st_mode & 0o022 == 0,
              let data = try? JSONSerialization.data(withJSONObject: object, options: [.sortedKeys]),
              data.count <= limit else { return false }
        let fd = socket(AF_UNIX, SOCK_DGRAM, 0)
        guard fd >= 0 else { return false }
        defer { close(fd) }
        _ = fcntl(fd, F_SETFL, O_NONBLOCK)
        var address = sockaddr_un()
        address.sun_family = sa_family_t(AF_UNIX)
        let bytes = Array(path.utf8) + [0]
        guard bytes.count <= MemoryLayout.size(ofValue: address.sun_path) else { return false }
        withUnsafeMutableBytes(of: &address.sun_path) { $0.copyBytes(from: bytes) }
        address.sun_len = UInt8(MemoryLayout<sockaddr_un>.size)
        let result = data.withUnsafeBytes { payload in
            withUnsafePointer(to: &address) { pointer in
                pointer.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                    sendto(fd, payload.baseAddress, data.count, 0, $0, socklen_t(MemoryLayout<sockaddr_un>.size))
                }
            }
        }
        return result == data.count
    }

    func beginHUD() -> Bool {
        cancelHUD(reason: "user")
        let id = UUID().uuidString
        gestureID = id; lastGestureID = id; sequence = 0
        let sent = send(["command":"agentic_mouse_wand_selection", "version":1,
                         "phase":"begin", "gesture_id":id, "seq":sequence], path:agenticPath, limit:512)
        if !sent { gestureID = nil; lastGestureID = nil }
        return sent
    }

    func updateHUD(x: Double, y: Double, ending: Bool = false) -> Bool {
        guard let id = gestureID, x.isFinite, y.isFinite, abs(x) <= 7200, abs(y) <= 7200 else { return false }
        sequence += 1
        let sent = send(["command":"agentic_mouse_wand_selection", "version":1,
                         "phase":ending ? "end" : "update", "gesture_id":id, "seq":sequence,
                         "x_deg":x, "y_deg":y], path:agenticPath, limit:512)
        if ending || !sent { gestureID = nil }
        return sent
    }

    func cancelHUD(reason: String = "disconnect") {
        guard let id = gestureID ?? (reason == "disconnect" ? lastGestureID : nil) else { return }
        sequence += 1
        _ = send(["command":"agentic_mouse_wand_selection", "version":1,
                  "phase":"cancel", "gesture_id":id, "seq":sequence, "reason":reason], path:agenticPath, limit:512)
        gestureID = nil; lastGestureID = nil
    }

    private var persistentID = UUID().uuidString
    private var persistentSequence=0
    func persistent(_ phase:String,x:Double=0,y:Double=0) {
        if ["open","hover","navigate","press","activate","choose","dismiss"].contains(phase) {persistentID=UUID().uuidString;persistentSequence=0}
        persistentSequence += 1
        _=send(["command":"agentic_mouse_wand_control","version":1,"phase":phase,"id":persistentID,
                "seq":persistentSequence,"x":x,"y":y],path:agenticPath,limit:512)
    }

    func speech(down: Bool) -> Bool {
        guard down != speechPressed else { return true }
        let sent = send(["version":1, "action":"primaryRecordingMouse", "source":"wand",
                         "phase":down ? "down" : "up"], path:speechPath, limit:256)
        speechPressed = down && sent
        return sent
    }

    func cancel() {
        cancelHUD()
        persistent("dismiss")
        if speechPressed {
            _ = send(["version":1, "action":"primaryRecordingMouse", "source":"wand", "phase":"cancel"], path:speechPath, limit:256)
        }
        speechPressed = false
    }
}
