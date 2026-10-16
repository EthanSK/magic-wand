# [Magic Wand ↗](https://ethansk.github.io/magic-wand/)

[Try the wand](https://ethansk.github.io/magic-wand/) · [Ethan’s setup](https://ethansk.github.io/ethan-setup/) · [Agentic Mouse](https://ethansk.github.io/agentic-mouse/) · [Agent Flow](https://ethansk.github.io/AgentFlow/)

<!-- wand:intro -->
Mouse, HUD, scrolling and speech to text from three buttons on a wand.

Turning the wand moves my Mac’s pointer or the Agentic Mouse HUD outline. A Puck.js at the tip reads the rotation and sends it over Bluetooth.
<!-- /wand:intro -->

![Magic Wand](docs/assets/social.png)

The website runs the wand’s own device code in your browser, with the Mac side simulated, so you can try every control without the hardware. Nothing connects to a wand, Bluetooth or your Mac.

## Controls

<!-- wand:controls -->
**Top** (`D30`) · Speech to text

| Gesture | Result |
| --- | --- |
| Tap | Start Agent Flow dictation |
| Tap again | Stop and paste |

**Middle** (`D2`) · Agentic Mouse HUD

| Gesture | Result |
| --- | --- |
| Tap | Open the HUD on Switch App, then turn the wand to move the outline |
| Hold to open, turn, release | Use the outlined card on release |
| Tap again | Use the outlined card |
| Hold while open | Hold the card; on some wheel cards, tilt to turn the wheel |
| Double tap | Open the current app’s controls; double tap again to close |

- The outline stops at the edges instead of wrapping.
- Bottom goes back to the pointer.
- VS Code app mode: hold Bottom and tilt down or up to review changes. Crossed files are staged on release through Better Git. Double tap Bottom to toggle file staging mode; green is change review and purple is file staging.
- The browser demo shows the main HUD; native app-specific controls and desk detection need the installed integrations.

**Bottom** (`D1`) · Mouse

| Gesture | Result |
| --- | --- |
| Tap from off | Enter high-sensitivity follow without clicking |
| Stop after moving in HIGH | Click once after a 450 ms pause |
| Tap while following | Stop following without clicking |
| Hold, turn, release | Aim at one-third speed; release clicks once |
| Hold while following | Aim at low sensitivity; release clicks, pauses 300 ms, then resumes HIGH |
| Tap, then hold | Drag with the actual mouse button held; release drops |

- HIGH is released-button follow. LOW is a plain Bottom hold at one-third speed.
- Hold Bottom and make a rough clockwise loop to scroll down, or anticlockwise to scroll up. Cyan shows recognition; release stops without an endpoint click.
- Leave the wand idle on the desk for about two seconds to learn its resting pose. Picking it up can then enter HIGH automatically; setting it down stops following after sustained desk confirmation.
- Agent Flow stops after about five seconds of confirmed desk rest during recording. Moving the wand cancels the pending stop.
- Desk detection is an IMU estimate, not a touch sensor; a very still supported hand can resemble a desk. The browser demo covers the buttons, not physical desk detection.
- Middle switches to the HUD. The pointer stays within real display edges.

**Bottom + Middle** · Scroll

| Gesture | Result |
| --- | --- |
| Hold both and turn | Scroll sideways and up or down at once, including diagonals |
| Release either | Stop scrolling; nothing clicks |

**Lights**, highest priority first

| Light | Shows |
| --- | --- |
| Updating | Receiver is updating the device code |
| Disconnected | Dim orange |
| Calibrating | Keep it still with no buttons pressed for two seconds |
| Scrolling | Cyan |
| App review | Green for app review; purple for VS Code file staging |
| Pointer | Blue |
| HUD | Orange |
| Recording | Red, unless the pointer, HUD or scrolling is active |
| Idle | Off |
<!-- /wand:controls -->

## How it works

1. **Puck.js.** Espruino JavaScript on the wand reads the gyro and three buttons, sends raw pointing samples to the Mac and decides each button gesture.
2. **Bluetooth UART.** Short text lines carry raw gyro samples (`@RAW`), calibration and tuning (`@ZERO`), legacy pointer reports (`@WAND x,y,buttons`), HUD angles (`@NAV`), scrolling (`@SCROLL`), Bottom edges (`@BOTTOM`), Middle presses (`@MIDDLE`), Top presses (`@STT`) and light changes.
3. **Wand Receiver.** A background Mac app (Swift, CoreBluetooth) filters raw pointing samples with the same sensitivity and noise rejection, posts ordinary pointer, click and wheel events, sends HUD commands to Agentic Mouse and Top presses to Agent Flow over same-user local sockets, and sends the recording state back to the wand.
4. **Lights.** The wand shows its mode on the Puck’s RGB light; Agent Flow’s recording notifications keep it red while recording.

The Puck also advertises as a Bluetooth mouse, but macOS pairing stalled, so the receiver switches mouse reports to the UART link. On every connection the receiver checks the device code’s version and the bridge’s SHA-256; it uploads only what differs, one statement at a time, because one large command ran the Puck out of memory.

### Needs

<!-- wand:dependencies -->
- [Agentic Mouse](https://ethansk.github.io/agentic-mouse/): Draws the HUD and runs its cards. Wand support is in Ethan’s local build and isn’t published yet.
- [Agent Flow](https://ethansk.github.io/AgentFlow/): Records and pastes dictation. The public build accepts its mouse controls; wand input isn’t published yet.
- [Espruino](https://www.espruino.com/): JavaScript firmware on the Puck.js. Public. The first upload uses the Espruino Web IDE.
<!-- /wand:dependencies -->

Without Agentic Mouse and Agent Flow wand support, pointing, clicking, dragging and scrolling still work; Middle and Top have nothing to talk to.

The wand’s main HUD uses `⌘↩ Steer` on cell 7: it sends Command-Enter instead of ordinary Enter. Other mouse sources keep Enter. The tested local change is saved in [`integrations/agentic-mouse/wand-command-enter.patch`](integrations/agentic-mouse/wand-command-enter.patch); it depends on the locally installed wand integration, which is not on Agentic Mouse’s public main yet.

## Hardware

- Puck.js v2.1 at the tip of a roughly 50 cm carbon-fibre tube.
- Three separate wired momentary buttons on the grip: Top to `D30`, Middle to `D2`, Bottom to `D1`, each also to `GND`. The Puck’s internal pull-ups make a press read low.

No photo yet; the website shows a schematic. Lighter replacement switches have been researched but aren’t fitted, so they aren’t described here.

<details>
<summary>Tuning</summary>

Holding Bottom uses one-third of the normal pointer gain, for both temporary movement and
tap-then-hold dragging. Released-button follow keeps the normal gain. HUD movement and scrolling
keep their own settings. The factor is applied before fractional pointer counts are accumulated;
The pointer uses a 0.2-degree radial tolerance for hand wobble, with quiet re-centering.
LOW release clicks, holds the pointer for 300 ms and continues prior HIGH mode.
From off, LOW release clicks and returns to off. Tap-then-hold drags objects or text, then resumes prior HIGH after the same short pause.
Tiny starting nudges and reversals need to cross the angular tolerance; Ethan confirmed that noise rejection feels good.

<!-- wand:tuning -->
| Setting | Value | Note |
| --- | --- | --- |
| Pointer gain | 86.4 counts per degree | 20% below the earlier 108 |
| Vertical | × 1.4 | Up and down move further than sideways |
| Fine aim | 35% gain below 2°/s | Full gain from 18°/s |
| Noise zone | Up to 1.2°/s | Measured during calibration |
| Sensor | 104 Hz requested | About 50 Hz fully processed in a recent measurement |
| Bluetooth interval | 15 ms requested |  |
| Button-jolt guard | 50 ms after a press, 70 ms after a release | Motion in the guard is dropped, not replayed |
| Cold start | 96 ms settling | Skipped when the sensor is still warm |
| Gyro sleep | After 1 s idle | Accelerometer stays at 1.6 Hz for pickup; off on disconnect |
| Hold | 220 ms | Longer presses count as holds |
| LOW movement delay | 0 ms |  |
| HIGH stop-to-click | 450 ms still | One click after deliberate movement; no repeat while still |
| Double-click window | 0.3 s | Read from the Mac’s setting |
| Scrolling | Horizontal × 1.4 | Mac wheel gain 0.8 |
| Middle report | After 80 ms | So Bottom + Middle can become a scroll |
| Reports | Every 30 ms | While the HUD or scrolling is active |
| Calibration | 2 s still, no buttons pressed | Kept across reconnects |
<!-- /wand:tuning -->

</details>

## Status

<!-- wand:status -->
- Ethan confirmed the latest native pointing feels much smoother; the other experimental gestures still need a physical check.
- Held positioning clicks on release and resumes prior high sensitivity after 300 ms. Ethan confirmed the still-hand tolerance feels good.
- HIGH dwell, held rough circles, desk inference and VS Code review pass automated checks; physical acceptance is pending.
- End-to-end latency, accuracy and battery life haven’t been measured.

Receiver 1.2.35 (40) · device code `wand-e1ce30d7c407` · bridge `c6948df5` · updated 17 October 2026.
<!-- /wand:status -->

Source only: there’s no packaged receiver, signed app or release. [BUILDING.md](BUILDING.md) explains building the receiver and loading the device code.

## Repository

| Path | What it is |
| --- | --- |
| [`wand.json`](wand.json) | The one maintained description: controls, pins, lights, tuning, versions and dependencies |
| [`device/wand-mouse-prototype.js`](device/wand-mouse-prototype.js) | Base Puck program (Espruino JavaScript), loaded once from the Espruino Web IDE |
| [`device/wand-mode-bridge.js`](device/wand-mode-bridge.js) | The current controls, applied by the receiver over Bluetooth on top of the base program |
| [`device/generated/`](device/generated) | Upload commands, runtime, boot image and compacted bridge, built by `scripts/build.py` |
| [`receiver/`](receiver) | Wand Receiver’s Swift source and `Info.plist` |
| [`docs/`](docs) | The GitHub Pages website; `docs/sim/` holds the in-browser simulation |
| [`data/`](data) | Synced Agentic Mouse HUD labels, the import lock and the vendored-file lock |
| [`tests/`](tests) | Device, simulation, manifest and website checks |

## Run the checks

Requires Python 3.10+ and Node.js 22+; there are no npm dependencies.

```sh
python3 scripts/build.py --check   # generated files match wand.json and the sources
python3 scripts/vendor.py --check  # Three.js and fonts match their lock
python3 scripts/check.py           # website and privacy checks
node --test tests/*.test.*          # device code, receiver and HUD ports, manifest, site
python3 -m http.server 8848 --bind 127.0.0.1 --directory docs
```

Then open [127.0.0.1:8848](http://127.0.0.1:8848/). The demo needs an HTTP server because its worker loads the device code with `fetch`.

## Updating the wand

Change the wand first, then this repository: import the sources, update `wand.json`, rebuild and test. [AGENTS.md](AGENTS.md) has the exact steps and the rules that keep the website honest. [SOURCES.md](SOURCES.md) records where everything came from and what was left out.

## Licence

Code is MIT licensed. Three.js keeps its MIT licence and the fonts their SIL Open Font License, in `docs/lib/` and `docs/fonts/`. Agentic Mouse’s HUD labels and colours come from its MIT-licensed public website. Puck.js and Espruino are products of Pur3 Ltd; this project isn’t affiliated with them.

## Hardware prototypes

The original wand is [Prototype V1](prototypes/README.md), preserved at
[`prototype-v1.0.0`](https://github.com/EthanSK/magic-wand/tree/prototype-v1.0.0).
New hardware prototypes get separate profiles so the V1 controls remain recoverable.
