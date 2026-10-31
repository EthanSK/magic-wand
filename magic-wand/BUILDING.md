# Building Magic Wand

This is the `magic-wand/` component of the controller monorepo. Run the commands in this guide from this folder:

```sh
cd magic-wand  # From the repository root
```

The published site stays in `../docs/`; root `npm run check` checks every component.

This is a source-only project. There’s no packaged, signed or notarised receiver, and no release.
These steps describe the parts in this repository; they haven’t been rehearsed end to end on a
second wand.

## What you need

- A [Puck.js](https://www.espruino.com/Puck.js) v2.1 running Espruino.
- Three momentary push buttons, wire, and a tube or handle. Ethan’s wand is a roughly 50 cm carbon-fibre tube with the Puck at the tip and the buttons on the grip.
- A Mac with macOS 13 or later and the Xcode command line tools (`swiftc`, `codesign`).
- Python 3.10+ and Node.js 22+ for the build and tests.
- Optional, for the HUD button and the speech button: [Agentic Mouse](https://ethansk.github.io/agentic-mouse/) and [Agent Flow](https://ethansk.github.io/AgentFlow/) builds with wand support. Neither is published yet, so with public builds only pointing, clicking, dragging and scrolling work.

## 1. Wire the buttons

| Button | Puck pin | Role |
| --- | --- | --- |
| The speech button | `D30` | Speech to text |
| The HUD button | `D2` | Agentic Mouse HUD |
| The mouse button | `D1` | Mouse |

Connect the other side of each button to `GND`. The device code turns on the Puck’s internal
pull-ups, so a press reads low and no resistors are needed. If you mount the Puck differently,
check the gyro axes in `CONFIG` at the top of the device code: the wand maps the gyro’s z axis to
sideways movement and its x axis to up and down.

## 2. Install the complete saved device program

From the repository root, run `npm ci`, then from this component run
`python3 scripts/build.py`. The pinned minifier removes formatting without
changing variable names or compressing behavior.

`device/generated/persistent/manifest.json` maps each payload to its Puck Storage
filename and records its byte count and checksums. Install the whole set:

| Payload | Puck Storage name |
| --- | --- |
| `base.js` | `wand.boot.v4` |
| `bridge.js` | `wand.bridge.p1` |
| `power.js` | `wand.power.p1` |
| `startup.js` | `.bootcde` |

Use the documented Espruino `Storage.write(name, data, offset, size)` API with
bounded chunks. Inventory and back up an existing device before reclaiming old
images. Read back and verify every payload; activate `.bootcde` only with its
dependencies present. Flash compaction can move running function bodies, so do
it in a maintenance session with the old program stopped, before the clean boot.
Do not call `save()` over these flash-backed sources.

The startup contains the HID module, initializes the base and complete motion
bridge, loads the power policy and restores the device's `wand.zero` calibration
record. It does not depend on an old `.varimg` interpreter snapshot. The private
installer has been exercised on Ethan's wand; this is still not a packaged
installer for another owner's device.

Disconnect the programming console before starting the receiver. Verify a clean
saved-program restart and then a normal receiver connection without code upload.
Calibration is private device data, not a public firmware payload: an existing
wand keeps its accepted values, and a new wand learns its own stationary zero.

## 3. Build the receiver

```sh
zsh scripts/build_receiver.sh
```

This checks the generated files, compiles `receiver/Sources/*.swift`, adds the upload commands and
the compacted bridge from `device/generated/`, and ad-hoc signs `build.noindex/Wand Receiver.app` for your
Mac. It includes the original Magic Wand icon from `receiver/AppIcon.icns`;
`scripts/make_images.py` regenerates it alongside the website artwork.

The bundle identifier is `com.ethansk.wand-receiver`. If you already run an installed copy, change
`CFBundleIdentifier` in `receiver/Info.plist` and the `codesign` identifiers in the script for your
build, so macOS doesn’t confuse the two apps or their permissions.

## 4. Point it at your Puck

Create `~/Library/Application Support/WandReceiver/device.json`:

```json
{ "name": "Puck.js xxxx" }
```

Use the name your Puck advertises (the Espruino Web IDE’s device list shows it). You can add
`"identifier"` with the Puck’s CoreBluetooth UUID later; it only lets reconnects skip scanning.
`device.json` is ignored by Git.

## 5. Run it

1. Open `build.noindex/Wand Receiver.app` once. It has no window or Dock icon.
2. Allow Bluetooth when asked, and turn on Accessibility for Wand Receiver in System Settings →
   Privacy & Security. Starting it with `--request-permissions` shows the Accessibility prompt.
   It only connects once Accessibility is on, because it posts pointer, click and wheel events.
3. On each connection it compares the Puck’s runtime version with `wand-runtime-version.txt`.
   If they differ it uploads `wand-commands.json` (orange while updating), then sends the bridge
   one statement at a time.
4. To start it at login, add it to Login Items or a LaunchAgent. Ethan’s install uses a LaunchAgent.

Logs and status are in `~/Library/Application Support/WandReceiver/` (`receiver.log`,
`status.json`). Quitting with `SIGTERM` or `SIGINT` restores the Puck’s original Bluetooth mouse
sender before the receiver exits.

The HUD button talks to Agentic Mouse and the speech button to Agent Flow over same-user local sockets. The receiver only
accepts HUD context from `/Applications/AgenticMouse.app` and follows recording state for
`/Applications/AgentFlow.app`.

## 6. Change the controls

Edit `device/wand-mode-bridge.js`, update `wand.json`, then run:

```sh
python3 scripts/build.py
node --test tests/*.test.*
```

A rebuilt receiver sends a changed bridge on its next connection, because the bridge’s SHA-256 no
longer matches the Puck’s. A running receiver can also take a bridge without reconnecting: write
`// WAND_BRIDGE_UPDATE`, a newline and the contents of `device/generated/wand-mode-bridge.compact.js`
to `~/Library/Application Support/WandReceiver/maintenance.js` with mode `600`, then send the
receiver `SIGUSR1`. It caches that bridge for the same runtime and receiver build, so raise
`CFBundleVersion` in `receiver/Info.plist` when you rebuild; otherwise the cached bridge keeps
winning over the bundled one.

Changing the device program below its `// Adjust only` line changes the runtime version, so the
receiver re-uploads the whole runtime on the next connection.

## Checks

```sh
python3 scripts/build.py --check
python3 scripts/vendor.py --check
python3 scripts/check.py           # website checks only
node --test tests/*.test.*
npm --prefix .. run check          # repository-wide checks, including privacy
```

`tests/` runs the real device code and bridge through the website’s Espruino shim with a simulated
clock. These tests don’t replace trying the wand: physical feel, light colours and Bluetooth timing
only show up on the hardware.

## XIAO nRF52840 Sense wand

The Sense is a separate profile; the Puck steps above are unchanged. Install
`device/sense/wand_sense/wand_sense.ino` on the original XIAO nRF52840 Sense through the
private installation workflow, then set `{"profile": "sense"}` in `device.json`. The receiver
runs the canonical Puck program on the Mac for it, so every control and option above applies.
See [device/sense/README.md](device/sense/README.md) for wiring, protocol, axes and checks.

## Experimental wrist-roll compensation

The native receiver defaults to the original fixed mouse axes. To try gravity-based
wrist-roll compensation, add `"orientationCompensation": true` to
`~/Library/Application Support/WandReceiver/feature-flags.json`. Preserve any other
keys in that file. The receiver reloads it every five seconds; set the value to
`false` to return to the original mapping without reinstalling.

This changes native mouse pointing only. It reuses existing gravity telemetry,
rotates angular rates before the existing filter and sensitivity, and adds no
pointer buffer. It also corrects horizontal heading sensitivity as the tip rises,
before the nonlinear speed curve; correction is capped at 2x near vertical.
The chosen vertical multiplier and one-third held gain still apply afterward. HUD and chord scrolling retain their device-side mapping. This is
not absolute 3D position tracking; near a vertical shaft or during obvious
acceleration shocks it retains the last usable rotation estimate. Physical feel
still needs testing with the actual grip.


### Prepared Sense wireless application updater

The host updater needs the complete firmware-6 USB installation first. It updates
only the application, using an application-only Nordic/Adafruit legacy DFU package
for the original XIAO nRF52840 Sense. It does not replace the bootloader or SoftDevice.
Hardware transfer and interruption recovery remain unverified; USB recovery is still
required when the bootloader cannot return to the application.

The existing receiver watches its private support directory for
`firmware-update.request`. The installation workflow first checks Agent Flow is idle,
warns about the interruption, and validates the selected board/package. It then
writes an owner-only (0600) request atomically:

```json
{"version":1,"id":"<32 lowercase hex>","package":"<absolute unpacked package directory>","sha256":"<64 lowercase hex image hash>","firmware":7,"firstTrial":true,"acceptUSBRecovery":true}
```

The package must contain `manifest.json` and its named `.bin` and `.dat` files.
Preflight checks the exact image hash and embedded board/version marker, reviewed
bootloader 0.6.1 or 0.6.2, the exact original Sense SoftDevice/memory layout,
conservative application-size cap, key, battery and Bluetooth connection.
`firstTrial` allows an explicitly requested trial of a source-reviewed bootloader;
it does not mean that hardware was already proven. Independently,
`acceptUSBRecovery` must be explicitly true: these bootloaders use single-bank
updates and erase the running application before receiving its replacement.
An interrupted or invalid transfer can leave no runnable application. Resetting
cannot restore those overwritten bytes; recovery then requires the checked
application ZIP over the existing USB bootloader. The default is false, including
older requests that omit this field. No bootloader upgrade is required or performed.

Read `senseFirmwareUpdate` in `status.json` for the result. A request is consumed
once and never replayed across receiver restarts. Reconnecting cannot start an update.
If a previous attempt left a pending result, a separate owner-only
`firmware-update-reconcile.request` acknowledges only that exact observed result:

```json
{"version":1,"id":"<32 lowercase hex>","boardID":"<16 lowercase hex>","running":6,"target":7}
```

`running` and `target` must match the connected identity and pending target. Different
numbers acknowledge `not-installed` while preserving the failure; equal numbers
acknowledge `installed`, including after a receiver restart. The host waits for the
board's acknowledgement before clearing its pending status. Another normal update
request is required for a retry. Both request types are removed at receiver startup.

Source checks (no device connection or native input):

```sh
npm run check
swiftc -typecheck magic-wand/receiver/Sources/*.swift
```

Run those commands at the repository root. The test wildcard includes the updater
protocol, persistence and fake-Bluetooth transport tests; no additional package
script or installed application is needed.
