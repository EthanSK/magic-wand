import Foundation
import AppKit

// Observe recording without sending media/recording commands to Agent Flow.
final class WandRecordingState {
    typealias Session = () -> String?
    private let center: NotificationCenter
    private let cache: URL
    private let session: Session
    private var observers: [NSObjectProtocol] = []
    private var owner: String?
    private(set) var isRecording = false
    var onChange: ((Bool) -> Void)?
    static let started = "com.ethansk.voiceink.recordingStarted"
    static let stopped = ["com.ethansk.voiceink.recordingStopped", "com.ethansk.voiceink.recordingStoppedPreservingPlayback"]
    init(center: NotificationCenter = DistributedNotificationCenter.default(), cache: URL, session: @escaping Session = WandRecordingState.agentFlowSession) {
        self.center=center; self.cache=cache; self.session=session
    }
    static func agentFlowSession() -> String? {
        guard let app=NSWorkspace.shared.runningApplications.first(where: {
            $0.bundleURL?.standardizedFileURL.path == "/Applications/AgentFlow.app"
        }), let date=app.launchDate else {return nil}
        return "\(app.processIdentifier):\(date.timeIntervalSince1970)"
    }
    func start() {
        owner=session()
        if let data=try? Data(contentsOf:cache),
           let value=try? JSONSerialization.jsonObject(with:data) as? [String:Any],
           let savedOwner=value["session"] as? String, savedOwner == owner {
            isRecording=value["recording"] as? Bool ?? false
        }
        observers.append(center.addObserver(forName:Notification.Name(Self.started),object:nil,queue:.main){[weak self] _ in self?.receive(true)})
        for name in Self.stopped {
            observers.append(center.addObserver(forName:Notification.Name(name),object:nil,queue:.main){[weak self] _ in self?.receive(false)})
        }
        persist()
    }
    func refresh() {
        let current=session()
        guard current != owner else{return}
        owner=current; set(false)
    }
    private func receive(_ active: Bool) {
        owner=session()
        set(active && owner != nil)
    }
    private func set(_ active:Bool) {
        let changed=isRecording != active
        isRecording=active;persist()
        if changed {onChange?(active)}
    }
    private func persist() {
        let value:[String:Any] = ["session":owner ?? "", "recording":isRecording]
        if let data=try? JSONSerialization.data(withJSONObject:value) {try? data.write(to:cache,options:.atomic)}
    }
    deinit {for observer in observers {center.removeObserver(observer)}}
}
