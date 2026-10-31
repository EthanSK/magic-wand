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
ack(); response(1); ack(); ack(); response(2); ack(); ack()
// One 20-byte packet per receipt, even if CoreBluetooth can queue more.
// Each receipt earns exactly one next packet; host availability alone does not.
func packetCount() -> Int { peripheral.writes.filter { $0.1 == .withoutResponse && $0.0.count == 20 }.count }
precondition(packetCount() == 1)
transfer.peripheralIsReady(toSendWriteWithoutResponse: peripheral)
precondition(packetCount() == 1, "availability must not bypass a device receipt")
for count in stride(from: 20, through: 80, by: 20) {
    control.value = Data([17, UInt8(count), 0, 0, 0])
    transfer.peripheral(peripheral, didUpdateValueFor: control, error: nil)
    precondition(packetCount() == count / 20 + 1)
}
response(3); ack(); response(4)
precondition(peripheral.writes.last?.0 == WandSenseLegacyDFU.activate, "actual transfer runner sends Activate only after validation")
transfer.peripheral(peripheral, didWriteValueFor: control, error: NSError(domain: "test", code: 1))
precondition(completed && transferError?.contains("activation") == true, "activation write failure cannot report transfer success")
link.centralManager(central, didDisconnectPeripheral: peripheral, error: nil)
precondition(transferError?.contains("activation") == true && link.updater == nil)
print("PASS: real updater/link orchestration against fake Bluetooth bounds handoff, excludes USB, routes exact peripheral and handles activation failure")

// Late callbacks belong to a finished transfer and must never activate a board.
let latePeripheral = CBPeripheral(), lateCentral = CBCentralManager(delegate:nil,queue:nil)
lateCentral.known = [latePeripheral]
let late = WandSenseDFUTransfer(central:lateCentral,peripheralID:latePeripheral.identifier,package:package())
precondition(late.transferBudgetSeconds >= 240, "small images retain the existing timeout")
late.start()
late.didConnect(latePeripheral)
let lateControl = CBCharacteristic(WandSenseLegacyDFU.control), latePacket = CBCharacteristic(WandSenseLegacyDFU.packet)
let lateService = CBService(WandSenseLegacyDFU.service,[lateControl,latePacket]); latePeripheral.services=[lateService]
late.peripheral(latePeripheral,didDiscoverServices:nil)
late.peripheral(latePeripheral,didDiscoverCharacteristicsFor:lateService,error:nil)
late.peripheral(latePeripheral,didUpdateNotificationStateFor:lateControl,error:nil)
func lateAck(){late.peripheral(latePeripheral,didWriteValueFor:lateControl,error:nil)}
func lateResponse(_ bytes:[UInt8]){lateControl.value=Data(bytes);late.peripheral(latePeripheral,didUpdateValueFor:lateControl,error:nil)}
lateAck();lateResponse([16,1,1]);lateAck();lateAck();lateResponse([16,2,1]);lateAck();lateAck()
for n in stride(from:20,through:80,by:20){lateResponse([17,UInt8(n),0,0,0])}
lateResponse([16,3,1]);lateAck()
late.finish("cancelled before validation response")
let beforeLateResponse=latePeripheral.writes.count
let beforeLateTimers=WandRunLoop.timers.count
lateResponse([16,4,1])
late.peripheral(latePeripheral,didUpdateNotificationStateFor:lateControl,error:nil)
precondition(latePeripheral.writes.count==beforeLateResponse,"cancelled transfer sent Activate from a late validation response")
precondition(WandRunLoop.timers.count==beforeLateTimers,"late notification callback restarted a finished update timer")
print("PASS: cancelled transfers ignore late validation callbacks")

