import Foundation

// Test doubles only. This executable compiles the actual link/updater source
// against these types; it never creates a CoreBluetooth manager or opens USB.
protocol CBPeripheralDelegate: AnyObject {}
protocol CBCentralManagerDelegate: AnyObject {}
struct CBUUID: Hashable { let text: String; init(string: String) { text = string.uppercased() } }
enum CBManagerState { case poweredOn, poweredOff }
enum CBPeripheralState { case connected, disconnected }
enum CBCharacteristicWriteType { case withResponse, withoutResponse }
struct CBCharacteristicProperties: OptionSet {
    let rawValue: Int
    static let writeWithoutResponse = Self(rawValue: 1)
}
let CBAdvertisementDataLocalNameKey = "name", CBAdvertisementDataManufacturerDataKey = "manufacturer"
final class CBCharacteristic {
    let uuid: CBUUID
    var value: Data?, isNotifying = true
    var properties: CBCharacteristicProperties = [.writeWithoutResponse]
    init(_ uuid: CBUUID) { self.uuid = uuid }
}
final class CBService {
    let uuid: CBUUID
    var characteristics: [CBCharacteristic]?
    init(_ uuid: CBUUID, _ chars: [CBCharacteristic]) { self.uuid = uuid; characteristics = chars }
}
final class CBPeripheral: NSObject {
    let identifier = UUID()
    let name: String? = "Magic Wand Sense"
    weak var delegate: CBPeripheralDelegate?
    var state = CBPeripheralState.connected, canSendWriteWithoutResponse = true
    var services: [CBService]?
    var writes: [(Data, CBCharacteristicWriteType)] = [], serviceRequests: [[CBUUID]?] = []
    func discoverServices(_ values: [CBUUID]?) { serviceRequests.append(values) }
    func discoverCharacteristics(_ values: [CBUUID]?, for service: CBService) {}
    func setNotifyValue(_ value: Bool, for characteristic: CBCharacteristic) {}
    func writeValue(_ data: Data, for characteristic: CBCharacteristic, type: CBCharacteristicWriteType) { writes.append((data, type)) }
}
final class CBCentralManager {
    static var latest: CBCentralManager?
    weak var delegate: CBCentralManagerDelegate?
    var state = CBManagerState.poweredOn
    var known: [CBPeripheral] = [], connects = 0, cancels = 0
    init(delegate: CBCentralManagerDelegate?, queue: DispatchQueue?) { self.delegate = delegate; Self.latest = self }
    func retrievePeripherals(withIdentifiers values: [UUID]) -> [CBPeripheral] { known.filter { values.contains($0.identifier) } }
    func scanForPeripherals(withServices values: [CBUUID]?) {}
    func stopScan() {}
    func connect(_ peripheral: CBPeripheral) { connects += 1 }
    func cancelPeripheralConnection(_ peripheral: CBPeripheral) { cancels += 1 }
}
enum WandRunLoop {
    static var timers: [(Double, Timer)] = []
    static func commonTimer(interval: TimeInterval, repeats: Bool = true, _ body: @escaping (Timer) -> Void) -> Timer {
        let timer = Timer(timeInterval: interval, repeats: repeats, block: body)
        timers.append((interval, timer)); return timer
    }
}
enum TestHardware { static var usbPolls = 0 }

