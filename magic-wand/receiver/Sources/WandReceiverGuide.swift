import AppKit

/// The receiver's wand guide lifecycle; the panel and its rules are WandGuidePanel.swift.
extension WandReceiver {
    var guideRequestPath: String { support.appendingPathComponent(WandGuideRequest.fileName).path }

    /// Opens at launch only if left open, or if an agent asked while the
    /// receiver was not running.
    func startGuide() {
        let controller = WandGuideController(
            preference: support.appendingPathComponent("guide.json"), presenter: WandGuidePanelPresenter(),
            content: { [weak self] in
                guard let self, let url = Bundle.main.url(forResource: "wand-guide", withExtension: "json"),
                      let data = try? Data(contentsOf: url) else { return nil }
                return WandGuideContent.parse(data, sense: self.isSense)
            })
        controller.onChange = { [weak self] in self?.guideChanged() }
        guide = controller
        if let request = WandGuideRequest.take(at: guideRequestPath) { controller.apply(request) } else { controller.restore() }
        guideChanged()
    }

    func readGuideRequest() {
        guard let request = WandGuideRequest.take(at: guideRequestPath) else { return }
        guide?.apply(request); log("GUIDE_REQUEST", request.visible ? "show" : "hide")
    }

    func guideChanged() {
        guideMenuItem?.state = guide?.visible == true ? .on : .off
        status()
    }

    @objc func toggleGuide() { guide?.set(!(guide?.visible ?? false)) }
}
