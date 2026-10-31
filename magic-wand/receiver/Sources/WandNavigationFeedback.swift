// Displays the receiver's brief Back/Forward acknowledgement, independently of
// the destination app. It confirms a completed gesture, not that navigation loaded.
import AppKit

enum WandNavigationDirection: Equatable {
    case back, forward

    init?(horizontalDelta: Int64) {
        guard horizontalDelta != 0 else { return nil }
        // Native positive horizontal scroll drags content right: Back.
        self = horizontalDelta > 0 ? .back : .forward
    }

    var title: String { self == .back ? "← Back gesture" : "Forward gesture →" }
}

enum WandNavigationPulse {
    static let duration: TimeInterval = 0.85

    static func opacity(at elapsed: TimeInterval) -> CGFloat {
        guard elapsed >= 0, elapsed < duration else { return 0 }
        if elapsed < 0.08 { return CGFloat(elapsed / 0.08) }
        if elapsed < 0.45 { return 1 }
        let progress = (elapsed - 0.45) / (duration - 0.45)
        return CGFloat((1 - progress) * (1 - progress))
    }

    static func frame(in visible: CGRect) -> CGRect {
        let width = min(320, max(1, visible.width - 32))
        return CGRect(x: visible.midX - width / 2, y: visible.minY + 16,
                      width: width, height: 60)
    }
}

private final class WandNavigationPanel: NSPanel {
    override var canBecomeKey: Bool { false }
    override var canBecomeMain: Bool { false }
}

/// Same large, single-line cyan capsule as the wand's transient status messages.
/// It never activates an app or intercepts the pointer. A new gesture replaces
/// and re-pulses this one panel; there is no stale queue of acknowledgements.
final class WandNavigationFeedback {
    private var panel: NSPanel?
    private var label: NSTextField?
    private var timer: Timer?
    private var started: TimeInterval = 0
    private(set) var direction: WandNavigationDirection?

    func show(_ direction: WandNavigationDirection, at screenPoint: CGPoint) {
        guard let primary = NSScreen.screens.first else { return }
        let cocoaPoint = CGPoint(x: screenPoint.x, y: primary.frame.maxY - screenPoint.y)
        let screen = NSScreen.screens.first { $0.frame.contains(cocoaPoint) } ?? NSScreen.main ?? primary
        let panel = self.panel ?? makePanel()
        self.panel = panel
        self.direction = direction
        label?.stringValue = direction.title
        panel.setFrame(WandNavigationPulse.frame(in: screen.visibleFrame), display: true)
        timer?.invalidate()
        started = ProcessInfo.processInfo.systemUptime
        panel.alphaValue = 0
        panel.orderFrontRegardless()
        // The fade changes presentation only. It never holds a gesture or pointer
        // event, and common run-loop modes keep it running during menu tracking.
        let timer = Timer(timeInterval: 1.0 / 60.0, repeats: true) { [weak self] _ in
            self?.animate()
        }
        self.timer = timer
        RunLoop.main.add(timer, forMode: .common)
    }

    func dismiss() {
        timer?.invalidate(); timer = nil
        panel?.orderOut(nil)
        direction = nil
    }

    private func animate() {
        let elapsed = ProcessInfo.processInfo.systemUptime - started
        if elapsed >= WandNavigationPulse.duration { dismiss(); return }
        panel?.alphaValue = WandNavigationPulse.opacity(at: elapsed)
    }

    private func makePanel() -> NSPanel {
        let panel = WandNavigationPanel(contentRect: .zero, styleMask: [.borderless, .nonactivatingPanel],
                            backing: .buffered, defer: false)
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.hasShadow = true
        panel.hidesOnDeactivate = false
        panel.ignoresMouseEvents = true
        panel.level = NSWindow.Level(rawValue: NSWindow.Level.floating.rawValue + 3)
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        panel.isReleasedWhenClosed = false
        let view = NSView()
        view.wantsLayer = true
        view.layer?.backgroundColor = NSColor(calibratedRed: 0, green: 205.0 / 255, blue: 1, alpha: 1).cgColor
        view.layer?.cornerRadius = 30
        view.layer?.borderWidth = 1
        view.layer?.borderColor = NSColor.white.withAlphaComponent(0.28).cgColor
        let label = NSTextField(labelWithString: "")
        let font = NSFont.systemFont(ofSize: 22, weight: .semibold)
        label.font = font.fontDescriptor.withDesign(.rounded).flatMap { NSFont(descriptor: $0, size: 22) } ?? font
        label.textColor = .black
        label.alignment = .center
        label.lineBreakMode = .byClipping
        label.maximumNumberOfLines = 1
        label.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(label)
        NSLayoutConstraint.activate([
            label.centerYAnchor.constraint(equalTo: view.centerYAnchor),
            label.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 20),
            label.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20)
        ])
        panel.contentView = view
        self.label = label
        return panel
    }

    deinit { timer?.invalidate() }
}
