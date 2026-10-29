import AppKit
import Darwin

// Ethan: "have a HUD that's always showing that gives away all the instructions for
// how to do everything ... Have it somewhere where the other HUDs don't interfere ...
// I should be able to close it with the close button ... And the agent can turn it
// on and off." Agentic Mouse never dismisses it.
//
// The text is device/generated/wand-guide.json, generated from wand.json by
// scripts/guide_build.py; nothing here is a second copy of the instructions.

/// The panel's content for one wand profile.
struct WandGuideContent: Equatable {
    struct Section: Equatable { let heading: String; let rows: [[String]] }
    let title: String
    let sections: [Section]

    /// `sense`: label the buttons by their position on the Sense grip
    /// (Button 1 left, 2 centre, 3 right) rather than the Puck's names.
    static func parse(_ data: Data, sense: Bool) -> WandGuideContent? {
        guard let value = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
              value["schemaVersion"] as? Int == 1, let title = value["title"] as? String,
              let buttons = value["sections"] as? [[String: Any]], let power = value["power"] as? [[String]],
              let lights = value["lights"] as? [[String: Any]] else { return nil }
        var sections: [Section] = []
        for button in buttons {
            guard let role = button["role"] as? String, let puck = button["puckLabel"] as? String,
                  let senseLabel = button["senseLabel"] as? String, let rows = button["rows"] as? [[String]],
                  rows.allSatisfy({ $0.count == 2 }) else { return nil }
            // The gesture text names the Puck buttons; keep that name beside the Sense position.
            sections.append(.init(heading: sense ? "\(senseLabel) · \(role) (\(puck))" : "\(puck) · \(role)", rows: rows))
        }
        guard power.allSatisfy({ $0.count == 2 }) else { return nil }
        sections.append(.init(heading: "Power", rows: power))
        let lightRows = lights.compactMap { light -> [String]? in
            guard let name = light["name"] as? String, let detail = light["detail"] as? String else { return nil }
            return [name, detail]
        }
        guard lightRows.count == lights.count else { return nil }
        sections.append(.init(heading: "Light", rows: lightRows))
        return .init(title: title, sections: sections)
    }
}

/// Where the panel goes: the top-right of the built-in display's visible area,
/// below the menu bar. That keeps it clear of Agent Flow's bottom-centre
/// indicator and Agentic Mouse's centred radial HUD.
enum WandGuidePlacement {
    static let width: CGFloat = 340, margin: CGFloat = 16

    static func frame(visible: CGRect, contentHeight: CGFloat) -> CGRect {
        let safe = visible.insetBy(dx: max(margin, visible.width * 0.1), dy: max(margin, visible.height * 0.1))
        let width = min(Self.width, max(160, safe.width / 3))
        let height = min(safe.height, max(120, contentHeight))
        return CGRect(x: safe.maxX - width, y: safe.maxY - height, width: width, height: height)
    }
}

/// An agent's show/hide request: a private, same-user file in the receiver's
/// support folder, the same mechanism as the dashboard's debug pause.
/// `{"version":1,"visible":true,"id":"<32 lowercase hex>"}`, written atomically.
struct WandGuideRequest: Equatable {
    static let fileName = "guide.request"
    let visible: Bool
    let id: String

    static func parse(_ data: Data) -> WandGuideRequest? {
        guard data.count <= 256, let value = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
              value.count == 3, let version = value["version"] as? NSNumber, !isBoolean(version), version == 1,
              let visible = value["visible"] as? NSNumber, isBoolean(visible),
              let id = value["id"] as? String, id.count == 32, id.allSatisfy({ $0.isHexDigit && !$0.isUppercase }) else { return nil }
        return .init(visible: visible.boolValue, id: id)
    }

    /// Read and remove one pending request. Links, shared permissions and
    /// oversized files are refused; any file found is consumed.
    static func take(at path: String) -> WandGuideRequest? {
        let fd = open(path, O_RDONLY | O_NOFOLLOW | O_NONBLOCK)
        guard fd >= 0 else { if errno == ELOOP { unlink(path) }; return nil }
        defer { close(fd) }
        unlink(path)
        var info = stat()
        guard fstat(fd, &info) == 0, info.st_uid == geteuid(), info.st_mode & S_IFMT == S_IFREG,
              info.st_mode & 0o077 == 0, info.st_size > 0, info.st_size <= 256 else { return nil }
        var bytes = [UInt8](repeating: 0, count: Int(info.st_size))
        guard read(fd, &bytes, bytes.count) == bytes.count else { return nil }
        return parse(Data(bytes))
    }

    private static func isBoolean(_ number: NSNumber) -> Bool { CFGetTypeID(number) == CFBooleanGetTypeID() }
}

protocol WandGuidePresenting: AnyObject {
    var onUserClose: (() -> Void)? { get set }
    func present(_ content: WandGuideContent)
    func dismiss()
}

/// Visibility and its saved choice. It opens at launch only if it was left
/// open; reconnecting never reopens it after Ethan closed it. The menu and an
/// agent's request show or hide it; its own close button hides it.
final class WandGuideController {
    private let preference: URL
    private let presenter: WandGuidePresenting
    private let content: () -> WandGuideContent?
    private(set) var visible = false
    private(set) var lastRequest: String?
    var onChange: (() -> Void)?

