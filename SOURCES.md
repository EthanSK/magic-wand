# Sources and provenance

## Where the code came from

The wand was built in one of Ethan’s private working directories, alongside logs, receipts and
installation records. On 16 October 2026 `scripts/import_private.py` copied only the canonical
sources into this repository. `data/import.lock.json` records each file’s original and public
SHA-256; the private directory’s path isn’t recorded.

| Repository file | Origin | Change |
| --- | --- | --- |
| `device/wand-mouse-prototype.js` | Base Puck program | None |
| `device/wand-mode-bridge.js` | The current controls, applied over Bluetooth | None |
| `receiver/Sources/main.swift` | Wand Receiver | Device identity moved to `device.json` (below) |
| `receiver/Sources/WandControlTransport.swift` | HUD and speech sockets | None |
| `receiver/Sources/WandContextListener.swift` | Agentic Mouse HUD context | None |
| `receiver/Sources/WandRecordingState.swift` | Agent Flow recording state | None |
| `receiver/Sources/WandPointerControl.swift` | Display bounds, LOW routing, rough loops, HIGH dwell clicks and desk inference | None |
| `receiver/Info.plist` | Receiver bundle 1.2.23 (28) | None |
| `receiver/Sources/WandDeviceConfiguration.swift` | Written for this repository | New |

The installed receiver pinned one Puck’s CoreBluetooth identifier and advertised name. The public
copy has exactly four changes in `main.swift`: it reads both from `device.json`, refuses to connect
until one is set, and matches the name through `WandDeviceConfiguration`. The import script refuses
to write if any other identifier, home-directory path or token pattern would survive.

The private directory also held generated files; this repository regenerates them instead of
copying them:

| Generated file | Built by |
| --- | --- |
| `device/generated/wand-runtime-version.txt` | SHA-256 of the device program below its `// Adjust only` line |
| `device/generated/wand-commands.json` | The device program split into complete statements, for upload |
| `device/generated/wand-runtime.js` | The same program as one command |
| `device/generated/wand-boot.js` | The statements the Puck keeps in storage for boot |
| `device/generated/wand-mode-bridge.compact.js` | The bridge without comments, one statement per line |

`scripts/device_build.py` keeps the original algorithms. From the imported sources it reproduces
the private build byte for byte: runtime `wand-e1ce30d7c407`, commands SHA-256 `33bf21e3…`,
runtime SHA-256 `e25a4de5…`, boot image SHA-256 `b334feb2…` and bridge revision `95988d7a…`.
The bridge revision matches the receiver 1.2.23 (28) bundle, private cache and final live patch readback. The final power-state correction retained calibration and reported no error flags. Earlier large diagnostic queries raised LOW_MEMORY warnings without an observed out-of-memory failure. New gestures still need a physical check.
`tests/manifest.test.mjs` recomputes these identifiers on every run.

The private `wand-status.txt` described receiver 1.2.1 and an older button layout, so it wasn’t used.
Ethan’s interaction contract from the same directory was the reference for the controls in
`wand.json`; the tests compare those controls with the code, not with the contract.

### Tests

`tests/device-modes.test.cjs`, `tests/scroll-chord.test.cjs` and `tests/handshake.test.cjs` are ports
of the wand’s private regression scripts, rewritten to use the website’s Espruino shim. Each device
scenario runs with the readable bridge and with the compacted bridge sent statement by statement,
like the receiver. Older private scripts that tested superseded layouts weren’t ported.

## Left out

- Logs, install receipts, readback dumps, notification and speech payloads, and screenshots.
- Earlier receiver builds, rollback apps, device backups and private console tools.
- Purchase research and baskets for lighter switches. Those switches aren’t fitted, so the site
  doesn’t describe them.
- Agent prompts, transcripts and review notes.
- Copies of Espruino’s C sources that were kept for reference.
- The installed receiver’s icon, which draws Apple’s 🪄 emoji glyph. The public mark in
  `docs/icon.svg` is original, drawn by `scripts/make_images.py`, which also generates
  `receiver/AppIcon.icns` for receiver builds.

## The demo

`docs/sim/espruino.js` provides just the Espruino APIs the wand uses. It evaluates the unmodified
device program and compacted bridge in a Web Worker, like the Puck’s REPL. Espruino’s
`Function.replaceWith` changes a function in place; the shim gives each top-level device function a
stable forwarder, so the bridge’s replacements reach the same watches, timers and listeners.

| Demo part | Based on |
| --- | --- |
| Device behaviour, lights and timing | The real device program and bridge |
| `docs/sim/receiver.mjs` | A port of `receiver/Sources/main.swift`’s message handling |
| `docs/sim/pointer.mjs` | A port of `WandPointerControl.swift`’s circular-scroll recogniser; native and demo traces are compared on macOS |
| `docs/sim/hud.mjs` | A port of Agentic Mouse’s wand grid navigator, wheel-detent tracker and persistent HUD controller, from Ethan’s local Agentic Mouse build on 16 October 2026 (MIT, not yet published) |
| HUD labels and colours | Agentic Mouse’s published `simulator-data.json`, revision `e5fbb056` (v1.0.182 (188)), via `scripts/sync_hud.py` into `data/agentic-mouse-hud.json` |
| Agent Flow | Its public Primary behaviour: the first press starts, a later press stops on release |

