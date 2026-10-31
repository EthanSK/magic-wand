import Foundation
import AppKit
import CoreBluetooth
import ApplicationServices
import CoreGraphics
import Darwin
import CryptoKit

let support = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/WandReceiver")
try? FileManager.default.createDirectory(at: support, withIntermediateDirectories: true)
let logURL = support.appendingPathComponent("receiver.log")
func log(_ values: Any...) {
    let line = ISO8601DateFormatter().string(from: Date()) + " " + values.map { String(describing: $0) }.joined(separator: " ") + "\n"
    if ((try? logURL.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? 0) > 524288 {
        let previous = support.appendingPathComponent("receiver.previous.log")
        try? FileManager.default.removeItem(at: previous)
        try? FileManager.default.moveItem(at: logURL, to: previous)
    }
    if !FileManager.default.fileExists(atPath: logURL.path) { FileManager.default.createFile(atPath: logURL.path, contents: nil) }
    if let file = try? FileHandle(forWritingTo: logURL) { defer { try? file.close() }; _ = try? file.seekToEnd(); try? file.write(contentsOf: Data(line.utf8)) }
}
/// Ethan's "two-finger drag": a native precise scroll gesture, not a guessed
/// Back/Forward shortcut. The receiving app owns scrolling and edge navigation.
/// Keep the existing wheel distance (one line is ten CoreGraphics points).
/// This is transport only: no pointer buffering, inertia or replay.
/// Used only for a held scroll's purely sideways output; page scrolling with
/// any vertical part uses the separate page transport (see postSustainedScroll).
struct WandNativeScrollGesture {
    private(set) var active=false
    private var anchor=CGPoint.zero
    mutating func update(x:Int32,y:Int32,at point:CGPoint)->CGEvent? {
        guard x != 0 || y != 0 else{return nil}
        let phase:CGScrollPhase=active ? .changed:.began
        let position=active ? anchor:point
        guard let event=Self.event(x:x,y:y,phase:phase,at:position) else{return nil}
        anchor=position;active=true
        return event
    }
    mutating func finish(cancelled:Bool)->CGEvent? {
        guard active else{return nil}
        active=false
        return Self.event(x:0,y:0,phase:cancelled ? .cancelled:.ended,at:anchor)
    }
    private static func event(x:Int32,y:Int32,phase:CGScrollPhase,at point:CGPoint)->CGEvent? {
        guard let source=CGEventSource(stateID:.hidSystemState),
              let event=CGEvent(scrollWheelEvent2Source:source,units:.pixel,wheelCount:2,
                               wheel1:Int32(clamping:Int64(y)*10),wheel2:Int32(clamping:Int64(x)*10),wheel3:0) else{return nil}
        event.location=point
        event.setIntegerValueField(.scrollWheelEventScrollPhase,value:Int64(phase.rawValue))
        event.setIntegerValueField(.scrollWheelEventMomentumPhase,value:0)
        return event
    }
}

final class WandReceiver: NSObject, CBCentralManagerDelegate, CBPeripheralDelegate {
    var manager: CBCentralManager!
    var device: CBPeripheral?
    var tx: CBCharacteristic?
    var chunks: [Data] = []
    var writing = false, configuring = false, uartPaused = false
    var input = "", buttons = 0, reportCount = 0, movementCount = 0
    // Real-life debug recordings: gyro motion alone does not prove mouse use.
    // This grows only when a native pointer event actually changes its position.
    var pointerTravel = 0.0
    var restoring = false, bridgeLoadFailed = false, loadingBridge = false, loadingRuntime = false, generation = 0, retry: DispatchWorkItem?
    var lastTrusted = false, ready = false, legacySignaled = false
    var lastStatusKey = ""
    var lightMode = "unknown"
    var batteryPercent:Int?,batteryVolts:Double?,batterySampleAt:Date?
    var batteryRequested=Date.distantPast
    var pointerDisplays:[CGRect]=[]
    var deliveryPoint:CGPoint?
    var circleAnchor:CGPoint?,scrollAnchor:CGPoint?
    var displayObserver:NSObjectProtocol?
    // LOW aiming delay, loop scrolling and consumed-click removal live in the
    // pure WandPointerRouter (wand-pointer-control.swift); this class only posts.
    let pointerRouter=WandPointerRouter()
    let recenterGesture=WandRecenterGesture()
    var recenterSuppressButtons=false
    // Ethan's mouse-button triple-click screenshot shortcut shares the double click's
    // first two clicks; that recentre now waits out the third press's window.
    var tripleClick=WandTripleClick()
    var pendingRecenter:Timer?
    // Only the short exit-follow click waits for the existing double/triple window.
    var pendingMouseExitClick:Timer?,mouseExitClickToken=UUID()
    var clickFollowChoice:(following:Bool,paused:Bool,restore:Bool?,rest:WandRestFollowMemory)?
    // Screenshot mode: temporary pointer and mouse-button ownership while the native
    // selection is active. It never changes the ordinary follow choice.
    let screenshot=WandScreenshotGesture()
    var screenshotTimer:Timer?
    let motionFilter=WandMotionFilter()
    // Cumulative unrounded HIGH mouse counts, scoped to the current HUD button
    // hold. Native Switch App alone consumes this; other HUD cards stay angular.
    // Previously middleMouseX and middleMouseSampleAt.
    var hudButtonMouseX=0.0,hudButtonMouseSampleAt = -100.0
    // Ethan's Switch App winding while Agentic Mouse reports dotted app switching.
    var hudButtonMouseOffset:Double? { // Previously middleMouseOffset.
        let age=ProcessInfo.processInfo.systemUptime-hudButtonMouseSampleAt
        return age>=0 && age<=0.25 && hudButtonMouseX.isFinite && abs(hudButtonMouseX)<=7_200_000 ? hudButtonMouseX : nil
    }
    let options=WandUserOptions(url:support.appendingPathComponent("feature-flags.json"))
    let flickScroll=WandFlickScroll()
    let heldScroll=WandHeldScroll()
    var nativeScroll=WandNativeScrollGesture()
    var scrollFollowBefore=false
    var heldScrollAnchor:CGPoint?
    var heldTargetToken=UUID()
    var heldSafetyTimer:Timer?
    var controlVersion:WandControlVersion = .pointerV1
    var controlV1Menu:NSMenuItem?,controlV2Menu:NSMenuItem?,controlV3Menu:NSMenuItem?
    var flickScrollEnabled=false
    var pointerFilterMenuItem:NSMenuItem?
    // Opt-in: one local line per Control V3 hold with stroke counts and wheel
    // rates, never positions. Off unless feature-flags.json enables it.
    var heldScrollDiagnostics=false
    var reviewAxisEnabled=false
    var reviewAxisMenuItem:NSMenuItem?
    var flickAnchor:CGPoint?
    /// Ethan's always-available instruction panel (WandGuidePanel.swift).
    var guide:WandGuideController?,guideMenuItem:NSMenuItem?
    var statusItem:NSStatusItem?,connectionMenuItem:NSMenuItem?,flickMenuItem:NSMenuItem?,rotationMenuItem:NSMenuItem?

    var rawLastArrival=0.0,rawReports=0,rawWindowStart=0.0,rawMaxGap=0.0
    // Ordinary stop-to-click stays single-shot (receiver 114 behaviour).
    // Ethan's 2026-10-30 "as little weirdness as possible" amendment pauses
    // the 300 ms repeat experiment; the captured no-click jumps were a
    // separate stale-origin defect, fixed by WandPointerOrigin below.
    let dwell=WandDwellClick()
    // Per physical wand: the Sense profile swaps in its own learned desk pose.
    var restDetection=WandRestDetection(cache:support.appendingPathComponent("desk-reference.json"))
    var deskSleep=WandDeskSleep()
    var powerPolicyReady=false,loadingPowerPolicy=false
    var standbyResume:Bool?
    func calibrationURL(for device:String)->URL {support.appendingPathComponent("calibrations").appendingPathComponent(device+".json")}
    var dwellTimer:Timer?,probeTimer:Timer?
    var restDiagnosticsRemaining=30
    let review=WandReviewGesture()
    var reviewTimer:Timer?,reviewOriginY=0.0,appMode:String?
    var wandShortcutMode:String?,wandShortcutX=0.0,wandShortcutY=0.0,wandShortcutTime=0.0
    let reviewTrace = WandReviewTrace(directory:support.appendingPathComponent("review-traces"),
        configuration:support.appendingPathComponent("review-trace.json"),
        build:Bundle.main.object(forInfoDictionaryKey:"CFBundleVersion") as? String ?? "unknown")
    var wandShortcutCircle=WandReviewNavigation()
    var hudButtonReviewExit=false // Previously middleReviewExit.
    var reviewExitGesture=WandReviewExitGesture()
    var reviewExitTimer:Timer?
    var selectedReviewMode:String?
    var hiddenReviewOperating=false
    var hiddenReviewPending=false
    var screenshotActive=false,screenshotHUD=false
    // Previously middleLastRelease, middlePressedAt and middleDoubleConsumed.
    var hudButtonLastRelease = -100.0,hudButtonPressedAt=0.0,hudButtonDoubleConsumed=false
    /// The pending `hudButtonTap` is a tap that opened the HUD from closed: a
    /// second press inside its double-click window right-clicks instead.
    var hudButtonClosedTap=false // Previously middleClosedTap.
    var circleLight=false
    var circleTimer:Timer?,lowDelayTimer:Timer?
    var heartbeat: Timer?
    // Ethan's debug pause (WandActionPause / WandReceiverActions.swift): memory only.
    var actionPause=WandActionPause()
    var actionRequestSource:DispatchSourceFileSystemObject?
    var actionPauseGeneration=0
    let controls = WandControlTransport()
    let context = WandContextListener()
    let recording = WandRecordingState(cache:support.appendingPathComponent("recording-state.json"))
    var recordingPointerPaused=false
    var recordingRestoreFollow:Bool?
    var restFollow=WandRestFollowMemory()
    // One serial lane bounds the mouse-button-hold Accessibility probe off the
    // main thread; motion and posting never wait for it.
    let holdTargetQueue=DispatchQueue(label:"wand.hold-target",qos:.userInitiated)
    var pointerInHUD=false, hudButtonOperating=false, hudButtonSecondTap=false // Previously middleOperating and middleSecondTap.
    var acceptHUDContext=true
    var navStream=WandAngularStream(),moveStream=WandAngularStream(),legacyHUDStream=WandAngularStream(),scrollStream=WandAngularStream()
    var hudSession=false,hudEntryPress=false
    var hudEntryPressStarted=0.0
    // Ethan's hold-to-show HUD: true from HUD button down to HUD button up while the
    // HUD is steering. Agentic Mouse decides on release whether it stays open.
    var hudButtonHeld=false,hudButtonQualified=false,hudOpenedAt=0.0 // Previously middleHeld and middleQualified.
    let hudHoldSeconds=0.14 // Existing received HUD-button hold cutoff; firmware already waits 80 ms.
    var navX=0.0,navY=0.0,navOriginX=0.0,navOriginY=0.0,operationOriginX=0.0,operationOriginY=0.0
    var hudButtonX=0.0,hudButtonY=0.0 // Previously middleX and middleY.
    var hudButtonHold:Timer?, hudButtonTap:Timer? // Previously middleHold and middleTap.
    var hudActive = false, hudLastUpdate = Date.distantPast
    var hudWatchdog: Timer?
    var navigationOpenedHUD=false,scrollActive=false
    var scrollX=0.0,scrollY=0.0,scrollFractionX=0.0,scrollFractionY=0.0
    var scrollPostedX=0,scrollPostedY=0
    var scrollUpdated=Date.distantPast
    var scrollWatchdog:Timer?
    // Public source: the installed build pinned one Puck here. Set yours in device.json
    // (see BUILDING.md); the identifier is optional and only skips scanning.
    let deviceSettings = WandDeviceConfiguration.load(from: support.appendingPathComponent("device.json"))
    var target: UUID? { deviceSettings.identifier }
    // XIAO nRF52840 Sense profile ("Sense wand"): one USB/Bluetooth owner plus
    // the canonical Puck program run on the Mac (WandVirtualPuck). See
    // WandReceiverSense.swift. Never active for the Puck profile.
    var isSense: Bool { deviceSettings.profile == .sense }
    var senseLink: WandSenseLink?
    var senseVirtual: WandVirtualPuck?
    var senseInfo: WandSenseInfo?
    var senseTransport: WandSenseLink.Transport?
    var senseSession=WandSenseSession(),senseClock=WandSenseClock(),senseSessionNumber=0,senseLastReading = -Double.infinity
    var senseMouseButtonTimer=WandSenseMouseButtonTimer() // Previously senseBottomTimer.
    // Wireless Sense updates (WandReceiverSenseUpdate.swift).
    let senseUpdate=WandSenseUpdateSession()
    var senseUpdateRefusal:String?
    var pointerOrigin=WandPointerOrigin()
    /// Why stop-to-click cannot act right now (nil: it can).
    var clickGate:String?
    /// Late readings kept out of normal pointing this session (`WandSenseStaleness`).
    var senseStaleReadings=0
    let senseDashboard=WandSenseDashboardTap(path:support.appendingPathComponent("sense-dashboard.sock").path)
    /// Calibration belongs to one physical wand; a Sense never reads a Puck zero.
    var calibrationKey:String? {
        // "-c875": Puck-equivalent gyro counts (8.75 mdps). The older key held 134-per-deg/s zeros.
        isSense ? senseInfo.map{"sense-"+$0.id+"-"+deviceSettings.senseAxes.signature+"-c875"} : device?.identifier.uuidString
    }
    var deviceConnected:Bool { isSense ? senseTransport != nil : device?.state == .connected }
    let uart = CBUUID(string: "6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
    var restore: String {
        // Ethan's "blinking orange while restarting": an update keeps the device's
        // loading light blinking until the next receiver reports ready.
        let loading = FileManager.default.fileExists(atPath:support.appendingPathComponent("update.inprogress").path)
            ? "global.WAND_UPDATING=true;if(typeof updateLights==='function')updateLights();" : ""
        return loading + "global.wandShot=0;if(global.wandBridgeOriginalSend){mouse.send=global.wandBridgeOriginalSend;delete global.wandBridgeOriginalSend;}print('WAND_BRIDGE_RESTORED');"
    }
    let bridgeCache = support.appendingPathComponent("active-bridge.json")
    var receiverBuild:String {Bundle.main.object(forInfoDictionaryKey:"CFBundleVersion") as? String ?? "unknown"}
    var modeBridge:String {
        var metadata=stat()
        if lstat(bridgeCache.path,&metadata)==0,metadata.st_uid==geteuid(),metadata.st_mode & S_IFMT == S_IFREG,
           metadata.st_mode & 0o022 == 0,metadata.st_size<=65536,
           let data=try? Data(contentsOf:bridgeCache),let value=try? JSONSerialization.jsonObject(with:data) as? [String:String],
           value["runtime"]==runtimeVersion,value["build"]==receiverBuild,let code=value["code"] {return code}
        return (Bundle.main.url(forResource:"wand-mode-bridge",withExtension:"js").flatMap {try? String(contentsOf:$0,encoding:.utf8)}) ?? ""
    }
    func bridgeRevision(_ code:String)->String {SHA256.hash(data:Data(code.utf8)).map{String(format:"%02x",$0)}.joined()}
    func loadModeBridge(_ code:String?=nil) {
        let source=code ?? modeBridge
        bridgeLoadFailed=false;loadingBridge=true;ready=false
        deadline(seconds:60)
        // The placeholder keeps the saved base's loading blink running while the
        // bridge statements arrive; a pre-blink base keeps the old steady orange.
        queue("global.WAND_UPDATING=true;global.wandRawPointer=true;global.wandMotionReady=false;updateLights.replaceWith(function(){if(typeof loadingLight==='function')loadingLight();else{writeLight(LED1,0.45);writeLight(LED2,0.45);writeLight(LED3,0.45);}});updateLights();")
        // Each complete statement is small; the old single giant REPL function
        // exceeded the device's available memory during repeated live updates.
        for command in source.split(separator:"\n") where !command.contains("WAND_MODE_ROUTING_READY") {queue(String(command))}
        if isSense { senseVirtual?.configurePointer(deviceSettings.sensePointerGain) }
        queue("if(global.wandMotionReady){global.WAND_BRIDGE_REVISION='"+bridgeRevision(source)+"';print('WAND_MODE_ROUTING_READY');}else print('WAND_UPDATE_FAILED');")
    }
    let commands: [String]
    let runtimeVersion = (try? String(contentsOf: Bundle.main.url(forResource: "wand-runtime-version", withExtension: "txt")!, encoding: .utf8)) ?? ""
    override init() {
        commands = (try? JSONDecoder().decode([String].self, from: Data(contentsOf: Bundle.main.url(forResource: "wand-commands", withExtension: "json")!))) ?? []
        super.init()
        refreshPointerDisplays()
        displayObserver=NotificationCenter.default.addObserver(forName:NSApplication.didChangeScreenParametersNotification,object:nil,queue:.main){[weak self] _ in self?.refreshPointerDisplays()}
        context.onChange = {[weak self] active in
            guard let self,self.ready,!self.restoring else{return}
            // Agentic Mouse closes the HUD after a completed action. It already
            // knows, so this close sends no dismiss that would cut short the
            // action's follow-up. A live HUD button hold settles it on release.
            if !active {if self.hudSession && !self.hudButtonHeld {self.closeHUD(reason:"context ended",notifyNative:false)};return}
            guard self.acceptHUDContext else{return}
            // Waiting for the next hold: show the HUD, but never steer it unheld.
            if !self.hudSession {self.cancelCircleScroll();self.hudSession=true;self.hudOpenedAt=ProcessInfo.processInfo.systemUptime;self.navStream.reset();self.navX=0;self.navY=0}
            self.queue("if(typeof setHUDOpen==='function')setHUDOpen(true);")
        }
        context.start()
        context.onModeChange = {[weak self] mode in
            guard let self,self.acceptHUDContext,self.hudSession else{return};self.sendReview(self.review.cancel());self.appMode=mode
            self.queue("global.wandAppMode="+(mode.map{ "'"+$0+"'" } ?? "undefined")+";updateLights();")
            // App-specific entry is a submenu of the existing wand journey.
            // Its selection already resumed navigation. A second navigate ID
            // conflicts with that live hold and makes Agentic Mouse close it.
        }
        // Review selection, rather than a held HUD card, owns the independent session.
        context.onReviewChange = {_ in }
        context.onSelectionChange = {[weak self] mode in
            guard let self else{return}
            // Agentic Mouse alone owns the selection. Its acknowledgement of our
            // own Review/Stage toggle keeps presses made since; any other change
            // is newer than the review gesture and cancels it.
            if self.reviewExitGesture.acknowledgeToggle(from:self.selectedReviewMode,to:mode,now:ProcessInfo.processInfo.systemUptime) {
                log("WAND_REVIEW_TOGGLED",mode ?? "none")
            } else {
                self.reviewExitTimer?.invalidate();self.reviewExitTimer=nil;self.reviewExitGesture.reset()
            }
            self.selectedReviewMode=mode
            self.setWandShortcut(mode)
        }
        context.onScreenshotChange = {[weak self] active in self?.setScreenshotActive(active)}
        // The held Switch App chooser starts or ends: a fresh cumulative
        // stream; Agentic Mouse rebases on its first sample, so nothing jumps
        // or replays. (The log key keeps its historical DOTTED name.)
        context.onSwitchAppAdjustingChange = {[weak self] adjusting in
            guard let self else{return}
            self.hudButtonMouseX=0;self.hudButtonMouseSampleAt = -100
            log("SWITCH_APP_DOTTED",adjusting)
        }
        recording.onChange = {[weak self] active in
            self?.recordingChanged(active)
        }
        recording.start()
        lastTrusted = AXIsProcessTrusted()
        setupOptionsMenu()
        refreshFeatureFlags()
        log("STARTED", ProcessInfo.processInfo.processIdentifier, "ACCESSIBILITY", lastTrusted)
        if CommandLine.arguments.contains("--request-permissions") {
            let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary
            _ = AXIsProcessTrustedWithOptions(options)
        }
        manager = CBCentralManager(delegate: self, queue: nil)
        if isSense { connect() }
        heartbeat = WandRunLoop.commonTimer(interval: 5, repeats: true) { [weak self] _ in
            guard let self else { return }
            let trusted = AXIsProcessTrusted()
            if self.lastTrusted != trusted { self.lastTrusted = trusted; log("ACCESSIBILITY", trusted); self.status() }
            self.recording.refresh()
            self.refreshFeatureFlags()
            self.requestBattery()
            self.status()
            if !self.ready && (self.isSense || (self.manager.state == .poweredOn && self.device == nil)) { self.connect() }
            self.readActionRequest()
            self.readFirmwareUpdateRequest()
        }
        startActionRequests()
        startGuide()
        status()
    }
    func restoreKnownCalibration() {
        guard let id=calibrationKey,
              let value=WandCalibrationStore.read(calibrationURL(for:id),device:id),let json=value.json else{return}
        queue("if(global.wandState&&!global.wandState().calibrated&&typeof global.restoreWandCalibration==='function')global.restoreWandCalibration("+json+");")
        log("KNOWN_CALIBRATION_RESTORE_REQUESTED")
    }
    func rememberCalibration(_ line:String) {
        guard let id=calibrationKey,let marker=line.range(of:"WAND_CALIBRATED "),
              let data=String(line[marker.upperBound...]).trimmingCharacters(in:.whitespacesAndNewlines).data(using:.utf8),
              let value=try? JSONDecoder().decode(WandCalibration.self,from:data),value.valid else{return}
        do {try WandCalibrationStore.write(value,to:calibrationURL(for:id),device:id);log("KNOWN_CALIBRATION_SAVED")}
        catch {log("KNOWN_CALIBRATION_SAVE_FAILED",error.localizedDescription)}
    }
    func checkPowerPolicy() {
        // Checking first matters even if the source guards its own version:
        // parsing the whole skipped function body can exhaust a warm Puck.
        powerPolicyReady=false
        queue("if(global.WAND_POWER_POLICY_VERSION===4&&typeof global.wandEnterDeepStandby==='function'&&global.wandPowerWatches&&global.wandPowerWatches.length===3)print('WAND_POWER_POLICY_READY');else print('WAND_POWER_POLICY_NEEDED');")
    }
    func loadPowerPolicy() {
        guard let url=Bundle.main.url(forResource:"wand-power-policy",withExtension:"js"),
              let source=try? String(contentsOf:url,encoding:.utf8) else{return}
        powerPolicyReady=false;loadingPowerPolicy=true
        for line in source.split(separator:"\n") where !line.trimmingCharacters(in:.whitespaces).hasPrefix("//") {queue(String(line))}
    }
    func syncRecordingLight() {
        guard ready,!restoring else{return}
        queue("setWandRecording("+(recording.isRecording ? "true":"false")+");")
    }
    func recordingChanged(_ active:Bool) {
        cancelMouseExitClick()
        // A recording transition is newer than a possible screenshot triple's
        // first-click snapshot. Apply it to that snapshot too, so undoing the
        // first two taps cannot undo a recording pause or its later restoration.
        if var choice=clickFollowChoice {
            if active {
                choice.restore=choice.following || choice.rest.handOverToRecording()
                choice.following=false;choice.paused=true
            } else {
                let resume=choice.paused && choice.restore == true
                choice.paused=false;choice.restore=nil
                if resume && restDetection.parked {choice.rest.restoreOnPickup()}
                else if resume {choice.following=true}
            }
            clickFollowChoice=choice
        }
        // Ethan: recording switches mouse follow off once. It is not a lock:
        // The mouse button can explicitly re-enter mouse mode while speech keeps running.
        performPointer(pointerRouter.interrupt());motionFilter.reset();deliveryPoint=nil
        if active {
            // A resting wand keeps the user's choice in rest memory; recording
            // takes it over so pickup during speech cannot switch it back on.
            recordingRestoreFollow=dwell.following || restFollow.handOverToRecording()
            recordingPointerPaused=true
            dwell.follow(false);restDetection.pointerStopped()
            queue("setMouseFollow(false);")
        } else {
            let resume=recordingPointerPaused && recordingRestoreFollow == true
            recordingPointerPaused=false;recordingRestoreFollow=nil
            // Still resting on the desk: resume on pickup, not on the table.
            if resume && restDetection.parked {restFollow.restoreOnPickup()}
            else if resume {dwell.follow(true);restDetection.pointerActivated();queue("setMouseFollow(true);")}
        }
        dwell.reset();scheduleDwell()
        log("RECORDING_STATE",active);syncRecordingLight();status()
    }
    /// The device's own follow report (`@FOLLOW`).
    func deviceFollowChanged(_ on:Bool) {
        guard !recordingPointerPaused,!screenshot.ownsPointer else{return}
        if on {restDetection.pointerActivated()}else{restDetection.pointerStopped();flickScroll.reset();flickAnchor=nil;setCircleLight(false)}
        dwell.follow(on);scheduleDwell()
    }
    func manualPointerDuringRecording() {
        // Manual mouse-button input wins over automatic speech-time restoration,
        // including a later explicit switch off. Never stop Agent Flow here.
        recordingPointerPaused=false;recordingRestoreFollow=nil
        restFollow.manualChoice()
    }
    // Opt-in, local-only flag. A missing or invalid file restores the original
    // axes. Read off the motion path so pointer delivery never waits for disk.
    func refreshFeatureFlags() {
        let enabled=options.enabled("orientationCompensation")
        let selected=WandControlVersion.read(options.read()["controlVersion"])
        if controlVersion != selected {controlVersion=selected;heldSafetyTimer?.invalidate();heldSafetyTimer=nil;finishNativeScroll(cancelled:true);heldScroll.reset();heldScrollAnchor=nil;flickScroll.reset();flickAnchor=nil;performPointer(pointerRouter.cancelAll());setCircleLight(false);releaseButtons();motionFilter.reset();if ready {queue("global.wandHostHeldScroll="+(selected.usesHeldScroll ? "true":"false")+";")}}
        controlV1Menu?.state=selected == .pointerV1 ? .on : .off
        controlV2Menu?.state=selected == .scrollV2 ? .on : .off
        controlV3Menu?.state=selected == .sustainedV3 ? .on : .off
        let flick=selected == .pointerV1 && options.enabled("flickScroll")
        flickMenuItem?.isEnabled=selected == .pointerV1
        flickMenuItem?.isHidden=selected.usesHeldScroll
        if flickScrollEnabled != flick {if flickScroll.active {setCircleLight(false);motionFilter.reset()};flickScrollEnabled=flick;flickScroll.reset();flickAnchor=nil}
        flickMenuItem?.state=flick ? .on : .off
        heldScrollDiagnostics=options.enabled("heldScrollDiagnostics")
        rotationMenuItem?.state=enabled ? .on : .off
        // Sense only: the direct pointer is the default; "sensePointer":"tuned"
        // returns to the Puck filter. A Puck always keeps the tuned filter.
        let pointerPath:WandPointerPath = isSense ? WandPointerPath.read(options.read()["sensePointer"],default:.direct) : .tuned
        if motionFilter.path != pointerPath {
            motionFilter.path=pointerPath;motionFilter.reset();dwell.reset();scheduleDwell();log("POINTER_PATH",pointerPath.rawValue)
        }
        pointerFilterMenuItem?.state=pointerPath == .tuned ? .on : .off
        let reviewAxes=options.enabled("reviewAxisGestures")
        if reviewAxisEnabled != reviewAxes {
            reviewTrace.record(.init(kind:"boundary",t:ProcessInfo.processInfo.systemUptime,
                                     reason:"axes changed",axisGestures:reviewAxes))
            reviewAxisEnabled=reviewAxes;wandShortcutCircle.useAxisGestures=reviewAxes;wandShortcutCircle.reset()
        }
        reviewAxisMenuItem?.state=reviewAxes ? .on : .off
        // Sense: gravity samples taken mid-jerk or mid-twist never set the basis.
        motionFilter.orientation.strictGravity=isSense
        if motionFilter.orientationCompensation != enabled {
            motionFilter.orientationCompensation=enabled;motionFilter.reset()
            log("ORIENTATION_COMPENSATION",enabled)
        }
    }
    func setupOptionsMenu() {
        let item=NSStatusBar.system.statusItem(withLength:NSStatusItem.variableLength)
        item.button?.image=NSImage(systemSymbolName:"wand.and.stars",accessibilityDescription:"Magic Wand")
        item.button?.image?.isTemplate=true
        item.button?.toolTip="Magic Wand"
        let menu=NSMenu(title:"Magic Wand")
        let title=NSMenuItem(title:"Wand Receiver",action:nil,keyEquivalent:"");title.isEnabled=false;menu.addItem(title)
        let connection=NSMenuItem(title:"Connecting…",action:nil,keyEquivalent:"");connection.isEnabled=false;menu.addItem(connection);connectionMenuItem=connection
        menu.addItem(.separator())
        let guideItem=NSMenuItem(title:"Wand Guide",action:#selector(toggleGuide),keyEquivalent:"")
        guideItem.target=self;guideItem.toolTip="Show every wand control in a small panel at the top right."
        menu.addItem(guideItem);guideMenuItem=guideItem
        let versions=NSMenu(title:"Control version")
        let v1=NSMenuItem(title:"V1 · Pointer",action:#selector(selectControlV1),keyEquivalent:"");v1.target=self;versions.addItem(v1);controlV1Menu=v1
        let v2=NSMenuItem(title:"V2 · Hold to scroll",action:#selector(selectControlV2),keyEquivalent:"");v2.target=self;versions.addItem(v2);controlV2Menu=v2
        let v3=NSMenuItem(title:"V3 · Hold to continue scrolling",action:#selector(selectControlV3),keyEquivalent:"");v3.target=self;versions.addItem(v3);controlV3Menu=v3
        let versionItem=NSMenuItem(title:"Control version",action:nil,keyEquivalent:"");versionItem.submenu=versions;menu.addItem(versionItem)
        let settings=NSMenu(title:"Options")
        let flick=NSMenuItem(title:"Flick to scroll",action:#selector(toggleFlickScroll),keyEquivalent:"")
        flick.target=self;flick.toolTip="In mouse mode, flick up then lower slowly to scroll up. No buttons needed."
        settings.addItem(flick);flickMenuItem=flick
        let rotation=NSMenuItem(title:"Rotation-independent controls",action:#selector(toggleRotation),keyEquivalent:"")
        rotation.target=self;rotation.toolTip="Keep mouse, HUD and scroll directions upright when you rotate the wand."
        settings.addItem(rotation);rotationMenuItem=rotation
        let pointer=NSMenuItem(title:"Pointer filtering",action:#selector(togglePointerFiltering),keyEquivalent:"")
        pointer.target=self;pointer.isHidden = !isSense
        pointer.toolTip="Puck smoothing, slack and slower speed for small movements. Off moves the pointer from the gyro with only light smoothing."
        settings.addItem(pointer);pointerFilterMenuItem=pointer
        let reviewAxes=NSMenuItem(title:"Review with nods and shakes",action:#selector(toggleReviewAxes),keyEquivalent:"")
        reviewAxes.target=self
        reviewAxes.toolTip="Up/down goes next; side-to-side goes previous. Replaces review circles and flicks."
        settings.addItem(reviewAxes);reviewAxisMenuItem=reviewAxes
        let parent=NSMenuItem(title:"Options",action:nil,keyEquivalent:"");parent.submenu=settings;menu.addItem(parent)
        item.menu=menu;statusItem=item
    }
    func changeOption(_ key:String) {
        do {try options.set(key,!options.enabled(key));refreshFeatureFlags();status();log("OPTION_CHANGED",key,options.enabled(key))}
        catch {connectionMenuItem?.title="Couldn’t save option";log("OPTION_SAVE_FAILED",key,error)}
    }
    func selectControlVersion(_ version:WandControlVersion) {
        do {try options.setValue("controlVersion",version.rawValue);refreshFeatureFlags();status();log("CONTROL_VERSION",version.rawValue)}
        catch {connectionMenuItem?.title="Couldn’t save option";log("OPTION_SAVE_FAILED",error)}
    }
    @objc func selectControlV1(){selectControlVersion(.pointerV1)}
    @objc func selectControlV2(){selectControlVersion(.scrollV2)}
    @objc func selectControlV3(){selectControlVersion(.sustainedV3)}
    @objc func toggleFlickScroll(){changeOption("flickScroll")}
    @objc func toggleRotation(){changeOption("orientationCompensation")}
    @objc func togglePointerFiltering(){
        do {try options.setValue("sensePointer",motionFilter.path == .tuned ? "direct" : "tuned");refreshFeatureFlags();status();log("OPTION_CHANGED","sensePointer",motionFilter.path.rawValue)}
        catch {connectionMenuItem?.title="Couldn’t save option";log("OPTION_SAVE_FAILED","sensePointer",error)}
    }
    @objc func toggleReviewAxes(){changeOption("reviewAxisGestures")}
    // Developer maintenance uses the existing BLE owner, so diagnosis and small
    // device updates do not disconnect the user's working pointer. Only consume
    // a same-user regular file with private permissions; never follow symlinks.
    func maintenance() {
        guard !restoring,isSense ? senseVirtual != nil : device?.state == .connected && tx != nil else {log("MAINTENANCE_NOT_READY");return}
        let path=support.appendingPathComponent("maintenance.js").path
        let fd=open(path,O_RDONLY|O_NOFOLLOW)
        guard fd>=0 else{return}
        defer{close(fd)}
        var metadata=stat()
        guard fstat(fd,&metadata)==0, metadata.st_uid==geteuid(), metadata.st_mode & S_IFMT == S_IFREG,
              metadata.st_mode & 0o077 == 0, metadata.st_size>0,metadata.st_size<=32768 else{log("MAINTENANCE_REJECTED");return}
        var data=[UInt8](repeating:0,count:Int(metadata.st_size))
        let count=read(fd,&data,data.count)
        guard count==data.count,let command=String(bytes:data,encoding:.utf8) else{return}
        unlink(path);log("MAINTENANCE_QUEUED",count)
        let marker="// WAND_BRIDGE_UPDATE\n"
        if command.hasPrefix("// WAND_PATCH\n") {
            ready=false;loadingBridge=true;bridgeLoadFailed=false;status();deadline(seconds:60)
            // Quiet and pace each complete statement, as in the normal bridge loader.
            for line in command.dropFirst("// WAND_PATCH\n".count).split(separator:"\n") {queue(String(line))}
            queue("print('WAND_MODE_ROUTING_READY');")
        } else if command.hasPrefix(marker) {
            let code=String(command.dropFirst(marker.count))
            let previous=modeBridge
            let value=["runtime":runtimeVersion,"build":receiverBuild,"code":code]
            guard let encoded=try? JSONSerialization.data(withJSONObject:value) else{return}
            do {try encoded.write(to:bridgeCache,options:.atomic);try FileManager.default.setAttributes([.posixPermissions:0o600],ofItemAtPath:bridgeCache.path)}
            catch {log("BRIDGE_CACHE_FAILED",error);return}
            log("BRIDGE_CACHE_SAVED",bridgeRevision(code))
            if code != previous {loadModeBridge(code)}
        } else {queue(command)}
    }
    func status() {
        connectionMenuItem?.title=ready ? (actionPause.paused ? "Connected · Wand actions paused" : "Connected") : "Connecting…"
        let traceState=reviewTrace.status
        let key = "\(isSense)|\(senseTransport?.rawValue ?? "")|\(deviceConnected)|\(ready)|\(AXIsProcessTrusted())|\(CBCentralManager.authorization.rawValue)|\(recording.isRecording)|\(lightMode)|\(deskSleep.sleeping)|\(controlVersion.rawValue)|\(flickScrollEnabled)|\(reviewAxisEnabled)|\(motionFilter.orientationCompensation)|\(traceState["enabled"] ?? false)|\(traceState["diskError"] ?? false)|\(actionPause.paused)|\(actionPause.lastRequest ?? "")|\(motionFilter.path.rawValue)"
        // The update result can change while every ordinary connection field
        // stays the same. Derive the write key from the exact published value.
        let firmwareStatus: [String: Any] = isSense ? senseUpdateStatus : [:]
        let firmwareStatusData = (try? JSONSerialization.data(withJSONObject: firmwareStatus, options: [.sortedKeys])) ?? Data()
        let batteryKey=key+"|"+String(batterySampleAt?.timeIntervalSince1970 ?? 0)+"|"+String(guide?.visible ?? false)+(guide?.lastRequest ?? "")+"|"+(clickGate ?? "")+String(decoding:firmwareStatusData,as:UTF8.self)
        guard batteryKey != lastStatusKey else { return }
        lastStatusKey = batteryKey
        var value: [String: Any] = ["pid": ProcessInfo.processInfo.processIdentifier, "connected": deviceConnected,
            "device": isSense ? "sense" : "puck", "transport": senseTransport?.rawValue ?? (device?.state == .connected ? "Bluetooth" : ""),
            "motionSensor": isSense ? (senseInfo?.motion ?? false) : true,
            "ready": ready, "options":["controlVersion":controlVersion.rawValue,"flickScroll":flickScrollEnabled,"reviewAxisGestures":reviewAxisEnabled,"orientationCompensation":motionFilter.orientationCompensation], "recording":recording.isRecording,"deskSleeping":deskSleep.sleeping, "lightMode":lightMode, "accessibility": AXIsProcessTrusted(), "bluetoothAuthorization": CBCentralManager.authorization.rawValue,
            "reviewTrace":traceState,
            // The debug pause's actual state; the dashboard only displays this.
            "actionsPaused":actionPause.paused,
            // The ordinary pointer conversion actually in use (WandPointerPath).
            "pointerPath":motionFilter.path.rawValue,
            "updatedAt": ISO8601DateFormatter().string(from: Date())]
        if let since=actionPause.since {value["actionsPausedAt"]=since.timeIntervalSince1970}
        if let request=actionPause.lastRequest {value["actionsRequest"]=request}
        // The instruction panel's actual visibility; an agent's request id once applied.
        value["guideVisible"]=guide?.visible ?? false
        // Why stop-to-click is blocked right now, and the HUD session behind it.
        value["clickGate"]=clickGate ?? "open"
        value["hudSession"]=hudSession
        if let request=guide?.lastRequest {value["guideRequest"]=request}
        if isSense {value["senseFirmwareUpdate"]=firmwareStatus}
        if let percent=batteryPercent,let volts=batteryVolts,let measured=batterySampleAt {
            value["battery"]=["percent":percent,"volts":volts,"measuredAt":measured.timeIntervalSince1970]
        }
        if let data = try? JSONSerialization.data(withJSONObject: value, options: [.sortedKeys]) { try? data.write(to: support.appendingPathComponent("status.json"), options: .atomic) }
    }
    /// The Puck's own CR2032 voltage estimate, using the existing connection.
    /// Querying built-in functions adds no firmware helper or second BLE owner.
    func requestBattery() {
        guard ready,!restoring,!deskSleep.deepSleeping,Date().timeIntervalSince(batteryRequested)>=60 else{return}
        batteryRequested=Date()
        queue("print('WAND_BATTERY '+JSON.stringify({percent:E.getBattery(),volts:NRF.getBattery()}));")
    }
    func handleBattery(_ payload:String) {
        guard let data=payload.data(using:.utf8),let v=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],
              let number=v["percent"] as? NSNumber,CFGetTypeID(number) != CFBooleanGetTypeID(),
              number.doubleValue.rounded()==number.doubleValue,let volts=v["volts"] as? Double,
              let percent=Int(exactly:number.doubleValue),
              (0...100).contains(percent),volts.isFinite,(1...5).contains(volts) else{return}
        batteryPercent=percent;batteryVolts=volts;batterySampleAt=Date()
        log("BATTERY",percent,String(format:"%.3f",volts));status()
    }
    func centralManagerDidUpdateState(_ c: CBCentralManager) {
        log("RADIO_STATE", c.state.rawValue)
        status()
        guard !isSense else { return } // The Sense link owns its own Bluetooth fallback.
        if c.state == .poweredOn { connect() }
        else { reset(); device = nil; status() }
    }
    func connect() {
        if isSense {
            guard !CommandLine.arguments.contains("--permissions-only"), AXIsProcessTrusted(), !restoring else { return }
            startSense(); return
        }
        guard !CommandLine.arguments.contains("--permissions-only"), deviceSettings.isConfigured, AXIsProcessTrusted(), !restoring, manager.state == .poweredOn, device == nil, !commands.isEmpty else { return }
        guard finishLegacyHandover() else { return }
        retry?.cancel(); manager.stopScan()
        if let target, let p = manager.retrievePeripherals(withIdentifiers: [target]).first { begin(p) }
        else { log("SCANNING_FOR_PUCK"); manager.scanForPeripherals(withServices: [uart]) }
    }
    func finishLegacyHandover() -> Bool {
        let file = support.appendingPathComponent("legacy-handover.json")
        guard let data = try? Data(contentsOf: file),
              let record = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let pid = record["pid"] as? Int32, let expected = record["executable"] as? String else { return true }
        var path = [CChar](repeating: 0, count: 4096)
        let length = proc_pidpath(pid, &path, UInt32(path.count))
        let actual = length > 0 ? String(cString: path) : ""
        guard actual == expected, URL(fileURLWithPath: actual).lastPathComponent == "wand-mac-receiver" else {
            try? FileManager.default.removeItem(at: file); log("LEGACY_HANDOVER_COMPLETE"); return true
        }
        if !legacySignaled {
            legacySignaled = true; log("STOPPING_LEGACY_RECEIVER", pid)
            if kill(pid, SIGTERM) != 0 { log("LEGACY_STOP_FAILED", errno) }
        }
        return false
    }
    func centralManager(_ c: CBCentralManager, didDiscover p: CBPeripheral, advertisementData: [String: Any], rssi RSSI: NSNumber) {
        let name = (advertisementData[CBAdvertisementDataLocalNameKey] as? String) ?? p.name ?? ""
        guard p.identifier == target || deviceSettings.matches(name: name) else { return }
        c.stopScan(); begin(p)
    }
    func begin(_ p: CBPeripheral) {
        guard !restoring, device == nil else { return }
        device = p; p.delegate = self; manager.connect(p)
        log("CONNECTING", p.identifier); deadline(seconds: 30)
    }
    func deadline(seconds: Double) {
        generation += 1; let token = generation
        DispatchQueue.main.asyncAfter(deadline: .now() + seconds) { [weak self] in
            guard let self, self.generation == token, !self.ready, !self.restoring else { return }
            log("CONNECTION_TIMEOUT"); self.reconnect()
        }
    }
    func reset() {
        cancelMouseExitClick()
        powerPolicyReady=false;loadingPowerPolicy=false;batteryRequested=Date.distantPast
        reviewTrace.boundary("receiver reset",mode:wandShortcutMode)
        reviewExitTimer?.invalidate();reviewExitTimer=nil;reviewExitGesture.reset();hudButtonReviewExit=false
        heldSafetyTimer?.invalidate();heldSafetyTimer=nil;finishNativeScroll(cancelled:true);heldScroll.reset();heldScrollAnchor=nil
        flickScroll.reset();flickAnchor=nil
        sendReview(review.cancel());appMode=nil;reviewTimer?.invalidate();reviewTimer=nil;hudButtonLastRelease = -100;hudButtonDoubleConsumed=false
        wandShortcutMode=nil;wandShortcutCircle.reset()
        dwell.follow(false);dwellTimer?.invalidate();dwellTimer=nil
        probeTimer?.invalidate();probeTimer=nil;restDetection.reset(keepingReference:true);deskSleep.reset();restFollow.reset()
        recenterGesture.cancel();recenterSuppressButtons=false;performPointer(pointerRouter.cancelAll());setCircleLight(false)
        pendingRecenter?.invalidate();pendingRecenter=nil;tripleClick.cancel();clickFollowChoice=nil
        endScreenshot(reason:"receiver reset",contextActive:screenshotActive,forgetPress:true)
        lightMode="disconnected"
        hudSession=false;hudEntryPress=false
        finishScroll()
        controls.cancel(); hudActive = false; hudWatchdog?.invalidate(); hudWatchdog = nil
        generation += 1; hudButtonHold?.invalidate();hudButtonTap?.invalidate();hudButtonHold=nil;hudButtonTap=nil;hudButtonClosedTap=false;hudButtonOperating=false;pointerInHUD=false;hudButtonHeld=false;controls.persistent("dismiss");releaseButtons(); ready = false; tx = nil; chunks = []; input = ""; writing = false; configuring = false; uartPaused = false
    }
    func reconnect() {
        if isSense { senseLink?.drop("receiver deadline"); endSenseSession(); return }
        if let p = device { manager.cancelPeripheralConnection(p) }
        reset(); device = nil; status()
        retry?.cancel()
        let item = DispatchWorkItem { [weak self] in self?.connect() }; retry = item
        // Button-wake standby must be ready to reconnect promptly; active
        // movement timing is unchanged.
        DispatchQueue.main.asyncAfter(deadline: .now() + (standbyResume == nil ? 3 : 0.2), execute: item)
    }
    func centralManager(_ c: CBCentralManager, didConnect p: CBPeripheral) {
        guard device === p, !restoring else { c.cancelPeripheralConnection(p); return }
        loadingRuntime=false;bridgeLoadFailed=false;log("CONNECTED_TO_PUCK"); deadline(seconds: 60); status(); p.discoverServices([uart])
    }
    func centralManager(_ c: CBCentralManager, didFailToConnect p: CBPeripheral, error: Error?) {
        guard device === p else { return }; log("CONNECT_FAILED", error?.localizedDescription ?? "unknown"); reconnect()
    }
    func centralManager(_ c: CBCentralManager, didDisconnectPeripheral p: CBPeripheral, error: Error?) {
        guard device === p else { return }; log("DISCONNECTED", error?.localizedDescription ?? "cleanly")
        if restoring { exit(0) }; reconnect()
    }
    func peripheral(_ p: CBPeripheral, didDiscoverServices error: Error?) {
        guard device === p else { return }
        guard error == nil, let s = p.services?.first(where: { $0.uuid == uart }) else { log("UART_UNAVAILABLE"); reconnect(); return }
        p.discoverCharacteristics([CBUUID(string: "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"), CBUUID(string: "6E400003-B5A3-F393-E0A9-E50E24DCCA9E")], for: s)
    }
    func peripheral(_ p: CBPeripheral, didDiscoverCharacteristicsFor s: CBService, error: Error?) {
        guard device === p else { return }
        guard error == nil else { reconnect(); return }
        for c in s.characteristics ?? [] {
            if c.uuid.uuidString.hasPrefix("6E400002") { tx = c }
            if c.uuid.uuidString.hasPrefix("6E400003") { p.setNotifyValue(true, for: c) }
        }
    }
    func peripheral(_ p: CBPeripheral, didUpdateNotificationStateFor c: CBCharacteristic, error: Error?) {
        guard device === p else { return }
        guard error == nil, c.isNotifying else { log("NOTIFY_FAILED"); reconnect(); return }
        guard !configuring else { return }; configuring = true
        let acknowledged=p.maximumWriteValueLength(for:.withResponse)
        let unacknowledged=p.maximumWriteValueLength(for:.withoutResponse)
        log("UART_WRITE_LIMIT",WandUART.payloadLimit(acknowledged:acknowledged,unacknowledged:unacknowledged),"acknowledged",acknowledged,"unacknowledged",unacknowledged)
        // One-shot local recovery: start from saved flash before loading a bridge.
        // A fresh connection is needed when memory exhaustion left UART XOFF stuck.
        let resetPath=support.appendingPathComponent("reload-on-connect").path
        var resetInfo=stat()
        if lstat(resetPath,&resetInfo)==0,resetInfo.st_uid==geteuid(),
           resetInfo.st_mode & S_IFMT == S_IFREG,resetInfo.st_mode & 0o077 == 0 {
            unlink(resetPath);log("RELOADING_SAVED_PROGRAM")
            queue("\u{03}\u{03}\n\u{10}load();")
            DispatchQueue.main.asyncAfter(deadline:.now()+2){[weak self] in
                guard let self,self.device === p,!self.ready,!self.restoring else{return}
                self.reconnect()
            }
            return
        }
        startRuntimeHandshake()
    }
    /// Extraction of the existing Puck runtime handshake, unchanged, shared by
    /// the Puck connection and the Sense profile's virtual Puck.
    func startRuntimeHandshake() {
        log("CHECKING_RUNTIME", runtimeVersion)
        let handshake = "if(global.WAND_RUNTIME_VERSION===\"" + runtimeVersion + "\"){if(!global.wandBridgeOriginalSend)global.wandBridgeOriginalSend=mouse.send;mouse.send=function(x,y,b,cb){Bluetooth.println(\"@WAND \"+x+\",\"+y+\",\"+b);if(cb)cb();};if(!connected)onConnect();print(\"WAND_BRIDGE_READY\");}else print(\"WAND_NEEDS_CONFIG\");"
        // An interrupted prior UART write can leave a partial REPL expression.
        // Cancel only that input before the handshake; keep saved code and calibration.
        // Loading blinks orange until ready; an older saved program shows steady orange.
        queue("\u{03}\u{03}\n\u{10}global.WAND_UPDATING=true;if(typeof loadingLight==='function')loadingLight();else if(typeof writeLight==='function'){writeLight(LED1,0.45);writeLight(LED2,0.45);writeLight(LED3,0.45);}" )
        queue(handshake)
    }
    func queue(_ command: String) {
        // Sense profile: the same JS commands go to the canonical program on the Mac.
        if isSense { senseVirtual?.send(command); return }
        chunks += WandUART.packets(command,
            acknowledged:device?.maximumWriteValueLength(for:.withResponse) ?? 0,
            unacknowledged:device?.maximumWriteValueLength(for:.withoutResponse) ?? 0)
        sendNext()
    }
    func sendNext() {
        guard !writing, !uartPaused, let p = device, p.state == .connected, let characteristic = tx, !chunks.isEmpty else { return }
        writing = true; p.writeValue(chunks.removeFirst(), for: characteristic, type: .withResponse)
    }
    func peripheral(_ p: CBPeripheral, didWriteValueFor c: CBCharacteristic, error: Error?) {
        guard device === p else { return }
        if let error {writing=false;log("WRITE_FAILED",error.localizedDescription);reconnect();return}
        // A GATT acknowledgement precedes the Puck parsing a large code fragment.
        // Pace installation only: FIFO_FULL otherwise drops bytes inside functions.
        if !ready || loadingPowerPolicy {
            DispatchQueue.main.asyncAfter(deadline:.now()+0.01){[weak self] in
                guard let self,self.device === p,!self.restoring else{return}
                self.writing=false;self.sendNext()
            }
        } else {writing=false;sendNext()}
    }
    func peripheral(_ p: CBPeripheral, didUpdateValueFor c: CBCharacteristic, error: Error?) {
        guard device === p,error == nil,let bytes=c.value else{return}
        // Espruino sends XOFF while parsing code and XON when its UART can accept
        // more bytes. A BLE acknowledgement alone is not this permission.
        for byte in bytes {
            if byte==0x13 {uartPaused=true}
            else if byte==0x11 {uartPaused=false}
        }
        sendNext()
        guard let text=String(data:Data(bytes.filter{$0 != 0x11 && $0 != 0x13}),encoding:.utf8) else{return}
        receiveText(text)
    }
    /// Extraction of the existing Puck UART line handler, unchanged, so the
    /// Sense profile's virtual Puck output reaches exactly the same code.
    func receiveText(_ text:String) {
        deliveryPoint=currentPointerOrigin()
        defer {deliveryPoint=nil}
        input += text.replacingOccurrences(of: "\r", with: "")
        if input.count > 16384 { input = String(input.suffix(4096)) }
        while let newline = input.firstIndex(of: "\n") {
            let line = String(input[..<newline]); input.removeSubrange(...newline)
            if line.contains("Error") || line.contains("OUT OF MEMORY") || line.contains("Uncaught") { log("DEVICE_ERROR", line) }
            // Source echo may contain the word Error. Only actual runtime failures
            // invalidate a bridge load; a later ready marker cannot hide one.
            if (loadingBridge || loadingRuntime) && (line.contains("Uncaught ") || line.contains("OUT OF MEMORY") || line == "WAND_UPDATE_FAILED" || line == ">WAND_UPDATE_FAILED") {
                bridgeLoadFailed=true;ready=false;lightMode="update";status()
            }

            if line == "WAND_NEEDS_CONFIG" || line == ">WAND_NEEDS_CONFIG" {
                guard !loadingRuntime else {continue}
                loadingRuntime=true;bridgeLoadFailed=false
                log("UPLOADING_RUNTIME", commands.count); for command in commands { queue(command) }
            }
            if line.hasPrefix("WAND_BRIDGE_READY") || line.hasPrefix(">WAND_BRIDGE_READY") {
                guard !bridgeLoadFailed else {log("RUNTIME_LOAD_REJECTED");continue}
                loadingRuntime=false
                queue("E.setFlags({pretokenise:1});global.wandDoubleClickSeconds="+String(min(0.3,NSEvent.doubleClickInterval))+";if(global.WAND_BRIDGE_REVISION==='"+bridgeRevision(modeBridge)+"'&&global.wandMotionReady!==false)print('WAND_MODE_ROUTING_READY');else print('WAND_PATCH_NEEDED');")
            }
            if line == "WAND_PATCH_NEEDED" || line == ">WAND_PATCH_NEEDED" {loadModeBridge()}
            if line == "WAND_MODE_ROUTING_READY" || line == ">WAND_MODE_ROUTING_READY" {
                guard !bridgeLoadFailed else {queue("global.WAND_UPDATING=true;global.wandMotionReady=false;updateLights();");log("BRIDGE_LOAD_REJECTED");continue}
                loadingBridge=false;loadingRuntime=false;ready=true;motionFilter.reset();rawLastArrival=0;generation+=1;log("RUNTIME_READY");syncRecordingLight();status()
                restoreKnownCalibration();checkPowerPolicy()
                requestBattery()
                if let remembered=standbyResume {let resume=remembered && !recording.isRecording;standbyResume=nil;queue("setMouseFollow("+(resume ? "true":"false")+");");dwell.follow(resume);log("DEEP_STANDBY_RESUMED",resume)}
                if context.isActive {hudSession=true;hudOpenedAt=ProcessInfo.processInfo.systemUptime}
                if let mode=selectedReviewMode {setWandShortcut(mode)}
                queue("global.wandShot=0;global.wandRawPointer=true;global.wandRawBias=undefined;global.wandRawActive=false;global.WAND_UPDATING=false;setHUDOpen("+(context.isActive ? "true":"false")+");updateLights();")
                queue("global.wandHostHeldScroll="+(controlVersion.usesHeldScroll ? "true":"false")+";")
            }
            if line.hasPrefix("WAND_DIAG ") || line.hasPrefix(">WAND_DIAG ") || line.hasPrefix("WAND_CALLBACK_MATCH ") || line.hasPrefix(">WAND_CALLBACK_MATCH ") {log("DEVICE",line)}
            if line.hasPrefix("WAND_BATTERY ") || line.hasPrefix(">WAND_BATTERY "),let range=line.range(of:"WAND_BATTERY ") {handleBattery(String(line[range.upperBound...]))}
            if line.hasPrefix("WAND_BUTTON_STATE ") || line.hasPrefix(">WAND_BUTTON_STATE ") {log("DEVICE",line)}
            if let marker=line.range(of:"WAND_LIGHT_STATE ") {
                let payload=String(line[marker.upperBound...])
                let mode=String(payload.prefix{!$0.isWhitespace})
                if ["update","calibration","disconnected","sleep","scroll","app","mouse","hud","recording","idle"].contains(mode),
                   let first=payload.firstIndex(of:"["),let last=payload[first...].firstIndex(of:"]"),
                   let levels=try? JSONDecoder().decode([Double].self,from:Data(payload[first...last].utf8)),levels.count==3 {
                    lightMode=mode;log("DEVICE_LIGHT",mode,levels);status()
                }
            }
            if line.hasSuffix("WAND_RECORDING_LIGHT 0") || line.hasSuffix("WAND_RECORDING_LIGHT 1") {log("DEVICE",line)}
            // Debug pause: telemetry and status lines continue; action lines stop here.
            let paused=actionPause.paused
            if line.hasSuffix("@POINTER_MODE"), !paused {manualPointerDuringRecording();enterPointerMode()}
            if let marker=line.range(of:"@FOLLOW "), !paused {
                let value=line[marker.upperBound...].trimmingCharacters(in:.whitespaces)
                if value=="0" || value=="1" {deviceFollowChanged(value=="1")}
            }
            if let marker=line.range(of:"@ZERO "),let data=String(line[marker.upperBound...]).data(using:.utf8),let config=try? JSONDecoder().decode([Double].self,from:data) {log("NATIVE_MOTION_CONFIG",motionFilter.configure(config))}
            if let marker=line.range(of:"@RAW "), !paused {handleRaw(String(line[marker.upperBound...]))}
            if let marker=line.range(of:"@IMU ") {handleIMU(String(line[marker.upperBound...]))}
            // Legacy held app-page packets never own a selected persistent review set.
            if let marker=line.range(of:"@REVIEW "),!paused,appMode=="vsCode",selectedReviewMode==nil {
                let value=line[marker.upperBound...].trimmingCharacters(in:.whitespaces)
                if value=="0" || value=="1" {
                    if value=="1" {reviewOriginY=navY;if hudActive {controls.persistent("park");hudActive=false;stopHUDWatchdog()}}
                    let wasFiles=review.files
                    sendReview(review.button(down:value=="1",now:ProcessInfo.processInfo.systemUptime))
                    if value=="0" {resumeHUDNavigation()}
                    if wasFiles != review.files {queue("global.wandReviewFiles="+(review.files ? "true":"false")+";updateLights();");log("VSCODE_REVIEW_MODE",review.mode)}
                    if reviewTimer==nil {reviewTimer=WandRunLoop.commonTimer(interval:0.2,repeats:true){[weak self] _ in guard let self else{return};self.sendReview(self.review.tick(now:ProcessInfo.processInfo.systemUptime))}}
                }
            }
            if line.contains("WAND_CALIBRATED") { log(line);rememberCalibration(line) }
            if line=="WAND_POWER_POLICY_READY" || line==">WAND_POWER_POLICY_READY" {loadingPowerPolicy=false;powerPolicyReady=true;log("POWER_POLICY_READY")}
            if line=="WAND_POWER_POLICY_NEEDED" || line==">WAND_POWER_POLICY_NEEDED" {if !loadingPowerPolicy {loadPowerPolicy()}}
            if loadingPowerPolicy && line.contains("Uncaught ") {loadingPowerPolicy=false;powerPolicyReady=false;log("POWER_POLICY_FAILED")}
            if line=="WAND_POWER_STANDBY_DENIED" || line==">WAND_POWER_STANDBY_DENIED" {standbyResume=nil}
            if line=="WAND_POWER_STANDBY_CANCELLED" || line==">WAND_POWER_STANDBY_CANCELLED" {standbyResume=nil;log("DEEP_STANDBY_CANCELLED")}
            if line=="WAND_POWER_STANDBY_ENTERED" || line==">WAND_POWER_STANDBY_ENTERED" {log("DEEP_STANDBY_ENTERED")}
            // Wire names are unchanged for compatibility with the saved firmware:
            // @BOTTOM is the mouse button, @MIDDLE the HUD button, @STT the speech button.
            if let marker=line.range(of:"@BOTTOM ") {
                let value=String(line[marker.upperBound...]).trimmingCharacters(in:.whitespaces)
                // The device prints each edge before the click it emits on release,
                // so a consumed (scrolled) hold's endpoint click is dropped by order.
                if value=="0" || value=="1" {
                    guard actionPause.admit(.mouseButton,down:value=="1") else {continue}
                    if screenshotMouseButton(down:value=="1",now:ProcessInfo.processInfo.systemUptime) {continue}
                    if value=="1" {
                        if !scrollActive && !heldScroll.active {scrollFollowBefore=dwell.following}
                        manualPointerDuringRecording()
                    }
                    // Finish the physical release before double-click recognition consumes it.
                    // The exit click waits for that recognition; follow stops immediately.
                    if controlVersion.usesHeldScroll && value=="0" {finishMouseButtonHold(now:ProcessInfo.processInfo.systemUptime)}
                    if recognizeMouseButtonRecenter(down:value=="1",now:ProcessInfo.processInfo.systemUptime) {continue}
                    if controlVersion.usesHeldScroll && !scrollActive {
                        if value=="1" {
                            beginMouseButtonHold(now:ProcessInfo.processInfo.systemUptime,following:scrollFollowBefore)
                            if heldScroll.resolving {probeHoldTarget(at:heldScrollAnchor ?? .zero,token:heldTargetToken)}
                        }
                    }
                    if value=="1" && flickScroll.active {flickScroll.reset();flickAnchor=nil;setCircleLight(false);motionFilter.reset()}
                    let endedLegacyScroll=value=="0" && pointerRouter.circle.active
                    dwell.reset();scheduleDwell();performPointer(pointerRouter.mouseButton(down:value=="1"))
                    if endedLegacyScroll {restoreMouseAfterScroll()}
                }
            }
            if let marker=line.range(of:"@MIDDLE "){
                let value=String(line[marker.upperBound...])
                if actionPause.admit(.hudButton,down:value.trimmingCharacters(in:.whitespaces)=="1") {handleHUDButton(value)}
            }
            if let marker=line.range(of:"@NAV "), !paused {handleNavigation(String(line[marker.upperBound...]))}
            if let marker = line.range(of: "@SCROLL "), !paused { handleScroll(String(line[marker.upperBound...])) }
            if let marker = line.range(of: "@MOVE "), !paused { handleMove(String(line[marker.upperBound...])) }
            if let marker = line.range(of: "@HUD "), !paused { handleHUD(String(line[marker.upperBound...])) }
            if let marker = line.range(of: "@STT "), !restoring, AXIsProcessTrusted() {
                let value=String(line[marker.upperBound...]).trimmingCharacters(in: .whitespaces)
                // Paused: nothing reaches Agent Flow, so a running recording keeps going.
                if value == "0" || value == "1" {
                    guard actionPause.admit(.speechButton,down:value=="1") else {log("SPEECH_BUTTON",value,"PAUSED");continue}
                    log("SPEECH_BUTTON", value, controls.speech(down:value == "1") ? "SENT" : "UNAVAILABLE")
                }
            }
            if let marker = line.range(of: "@WAND "), !paused { handle(String(line[marker.upperBound...])) }
            if restoring && line.contains("WAND_BRIDGE_RESTORED") { log("STOPPED"); exit(0) }
        }
    }
    // Legacy @MOVE card operation. The HUD button itself now uses the hold-to-show
    // lifecycle in handleHUDButton: hold steers, release uses the card.
    var hudDoubleClickInterval:Double {max(0.25,min(0.3,NSEvent.doubleClickInterval))}
    func handleMove(_ payload:String,project:Bool=true) {
        guard !restoring,!scrollActive,AXIsProcessTrusted() else{return}
        let f=payload.split(separator:",",omittingEmptySubsequences:false)
        guard f.count==3,let x=Double(f[1]),let y=Double(f[2]),x.isFinite,y.isFinite,abs(x)<=7_200_000,abs(y)<=7_200_000 else{return}
        guard hudSession else{return}
        if f[0]=="B" {moveStream.reset()}
        let point=project ? moveStream.update(x:x/1000,y:y/1000,using:motionFilter) : (x:x/1000,y:y/1000)
        hudButtonX=point.x;hudButtonY=point.y
        switch f[0] {
        case "B":
            if hudButtonTap != nil {
                hudButtonTap?.invalidate();hudButtonTap=nil
                hudButtonHold?.invalidate();hudButtonHold=nil
                closeHUD(reason:"middle double click")
                return
            }
            guard context.isActive || hudSession else{return}
            pointerInHUD=true;hudButtonOperating=false
            hudButtonSecondTap=false
            hudButtonHold=WandRunLoop.commonTimer(interval:0.22,repeats:false){[weak self] _ in
                guard let self,self.pointerInHUD,(self.context.isActive || self.hudSession) else{return}
                self.hudButtonOperating=true;self.controls.persistent("press")
                self.controls.persistent("motion",x:self.hudButtonX,y:self.hudButtonY)
            }
            startHUDWatchdog()
        case "U":
            guard pointerInHUD else{return};hudLastUpdate=Date()
            if hudButtonOperating {controls.persistent("motion",x:hudButtonX,y:hudButtonY)}
        case "E":
            guard pointerInHUD else{return};pointerInHUD=false
            hudButtonHold?.invalidate();hudButtonHold=nil;stopHUDWatchdog()
            if hudButtonOperating {controls.persistent("motion",x:hudButtonX,y:hudButtonY);controls.persistent("release");resumeHUDNavigation()}
            else {
                hudButtonTap=WandRunLoop.commonTimer(interval:hudDoubleClickInterval,repeats:false){[weak self] _ in
                    guard let self else{return};self.hudButtonTap=nil
                    guard self.hudSession,self.acceptHUDContext,self.context.isActive,!self.restoring else{return}
                    self.controls.persistent("activate");self.resumeHUDNavigation()
                }
            }
            hudButtonOperating=false
        default:break
        }
    }
    /// Close the entire wand session, including delayed clicks and app-specific state.
    /// Ignore stale positive heartbeats until a fresh physical HUD button press opens it.
    /// `notifyNative` is false when Agentic Mouse itself closed the HUD.
    func closeHUD(reason:String,notifyNative:Bool=true) {
        finishWandShortcut(commit:false)
        // An explicit close is newer than a waiting review tap: it never exits later.
        if notifyNative {cancelReviewTap("HUD closed")}
        hiddenReviewPending=false;hiddenReviewOperating=false
        screenshotHUD=false
        acceptHUDContext=false
        sendReview(review.cancel());appMode=nil;reviewTimer?.invalidate();reviewTimer=nil
        hudSession=false;hudEntryPress=false;hudActive=false;pointerInHUD=false;hudButtonOperating=false;navigationOpenedHUD=false;hudButtonHeld=false
        hudButtonTap?.invalidate();hudButtonTap=nil;hudButtonHold?.invalidate();hudButtonHold=nil;hudButtonClosedTap=false
        stopHUDWatchdog();if notifyNative {controls.persistent("dismiss")}
        queue("global.wandAppMode=undefined;setHUDOpen(false);updateLights();")
        log("HUD_CLOSED",reason)
    }
    /// Ethan (2026-10-30): "the HUD button, if I double click it, I think it
    /// should do the right mouse menu, like right click basically", starting
    /// from a closed HUD (an open HUD's double click still only closes it).
    /// One native right press and release at the pointer he sees, with mouse
    /// follow on or off and without moving or warping it. Never while the mouse button,
    /// a scroll, a native button or screenshot mode owns the pointer.
    func hudDoubleRightClick() {
        let blocker = screenshot.ownsPointer ? "screenshot" : pointerRouter.mouseButtonHeld || heldScroll.active ? "bottom held" :
            buttons != 0 ? "button down" : nil
        if let blocker {log("HUD_RIGHT_CLICK_SKIPPED",blocker);return}
        let point=deliveryPoint ?? currentPointerOrigin()
        transition(to:buttons|2,at:point);transition(to:buttons & ~2,at:point)
        log("HUD_RIGHT_CLICK")
    }
    func setScreenshotActive(_ active:Bool) {
        // Cancelling the screenshot tool must not carry its mouse-down into
        // the underlying app, even if the mouse button has not been released yet.
        if screenshotActive && !active {finishMouseButtonHold(now:ProcessInfo.processInfo.systemUptime,released:false)}
        screenshotActive=active
        screenshotContextChanged(active)
        if !active,screenshotHUD {
            screenshotHUD=false
            // Only a HUD Agentic Mouse still shows returns waiting. The HUD's
            // own Screenshot card hides it as a completed action, so its end
            // must leave no session behind: a restored ghost session blocked
            // every stop-to-click (2026-10-30, "it's straight up not clicking").
            // Screenshot mode never changed the mouse-follow choice.
            if context.isActive {
                hudSession=true;acceptHUDContext=true;hudOpenedAt=ProcessInfo.processInfo.systemUptime
                queue("setHUDOpen(true);")
            }
        }
    }
    /// Agentic Mouse's native selection started or ended. Its heartbeat repeats
    /// `true` without resetting progress; expiry or an end is a cancellation,
    /// never permission for an ordinary click in the app underneath.
    func screenshotContextChanged(_ active:Bool) {
        guard active else{endScreenshot(reason:"capture ended",contextActive:false);return}
        guard ready,!restoring,!actionPause.paused,screenshot.contextActive(now:ProcessInfo.processInfo.systemUptime,pressed:pointerRouter.mouseButtonHeld) else{return}
        takeScreenshotPointer(follow:"moveLatched")
        enterPointerMode()
        log("SCREENSHOT_MODE",screenshot.shortcut ? "shortcut":"selection")
    }
    /// Take the pointer from every ordinary mouse-button lane and ask the wand for
    /// HIGH motion even with mouse follow off. `setMouseFollow` here only
    /// clears the wand's mouse-button gesture; `follow` is the unchanged choice.
    func takeScreenshotPointer(follow:String) {
        cancelMouseExitClick()
        pendingRecenter?.invalidate();pendingRecenter=nil;tripleClick.cancel();recenterGesture.cancel()
        cancelCircleScroll();finishMouseButtonHold(now:ProcessInfo.processInfo.systemUptime,released:false)
        performPointer(pointerRouter.cancelAll());if buttons != 0 {releaseButtons()}
        motionFilter.reset();dwell.reset();scheduleDwell()
        queue("global.wandShot=1;setMouseFollow("+follow+");wakeGyro();")
        superviseScreenshot()
    }
    /// Mouse-button edges before every ordinary lane. Screenshot mode owns the mouse button
    /// outright; otherwise watch for Ethan's triple-click shortcut.
    /// Previously screenshotBottom.
    func screenshotMouseButton(down:Bool,now:Double)->Bool {
        if down {cancelMouseExitClick()}
        switch screenshot.mouseButton(down:down) {
        case .consumed: tripleClick.cancel();return true
        case .press: tripleClick.cancel();latchScreenshotIfReady();return true
        case .release: tripleClick.cancel();finishScreenshotDrag(reason:"Bottom release");return true
        case .pass: break
        }
        switch tripleClick.edge(down:down,now:now) {
        case .first: clickFollowChoice=(dwell.following,recordingPointerPaused,recordingRestoreFollow,restFollow)
        case .third: startScreenshotShortcut(now:now);return true
        case .none: break
        }
        // Any other press after a double click centres first, exactly as the
        // double click did before, then acts normally.
        if down,let waiting=pendingRecenter {waiting.invalidate();pendingRecenter=nil;recenterPointer()}
        return false
    }
    /// Ethan's mouse-button triple-click: start the ordinary native macOS selection.
    /// All three presses are consumed, cancelling any pending exit click and centre.
    /// The follow choice is restored. A fresh mouse-button press then drags the
    /// area like a mouse button and its release captures.
    func startScreenshotShortcut(now:Double) {
        cancelMouseExitClick()
        pendingRecenter?.invalidate();pendingRecenter=nil
        // Undo the first two clicks' follow and recording-override effects.
        if let choice=clickFollowChoice {
            dwell.follow(choice.following);recordingPointerPaused=choice.paused
            recordingRestoreFollow=choice.restore;restFollow=choice.rest
        }
        clickFollowChoice=nil
        let follow=dwell.following ? "true":"false"
        guard ready,!restoring,!scrollActive,AXIsProcessTrusted(),screenshot.phase == .idle,controls.screenshotStart() else {
            screenshot.holdRelease();queue("setMouseFollow("+follow+");")
            log("SCREENSHOT_SHORTCUT_UNAVAILABLE");return
        }
        _=screenshot.requestShortcut(now:now)
        takeScreenshotPointer(follow:follow)
        if screenshotActive {_=screenshot.contextActive(now:now,pressed:true);enterPointerMode()}
        log("SCREENSHOT_SHORTCUT")
    }
    /// One bounded supervisor while screenshot mode owns the pointer: native
    /// start, lost telemetry, and a mouse-button press made before the selector
    /// appeared. It never moves the pointer.
    func superviseScreenshot() {
        if screenshotTimer==nil {
            screenshotTimer=WandRunLoop.commonTimer(interval:0.05,repeats:true){[weak self] _ in self?.checkScreenshot()}
        }
        latchScreenshotIfReady()
    }
    func checkScreenshot() {
        guard screenshot.ownsPointer else{screenshotTimer?.invalidate();screenshotTimer=nil;return}
        if !ready || restoring {endScreenshot(reason:"receiver unavailable",contextActive:screenshotActive);return}
        if let reason=screenshot.expired(now:ProcessInfo.processInfo.systemUptime) {endScreenshot(reason:reason,contextActive:screenshotActive);return}
        latchScreenshotIfReady()
    }
    /// The mouse button is down: press the native button, but only once macOS's own
    /// selector is up; a press before it exists would click the app underneath.
    func latchScreenshotIfReady() {
        guard !actionPause.paused,screenshot.phase == .aiming,screenshot.pressHeld,AXIsProcessTrusted(),Self.screenshotSelectorVisible() else{return}
        let point=deliveryPoint ?? currentPointerOrigin()
        guard screenshot.latch(now:ProcessInfo.processInfo.systemUptime) else{return}
        transition(to:buttons|1,at:point)
        log("SCREENSHOT_DRAG_BEGIN",screenshot.shortcut ? "shortcut":"selection")
    }
    /// macOS's selected-area tracking surface, detected as Agentic Mouse does.
    static func screenshotSelectorVisible()->Bool {
        guard let windows=CGWindowListCopyWindowInfo([.optionAll,.excludeDesktopElements],kCGNullWindowID) as? [[String:Any]] else{return false}
        return windows.contains{$0[kCGWindowOwnerName as String] as? String == "screencapture"}
    }
    /// Screenshot motion: the same HIGH sensor-space calculation and gain as
    /// normal mouse follow. Mouse button down is only a click here, never LOW, and the
    /// wand's HUD-only flag is expected because follow may be off.
    func handleScreenshotRaw(_ v:[Int],now:Double) {
        screenshot.telemetry(now:now)
        guard !scrollActive,AXIsProcessTrusted() else{return}
        let gap=rawLastArrival>0 ? now-rawLastArrival : 0
        guard let sample=motionFilter.sample(rawX:v[1],rawY:v[2],microseconds:v[0],held:false,resetState:v[3]&2 != 0 || gap>0.25) else{return}
        rawLastArrival=now
        guard sample.x != 0 || sample.y != 0 else{return}
        let point=deliveryPoint ?? currentPointerOrigin()
        let moved=postPointerMove(dx:sample.x,dy:sample.y,from:point)
        if deliveryPoint != nil {deliveryPoint=moved}
    }
    func finishScreenshotDrag(reason:String) {
        guard screenshot.dragging else{return}
        endScreenshot(reason:reason,contextActive:screenshotActive)
    }
    /// Return the pointer: lift a latched native press (never a stuck
    /// leftDown), stop screenshot motion and keep the ordinary follow choice.
    func endScreenshot(reason:String,contextActive:Bool,forgetPress:Bool=false) {
        screenshotTimer?.invalidate();screenshotTimer=nil
        let owned=screenshot.ownsPointer
        if screenshot.end(contextActive:contextActive,forgetPress:forgetPress) {
            transition(to:buttons & ~1,at:deliveryPoint ?? currentPointerOrigin())
            log("SCREENSHOT_DRAG_END",reason)
        }
        guard owned else{return}
        motionFilter.reset();dwell.reset();scheduleDwell()
        if ready && !restoring {queue("global.wandShot=0;sleepGyro();")}
        log("SCREENSHOT_MODE_END",reason)
    }
    func enterPointerMode(){
        if screenshotActive && (hudSession || screenshotHUD) {
            screenshotHUD=true;controls.persistent("park");hudActive=false;hudSession=false
            pointerInHUD=false;hudButtonOperating=false;stopHUDWatchdog();queue("setHUDOpen(false);")
        } // The mouse button changes pointing only; it never closes the HUD or review owned by the HUD button.
        log("POINTER_MODE_ENTERED")
    }
    /// The HUD button's `@MIDDLE` edges (legacy wire name). Previously handleMiddle.
    func handleHUDButton(_ payload:String){
        guard !restoring,!scrollActive,AXIsProcessTrusted() else{return}
        switch payload.trimmingCharacters(in:.whitespaces){
        case "1":
            cancelMouseExitClick()
            let now=ProcessInfo.processInfo.systemUptime;hudButtonPressedAt=now
            // A new press proves any earlier release happened, even if its
            // edge never arrived (2026-10-29: a double click's lost release
            // swallowed the next hold's release and left the HUD button "held",
            // blocking the pointer). Start every press from a clean state.
            if hudButtonDoubleConsumed || hudButtonHeld {log("MIDDLE_RELEASE_RECOVERED")}
            hudButtonDoubleConsumed=false
            // A first tap whose double-click window already ended (its timer ran
            // late) exits now, exactly as on time, before this press is judged.
            if selectedReviewMode != nil,reviewExitGesture.expiredTap(now:now) {expireReviewTap()}
            if selectedReviewMode != nil {
                guard !reviewExitGesture.pending else{return}
                hudButtonReviewExit=true;hudButtonLastRelease = -100
                reviewExitTimer?.invalidate();reviewExitTimer=nil
                beginReviewCommitHold(now:now)
                return
            }
            if now-hudButtonLastRelease<=hudDoubleClickInterval {
                // Double click still dismisses, cancelling the first tap's pending use.
                // Started from a closed HUD it is Ethan's right click instead
                // (2026-10-30); its first press only showed the HUD, so close that.
                let rightClick=hudButtonClosedTap && hudButtonTap != nil
                hudButtonLastRelease = -100;hudButtonDoubleConsumed=true;hudButtonClosedTap=false
                hudButtonTap?.invalidate();hudButtonTap=nil;hudButtonHold?.invalidate();hudButtonHold=nil
                closeHUD(reason:rightClick ? "middle double click from closed" : "middle double click")
                if rightClick {hudDoubleRightClick()}
                return
            }
            let closedTapPending=hudButtonClosedTap;hudButtonClosedTap=false
            // A session Agentic Mouse no longer shows (it quit or lost the
            // lease) is stale: start a fresh HUD instead of steering nothing.
            if hudSession && !context.isActive && now-hudOpenedAt>1 {closeHUD(reason:"context missing",notifyNative:false);acceptHUDContext=true}
            if let pending=hudButtonTap {
                // A tap whose double-click window just ended: use it now, before
                // this new hold, rather than lose it to a late timer.
                pending.invalidate();hudButtonTap=nil
                if hudSession,acceptHUDContext,context.isActive || closedTapPending {controls.persistent("activate");log("HUD_TAP_USED")}
            }
            hudButtonHeld=true;hudButtonQualified=false;hudEntryPress=false
            hudButtonMouseX=0;hudButtonMouseSampleAt = -100
            if !hudSession {
                // Holding the HUD button shows the HUD and steers it from Switch App.
                acceptHUDContext=true;navStream.reset()
                hudSession=true;hudOpenedAt=now;navigationOpenedHUD=true;navX=0;navY=0
                controls.persistent("open");resumeHUDNavigation()
                queue("setHUDOpen(true);")
                return
            }
            // The HUD stayed open for more: steer its page, or adjust the card
            // the last release armed. Agentic Mouse knows which.
            resumeHUDNavigation()
        case "0":
            if hudButtonReviewExit {
                hudButtonReviewExit=false
                reviewExitTimer?.invalidate();reviewExitTimer=nil
                let now=ProcessInfo.processInfo.systemUptime
                // One short click exits unstaged once its double-click window
                // ends; a second short click toggles; a 0.5 s hold still stages.
                switch reviewExitGesture.up(now:now,window:hudDoubleClickInterval) {
                case .wait: scheduleReviewTapTimeout()
                case .toggle: requestReviewToggle(now:now)
                case .commit: commitSelectedReview()
                case .none: break
                }
                // Held movement is never replayed into the next working selection.
                wandShortcutCircle.reset()
                return
            }
            if hiddenReviewOperating {
                finishWandShortcut(commit:true);hiddenReviewOperating=false
                hudButtonHold?.invalidate();hudButtonHold=nil
                queue("setHUDOpen(false);");return
            }
            if hiddenReviewPending {
                hiddenReviewPending=false;hudButtonHold?.invalidate();hudButtonHold=nil
                // A tap reopens the main HUD without changing the selected review mode.
                acceptHUDContext=true;hudSession=true;hudEntryPress=false;navStream.reset();navX=0;navY=0
                controls.persistent("open");queue("setHUDOpen(true);");resumeHUDNavigation()
                hudButtonLastRelease=ProcessInfo.processInfo.systemUptime;return
            }
            // A bounced or duplicate release in a selected review set is not a
            // gesture: it must neither stage the set nor end a waiting tap.
            if selectedReviewMode != nil && !hudButtonHeld {hudButtonDoubleConsumed=false;return}
            finishWandShortcut(commit:true)
            // The double click's own release: it is still a release.
            if hudButtonDoubleConsumed {hudButtonDoubleConsumed=false;hudButtonHeld=false;hudButtonQualified=false;return}
            guard hudButtonHeld else{return}
            let openedByThisPress=navigationOpenedHUD
            hudButtonHeld=false;hudButtonQualified=false;navigationOpenedHUD=false
            // Firmware delays a held HUD-button down edge by 80 ms to arbitrate the scroll
            // chord, so under 140 ms here is a physical tap under 220 ms.
            let now=ProcessInfo.processInfo.systemUptime
            let tap=now-hudButtonPressedAt<hudHoldSeconds
            hudButtonLastRelease=tap ? now : -100
            if hudActive {
                hudLastUpdate=Date();controls.persistent("motion",x:navX-navOriginX,y:navY-navOriginY,mouseX:hudButtonMouseOffset)
                controls.persistent("park")
            }
            hudActive=false;stopHUDWatchdog()
            if tap && openedByThisPress {
                // Ethan: "when I just quickly tap the HUD button, it should just
                // instantly switch app". Then (2026-10-30): "the HUD button, if I
                // double click it, I think it should do the right mouse menu".
                // He approved this closed-HUD tap waiting up to 300 ms
                // (`hudDoubleClickInterval` is at most 0.3 s) so the first click
                // of that double click never switches apps. Holds, pointer
                // movement and an already open HUD are not delayed. Unlike the
                // open-HUD tap it never needed the HUD's first heartbeat.
                hudButtonClosedTap=true
                hudButtonTap=WandRunLoop.commonTimer(interval:hudDoubleClickInterval,repeats:false){[weak self] _ in
                    guard let self else{return};self.hudButtonTap=nil;self.hudButtonClosedTap=false
                    guard self.hudSession,self.acceptHUDContext,!self.restoring else{return}
                    self.controls.persistent("activate");log("HUD_TAP_USED")
                }
            } else if tap {
                // A tap uses the outlined card once the double-click window
                // passes, so a double click can still dismiss without acting.
                hudButtonTap=WandRunLoop.commonTimer(interval:hudDoubleClickInterval,repeats:false){[weak self] _ in
                    guard let self else{return};self.hudButtonTap=nil
                    guard self.hudSession,self.acceptHUDContext,self.context.isActive,!self.restoring else{return}
                    self.controls.persistent("activate");log("HUD_TAP_USED")
                }
            } else {
                // Releasing a hold uses the outlined card at once; a card that
                // needs more motion is armed for the next hold instead.
                controls.persistent("choose");log("HUD_HOLD_RELEASED")
                if !context.isActive && now-hudOpenedAt>1 {closeHUD(reason:"context missing",notifyNative:false)}
            }
        default:break
        }
    }
    func handleNavigation(_ payload:String){
        let f=payload.split(separator:",")
        guard f.count==2,let x=Double(f[0]),let y=Double(f[1]),x.isFinite,y.isFinite,abs(x)<=7_200_000,abs(y)<=7_200_000 else{return}
        let point=navStream.update(x:x/1000,y:y/1000,using:motionFilter)
        navX=point.x;navY=point.y
        if wandShortcutMode != nil {
            let now=ProcessInfo.processInfo.systemUptime
            let dx=navX-wandShortcutX,dy=navY-wandShortcutY
            wandShortcutX=navX;wandShortcutY=navY;wandShortcutTime=now
            // The mouse button retains its mouse gesture. Never interpret that held movement as review.
            // Review also holds still while one HUD button tap may become a double
            // click, and until Agentic Mouse acknowledges the resulting toggle.
            let blocked = pointerRouter.mouseButtonHeld ? "bottom held" : reviewExitGesture.pending ? "middle held" :
                reviewExitGesture.awaitingSecond ? "double click pending" : reviewExitGesture.toggling(now:now) ? "toggle pending" :
                (!ready || restoring) ? "receiver unavailable" : !context.isFresh ? "context expired" :
                NSWorkspace.shared.frontmostApplication?.bundleIdentifier != "com.microsoft.VSCode" ? "app not frontmost" : nil
            if let blocked {
                wandShortcutCircle.reset()
                recordReviewInput(rawX:x/1000,rawY:y/1000,dx:dx,dy:dy,now:now,blocked:blocked,step:0)
                return
            }
            let step=wandShortcutCircle.sample(dx:dx,dy:dy,now:now)
            recordReviewInput(rawX:x/1000,rawY:y/1000,dx:dx,dy:dy,now:now,blocked:nil,step:step)
            sendReview(review.detents(step,now:now))
            return
        }
        if appMode=="vsCode" && review.isHeld && selectedReviewMode==nil {sendReview(review.motion(y:navY-reviewOriginY,now:ProcessInfo.processInfo.systemUptime));return}
        guard !restoring,!scrollActive,hudSession else{return}
        // Ethan wants the dotted Switch App outline while the first hold is
        // still down. Qualify the current gesture; release still owns choose.
        if hudButtonHeld && !hudButtonQualified && ProcessInfo.processInfo.systemUptime-hudButtonPressedAt>=hudHoldSeconds {
            hudButtonQualified=true;controls.persistent("qualify")
        }
        // Ethan's mouse-button lane stays independent from the dotted Switch
        // App hover. Park before a drag/scroll, then start a fresh origin so
        // that movement cannot jump the outline when the mouse button is released.
        if !hudButtonHeld && pointerRouter.mouseButtonHeld {
            if hudActive {controls.persistent("park");hudActive=false;stopHUDWatchdog()}
            navOriginX=navX;navOriginY=navY
            return
        }
        // A short click has selected this outline already. While its existing
        // double-click window is pending, ignore aim movement; activate must use
        // the clicked wedge, never a later Back/Utilities outline. The next
        // stream takes a fresh origin, so this movement is dropped, not replayed.
        guard hudButtonTap == nil else{return}
        // Unheld movement aims within a submenu. A selected dotted control
        // adjusts only while held; native state owns that choice. Passive aim never times out.
        if !hudButtonHeld,!pointerInHUD,!hudActive,acceptHUDContext,context.isActive {
            navOriginX=navX;navOriginY=navY;hudActive=true
            stopHUDWatchdog();controls.persistent("hover")
        }
        if pointerInHUD {
            handleMove("U,"+String((navX-operationOriginX)*1000)+","+String((navY-operationOriginY)*1000),project:false)
        }else if hudActive {
            hudLastUpdate=Date();controls.persistent("motion",x:navX-navOriginX,y:navY-navOriginY,mouseX:hudButtonMouseOffset)
        }
    }
    func recordReviewInput(rawX:Double,rawY:Double,dx:Double,dy:Double,now:Double,blocked:String?,step:Int32) {
        guard reviewTrace.enabled else{return}
        let state=wandShortcutCircle.snapshot
        let metrics=WandReviewTrace.Metrics(event:state.event.rawValue,active:state.active,
            turn:state.turn,effective:state.effective,scale:state.scale,segment:state.segment,
            pending:state.pending,direction:state.direction,runSteps:state.runSteps,credit:state.credit,sideways:state.sideways)
        reviewTrace.record(.init(kind:"input",t:now,reason:blocked,mode:wandShortcutMode,
            rawX:rawX,rawY:rawY,x:navX,y:navY,dx:dx,dy:dy,eligible:blocked==nil,
            axisGestures:reviewAxisEnabled,step:Int(step),metrics:metrics))
    }
    func resumeHUDNavigation(){
        guard hudSession,!scrollActive,!restoring else{return}
        if hudActive { controls.persistent("park") }
        navOriginX=navX;navOriginY=navY;hudActive=true
        controls.persistent("navigate");startHUDWatchdog()
    }
    // MIDDLE opens the grid and directly moves its existing liquid outline.
    func handleHUD(_ payload:String) {
        guard !restoring,!scrollActive,hudSession,AXIsProcessTrusted() else{return}
        let f=payload.split(separator:",",omittingEmptySubsequences:false)
        guard f.count==3,let rawX=Double(f[1]),let rawY=Double(f[2]),rawX.isFinite,rawY.isFinite,abs(rawX)<=7_200_000,abs(rawY)<=7_200_000 else{return}
        if f[0]=="B" {cancelMouseExitClick();legacyHUDStream.reset()}
        let point=legacyHUDStream.update(x:rawX,y:rawY,using:motionFilter)
        let x=point.x,y=point.y
        switch f[0] {
        case "B":
            hudButtonTap?.invalidate();hudButtonTap=nil;hudButtonHold?.invalidate();hudButtonHold=nil
            if hudButtonOperating {controls.persistent("release");hudButtonOperating=false}
            pointerInHUD=false;releaseButtons();hudActive=true
            navigationOpenedHUD = !context.isActive
            if navigationOpenedHUD {controls.persistent("open")}
            controls.persistent("navigate");startHUDWatchdog()
        case "U":
            guard hudActive else{return};hudLastUpdate=Date()
            controls.persistent("motion",x:x/1000,y:y/1000)
        case "E":
            guard hudActive else{return};hudActive=false;stopHUDWatchdog()
            controls.persistent("motion",x:x/1000,y:y/1000);controls.persistent("park")
        default:break
        }
    }
    func startHUDWatchdog() {
        hudLastUpdate=Date();hudWatchdog?.invalidate()
        hudWatchdog=WandRunLoop.commonTimer(interval:0.25,repeats:true){[weak self] timer in
            guard let self else{timer.invalidate();return}
            if self.deskSleep.sleeping {return}
            if Date().timeIntervalSince(self.hudLastUpdate)>0.8 {
                self.closeHUD(reason:"navigation timed out");timer.invalidate()
            }
        }
    }
    func stopHUDWatchdog(){hudWatchdog?.invalidate();hudWatchdog=nil}
    // Ordinary wheel events use the same line units as Agentic Mouse.
    // Keep fractional lines so slow motion still accumulates into wheel steps.
    func handleScroll(_ payload:String){
        guard !restoring,AXIsProcessTrusted() else{return}
        let f=payload.split(separator:",",omittingEmptySubsequences:false)
        guard f.count==3,let rawX=Double(f[1]),let rawY=Double(f[2]),rawX.isFinite,rawY.isFinite,abs(rawX)<=7_200_000,abs(rawY)<=7_200_000 else{return}
        if f[0]=="B" {scrollStream.reset()}
        let point=scrollStream.update(x:rawX,y:rawY,using:motionFilter,horizontalGain:1.4)
        let x=point.x,y=point.y
        switch f[0]{
        case "B":
            let followingBefore=heldScroll.active || pointerRouter.mouseButtonHeld ? scrollFollowBefore:dwell.following
            if screenshot.ownsPointer {endScreenshot(reason:"scroll chord",contextActive:screenshotActive)}
            sendReview(review.cancel());cancelCircleScroll();finishScroll();hudEntryPress=false;hudButtonTap?.invalidate();hudButtonTap=nil;hudButtonHold?.invalidate();hudButtonHold=nil
            if hudActive {controls.persistent("park");if navigationOpenedHUD{controls.persistent("dismiss");hudSession=false;queue("setHUDOpen(false);")}}
            else if hudButtonOperating {controls.persistent("release")}
            hudActive=false;pointerInHUD=false;hudButtonOperating=false;navigationOpenedHUD=false
            stopHUDWatchdog();releaseButtons()
            scrollAnchor=deliveryPoint ?? currentPointerOrigin()
            scrollFollowBefore=followingBefore
            scrollActive=true;scrollX=x/1000;scrollY=y/1000;scrollFractionX=0;scrollFractionY=0
            scrollPostedX=0;scrollPostedY=0
            scrollUpdated=Date();log("SCROLL_BEGIN")
            scrollWatchdog=WandRunLoop.commonTimer(interval:0.25,repeats:true){[weak self] _ in
                guard let self else{return};if Date().timeIntervalSince(self.scrollUpdated)>0.8{self.finishScroll()}
            }
        case "U","E":
            guard scrollActive else{return};scrollUpdated=Date()
            scrollFractionX+=(x/1000-scrollX)*0.8;scrollFractionY+=(y/1000-scrollY)*0.8
            scrollX=x/1000;scrollY=y/1000
            let dx=max(-4096,min(4096,scrollFractionX.rounded(.towardZero)))
            let dy=max(-4096,min(4096,scrollFractionY.rounded(.towardZero)))
            scrollFractionX-=dx;scrollFractionY-=dy
            if dx != 0 || dy != 0 {postScroll(x:Int32(dx),y:Int32(dy))}
            if f[0]=="E"{finishScroll(released:true)}
        default:break
        }
    }
    /// Ethan's smart hold: over a real scroll area it scrolls (V3 sustained),
    /// over a draggable target it becomes a native drag. Until the bounded
    /// target probe answers it behaves as a scroll and can never drag, and an
    /// unknown answer keeps scrolling. Tap-then-hold is always a native drag.
    /// Previously beginBottomHold.
    func beginMouseButtonHold(now:Double,following:Bool?=nil) {
        cancelMouseExitClick()
        scrollFollowBefore=following ?? dwell.following
        finishNativeScroll(cancelled:true)
        heldScrollAnchor=deliveryPoint ?? currentPointerOrigin()
        heldTargetToken=UUID()
        let explicitDrag=recenterGesture.isSecondPress
        heldScroll.begin(now:now,scrollable:!explicitDrag,sustain:controlVersion == .sustainedV3,resolving:!explicitDrag)
        heldSafetyTimer?.invalidate()
        heldSafetyTimer=WandRunLoop.commonTimer(interval:0.02,repeats:true){[weak self] _ in
            guard let self else{return};let now=ProcessInfo.processInfo.systemUptime
            if self.heldScroll.stale(now:now){self.reconcileMouseButtonHold(down:false,now:now,reason:"button telemetry timeout",released:false);return}
            // A pause mid-gesture cancels it at once rather than leaving it open.
            if self.actionPause.paused {self.finishNativeScroll(cancelled:true)}
            guard self.ready,!self.restoring,!self.actionPause.paused,AXIsProcessTrusted() else{return}
            let units=self.heldScroll.continuation(now:now,pageUnitsPerLine:WandSustainedScroll.pagePixelsPerLine)
            if units.x != 0 || units.y != 0 {
                self.setCircleLight(true)
                self.postSustainedScroll(x:units.x,y:units.y,at:self.heldScrollAnchor)
            }
        }
        releaseButtons()
        if explicitDrag {log("BOTTOM_HOLD_TARGET","explicit drag")}
    }
    /// One bounded Accessibility hit test per hold, off the main thread. The
    /// gesture token drops any reply that arrives after the hold ended, and
    /// the hold itself rejects one that arrives after the tap/hold decision.
    func probeHoldTarget(at point:CGPoint,token:UUID) {
        holdTargetQueue.async { [weak self] in
            let probe=Self.holdTargetProbe(at:point)
            DispatchQueue.main.async {
                guard let self else{return}
                let current=self.heldTargetToken==token && self.heldScroll.active
                let applied=current && self.heldScroll.setTarget(scrollable:probe.target != .drag,now:ProcessInfo.processInfo.systemUptime)
                // One result per request, even when released or too late. No chat content.
                let disposition = applied ? "applied" : current ? "late (scroll)" : "discarded"
                log("BOTTOM_HOLD_TARGET",probe.target.rawValue,"id="+token.uuidString,disposition,probe.diagnostic)
            }
        }
    }
    /// Roles and app identity only, nearest first, within the existing 60 ms budget.
    /// Stop at a decision or boundary, and report exactly why traversal ended.
    static func holdTargetProbe(at point:CGPoint,budget:TimeInterval=0.06)->WandHoldTargetProbe {
        var probe=WandHoldTargetProbe()
        let start=ProcessInfo.processInfo.systemUptime
        func finished(_ stop:String,_ error:AXError = .success)->WandHoldTargetProbe {
            probe.stop=stop;probe.error=Int(error.rawValue)
            probe.milliseconds=Int((ProcessInfo.processInfo.systemUptime-start)*1000)
            return probe
        }
        guard AXIsProcessTrusted() else{return finished("not-trusted")}
        let deadline=start+budget,system=AXUIElementCreateSystemWide()
        AXUIElementSetMessagingTimeout(system,Float(max(0.001,min(0.02,budget))))
        var hit:AXUIElement?
        let hitResult=AXUIElementCopyElementAtPosition(system,Float(point.x),Float(point.y),&hit)
        guard hitResult == .success,let hit else{return finished("hit-error",hitResult)}
        var owner:pid_t=0
        if AXUIElementGetPid(hit,&owner) == .success {
            probe.bundleIdentifier=NSRunningApplication(processIdentifier:owner)?.bundleIdentifier ?? "unknown"
        }
        let notificationCenter=probe.bundleIdentifier=="com.apple.notificationcenterui"
        var current:AXUIElement?=hit
        for _ in 0..<24 {
            guard let item=current else{return finished("no-parent")}
            let remaining=deadline-ProcessInfo.processInfo.systemUptime
            guard remaining>0 else{return finished("budget")}
            AXUIElementSetMessagingTimeout(item,Float(max(0.001,min(0.01,remaining))))
            var role:CFTypeRef?
            let roleResult=AXUIElementCopyAttributeValue(item,kAXRoleAttribute as CFString,&role)
            guard roleResult == .success,let name=role as? String else{return finished("role-error",roleResult)}
            probe.roles.append(name)
            // Notification banners are positively draggable, even in a scroll area.
            if notificationCenter,name=="AXGroup" {
                let remaining=deadline-ProcessInfo.processInfo.systemUptime
                guard remaining>0 else{return finished("budget")}
                AXUIElementSetMessagingTimeout(item,Float(max(0.001,min(0.01,remaining))))
                var subrole:CFTypeRef?
                if AXUIElementCopyAttributeValue(item,kAXSubroleAttribute as CFString,&subrole) == .success,
                   let value=subrole as? String,value=="AXNotificationCenterAlert" {
                    probe.roles.append(value);return finished("decisive-role")
                }
            }
            if WandHoldTarget.ends(at:name) {return finished("boundary")}
            let parentRemaining=deadline-ProcessInfo.processInfo.systemUptime
            guard parentRemaining>0 else{return finished("budget")}
            AXUIElementSetMessagingTimeout(item,Float(max(0.001,min(0.01,parentRemaining))))
            var parent:CFTypeRef?
            let parentResult=AXUIElementCopyAttributeValue(item,kAXParentAttribute as CFString,&parent)
            guard parentResult == .success,let value=parent,CFGetTypeID(value)==AXUIElementGetTypeID() else{return finished("parent-error",parentResult)}
            current=(value as! AXUIElement)
        }
        return finished("depth")
    }
    // Ordinary mice deliver one wheel axis at a time. Mixed-axis line events
    // can be reduced to the dominant direction by native scrolling views.
    // Send both components back-to-back so diagonal wand motion retains both.
    static func wheelEvents(x:Int32,y:Int32,at point:CGPoint?=nil)->[CGEvent] {
        guard let source=CGEventSource(stateID:.hidSystemState) else{return []}
        var events:[CGEvent]=[]
        if x != 0, let event=CGEvent(scrollWheelEvent2Source:source,units:.line,wheelCount:2,wheel1:0,wheel2:x,wheel3:0) {events.append(event)}
        if y != 0, let event=CGEvent(scrollWheelEvent2Source:source,units:.line,wheelCount:2,wheel1:y,wheel2:0,wheel3:0) {events.append(event)}
        if let point {for event in events {event.location=point}}
        return events
    }
    /// Ethan, 2026-10-31: "make the up-down mechanism be different from the side
    /// scrolling" and "the same feeling as before". Output with any vertical part
    /// (vertical or diagonal page scrolling) uses the ordinary line wheel events his
    /// normal scroll feel was tuned on, exactly as before native gestures. Only a
    /// purely sideways output is a native precise phased gesture, so the app itself
    /// still decides horizontal scrolling or Back/Forward. Turning from sideways to
    /// page scrolling abandons that swipe: cancel it, so no history commits, before
    /// any line event. A later sideways stroke begins a fresh gesture. Same tick,
    /// same values: routing adds no delay, buffering or replay.
    func postHeldScroll(x:Int32,y:Int32,at point:CGPoint?) {
        guard !actionPause.paused else{finishNativeScroll(cancelled:true);return}
        guard x != 0 || y != 0 else{return}
        if y == 0 {postNativeScroll(x:x,y:0,at:point);return}
        finishNativeScroll(cancelled:true)
        for event in Self.wheelEvents(x:x,y:y,at:point) {event.post(tap:.cghidEventTap)}
    }
    /// V3 page motion carries pixel units at the existing 20 ms cadence. It has
    /// no history-swipe phase, while the horizontal stroke retains its native
    /// lifecycle. V2 and the two-button chord keep their ordinary line events.
    func postSustainedScroll(x:Int32,y:Int32,at point:CGPoint?) {
        guard !actionPause.paused else{finishNativeScroll(cancelled:true);return}
        guard x != 0 || y != 0 else{return}
        if heldScroll.sustained.velocityY == 0 {postHeldScroll(x:x,y:y,at:point);return}
        finishNativeScroll(cancelled:true)
        if let event=Self.pagePixelEvent(x:x,y:y,at:point) {event.post(tap:.cghidEventTap)}
    }
    static func pagePixelEvent(x:Int32,y:Int32,at point:CGPoint?)->CGEvent? {
        guard let source=CGEventSource(stateID:.hidSystemState),
              let event=CGEvent(scrollWheelEvent2Source:source,units:.pixel,wheelCount:2,wheel1:y,wheel2:x,wheel3:0) else{return nil}
        if let point {event.location=point}
        event.setIntegerValueField(.scrollWheelEventIsContinuous,value:1)
        event.setIntegerValueField(.scrollWheelEventScrollPhase,value:0)
        event.setIntegerValueField(.scrollWheelEventMomentumPhase,value:0)
        return event
    }
    /// A completed sideways stroke hands its native gesture back to the app
    /// immediately. The held button may then start a fresh deliberate stroke.
    func finishHorizontalStrokeIfNeeded() {
        guard let boundary=heldScroll.sustained.takeHorizontalBoundary() else{return}
        finishNativeScroll(cancelled:boundary == .cancelled)
    }
    func postNativeScroll(x:Int32,y:Int32,at point:CGPoint?) {
        guard !actionPause.paused else{finishNativeScroll(cancelled:true);return}
        let beginning = !nativeScroll.active
        if let event=nativeScroll.update(x:x,y:y,at:point ?? currentPointerOrigin()) {
            event.post(tap:.cghidEventTap)
            if beginning {log("NATIVE_SCROLL_BEGIN")}
        }
    }
    /// Ends or cancels the open native gesture (a no-op when none is open).
    /// Every path that ends a held or chord scroll, starts a native drag, or
    /// tears the receiver down must come through here.
    func finishNativeScroll(cancelled:Bool) {
        if let event=nativeScroll.finish(cancelled:cancelled) {
            event.post(tap:.cghidEventTap)
            log(cancelled ? "NATIVE_SCROLL_CANCEL" : "NATIVE_SCROLL_END")
        }
    }
    func postScroll(x:Int32,y:Int32){
        // The two-button chord keeps its original line wheel events. Its raw
        // two-axis stream has no snapped axis, so it could not own a clean
        // sideways-only native gesture without flipping transports mid-chord.
        guard !actionPause.paused else{finishNativeScroll(cancelled:true);return}
        for event in Self.wheelEvents(x:x,y:y,at:scrollAnchor ?? circleAnchor) {event.post(tap:.cghidEventTap)}
        scrollPostedX+=Int(x);scrollPostedY+=Int(y)
    }
    /// Formerly enableMouseAfterScroll. A completed page scroll restores the
    /// mouse-follow choice captured before the mouse-button/chord gesture.
    /// Ethan: "if I wasn't in mouse follow mode when I started scrolling,
    /// on end it shouldn't enter mouse follow mode after" (2026-10-30).
    /// Taps, native drags, lost telemetry and screenshots keep their own paths.
    func restoreMouseAfterScroll(){
        guard ready,!restoring else{return}
        if scrollFollowBefore {enterPointerMode()}
        motionFilter.reset();dwell.reset();dwell.follow(scrollFollowBefore)
        if scrollFollowBefore {restDetection.pointerActivated()}else{restDetection.pointerStopped()}
        scheduleDwell()
        queue("global.wandPointerPauseUntil=0;setMouseFollow("+(scrollFollowBefore ? "true":"false")+");")
        log(scrollFollowBefore ? "SCROLL_FINISHED_MOUSE_ON":"SCROLL_FINISHED_MOUSE_OFF")
    }
    /// `released`: a physical release ended the chord scroll.
    func finishScroll(released:Bool=false){
        if scrollActive{log("SCROLL_END lines",scrollPostedX,scrollPostedY)}
        let wasActive=scrollActive
        scrollActive=false;scrollAnchor=nil;scrollWatchdog?.invalidate();scrollWatchdog=nil
        if wasActive {finishNativeScroll(cancelled:!released);if released {restoreMouseAfterScroll()}else{resumeHUDNavigation()}}
    }
    /// A mouse-button double tap is a global escape into pointing, not a mode action.
    /// Keep its recognition alive when the first tap closes a HUD or scroll.
    /// Ethan's triple-click screenshot shares its two clicks, so the centre
    /// waits out the third press's 0.3 s window rather than jumping before a
    /// screenshot anchor. No pointer motion is buffered or replayed meanwhile.
    /// Previously recognizeBottomRecenter.
    func recognizeMouseButtonRecenter(down:Bool,now:Double)->Bool {
        if down {cancelMouseExitClick();recenterSuppressButtons=false}
        guard recenterGesture.edge(down:down,now:now) else{return false}
        cancelMouseExitClick()
        pendingRecenter?.invalidate()
        pendingRecenter=WandRunLoop.commonTimer(interval:WandTripleClick.window,repeats:false){[weak self] _ in
            guard let self else{return};self.pendingRecenter=nil;self.recenterPointer()
        }
        return true
    }
    /// Recenter only the mouse-button pointer lane; preserve the HUD button's HUD/review and speech.
    func recenterPointer() {
        cancelMouseExitClick()
        guard ready,!restoring,!actionPause.paused,!screenshot.ownsPointer,AXIsProcessTrusted() else{return}
        cancelCircleScroll();finishScroll();performPointer(pointerRouter.cancelAll());releaseButtons();motionFilter.reset()
        recenterSuppressButtons=true
        dwell.follow(true);restDetection.pointerActivated();scheduleDwell()
        queue("stopScroll();stopPointerTrack();scrollSuppress=false;global.wandCircleScrolling=false;setMouseFollow(true);")
        let bounds=CGDisplayBounds(CGMainDisplayID())
        let point=CGPoint(x:bounds.midX,y:bounds.midY)
        CGWarpMouseCursorPosition(point)
        settleRecenteredCursor(at:point)
        pointerOrigin.begin(at:point,now:ProcessInfo.processInfo.systemUptime)
        deliveryPoint=point
        log("POINTER_RECENTER")
    }
    /// One ordinary move to the centre through the same input queue as the
    /// wand's earlier events, so anything posted before the warp lands first
    /// and the cursor finishes at the centre.
    func settleRecenteredCursor(at point:CGPoint) {
        Self.mouseMovementEvent(buttons:0,from:point,to:point)?.post(tap:.cghidEventTap)
    }
    func refreshPointerDisplays() {
        var ids=[CGDirectDisplayID](repeating:0,count:32),count:UInt32=0
        if CGGetActiveDisplayList(UInt32(ids.count),&ids ,&count) == .success {
            pointerDisplays=ids.prefix(Int(count)).map{CGDisplayBounds($0)}.filter{!$0.isEmpty}
        }
    }
    func setCircleLight(_ active:Bool) {
        guard circleLight != active else{return};circleLight=active
        if !active {circleAnchor=nil}
        if ready && !restoring {queue("global.wandCircleScrolling="+(active ? "true":"false")+";updateLights();")}
        if active && circleTimer == nil {
            circleTimer=WandRunLoop.commonTimer(interval:0.1,repeats:true){[weak self] _ in
                guard let self else{return}
                self.performPointer(self.pointerRouter.tick(now:ProcessInfo.processInfo.systemUptime))
            }
        } else if !active {circleTimer?.invalidate();circleTimer=nil}
    }
    /// Scroll chord, HUD and speech take over: drop unshown LOW motion and any circle.
    func cancelCircleScroll(){cancelMouseExitClick();if heldScroll.dragging {transition(to:0,at:deliveryPoint ?? currentPointerOrigin())};heldSafetyTimer?.invalidate();heldSafetyTimer=nil;finishNativeScroll(cancelled:true);heldScroll.reset();heldScrollAnchor=nil;flickScroll.reset();flickAnchor=nil;dwell.reset();scheduleDwell();performPointer(pointerRouter.interrupt());setCircleLight(false)}
    // Ethan: Review changes = eyes mode; Stage files = whole-file "bang" selection.
    // Keep the existing Better Git URI lifecycle; only the gesture source changes.
    func setWandShortcut(_ mode:String?) {
        guard let mode else {finishWandShortcut(commit:false);return}
        guard ready,!restoring,context.isFresh,["changes","files"].contains(mode),
              NSWorkspace.shared.frontmostApplication?.bundleIdentifier=="com.microsoft.VSCode" else{
            // A live session that cannot follow the newly selected mode is
            // cancelled now, never left running in the old one.
            if wandShortcutMode != nil && wandShortcutMode != mode {finishWandShortcut(commit:false)}
            return
        }
        if wandShortcutMode==mode{return}
        // Ethan's Review/Stage toggle keeps the same selection: switch the live
        // session in place rather than cancel it and start an empty one.
        if wandShortcutMode != nil {switchWandShortcut(to:mode);return}
        finishWandShortcut(commit:false)
        let now=ProcessInfo.processInfo.systemUptime
        wandShortcutMode=mode;wandShortcutX=navX;wandShortcutY=navY;wandShortcutTime=now
        wandShortcutCircle.reset();navStream.reset();navX=0;navY=0;wandShortcutX=0;wandShortcutY=0
        review.beginDetents(mode:mode,now:now)
        reviewTrace.boundary("begin",mode:mode,now:now)
        queue("setWandReviewTracking(true);")
        reviewTimer=WandRunLoop.commonTimer(interval:0.2,repeats:true){[weak self] _ in
            guard let self else{return}
            let now=ProcessInfo.processInfo.systemUptime
            if !self.context.isFresh || NSWorkspace.shared.frontmostApplication?.bundleIdentifier != "com.microsoft.VSCode" || now-self.wandShortcutTime>0.8 {
                self.finishWandShortcut(commit:false);return
            }
            _=self.review.detents(0,now:now)
            self.sendReview(self.review.tick(now:now))
        }
        log("WAND_REVIEW_SHORTCUT",mode)
    }
    /// Better Git keeps the existing selection and adds the file being
    /// viewed. Only the review circle restarts: the NAV stream, tracking
    /// light, heartbeat timer and transaction ID all carry on, so the next
    /// ratchet and the hold commit act in the new mode.
    func switchWandShortcut(to mode:String) {
        let now=ProcessInfo.processInfo.systemUptime
        sendReview(review.changeMode(mode,now:now))
        wandShortcutMode=mode;wandShortcutCircle.reset()
        reviewTrace.boundary("mode",mode:mode,now:now)
        log("WAND_REVIEW_MODE",mode)
    }
    func finishWandShortcut(commit:Bool) {
        guard wandShortcutMode != nil else{return}
        reviewTrace.boundary(commit ? "finish":"cancel",mode:wandShortcutMode)
        wandShortcutMode=nil;wandShortcutCircle.reset()
        sendReview(review.endDetents(commit:commit));reviewTimer?.invalidate();reviewTimer=nil
        if ready && !restoring {queue("setWandReviewTracking(false);")}
    }
    func exitSelectedReview(commit:Bool) {
        reviewExitTimer?.invalidate();reviewExitTimer=nil;reviewExitGesture.reset()
        finishWandShortcut(commit:commit);selectedReviewMode=nil
        controls.persistent("exitReview")
        log("WAND_REVIEW_EXIT",commit ? "stage set":"cancel set")
    }
    func beginReviewCommitHold(now:Double) {
        reviewTrace.boundary("middle down",mode:wandShortcutMode,now:now)
        reviewExitGesture.down(now:now)
        wandShortcutCircle.reset()
        reviewExitTimer=WandRunLoop.commonTimer(interval:WandReviewExitGesture.holdSeconds,repeats:false){[weak self] _ in
            self?.commitReviewHold(now:ProcessInfo.processInfo.systemUptime)
        }
    }
    func commitReviewHold(now:Double) {
        guard selectedReviewMode != nil,reviewExitGesture.commitIfHeld(now:now) else{return}
        commitSelectedReview()
    }
    /// Ethan's single HUD-button click in review waits out the double-click window
    /// (at most 0.3 s, approved) before exiting. Only review navigation pauses
    /// meanwhile; pointer motion is never buffered or delayed.
    func scheduleReviewTapTimeout() {
        guard let deadline=reviewExitGesture.tapDeadline else{return}
        reviewExitTimer?.invalidate()
        reviewExitTimer=WandRunLoop.commonTimer(interval:max(0.001,deadline-ProcessInfo.processInfo.systemUptime),repeats:false){[weak self] _ in
            // A superseded timer finds another deadline, or none, and does nothing.
            guard let self,self.reviewExitGesture.tapTimedOut(deadline:deadline) else{return}
            self.expireReviewTap()
        }
    }
    /// The window ended with one tap: leave the set unstaged, as a single
    /// click always did. This stays the local escape even if the context is stale.
    func expireReviewTap() {
        reviewExitTimer?.invalidate();reviewExitTimer=nil
        guard selectedReviewMode != nil,!restoring else{reviewExitGesture.reset();return}
        exitSelectedReview(commit:false)
    }
    func cancelReviewTap(_ reason:String) {
        guard reviewExitGesture.cancelTap() else{return}
        reviewExitTimer?.invalidate();reviewExitTimer=nil
        log("WAND_REVIEW_TAP_CANCELLED",reason)
    }
    /// A second short click asks Agentic Mouse, the one selection owner, to
    /// switch Review changes and Stage files. Nothing is staged here, and the
    /// local mode changes only on its selection acknowledgement.
    func requestReviewToggle(now:Double) {
        guard let mode=selectedReviewMode,ready,!restoring,context.isFresh else{log("WAND_REVIEW_TOGGLE_DROPPED");return}
        reviewExitGesture.toggleRequested(now:now)
        reviewTrace.boundary("toggle request",mode:wandShortcutMode,now:now)
        controls.persistent("toggleReview")
        log("WAND_REVIEW_TOGGLE_REQUESTED",mode)
    }
    func commitSelectedReview() {
        reviewExitTimer?.invalidate();reviewExitTimer=nil
        // Keep the held latch until HUD-button release: circling must not change the set,
        // including after this one staging action has already completed.
        guard let mode=selectedReviewMode else{return}
        sendReview(review.endDetents(commit:true))
        // Start another Better Git transaction lazily on the next ratchet. Keep
        // the live NAV stream, tracking timer and selected badge uninterrupted.
        review.beginDetents(mode:mode,now:ProcessInfo.processInfo.systemUptime)
        reviewTrace.boundary("commit",mode:mode)
        wandShortcutCircle.reset()
        log("WAND_REVIEW_COMMIT",mode,"continue")
    }
    func sendReview(_ requests:[WandReviewGesture.Request]){
        // Paused: only a cancellation may close an existing Better Git transaction.
        for request in requests where !actionPause.paused || request.phase == "cancel" {
            guard let app=NSRunningApplication.runningApplications(withBundleIdentifier:"com.microsoft.VSCode").first,
                  app.isActive,let application=app.bundleURL else{continue}
            var url=URLComponents();url.scheme="vscode";url.host="ethansk.better-git-vscode";url.path="/wand-review/"+request.phase
            url.queryItems=[URLQueryItem(name:"version",value:"1"),URLQueryItem(name:"id",value:request.id),URLQueryItem(name:"seq",value:String(request.seq)),URLQueryItem(name:"direction",value:request.direction),URLQueryItem(name:"mode",value:request.mode)]
            guard let target=url.url else{continue}
            let config=NSWorkspace.OpenConfiguration();config.activates=false;config.addsToRecentItems=false
            NSWorkspace.shared.open([target],withApplicationAt:application,configuration:config){_,error in if let error {log("VSCODE_REVIEW_FAILED",error.localizedDescription)}}
            reviewTrace.record(.init(kind:"request",t:ProcessInfo.processInfo.systemUptime,mode:request.mode,
                                    phase:request.phase,direction:request.direction))
            log("VSCODE_REVIEW_SENT",request.phase,request.direction,request.mode)
        }
    }
    func performPointer(_ actions:[WandPointerRouter.Action]) {
        // A drain can contain several frames. Carry a locally clamped point
        // through the batch; posting CGEvents need not update the system cursor
        // synchronously before the next frame is posted.
        var point=deliveryPoint ?? currentPointerOrigin()
        for action in actions {
            switch action {
            case .move(let dx,let dy): point=postPointerMove(dx:dx,dy:dy,from:point)
            case .scroll(let lines): postScroll(x:0,y:lines)
            case .circleLight(let on):
                if on {circleAnchor=point}
                setCircleLight(on)
            }
        }
        if deliveryPoint != nil {deliveryPoint=point}
        scheduleLowDelay()
    }
    // One one-shot timer for the earliest delayed LOW frame; never runs when idle.
    func scheduleLowDelay() {
        lowDelayTimer?.invalidate();lowDelayTimer=nil
        guard let due=pointerRouter.nextDue else{return}
        lowDelayTimer=WandRunLoop.commonTimer(interval:max(0,due-ProcessInfo.processInfo.systemUptime),repeats:false){[weak self] _ in
            guard let self else{return}
            self.lowDelayTimer=nil
            self.performPointer(self.pointerRouter.drain(now:ProcessInfo.processInfo.systemUptime))
        }
    }
    @discardableResult
    /// Where the next pointer event starts: the system cursor, unless it only
    /// lags the wand's own just-posted movement (`WandPointerOrigin`).
    func currentPointerOrigin()->CGPoint {
        pointerOrigin.origin(system:WandPointerBounds.clamp(CGEvent(source:nil)?.location ?? .zero,to:pointerDisplays),
                             now:ProcessInfo.processInfo.systemUptime)
    }
    func postPointerMove(dx:Int,dy:Int,from point:CGPoint)->CGPoint {
        guard !actionPause.paused else{return point}
        guard !recordingPointerPaused || screenshot.ownsPointer else{return point}
        // Ethan's "switch app button": the HUD button operates the selected HUD card.
        // Keep horizontal card input, but drop concurrent mouse-mode movement
        // for the whole press, including entry and the card's hold threshold.
        // Returning the unchanged point discards motion instead of replaying it
        // on release; an open, unheld HUD and independent review stay separate.
        guard !(hudSession && (hudButtonHeld || hudEntryPress || pointerInHUD)) else{return point}
        // Ethan (2026-10-29): "it should not block me from using the mouse
        // ever in any HUD." An open HUD no longer freezes the pointer: when
        // mouse follow is on, unheld motion moves it while the HUD's outline
        // follows too. Follow-on stop-to-click also stays available with an
        // open, unheld HUD; operating a HUD card still owns that press.
        let newPoint=WandPointerBounds.clamp(CGPoint(x:point.x+CGFloat(dx),y:point.y+CGFloat(dy)),to:pointerDisplays)
        if let event=Self.mouseMovementEvent(buttons:buttons,from:point,to:newPoint) {
            event.post(tap:.cghidEventTap)
            pointerOrigin.moved(from:point,to:newPoint,now:ProcessInfo.processInfo.systemUptime)
            pointerTravel += abs(newPoint.x-point.x)+abs(newPoint.y-point.y)
        }
        movementCount += 1
        if movementCount == 1 || movementCount % 100 == 0 { log("MOVEMENT_REPORTS_POSTED", movementCount) }
        return newPoint
    }
    func handle(_ payload: String) {
        let values = payload.split(separator: ",", omittingEmptySubsequences: false)
        guard values.count == 3, let x = Int(values[0]), let y = Int(values[1]), let b = Int(values[2]),
              (-4095...4095).contains(x), (-4095...4095).contains(y), (0...3).contains(b), !restoring, !scrollActive, AXIsProcessTrusted() else { return }
        handleFrame(x:x,y:y,b:b)
    }
    func handleFrame(x:Int,y:Int,b:Int,stopX:Int?=nil,stopY:Int?=nil){
        // Screenshot mode owns the mouse button and the native button; the wand's legacy
        // button frames carry no motion in raw mode and must never act here.
        if screenshot.ownsPointer {return}
        // The device can finish an old release click after the global escape.
        if recenterSuppressButtons && b != 0 {return}
        if controlVersion.usesHeldScroll && (heldScroll.consumes(buttons:b) || pointerRouter.mouseButtonHeld) {dwell.reset();scheduleDwell();return}
        // V2/V3 owns native drags in the physical mouse-button hold. Firmware's
        // legacy drag/click queue must never relatch the Mac after release.
        if controlVersion.usesHeldScroll && b != 0 {return}
        reportCount += 1
        if reportCount == 1 { log("FIRST_DEVICE_REPORT_VALIDATED") }
        let point = deliveryPoint ?? currentPointerOrigin()
        // The router may drop a consumed hold's endpoint click; button changes are
        // applied before motion, at the position already shown.
        let routed=pointerRouter.frame(dx:x,dy:y,buttons:b,hud:false,now:ProcessInfo.processInfo.systemUptime)
        // A HUD session Agentic Mouse no longer shows never blocks clicks: the
        // same stale rule a HUD-button press applies, checked as the mouse moves.
        if hudSession && !hudButtonHeld && !context.isActive && ProcessInfo.processInfo.systemUptime-hudOpenedAt>1 {
            closeHUD(reason:"context missing",notifyNative:false)
        }
        // Stop-to-click follows the tuned stop counts on either pointer path.
        let gate=WandClickGate.blocker(recordingPaused:recordingPointerPaused,mouseButtonHeld:pointerRouter.mouseButtonHeld,buttons:b,
                                       hudSession:hudSession,hudShown:context.isActive,scrollActive:scrollActive,
                                       hudOperating:hudButtonHeld || hudEntryPress || pointerInHUD)
        noteClickGate(gate)
        dwell.move(dx:stopX ?? x,dy:stopY ?? y,now:ProcessInfo.processInfo.systemUptime,eligible:gate == nil)
        scheduleDwell()
        if routed.buttons != b {log("CONSUMED_HOLD_CLICK_DROPPED")}
        transition(to: routed.buttons, at: point)
        performPointer(routed.actions)
    }
    /// `released`: the physical release, as opposed to lost telemetry or a
    /// screenshot taking over. Only a released, qualified scroll changes follow.
    /// Previously finishBottomHold.
    func finishMouseButtonHold(now:Double,released:Bool=true) {
        if !released {cancelMouseExitClick()}
        heldSafetyTimer?.invalidate();heldSafetyTimer=nil;heldTargetToken=UUID()
        // Ethan: dragging is only while holding the mouse button. Release an orphaned
        // native down too, even if another path already cleared the hold.
        if buttons & 1 != 0 {transition(to:buttons & ~1,at:deliveryPoint ?? currentPointerOrigin())}
        guard heldScroll.active else{
            // @BOTTOM 0 precedes @SCROLL E on the device. The chord owns
            // its open gesture until that end marker, not this mouse-button edge.
            if !scrollActive {finishNativeScroll(cancelled:true)}
            return
        }
        // A Sense press judged by its physical edges: a short tap that only
        // looked long because its release arrived late never counts as a
        // completed scroll, so it cannot turn mouse follow back on.
        let physicalDuration=released ? mouseButtonPhysicalTapDuration() : nil
        let physicalTap=physicalDuration.map{$0<heldScroll.holdSeconds} ?? false
        if physicalTap {log("BOTTOM_PHYSICAL_TAP",Int((physicalDuration ?? 0)*1000))}
        let completedScroll=heldScroll.scrollable && !heldScroll.dragging && heldScroll.qualified(now:now) && !physicalTap
        // Ethan (2026-10-31): stop follow now, but wait up to the existing
        // 300 ms double/triple window before clicking. Either gesture cancels it.
        // Physical duration wins when Bluetooth delivery is late; held scrolling,
        // dragging, entering follow and duplicate/cancelled releases never click.
        let shortRelease=physicalDuration.map{$0>=0 && $0<heldScroll.holdSeconds} ?? (heldScroll.elapsed(now:now)>=0 && !heldScroll.qualified(now:now))
        let exitClick=released && shortRelease && scrollFollowBefore && !heldScroll.dragging && !scrollActive
        if exitClick && ready && !restoring && !actionPause.paused && !screenshot.ownsPointer && AXIsProcessTrusted() {
            scheduleMouseExitClick(at:currentPointerOrigin())
        }
        // A delayed short tap is not an accepted scroll. Cancel its native
        // phase so an app cannot commit history navigation on that release.
        finishNativeScroll(cancelled:!released || !completedScroll)
        if heldScrollDiagnostics && heldScroll.sustaining && completedScroll {
            log("V3_SCROLL_HOLD",heldScroll.sustained.report(seconds:heldScroll.elapsed(now:now),ended:released ? "release":"lost"))
        }
        if heldScroll.dragging {transition(to:0,at:deliveryPoint ?? currentPointerOrigin())}
        if heldScroll.end(now:now) {queue("global.wandPointerPauseUntil=0;")}
        heldScrollAnchor=nil;setCircleLight(false)
        if completedScroll && released {restoreMouseAfterScroll()}
    }
    /// The only delayed ordinary click. Keep its release point and reject it
    /// after a new action, pointer movement, app switch or overdue run-loop wake.
    /// This never delays follow-off, pointing, dragging or scrolling.
    func scheduleMouseExitClick(at point:CGPoint) {
        cancelMouseExitClick()
        dwell.follow(false);restDetection.pointerStopped();scheduleDwell()
        guard let app=mouseExitClickContext() else{return}
        let token=mouseExitClickToken,started=ProcessInfo.processInfo.systemUptime,hudWasOpen=hudSession
        pendingMouseExitClick=WandRunLoop.commonTimer(interval:WandTripleClick.window,repeats:false){[weak self] _ in
            guard let self,self.mouseExitClickToken==token else{return}
            self.pendingMouseExitClick=nil
            // A late timer is dropped, never replayed after the Mac was busy.
            guard ProcessInfo.processInfo.systemUptime-started<=WandTripleClick.window+0.1,
                  self.ready,!self.restoring,!self.actionPause.paused,!self.screenshot.ownsPointer,
                  !self.heldScroll.active,!self.scrollActive,!self.pointerRouter.mouseButtonHeld,
                  self.hudSession==hudWasOpen,!self.hudButtonHeld,!self.hudEntryPress,!self.pointerInHUD,
                  !self.dwell.following,self.mouseExitClickContext()==app,AXIsProcessTrusted() else{return}
            let current=self.currentPointerOrigin(),tolerance=WandPointerOrigin.tolerance
            guard abs(current.x-point.x)<=tolerance,abs(current.y-point.y)<=tolerance else{return}
            self.transition(to:1,at:point);self.transition(to:0,at:point)
            log("MOUSE_EXIT_CLICK")
        }
    }
    func mouseExitClickContext()->String? {NSWorkspace.shared.frontmostApplication?.bundleIdentifier}
    func cancelMouseExitClick() {
        pendingMouseExitClick?.invalidate();pendingMouseExitClick=nil;mouseExitClickToken=UUID()
    }
    /// Previously reconcileBottomHold.
    func reconcileMouseButtonHold(down:Bool,now:Double,reason:String,released:Bool=true) {
        // A latched screenshot drag outlives its tap's physical release.
        guard !screenshot.ownsPointer else{return}
        // V1's normal click pair is synchronous. After its physical release
        // edge, a later up sample can safely clear an orphaned device drag.
        if !controlVersion.usesHeldScroll {
            if !down && !pointerRouter.mouseButtonHeld && buttons & 1 != 0 {
                transition(to:buttons & ~1,at:deliveryPoint ?? currentPointerOrigin())
                log("BOTTOM_HOLD_RECOVERED",reason)
            }
            return
        }
        guard controlVersion.usesHeldScroll else{return}
        if down {heldScroll.confirmHeld(now:now);return}
        guard heldScroll.active || pointerRouter.mouseButtonHeld || buttons & 1 != 0 else{return}
        finishMouseButtonHold(now:now,released:released)
        performPointer(pointerRouter.mouseButton(down:false))
        dwell.reset();scheduleDwell();log("BOTTOM_HOLD_RECOVERED",reason)
    }
    func handleRaw(_ payload:String){
        guard ready,!restoring else{return}
        let fields=payload.split(separator:",",omittingEmptySubsequences:false)
        guard fields.count==4 else{return}
        let v=fields.compactMap{Int($0)}
        // ±65535: the Sense's 500 deg/s range in Puck counts; a Puck never exceeds int16.
        guard v.count==4,(1...50000).contains(v[0]),(-65535...65535).contains(v[1]),(-65535...65535).contains(v[2]),(0...7).contains(v[3]) else{return}
        let now=ProcessInfo.processInfo.systemUptime
        // Screenshot mode precedes every ordinary mouse-button guard: its latched
        // drag must survive the latching tap's physical release.
        if screenshot.ownsPointer {handleScreenshotRaw(v,now:now);return}
        let released=heldScroll.active && v[3]&1 == 0
        reconcileMouseButtonHold(down:v[3]&1 != 0,now:now,reason:"motion button state")
        guard !released,!scrollActive,AXIsProcessTrusted() else{return}
        let gap=rawLastArrival>0 ? now-rawLastArrival : 0
        guard let sample=motionFilter.sample(rawX:v[1],rawY:v[2],microseconds:v[0],held:v[3]&1 != 0,resetState:v[3]&2 != 0 || gap>0.25) else{return}
        rawLastArrival=now
        // Held Switch App moves straight forward and back with real left/right
        // HIGH motion, reversals included. Ethan removed its circular latch:
        // "Just do normal scroll forward and backwards for the switch app
        // thing" (2026-10-29).
        if hudButtonHeld && !pointerRouter.mouseButtonHeld {
            hudButtonMouseX+=sample.highX;hudButtonMouseSampleAt=now
        }
        if rawWindowStart==0 || gap>0.25 {rawWindowStart=now;rawReports=0;rawMaxGap=0}
        rawReports+=1;rawMaxGap=max(rawMaxGap,gap)
        if now-rawWindowStart>=5 {
            log("RAW_DELIVERY",rawReports,"seconds",String(format:"%.2f",now-rawWindowStart),"maxGapMs",Int(rawMaxGap*1000))
            rawWindowStart=now;rawReports=0;rawMaxGap=0
        }
        // The mouse button owns its scroll/drag independently of follow. A HUD-only
        // flag must not discard those held samples when follow is off.
        if controlVersion.usesHeldScroll && heldScroll.active {
            dwell.reset();scheduleDwell()
            heldScroll.settleTarget(now:now)
            if heldScroll.scrollable {
                let lines=heldScroll.sample(x:sample.angularX,y:sample.angularY,dt:Double(v[0])/1_000_000,now:now)
                finishHorizontalStrokeIfNeeded()
                if lines != 0 {
                    setCircleLight(true)
                    let x: Int32=heldScroll.horizontal ? lines:0
                    let y: Int32=heldScroll.horizontal ? 0:lines
                    postHeldScroll(x:x,y:y,at:heldScrollAnchor)
                }
            } else {
                // A native drag never starts inside an open scroll gesture.
                if heldScroll.startDrag(now:now) {finishNativeScroll(cancelled:true);transition(to:1,at:heldScrollAnchor ?? deliveryPoint ?? .zero)}
                if heldScroll.dragging {
                    let point=deliveryPoint ?? currentPointerOrigin()
                    let moved=postPointerMove(dx:sample.x,dy:sample.y,from:point)
                    if deliveryPoint != nil {deliveryPoint=moved}
                }
            }
            return
        }
        // Unheld HUD-only samples still never move or click the pointer.
        if v[3]&4 != 0 {return}
        if controlVersion.usesHeldScroll && pointerRouter.mouseButtonHeld {return}
        let wasFlick=flickScroll.active
        let flick=flickScroll.sample(x:sample.angularX,y:sample.angularY,dt:Double(v[0])/1_000_000,now:now,
            eligible:flickScrollEnabled && dwell.following && !pointerRouter.mouseButtonHeld && buttons==0)
        if flick.consumesPointer {
            if flickAnchor==nil {flickAnchor=deliveryPoint ?? currentPointerOrigin();setCircleLight(true)}
            dwell.reset();scheduleDwell()
            if flick.lines != 0 {for event in Self.wheelEvents(x:0,y:flick.lines,at:flickAnchor){event.post(tap:.cghidEventTap)}}
            return
        }
        flickAnchor=nil
        if wasFlick {setCircleLight(false);motionFilter.reset();dwell.reset();scheduleDwell();return}
        dwell.intent(sample.intent,now:now)
        handleFrame(x:sample.x,y:sample.y,b:buttons,stopX:sample.stopX,stopY:sample.stopY)
    }
    /// Bounded click telemetry: one line when the reason stop-to-click cannot
    /// act changes (never per frame), and the current reason in status.json.
    func noteClickGate(_ gate:String?) {
        guard gate != clickGate else{return}
        clickGate=gate
        log("CLICK_GATE",gate ?? "open")
        status()
    }
    func scheduleDwell(){
        dwellTimer?.invalidate();dwellTimer=nil
        guard ready,!restoring,!actionPause.paused,!recordingPointerPaused,!screenshot.ownsPointer,let due=dwell.nextDue else{return}
        dwellTimer=WandRunLoop.commonTimer(interval:max(0.001,due-ProcessInfo.processInfo.systemUptime),repeats:false){[weak self] _ in
            guard let self else{return};self.dwellTimer=nil
            guard self.ready,!self.restoring,!self.actionPause.paused,!self.screenshot.ownsPointer,!self.heldScroll.active,
                  WandClickGate.blocker(recordingPaused:self.recordingPointerPaused,mouseButtonHeld:self.pointerRouter.mouseButtonHeld,buttons:self.buttons,
                      hudSession:self.hudSession,hudShown:self.context.isActive,scrollActive:self.scrollActive,
                      hudOperating:self.hudButtonHeld || self.hudEntryPress || self.pointerInHUD)==nil,
                  AXIsProcessTrusted(),self.dwell.tick(now:ProcessInfo.processInfo.systemUptime) else{return}
            let point=self.currentPointerOrigin()
            self.transition(to:1,at:point);self.transition(to:0,at:point);log("HIGH_DWELL_CLICK")
            // Re-arms only when repeats are enabled; single-shot schedules nothing.
            self.scheduleDwell()
        }
    }
    func handleIMU(_ payload:String){
        guard ready,!restoring else{return}
        let parts=payload.split(separator:",",omittingEmptySubsequences:false)
        guard (5...7).contains(parts.count),let x=Double(parts[0]),let y=Double(parts[1]),let z=Double(parts[2]),let gyro=Double(parts[3]),let held=Int(parts[4]),(0...1).contains(held),abs(x)<=32768,abs(y)<=32768,abs(z)<=32768,(0...100_000).contains(gyro) else{return}
        let now=ProcessInfo.processInfo.systemUptime
        if parts.count==7,let mask=Int(parts[6]),(0...7).contains(mask) {
            reconcileMouseButtonHold(down:mask&1 != 0,now:now,reason:"sensor button state")
        } else if held==0 {reconcileMouseButtonHold(down:false,now:now,reason:"all buttons released")}
        if !motionFilter.configured,parts.count>=6,parts[5]=="0" || parts[5]=="1" {dwell.intent(parts[5]=="1",now:now);scheduleDwell()}
        motionFilter.observeGravity(x:x/8192,y:y/8192,z:z/8192,rotation:gyro/100)
        if restDiagnosticsRemaining>0 {
            restDiagnosticsRemaining-=1
            log("REST_SAMPLE",x/8192,y/8192,z/8192,"gyro",gyro/100,"held",held,"follow",dwell.following,"parked",restDetection.parked)
        }
        let wasParked=restDetection.parked
        let events=restDetection.update(x:x/8192,y:y/8192,z:z/8192,gyro:gyro/100,now:now,buttons:held==1 || scrollActive || buttons != 0 || screenshot.ownsPointer,idle:!dwell.following && !hudSession)
        if !wasParked && restDetection.parked {
            // Remember the choice rest is about to hide, before put-down acts.
            restFollow.cameToRest(following:dwell.following)
            log("TABLE_REST_CONFIRMED", "reference",restDetection.hasReference,"follow",dwell.following)
        }
        for event in events {
            switch event {
            case .probe:
                queue("wakeGyro();")
                probeTimer?.invalidate();probeTimer=WandRunLoop.commonTimer(interval:1.5,repeats:false){[weak self] _ in self?.queue("if(global.wandDeskSleeping)global.wandPowerDownGyro();else if(!moveLatched&&!hudOpen&&!scrollHeld)sleepGyro();")}
            case .pickedUp:
                probeTimer?.invalidate();probeTimer=nil
                // Ethan: waking returns to the state before rest. Mouse mode
                // comes back only if it was on, never while recording paused it.
                // Paused: rest detection still runs, but never changes follow or the HUD.
                guard !actionPause.paused else{log("AUTO_PICKUP_PAUSED");continue}
                let resume=restFollow.pickedUp(recordingPaused:recordingPointerPaused)
                guard !hudSession,resume else{log("AUTO_PICKUP_KEPT_STATE",dwell.following);continue}
                enterPointerMode();dwell.follow(true);queue("setMouseFollow(true);");log("AUTO_PICKUP")
            case .settling:
                dwell.inhibit(until:now+3);scheduleDwell()
            case .putDown:
                // Rest may sleep the LEDs, but an explicit HUD remains open.
                guard !hudSession,!actionPause.paused else{continue}
                cancelCircleScroll();enterPointerMode();dwell.follow(false);releaseButtons();queue("setMouseFollow(false);setHUDOpen(false);");log("AUTO_PUT_DOWN")
            }
        }
        if let sleeping=deskSleep.sample(parked:restDetection.parked,
                                        buttons:held==1 || scrollActive || buttons != 0 || screenshot.ownsPointer,now:now) {
            queue("if(typeof setWandDeskSleeping==='function')setWandDeskSleeping("+(sleeping ? "true":"false")+");")
            log(sleeping ? "DESK_SLEEP":"DESK_WAKE")
        }
        // Five-minute standby is button-wake only. Keep an explicit HUD,
        // review selection and dictation connected; sleep never owns those lanes.
        if deskSleep.deepSleeping,powerPolicyReady,standbyResume==nil,
           !hudSession,selectedReviewMode==nil,!recording.isRecording,!scrollActive,!screenshot.ownsPointer,held==0,buttons==0 {
            standbyResume=restFollow.remembered ?? dwell.following
            queue("if(typeof global.wandEnterDeepStandby!=='function'||!global.wandEnterDeepStandby())print('WAND_POWER_STANDBY_DENIED');")
            log("DEEP_STANDBY_REQUESTED")
        }
        // Rest detection owns pointer power only. It must never stop Agent Flow:
        // a still wand is not evidence that Ethan has finished speaking.

    }
    /// Ethan's "normal click": a plain single click, never inherited Command-click
    /// or an OS double-click made from two independent stop-to-click gestures.
    /// A mouse-button double-tap is classified by the wand router (recenter), not here.
    /// Ordinary native pointer motion includes relative distance as well as
    /// position. Some draggable controls consume deltaX/deltaY, not location.
    static func mouseMovementEvent(buttons:Int,from start:CGPoint,to end:CGPoint)->CGEvent? {
        let kind:CGEventType = buttons & 1 != 0 ? .leftMouseDragged : (buttons & 2 != 0 ? .rightMouseDragged : .mouseMoved)
        let button:CGMouseButton = buttons & 1 != 0 ? .left : (buttons & 2 != 0 ? .right : .left)
        guard let event=CGEvent(mouseEventSource:nil,mouseType:kind,mouseCursorPosition:end,mouseButton:button) else{return nil}
        event.setIntegerValueField(.mouseEventDeltaX,value:Int64((end.x-start.x).rounded()))
        event.setIntegerValueField(.mouseEventDeltaY,value:Int64((end.y-start.y).rounded()))
        return event
    }
    static func mouseButtonEvent(button:CGMouseButton,down:Bool,at point:CGPoint)->CGEvent? {
        let kind:CGEventType = button == .left ? (down ? .leftMouseDown:.leftMouseUp) : (down ? .rightMouseDown:.rightMouseUp)
        guard let event=CGEvent(mouseEventSource:nil,mouseType:kind,mouseCursorPosition:point,mouseButton:button) else{return nil}
        event.flags=[]
        event.setIntegerValueField(.mouseEventClickState,value:1)
        return event
    }
    func transition(to next: Int, at point: CGPoint) {
        // Paused: a held native button may still be released, never pressed.
        let next = actionPause.paused ? next & buttons : next
        for (mask, button) in [(1, CGMouseButton.left), (2, CGMouseButton.right)] where buttons & mask != next & mask {
            let down = next & mask != 0
            let event=Self.mouseButtonEvent(button:button,down:down,at:point)
            event?.post(tap:.cghidEventTap)
            log("BUTTON",button == .left ? "LEFT":"RIGHT",down ? "DOWN":"UP","flags",event?.flags.rawValue ?? 0,"clickCount",event?.getIntegerValueField(.mouseEventClickState) ?? 0)
        }
        buttons = next
    }
    func releaseButtons() { transition(to: 0, at: currentPointerOrigin()) }
    func stop() {
        cancelMouseExitClick()
        sendReview(review.cancel());reviewTimer?.invalidate();reviewTimer=nil
        dwell.follow(false);dwellTimer?.invalidate();dwellTimer=nil;probeTimer?.invalidate();probeTimer=nil
        pendingRecenter?.invalidate();pendingRecenter=nil;endScreenshot(reason:"receiver stopped",contextActive:false,forgetPress:true)
        guard !restoring else { return }; performPointer(pointerRouter.cancelAll());setCircleLight(false);restoring = true; retry?.cancel(); controls.cancel(); hudWatchdog?.invalidate(); releaseButtons()
        finishScroll();finishNativeScroll(cancelled:true);log("STOPPING"); status()
        if isSense {
            // Restore the program's sender, end the firmware session, then exit.
            if senseVirtual != nil { queue(restore) }
            senseLink?.end(restarting: FileManager.default.fileExists(atPath: support.appendingPathComponent("update.inprogress").path)); DispatchQueue.main.asyncAfter(deadline: .now() + 1) { exit(0) }; return
        }
        // Preserve the low-power runtime, restoring only its original output sender.
        if device?.state == .connected && tx != nil { chunks = []; queue(restore); DispatchQueue.main.asyncAfter(deadline: .now() + 3) { exit(0) } }
        else { exit(0) }
    }
}
let instanceLock = open(support.appendingPathComponent("receiver.lock").path, O_CREAT | O_RDWR, S_IRUSR | S_IWUSR)
guard instanceLock >= 0, flock(instanceLock, LOCK_EX | LOCK_NB) == 0 else { log("ALREADY_RUNNING"); exit(0) }
let application=NSApplication.shared
application.setActivationPolicy(.accessory)
let receiver = WandReceiver()
signal(SIGINT, SIG_IGN); signal(SIGTERM, SIG_IGN); signal(SIGUSR1, SIG_IGN)
let interrupt = DispatchSource.makeSignalSource(signal: SIGINT, queue: .main)
let terminate = DispatchSource.makeSignalSource(signal: SIGTERM, queue: .main)
interrupt.setEventHandler { receiver.stop() }; terminate.setEventHandler { receiver.stop() }
let maintenanceSignal = DispatchSource.makeSignalSource(signal: SIGUSR1, queue: .main)
maintenanceSignal.setEventHandler { receiver.maintenance() }
interrupt.resume(); terminate.resume(); maintenanceSignal.resume()
application.run()