// A link drop during data transfer must reconnect the exact same peripheral.
let recoverP = CBPeripheral(), recoverC = CBCentralManager(delegate:nil,queue:nil)
recoverC.known=[recoverP]
let recover = WandSenseDFUTransfer(central:recoverC,peripheralID:recoverP.identifier,package:package())
var recoverFinished=false
recover.onFinish={_ in recoverFinished=true}
recover.start()
recover.didConnect(recoverP)
let recoverControl=CBCharacteristic(WandSenseLegacyDFU.control), recoverPacket=CBCharacteristic(WandSenseLegacyDFU.packet)
let recoverService=CBService(WandSenseLegacyDFU.service,[recoverControl,recoverPacket]);recoverP.services=[recoverService]
recover.peripheral(recoverP,didDiscoverServices:nil)
recover.peripheral(recoverP,didDiscoverCharacteristicsFor:recoverService,error:nil)
recover.peripheral(recoverP,didUpdateNotificationStateFor:recoverControl,error:nil)
func recoverAck(){recover.peripheral(recoverP,didWriteValueFor:recoverControl,error:nil)}
func recoverResponse(_ bytes:[UInt8]){recoverControl.value=Data(bytes);recover.peripheral(recoverP,didUpdateValueFor:recoverControl,error:nil)}
recoverAck();recoverResponse([16,1,1]);recoverAck();recoverAck();recoverResponse([16,2,1]);recoverAck();recoverAck()
recoverResponse([17,20,0,0,0]) // one acknowledged packet, one possibly in flight
let connectionsBeforeDrop=recoverC.connects
recover.didDisconnect(recoverP)
precondition(!recoverFinished && recoverC.connects==connectionsBeforeDrop+1,"transient link drop abandoned a resumable update")
// A queued receipt/write callback from the old connection cannot get ahead of
// the new byte-count query, even when CoreBluetooth reuses its peripheral.
recoverResponse([17,40,0,0,0]);recoverAck()
let startWritesBeforeResume=recoverP.writes.filter{$0.0==Data([1,4])}.count
recover.didConnect(recoverP)
recover.peripheral(recoverP,didDiscoverServices:nil)
recover.peripheral(recoverP,didDiscoverCharacteristicsFor:recoverService,error:nil)
recover.peripheral(recoverP,didUpdateNotificationStateFor:recoverControl,error:nil)
precondition(recoverP.writes.last?.0==Data([7]),"resumption queries received bytes instead of erasing")
recoverAck()
recoverResponse([16,7,1,40,0,0,0]) // SDK11's opcode7 response includes status before the byte count.
recoverAck();recoverAck()
precondition(recoverP.writes.filter{$0.0==Data([1,4])}.count==startWritesBeforeResume,"resumption must not send Start again")
for n in [60,80]{recoverResponse([17,UInt8(n),0,0,0])}
recoverResponse([16,3,1]);recoverAck();recoverResponse([16,4,1])
precondition(recoverP.writes.last?.0==WandSenseLegacyDFU.activate,"resumed image validates before activation")
recover.didDisconnect(recoverP)
precondition(recoverFinished,"activation disconnect completes the resumed transfer")
print("PASS: data-transfer reconnect queries its exact offset and finishes without erasing or replaying confirmed bytes")

func makeStreamingTransfer() -> (WandSenseDFUTransfer,CBCentralManager,CBPeripheral,CBService,CBCharacteristic) {
 let p=CBPeripheral(),c=CBCentralManager(delegate:nil,queue:nil);c.known=[p]
 let t=WandSenseDFUTransfer(central:c,peripheralID:p.identifier,package:package());t.start();t.didConnect(p)
 let control=CBCharacteristic(WandSenseLegacyDFU.control),packet=CBCharacteristic(WandSenseLegacyDFU.packet)
 let service=CBService(WandSenseLegacyDFU.service,[control,packet]);p.services=[service]
 t.peripheral(p,didDiscoverServices:nil);t.peripheral(p,didDiscoverCharacteristicsFor:service,error:nil);t.peripheral(p,didUpdateNotificationStateFor:control,error:nil)
 func ack(){t.peripheral(p,didWriteValueFor:control,error:nil)}
 func note(_ b:[UInt8]){control.value=Data(b);t.peripheral(p,didUpdateValueFor:control,error:nil)}
 ack();note([16,1,1]);ack();ack();note([16,2,1]);ack();ack();note([17,20,0,0,0])
 return (t,c,p,service,control)
}
let (boundedTransfer,boundedCentral,boundedPeripheral,boundedService,boundedControl)=makeStreamingTransfer()
var boundedFailure:String?
boundedTransfer.onFinish={boundedFailure=$0}
let originalBudget=boundedTransfer.transferBudgetSeconds
for attempt in 1...2 {
 let before=boundedCentral.connects
 boundedTransfer.didDisconnect(CBPeripheral())
 precondition(boundedCentral.connects==before,"another peripheral must not trigger a retry")
 boundedTransfer.didDisconnect(boundedPeripheral)
 precondition(boundedCentral.connects==before+1)
 boundedTransfer.didConnect(boundedPeripheral)
 boundedTransfer.peripheral(boundedPeripheral,didDiscoverServices:nil)
 boundedTransfer.peripheral(boundedPeripheral,didDiscoverCharacteristicsFor:boundedService,error:nil)
 boundedTransfer.peripheral(boundedPeripheral,didUpdateNotificationStateFor:boundedControl,error:nil)
 precondition(WandRunLoop.timers.last!.0<=originalBudget,"reconnect must not renew the overall deadline")
 boundedTransfer.peripheral(boundedPeripheral,didWriteValueFor:boundedControl,error:nil)
 boundedControl.value=Data([16,7,1,20,0,0,0]);boundedTransfer.peripheral(boundedPeripheral,didUpdateValueFor:boundedControl,error:nil)
 boundedTransfer.peripheral(boundedPeripheral,didWriteValueFor:boundedControl,error:nil)
 boundedTransfer.peripheral(boundedPeripheral,didWriteValueFor:boundedControl,error:nil)
 precondition(boundedFailure==nil,"allowed reconnect failed at attempt \(attempt)")
}
let beforeLimit=boundedCentral.connects
boundedTransfer.didDisconnect(boundedPeripheral)
precondition(boundedFailure != nil && boundedCentral.connects==beforeLimit,"reconnects must be bounded")
print("PASS: retries preserve the deadline, ignore other devices and stop at the finite limit")

