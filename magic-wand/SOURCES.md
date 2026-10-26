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
| `receiver/Sources/WandReviewTrace.swift` | Bounded opt-in local review point capture | None |
| `receiver/Sources/WandUART.swift` | Shared receiver and saved-program-console packet sizing | None |
| `receiver/Sources/WandPointerControl.swift` | Display bounds, LOW routing, rough loops, HIGH dwell clicks and desk inference | None |
| `receiver/Info.plist` | Receiver bundle 1.2.33 (38) | None |
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
runtime SHA-256 `e25a4de5…`, boot image SHA-256 `b334feb2…` and bridge revision `c6948df5…`.
The bridge revision matches the receiver 1.2.33 (38) bundle, private cache and final live patch readback. The final power-state correction retained calibration and reported no error flags. Earlier large diagnostic queries raised LOW_MEMORY warnings without an observed out-of-memory failure. New gestures still need a physical check.
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
  requests 104 Hz. The native receiver processed about 50 samples per second in the latest
  active windows. This is sample throughput, not a measurement of end-to-end latency.
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

## Horizontal app switching

`integrations/agentic-mouse/wand-horizontal-switcher.patch` preserves the incremental change installed in signed Agentic Mouse 1.0.263 (269). While holding the Switch App card, horizontal wand movement selects the next or previous app using the existing Command-Tab lifecycle; release chooses it. The patch includes focused control and modifier-lifecycle tests, and the complete native check passed before installation. The installed app’s signature, input readiness, command-socket ownership and unchanged mouse configuration were verified. Physical acceptance of horizontal selection remains pending. This patch depends on the earlier local wand integration and is not a standalone Agentic Mouse distribution.

## Sensor-rate and update readiness

Receiver 1.2.33 (38) retains 104 Hz after a 208 Hz trial felt more jumpy to Ethan, and keeps
1.6 Hz accelerometer-only idle sensing. The motion calculation uses private scalar state and cached references while keeping the accepted integration,
angular tolerance, gain and ordinary button-aware sender. Host tests compare exact reports with
the preceding calculation at 20, 35, 104 and 208 delivered samples per second. These comparisons
do not measure end-to-end latency or establish a delivered rate of 208 updates per second.

The update light is orange. An incomplete motion callback also holds orange; neither a timeout
nor a later ready marker is sufficient to clear a failed bridge load. The receiver rejects a
ready marker after an actual interpreter failure during that load. Recording remains red, mouse
mode blue, and a lost Bluetooth connection retains its dim-orange indication.

## Approved held-aim release-flick buffer

After clarifying that the old buffer never affected released-button HIGH, Ethan explicitly
approved restoring 90 ms for held LOW precision aiming on 17 October 2026. The Mac holds only
those pointer deltas and discards the final queued deltas on Bottom release, so the endpoint
click stays at the last shown position. Released HIGH, real left-button dragging and HUD input
bypass this queue. This changes the receiver and its browser model; the Puck bridge is unchanged.

## Wide UART motion and unchanged filtering

The Puck's original HID path clamps each axis to 127 counts. Applying that same limit to the
UART receiver discarded fast travel, especially at low delivered rates. The bridge and native
receiver now accept up to 4095 counts per axis for UART, while the HID fallback stays at 127.
Physical display bounds still clamp the final target. Tests exercise large UART travel, the
bounded HID fallback, and receiver rejection of out-of-range packets.

The exponential 2–8 ms filter, radial slack and intentional-motion thresholds are unchanged.
The implementation holds intent state in private scalars and skips the telemetry helper call
between its existing deadlines. These reduce repeated interpreter work without adding a queue
or changing filter coefficients. End-to-end smoothness still needs physical confirmation.

For the update indicator, Ethan identified the earlier nominal-white setting as the orange he
actually saw on this hardware. Updating therefore requests 0.45 on each LED channel; the public
display swatch describes the perceived orange, not a calibrated RGB measurement. No five-second
completion timeout is used. Failed loads remain visibly updating and may be repaired through the
same private maintenance channel while connected.

### Native pointing calculation

The native receiver opts into `@RAW dtMicroseconds,x,y,flags`. Raw axes are signed
16-bit gyro readings; `@ZERO` supplies their calibration offsets and 11 existing
tuning values. Flag 1 identifies a held Bottom button; flag 2 resets filter state
at a new active segment. Unknown/invalid samples are rejected. No future sample
is required. The Puck still owns button semantics, HUD angles and chord scrolling.
Other receivers keep the previous `@WAND` filtered fallback unless they opt in.

