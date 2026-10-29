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

    /// Test seam: replaces the socket write. Same contract as `socketSend`.
    var deliver: (([String: Any], String, Int) -> Bool)?
    @discardableResult
    private func send(_ object: [String: Any], path: String, limit: Int) -> Bool {
        if let deliver { return deliver(object, path, limit) }
        return socketSend(object, path: path, limit: limit)
    }
    private func socketSend(_ object: [String: Any], path: String, limit: Int) -> Bool {
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

    /// Ethan's debug pause (WandActionPause): no new HUD, review, screenshot or
    /// dictation command leaves the receiver. Closing the wand's own HUD session
    /// is still allowed, and nothing is sent to Agent Flow, so a recording in
    /// progress is never stopped. `refused` counts blocked commands for tests.
    var suspended = false { didSet { if suspended { discardPendingPersistent(keepingCleanup:true) } } }
    private(set) var refused = 0
    private func allowed() -> Bool { if suspended { refused += 1 }; return !suspended }

    func beginHUD() -> Bool {
        guard allowed() else { return false }
        cancelHUD(reason: "user")
        let id = UUID().uuidString
        gestureID = id; lastGestureID = id; sequence = 0
        let sent = send(["command":"agentic_mouse_wand_selection", "version":1,
                         "phase":"begin", "gesture_id":id, "seq":sequence], path:agenticPath, limit:512)
        if !sent { gestureID = nil; lastGestureID = nil }
        return sent
    }

    func updateHUD(x: Double, y: Double, ending: Bool = false) -> Bool {
        guard allowed(), let id = gestureID, x.isFinite, y.isFinite, abs(x) <= 7200, abs(y) <= 7200 else { return false }
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
    /// State-changing HUD packets retain order only within the current live
    /// session. Motion is cumulative and never queued. Pause/dismiss/reset
    /// invalidate earlier actions; a busy main queue never extends the deadline.
    private struct Pending { let packet:[String:Any]; let queuedAt:TimeInterval }
    private var outbox:[Pending]=[]
    private var flushScheduled=false,flushGeneration:UInt64=0
    private(set) var droppedPackets=0
    var retryDelay:TimeInterval=0.015
    var monotonicNow:()->TimeInterval = {ProcessInfo.processInfo.systemUptime}
    private func cleanup(_ packet:[String:Any])->Bool { ["dismiss","park"].contains(packet["phase"] as? String ?? "") }
    func discardPendingPersistent(keepingCleanup:Bool=false) {
        let before=outbox.count
        outbox=keepingCleanup ? outbox.filter{cleanup($0.packet)} : []
        droppedPackets+=before-outbox.count
        flushGeneration &+= 1;flushScheduled=false
        if !outbox.isEmpty {flushOutbox()}
    }
    func persistent(_ phase:String,x:Double=0,y:Double=0,mouseX:Double?=nil) {
        guard phase == "dismiss" || phase == "park" || allowed() else {return}
        // A dismiss ends the journey; no older refused selection may precede it.
        if phase == "dismiss" {discardPendingPersistent()}
        if ["open","hover","navigate","press","activate","choose","dismiss","toggleReview"].contains(phase) {persistentID=UUID().uuidString;persistentSequence=0}
        persistentSequence += 1
        var packet:[String:Any] = ["command":"agentic_mouse_wand_control","version":1,"phase":phase,"id":persistentID,
                "seq":persistentSequence,"x":x,"y":y]
        if phase=="motion",let mouseX,mouseX.isFinite,abs(mouseX)<=7_200_000 {packet["mouseX"]=mouseX}
        if phase == "motion" {
            if outbox.isEmpty, !send(packet,path:agenticPath,limit:512) {droppedPackets += 1}
            return
        }
        guard outbox.count<64 else {discardPendingPersistent();droppedPackets+=1;return}
        outbox.append(Pending(packet:packet,queuedAt:monotonicNow()))
        flushOutbox()
    }
    private func flushOutbox() {
        while let pending=outbox.first {
            guard monotonicNow()-pending.queuedAt<=1 else {discardPendingPersistent();return}
            if suspended && !cleanup(pending.packet) {outbox.removeFirst();droppedPackets+=1;continue}
            guard send(pending.packet,path:agenticPath,limit:512) else {
                guard !flushScheduled else {return}
                flushScheduled=true;let generation=flushGeneration
                DispatchQueue.main.asyncAfter(deadline:.now()+retryDelay){[weak self] in
                    guard let self,self.flushGeneration==generation else{return}
                    self.flushScheduled=false;self.flushOutbox()
                }
                return
            }
            outbox.removeFirst()
        }
    }
    /// Pending state-changing HUD packets (for tests and diagnostics).
    var pendingPackets:Int {outbox.count}

    /// Ethan's Bottom triple-click. Agentic Mouse starts its native selected-area
    /// screenshot for a fresh identity and ignores a repeated one; this request
    /// never cancels an active selection and sends no keyboard shortcut itself.
    @discardableResult
    func screenshotStart(id: String = UUID().uuidString) -> Bool {
        guard allowed() else { return false }
        return send(["command":"agentic_mouse_wand_screenshot_start", "version":1, "id":id],
             path:agenticPath, limit:256)
    }

    func speech(down: Bool) -> Bool {
        guard allowed() else { return false }
        guard down != speechPressed else { return true }
        let sent = send(["version":1, "action":"primaryRecordingMouse", "source":"wand",
                         "phase":down ? "down" : "up"], path:speechPath, limit:256)
        speechPressed = down && sent
        return sent
    }

    func cancel() {
        discardPendingPersistent()
        cancelHUD()
        persistent("dismiss")
        // Paused: leave Agent Flow's button state alone rather than risk ending a recording.
        guard !suspended else { return }
        if speechPressed {
            _ = send(["version":1, "action":"primaryRecordingMouse", "source":"wand", "phase":"cancel"], path:speechPath, limit:256)
        }
        speechPressed = false
    }
}