// A duplicate subscription callback cannot send Start or reset the timer/state.
do {
 let (t,_,p,_,control)=makeStreamingTransfer();var failure:String?
 t.onFinish={failure=$0};let count=p.writes.count
 t.peripheral(p,didUpdateNotificationStateFor:control,error:nil)
 precondition(p.writes.count==count && failure==nil)
 t.finish("test complete")
}
// Once a new link exists, another disconnect is genuine even before its query.
do {
 let (t,c,p,_,_)=makeStreamingTransfer();var done=false;t.onFinish={_ in done=true}
 t.didDisconnect(p);let first=c.connects;t.didConnect(p);t.didDisconnect(p)
 precondition(!done && c.connects==first+1,"a resumed connection's drop must retry")
 t.didDisconnect(p);precondition(c.connects==first+1,"old duplicate must not spend a retry")
 t.finish("test complete")
}
do {
 let (t,c,p,_,_)=makeStreamingTransfer();var done=false;t.onFinish={_ in done=true}
 t.didDisconnect(p);let first=c.connects;t.didFailToConnect(p)
 precondition(!done && c.connects==first+1,"a failed reconnect gets the remaining bounded attempt")
 t.didFailToConnect(p);precondition(done,"failed reconnects do not loop forever")
}
// Radio changes need no synthetic per-peripheral disconnect to be handled.
do {
 let (t,c,p,service,control)=makeStreamingTransfer();var done=false;t.onFinish={_ in done=true}
 let initial=c.connects;t.radioChanged(available:false);t.didDisconnect(p);t.didFailToConnect(p);t.didConnect(p)
 let writes=p.writes.count
 t.peripheral(p,didDiscoverServices:NSError(domain:"old connection",code:1))
 t.peripheral(p,didDiscoverCharacteristicsFor:service,error:nil)
 t.peripheral(p,didUpdateNotificationStateFor:control,error:nil)
 precondition(!done && p.writes.count==writes,"old discovery callbacks cannot bypass the radio wait")
 precondition(!done && c.connects==initial)
 t.radioChanged(available:true);precondition(!done && c.connects==initial+1)
 t.finish("test complete")
}
// Lost receipts and a one-packet buffer rejection query, never blindly replay.
for rejected in [false,true] {
 let (t,_,p,_,control)=makeStreamingTransfer();var done=false;t.onFinish={_ in done=true}
 if rejected {control.value=Data([16,3,6]);t.peripheral(p,didUpdateValueFor:control,error:nil)}
 else {WandRunLoop.timers.last!.1.fire()}
 precondition(p.writes.last?.0==Data([7]),"stalled/rejected packet needs a byte-count query")
 t.peripheral(p,didWriteValueFor:control,error:nil)
 // A late normal receipt does not answer the explicit query.
 control.value=Data([17,40,0,0,0]);t.peripheral(p,didUpdateValueFor:control,error:nil)
 precondition(!done && p.writes.last?.0==Data([7]))
 control.value=Data([16,7,1,40,0,0,0]);t.peripheral(p,didUpdateValueFor:control,error:nil)
 t.peripheral(p,didWriteValueFor:control,error:nil);t.peripheral(p,didWriteValueFor:control,error:nil)
 precondition(!done && p.writes.filter{$0.0==Data([1,4])}.count==1)
 t.finish("test complete")
}
// An activation disconnect can mean the new app is already booting. The caller
// still verifies its exact version; an unrelated write error remains a failure.
do {
 let (t,_,p,_,control)=makeStreamingTransfer();var result:String??
 t.onFinish={result=$0}
 for n in [40,60,80] {control.value=Data([17,UInt8(n),0,0,0]);t.peripheral(p,didUpdateValueFor:control,error:nil)}
 control.value=Data([16,3,1]);t.peripheral(p,didUpdateValueFor:control,error:nil)
 t.peripheral(p,didWriteValueFor:control,error:nil)
 control.value=Data([16,4,1]);t.peripheral(p,didUpdateValueFor:control,error:nil)
 precondition(p.writes.last?.0==WandSenseLegacyDFU.activate)
 t.peripheral(p,didWriteValueFor:control,error:NSError(domain:"CBErrorDomain",code:7))
 precondition(result != nil && result! == nil,"activation reboot is pending verification, not certain failure")
}
print("PASS: repeated setup, resumed-link loss, connection failure, radio loss, receipt loss and activation races are bounded")
