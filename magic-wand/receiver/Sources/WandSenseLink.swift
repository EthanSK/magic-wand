import Foundation
import IOKit
import IOKit.serial
import CoreBluetooth
import Darwin

/// The one owner of the Sense board's connections: USB first, Bluetooth only
/// as fallback, and only for the explicitly selected board (its identity is
/// checked on both transports). Control Hand / Control Stones and other
/// Nordic UART devices are never opened: they neither advertise the Sense
/// name nor answer the wand-sense-1 identity.
final class WandSenseLink: NSObject, CBCentralManagerDelegate, CBPeripheralDelegate {
    enum Transport: String { case usb = "USB", bluetooth = "Bluetooth" }
    static let vendor = 0x2886, product = 0x8045 // Original Sense running firmware; bootloader 0x0045 is never opened.
    static let name = "Magic Wand Sense"
    static let uart = CBUUID(string: "6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
    static let uartTX = CBUUID(string: "6E400003-B5A3-F393-E0A9-E50E24DCCA9E")
    static let uartRX = CBUUID(string: "6E400002-B5A3-F393-E0A9-E50E24DCCA9E")
    static let staleSeconds = 0.75, heartbeatSeconds = 0.5, identifySeconds = 3.0

    var onReady: ((WandSenseInfo, Transport) -> Void)?
    var onLine: ((WandSenseLine, Double) -> Void)?
    var onLost: ((Transport, String) -> Void)?
    var onPin: ((String) -> Void)?
    var onLog: ((String) -> Void)?
    /// The selected board. USB pairing (a physical, explicit choice) sets it
    /// when none is configured; Bluetooth never connects without it.
    var pinnedID: String?
    private(set) var active: Transport?
    private(set) var info: WandSenseInfo?
    private var started = false, tick: Timer?
    private var lastLineAt = 0.0, heartbeatAt = 0.0
    // USB
    private var fd: Int32 = -1, usbSource: DispatchSourceRead?, usbFramer = WandSenseFramer()
    private var usbOpenedAt = 0.0, usbIdentifyAt = 0.0, usbRetryAfter = 0.0, usbScanAt = 0.0
    // Bluetooth
    private var central: CBCentralManager?, peripheral: CBPeripheral?, rx: CBCharacteristic?
    private var bleFramer = WandSenseFramer(), bleStartedAt = 0.0, bleIdentifyAt = 0.0, scanning = false
    private var ignoredPeripherals: Set<UUID> = []

    private var now: Double { ProcessInfo.processInfo.systemUptime }
    var usbPresent: Bool { fd >= 0 }

    func start() {
        guard !started else { return }
        started = true
        if central == nil { central = CBCentralManager(delegate: self, queue: nil) }
        tick = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in self?.poll() }
        poll()
    }

