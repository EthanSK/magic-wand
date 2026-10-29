# Magic Wand Dashboard V2

A bench dashboard for the **original XIAO nRF52840 Sense** and three Choc switches. Version `2.0.0` identifies this dashboard; the telemetry protocol remains `wand-v1`. This is a separate diagnostic sketch and dashboard, not the full Puck mouse/HUD/speech firmware. Existing Puck and Control Hand code is unchanged.

## Run after pulling

Requires Python 3.10 or newer. The browser interface uses local files and no external web packages. For automatic USB/Bluetooth reading, prepare a fresh private runtime from the repository root:

```sh
git pull --ff-only
wand_runtime=$(mktemp -d "$HOME/Downloads/magic-wand-dashboard-v2.XXXXXX")
cp -R magic-wand/hardware/xiao-wand-dashboard/. "$wand_runtime/"
python3 -m venv "$wand_runtime/.venv"
"$wand_runtime/.venv/bin/python" -m pip install -r "$wand_runtime/requirements.txt"
"$wand_runtime/.venv/bin/python" -B "$wand_runtime/bridge.py" --hardware
```

Open **http://127.0.0.1:8872/**. Leave that terminal running. Grant the Python reader Bluetooth permission if macOS requests it. Use `--port` to choose another local port. Stop the previous reader before starting a replacement; only one process should own the board. The explicit `--hardware` flag opens the real connections from the private copy. Importing `bridge.py` or running it without that flag does not connect or flash anything.

The board must already run the matching diagnostic sketch below. Plugging in a board with unrelated firmware cannot supply these button readings. The dashboard never uploads firmware automatically.

For the labelled demo or manual browser readers, serve the repository root with `python3 -m http.server 8870 --bind 127.0.0.1` and open `/magic-wand/hardware/xiao-wand-dashboard/` on that server. Browser USB/Bluetooth readers require the corresponding APIs, such as Chrome on macOS, and a device choice after clicking Connect. The automatic local reader also works with an embedded browser because Python owns the hardware connection.

## With the control firmware

Once the board runs the Sense control firmware (`device/sense/`), Wand Receiver is its only
USB/Bluetooth owner. Start the reader with `--receiver` instead of `--hardware`: it observes the
receiver's accepted packets through a same-user datagram socket, opens no hardware connection and
sends nothing back, so it cannot compete for the board or move the pointer. `--hardware` remains
for the diagnostic sketch only; the two modes cannot be combined.

With the observer running, `python3 -I measure.py --seconds 60` reports cadence, missing readings,
arrival grouping, clipping, the held gravity frame and a gyro scale check from that same read-only
feed. Its arrival times include host scheduling; they are not end-to-end latency.

## What V2 shows

- Independent states for buttons 1, 2 and 3 (left to right): Pressed, Released or Unknown.
- Board press totals since the Sense last restarted in automatic local mode. The activity list starts with the current page/session. Manual browser and demo modes use session-relative counts.
- Acceleration in g including gravity, rotation speed in degrees/s, ten-second histories, and a relative gyro illustration. It drifts; Zero view resets only the illustration, not board calibration.
- Active transport, packet age, receive rate, rejected frames and button activity. A 1.5-second gap or disconnect makes current buttons Unknown and clears current axis values. History remains labelled as old data.
- Save readings exports up to 3,000 accepted packets as JSONL. Cumulative firmware counters preserve brief clicks between received frames.
- A clearly labelled demo with simultaneous buttons, keys 1/2/3 and Pause demo data to exercise stale state. It never connects to hardware.

## Automatic transport selection

The local reader prefers one connected original Sense over Bluetooth. While USB is present, Bluetooth is on standby. After USB removal it looks for exactly one `Magic Wand Sense` advertiser with Nordic UART notifications. The board needs battery power to continue when USB is unplugged. USB reconnection regains priority. This is transport selection; it does not charge the board or turn battery power on.

