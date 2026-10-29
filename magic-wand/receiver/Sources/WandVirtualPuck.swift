import Foundation
import JavaScriptCore

/// Ethan's Sense wand runs the canonical Puck program here ("virtual Puck"):
/// the unchanged base, mode bridge and power policy, in JavaScriptCore through
/// the website's Espruino shim and device/sense/wand-sense-host.js. The
/// receiver talks to it exactly as to a Puck: queue(JS) commands in, UART
/// lines out. One instance per Sense session; teardown cancels every timer.
final class WandVirtualPuck {
    struct Sources {
        let shim: String, host: String, base: String, bridge: String, power: String
        static func bundled(bridge: String) -> Sources? {
            func resource(_ name: String, _ ext: String) -> String? {
                Bundle.main.url(forResource: name, withExtension: ext).flatMap { try? String(contentsOf: $0, encoding: .utf8) }
            }
            guard let shim = resource("wand-espruino", "js"), let host = resource("wand-sense-host", "js"),
                  let base = resource("wand-base", "js"), let power = resource("wand-power-policy", "js"), !bridge.isEmpty else { return nil }
            return .init(shim: shim, host: host, base: base, bridge: bridge, power: power)
        }
    }
    /// Batched UART text: every line produced in one main-queue turn arrives in
    /// one chunk, like one BLE notification batch (one shared delivery point).
    var onText: ((String) -> Void)?
    var onLight: ((Double, Double, Double) -> Void)?
    var onSensor: ((Int) -> Void)?
    var onSleep: (() -> Void)?
    var onLog: ((String) -> Void)?
    private let context: JSContext
    private var api: JSValue?
    private var timers: [Int: DispatchSourceTimer] = [:]
    private var pending = "", flushScheduled = false, dead = false
    private let clock: () -> Double

    init?(sources: Sources, clock: @escaping () -> Double = { ProcessInfo.processInfo.systemUptime }) {
        guard let context = JSContext() else { return nil }
        self.context = context; self.clock = clock
        context.name = "Magic Wand Sense"
        context.exceptionHandler = { [weak self] _, exception in self?.onLog?("JS_EXCEPTION " + (exception?.toString() ?? "?")) }
        let native = JSValue(newObjectIn: context)!
        let now: @convention(block) () -> Double = { [weak self] in self?.clock() ?? 0 }
        let schedule: @convention(block) (Int, Double, Bool) -> Void = { [weak self] id, ms, repeating in self?.schedule(id, ms: ms, repeating: repeating) }
        let cancel: @convention(block) (Int) -> Void = { [weak self] id in self?.timers.removeValue(forKey: id)?.cancel() }
        let text: @convention(block) (String) -> Void = { [weak self] line in self?.emit(line) }
        let light: @convention(block) (Double, Double, Double) -> Void = { [weak self] r, g, b in self?.onLight?(r, g, b) }
        let sensor: @convention(block) (Int) -> Void = { [weak self] mode in self?.onSensor?(mode) }
        let sleep: @convention(block) () -> Void = { [weak self] in self?.onSleep?() }
        let logger: @convention(block) (String) -> Void = { [weak self] line in self?.onLog?(line) }
        for (name, block) in [("now", now as Any), ("schedule", schedule), ("cancel", cancel), ("text", text),
                              ("light", light), ("imu", sensor), ("sleep", sleep), ("log", logger)] {
            native.setObject(block, forKeyedSubscript: name as NSString)
        }
        context.setObject(native, forKeyedSubscript: "__wandNative" as NSString)
        context.evaluateScript(sources.shim, withSourceURL: URL(string: "wand://docs/sim/espruino.js"))
        context.evaluateScript(sources.host, withSourceURL: URL(string: "wand://device/sense/wand-sense-host.js"))
        guard let api = context.evaluateScript("WandSenseHost.create(globalThis, __wandNative)"), api.isObject else { return nil }
        self.api = api
    }

    /// The Puck's saved boot, on the Mac. Returns false if any part failed:
    /// the receiver's handshake then reports the bridge as not ready.
    func boot(_ s: Sources, zero: String?, runtime: String, revision: String, pointerGain: Double = 1) -> Bool {
        guard let api, !dead else { return false }
        let options: [String: Any] = ["pointerGain": pointerGain]
        let result = api.invokeMethod("boot", withArguments: [s.base, s.bridge, s.power, zero ?? "", runtime, revision, options])
        return result?.toBool() ?? false
    }

    /// One receiver queue() command, with Espruino console semantics.
    func send(_ command: String) { guard !dead else { return }; api?.invokeMethod("repl", withArguments: [command]) }

    /// Reapply mounting and pointer-only gain after loading a fresh bridge.
    /// Debug pause: keep the board streaming 104 Hz gyro and accelerometer for
    /// the dashboard. The canonical program still sees only its own requested rate.
    func holdSensor(_ on: Bool) {
        guard !dead else { return }
        api?.invokeMethod("holdSensor", withArguments: [on])
    }
    func configurePointer(_ gain: Double) {
        guard !dead else { return }
        api?.invokeMethod("configurePointer", withArguments: [gain])
    }

    /// Apply one Sense frame at its device-aligned time. Values are already
    /// in Puck units and the Puck body frame.
    func deliver(time: Double, mask: Int, accel: [Int]?, gyro: [Int]?) {
        guard !dead else { return }
        api?.invokeMethod("deliver", withArguments: [time, mask, accel.map { $0 as Any } ?? NSNull(), gyro.map { $0 as Any } ?? NSNull()])
    }

    func battery(volts: Double?, percent: Int?) {
        api?.invokeMethod("battery", withArguments: [volts.map { $0 as Any } ?? NSNull(), percent.map { $0 as Any } ?? NSNull()])
    }

    func evaluate(_ expression: String) -> JSValue? { dead ? nil : context.evaluateScript(expression) }

    func teardown() {
        guard !dead else { return }
        dead = true; pending = ""
        api?.invokeMethod("teardown", withArguments: [])
        for timer in timers.values { timer.cancel() }
        timers.removeAll(); api = nil
    }
    deinit { teardown() }

    private func schedule(_ id: Int, ms: Double, repeating: Bool) {
        guard !dead else { return }
        timers.removeValue(forKey: id)?.cancel()
        let timer = DispatchSource.makeTimerSource(queue: .main)
        let interval = max(0.001, ms / 1000)
        timer.schedule(deadline: .now() + (repeating ? interval : max(0, ms / 1000)),
                       repeating: repeating ? .milliseconds(Int(interval * 1000)) : .never, leeway: .milliseconds(1))
        timer.setEventHandler { [weak self] in
            guard let self, !self.dead else { return }
            if !repeating { self.timers.removeValue(forKey: id) }
            self.api?.invokeMethod("fire", withArguments: [id])
        }
        timers[id] = timer
        timer.resume()
    }

    private func emit(_ line: String) {
        guard !dead else { return }
        pending += line + "\n"
        guard !flushScheduled else { return }
        flushScheduled = true
        DispatchQueue.main.async { [weak self] in
            guard let self else { return }
            self.flushScheduled = false
            guard !self.dead, !self.pending.isEmpty else { self.pending = ""; return }
            let text = self.pending; self.pending = ""
            self.onText?(text)
        }
    }
}
