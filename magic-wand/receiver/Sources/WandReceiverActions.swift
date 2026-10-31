import Foundation
import Darwin

/// Ethan's debug pause (WandActionPause), owned by this receiver: the dashboard
/// asks through a private request file and displays status.json, never its own guess.
extension WandReceiver {
    var actionRequestPath: String { support.appendingPathComponent(WandActionPauseRequest.fileName).path }
    var lightDemoRequestPath: String { support.appendingPathComponent("light-demo.request").path }

    /// Watch the private support directory for the dashboard's request file.
    /// A request left by an earlier run is discarded: a restart clears the pause.
    func startActionRequests() {
        unlink(actionRequestPath)
        unlink(lightDemoRequestPath) // Never replay an old physical demo at launch.
        // Update permissions are scoped to this receiver run, including failure acknowledgement.
        unlink(firmwareUpdateRequestPath)
        unlink(support.appendingPathComponent(WandSenseUpdateReconcileRequest.fileName).path)
        let fd = open(support.path, O_EVTONLY)
        guard fd >= 0 else { log("ACTIONS_REQUESTS_UNAVAILABLE"); return }
        let source = DispatchSource.makeFileSystemObjectSource(fileDescriptor: fd, eventMask: [.write], queue: .main)
        source.setEventHandler { [weak self] in self?.readActionRequest(); self?.readGuideRequest(); self?.readFirmwareUpdateRequest(); self?.readLightDemoRequest() }
        source.setCancelHandler { close(fd) }
        source.resume(); actionRequestSource = source
    }

    func readActionRequest() {
        guard let request = WandActionPauseRequest.take(at: actionRequestPath) else { return }
        setActionsPaused(request.paused, request: request.id)
    }

    /// Reuse the guide's strict private show/hide envelope and safe file reader.
    /// Here `visible` starts/stops only the bounded RGB demonstration.
    func readLightDemoRequest() {
        guard let request = WandGuideRequest.take(at: lightDemoRequestPath) else { return }
        guard isSense, ready, !restoring, let virtual = senseVirtual else { log("LIGHT_DEMO_NOT_READY"); return }
        log("LIGHT_DEMO_REQUEST", virtual.lightDemo(request.visible) ? "accepted" : "rejected")
    }

    func setActionsPaused(_ paused: Bool, request: String? = nil) {
        actionPauseGeneration += 1
        if paused {
            pauseActions()
            if let request { actionPause.acknowledge(request) }
            status()
        } else { resumeActions(request: request) }
    }

    /// Finish every outward lane once, then send nothing more until resumed:
    /// release native buttons; cancel recentre, screenshot, scroll, dwell, drag,
    /// HUD and review timers. Agent Flow is not contacted, so dictation in
    /// progress continues. Sensors, lights, power and calibration keep running.
    private func pauseActions() {
        controls.suspended = true
        if isSense { senseVirtual?.holdSensor(true) }
        guard !actionPause.paused else { return }
        controls.suspended = false // Cleanup below may still close the wand's own HUD session.
        pendingRecenter?.invalidate(); pendingRecenter = nil; tripleClick.cancel(); recenterGesture.cancel()
        clickFollowChoice = nil; recenterSuppressButtons = false
        endScreenshot(reason: "actions paused", contextActive: screenshotActive, forgetPress: true)
        if hudSession || screenshotHUD { closeHUD(reason: "actions paused") }
        hudButtonTap?.invalidate(); hudButtonTap = nil; hudButtonHold?.invalidate(); hudButtonHold = nil
        hudButtonHeld = false; hudButtonQualified = false; hudEntryPress = false; pointerInHUD = false
        hudButtonOperating = false; hudButtonDoubleConsumed = false
        reviewExitTimer?.invalidate(); reviewExitTimer = nil; reviewExitGesture.reset(); hudButtonReviewExit = false
        hiddenReviewPending = false; hiddenReviewOperating = false
        finishWandShortcut(commit: false); sendReview(review.cancel()); reviewTimer?.invalidate(); reviewTimer = nil
        cancelCircleScroll(); finishScroll()
        performPointer(pointerRouter.cancelAll()); lowDelayTimer?.invalidate(); lowDelayTimer = nil
        dwell.reset(); dwellTimer?.invalidate(); dwellTimer = nil
        releaseButtons(); motionFilter.reset()
        actionPause.pause(); controls.suspended = true
        log("ACTIONS_PAUSED")
    }

    /// Drop any wand gesture begun while paused and restore this receiver's own
    /// follow choice. The program's reply to that reset is still ignored: the
    /// unpause happens on the next main-queue turn, after the virtual Puck's
    /// output for it. Afterwards each lane needs a fresh press (WandActionPause.admit).
    private func resumeActions(request: String?) {
        guard actionPause.paused else {
            if let request { actionPause.acknowledge(request) }
            status(); return
        }
        if ready && !restoring { queue("global.wandShot=0;setMouseFollow(" + (dwell.following ? "true" : "false") + ");") }
        if isSense { senseVirtual?.holdSensor(false) }
        motionFilter.reset(); rawLastArrival = 0
        let generation = actionPauseGeneration
        DispatchQueue.main.async { [weak self] in
            guard let self, self.actionPauseGeneration == generation, self.actionPause.paused else { return }
            self.actionPause.resume(); self.controls.suspended = false
            self.dwell.reset(); self.scheduleDwell()
            if let mode = self.selectedReviewMode { self.setWandShortcut(mode) }
            if let request { self.actionPause.acknowledge(request) }
            log("ACTIONS_RESUMED"); self.status()
        }
    }
}