    /// End the host session cleanly: the firmware returns to its own light
    /// and power policy at once instead of after its timeout.
    func end(restarting: Bool = false) {
        send(WandSenseCommand.ending(restarting: restarting))
        started = false; tick?.invalidate(); tick = nil
        // Give the final BLE command a bounded chance to leave before teardown.
        // This only runs while quitting; it never delays pointer movement.
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) { [weak self] in
            guard let self else { return }
            self.closeUSB(); self.closeBluetooth()
            self.active = nil; self.info = nil
        }
    }

    /// The receiver gave up on this session (for example its ready deadline):
    /// close the transport so the next identity starts a fresh session.
    func drop(_ reason: String) { if let active { fail(active, reason: reason) } }

    func send(_ command: String) {
        guard let active else { return }
        let data = Data((command + "\n").utf8)
        switch active {
        case .usb: writeUSB(data)
        case .bluetooth:
            guard let peripheral, let rx, peripheral.state == .connected else { return }
            peripheral.writeValue(data, for: rx, type: rx.properties.contains(.writeWithoutResponse) ? .withoutResponse : .withResponse)
        }
    }

    // MARK: Supervision

    private func poll() {
        guard started else { return }
        let t = now
        if let active, t - lastLineAt > Self.staleSeconds { fail(active, reason: "telemetry stopped") }
        if active != nil, t - heartbeatAt >= Self.heartbeatSeconds { heartbeatAt = t; send(WandSenseCommand.heartbeat) }
        if active != .usb {
            if fd < 0, t >= usbRetryAfter, t - usbScanAt >= 1 { usbScanAt = t; openUSBIfPresent() }
            if fd >= 0, t - usbOpenedAt > Self.identifySeconds {
                onLog?("SENSE_USB_NO_IDENTITY"); closeUSB(); usbRetryAfter = t + 5
            } else if fd >= 0, t - usbIdentifyAt >= 0.5 { usbIdentifyAt = t; writeUSB(Data("\n?\n".utf8)) }
        }
        if active != .bluetooth, let peripheral, peripheral.state == .connected, rx != nil {
            if t - bleStartedAt > Self.identifySeconds + 2 { onLog?("SENSE_BLUETOOTH_NO_IDENTITY"); closeBluetooth() }
            else if t - bleIdentifyAt >= 0.5 { bleIdentifyAt = t; writeBluetooth("?") }
        }
        if active != .bluetooth, peripheral != nil, t - bleStartedAt > 10 {
            onLog?("SENSE_BLUETOOTH_CONNECT_TIMEOUT"); closeBluetooth()
        }
        updateScan()
    }

    private func fail(_ transport: Transport, reason: String) {
        switch transport { case .usb: closeUSB(); usbRetryAfter = now + 0.5; case .bluetooth: closeBluetooth() }
        guard active == transport else { return }
        active = nil; info = nil
        onLost?(transport, reason)
    }

    private func handle(_ raw: String, from transport: Transport) {
        guard let line = WandSenseLine.parse(raw) else { return }
        let arrival = now
        if case .info(let identity) = line {
            guard active != transport else {
                if identity.id != info?.id { fail(transport, reason: "different board") }
                return
            }
            guard pinnedID != nil || transport == .usb else { closeBluetooth(); return }
            if pinnedID == nil { pinnedID = identity.id; onPin?(identity.id) }
            guard identity.id == pinnedID else {
                onLog?("SENSE_OTHER_BOARD_IGNORED " + transport.rawValue)
                if transport == .usb { closeUSB(); usbRetryAfter = now + 10 }
                else { if let p = peripheral { ignoredPeripherals.insert(p.identifier) }; closeBluetooth() }
                return
            }
            // USB regains priority over a live Bluetooth session.
            if active == .bluetooth { fail(.bluetooth, reason: "USB preferred") }
            active = transport; info = identity; lastLineAt = arrival; heartbeatAt = 0
            onReady?(identity, transport)
            return
        }
        guard active == transport else { return }
        lastLineAt = arrival
        onLine?(line, arrival)
    }

    // MARK: USB

    /// Running original Sense firmware ports by USB vendor/product, never by name alone.
    static func sensePorts() -> [String] {
        guard let matching = IOServiceMatching(kIOSerialBSDServiceValue) else { return [] }
        var iterator: io_iterator_t = 0
        guard IOServiceGetMatchingServices(kIOMainPortDefault, matching, &iterator) == KERN_SUCCESS else { return [] }
        defer { IOObjectRelease(iterator) }
        var ports: [String] = []
        while true {
            let service = IOIteratorNext(iterator)
            guard service != 0 else { break }
            defer { IOObjectRelease(service) }
            guard let path = IORegistryEntryCreateCFProperty(service, kIOCalloutDeviceKey as CFString, kCFAllocatorDefault, 0)?
                .takeRetainedValue() as? String else { continue }
            let options = IOOptionBits(kIORegistryIterateRecursively | kIORegistryIterateParents)
            let vendor = IORegistryEntrySearchCFProperty(service, kIOServicePlane, "idVendor" as CFString, kCFAllocatorDefault, options) as? Int
            let product = IORegistryEntrySearchCFProperty(service, kIOServicePlane, "idProduct" as CFString, kCFAllocatorDefault, options) as? Int
            if vendor == Self.vendor && product == Self.product { ports.append(path) }
        }
        return ports
    }

    private func openUSBIfPresent() {
        let ports = Self.sensePorts()
        guard ports.count == 1, let path = ports.first else {
            if ports.count > 1 { onLog?("SENSE_USB_AMBIGUOUS \(ports.count)") }
            return
        }
        let handle = open(path, O_RDWR | O_NOCTTY | O_NONBLOCK)
        guard handle >= 0 else { usbRetryAfter = now + 2; return }
        // One owner: exclusive tty plus the same advisory lock other readers use.
        let TIOCEXCL: UInt = 0x2000_740D, TIOCSDTR: UInt = 0x2000_7479
        guard flock(handle, LOCK_EX | LOCK_NB) == 0, ioctl(handle, TIOCEXCL) == 0 else {
            close(handle); onLog?("SENSE_USB_BUSY"); usbRetryAfter = now + 2; return
        }
        var settings = termios()
        if tcgetattr(handle, &settings) == 0 {
            cfmakeraw(&settings)
            settings.c_cflag |= tcflag_t(CLOCAL | CREAD)
            cfsetspeed(&settings, speed_t(B115200)) // Never 1200: that baud requests the bootloader.
            tcsetattr(handle, TCSANOW, &settings)
        }
        _ = ioctl(handle, TIOCSDTR)
        fd = handle; usbFramer.reset(); usbOpenedAt = now; usbIdentifyAt = 0
        let source = DispatchSource.makeReadSource(fileDescriptor: handle, queue: .main)
        source.setEventHandler { [weak self] in self?.readUSB() }
        source.resume(); usbSource = source
        onLog?("SENSE_USB_OPENED")
    }

    private func readUSB() {
        guard fd >= 0 else { return }
        var buffer = [UInt8](repeating: 0, count: 4096)
        let n = read(fd, &buffer, buffer.count)
        if n > 0 {
            // A rejected identity can close/reset the framer. Finish its mutation
            // before dispatching lines, avoiding overlapping Swift access.
            var lines: [String] = []
            buffer.withUnsafeBytes { bytes in
                usbFramer.feed(UnsafeRawBufferPointer(rebasing: bytes[0..<n])) { lines.append($0) }
            }
            for line in lines { guard fd >= 0 else { break }; handle(line, from: .usb) }
        } else if n == 0 || (errno != EAGAIN && errno != EINTR) {
            fail(.usb, reason: "USB removed")
        }
    }

    private func writeUSB(_ data: Data) {
        guard fd >= 0 else { return }
        let written = data.withUnsafeBytes { write(fd, $0.baseAddress, data.count) }
        if written != data.count {
            // Never silently lose a sensor/sleep command or replay a partial
            // command later. Drop this session; reconnect restores current state.
            let expectedFD = fd
            DispatchQueue.main.async { [weak self] in
                guard let self, self.fd == expectedFD else { return }
                self.fail(.usb, reason: "USB command write failed")
            }
        }
    }

    private func closeUSB() {
        usbSource?.cancel(); usbSource = nil
        if fd >= 0 { flock(fd, LOCK_UN); close(fd) }
        fd = -1; usbFramer.reset()
    }

    // MARK: Bluetooth fallback

    private func updateScan() {
        guard let central, central.state == .poweredOn else { return }
        let want = started && fd < 0 && active == nil && peripheral == nil && pinnedID != nil
        if want && !scanning { scanning = true; central.scanForPeripherals(withServices: [Self.uart]); onLog?("SENSE_SCANNING") }
        else if !want && scanning { scanning = false; central.stopScan() }
    }

    func centralManagerDidUpdateState(_ c: CBCentralManager) {
        scanning = false
        if c.state != .poweredOn { if active == .bluetooth { fail(.bluetooth, reason: "Bluetooth off") }; peripheral = nil; rx = nil }
        updateScan()
    }

    func centralManager(_ c: CBCentralManager, didDiscover p: CBPeripheral, advertisementData: [String: Any], rssi: NSNumber) {
        let name = (advertisementData[CBAdvertisementDataLocalNameKey] as? String) ?? p.name ?? ""
        guard name == Self.name, !ignoredPeripherals.contains(p.identifier), peripheral == nil, fd < 0 else { return }
        // Scan-response identity (test company 0xFFFF + 8-byte board ID) lets
        // another Sense be skipped before connecting; the identity reply decides.
        if let data = advertisementData[CBAdvertisementDataManufacturerDataKey] as? Data, data.count == 10,
           data[data.startIndex] == 0xFF, data[data.startIndex + 1] == 0xFF, let pinnedID,
           data.dropFirst(2).map({ String(format: "%02x", $0) }).joined() != pinnedID { ignoredPeripherals.insert(p.identifier); return }
        scanning = false; c.stopScan()
        peripheral = p; p.delegate = self; bleFramer.reset(); bleStartedAt = now; bleIdentifyAt = 0
        c.connect(p); onLog?("SENSE_BLUETOOTH_CONNECTING")
    }

    func centralManager(_ c: CBCentralManager, didConnect p: CBPeripheral) {
        guard p === peripheral else { c.cancelPeripheralConnection(p); return }
        p.discoverServices([Self.uart])
    }
    func centralManager(_ c: CBCentralManager, didFailToConnect p: CBPeripheral, error: Error?) {
        guard p === peripheral else { return }
        peripheral = nil; rx = nil
    }
    func centralManager(_ c: CBCentralManager, didDisconnectPeripheral p: CBPeripheral, error: Error?) {
        guard p === peripheral else { return }
        peripheral = nil; rx = nil; bleFramer.reset()
        if active == .bluetooth { active = nil; info = nil; onLost?(.bluetooth, "Bluetooth disconnected") }
    }
    func peripheral(_ p: CBPeripheral, didDiscoverServices error: Error?) {
        guard p === peripheral else { return }
        guard error == nil, let s = p.services?.first(where: { $0.uuid == Self.uart }) else { closeBluetooth(); return }
        p.discoverCharacteristics([Self.uartTX, Self.uartRX], for: s)
    }
    func peripheral(_ p: CBPeripheral, didDiscoverCharacteristicsFor s: CBService, error: Error?) {
        guard p === peripheral else { return }
        guard error == nil else { closeBluetooth(); return }
        for c in s.characteristics ?? [] {
            if c.uuid == Self.uartRX { rx = c }
            if c.uuid == Self.uartTX { p.setNotifyValue(true, for: c) }
        }
    }
    func peripheral(_ p: CBPeripheral, didUpdateNotificationStateFor c: CBCharacteristic, error: Error?) {
        guard p === peripheral else { return }
        guard error == nil, c.isNotifying else { closeBluetooth(); return }
        bleIdentifyAt = now; writeBluetooth("?")
    }
    func peripheral(_ p: CBPeripheral, didUpdateValueFor c: CBCharacteristic, error: Error?) {
        guard p === peripheral, error == nil, let value = c.value else { return }
        var lines: [String] = []
        bleFramer.feed(value) { lines.append($0) }
        for line in lines { guard p === peripheral else { break }; handle(line, from: .bluetooth) }
    }

    private func writeBluetooth(_ command: String) {
        guard let peripheral, let rx, peripheral.state == .connected else { return }
        peripheral.writeValue(Data(("\n" + command + "\n").utf8), for: rx,
                              type: rx.properties.contains(.writeWithoutResponse) ? .withoutResponse : .withResponse)
    }

    private func closeBluetooth() {
        if let peripheral { central?.cancelPeripheralConnection(peripheral) }
        peripheral = nil; rx = nil; bleFramer.reset()
    }
}
