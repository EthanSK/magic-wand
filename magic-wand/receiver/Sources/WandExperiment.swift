// Ethan's reusable bottom-left experiment label. Configuration is private and
// polled by the receiver's existing housekeeping tick, never by sensor input.
import AppKit

private final class WandExperimentPanel: NSPanel {
    override var canBecomeKey: Bool { false }
    override var canBecomeMain: Bool { false }
}

final class WandExperiment {
    let configurationURL: URL
    private var configuration: WandExperimentConfiguration?
    private var source: Data?
    private var connected = false, rateControl = false, rejected = false
    private var confirmedHz: Int?
    private var attempts = 0, sentAt = -Double.infinity
    private var counter = WandExperimentRateCounter()
    private var rates: WandExperimentRates?
    private var panel: NSPanel?
    private var title: NSTextField?, sensor: NSTextField?, delivery: NSTextField?
    private var screenID: NSNumber?

    init(url: URL) { configurationURL = url }

    func connection(hz: Double, supportsRateControl: Bool, now: Double) {
        connected = true; rateControl = supportsRateControl
        confirmedHz = hz.isFinite && hz >= 1 && hz <= 6660 ? Int(hz) : nil
        attempts = 0; rejected = false; sentAt = -.infinity
        counter.reset(now: now); rates = nil
    }
    func disconnected(now: Double) {
        connected = false; confirmedHz = nil; rateControl = false
        attempts = 0; rejected = false; sentAt = -.infinity
        counter.reset(now: now); rates = nil
    }
    func received(readings: Int) { counter.frame(readingCount: readings) }
    func postedPointerEvent() { counter.postedPointerEvent() }
    func reply(_ event: String) {
        guard connected, let value = WandExperimentRateReply.parse(event) else { return }
        confirmedHz = value.hz
        // Never claim a requested rate is active before firmware readback.
        rejected = !value.accepted
        if rejected { attempts = 3 }
    }

    func tick(now: Double, maySend: Bool, send: (String) -> Void) {
        // Bound the file read before allocation. Invalid edits retain the last
        // valid configuration; no settings or hardware state change on parse failure.
        if let attributes = try? FileManager.default.attributesOfItem(atPath: configurationURL.path),
           let size = attributes[.size] as? NSNumber, size.intValue <= 2048,
           let data = try? Data(contentsOf: configurationURL), data != source,
           let next = WandExperimentConfiguration.parse(data) {
            if configuration?.sensorHz != next.sensorHz { attempts = 0; rejected = false; sentAt = -.infinity }
            source = data; configuration = next
        }
        if let value = counter.measure(now: now) { rates = value }
        if connected, rateControl, maySend, let desired = configuration?.sensorHz,
           desired != confirmedHz, attempts < 3, now - sentAt >= 2 {
            // Presentation/configuration only. Existing BLE ownership sends the
            // one runtime command; there is no extra radio connection or input queue.
            send("R\(desired)"); attempts += 1; sentAt = now
        }
        render()
    }

    var status: [String: Any] {
        var value: [String: Any] = ["visible": configuration?.visible ?? false, "connected": connected,
                                   "rateControl": rateControl, "attempts": attempts, "rejected": rejected]
        if let configuration { value["label"] = configuration.label; value["requestedHz"] = configuration.sensorHz }
        if let confirmedHz { value["sensorHz"] = confirmedHz }
        if let rates { value["readingsPerSecond"] = rates.readings; value["reportsPerSecond"] = rates.frames; value["pointerEventsPerSecond"] = rates.pointerEvents }
        return value
    }

    func stop() { panel?.orderOut(nil) }

    private func render() {
        guard let configuration, configuration.visible else { panel?.orderOut(nil); return }
        let panel = panel ?? makePanel()
        self.panel = panel
        title?.stringValue = "Experiment · \(configuration.label)"
        if connected {
            var text = confirmedHz.map { "Sensor \(Self.number(Double($0))) Hz" } ?? "Sensor rate unavailable"
            if let desired = configuration.sensorHz, desired != confirmedHz {
                text += rejected ? " · Rate rejected" : !rateControl ? " · Firmware update needed" : attempts >= 3 ? " · Rate not confirmed" : " · Changing rate…"
            }
            sensor?.stringValue = text
            if let rates {
                delivery?.stringValue = "Readings \(Self.number(rates.readings))/s · Reports \(Self.number(rates.frames))/s · Pointer \(Self.number(rates.pointerEvents))/s"
            } else { delivery?.stringValue = "Measuring delivery…" }
        } else {
            sensor?.stringValue = "Wand disconnected"
            delivery?.stringValue = "Waiting for Bluetooth or USB"
        }
        place(panel)
        if !panel.isVisible { panel.orderFrontRegardless() }
    }

    private static func number(_ value: Double) -> String {
        String(format: "%.0f", value)
    }

    private func place(_ panel: NSPanel) {
        guard let primary = NSScreen.screens.first else { return }
        let key = NSDeviceDescriptionKey("NSScreenNumber")
        let selected: NSScreen
        if let existing = NSScreen.screens.first(where: { $0.deviceDescription[key] as? NSNumber == screenID }) {
            selected = existing
        } else {
            let p = CGEvent(source: nil)?.location ?? .zero
            let cocoa = CGPoint(x: p.x, y: primary.frame.maxY - p.y)
            selected = NSScreen.screens.first(where: { $0.frame.contains(cocoa) }) ?? NSScreen.main ?? primary
            screenID = selected.deviceDescription[key] as? NSNumber
        }
        let visible = selected.visibleFrame
        let width = min(570, max(1, visible.width - 32))
        let frame = CGRect(x: visible.minX + 16, y: visible.minY + 16, width: width, height: 105)
        if panel.frame != frame { panel.setFrame(frame, display: true) }
    }

    private func makePanel() -> NSPanel {
        let panel = WandExperimentPanel(contentRect: .zero, styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        panel.isOpaque = false; panel.backgroundColor = .clear; panel.hasShadow = true
        panel.hidesOnDeactivate = false; panel.ignoresMouseEvents = true
        panel.level = NSWindow.Level(rawValue: NSWindow.Level.floating.rawValue + 3)
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        panel.isReleasedWhenClosed = false
        let view = NSView(); view.wantsLayer = true
        view.layer?.backgroundColor = NSColor(calibratedWhite: 0.08, alpha: 0.94).cgColor
        view.layer?.cornerRadius = 16
        view.layer?.borderColor = NSColor.systemCyan.withAlphaComponent(0.6).cgColor
        view.layer?.borderWidth = 1
        func label(_ size: CGFloat, _ weight: NSFont.Weight, _ color: NSColor) -> NSTextField {
            let value = NSTextField(labelWithString: "")
            value.font = .monospacedDigitSystemFont(ofSize: size, weight: weight)
            value.textColor = color; value.maximumNumberOfLines = 1; value.lineBreakMode = .byTruncatingTail
            return value
        }
        let title = label(20, .semibold, .white)
        let sensor = label(16, .medium, .systemCyan)
        let delivery = label(15, .regular, .white.withAlphaComponent(0.85))
        let row = NSStackView(views: [title, sensor, delivery])
        row.orientation = .vertical; row.alignment = .leading; row.spacing = 5
        row.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(row)
        NSLayoutConstraint.activate([
            row.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 18),
            row.trailingAnchor.constraint(lessThanOrEqualTo: view.trailingAnchor, constant: -18),
            row.centerYAnchor.constraint(equalTo: view.centerYAnchor)
        ])
        self.title = title; self.sensor = sensor; self.delivery = delivery
        panel.contentView = view
        return panel
    }
}
