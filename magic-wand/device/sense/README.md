# Sense wand profile

A separate hardware profile for the **original Seeed XIAO nRF52840 Sense** wand. The Puck.js
profile, its firmware and its installed program are unchanged and remain the default.

## How the controls are reused

The Sense does not get a second copy of the gestures. Wand Receiver runs the canonical Puck
program on the Mac: `device/wand-mouse-prototype.js`, the compact mode bridge and the compact
power policy, through the website's Espruino shim (`docs/sim/espruino.js`) and
`wand-sense-host.js`, in JavaScriptCore (`receiver/Sources/WandVirtualPuck.swift`). The receiver
talks to it exactly as it does to a Puck, through the same `queue(JS)` commands and UART lines.
All existing mouse, HUD, review, scrolling, dwell, screenshot, rest, Agent Flow and sleep
behaviour therefore applies unchanged, including the selected control version and options.

`wand-sense-host.js` supplies only device facts: real button pins, real gravity and gyro
readings at their device-aligned time, real timers, the status light, sensor power and
button-wake standby. Received readings are applied immediately. During radio backpressure,
firmware d represents a run by its mean rate, count and timestamps, so individual changes
inside that run are approximate. No intentional waiting is added; button, sensor and session
boundaries discard obsolete motion.

## Firmware

Release labels use numeric versions from now on, rather than letters. Keep a
legacy board's exact reported identifier in diagnostics until it is actually
flashed; never relabel an installed board as a newer release.

The board firmware and the Mac receiver are separate programs. The board reads
sensors and buttons and handles its radio, lights and power. The receiver owns
most mouse, HUD, click and gesture behaviour. Installing a receiver update does
not flash the board, and an older board identifier does not mean those Mac
improvements are missing. A built firmware file is only a candidate until the
board is flashed and its reported version is read back.

`wand_sense/wand_sense.ino` is the complete saved program (Seeeduino:nrf52:xiaonRF52840Sense,
core 1.1.13, Seeed Arduino LSM6DS3 2.0.7). Nothing is uploaded on connection.

| Physical button | Sense pin | Control | Wire channel |
| --- | --- | --- | --- |
| Button 1, left | D10 | HUD button (HUD/review) | `middle` |
| Button 2, centre | D8 | Mouse button | `thumb` |
| Button 3, right | D9 | Speech button | `index` |

The wire channel names are the dashboard's legacy `wand-v1` keys, kept as compatibility aliases; they do not name fingers or buttons. The buttons were formerly called Middle, Bottom and Top.

