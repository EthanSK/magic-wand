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
button-wake standby. Readings are applied as they arrive; nothing is buffered or smoothed.

## Firmware

`wand_sense/wand_sense.ino` is the complete saved program (Seeeduino:nrf52:xiaonRF52840Sense,
core 1.1.13, Seeed Arduino LSM6DS3 2.0.7). Nothing is uploaded on connection.

| Physical button | Sense pin | Control | Wire channel |
| --- | --- | --- | --- |
| Button 1, left, middle finger | D8 | Bottom (mouse) | `thumb` |
| Button 2, centre, thumb | D9 | Top (speech) | `index` |
| Button 3, right, index finger | D10 | Middle (HUD/review) | `middle` |

The wire channel names are the dashboard's legacy `wand-v1` keys and do not name fingers.

- Streams each 104 Hz LSM6DS3 reading (gyro 245 deg/s, accelerometer 4 g, the Puck's scales) as
  it is read, plus button edges and press counters. 10 ms switch debounce.
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

Optional `"sense": {"id": "…", "axes": ["-y", "+x", "+z"]}` pins one board and maps the Sense
axes onto the Puck's x (right), y (towards the tip) and z (up). The default axes assume the
board runs along the shaft with USB towards the tip and its parts facing up; this is not yet
physically verified. Without an ID, the first single Sense on USB is selected and saved in
`sense-device.json`; Bluetooth then reconnects only to that board. USB always wins; the
Bluetooth fallback is used only while no Sense is on USB. Calibration and the learned desk pose
are stored per Sense board and axes, never shared with the Puck.

## Checks

`tests/sense-host.test.cjs` and `tests/native-sense.test.mjs` run the canonical program on
simulated Sense input. They do not establish compilation for the board, flashing, Bluetooth
range, light colours, axis direction, pointer feel, latency or battery life.
