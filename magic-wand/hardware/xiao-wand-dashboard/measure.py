#!/usr/bin/env python3
"""Measure the Sense wand's real data stream from the running dashboard observer.

Opt-in and passive: reads only the read-only local dashboard API (--receiver mode),
which itself only observes Wand Receiver, the board's one hardware owner. Opens no
USB or Bluetooth connection, sends nothing to the board and moves no pointer.

    python3 -I measure.py --seconds 60 --save capture.json   # capture, then report
    python3 -I measure.py --input capture.json               # report a saved capture

Reports device sample cadence and estimated missing readings, host arrival grouping,
arrival lag spread, saturation, quiet-window noise, the gravity frame
while held, and a gyro scale check against gravity between still poses.
Arrival times include host scheduling; they are not radio-only or end-to-end latency.
"""
import argparse, json, math, statistics, time, urllib.request
from collections import Counter

def capture(url, seconds):
    cursor, rows, end = -1, [], time.monotonic() + seconds
    while time.monotonic() < end:
        polled = time.monotonic()
        try:
            with urllib.request.urlopen(f"{url}/api/wand?after={cursor}", timeout=2) as response: snapshot = json.load(response)
        except (OSError, ValueError):
            time.sleep(0.2); continue
        for packet in snapshot.get("packets", []):
            if packet["id"] > cursor:
                cursor = packet["id"]; packet["poll"] = polled; rows.append(packet)
        time.sleep(0.1)
    return rows

def q(values, fraction):
    return values[min(len(values) - 1, int(fraction * len(values)))] if values else None

def rounded(value, digits):
    return round(value, digits) if value is not None else None

def rotate(f, w, dt):
    # A world-fixed vector in body coordinates evolves as df/dt = -w x f.
    wx, wy, wz = w
    return [f[0] - dt * (wy * f[2] - wz * f[1]), f[1] - dt * (wz * f[0] - wx * f[2]), f[2] - dt * (wx * f[1] - wy * f[0])]

def angle(a, b):
    na, nb = math.sqrt(sum(v * v for v in a)), math.sqrt(sum(v * v for v in b))
    return math.degrees(math.acos(max(-1, min(1, sum(x * y for x, y in zip(a, b)) / (na * nb)))))