- Streams each 104 Hz LSM6DS3TR-C reading (gyro 500 deg/s range, accelerometer 4 g with the
  Puck's 50 Hz anti-alias filter) plus button edges and press counters. 10 ms switch debounce.
  A free link sends each reading at once. While the radio is busy, newer readings merge into
  the next frame (`count`, first time, mean rate) instead of blocking sampling;
  normal pointing uses the latest reading without replaying historical motion; gesture lanes retain their own timing.
- Asks macOS for the Puck's 15 ms connection interval after connecting and reports the
  negotiated interval, MTU, PHY and merged-frame counts as `Elink …` every 10 s.
- Takes light (`L`), sensor (`M0` off, `M1` accelerometer about 1.6 Hz, `M2` both at 104 Hz),
  heartbeat (`H`), standby (`Z`) and end (`X`) commands; identity on `?`.
- Without a host: orange, dark after one minute, button-wake power-off after five minutes;
  all three buttons flash every colour twice and power off. With the receiver, its canonical
  power policy owns the same choices. Power-off waits until every button is released; any
  one button wakes the board, and a button held at start-up is reported released until let go.
- Advertises `Magic Wand Sense` with the board ID in its scan response.

## Receiver profile

`~/Library/Application Support/WandReceiver/device.json`:

```json
{"profile": "sense"}
```

Optional `"sense": {"id": "…", "axes": ["-y", "+x", "+z"], "pointerGain": 1.1725}` pins one board and maps the Sense
axes onto the Puck's x (right), y (towards the tip) and z (up). The default axes assume the
board runs along the shaft with USB towards the tip and its parts facing up; this is not yet
physically verified. Without an ID, the first single Sense on USB is selected and saved in
`sense-device.json`; Bluetooth then reconnects only to that board. USB always wins; the
Bluetooth fallback is used only while no Sense is on USB. Calibration and the learned desk pose
are stored per Sense board and axes, never shared with the Puck.

Gyro readings are converted to the counts the Puck's identical LSM6DS3TR-C produces at its
245 deg/s setting (8.75 mdps per count), so every canonical speed, stillness, dead-zone and
calibration threshold matches the Puck physically. Earlier Sense builds used 134 counts per
deg/s; their saved zero is converted once. `pointerGain` (0.25–4, default 1.1725) is the only
Sense pointer difference: 86.4 counts per degree at full speed, the same feel as the 2026-10-29c
Sense build (1.17 times the Puck). Ethan asked for the earlier 25% boost (1.466) to be undone
once the wand returned to the other rod. HUD, review and scrolling are unchanged by it.

## Pointer path

The Sense uses the **direct** pointer by default: calibrated, orientation-projected gyro rate ×
time × the gain above, the 1.4 vertical gain and the one-third held gain, keeping the subpixel
remainder. Since 2026-10-29 it adds only what was measured or approved: Ethan's approved ~8 ms
causal smoothing of the rate, a continuous tiny-motion stop (still at or below the existing
slow-speed boundary, about 2.3 deg/s here, full gain from twice it) and a bounded step, so a
gap longer than 25 ms is skipped rather than caught up. In normal pointing, a reading that
arrives more than 75 ms behind the best delivery updates buttons, gravity and desk sensing but
never moves the pointer. Merged historical motion is also skipped during normal pointing. It still has none of the Puck filter's 150 ms directional mean, 250 ms
intent gate, 0.2° slack or slow-speed curve, and nothing is buffered or predicted.
Stop-to-click and screenshot settling judge the posted pointer counts, the pointer you see: the
quiet stop keeps tremor out. After a fresh movement arms clicking, 200 ms without posted movement
triggers one click; movement postpones it. A radio stall can still resemble a pause.
Held scrolling, HUD and review keep their own lanes and every reading. Options › **Pointer
filtering** (or `"sensePointer": "tuned"` in `feature-flags.json`) returns to the tuned filter;
the Puck always uses it. `status.json` and the dashboard report the path actually in use.

Expect the direct path to show what the filter used to hide: on the recorded Sense stream the
tuned filter passed only 8% of motion slower than 2°/s and first moved 173 ms into a steady
2°/s turn, against 10 ms direct. A residual zero error of 0.5°/s now drifts the pointer about
43 counts per second, and hand tremor appears as small movement. Still active by design: the
zero-buffer held LOW pointer routing, the bridge's 50–70 ms motion discard around
button edges, the 96 ms gyro start-up discard and the HUD's 1.2°/s dead zone.

## Debug pause

The dashboard's **Pause wand actions** button (`--receiver` mode) asks Wand Receiver to stop every
outward action: pointer, clicks, drags, scrolling, dwell clicks, recentring, HUD, review, screenshots
and dictation commands. Readings, lights, calibration, desk sleep and standby continue, and the
board keeps streaming full-rate motion for the dashboard. Held native buttons are released on
entry; a recording already in progress keeps going. After **Resume wand actions**, each button
needs a fresh press. The pause lives only in the receiver's memory and `status.json`; a receiver
restart clears it.

## Measured stream (2026-10-29, Bluetooth, firmware c, 90 s passive)

`hardware/xiao-wand-dashboard/measure.py` reads only the dashboard observer.

| Measure | Result |
| --- | --- |
| Sensor | Same LSM6DS3TR-C as Puck.js v2 (Espruino and Seeed documentation) |
| Host arrival grouping | About three readings every 30 ms; this is not proof of the negotiated radio interval |
| Estimated missing readings | 17.7% within adjacent active frames; p99 device-time gap 46 ms, max 112 ms; idle/session boundaries excluded |
| Cause in firmware | Core `BANDWIDTH_MAX` queues 3 notifications; `notify()` then waits up to 100 ms |
| Arrival lag spread | Median 44.5 ms above the best case, p90 69.5 ms, p99 110 ms |
| Clipping | 26 axis readings at the 286.7 deg/s full scale; fastest vector 420 deg/s |
| Gyro scale vs gravity | No qualified uninterrupted still-to-still turn in this capture |
| Held gravity | Mostly Sense +z; least rotation about Sense x (the shaft) |

Arrival times include host scheduling, so they are not radio-only or end-to-end latency.
Missing readings are estimated from timestamps, not counted at the sensor. Firmware d's
negotiated interval, delivery improvement and physical feel remain unverified until installation. The
quietest hand-held window had 0.6–0.9 deg/s gyro spread with 0.006–0.027 g accelerometer
spread: hand tremor, not sensor noise. Stationary noise with the gyro on, bias drift with
temperature and USB timing after firmware d remain unmeasured.

## Checks

`tests/sense-host.test.cjs`, `tests/native-sense.test.mjs` and `tests/sense-clock.test.mjs` run
the canonical program, the protocol and the firmware's merge and clock arithmetic on simulated
Sense input. They do not establish compilation for the board, flashing, Bluetooth
range, light colours, axis direction, pointer feel, latency or battery life.
