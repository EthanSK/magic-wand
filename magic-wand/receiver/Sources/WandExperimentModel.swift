// Reusable experiment configuration and constant-memory rate counters.
// Receiver input only increments counters; a separate UI tick reads them.
// Statistics never schedule, alter, combine or replay pointer/sensor input.
import Foundation
import CoreFoundation

struct WandExperimentConfiguration: Equatable {
    static let rates: Set<Int> = [104, 208, 416, 833, 1660, 3330, 6660]
    let visible: Bool
    let label: String
    let sensorHz: Int?
    var manualClick = false

    static func parse(_ data: Data) -> Self? {
        guard data.count <= 2048,
              let value = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
              Set(value.keys).isSubset(of: ["version", "visible", "label", "sensorHz", "manualClick"]),
              let version = value["version"] as? NSNumber,
              CFGetTypeID(version) != CFBooleanGetTypeID(), version.doubleValue == 1,
              let visibleNumber = value["visible"] as? NSNumber, CFGetTypeID(visibleNumber) == CFBooleanGetTypeID(),
              let visible = value["visible"] as? Bool,
              let label = value["label"] as? String, !label.isEmpty, label.count <= 80,
              !label.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }) else { return nil }
        var hz: Int?
        if let raw = value["sensorHz"] {
            guard let number = raw as? NSNumber, CFGetTypeID(number) != CFBooleanGetTypeID(),
                  number.doubleValue.isFinite, number.doubleValue == number.doubleValue.rounded(),
                  number.doubleValue >= 104, number.doubleValue <= 6660,
                  rates.contains(number.intValue) else { return nil }
            hz = number.intValue
        }
        var manualClick = false
        if let raw = value["manualClick"] {
            guard let number = raw as? NSNumber, CFGetTypeID(number) == CFBooleanGetTypeID(),
                  let enabled = raw as? Bool else { return nil }
            manualClick = enabled
        }
        return .init(visible: visible, label: label, sensorHz: hz, manualClick: manualClick)
    }
}

struct WandExperimentRates: Equatable {
    let readings: Double
    let frames: Double
    let pointerEvents: Double
}

struct WandExperimentRateCounter {
    private var since: Double?
    private var readings = 0, frames = 0, pointerEvents = 0

    mutating func reset(now: Double) {
        since = now; readings = 0; frames = 0; pointerEvents = 0
    }
    mutating func frame(readingCount: Int) {
        guard (1...255).contains(readingCount) else { return }
        readings += readingCount; frames += 1
    }
    mutating func postedPointerEvent() { pointerEvents += 1 }
    mutating func measure(now: Double) -> WandExperimentRates? {
        guard now.isFinite else { return nil }
        guard let start = since, now >= start else { reset(now: now); return nil }
        let seconds = now - start
        guard seconds >= 1 else { return nil }
        let value = WandExperimentRates(readings: Double(readings) / seconds,
                                        frames: Double(frames) / seconds,
                                        pointerEvents: Double(pointerEvents) / seconds)
        reset(now: now)
        return value
    }
}

struct WandExperimentRateReply: Equatable {
    let hz: Int
    let mode: Int
    let accepted: Bool

    static func parse(_ event: String) -> Self? {
        let parts = event.split(separator: " ")
        guard parts.count == 4, parts[0] == "rate",
              parts[1].hasPrefix("hz="), let hz = Int(parts[1].dropFirst(3)),
              WandExperimentConfiguration.rates.contains(hz),
              parts[2].hasPrefix("mode="), let mode = Int(parts[2].dropFirst(5)), (0...2).contains(mode),
              parts[3] == "ok=1" || parts[3] == "ok=0" else { return nil }
        return .init(hz: hz, mode: mode, accepted: parts[3] == "ok=1")
    }
}
