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

### R58 key holder inputs (firmware 14)

These are the R58 connections as Ethan reported them on 23 November 2026, with the bench results from that night. An input counts as physically checked only after a recorded press or touch.

| R58 part | Sense pin | Firmware 14 | Bench check, 23 November 2026 (USB) |
| --- | --- | --- | --- |
| Upper-left key | D0 | Reported only, no control action yet | Not fitted |
| Upper-right key | D9 | Speech button, unchanged | Not fitted; see the note below |
| Lower-left key | D10 | HUD button, unchanged | Not fitted |
| Lower-right key | D1 | Reported only, no control action yet | Reads 0 when pressed |
| Centre click, press contact | D6 | Mouse button (wire channel 0) | Closes on every press |
| Centre click, resting contact | D8 | Reported only; no longer a control | Closed at rest, opens on every press |
| DFRobot DFR0030 digital touch output | D4 | Reported only; powered from 3V3 and GND | Reads 1 while touched |

Each key and click contact is a switch to shared GND, read through an internal pull-up. The fitted centre-click switch has a working resting contact. On the bench, D8 opened in an earlier report than D6 closed on 78 of 89 presses; on the other 11 both changed within one report. On release, D6 opened first on 57, and both changed within one report on the other 32. No press or release showed the reverse order. The delay between the two contacts was not measured. Which switch model is fitted, and which wire colour goes to which contact, is not yet established. D2 is blocked, and D3 and D5 are used by other parts.

Wire channel 0 (legacy key `thumb`, historically D8) now reads D6, so the R58 centre click gives the normal mouse-button behaviour. Firmware 13 read D8 as its mouse button, so the resting contact looked like a button held down continuously. Firmware 13 therefore held the mouse button down, could not sleep, and refused the wireless update as busy: the held-button check is the last of the update checks, after the key, signature, version, size and battery checks. D8 is now reported only, so it cannot hold a control, block sleep or block an update. For earlier Sense wiring with the mouse button on D8, use firmware 13 (source at commit `ade6f38`), or set `MOUSE_BUTTON_PIN` back to `D8`. The `S` frame, its three wire channels and the identity line are unchanged: receivers released before firmware 14 reject a frame with a button mask above 7 or extra fields.

D6, D9 and D10 are still controls, so pressing any of them still blocks a wireless update, as intended. An unfitted key lead can still matter: for about a minute on 23 November the speech channel (D9) followed the resting contact, reading pressed at rest and released while the click was pressed, then stopped. That is consistent with the loose D9 lead touching the resting-contact circuit; it is not confirmed. While D9 reads pressed, wireless updates are refused as busy and the wand cannot sleep. Insulate or fit loose key leads before relying on wireless updates.

To check each soldered input separately, firmware 14 also sends `Ein D0=l:n D1=l:n D4=l:n D6=l:n D8=l:n` event lines. `l` is the debounced pin level (1 = high, 0 = low) and `n` counts that pin's level changes since the board started. A line is sent when a level changes (at most every 25 ms), when a host session starts and every 10 seconds. The installed receiver logs these lines as `SENSE_EVENT`, so no receiver update is needed. Several changes inside 25 ms share one line, so these lines show the order of two contact changes only when they land in different lines, and never their exact spacing.

The levels are raw, not "pressed". A closed key or click contact reads 0. The DFR0030 drives D4 itself and reads 1 while touched; D4 has a pull-down, so it reads 0 when the module is unplugged or unpowered. D0, D1, D4 and D8 never wake the board, delay sleep or block an update, so a stuck or miswired lead on those pins cannot change the existing controls. They are disconnected in standby, so a lead stuck to GND draws no pull-up current while the board is off. D6 is the mouse button, so it does all three, like any grip button.

- Streams each 104 Hz LSM6DS3TR-C reading (gyro 500 deg/s range, accelerometer 4 g with the
  Puck's 50 Hz anti-alias filter) plus button edges and press counters. 10 ms switch debounce.
  A free link sends each reading at once. While the radio is busy, newer readings merge into
  the next frame (`count`, first time, mean rate) instead of blocking sampling;
  normal pointing uses the latest reading without replaying historical motion; gesture lanes retain their own timing.
- Asks macOS for the Puck's 15 ms connection interval after connecting and reports the
  negotiated interval, MTU, PHY and merged-frame counts as `Elink …` every 10 s.
- Takes light (`L`), sensor (`M0` off, `M1` accelerometer about 1.6 Hz, `M2` both at 104 Hz),
  heartbeat (`H`), standby (`Z`) and end (`X`) commands; identity on `?`.
- Without a host: pulsing white, dark after one minute, button-wake power-off after five minutes;
  all three buttons flash every colour twice and power off. With the receiver, its canonical
  power policy owns the same choices. Power-off waits until every button is released; any
  one button wakes the board, and a button held at start-up is reported released until let go.
- Advertises `Magic Wand Sense` with the board ID in its scan response.

Firmware 9 adds a local button acknowledgement: when the normal status light is
dark, a debounced physical press shows white for 160 ms. This includes the first
wake press, whose mouse/HUD/speech action is intentionally consumed. The light
does not wait for Bluetooth or the Mac. Existing mode colours take priority,
and normal idle darkness returns afterward. The all-button standby chord and
firmware-update patterns cancel the acknowledgement so their dark phases remain
dark. This changes only light feedback; it adds no pointer or button-action wait.
A light acknowledgement proves the firmware detected a press, not that the Mac
completed its action. No light by itself cannot distinguish missing power from
a button connection or startup failure.

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

## R58 battery

The R58 key holder runs on a Micron Radio Control 72217 pack: a single-cell, 3.7 V nominal, 100 mAh LiPo with a built-in protection circuit. These are the supplier's ratings, checked against the order and the product page on 23 November 2026; none were measured on the wand. The `battery` entry in [`prototypes/sense-r58.json`](../../prototypes/sense-r58.json) is the record, and the dashboard's R58 panel shows the pack from there.

- **Estimated charge.** Firmware 14 averages eight readings of the board's battery divider every 10 seconds and sends them as `V<millivolts>,<charging>`. Wand Receiver turns the voltage into a generic single-cell estimate: 3.30 V reads 0% and 4.15 V reads 100%, in a straight line. It is not calibrated for this pack, and the divider has not been checked against a meter. Charging raises the measured voltage, so the estimate reads high while charging.
- **Charging.** The flag is the charger's status pin. It reads not charging once a charge finishes, even with USB attached. The board core leaves the charge-current pin at Seeed's documented 50 mA setting, about 0.5C for this pack. Firmware 14 doesn't change it, and the actual current has not been measured.
- **Runtime.** Not measured. The 100 mAh capacity alone doesn't give a runtime, because the wand's average current in use is unknown. Measuring it needs one representative unplugged run: charge until the charging flag clears, unplug, use the wand normally over Bluetooth with Wand Receiver logging battery readings, and time it from unplugging until it reads 3.30 V or disconnects. That gives the runtime for that use and a voltage curve for calibrating this pack's estimate.
- **Safety limits are unchanged.** The board and Wand Receiver both refuse a wireless update below 3600 mV unless charging. The supplier doesn't state the pack's charge voltage, charge current or protection cutoff voltages.

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