def report(rows, period_ms=1000 / 104):
    rows = [r for r in rows if "packet" in r]
    packets = [(r["packet"], r["poll"] - r.get("age_ms", 0) / 1000) for r in rows]
    def is_active(p):
        return bool(p.get("imu") and (p["imuFlags"] & 2 if "imuFlags" in p else any(p["imu"][k] for k in ("gx", "gy", "gz"))))
    def continuous(i):
        a, b = rows[i-1], rows[i]
        return (a.get("session") == b.get("session") and a.get("transport") == b.get("transport") and
                (b["packet"]["seq"] - a["packet"]["seq"]) % 2**32 == 1 and
                is_active(a["packet"]) and is_active(b["packet"]))
    if not packets: return {"error": "no packets"}
    active = [(p, a) for p, a in packets if is_active(p)]
    out = {"packets": len(packets), "activeFrames": len(active), "transport": rows[-1].get("transport"),
           "deviceSeconds": round((packets[-1][0]["ms"] - packets[0][0]["ms"]) / 1000, 2)}
    out["measurementLimits"] = ["Arrival grouping includes Mac scheduling and observer timing; use the firmware link event for the negotiated BLE interval.",
        "Missing readings are estimated from adjacent active frames only, not counted at the sensor; sleep/session/sequence boundaries are excluded.",
        "Quiet windows are handheld candidates, not a fixed-board noise or temperature test."]
    if not active: return out
    gaps = sorted(packets[i][0].get("firstMicros", packets[i][0]["ms"] * 1000) / 1000 - packets[i-1][0]["ms"]
                  for i in range(1, len(packets)) if continuous(i) and
                  0 < packets[i][0].get("firstMicros", packets[i][0]["ms"] * 1000) / 1000 - packets[i-1][0]["ms"] < 1000)
    missing = sum(round(g / period_ms) - 1 for g in gaps if g > 1.5 * period_ms)
    out["deviceIntervalMs"] = {"median": q(gaps, .5), "p90": q(gaps, .9), "p99": q(gaps, .99), "max": gaps[-1] if gaps else None}
    out["estimatedMissingReadingsPercent"] = round(100 * missing / max(1, missing + sum(p.get("sampleCount", 1) for p, _ in active)), 1)
    arrivals = [a for _, a in active]
    burst, sizes, starts = 1, [], [arrivals[0]] if arrivals else []
    for a, b in zip(arrivals, arrivals[1:]):
        if (b - a) * 1000 < 3: burst += 1
        else: sizes.append(burst); burst = 1; starts.append(b)
    sizes.append(burst)
    intervals = sorted((b - a) * 1000 for a, b in zip(starts, starts[1:]) if b - a < 0.2)
    out["arrivalBursts"] = {"sizes": dict(sorted(Counter(sizes).items())), "startIntervalMsMedian": rounded(q(intervals, .5), 1),
                            "p10": rounded(q(intervals, .1), 1), "p90": rounded(q(intervals, .9), 1)}
    offsets = [a - p["ms"] / 1000 for p, a in active]
    lag = sorted((o - min(offsets)) * 1000 for o in offsets) if offsets else []
    out["arrivalLagAboveBestMs"] = {"median": rounded(q(lag, .5), 1), "p90": rounded(q(lag, .9), 1), "p99": rounded(q(lag, .99), 1)}
    G = [[p["imu"][k] for k in ("gx", "gy", "gz")] for p, _ in active]
    A = [[p["imu"][k] for k in ("ax", "ay", "az")] for p, _ in active]
    T = [p["ms"] / 1000 for p, _ in active]
    rates = sorted(math.sqrt(sum(v * v for v in g)) for g in G)
    full = max((abs(v) for g in G for v in g), default=0)
    out["gyroDps"] = {"median": rounded(q(rates, .5), 2), "p99": rounded(q(rates, .99), 1), "maxAxis": round(full, 1),
                      "axisReadingsAbove280": sum(1 for g in G for v in g if abs(v) >= 280)}
    quiet = None
    for i in range(0, max(0, len(G) - 50), 5):
        if any(b - a <= 0 or b - a > 0.05 for a, b in zip(T[i:i+50], T[i+1:i+50])): continue
        sd = [statistics.pstdev(c) for c in zip(*G[i:i + 50])]
        if quiet is None or sum(sd) < sum(quiet["gyroSd"]):
            quiet = {"gyroSd": [round(v, 3) for v in sd], "gyroMean": [round(statistics.mean(c), 3) for c in zip(*G[i:i + 50])],
                     "accelSd": [round(statistics.pstdev(c), 4) for c in zip(*A[i:i + 50])]}
    out["quietestWindow"] = quiet
    mean = [statistics.mean(c) for c in zip(*A)] if A else [0, 0, 0]
    norm = math.sqrt(sum(v * v for v in mean)) or 1
    out["heldGravityUnit"] = [round(v / norm, 3) for v in mean]
    # Gyro scale against gravity: integrate between consecutive still poses.
    still = [i for i in range(len(G) - 8) if all(abs(math.sqrt(sum(v * v for v in A[j])) - 1) < 0.04 for j in range(i, i + 8))
             and statistics.pstdev([math.sqrt(sum(v * v for v in g)) for g in G[i:i + 8]]) < 2 and max(math.sqrt(sum(v * v for v in g)) for g in G[i:i + 8]) < 12]
    bias = [statistics.median([G[i][k] for i in still]) for k in range(3)] if still else [0, 0, 0]
    pairs = []
    for a, b in zip(still, still[1:]):
        if b - a < 10 or T[b] - T[a] > 3 or angle(A[a], A[b]) < 12: continue
        if any(T[i+1] - T[i] <= 0 or T[i+1] - T[i] > 0.05 for i in range(a, b)): continue
        best = None
        for s in [x / 100 for x in range(60, 161, 2)]:
            f = list(A[a])
            for i in range(a, b):
                dt = min(0.05, T[i + 1] - T[i])
                f = rotate(f, [math.radians((G[i][k] - bias[k]) * s) for k in range(3)], dt)
            err = angle(f, A[b])
            if best is None or err < best[1]: best = (s, err)
        pairs.append({"turnDeg": round(angle(A[a], A[b]), 1), "bestScale": best[0], "residualDeg": round(best[1], 1)})
    out["stillBiasEstimateDps"] = [round(v, 2) for v in bias]
    out["gyroScaleCheck"] = pairs[:20]
    if pairs: out["gyroScaleMedian"] = statistics.median(p["bestScale"] for p in pairs)
    return out

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://127.0.0.1:8872")
    parser.add_argument("--seconds", type=float, default=60)
    parser.add_argument("--input"); parser.add_argument("--save")
    args = parser.parse_args()
    rows = json.load(open(args.input)) if args.input else capture(args.url, args.seconds)
    if args.save: json.dump(rows, open(args.save, "w"))
    print(json.dumps(report(rows), indent=1))

if __name__ == "__main__":
    main()