func package() -> WandSenseDFUPackage {
    var image = Data("WANDIMG1;xiao-nrf52840-sense;7\u{0}".utf8)
    image.append(Data(repeating: 1, count: 100 - image.count))
    let crc = WandSenseDFUPackage.crc16(image)
    let dat = Data([0x52, 0, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 1, 0, 0x23, 1, UInt8(crc & 255), UInt8(crc >> 8)])
    return try! .make(image: image, initPacket: dat, manifestFields: ["device_type": 82, "firmware_crc16": Int(crc), "softdevice_req": [291]])
}
func connectedLink() -> (WandSenseLink, CBCentralManager, CBPeripheral) {
    let link = WandSenseLink(); link.pinnedID = "1a2b3c4d5e6f7081"; link.start()
    let central = CBCentralManager.latest!, peripheral = CBPeripheral(); central.known = [peripheral]
    link.centralManager(central, didDiscover: peripheral, advertisementData: [CBAdvertisementDataLocalNameKey: WandSenseLink.name], rssi: 0)
    link.centralManager(central, didConnect: peripheral)
    let rx = CBCharacteristic(WandSenseLink.uartRX), tx = CBCharacteristic(WandSenseLink.uartTX)
    let service = CBService(WandSenseLink.uart, [rx, tx]); peripheral.services = [service]
    link.peripheral(peripheral, didDiscoverServices: nil)
    link.peripheral(peripheral, didDiscoverCharacteristicsFor: service, error: nil)
    let identity: [String: Any] = ["protocol": "wand-sense-1", "firmware": "wand-sense-6", "id": "1a2b3c4d5e6f7081", "imu": true, "gyroDpsPerLsb": 0.0175, "accelGPerLsb": 0.000122]
    tx.value = Data("\nI".utf8) + (try! JSONSerialization.data(withJSONObject: identity)) + Data("\n".utf8)
    link.peripheral(peripheral, didUpdateValueFor: tx, error: nil)
    precondition(link.active == .bluetooth)
    return (link, central, peripheral)
}
let (waitingLink, _, _) = connectedLink()
let neverHandsOver = waitingLink.prepareUpdate(package())!
var handoffError: String?
neverHandsOver.onFinish = { handoffError = $0; waitingLink.finishUpdate() }
let polls = TestHardware.usbPolls
WandRunLoop.timers.first { $0.0 == 0.1 }!.1.fire()
precondition(TestHardware.usbPolls == polls, "normal USB supervision must wait while updater owns the link")
WandRunLoop.timers.last { $0.0 == 10 }!.1.fire()
precondition(handoffError?.contains("hand over") == true && waitingLink.updater == nil, "GO without disconnect has a bounded failure")

let (link, central, peripheral) = connectedLink()
let transfer = link.prepareUpdate(package())!
var completed = false, transferError: String?
transfer.onFinish = { completed = true; transferError = $0; link.finishUpdate() }
link.centralManager(central, didDisconnectPeripheral: peripheral, error: nil)
precondition(peripheral.delegate === transfer, "the exact peripheral changes owner after disconnect")
let connectionsDuringUpdate = central.connects
link.centralManager(central, didDiscover: CBPeripheral(), advertisementData: [CBAdvertisementDataLocalNameKey: WandSenseLink.name], rssi: 0)
precondition(central.connects == connectionsDuringUpdate, "queued ordinary advertisements cannot steal updater ownership")
link.centralManager(central, didConnect: peripheral)
precondition(peripheral.serviceRequests.last! == [WandSenseLegacyDFU.service])
let control = CBCharacteristic(WandSenseLegacyDFU.control), packet = CBCharacteristic(WandSenseLegacyDFU.packet)
let dfuService = CBService(WandSenseLegacyDFU.service, [control, packet]); peripheral.services = [dfuService]
transfer.peripheral(peripheral, didDiscoverServices: nil)
transfer.peripheral(peripheral, didDiscoverCharacteristicsFor: dfuService, error: nil)
transfer.peripheral(peripheral, didUpdateNotificationStateFor: control, error: nil)
func ack() { transfer.peripheral(peripheral, didWriteValueFor: control, error: nil) }
func response(_ procedure: UInt8) { control.value = Data([16, procedure, 1]); transfer.peripheral(peripheral, didUpdateValueFor: control, error: nil) }
ack(); response(1); ack(); ack(); response(2); ack(); ack(); response(3); ack(); response(4)
precondition(peripheral.writes.last?.0 == WandSenseLegacyDFU.activate, "actual transfer runner sends Activate only after validation")
transfer.peripheral(peripheral, didWriteValueFor: control, error: NSError(domain: "test", code: 1))
precondition(completed && transferError?.contains("activation") == true, "activation write failure cannot report transfer success")
link.centralManager(central, didDisconnectPeripheral: peripheral, error: nil)
precondition(transferError?.contains("activation") == true && link.updater == nil)
print("PASS: real updater/link orchestration against fake Bluetooth bounds handoff, excludes USB, routes exact peripheral and handles activation failure")