A cross-language test compares 2,400 samples against the actual Puck calculation,
including fast travel, quiet motion, intentional slow motion and one-third held
gain. A Swift test checks reset and invalid-input handling. The native receiver
records aggregate arrival timing once per five active seconds, not every sample.

Held LOW aiming is immediate again at Ethan's request. The optional 90 ms
buffer implementation remains disabled; enabling it requires fresh confirmation.

Ethan confirmed the native pointing felt much smoother on 17 October. Several active
windows delivered 244–254 samples over about five seconds. A brief 208 Hz trial
did not increase the received rate; 104 Hz remains selected.

## Wand VS Code home shortcuts

`integrations/agentic-mouse/wand-vscode-review-shortcuts.patch` preserves the incremental addition installed in signed Agentic Mouse 1.0.267 (273). It depends on the earlier local wand integration; apply this zero-context patch with `git apply --unidiff-zero`. The wand home HUD adds Review changes and Stage files immediately after Switch App only with VS Code frontmost; physical mouse grids remain unchanged. A held Middle publishes a short-lived review context. Wand Receiver 1.2.54 reuses its existing straight-to-circle scroll geometry and ordered Better Git review transport; release finishes and lost context cancels. Native input and rendered-layout checks passed. Physical gesture acceptance remains pending.

### Persistent wand review modes

`integrations/agentic-mouse/wand-persistent-review.patch` applies after the existing
wand VS Code review shortcut patch, using `git apply --unidiff-zero`. It retains
selected review mode independently of the visible HUD, adds the bottom-center
reminder and removes the healthy-hold duration limit. Receiver source preserves
the HUD through screenshot pointer use and never stops dictation on table rest.
Source tests pass; current local installation status is recorded in `wand.json`.

Better Git VS Code 1.2.130 enables its existing Eyes preview mode for wand change review; file staging uses its normal file mode. The focused real URI tests passed against Git-index changes and Undo. Marketplace validation and local Gallery installation were verified. VS Code’s extension host was restarted through its supported command and fresh Better Git activation was verified; physical wand acceptance remains pending.

The incremental `integrations/agentic-mouse/wand-bottom-placement.patch` preserves the native HUD layout installed in Agentic Mouse 1.0.275 (281). The main wand presenters and review reminder share bottom-centre placement above the actual visible Agent Flow recorder panels on each applicable display. WindowServer provides geometry; no recording command is sent for layout. Recorder geometry is polled only while the main HUD is visible, and unchanged geometry does not remeasure animated selection. This patch depends on the earlier unpublished wand integration. Clean native checks passed; installed visual overlap awaits normal unlocked-session input.

## Recording pauses pointer delivery

Receiver 1.2.77 observes Agent Flow's existing distributed recording notifications.
During recording the common pointer emitter drops motion and HIGH automatic clicks
are suspended. The latched follow choice stays intact; stop resets transient motion
and click state before fresh pointer movement resumes. No recording shortcut or
Agent Flow lifecycle change is used. Native inert-transport tests pass; physical
acceptance remains pending.

## Radial HUD, contextual holds and wake restoration

`integrations/agentic-mouse/wand-radial-controls.patch` records the incremental
change from the previously installed local integration to signed Agentic Mouse
1.0.276 (282). One shared radial layout places Switch App in the centre and
orders the other available actions clockwise. Native navigation, drawing and
liquid feedback use that layout; physical mouse grids are unchanged. It remains
a patch against the earlier unpublished wand integration, not a standalone
Agentic Mouse distribution. The browser simulator still shows its labelled older
grid interaction.

Wand Receiver 1.2.79 (84) restores contextual Bottom holds: a confirmed scrolling
surface scrolls; a draggable target drags. An unknown or late Accessibility
answer stays on the scrolling path, and a finished hold cannot accept a late
answer. The probe runs off the motion thread within the existing hold decision.
Sleep remembers the prior mouse-follow choice; manual choices and the one-time
recording pause take precedence. This adds no pointer buffer.

The complete native check passed, including the radial navigation and render
tests. The receiver's 18 native tests passed without skips against the candidate
sources. Both installed binaries, versions and preserved settings were checked;
the running radial HUD was visually inspected. Physical scroll/drag feel and
wake behaviour still need user acceptance.

## Held radial selection and larger labels

