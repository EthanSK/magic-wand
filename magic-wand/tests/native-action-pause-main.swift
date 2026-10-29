import Foundation
import Darwin
setbuf(stdout, nil)
// Pure checks for the debug pause: no native input, sockets or hardware.

var p = WandActionPause()
precondition(p.admit(.bottom, down: true) && p.admit(.bottom, down: false), "ordinary edges act before any pause")
precondition(p.pause() && !p.pause(), "pause is idempotent")
for lane in WandActionPause.Lane.allCases {
    precondition(!p.admit(lane, down: true) && !p.admit(lane, down: false), "nothing acts while paused")
}
precondition(p.resume() && !p.resume())
// Bottom was pressed during the pause and is released after resume: swallowed.
precondition(!p.admit(.bottom, down: false), "release of a paused-interval press is never replayed")
precondition(p.admit(.bottom, down: true) && p.admit(.bottom, down: false), "the next press is fresh")
// Middle was up at resume: its first press is fresh input.
precondition(p.admit(.middle, down: true) && p.admit(.middle, down: false))
// Top pressed and released entirely during the pause: no edge reaches it; next press fresh.
precondition(p.admit(.top, down: true))
precondition(p.since == nil && !p.paused)
p.pause(at: Date(timeIntervalSince1970: 100)); precondition(p.since == Date(timeIntervalSince1970: 100))
p.acknowledge("0123456789abcdef0123456789abcdef"); precondition(p.lastRequest == "0123456789abcdef0123456789abcdef")
print("PASS: pause blocks every lane; resume admits only fresh presses")

let id = "0123456789abcdef0123456789abcdef"
func data(_ s: String) -> Data { Data(s.utf8) }
precondition(WandActionPauseRequest.parse(data(#"{"version":1,"paused":true,"id":"\#(id)"}"#)) == .init(paused: true, id: id))
precondition(WandActionPauseRequest.parse(data(#"{"version":1,"paused":false,"id":"\#(id)"}"#))?.paused == false)
for bad in [#"{"version":1,"paused":1,"id":"\#(id)"}"#, #"{"version":true,"paused":true,"id":"\#(id)"}"#,
            #"{"version":2,"paused":true,"id":"\#(id)"}"#, #"{"version":1.5,"paused":true,"id":"\#(id)"}"#, #"{"version":1,"paused":true,"id":"short"}"#,
            #"{"version":1,"paused":true,"id":"\#(id.uppercased())"}"#, #"{"version":1,"paused":true}"#,
            #"{"version":1,"paused":true,"id":"\#(id)","code":"print(1)"}"#, "[]", "not json",
            #"{"version":1,"paused":true,"id":"\#(id)","pad":"\#(String(repeating: "x", count: 300))"}"#] {
    precondition(WandActionPauseRequest.parse(data(bad)) == nil, "rejected: \(bad.prefix(60))")
}
print("PASS: request shape is exact; no code or extra fields")

let dir = FileManager.default.temporaryDirectory.appendingPathComponent("wand-pause-\(getpid())")
try! FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
defer { try? FileManager.default.removeItem(at: dir) }
let path = dir.appendingPathComponent(WandActionPauseRequest.fileName).path
func write(_ text: String, mode: mode_t) {
    unlink(path)
    let fd = open(path, O_WRONLY | O_CREAT | O_EXCL, mode); precondition(fd >= 0)
    _ = text.withCString { write(fd, $0, strlen($0)) }; close(fd); chmod(path, mode)
}
precondition(WandActionPauseRequest.take(at: path) == nil, "no file, no request")
write(#"{"version":1,"paused":true,"id":"\#(id)"}"#, mode: 0o600)
precondition(WandActionPauseRequest.take(at: path)?.paused == true && access(path, F_OK) != 0, "private request applied once and removed")
write(#"{"version":1,"paused":true,"id":"\#(id)"}"#, mode: 0o644)
precondition(WandActionPauseRequest.take(at: path) == nil && access(path, F_OK) != 0, "shared-permission request rejected and removed")
let target = dir.appendingPathComponent("elsewhere").path
FileManager.default.createFile(atPath: target, contents: data(#"{"version":1,"paused":true,"id":"\#(id)"}"#), attributes: [.posixPermissions: 0o600])
symlink(target, path)
precondition(WandActionPauseRequest.take(at: path) == nil && access(path, F_OK) != 0 && access(target, F_OK) == 0, "linked request rejected; target untouched")
print("PASS: only a private same-user request file is consumed")

let transport = WandControlTransport(agenticPath: dir.appendingPathComponent("absent-agentic.sock").path,
                                     speechPath: dir.appendingPathComponent("absent-speech.sock").path)
transport.suspended = true
precondition(!transport.speech(down: true) && !transport.speech(down: false) && !transport.screenshotStart(), "paused: no dictation or screenshot command is attempted")
transport.persistent("navigate"); transport.persistent("activate"); transport.persistent("exitReview"); transport.persistent("toggleReview")
precondition(!transport.beginHUD() && !transport.updateHUD(x: 1, y: 1))
precondition(transport.refused == 9, "every outward command refused: \(transport.refused)")
transport.persistent("dismiss"); transport.persistent("park"); transport.cancel()
precondition(transport.refused == 9, "closing the wand's own HUD is not refused; cancel never touches dictation")
transport.suspended = false
_ = transport.speech(down: true)
precondition(transport.refused == 9, "resumed transport sends again")
print("PASS: suspended transport refuses dictation and screenshot commands")
