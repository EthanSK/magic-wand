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
- Optional, for Middle and Top: [Agentic Mouse](https://ethansk.github.io/agentic-mouse/) and [Agent Flow](https://ethansk.github.io/AgentFlow/) builds with wand support. Neither is published yet, so with public builds only pointing, clicking, dragging and scrolling work.

## 1. Wire the buttons

| Button | Puck pin | Role |
| --- | --- | --- |
| Top | `D30` | Speech to text |
| Middle | `D2` | Agentic Mouse HUD |
| Bottom | `D1` | Mouse |

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

Middle talks to Agentic Mouse and Top to Agent Flow over same-user local sockets. The receiver only
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
