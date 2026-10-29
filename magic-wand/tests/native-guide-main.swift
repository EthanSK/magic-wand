import AppKit
setbuf(stdout, nil)
// The instruction panel's logic without opening a window: generated content,
// Sense labels, placement, agent requests and the saved close choice.
let generated = URL(fileURLWithPath: CommandLine.arguments[1])
let data = try! Data(contentsOf: generated)
let sense = WandGuideContent.parse(data, sense: true)!, puck = WandGuideContent.parse(data, sense: false)!
let headings = sense.sections.map(\.heading)
precondition(headings[0] == "Button 1 · left · Agentic Mouse HUD (Middle)" && headings[1] == "Button 2 · centre · Mouse (Bottom)"
             && headings[2] == "Button 3 · right · Speech to text (Top)", "physical Sense buttons, not finger names: \(headings)")
precondition(puck.sections[0].heading == "Middle · Agentic Mouse HUD", "Puck keeps its own names")
let all = sense.sections.flatMap(\.rows).map { $0.joined(separator: " ") }.joined(separator: "\n")
for needle in ["submenu", "dotted mode", "click Middle to finish", "Triple tap", "screenshot", "Stage files", "dictation", "mouse follow", "flashes twice", "All three buttons", "Recording"] {
    precondition(all.lowercased().contains(needle.lowercased()), "the guide covers \(needle)")
}
precondition(!all.contains("hold Middle again"), "the superseded next-hold flow is gone")
print("PASS: generated content with Sense button positions")

// Top-right of the visible display, clear of the centred HUD and bottom-centre Agent Flow.
for visible in [CGRect(x: 0, y: 0, width: 1440, height: 875), CGRect(x: 0, y: 25, width: 1280, height: 775), CGRect(x: -1920, y: 0, width: 1920, height: 1055)] {
    let frame = WandGuidePlacement.frame(visible: visible, contentHeight: 2000)
    precondition(visible.contains(frame), "inside the display: \(frame) in \(visible)")
    precondition(frame.minX > visible.midX + visible.width * 0.12, "clear of the centred HUD: \(frame)")
    precondition(abs(frame.maxY - (visible.maxY - max(16, visible.height * 0.1))) < 0.01 && abs(frame.maxX - (visible.maxX - max(16, visible.width * 0.1))) < 0.01, "top right")
    let short = WandGuidePlacement.frame(visible: visible, contentHeight: 300)
    precondition(short.height == 300 && short.minY > visible.minY + visible.height * 0.5, "a short guide stays high, away from Agent Flow")
}
print("PASS: placement")

// Agent requests: strict shape only.
let id = String(repeating: "a", count: 32)
precondition(WandGuideRequest.parse(Data(#"{"version":1,"visible":true,"id":"\#(id)"}"#.utf8)) == .init(visible: true, id: id))
for bad in [#"{"version":1,"visible":1,"id":"\#(id)"}"#, #"{"version":2,"visible":true,"id":"\#(id)"}"#,
            #"{"version":1,"visible":true,"id":"short"}"#, #"{"version":1,"visible":true,"id":"\#(id)","x":1}"#] {
    precondition(WandGuideRequest.parse(Data(bad.utf8)) == nil, bad)
}
let folder = FileManager.default.temporaryDirectory.appendingPathComponent("wand-guide-\(getpid())")
try? FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
defer { try? FileManager.default.removeItem(at: folder) }
let requestPath = folder.appendingPathComponent(WandGuideRequest.fileName).path
FileManager.default.createFile(atPath: requestPath, contents: Data(#"{"version":1,"visible":true,"id":"\#(id)"}"#.utf8), attributes: [.posixPermissions: 0o644])
precondition(WandGuideRequest.take(at: requestPath) == nil && !FileManager.default.fileExists(atPath: requestPath), "a shared-permission request is refused and consumed")
FileManager.default.createFile(atPath: requestPath, contents: Data(#"{"version":1,"visible":false,"id":"\#(id)"}"#.utf8), attributes: [.posixPermissions: 0o600])
precondition(WandGuideRequest.take(at: requestPath)?.visible == false, "a private request is read once")
print("PASS: agent requests")

// Visibility: the close button is remembered; reconnecting or relaunching never reopens it.
final class Fake: WandGuidePresenting {
    var onUserClose: (() -> Void)?
    var shown = 0, dismissed = 0
    func present(_ content: WandGuideContent) { shown += 1 }
    func dismiss() { dismissed += 1 }
}
let preference = folder.appendingPathComponent("guide.json")
let fake = Fake(), controller = WandGuideController(preference: preference, presenter: fake, content: { sense })
controller.restore()
precondition(!controller.visible && fake.shown == 0, "never shown without a choice or a request")
controller.apply(.init(visible: true, id: id))
precondition(controller.visible && fake.shown == 1 && controller.lastRequest == id && controller.savedVisible, "an agent can show it")
fake.onUserClose?()
precondition(!controller.visible && !controller.savedVisible, "the close button hides it and is remembered")
let relaunch = Fake(), again = WandGuideController(preference: preference, presenter: relaunch, content: { sense })
again.restore()
precondition(relaunch.shown == 0, "after a manual close it does not reopen on launch or reconnect")
again.set(true)
let third = Fake(), reopened = WandGuideController(preference: preference, presenter: third, content: { sense })
reopened.restore()
precondition(third.shown == 1, "left open, it is back after a restart")
reopened.apply(.init(visible: false, id: id))
precondition(!reopened.visible && third.dismissed == 1 && !reopened.savedVisible, "an agent can hide it")
let empty = Fake(), missing = WandGuideController(preference: folder.appendingPathComponent("other.json"), presenter: empty, content: { nil })
missing.set(true)
precondition(!missing.visible && empty.shown == 0, "no content, no empty panel")
print("PASS: visibility and saved choice")