The local page disables browser device pickers and demo controls so a second browser reader does not compete. Original-Sense bootloader PID `0x0045` and ambiguous devices are not opened. The HTTP API is read-only, bound to loopback, checks Host headers, serves a fixed asset list and excludes device identifiers. Packet receive ages travel with the data so queued samples are not relabelled fresh.

Manual browser mode closes its previous reader when switching sources. It has no automatic fallback, rescan or reconnect. Do not use manual mode at the same time as the local reader.

## Wiring and firmware

| Switch | Sense label | MCU pin | Other contact |
| --- | --- | --- | --- |
| 1 · Left / Middle (HUD) | 10 / D10 | P1.15 | GND |
| 2 · Centre / Bottom (mouse) | 8 / D8 | P1.13 | GND |
| 3 · Right / Top (speech) | 9 / D9 | P1.14 | GND |

Use the two metal switch/socket contacts; an ordinary mechanical switch has no polarity. All three share GND. Internal pull-ups make pressed LOW. **No 3V3 wire goes to these switches.** The checked mapping is included in `pin-plan.json`; this dashboard does not depend on another unpublished wiring page.

The sketch is `firmware/wand_diagnostics/wand_diagnostics.ino`, compiled for `Seeeduino:nrf52:xiaonRF52840Sense` with Seeed nRF52 core **1.1.13** and Seeed Arduino LSM6DS3 **2.0.7**. It is not for MG24 or Sense Plus. Use the established private installation workflow for an authorised upload. This repository publishes source and does not install or restart hardware.

The sketch debounces switches for 10 ms and keeps cumulative press counters. USB snapshots are scheduled every 20 ms and Bluetooth snapshots at most every 50 ms when connected. Those are publication targets, not measured transport performance or latency. `imu` is null when no fresh six-axis sample is available; buttons remain valid independently. There is no finger multiplexer, battery reporting, RGB status, sleep, mouse, HUD or dictation code in this sketch.

## Wire format

Each transport carries newline-delimited JSON, including a leading newline for framing recovery:

```json
{"schema":1,"sensor":"wand","seq":1,"ms":20,"buttons":{"thumb":false,"index":false,"middle":false},"presses":{"thumb":0,"index":0,"middle":0},"imu":{"ax":0,"ay":0,"az":1,"gx":0,"gy":0,"gz":0}}
```

The original sketch’s `thumb`, `index`, `middle` keys identify D8, D9, D10 respectively. These legacy wire-channel names do **not** describe fingers: the grip buttons are numbered 1, 2, 3 left to right, so D10 is 1 (left), D8 is 2 (centre) and D9 is 3 (right). The dashboard labels and `pin-plan.json` preserve this distinction without requiring a firmware upload.

`seq`, `ms` and optional `presses` fields are unsigned 32-bit values. Wrapping is accepted; duplicate/out-of-order sequences are rejected. A board reboot needs a new reader session. All three buttons must be explicit booleans. `imu` may be null; otherwise all six axes must be finite numeric values. No device identifier or calibration is exported. Control Hand's `sensor: hand` and Puck packets are rejected rather than reinterpreted.

## Verification

From the repository root:

```sh
node --test magic-wand/tests/xiao-wand-dashboard.test.mjs magic-wand/tests/xiao-local-bridge.test.mjs
npm run check
```

Tests cover framing, invalid packets, short presses, simultaneous buttons, stale data, sequence wrap, USB priority and mock browser transport cleanup. They never connect to hardware.

On 28 October 2026 the sketch compiled using 125,820 bytes of flash and 14,564 bytes of globals. A separate authorised private installation produced real USB and Bluetooth packets containing all three button fields and the built-in IMU. The board press counters increased during testing. Battery-powered Bluetooth was subsequently observed live after the battery was connected. These observations do not establish solder quality, every physical control's acceptance or long-term Bluetooth reliability.

See [Seeed's original XIAO nRF52840 reference](https://wiki.seeedstudio.com/XIAO_BLE/), [Chrome Web Serial](https://developer.chrome.com/docs/capabilities/serial) and [Chrome Web Bluetooth](https://developer.chrome.com/docs/capabilities/bluetooth).
