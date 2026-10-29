import Foundation
import Darwin

/// Sense wand session lifecycle. The link owns USB/Bluetooth; the virtual Puck
/// runs the canonical program; every gesture, HUD, speech, scrolling, dwell,
/// rest and sleep decision stays in the existing receiver and Puck code.
extension WandReceiver {
    var senseSelectionURL: URL { support.appendingPathComponent("sense-device.json") }

    func rememberedSenseID() -> String? {
        guard let data = try? Data(contentsOf: senseSelectionURL),
              let value = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
              let id = value["id"] as? String, id.count == 16, id.allSatisfy({ $0.isHexDigit }) else { return nil }
        return id.lowercased()
    }

    /// The first Sense paired over USB becomes the explicitly selected board.
    func rememberSenseID(_ id: String) {
        guard let data = try? JSONSerialization.data(withJSONObject: ["schemaVersion": 1, "id": id]) else { return }
        do {
            try data.write(to: senseSelectionURL, options: .atomic)
            try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: senseSelectionURL.path)
            log("SENSE_SELECTED_OVER_USB")
        } catch { log("SENSE_SELECTION_SAVE_FAILED", error.localizedDescription) }
    }

    func startSense() {
        if senseLink == nil {
            let link = WandSenseLink()
            link.pinnedID = deviceSettings.senseID ?? rememberedSenseID()
            link.onPin = { [weak self] id in self?.rememberSenseID(id) }
            link.onLog = { log($0) }
            link.onReady = { [weak self] info, transport in self?.senseReady(info, transport) }
            link.onLost = { [weak self] transport, reason in log("SENSE_DISCONNECTED", transport.rawValue, reason); self?.endSenseSession() }
            link.onLine = { [weak self] line, arrival in self?.senseLine(line, arrival) }
            senseLink = link
        }
        senseLink?.start()
    }

    func senseReady(_ info: WandSenseInfo, _ transport: WandSenseLink.Transport) {
        endSenseSession()
        guard let sources = WandVirtualPuck.Sources.bundled(bridge: modeBridge), let virtual = WandVirtualPuck(sources: sources) else {
            // Do not fake a working wand: without the canonical program nothing is ready.
            log("SENSE_PROGRAM_UNAVAILABLE"); senseLink?.drop("program unavailable"); return
        }
        senseSessionNumber += 1
        senseInfo = info; senseTransport = transport; senseSession.reset(); senseClock.reset(); senseLastReading = -.infinity
        restDetection = WandRestDetection(cache: support.appendingPathComponent("desk-reference-sense-\(info.id).json"))
        virtual.onText = { [weak self, weak virtual] text in
            guard let self, let virtual, self.senseVirtual === virtual else { return }
            self.receiveText(text)
        }
        virtual.onLight = { [weak self] r, g, b in self?.senseLink?.send(WandSenseCommand.light(WandSenseLight.rgb(r, g, b))) }
        virtual.onSensor = { [weak self] mode in self?.senseLink?.send(WandSenseCommand.sensor(mode)) }
        virtual.onSleep = { [weak self] in self?.senseLink?.send(WandSenseCommand.sleep); log("SENSE_STANDBY_REQUESTED") }
        virtual.onLog = { log("SENSE_PROGRAM", $0) }
        senseVirtual = virtual
        let zero = knownSenseZero()?.json
        let booted = virtual.boot(sources, zero: zero, runtime: runtimeVersion, revision: bridgeRevision(sources.bridge),
                                  pointerGain: deviceSettings.sensePointerGain)
        if actionPause.paused { virtual.holdSensor(true) } // Debug pause keeps full-rate telemetry.
        log("SENSE_CONNECTED", transport.rawValue, info.firmware, "program", booted ? "complete" : "FAILED", "knownZero", zero != nil,
            "pointerGain", deviceSettings.sensePointerGain)
        if !info.motion { log("SENSE_MOTION_SENSOR_UNAVAILABLE") }
        senseDashboard.status(["type": "status", "state": "live", "transport": transport.rawValue, "session": senseSessionNumber])
        loadingRuntime = false; bridgeLoadFailed = false; deadline(seconds: 60); status()
        startRuntimeHandshake()
    }

    /// This board's saved zero. A zero saved by the 2026-10-29a–c builds (134 per
    /// deg/s, key without "-c875") is converted once, never re-learned or shared.
    func knownSenseZero() -> WandCalibration? {
        guard let key = calibrationKey else { return nil }
        if let zero = WandCalibrationStore.read(calibrationURL(for: key), device: key) { return zero }
        let legacy = String(key.dropLast("-c875".count))
        guard key.hasSuffix("-c875"), let old = WandCalibrationStore.read(calibrationURL(for: legacy), device: legacy) else { return nil }
        let zero = WandSenseUnits.migrateLegacyZero(old)
        guard zero.valid else { return nil }
        // The restore prints WAND_CALIBRATED, which saves it under the new key.
        log("KNOWN_CALIBRATION_MIGRATED"); return zero
    }

    /// Lost link, transport switch or deadline: release every native button and
    /// pending lane through the existing reset, then discard the program and
    /// its timers. Nothing from this session is replayed into the next.
    func endSenseSession() {
        guard senseVirtual != nil || senseTransport != nil else { return }
        reset()
        senseVirtual?.teardown(); senseVirtual = nil
        senseInfo = nil; senseTransport = nil; senseSession.reset(); senseClock.reset()
        senseDashboard.status(["type": "status", "state": "searching", "session": senseSessionNumber])
        status()
    }

    func senseLine(_ line: WandSenseLine, _ arrival: Double) {
        guard let virtual = senseVirtual, let info = senseInfo else { return }
        switch line {
        case .frame(let frame):
            senseDashboard.packet(["type": "packet", "transport": senseTransport?.rawValue ?? "", "session": senseSessionNumber,
                                   "packet": WandSenseDashboard.packet(frame, info: info),
                                   "usage": ["pointerPosts":movementCount,"pointerTravel":pointerTravel,
                                             "follow":dwell.following,"paused":actionPause.paused,
                                             "recording":recording.isRecording,"hud":hudSession,
                                             "pointerPath":motionFilter.path.rawValue]])
            guard let steps = senseSession.accept(frame, arrival: arrival) else { return }
            let time = senseClock.align(micros: frame.micros, arrival: arrival)
            let axes = deviceSettings.senseAxes
            let accel = frame.accel.map { WandSenseUnits.accel($0, info: info, axes: axes) }
            let gyro = frame.gyro.map { WandSenseUnits.gyro($0, info: info, axes: axes) }
            // A merged run (radio busy) is replayed reading by reading at its own
            // times, immediately, so its motion is integrated instead of lost.
            // Recovered short taps have no known historical edge time. Do not
            // run motion backwards through a synthetic press at the final time.
            let times = gyro == nil ? [time] : WandSenseReplay.times(last: time, frame: frame, after: senseLastReading,
                allowHistory: !steps.contains(where: { $0.synthetic }))
            senseLastReading = time
            for step in steps {
                if step.synthetic { log("SENSE_SHORT_PRESS_RESTORED"); virtual.deliver(time: time, mask: step.mask, accel: nil, gyro: nil) }
                else {
                    for at in times.dropLast() { virtual.deliver(time: at, mask: step.mask, accel: accel, gyro: gyro) }
                    virtual.deliver(time: time, mask: step.mask, accel: accel, gyro: gyro)
                }
            }
        case .battery(let millivolts, _):
            // Single-cell LiPo estimate only; capacity and runtime are not measured.
            let volts = Double(millivolts) / 1000
            let usable = volts >= 2.5 && volts <= 4.5
            virtual.battery(volts: usable ? volts : nil,
                            percent: usable ? Int(max(0, min(100, ((volts - 3.3) / 0.85 * 100).rounded()))) : nil)
        case .event(let text): log("SENSE_EVENT", text)
        case .info: break
        }
    }
}

