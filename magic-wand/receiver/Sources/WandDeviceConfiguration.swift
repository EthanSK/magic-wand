import Foundation

/// Public-source addition. The installed receiver pinned one Puck's CoreBluetooth identifier and
/// advertised name; this repository reads them from
/// `~/Library/Application Support/WandReceiver/device.json` instead:
///
///     {"name": "Puck.js xxxx", "identifier": "optional-CoreBluetooth-peripheral-UUID"}
///
/// `name` is the Puck's advertised Bluetooth name. `identifier` is optional: macOS assigns it
/// after the first connection, and it only lets reconnects skip scanning.
struct WandDeviceConfiguration {
    let name: String
    let identifier: UUID?

    var isConfigured: Bool { !name.isEmpty || identifier != nil }

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
        return .init(name: name, identifier: identifier)
    }
}
