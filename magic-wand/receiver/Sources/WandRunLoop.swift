import Foundation

/// Timers that must keep running while AppKit tracks a menu.
///
/// Opening the receiver's menu-bar menu runs the main run loop in event-tracking
/// mode, where a `Timer.scheduledTimer` (default mode only) does not fire. The
/// Sense link's 0.1 s supervision sends the board's heartbeat; with it paused,
/// the firmware ended the session after its 2 s host timeout (orange light, no
/// readings) and the receiver reconnected when the menu closed (2026-10-29,
/// 15 s without input). Main-queue work, Bluetooth delegate callbacks and the
/// virtual Puck's dispatch timers already run in every common mode.
/// Keep recording refresh, stop-to-click, button safety and gesture deadlines
/// in the same modes too; a menu must not defer those actions until it closes.
enum WandRunLoop {
    static func commonTimer(interval: TimeInterval, repeats: Bool = true, _ block: @escaping (Timer) -> Void) -> Timer {
        let timer = Timer(timeInterval: interval, repeats: repeats, block: block)
        RunLoop.main.add(timer, forMode: .common)
        return timer
    }
}