/// Read-only dashboard feed from the one hardware owner. The dashboard binds
/// this same-user datagram socket; the receiver only sends, never listens, and
/// drops a datagram rather than wait. Pointer input never depends on it.
final class WandSenseDashboardTap {
    private let path: String
    private var fd: Int32 = -1, checkedAt = -10.0, available = false
    init(path: String) { self.path = path }
    deinit { if fd >= 0 { close(fd) } }

    func packet(_ value: [String: Any]) { send(value) }
    func status(_ value: [String: Any]) { checkedAt = -10; send(value) }

    private func ready() -> Bool {
        let now = ProcessInfo.processInfo.systemUptime
        if now - checkedAt >= 1 {
            checkedAt = now
            var info = stat()
            available = lstat(path, &info) == 0 && info.st_uid == geteuid() &&
                info.st_mode & S_IFMT == S_IFSOCK && info.st_mode & 0o077 == 0
            if available && fd < 0 {
                fd = socket(AF_UNIX, SOCK_DGRAM, 0)
                if fd >= 0 { _ = fcntl(fd, F_SETFL, O_NONBLOCK) }
            }
        }
        return available && fd >= 0
    }

    private func send(_ value: [String: Any]) {
        guard ready(), let data = try? JSONSerialization.data(withJSONObject: value, options: [.sortedKeys]), data.count <= 2048 else { return }
        var address = sockaddr_un(); address.sun_family = sa_family_t(AF_UNIX)
        let bytes = Array(path.utf8) + [0]
        guard bytes.count <= MemoryLayout.size(ofValue: address.sun_path) else { return }
        withUnsafeMutableBytes(of: &address.sun_path) { $0.copyBytes(from: bytes) }
        address.sun_len = UInt8(MemoryLayout<sockaddr_un>.size)
        _ = data.withUnsafeBytes { payload in
            withUnsafePointer(to: &address) { pointer in
                pointer.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                    sendto(fd, payload.baseAddress, data.count, 0, $0, socklen_t(MemoryLayout<sockaddr_un>.size))
                }
            }
        }
    }
}
