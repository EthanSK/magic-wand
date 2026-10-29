import AppKit // RunLoop.Mode.eventTracking: the mode AppKit uses while a menu is open
setbuf(stdout, nil)
// As in the receiver: NSApplication adds event tracking to the common modes.
_ = NSApplication.shared.setActivationPolicy(.prohibited)
// AppKit tracks an open menu-bar menu in the event-tracking run-loop mode.
// Reproduce that mode without a window: the Sense heartbeat must keep running.
var plain = 0, common = 0, queued = 0, oneShot = 0
let defaultTimer = Timer.scheduledTimer(withTimeInterval: 0.02, repeats: true) { _ in plain += 1 }
let commonTimer = WandRunLoop.commonTimer(interval: 0.02) { _ in common += 1 }
let deadline = WandRunLoop.commonTimer(interval: 0.04, repeats: false) { _ in oneShot += 1 }
DispatchQueue.main.async { queued += 1 }
let end = Date().addingTimeInterval(0.3)
while Date() < end { _ = RunLoop.main.run(mode: .eventTracking, before: end) }
precondition(plain == 0, "a default-mode Timer stops while a menu is tracked (the incident): \(plain)")
precondition(common >= 8, "the common-mode heartbeat keeps running while a menu is open: \(common)")
precondition(queued == 1, "main-queue work (Bluetooth callbacks, the virtual Puck's timers) still runs")
precondition(oneShot == 1 && !deadline.isValid, "a click/hold deadline fires exactly once while a menu is tracked")
let before = common
RunLoop.main.run(until: Date().addingTimeInterval(0.1))
precondition(common > before && plain > 0, "both run normally outside menu tracking")
precondition(oneShot == 1, "closing the menu never replays a completed click/hold deadline")
defaultTimer.invalidate(); commonTimer.invalidate()
print("PASS: Sense heartbeat survives menu tracking")
