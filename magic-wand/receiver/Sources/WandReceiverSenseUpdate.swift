import Foundation
import CryptoKit

/// The receiver's side of a wireless Sense update. The protocol, policy and
/// state machine are in WandSenseUpdate.swift; this file only performs their
/// effects through the one existing Sense link (no second Bluetooth owner).
final class WandSenseUpdateSession {
    var flow = WandSenseUpdateFlow()
    var setup = WandSenseUpdateSetup()
    var package: WandSenseDFUPackage?
    var key: SymmetricKey?
    var requestID: String?
    var timer: Timer?
    var batteryMillivolts: Int?, charging = false
}

extension WandReceiver {
    var firmwareUpdateRequestPath: String { support.appendingPathComponent(WandSenseUpdateRequest.fileName).path }
    var senseUpdateKeys: WandSenseUpdateKeyStore { WandSenseUpdateKeyStore(folder: support) }

    /// One request at a time, only for the connected Sense over Bluetooth, and
    /// only after the complete preflight passes. A refused request changes nothing.
    func readFirmwareUpdateRequest() {
        let reconcilePath = support.appendingPathComponent(WandSenseUpdateReconcileRequest.fileName).path
        if let request = WandSenseUpdateReconcileRequest.take(at: reconcilePath) {
            guard !senseUpdate.flow.busy, let info = senseInfo, request.matches(info) else {
                log("SENSE_UPDATE_RECONCILE_REFUSED", "board or update result changed"); return
            }
            senseUpdate.requestID = request.id
            performSenseUpdate(senseUpdate.flow.reconcile(request, info: info))
            armSenseUpdateTimer(15)
            return // A later, separate update request is required to retry.
        }
        guard let request = WandSenseUpdateRequest.take(at: firmwareUpdateRequestPath) else { return }
        let update = senseUpdate
        log("SENSE_UPDATE_REQUEST", request.id, "firmware", request.firmware, request.firstTrial ? "first-trial" : "")
        guard !update.flow.busy else { log("SENSE_UPDATE_REFUSED", "an update is already running"); return }
        guard update.setup.keyBoardID == nil else { log("SENSE_UPDATE_REFUSED", "key provisioning is unconfirmed"); return }
        update.requestID = request.id
        guard isSense, let info = senseInfo else { failSenseUpdate("No Sense wand is connected."); return }
        let package: WandSenseDFUPackage
        do { package = try WandSenseDFUPackage.load(directory: request.package) }
        catch { failSenseUpdate("The package is invalid: \(error)."); return }
        let check = WandSenseUpdateCheck(batteryMillivolts: update.batteryMillivolts, charging: update.charging,
                                         overBluetooth: senseTransport == .bluetooth, expectedSHA256: request.sha256,
                                         expectedFirmware: request.firmware, allowFirstTrial: request.firstTrial, acceptUSBRecovery: request.acceptUSBRecovery)
        let blockers = WandSenseUpdatePreflight.blockers(info, package, check)
        guard blockers.isEmpty else { failSenseUpdate(blockers.joined(separator: " ")); return }
        guard let key = senseUpdateKeys.load(info.id) else { failSenseUpdate("This Mac has no update key for the wand. Connect it over USB once."); return }
        senseUpdateRefusal = nil
        update.package = package; update.key = key
        performSenseUpdate(update.flow.begin(boardID: info.id, target: package.target.firmwareNumber))
        armSenseUpdateTimer(15)
    }

    func senseUpdateReply(_ reply: WandSenseUpdateReply) {
        let update = senseUpdate
        switch reply {
        case .keySaved:
            if let info = senseInfo, senseTransport == .usb, update.setup.keySaved(boardID: info.id) {
                senseInfo?.update.keyProvisioned = true
                log("SENSE_UPDATE_KEY_SAVED"); status()
            }
            return
        case .keyRemoved: log("SENSE_UPDATE_KEY_REMOVED"); return
        case .refused(let reason):
            if update.setup.keyBoardID != nil {
                update.setup.reset(); log("SENSE_UPDATE_KEY_REFUSED", reason)
            }
            performSenseUpdate(update.flow.reply(reply) { _ in "" }); return
        case .verified:
            guard let info = senseInfo else { return }
            let effects = update.flow.verified(boardID: info.id)
            if !effects.isEmpty { senseInfo?.update.result = "none"; senseInfo?.update.pendingTarget = nil }
            performSenseUpdate(effects); return
        default: break
        }
        guard let info = senseInfo, let key = update.key, let package = update.package else { return }
        performSenseUpdate(update.flow.reply(reply) { nonce in
            WandSenseUpdateAuth.authorize(key: key, boardID: info.id, nonce: nonce, package: package)
        })
    }

