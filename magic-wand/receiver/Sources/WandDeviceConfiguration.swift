import Foundation

/// Public-source addition. The installed receiver pinned one Puck's CoreBluetooth identifier and
/// advertised name; this repository reads them from
/// `~/Library/Application Support/WandReceiver/device.json` instead:
///
///     {"name": "Puck.js xxxx", "identifier": "optional-CoreBluetooth-peripheral-UUID"}
///
/// `name` is the Puck's advertised Bluetooth name. `identifier` is optional: macOS assigns it
/// after the first connection, and it only lets reconnects skip scanning.
///
/// The XIAO nRF52840 Sense wand is a separate, explicit profile:
///
///     {"profile": "sense", "sense": {"id": "optional 16-hex board ID", "axes": ["-y", "+x", "+z"], "pointerGain": 1.1725}}
///
/// Without an ID, the first single Sense seen over USB is selected and remembered in
/// `sense-device.json`; Bluetooth only reconnects to that selected board. `axes` names the
/// Sense axis for the Puck's x (right), y (toward tip) and z (up). Absent keys keep the Puck.
struct WandDeviceConfiguration {
    enum Profile: String { case puck, sense }
    let name: String
    let identifier: UUID?
    var profile: Profile = .puck
    var senseID: String?
    var senseAxes: WandSenseAxes = .standard
    var sensePointerGain = WandSenseTuning.defaultPointerGain

    var isConfigured: Bool { profile == .sense || !name.isEmpty || identifier != nil }

    func matches(name advertised: String) -> Bool {
        !name.isEmpty && advertised.lowercased() == name.lowercased()
    }

    static func load(from url: URL) -> WandDeviceConfiguration {
        guard let data = try? Data(contentsOf: url),
              let value = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            log("DEVICE_NOT_CONFIGURED", url.lastPathComponent)
            return .init(name: "", identifier: nil)
        }
        let name = (value["name"] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let identifier = (value["identifier"] as? String).flatMap { UUID(uuidString: $0) }
        var settings = WandDeviceConfiguration(name: name, identifier: identifier)
        if (value["profile"] as? String) == Profile.sense.rawValue {
            settings.profile = .sense
            let sense = value["sense"] as? [String: Any] ?? [:]
            if let id = (sense["id"] as? String)?.lowercased(), id.count == 16, id.allSatisfy({ $0.isHexDigit }) { settings.senseID = id }
            if let gain = (sense["pointerGain"] as? NSNumber)?.doubleValue {
                if WandSenseTuning.pointerGainRange.contains(gain) { settings.sensePointerGain = gain } else { log("SENSE_POINTER_GAIN_INVALID_USING_DEFAULT") }
            }
            if let axes = sense["axes"] as? [String] {
                if let parsed = WandSenseAxes(text: axes) { settings.senseAxes = parsed } else { log("SENSE_AXES_INVALID_USING_DEFAULT") }
            }
        }
        return settings
    }
}
