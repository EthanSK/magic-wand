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
    private var toggle: NSButton?
    var onChange: (() -> Void)?
    var manualClick: Bool { configuration?.manualClick ?? false }
    private var appliedManualClick = false, manualClickSupported = false
    private var manualClickUnavailableReason = "Use Control V2 or V3 for Tap to click"
    func setManualClickSupport(_ supported: Bool, reason: String) {
        guard manualClickSupported != supported || manualClickUnavailableReason != reason else { return }
        manualClickSupported = supported; manualClickUnavailableReason = reason; render()
    }
    func setAppliedManualClick(_ enabled: Bool) {
        guard appliedManualClick != enabled else { return }
        appliedManualClick = enabled; render()
    }

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
            source = data; configuration = next; onChange?()
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
                                   "rateControl": rateControl, "attempts": attempts, "rejected": rejected,
                                   "inputPath": "macOS events", "virtualMouse": "Not available in this build"]
        if let configuration { value["label"] = configuration.label; value["requestedHz"] = configuration.sensorHz; value["manualClickSupported"] = manualClickSupported; value["manualClickUnavailableReason"] = manualClickUnavailableReason; value["manualClickDesired"] = configuration.manualClick; value["manualClickApplied"] = appliedManualClick; value["manualClick"] = appliedManualClick }
        if let confirmedHz { value["sensorHz"] = confirmedHz }
        if let rates { value["readingsPerSecond"] = rates.readings; value["reportsPerSecond"] = rates.frames; value["pointerEventsPerSecond"] = rates.pointerEvents }
        return value
    }

    func stop() { panel?.orderOut(nil) }

    // Keep the runtime checkbox and agent edits on the same canonical file.
    // Preserve the settled416Hz request; switching click mode never retunes it.
    @objc private func toggleManualClick(_ sender: NSButton) {
        guard let current = configuration else { return }
        let enabled = sender.state == .on
        var value: [String: Any] = ["version": 1, "visible": current.visible,
                                   "label": current.label, "manualClick": enabled]
        if let hz = current.sensorHz { value["sensorHz"] = hz }
        do {
            let data = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
            try data.write(to: configurationURL, options: .atomic)
            try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: configurationURL.path)
            source = data
            configuration = .init(visible: current.visible, label: current.label,
                                  sensorHz: current.sensorHz, manualClick: enabled)
            onChange?()
        } catch { sender.state = current.manualClick ? .on : .off }
        render()
    }

    private func render() {
        guard let configuration, configuration.visible else { panel?.orderOut(nil); return }
        let panel = panel ?? makePanel()
        self.panel = panel
        title?.stringValue = "Experiment · Tap to click"
        toggle?.state = configuration.manualClick ? .on : .off
        if connected && configuration.manualClick && !manualClickSupported {
            sensor?.stringValue = manualClickUnavailableReason
            delivery?.stringValue = "Automatic clicks on"
        } else if connected && configuration.manualClick != appliedManualClick {
            sensor?.stringValue = "Release mouse button to change mode"
            delivery?.stringValue = appliedManualClick ? "Automatic clicks off" : "Automatic clicks on"
        } else if connected {
            sensor?.stringValue = appliedManualClick
                ? "Tap mouse button to click · Hold mouse button without scrolling to stop following"
                : "Automatic clicks on"
            delivery?.stringValue = appliedManualClick
                ? "Pointer off: tap to follow · Automatic clicks off"
                : "Tap mouse button to stop following"
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
        let frame = CGRect(x: visible.minX + 16, y: visible.minY + 16, width: width, height: 184)
        if panel.frame != frame { panel.setFrame(frame, display: true) }
    }

    private func makePanel() -> NSPanel {
        let panel = WandExperimentPanel(contentRect: .zero, styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        panel.isOpaque = false; panel.backgroundColor = .clear; panel.hasShadow = true
        panel.hidesOnDeactivate = false; panel.ignoresMouseEvents = false
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
        sensor.maximumNumberOfLines = 2; sensor.lineBreakMode = .byWordWrapping
        sensor.preferredMaxLayoutWidth = 534
        let delivery = label(15, .regular, .white.withAlphaComponent(0.85))
        let toggle = NSButton(checkboxWithTitle: "Enable experiment", target: self, action: #selector(toggleManualClick(_:)))
        toggle.font = .systemFont(ofSize: 17)
        toggle.attributedTitle = NSAttributedString(string: "Enable experiment", attributes: [.font: NSFont.systemFont(ofSize: 17), .foregroundColor: NSColor.white])
        toggle.state = configuration?.manualClick == true ? .on : .off
        toggle.contentTintColor = .white
        self.toggle = toggle
        // The current build posts CGEvents. CoreHID is not a selectable backend
        // here; keep that limitation visible without inventing an active path.
        let inputStatus = label(13, .regular, .secondaryLabelColor)
        inputStatus.stringValue = "Input: macOS events · Virtual mouse: Not available in this build"
        let row = NSStackView(views: [title, toggle, sensor, delivery, inputStatus])
        row.orientation = .vertical; row.alignment = .leading; row.spacing = 5
        row.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(row)
        NSLayoutConstraint.activate([
            row.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 18),
            row.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -18),
            row.centerYAnchor.constraint(equalTo: view.centerYAnchor)
        ])
        self.title = title; self.sensor = sensor; self.delivery = delivery
        panel.contentView = view
        return panel
    }
}
