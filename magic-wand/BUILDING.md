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

## 2. Load the base device program

1. Open the [Espruino Web IDE](https://www.espruino.com/ide/) and connect to the Puck.
2. Open `device/wand-mouse-prototype.js` and send it to the Puck. The IDE supplies the
   `ble_hid_mouse` module it uses.
3. Save it so it runs after a restart: run `save()` in the IDE’s console, or use the IDE’s Save on
   Send setting. The program’s `onInit` cleans up the state that `save()` restores.
4. While the light is red, keep the wand still with no buttons pressed. Calibration needs about two
   seconds of steady readings.

Ethan’s wand keeps a boot image (`device/generated/wand-boot.js`) in Puck storage behind a short
`.bootcde` loader. The tool that staged and verified it on his device isn’t part of this repository
yet; the steps above are the public path.

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