What the demo doesn’t reproduce:

- Gyro readings are derived from the visitor’s aim at about 60 readings a second; the real wand
  requests 104 Hz and fully processed about 35 Hz in a recent measurement.
- Bluetooth delay, the Puck’s 20 ms switch debounce and its memory limits aren’t simulated.
- The 3D wand turns a quarter as far as the simulated sensor, so its tip stays below the HUD.
- HUD cards only report what they would do; child pages, held keys and app actions aren’t run.
- The Mac’s double-click interval is fixed at Ethan’s 0.8 seconds; a wheel line scrolls 14 points.

## Hardware

The Puck.js v2.1 at the tip of a roughly 50 cm carbon-fibre tube, with three separate wired
momentary buttons on the grip, comes from Ethan’s description of the current wand. The pins come
from the device code. There’s no photo; the website’s schematic and 3D model are illustrations, and
the button spacing and wire route in them are not measured. The flat Puck orientation in the 3D
model follows the device code’s axis mapping.

## Facts on the website

| Statement | Evidence |
| --- | --- |
| Controls and gestures | `device/wand-mode-bridge.js`, `docs/sim/receiver.mjs`, and the pipeline tests |
| Light colours and priority | The bridge’s `updateLights`, checked in `tests/manifest.test.mjs` |
| Gain 86.4, vertical × 1.4, 104 Hz requested, guards and timings | Device program and bridge, checked in tests |
| About 35 Hz processed | A measurement in Ethan’s wand session; not reproduced by these tests |
| Earlier controls physically tested; latest gestures and tuning unconfirmed | Ethan’s confirmations predate the endpoint-click and scroll-tuning changes |
| Newest guard passed device checks; feel unconfirmed | The 16 October 2026 readback; no physical confirmation yet |
| macOS pairing stalled | The wand session’s attempt at native HID bonding |
| Agentic Mouse wand support unpublished | Its wand files weren’t on `EthanSK/agentic-mouse` `main` on 16 October 2026 |
| Agent Flow wand input unpublished | Its public decoder accepted only `corsair` and `razer` sources on 16 October 2026 |

End-to-end latency, accuracy and battery life haven’t been measured, and the site doesn’t claim them.

## Third-party material

| Material | Licence | Notes |
| --- | --- | --- |
| Three.js 0.185.1 (`docs/lib/three-0.185.1/`) | MIT, `LICENSE.txt` | From the npm tarball, checked against its registry SHA-512. 0.186.1 ships no minified builds; 0.185.1’s match the files Agentic Mouse vendors |
| Big Shoulders Display | SIL OFL 1.1 | © 2019 The Big Shoulders Project Authors |
| Atkinson Hyperlegible Next | SIL OFL 1.1 | © 2020–2024 The Atkinson Hyperlegible Next Project Authors |
| Atkinson Hyperlegible Mono | SIL OFL 1.1 | © 2020–2024 The Atkinson Hyperlegible Mono Project Authors |
| Agentic Mouse HUD labels and colours | MIT | Ethan’s project |

`scripts/vendor.py` downloads these at pinned versions and `data/vendor.lock.json` records their
hashes. Fonts are Google Fonts’ Latin WOFF2 subsets.

The device code uses Espruino’s `ble_hid_mouse` module, which the Espruino Web IDE supplies; it
isn’t bundled here. Its Bluetooth advertising follows Espruino’s HID documentation. The UART UUIDs
in the receiver are the public Nordic UART Service. Puck.js and Espruino are made by Pur3 Ltd; this
project isn’t affiliated with them.

## Wand-only Command-Enter

`integrations/agentic-mouse/wand-command-enter.patch` records the four-file incremental change from the earlier local wand integration to the installed Agentic Mouse 1.0.261 (267). It is a recoverable source patch, not a complete Agentic Mouse distribution, and requires that earlier unpublished wand integration. The native handler holds Command across Return down/up and releases it on cancellation. The card is labelled `⌘↩ Steer` only for the wand; Corsair and Razer retain Enter. Focused tests and the full Agentic Mouse gate passed before signed installation; actual Steer acceptance remains unconfirmed. `wand.json` applies that card title over the unchanged published shared-mouse snapshot when generating the demo.

## App-specific review

`integrations/agentic-mouse/wand-app-review.patch` records the incremental source changes used by signed Agentic Mouse 1.0.262 (268). It depends on the earlier unpublished wand integration and is not a complete distribution. The receiver asks Agentic Mouse to enter the actual frontmost app’s controls, then consumes its same-user app context. In VS Code, Bottom sends source-isolated, ordered review requests to Better Git 1.2.127 over its registered URI handler; it reuses the existing staging transaction, Undo and file-range logic. Better Git is published on the Marketplace and its `codex/wand-review` source branch; the Agentic Mouse changes remain unpublished.

The main-HUD browser snapshot does not implement app-specific pages or the VS Code staging transport. Its double tap dismisses that snapshot; the installed receiver’s double tap enters the current app’s controls, and a second double tap leaves them. Native regression checks cover both modes and directions against real Git-index state. Physical wand acceptance of this integration is still pending.