`integrations/agentic-mouse/wand-held-radial-ux.patch` applies after
`wand-radial-controls.patch` and records Agentic Mouse 1.0.277 (283).
Wand Receiver 1.2.80 (85) opens selection while Middle is held and uses the
outlined card on release. Completed actions hide the HUD; submenus and
adjustable cards remain for another hold. A quick tap from closed switches
app once; a held selection of Switch App retains its horizontal chooser.
The independent review lane, Bottom controls and Top dictation are preserved.
The home Enter card sends ordinary Enter again.

Titles fit whole lines to their wedge and use larger mixed-case text within
the same wheel. The focus has one continuously morphing outline, with a
continuity regression for the return to centre. Native and receiver tests
passed; installed visual checks confirmed the labels and submenu lifecycle.
Physical gesture feel and animation perception still need user acceptance.
The browser simulator remains the explicitly labelled older grid demo.

## Larger angled labels and stable placement

`integrations/agentic-mouse/wand-readable-anchored-hud.patch` applies after
`wand-held-radial-ux.patch` and records Agentic Mouse 1.0.278 (284). It raises readable title sizes and uses an upright
card-aligned tilt only when that permits materially larger text. Crowded titles
still fit whole words inside their own wedge; the wheel size and controls are
unchanged. The shared text planner is cached and timing-tested.

Each visible wand HUD now retains the recorder clearance it captured when it
opened. Agent Flow startup cannot move an active target up and down; reopening
refreshes the clearance. Both native presenters and the small review indicator
share this policy. Agent Flow itself is not changed or restarted.

## Passive Switch App navigation and held qualification

`integrations/agentic-mouse/wand-passive-switch-app.patch` records the native
addition installed in Agentic Mouse 1.0.281 (287). It applies after the earlier
local wand integration and adds passive hover only for the armed Switch App
card. Wand Receiver 1.2.84 (89) starts that passive stream between holds,
without a held-input timeout, and isolates Bottom scrolling from the outline.
Its existing hold threshold also sends one qualification signal while Middle
remains held, so the dotted outline appears before release. Qualification
changes presentation only; release still arms the card and the next hold
operates it. Both installed binaries and preserved settings were checked after
separate capture-idle gates. Native and receiver regressions pass; physical
acceptance remains pending.
## Shared HIGH sensitivity for Switch App

`integrations/agentic-mouse/wand-high-sensitivity.patch` applies after
`wand-passive-switch-app.patch` and records the native addition installed in
Agentic Mouse 1.0.282 (288). Wand Receiver 1.2.86 (91) sends the cumulative,
unrounded HIGH pointer calculation as optional `mouseX` motion metadata.
Only a held Switch App card consumes it. The existing seven-degree tracker
uses the reference gain of 86.4 counts per degree, preserving its full-speed
spacing while inheriting the mouse's fine-motion response. Other cards retain
angular input; metric transitions rebase rather than replaying a jump.

The saved `full-20261024c` program also emits explicitly marked HUD-only raw
samples when mouse follow is off. The receiver uses these for sensitivity and
returns before posting any mouse event. The complete base, bridge, power and
startup artifacts reproduce the saved payloads; their lengths and native CRC32
checksums were verified on the device, followed by a clean saved-program start
before the receiver reconnected. Calibration was retained. The redundant terminal
return in the affected Bottom handler is removed in this saved bridge.
Physical sensitivity preference, a real battery removal and the full five-minute
sleep/wake cycle still need user acceptance.

## Shared click and hold cues

`integrations/agentic-mouse/wand-gesture-language.patch` preserves the incremental
change from the local Agentic Mouse 1.0.282 (288) baseline to installed 1.0.283
(289), after `wand-high-sensitivity.patch`. Apply with `git apply --unidiff-zero`
against that baseline; it does not apply to the older public Agentic Mouse main
branch and is not a standalone distribution. Its SHA-256 is
`a370776fe1288857a5f3a0a734fc786e48d379c08a543fc96b774248b52a4edd`.
The published patch omits unchanged context, including a private historical
chat reference; its 22 resulting source files match the checked local patch.

Typed gesture metadata supplies action labels and held wheel/wand adjustment
cues to both grid and radial presenters. Copy/Paste names Space explicitly;
source-specific titles keep mouse and wand capabilities distinct. The patch
also includes the matching exporter, preview wording and tests. It was applied
to the retained pre-change source and all 22 resulting files matched the native
checkout. The installed build passed 1,058 native tests with two existing skips,
16 showcase tests and native rendered-layout checks; browser interaction and
physical wand acceptance remain unverified. The shared demo snapshot still
tracks the published Agentic Mouse site, which has not deployed this change.