    init(preference: URL, presenter: WandGuidePresenting, content: @escaping () -> WandGuideContent?) {
        self.preference = preference; self.presenter = presenter; self.content = content
        presenter.onUserClose = { [weak self] in self?.closed() }
    }

    var savedVisible: Bool {
        guard let data = try? Data(contentsOf: preference),
              let value = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
              value["schemaVersion"] as? Int == 1 else { return false }
        return value["visible"] as? Bool ?? false
    }

    func restore() { if savedVisible { set(true, save: false) } }

    func apply(_ request: WandGuideRequest) { lastRequest = request.id; set(request.visible) }

    func set(_ show: Bool, save: Bool = true) {
        if show, let content = content() { presenter.present(content); visible = true }
        else if !show { presenter.dismiss(); visible = false }
        if save { remember(visible) }
        onChange?()
    }

    private func closed() { visible = false; remember(false); onChange?() }

    private func remember(_ show: Bool) {
        guard let data = try? JSONSerialization.data(withJSONObject: ["schemaVersion": 1, "visible": show], options: [.sortedKeys]) else { return }
        try? data.write(to: preference, options: .atomic)
        try? FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: preference.path)
    }
}

/// Plain readable text: a bold heading per button, then each gesture and what it does.
enum WandGuideText {
    static func attributed(_ content: WandGuideContent) -> NSAttributedString {
        let text = NSMutableAttributedString()
        let heading: [NSAttributedString.Key: Any] = [.font: NSFont.systemFont(ofSize: 13, weight: .semibold), .foregroundColor: NSColor.labelColor]
        let gesture: [NSAttributedString.Key: Any] = [.font: NSFont.systemFont(ofSize: 12, weight: .medium), .foregroundColor: NSColor.labelColor]
        let detail: [NSAttributedString.Key: Any] = [.font: NSFont.systemFont(ofSize: 12), .foregroundColor: NSColor.secondaryLabelColor]
        for (index, section) in content.sections.enumerated() {
            text.append(NSAttributedString(string: (index == 0 ? "" : "\n") + section.heading + "\n", attributes: heading))
            for row in section.rows {
                text.append(NSAttributedString(string: row[0], attributes: gesture))
                text.append(NSAttributedString(string: " — " + row[1] + "\n", attributes: detail))
            }
        }
        let paragraph = NSMutableParagraphStyle(); paragraph.paragraphSpacing = 3; paragraph.lineBreakMode = .byWordWrapping
        text.addAttribute(.paragraphStyle, value: paragraph, range: NSRange(location: 0, length: text.length))
        return text
    }
}

/// A non-activating floating panel: it never takes focus from the app in use,
/// stays above ordinary windows on every Space, and closes only with its own
/// close button, the menu or an agent's request.
final class WandGuidePanelPresenter: NSObject, WandGuidePresenting, NSWindowDelegate {
    var onUserClose: (() -> Void)?
    private var panel: NSPanel?
    private var closingProgrammatically = false

    func present(_ content: WandGuideContent) {
        let panel = self.panel ?? makePanel()
        self.panel = panel
        panel.title = content.title
        guard let scroll = panel.contentView as? NSScrollView, let view = scroll.documentView as? NSTextView,
              let screen = NSScreen.screens.first(where: { $0.localizedName == "Built-in Retina Display" }) ?? NSScreen.screens.first else { return }
        let width = WandGuidePlacement.frame(visible: screen.visibleFrame, contentHeight: 0).width
        view.frame = NSRect(x: 0, y: 0, width: width, height: 10)
        view.textStorage?.setAttributedString(WandGuideText.attributed(content))
        view.layoutManager?.ensureLayout(for: view.textContainer!)
        let used = view.layoutManager?.usedRect(for: view.textContainer!).height ?? 400
        let chrome = panel.frameRect(forContentRect: .zero).height
        let frame = WandGuidePlacement.frame(visible: screen.visibleFrame, contentHeight: used + 2 * view.textContainerInset.height + chrome)
        panel.setFrame(frame, display: true)
        panel.orderFrontRegardless()
    }

    func dismiss() {
        guard let panel, panel.isVisible else { return }
        closingProgrammatically = true; panel.close(); closingProgrammatically = false
    }

    func windowWillClose(_ notification: Notification) {
        if !closingProgrammatically { onUserClose?() }
    }

    private func makePanel() -> NSPanel {
        let panel = NSPanel(contentRect: NSRect(x: 0, y: 0, width: WandGuidePlacement.width, height: 400),
                            styleMask: [.titled, .closable, .utilityWindow, .nonactivatingPanel], backing: .buffered, defer: true)
        panel.isFloatingPanel = true; panel.level = .floating; panel.hidesOnDeactivate = false
        panel.becomesKeyOnlyIfNeeded = true; panel.isReleasedWhenClosed = false
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        panel.delegate = self
        let scroll = NSScrollView(); scroll.hasVerticalScroller = true; scroll.drawsBackground = false
        let view = NSTextView(); view.isEditable = false; view.isSelectable = true; view.drawsBackground = false
        view.textContainerInset = NSSize(width: 10, height: 10); view.isVerticallyResizable = true
        view.textContainer?.widthTracksTextView = true; view.autoresizingMask = [.width]
        scroll.documentView = view; panel.contentView = scroll
        return panel
    }
}