    /// Called with every new Sense identity: USB provisioning and the
    /// post-update confirmation.
    func senseUpdateIdentity(_ info: WandSenseInfo, _ transport: WandSenseLink.Transport) {
        // Existing physical-USB provisioning, now after H establishes the
        // firmware session. Never claim a matching key before KEY saved.
        var provision: String?
        if transport == .usb, info.update.updater == 1 {
            let key = senseUpdateKeys.load(info.id) ?? (try? senseUpdateKeys.create(info.id))
            if let key { provision = WandSenseUpdateAuth.provision(key) }
            else { log("SENSE_UPDATE_KEY_UNAVAILABLE") }
            senseInfo?.update.keyProvisioned = false
        }
        for command in senseUpdate.setup.begin(boardID: info.id, provision: provision) { senseLink?.send(command) }
        if info.update.result != "none", !senseUpdate.flow.busy { log("SENSE_UPDATE_RESULT_UNCONFIRMED", info.update.result) }
        performSenseUpdate(senseUpdate.flow.identity(info))
    }

    func senseUpdateConnectionLost() { senseUpdate.setup.reset(); performSenseUpdate(senseUpdate.flow.connectionLost()) }
    func senseUpdateBattery(millivolts: Int, charging: Bool) { senseUpdate.batteryMillivolts = millivolts; senseUpdate.charging = charging }

    private func performSenseUpdate(_ effects: [WandSenseUpdateFlow.Effect]) {
        let update = senseUpdate
        for effect in effects {
            switch effect {
            case .send(let command): senseLink?.send(command)
            case .beginTransfer:
                guard let package = update.package, let transfer = senseLink?.prepareUpdate(package) else {
                    performSenseUpdate(update.flow.transferEnded("the wand was not connected over Bluetooth at the handoff")); return
                }
                log("SENSE_UPDATE_HANDOFF", "firmware", package.target.firmwareNumber, "bytes", package.image.count)
                transfer.onLog = { log($0) }
                transfer.onStarted = { [weak self] in guard let self else { return }; self.performSenseUpdate(self.senseUpdate.flow.transferStarted()) }
                transfer.onFinish = { [weak self] error in
                    guard let self else { return }
                    self.senseLink?.finishUpdate()
                    self.performSenseUpdate(self.senseUpdate.flow.transferEnded(error))
                    if error == nil { self.armSenseUpdateTimer(90) } // Restart and reconnect.
                }
                update.timer?.invalidate(); update.timer = nil
            case .report:
                let flow = update.flow
                log("SENSE_UPDATE", flow.state.rawValue, "firmware", flow.target, flow.detail)
                if !flow.busy { update.timer?.invalidate(); update.timer = nil; update.key = nil; update.package = nil }
                status()
            }
        }
    }

    private func armSenseUpdateTimer(_ seconds: Double) {
        senseUpdate.timer?.invalidate()
        senseUpdate.timer = WandRunLoop.commonTimer(interval: seconds, repeats: false) { [weak self] _ in
            guard let self else { return }
            self.performSenseUpdate(self.senseUpdate.flow.timedOut())
        }
    }

    private func failSenseUpdate(_ text: String) {
        log("SENSE_UPDATE_REFUSED", text)
        senseUpdateRefusal = text
        status()
    }

    /// status.json: the actual update state, never a guess.
    var senseUpdateStatus: [String: Any] {
        let flow = senseUpdate.flow
        var value: [String: Any] = ["state": flow.state.rawValue, "firmware": flow.target, "detail": flow.detail]
        value["batteryMillivolts"] = senseUpdate.batteryMillivolts ?? NSNull()
        value["charging"] = senseUpdate.batteryMillivolts == nil ? NSNull() : senseUpdate.charging
        if let id = senseUpdate.requestID { value["request"] = id }
        if let refusal = senseUpdateRefusal { value["lastRefusal"] = refusal }
        if let info = senseInfo {
            value["installed"] = info.update.firmwareNumber ?? NSNull()
            value["bootloader"] = info.update.bootloader ?? NSNull()
            value["updater"] = info.update.updater
            value["keyProvisioned"] = info.update.keyProvisioned
            value["pendingResult"] = info.update.result
            value["pendingTarget"] = info.update.pendingTarget ?? NSNull()
        }
        return value
    }
}
