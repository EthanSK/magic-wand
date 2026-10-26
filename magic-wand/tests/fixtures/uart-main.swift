import Foundation

let cases: [(Int, Int, Int)] = [
    (512, 50, 50), (512, 20, 20), (512, 244, 50), (30, 50, 30),
    (0, 0, 20), (0, 10, 10), (10, 0, 10), (1, 50, 1)
]
for (acknowledged, unacknowledged, expected) in cases {
    precondition(WandUART.payloadLimit(acknowledged: acknowledged, unacknowledged: unacknowledged) == expected)
    // Byte boundaries, a long saved-file command, and a split multibyte UTF-8
    // sequence must all reconstruct exactly, including the console controls.
    for command in ["", String(repeating: "x", count: expected - 1),
                    String(repeating: "x", count: expected),
                    String(repeating: "abc🪄", count: 350)] {
        let packets = WandUART.packets(command, acknowledged: acknowledged, unacknowledged: unacknowledged)
        precondition(packets.allSatisfy { !$0.isEmpty && $0.count <= expected })
        precondition(packets.dropLast().allSatisfy { $0.count == expected })
        precondition(packets.reduce(into: Data()) { $0.append($1) } == Data(("\u{10}" + command + "\n").utf8))
    }
}
print("PASS negotiated UART limits, long-write cap and exact byte reconstruction")
