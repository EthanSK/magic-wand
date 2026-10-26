import Foundation

/// Packet sizing shared by the receiver and saved-program console.
enum WandUART {
    // Puck.js Espruino 2v27 configures MTU 53; the UART value uses MTU minus 3.
    // The Mac's acknowledged limit can include long writes, which this UART
    // does not implement. Its unacknowledged limit bounds a single ATT packet.
    static func payloadLimit(acknowledged: Int, unacknowledged: Int) -> Int {
        return min(50, acknowledged > 0 ? acknowledged : 20,
                   unacknowledged > 0 ? unacknowledged : 20)
    }

    static func packets(_ command: String, acknowledged: Int, unacknowledged: Int) -> [Data] {
        let data = Data(("\u{10}" + command + "\n").utf8)
        let size = payloadLimit(acknowledged: acknowledged, unacknowledged: unacknowledged)
        return stride(from: 0, to: data.count, by: size).map { offset in
            data.subdata(in: offset..<min(offset + size, data.count))
        }
    }
}
