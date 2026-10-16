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
final class WandReceiver: NSObject, CBCentralManagerDelegate, CBPeripheralDelegate {
    var manager: CBCentralManager!
    var device: CBPeripheral?
    var tx: CBCharacteristic?
    var chunks: [Data] = []
    var writing = false, configuring = false
    var input = "", buttons = 0, reportCount = 0, movementCount = 0
    var restoring = false, generation = 0, retry: DispatchWorkItem?
    var lastTrusted = false, ready = false, legacySignaled = false
    var lastStatusKey = ""
    var lightMode = "unknown"
    var pointerDisplays:[CGRect]=[]
    var displayObserver:NSObjectProtocol?
    // LOW aiming delay, loop scrolling and consumed-click removal live in the
    // pure WandPointerRouter (wand-pointer-control.swift); this class only posts.
    let pointerRouter=WandPointerRouter()
    let dwell=WandDwellClick()
    let restDetection=WandRestDetection()
    var dwellTimer:Timer?,probeTimer:Timer?
    var restStopPending=false
    let review=WandReviewGesture()
    var reviewTimer:Timer?,reviewOriginY=0.0,appMode:String?
    var middleLastRelease = -100.0,middlePressedAt=0.0,middleDoubleConsumed=false
    var circleLight=false
    var circleTimer:Timer?,lowDelayTimer:Timer?
    var lastClickTime = 0.0, clickCount: Int64 = 0
    var lastClickPoint = CGPoint.zero
    var heartbeat: Timer?
    let controls = WandControlTransport()
    let context = WandContextListener()
    let recording = WandRecordingState(cache:support.appendingPathComponent("recording-state.json"))
    var pointerInHUD=false, middleOperating=false, middleSecondTap=false
    var hudSession=false,hudEntryPress=false
    var hudEntryPressStarted=0.0
    var navX=0.0,navY=0.0,navOriginX=0.0,navOriginY=0.0,operationOriginX=0.0,operationOriginY=0.0
    var middleX=0.0,middleY=0.0
    var middleHold:Timer?, middleTap:Timer?
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
    let uart = CBUUID(string: "6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
    var restore: String {
        let red = FileManager.default.fileExists(atPath:support.appendingPathComponent("update.inprogress").path)
            ? "global.WAND_UPDATING=true;if(typeof updateLights==='function')updateLights();" : ""
        return red + "if(global.wandBridgeOriginalSend){mouse.send=global.wandBridgeOriginalSend;delete global.wandBridgeOriginalSend;}print('WAND_BRIDGE_RESTORED');"
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
        // Each complete statement is small; the old single giant REPL function
        // exceeded the device's available memory during repeated live updates.
        for command in source.split(separator:"\n") where command.trimmingCharacters(in:.whitespaces) != "print('WAND_MODE_ROUTING_READY');" {queue(String(command))}
        queue("global.WAND_BRIDGE_REVISION='"+bridgeRevision(source)+"';print('WAND_MODE_ROUTING_READY');")
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
            if !active && self.hudSession {self.hudSession=false;self.hudEntryPress=false;self.hudActive=false;self.navX=0;self.navY=0;self.stopHUDWatchdog();self.middleTap?.invalidate();self.middleTap=nil;self.middleHold?.invalidate();self.middleHold=nil;self.pointerInHUD=false;self.middleOperating=false}
            if active && !self.hudSession {self.cancelCircleScroll();self.hudSession=true;self.navX=0;self.navY=0;self.resumeHUDNavigation()}
            self.queue("if(typeof setHUDOpen==='function')setHUDOpen("+(active ? "true":"false")+");")
        }
        context.start()
        context.onModeChange = {[weak self] mode in
            guard let self else{return};self.sendReview(self.review.cancel());self.appMode=mode
            self.queue("global.wandAppMode="+(mode.map{ "'"+$0+"'" } ?? "undefined")+";updateLights();")
            if mode != nil {self.resumeHUDNavigation()}
        }
        recording.onChange = {[weak self] active in
            guard let self else{return}
            log("RECORDING_STATE",active);self.dwell.reset();self.scheduleDwell();self.syncRecordingLight();self.status()
            if !active {self.restStopPending=false}
        }
        recording.start()
        lastTrusted = AXIsProcessTrusted()
        log("STARTED", ProcessInfo.processInfo.processIdentifier, "ACCESSIBILITY", lastTrusted)
        if CommandLine.arguments.contains("--request-permissions") {
            let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary
            _ = AXIsProcessTrustedWithOptions(options)
        }
        manager = CBCentralManager(delegate: self, queue: nil)
        heartbeat = Timer.scheduledTimer(withTimeInterval: 5, repeats: true) { [weak self] _ in
            guard let self else { return }
            let trusted = AXIsProcessTrusted()
            if self.lastTrusted != trusted { self.lastTrusted = trusted; log("ACCESSIBILITY", trusted); self.status() }
            self.recording.refresh()
            self.status()
            if !self.ready && self.manager.state == .poweredOn && self.device == nil { self.connect() }
        }
        status()
    }
    func syncRecordingLight() {
        guard ready,!restoring else{return}
        queue("setWandRecording("+(recording.isRecording ? "true":"false")+");")
    }
    // Developer maintenance uses the existing BLE owner, so diagnosis and small
    // device updates do not disconnect the user's working pointer. Only consume
    // a same-user regular file with private permissions; never follow symlinks.
    func maintenance() {
        guard ready,!restoring else {log("MAINTENANCE_NOT_READY");return}
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
        if command.hasPrefix(marker) {
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
        let key = "\(device?.state == .connected)|\(ready)|\(AXIsProcessTrusted())|\(CBCentralManager.authorization.rawValue)|\(recording.isRecording)|\(lightMode)"
        guard key != lastStatusKey else { return }
        lastStatusKey = key
        let value: [String: Any] = ["pid": ProcessInfo.processInfo.processIdentifier, "connected": device?.state == .connected,
            "ready": ready, "recording":recording.isRecording, "lightMode":lightMode, "accessibility": AXIsProcessTrusted(), "bluetoothAuthorization": CBCentralManager.authorization.rawValue,
            "updatedAt": ISO8601DateFormatter().string(from: Date())]
        if let data = try? JSONSerialization.data(withJSONObject: value, options: [.sortedKeys]) { try? data.write(to: support.appendingPathComponent("status.json"), options: .atomic) }
    }
    func centralManagerDidUpdateState(_ c: CBCentralManager) {
        log("RADIO_STATE", c.state.rawValue)
        status()
        if c.state == .poweredOn { connect() }
        else { reset(); device = nil; status() }
    }
    func connect() {
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
        sendReview(review.cancel());appMode=nil;reviewTimer?.invalidate();reviewTimer=nil;middleLastRelease = -100;middleDoubleConsumed=false
        dwell.follow(false);dwellTimer?.invalidate();dwellTimer=nil
        probeTimer?.invalidate();probeTimer=nil;restDetection.reset();restStopPending=false
        performPointer(pointerRouter.cancelAll());setCircleLight(false)
        lightMode="disconnected"
        hudSession=false;hudEntryPress=false
        finishScroll()
        controls.cancel(); hudActive = false; hudWatchdog?.invalidate(); hudWatchdog = nil
        generation += 1; middleHold?.invalidate();middleTap?.invalidate();middleHold=nil;middleTap=nil;middleOperating=false;pointerInHUD=false;controls.persistent("dismiss");releaseButtons(); ready = false; tx = nil; chunks = []; input = ""; writing = false; configuring = false
    }
    func reconnect() {
        if let p = device { manager.cancelPeripheralConnection(p) }
        reset(); device = nil; status()
        retry?.cancel()
        let item = DispatchWorkItem { [weak self] in self?.connect() }; retry = item
        DispatchQueue.main.asyncAfter(deadline: .now() + 3, execute: item)
    }
    func centralManager(_ c: CBCentralManager, didConnect p: CBPeripheral) {
        guard device === p, !restoring else { c.cancelPeripheralConnection(p); return }
        log("CONNECTED_TO_PUCK"); deadline(seconds: 60); status(); p.discoverServices([uart])
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
        log("CHECKING_RUNTIME", runtimeVersion)
        let handshake = "if(global.WAND_RUNTIME_VERSION===\"" + runtimeVersion + "\"){if(!global.wandBridgeOriginalSend)global.wandBridgeOriginalSend=mouse.send;mouse.send=function(x,y,b,cb){Bluetooth.println(\"@WAND \"+x+\",\"+y+\",\"+b);if(cb)cb();};if(!connected)onConnect();print(\"WAND_BRIDGE_READY\");}else print(\"WAND_NEEDS_CONFIG\");"
        queue(handshake)
    }
    func queue(_ command: String) {
        let data = Data(("\u{10}" + command + "\n").utf8)
        for offset in stride(from: 0, to: data.count, by: 20) { chunks.append(data.subdata(in: offset..<min(offset + 20, data.count))) }
        sendNext()
    }
    func sendNext() {
        guard !writing, let p = device, p.state == .connected, let characteristic = tx, !chunks.isEmpty else { return }
        writing = true; p.writeValue(chunks.removeFirst(), for: characteristic, type: .withResponse)
    }
    func peripheral(_ p: CBPeripheral, didWriteValueFor c: CBCharacteristic, error: Error?) {
        guard device === p else { return }; writing = false
        if let error { log("WRITE_FAILED", error.localizedDescription); reconnect(); return }
        sendNext()
    }
    func peripheral(_ p: CBPeripheral, didUpdateValueFor c: CBCharacteristic, error: Error?) {
        guard device === p, error == nil, let bytes = c.value, let text = String(data: bytes, encoding: .utf8) else { return }
        input += text.replacingOccurrences(of: "\r", with: "")
        if input.count > 16384 { input = String(input.suffix(4096)) }
        while let newline = input.firstIndex(of: "\n") {
            let line = String(input[..<newline]); input.removeSubrange(...newline)
            if line.contains("Error") || line.contains("OUT OF MEMORY") || line.contains("Uncaught") { log("DEVICE_ERROR", line) }
            if line.contains("WAND_NEEDS_CONFIG") { log("UPLOADING_RUNTIME", commands.count); for command in commands { queue(command) } }
            if line.hasSuffix("WAND_BRIDGE_READY") {
                queue("E.setFlags({pretokenise:1});global.wandDoubleClickSeconds="+String(min(0.3,NSEvent.doubleClickInterval))+";if(global.WAND_BRIDGE_REVISION==='"+bridgeRevision(modeBridge)+"')print('WAND_MODE_ROUTING_READY');else print('WAND_PATCH_NEEDED');")
            }
            if line.hasSuffix("WAND_PATCH_NEEDED") {loadModeBridge()}
            if line.hasSuffix("WAND_MODE_ROUTING_READY") {
                ready=true;generation+=1;log("RUNTIME_READY");syncRecordingLight();status()
                if context.isActive {hudSession=true;resumeHUDNavigation()}
                queue("global.WAND_UPDATING=false;setHUDOpen("+(context.isActive ? "true":"false")+");updateLights();")
            }
            if line.hasPrefix("WAND_DIAG ") || line.hasPrefix(">WAND_DIAG ") || line.hasPrefix("WAND_CALLBACK_MATCH ") || line.hasPrefix(">WAND_CALLBACK_MATCH ") {log("DEVICE",line)}
            if line.hasPrefix("WAND_BUTTON_STATE ") || line.hasPrefix(">WAND_BUTTON_STATE ") {log("DEVICE",line)}
            if let marker=line.range(of:"WAND_LIGHT_STATE ") {
                let payload=String(line[marker.upperBound...])
                let mode=String(payload.prefix{!$0.isWhitespace})
                if ["update","calibration","disconnected","scroll","app","mouse","hud","recording","idle"].contains(mode),
                   let first=payload.firstIndex(of:"["),let last=payload[first...].firstIndex(of:"]"),
                   let levels=try? JSONDecoder().decode([Double].self,from:Data(payload[first...last].utf8)),levels.count==3 {
                    lightMode=mode;log("DEVICE_LIGHT",mode,levels);status()
                }
            }
            if line.hasSuffix("WAND_RECORDING_LIGHT 0") || line.hasSuffix("WAND_RECORDING_LIGHT 1") {log("DEVICE",line)}
            if line.hasSuffix("@POINTER_MODE") {enterPointerMode()}
            if let marker=line.range(of:"@FOLLOW ") {
                let value=line[marker.upperBound...].trimmingCharacters(in:.whitespaces)
                if value=="0" || value=="1" {dwell.follow(value=="1");scheduleDwell()}
            }
            if let marker=line.range(of:"@IMU ") {handleIMU(String(line[marker.upperBound...]))}
            if let marker=line.range(of:"@REVIEW "),appMode=="vsCode" {
                let value=line[marker.upperBound...].trimmingCharacters(in:.whitespaces)
                if value=="0" || value=="1" {
                    if value=="1" {reviewOriginY=navY;if hudActive {controls.persistent("park");hudActive=false;stopHUDWatchdog()}}
                    let wasFiles=review.files
                    sendReview(review.button(down:value=="1",now:ProcessInfo.processInfo.systemUptime))
                    if value=="0" {resumeHUDNavigation()}
                    if wasFiles != review.files {queue("global.wandReviewFiles="+(review.files ? "true":"false")+";updateLights();");log("VSCODE_REVIEW_MODE",review.mode)}
                    if reviewTimer==nil {reviewTimer=Timer.scheduledTimer(withTimeInterval:0.2,repeats:true){[weak self] _ in guard let self else{return};self.sendReview(self.review.tick(now:ProcessInfo.processInfo.systemUptime))}}
                }
            }
            if line.contains("WAND_CALIBRATED") { log(line) }
            if let marker=line.range(of:"@BOTTOM ") {
                let value=String(line[marker.upperBound...]).trimmingCharacters(in:.whitespaces)
                // The device prints each edge before the click it emits on release,
                // so a consumed (scrolled) hold's endpoint click is dropped by order.
                if value=="0" || value=="1" {restStopPending=false;dwell.reset();scheduleDwell();performPointer(pointerRouter.bottom(down:value=="1"))}
            }
            if let marker=line.range(of:"@MIDDLE "){cancelCircleScroll();handleMiddle(String(line[marker.upperBound...]))}
            if let marker=line.range(of:"@NAV "){handleNavigation(String(line[marker.upperBound...]))}
            if let marker = line.range(of: "@SCROLL ") { handleScroll(String(line[marker.upperBound...])) }
            if let marker = line.range(of: "@MOVE ") { handleMove(String(line[marker.upperBound...])) }
            if let marker = line.range(of: "@HUD ") { handleHUD(String(line[marker.upperBound...])) }
            if let marker = line.range(of: "@STT "), !restoring, AXIsProcessTrusted() {
                cancelCircleScroll()
                let value=String(line[marker.upperBound...]).trimmingCharacters(in: .whitespaces)
                if value == "0" || value == "1" { log("SPEECH_BUTTON", value, controls.speech(down:value == "1") ? "SENT" : "UNAVAILABLE") }
            }
            if let marker = line.range(of: "@WAND ") { handle(String(line[marker.upperBound...])) }
            if restoring && line.contains("WAND_BRIDGE_RESTORED") { log("STOPPED"); exit(0) }
        }
    }
    // MIDDLE latches the HUD, then operates the selected native card.
    var hudDoubleClickInterval:Double {max(0.25,min(0.3,NSEvent.doubleClickInterval))}
    func handleMove(_ payload:String) {
        guard !restoring,!scrollActive,AXIsProcessTrusted() else{return}
        let f=payload.split(separator:",",omittingEmptySubsequences:false)
        guard f.count==3,let x=Double(f[1]),let y=Double(f[2]),x.isFinite,y.isFinite,abs(x)<=7_200_000,abs(y)<=7_200_000 else{return}
        middleX=x/1000;middleY=y/1000
        switch f[0] {
        case "B":
            if middleTap != nil {
                middleTap?.invalidate();middleTap=nil
                middleHold?.invalidate();middleHold=nil
                pointerInHUD=false;middleOperating=false;middleSecondTap=false
                stopHUDWatchdog();releaseButtons()
                controls.persistent("dismiss")
                hudSession=false;hudEntryPress=false;hudActive=false
                queue("setHUDOpen(false);")
                log("HUD_DOUBLE_CLICK_DISMISSED")
                return
            }
            guard context.isActive || hudSession else{return}
            pointerInHUD=true;middleOperating=false
            middleSecondTap=false
            middleHold=Timer.scheduledTimer(withTimeInterval:0.22,repeats:false){[weak self] _ in
                guard let self,self.pointerInHUD,(self.context.isActive || self.hudSession) else{return}
                self.middleOperating=true;self.controls.persistent("press")
                self.controls.persistent("motion",x:self.middleX,y:self.middleY)
            }
            startHUDWatchdog()
        case "U":
            guard pointerInHUD else{return};hudLastUpdate=Date()
            if middleOperating {controls.persistent("motion",x:middleX,y:middleY)}
        case "E":
            guard pointerInHUD else{return};pointerInHUD=false
            middleHold?.invalidate();middleHold=nil;stopHUDWatchdog()
            if middleOperating {controls.persistent("motion",x:middleX,y:middleY);controls.persistent("release");resumeHUDNavigation()}
            else {
                middleTap=Timer.scheduledTimer(withTimeInterval:hudDoubleClickInterval,repeats:false){[weak self] _ in
                    guard let self else{return};self.middleTap=nil
                    guard self.context.isActive,!self.restoring else{return}
                    self.controls.persistent("press");self.controls.persistent("release");self.resumeHUDNavigation()
                }
            }
            middleOperating=false
        default:break
        }
    }
    func enterPointerMode(){
        sendReview(review.cancel());appMode=nil;reviewTimer?.invalidate();reviewTimer=nil
        queue("global.wandAppMode=undefined;updateLights();")
        hudSession=false;hudEntryPress=false;hudActive=false;pointerInHUD=false;middleOperating=false
        middleTap?.invalidate();middleTap=nil;middleHold?.invalidate();middleHold=nil
        stopHUDWatchdog();controls.persistent("dismiss")
        log("POINTER_MODE_ENTERED")
    }
    func handleMiddle(_ payload:String){
        guard !restoring,!scrollActive,AXIsProcessTrusted() else{return}
        switch payload.trimmingCharacters(in:.whitespaces){
        case "1":
            let now=ProcessInfo.processInfo.systemUptime;middlePressedAt=now
            if now-middleLastRelease<=hudDoubleClickInterval {
                middleLastRelease = -100;middleDoubleConsumed=true
                middleTap?.invalidate();middleTap=nil;middleHold?.invalidate();middleHold=nil
                controls.persistent("park");stopHUDWatchdog();hudActive=false;pointerInHUD=false;middleOperating=false;hudEntryPress=false
                if appMode != nil {enterPointerMode();queue("setHUDOpen(false);")}
                else {hudSession=true;controls.persistent("appSpecific");queue("setMouseFollow(false);setHUDOpen(true);")}
                return
            }
            if !hudSession && !context.isActive {
                hudSession=true;hudEntryPress=true;hudEntryPressStarted=ProcessInfo.processInfo.systemUptime;navigationOpenedHUD=true;navX=0;navY=0
                controls.persistent("open");resumeHUDNavigation()
                queue("setHUDOpen(true);")
                return
            }
            hudSession=true;hudEntryPress=false
            if hudActive {controls.persistent("park");hudActive=false;stopHUDWatchdog()}
            operationOriginX=navX;operationOriginY=navY
            handleMove("B,0,0")
        case "0":
            if middleDoubleConsumed {middleDoubleConsumed=false;return}
            middleLastRelease=ProcessInfo.processInfo.systemUptime-middlePressedAt<0.14 ? ProcessInfo.processInfo.systemUptime : -100
            if hudEntryPress {
                hudEntryPress=false;navigationOpenedHUD=false
                // Firmware delays a held Middle down by 80 ms to arbitrate the scroll chord.
                // A short entry tap latches navigation; a >=220 ms physical hold selects on up.
                if ProcessInfo.processInfo.systemUptime-hudEntryPressStarted >= 0.22-0.08 {
                    controls.persistent("park");hudActive=false;stopHUDWatchdog()
                    controls.persistent("press");controls.persistent("release")
                    resumeHUDNavigation();log("HUD_ENTRY_HOLD_SELECTED")
                }
                return
            }
            handleMove("E,"+String((navX-operationOriginX)*1000)+","+String((navY-operationOriginY)*1000))
        default:break
        }
    }
    func handleNavigation(_ payload:String){
        let f=payload.split(separator:",")
        guard f.count==2,let x=Double(f[0]),let y=Double(f[1]),x.isFinite,y.isFinite,abs(x)<=7_200_000,abs(y)<=7_200_000 else{return}
        navX=x/1000;navY=y/1000
        if appMode=="vsCode" && review.isHeld {sendReview(review.motion(y:navY-reviewOriginY,now:ProcessInfo.processInfo.systemUptime));return}
        guard !restoring,!scrollActive,hudSession else{return}
        if pointerInHUD {
            handleMove("U,"+String((navX-operationOriginX)*1000)+","+String((navY-operationOriginY)*1000))
        }else if hudActive {
            hudLastUpdate=Date();controls.persistent("motion",x:navX-navOriginX,y:navY-navOriginY)
        }
    }
    func resumeHUDNavigation(){
        guard hudSession,!scrollActive,!restoring else{return}
        navOriginX=navX;navOriginY=navY;hudActive=true
        controls.persistent("navigate");startHUDWatchdog()
    }
    // MIDDLE opens the grid and directly moves its existing liquid outline.
    func handleHUD(_ payload:String) {
        guard !restoring,!scrollActive,AXIsProcessTrusted() else{return}
        let f=payload.split(separator:",",omittingEmptySubsequences:false)
        guard f.count==3,let x=Double(f[1]),let y=Double(f[2]),x.isFinite,y.isFinite,abs(x)<=7_200_000,abs(y)<=7_200_000 else{return}
        switch f[0] {
        case "B":
            middleTap?.invalidate();middleTap=nil;middleHold?.invalidate();middleHold=nil
            if middleOperating {controls.persistent("release");middleOperating=false}
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
        hudWatchdog=Timer.scheduledTimer(withTimeInterval:0.25,repeats:true){[weak self] timer in
            guard let self else{timer.invalidate();return}
            if Date().timeIntervalSince(self.hudLastUpdate)>0.8 {
                self.middleHold?.invalidate();self.middleHold=nil
                self.middleTap?.invalidate();self.middleTap=nil
                self.controls.persistent("dismiss");self.hudActive=false
                self.pointerInHUD=false;self.middleOperating=false;timer.invalidate()
            }
        }
    }
    func stopHUDWatchdog(){hudWatchdog?.invalidate();hudWatchdog=nil}
    // Ordinary wheel events use the same line units as Agentic Mouse.
    // Keep fractional lines so slow motion still accumulates into wheel steps.
    func handleScroll(_ payload:String){
        guard !restoring,AXIsProcessTrusted() else{return}
        let f=payload.split(separator:",",omittingEmptySubsequences:false)
        guard f.count==3,let x=Double(f[1]),let y=Double(f[2]),x.isFinite,y.isFinite,abs(x)<=7_200_000,abs(y)<=7_200_000 else{return}
        switch f[0]{
        case "B":
            sendReview(review.cancel());cancelCircleScroll();finishScroll();hudEntryPress=false;middleTap?.invalidate();middleTap=nil;middleHold?.invalidate();middleHold=nil
            if hudActive {controls.persistent("park");if navigationOpenedHUD{controls.persistent("dismiss");hudSession=false;queue("setHUDOpen(false);")}}
            else if middleOperating {controls.persistent("release")}
            hudActive=false;pointerInHUD=false;middleOperating=false;navigationOpenedHUD=false
            stopHUDWatchdog();releaseButtons()
            scrollActive=true;scrollX=x/1000;scrollY=y/1000;scrollFractionX=0;scrollFractionY=0
            scrollPostedX=0;scrollPostedY=0
            scrollUpdated=Date();log("SCROLL_BEGIN")
            scrollWatchdog=Timer.scheduledTimer(withTimeInterval:0.25,repeats:true){[weak self] _ in
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
            if f[0]=="E"{finishScroll()}
        default:break
        }
    }
    // Ordinary mice deliver one wheel axis at a time. Mixed-axis line events
    // can be reduced to the dominant direction by native scrolling views.
    // Send both components back-to-back so diagonal wand motion retains both.
    static func wheelEvents(x:Int32,y:Int32)->[CGEvent] {
        guard let source=CGEventSource(stateID:.hidSystemState) else{return []}
        var events:[CGEvent]=[]
        if x != 0, let event=CGEvent(scrollWheelEvent2Source:source,units:.line,wheelCount:2,wheel1:0,wheel2:x,wheel3:0) {events.append(event)}
        if y != 0, let event=CGEvent(scrollWheelEvent2Source:source,units:.line,wheelCount:2,wheel1:y,wheel2:0,wheel3:0) {events.append(event)}
        return events
    }
    func postScroll(x:Int32,y:Int32){
        for event in Self.wheelEvents(x:x,y:y) {event.post(tap:.cghidEventTap)}
        scrollPostedX+=Int(x);scrollPostedY+=Int(y)
    }
    func finishScroll(){
        if scrollActive{log("SCROLL_END lines",scrollPostedX,scrollPostedY)}
        let wasActive=scrollActive
        scrollActive=false;scrollWatchdog?.invalidate();scrollWatchdog=nil
        if wasActive {resumeHUDNavigation()}
    }
    func refreshPointerDisplays() {
        var ids=[CGDirectDisplayID](repeating:0,count:32),count:UInt32=0
        if CGGetActiveDisplayList(UInt32(ids.count),&ids ,&count) == .success {
            pointerDisplays=ids.prefix(Int(count)).map{CGDisplayBounds($0)}.filter{!$0.isEmpty}
        }
    }
    func setCircleLight(_ active:Bool) {
        guard circleLight != active else{return};circleLight=active
        if ready && !restoring {queue("global.wandCircleScrolling="+(active ? "true":"false")+";updateLights();")}
        if active && circleTimer == nil {
            circleTimer=Timer.scheduledTimer(withTimeInterval:0.1,repeats:true){[weak self] _ in
                guard let self else{return}
                self.performPointer(self.pointerRouter.tick(now:ProcessInfo.processInfo.systemUptime))
            }
        } else if !active {circleTimer?.invalidate();circleTimer=nil}
    }
    /// Scroll chord, HUD and speech take over: drop unshown LOW motion and any circle.
    func cancelCircleScroll(){restStopPending=false;dwell.reset();scheduleDwell();performPointer(pointerRouter.interrupt());setCircleLight(false)}
    func sendReview(_ requests:[WandReviewGesture.Request]){
        for request in requests {
            guard let app=NSRunningApplication.runningApplications(withBundleIdentifier:"com.microsoft.VSCode").first,
                  app.isActive,let application=app.bundleURL else{continue}
            var url=URLComponents();url.scheme="vscode";url.host="ethansk.better-git-vscode";url.path="/wand-review/"+request.phase
            url.queryItems=[URLQueryItem(name:"version",value:"1"),URLQueryItem(name:"id",value:request.id),URLQueryItem(name:"seq",value:String(request.seq)),URLQueryItem(name:"direction",value:request.direction),URLQueryItem(name:"mode",value:request.mode)]
            guard let target=url.url else{continue}
            let config=NSWorkspace.OpenConfiguration();config.activates=false;config.addsToRecentItems=false
            NSWorkspace.shared.open([target],withApplicationAt:application,configuration:config){_,error in if let error {log("VSCODE_REVIEW_FAILED",error.localizedDescription)}}
            log("VSCODE_REVIEW_SENT",request.phase,request.direction,request.mode)
        }
    }
    func performPointer(_ actions:[WandPointerRouter.Action]) {
        // A drain can contain several frames. Carry a locally clamped point
        // through the batch; posting CGEvents need not update the system cursor
        // synchronously before the next frame is posted.
        var point=WandPointerBounds.clamp(CGEvent(source:nil)?.location ?? .zero,to:pointerDisplays)
        for action in actions {
            switch action {
            case .move(let dx,let dy): point=postPointerMove(dx:dx,dy:dy,from:point)
            case .scroll(let lines): postScroll(x:0,y:lines)
            case .circleLight(let on): setCircleLight(on)
            }
        }
        scheduleLowDelay()
    }
    // One one-shot timer for the earliest delayed LOW frame; never runs when idle.
    func scheduleLowDelay() {
        lowDelayTimer?.invalidate();lowDelayTimer=nil
        guard let due=pointerRouter.nextDue else{return}
        lowDelayTimer=Timer.scheduledTimer(withTimeInterval:max(0,due-ProcessInfo.processInfo.systemUptime),repeats:false){[weak self] _ in
            guard let self else{return}
            self.lowDelayTimer=nil
            self.performPointer(self.pointerRouter.drain(now:ProcessInfo.processInfo.systemUptime))
        }
    }
    @discardableResult
    func postPointerMove(dx:Int,dy:Int,from point:CGPoint)->CGPoint {
        let newPoint=WandPointerBounds.clamp(CGPoint(x:point.x+CGFloat(dx),y:point.y+CGFloat(dy)),to:pointerDisplays)
        let kind:CGEventType = buttons & 1 != 0 ? .leftMouseDragged : (buttons & 2 != 0 ? .rightMouseDragged : .mouseMoved)
        let button:CGMouseButton = buttons & 1 != 0 ? .left : (buttons & 2 != 0 ? .right : .left)
        CGEvent(mouseEventSource:nil,mouseType:kind,mouseCursorPosition:newPoint,mouseButton:button)?.post(tap:.cghidEventTap)
        movementCount += 1
        if movementCount == 1 || movementCount % 100 == 0 { log("MOVEMENT_REPORTS_POSTED", movementCount) }
        return newPoint
    }
    func handle(_ payload: String) {
        let values = payload.split(separator: ",", omittingEmptySubsequences: false)
        guard values.count == 3, let x = Int(values[0]), let y = Int(values[1]), let b = Int(values[2]),
              (-127...127).contains(x), (-127...127).contains(y), (0...3).contains(b), !restoring, !scrollActive, AXIsProcessTrusted() else { return }
        reportCount += 1
        if reportCount == 1 { log("FIRST_DEVICE_REPORT_VALIDATED") }
        let point = WandPointerBounds.clamp(CGEvent(source: nil)?.location ?? .zero,to:pointerDisplays)
        // The router may drop a consumed hold's endpoint click; button changes are
        // applied before motion, at the position already shown.
        let routed=pointerRouter.frame(dx:x,dy:y,buttons:b,hud:hudSession,now:ProcessInfo.processInfo.systemUptime)
        dwell.move(dx:x,dy:y,now:ProcessInfo.processInfo.systemUptime,eligible:!pointerRouter.bottomHeld && b==0 && !hudSession && !scrollActive)
        scheduleDwell()
        if routed.buttons != b {log("CONSUMED_HOLD_CLICK_DROPPED")}
        transition(to: routed.buttons, at: point)
        performPointer(routed.actions)
    }
    func scheduleDwell(){
        dwellTimer?.invalidate();dwellTimer=nil
        guard ready,!restoring,let due=dwell.nextDue else{return}
        dwellTimer=Timer.scheduledTimer(withTimeInterval:max(0.001,due-ProcessInfo.processInfo.systemUptime),repeats:false){[weak self] _ in
            guard let self else{return};self.dwellTimer=nil
            guard self.ready,!self.restoring,!self.pointerRouter.bottomHeld,!self.hudSession,!self.scrollActive,self.buttons==0,AXIsProcessTrusted(),self.dwell.tick(now:ProcessInfo.processInfo.systemUptime) else{return}
            let point=WandPointerBounds.clamp(CGEvent(source:nil)?.location ?? .zero,to:self.pointerDisplays)
            self.transition(to:1,at:point);self.transition(to:0,at:point);log("HIGH_DWELL_CLICK")
        }
    }
    func handleIMU(_ payload:String){
        guard ready,!restoring else{return}
        let parts=payload.split(separator:",",omittingEmptySubsequences:false)
        guard (5...6).contains(parts.count),let x=Double(parts[0]),let y=Double(parts[1]),let z=Double(parts[2]),let gyro=Double(parts[3]),let held=Int(parts[4]),(0...1).contains(held),abs(x)<=32768,abs(y)<=32768,abs(z)<=32768,(0...100_000).contains(gyro) else{return}
        let now=ProcessInfo.processInfo.systemUptime
        if parts.count==6,parts[5]=="0" || parts[5]=="1" {dwell.intent(parts[5]=="1",now:now);scheduleDwell()}
        let events=restDetection.update(x:x/8192,y:y/8192,z:z/8192,gyro:gyro/100,now:now,buttons:held==1 || scrollActive || buttons != 0,idle:!dwell.following && !recording.isRecording && !hudSession)
        for event in events {
            switch event {
            case .probe:
                restStopPending=false
                queue("wakeGyro();")
                probeTimer?.invalidate();probeTimer=Timer.scheduledTimer(withTimeInterval:1.5,repeats:false){[weak self] _ in self?.queue("if(!moveLatched&&!hudOpen&&!scrollHeld)sleepGyro();")}
            case .pickedUp:
                restStopPending=false
                probeTimer?.invalidate();probeTimer=nil
                guard !hudSession else{continue}
                enterPointerMode();dwell.follow(true);queue("setMouseFollow(true);");log("AUTO_PICKUP")
            case .settling:
                dwell.inhibit(until:now+3);scheduleDwell()
            case .putDown:
                cancelCircleScroll();enterPointerMode();dwell.follow(false);releaseButtons();queue("setMouseFollow(false);setHUDOpen(false);");log("AUTO_PUT_DOWN")
                restStopPending=recording.isRecording
            }
        }
        // Stopping dictation deserves stronger evidence than parking the
        // pointer: three more seconds of a quiet desk, cancelled by pickup or
        // any control. Send one ordinary Top tap, never a blind toggle.
        if restStopPending,restDetection.parked,let since=restDetection.deskQuietSince,now-since>=3,recording.isRecording {
            restStopPending=false
            let sent=controls.speech(down:true)
            DispatchQueue.main.asyncAfter(deadline:.now()+0.08){[weak self] in _=self?.controls.speech(down:false)}
            log("AUTO_RECORDING_STOP_REQUEST",sent)
        }
    }
    func transition(to next: Int, at point: CGPoint) {
        for (mask, button) in [(1, CGMouseButton.left), (2, CGMouseButton.right)] where buttons & mask != next & mask {
            let down = next & mask != 0
            let kind: CGEventType = button == .left ? (down ? .leftMouseDown : .leftMouseUp) : (down ? .rightMouseDown : .rightMouseUp)
            let event = CGEvent(mouseEventSource: nil, mouseType: kind, mouseCursorPosition: point, mouseButton: button)
            if button == .left {
                if down {
                    let now = ProcessInfo.processInfo.systemUptime
                    let close = hypot(point.x - lastClickPoint.x, point.y - lastClickPoint.y) <= 4
                    clickCount = close && now - lastClickTime <= NSEvent.doubleClickInterval ? clickCount + 1 : 1
                    lastClickTime = now; lastClickPoint = point
                }
                event?.setIntegerValueField(.mouseEventClickState, value: clickCount)
            }
            event?.post(tap: .cghidEventTap)
            log("BUTTON", button == .left ? "LEFT" : "RIGHT", down ? "DOWN" : "UP")
        }
        buttons = next
    }
    func releaseButtons() { transition(to: 0, at: CGEvent(source: nil)?.location ?? .zero) }
    func stop() {
        sendReview(review.cancel());reviewTimer?.invalidate();reviewTimer=nil
        dwell.follow(false);dwellTimer?.invalidate();dwellTimer=nil;probeTimer?.invalidate();probeTimer=nil;restStopPending=false
        guard !restoring else { return }; performPointer(pointerRouter.cancelAll());setCircleLight(false);restoring = true; retry?.cancel(); controls.cancel(); hudWatchdog?.invalidate(); releaseButtons()
        finishScroll();log("STOPPING"); status()
        // Preserve the low-power runtime, restoring only its original output sender.
        if device?.state == .connected && tx != nil { chunks = []; queue(restore); DispatchQueue.main.asyncAfter(deadline: .now() + 3) { exit(0) } }
        else { exit(0) }
    }
}
let instanceLock = open(support.appendingPathComponent("receiver.lock").path, O_CREAT | O_RDWR, S_IRUSR | S_IWUSR)
guard instanceLock >= 0, flock(instanceLock, LOCK_EX | LOCK_NB) == 0 else { log("ALREADY_RUNNING"); exit(0) }
let receiver = WandReceiver()
signal(SIGINT, SIG_IGN); signal(SIGTERM, SIG_IGN); signal(SIGUSR1, SIG_IGN)
let interrupt = DispatchSource.makeSignalSource(signal: SIGINT, queue: .main)
let terminate = DispatchSource.makeSignalSource(signal: SIGTERM, queue: .main)
interrupt.setEventHandler { receiver.stop() }; terminate.setEventHandler { receiver.stop() }
let maintenanceSignal = DispatchSource.makeSignalSource(signal: SIGUSR1, queue: .main)
maintenanceSignal.setEventHandler { receiver.maintenance() }
interrupt.resume(); terminate.resume(); maintenanceSignal.resume()
RunLoop.main.run()
