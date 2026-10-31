# [Magic Wand ↗](https://ethansk.github.io/magic-wand/)

This is the `magic-wand/` component of the controller monorepo. Run the commands in this guide from this folder:

```sh
cd magic-wand  # From the repository root
```

The published site stays in `../docs/`; root `npm run check` checks every component.

[Try the wand](https://ethansk.github.io/magic-wand/) · [Ethan’s setup](https://ethansk.github.io/ethan-setup/) · [Agentic Mouse](https://ethansk.github.io/agentic-mouse/) · [Agent Flow](https://ethansk.github.io/AgentFlow/)

<!-- wand:intro -->
Mouse, HUD, scrolling and speech to text from three buttons on a wand.

Turning the wand moves my Mac’s pointer or the Agentic Mouse HUD outline. A Puck.js at the tip reads the rotation and sends it over Bluetooth.

**The age of AI doesn’t need a keyboard.** The wand is my step toward that. It’s not a mouse replacement: lounge back with the wand and ask Computer Use for most things, ideally by talking through Hello Chat, then reach for your mouse and Agentic Mouse when you need precision. Keep the keyboard for text that has to be typed exactly, which I find is rare.
<!-- /wand:intro -->

![Magic Wand](../docs/assets/social.png)

The website runs the wand’s own device code in your browser, with the Mac side simulated, so you can try the button controls without the hardware. Nothing connects to a wand, Bluetooth or your Mac.

## Controls

<!-- wand:controls -->
**Speech button** (`D30`) · Speech to text

| Gesture | Result |
| --- | --- |
| Tap | Start Agent Flow dictation |
| Tap again | Stop and paste |
| Double tap while recording or transcribing | Won’t paste: copy the text without pasting it |

- Recording stays red in mouse mode. HUD, review, scrolling and loading keep their own indication.
- Putting the wand down never stops dictation. Use the speech button to stop and paste.

**HUD button** (`D2`) · Agentic Mouse HUD

| Gesture | Result |
| --- | --- |
| Quick tap from closed | Switch app once, after waiting at most 0.3 s for a second click |
| Double click from closed | Right-click at the pointer, with mouse follow on or off |
| Hold, turn, release | Open the HUD, point to a card and use it on release; the HUD stays open |
| In an open HUD or submenu | Move the wand to outline a card without holding the HUD button, then click it, or hold, aim and release, to use it. Select as many times as you want |
| Adjustable card | Click it, or release on it, to select it (dots); hold the HUD button and move to adjust, release to stop and reset the wand; tap to deselect |
| Hold the HUD button on an adjustable card | In wedge selection, hold and move the way its arrows point, like scrolling: values up or down; Spaces, scrolling, tabs and history left or right. Release to stop |
| Release a hold on Switch App | Armed for the next hold: unheld movement can still pick other cards; hold the HUD button on Switch App, move left or right, release to switch; in an open HUD a fresh hold on Switch App chooses at once |
| Go out twice on a card | Outer quick actions: Undo beyond Keys, Space beyond Enter, and in VS Code Review changes and Stage files beyond the app card. New Codex chat is on the main ring |
| Go out twice on Utility | Zoom, directly beyond Utility |
| In VS Code review | Circle clockwise for next and anticlockwise for previous; click the HUD button to exit, double-click to swap Review changes and Stage files, hold to stage the selection |
| Double click in an open HUD | Close the entire HUD |

- The installed wand uses a radial HUD with Switch App in the centre. The browser demo retains its earlier grid.
- The browser demo shows the main HUD; native app-specific controls and desk detection need the installed integrations.
- Ordinary actions act once and keep the HUD open on the same card, so you can select as many times as you want. Only a double click, Close or locking the Mac closes it; every open page’s centre says “Double click to close”. Exceptions: Screenshot parks the HUD for its crosshair; a quick tap from closed on Switch App and the held Switch App chooser switch and close; Review changes and Stage files hide the HUD for review. Unheld wand movement moves the outline; click the HUD button to use the outlined wedge. There is no inactivity timeout. The mouse and speech buttons remain independent.
- Adjustable cards are held only: click or release on one to select it (dots), then hold the HUD button and move to adjust it; releasing stops so the wand can reset, and nothing listens while the HUD button is up. Each card’s arrows show its direction: values move up and down; Spaces, Horizontal Scroll, Magnet, tabs, chat and cursor history and Tracks move left and right; Mission Control and similar actions act once per quick held swipe. Tracks keeps its click. Copy/Paste has no click on the wand; Space is its own outer card beyond Enter. Switch App: a tap switches once; in an open HUD a fresh hold on it chooses apps by moving left or right, and release switches.
- The wand home ring is grouped, clockwise from 12: the app card, Utility, Play/Pause, YouTube, Horizontal Scroll, Forward, Back, Enter, Copy/Paste, New Codex chat, Close and Keys. These positions stay the same in every app. Keys puts ← ↑ ↓ → across the top; Utility mirrors home, with Zoom beside Brightness. A second outer layer holds quick actions one reach further out on the same wedge: a thin Undo beyond Keys, Space beyond Enter, and, only while VS Code is frontmost, larger Review changes and Stage files beyond the app card. Zoom is in the second layer beyond Utility. On the wand, cell 10 reads Close and never holds Command, cell 5 reads Forward without the mice’s volume chord, and Codex Pin/Unpin has no Hold 2 cue. The physical mice are unchanged.
- The mouse, HUD and speech buttons are independent. Mouse follow can keep running while review is selected.
- In VS Code, go out past the app card and tap Review changes or Stage files to enter and hide the HUD. Move through a rough quarter-circle or diamond corner: clockwise for one next step, anticlockwise for one previous step, with no button held. A full loop gives four steps; straight up/down flicks are disabled. Tap the HUD button once to cancel and exit after at most 300 ms, double-click to switch between Review changes and Stage files, retaining the selection and including the current file without staging, or hold it for about half a second to stage the working selection and keep reviewing. Navigation stays frozen until release. The floating indicator says “Hold to stage selection” and names the mode a double-click will enter. Review changes uses Better Git eyes mode; Stage files uses its whole-file selection.
- Review input only runs while VS Code is frontmost. The small review indicator stays above Agent Flow.
- The native wand home HUD has Play/Pause after Utility around the ring. It uses the Mac’s standard media key, without changing either physical mouse.

**Mouse button** (`D1`) · Mouse

| Gesture | Result |
| --- | --- |
| Tap from off | Enter high-sensitivity follow without clicking |
| Stop after moving in HIGH | Click as soon as a larger, brisk move clearly stops; slow precision aiming keeps the 200 ms pause |
| While choosing where to click | Keep moving the wand slightly while you are not certain about placement so it does not click. Stop when you are ready. The pointer must still be moving; tiny movements filtered out as hand noise do not prevent a click. |
| Tap while following | Stop following without clicking |
| Hold | Over a scroll area, drag to scroll. Holding still continues page scrolling; sideways swipes end when the stroke stops. A confirmed draggable target drags instead. Release stops the gesture. |
| Tap, then hold the second press | Drag with the mouse button down; release to drop |
| Double tap | Centre the pointer on the main screen and enable mouse follow after the 300 ms triple-tap window; keep HUD and review selection unchanged |
| Triple tap | Start screenshot selection; hold the mouse button and move to select the area, then release to capture |

- Control V3 keeps ordinary short taps and tap-then-hold dragging unchanged. Clear sideways flicks can qualify before the usual 220 ms hold cutoff; other gestures keep that cutoff.
- A plain hold scrolls a scroll area or drags a confirmed draggable target. Unknown targets keep scrolling. Tap, then hold the second press to drag explicitly. The pointer stays fixed while scrolling until release.
- The HUD button switches to the HUD. The pointer stays within real display edges.
- Releasing a completed scroll restores the mouse-follow choice from before scrolling: off stays off and on stays on.
- The mouse button never opens, closes or clears the HUD or review selection.
- V3 uses straight strokes in either axis, including diagonals. Holding still continues the captured speed; a new stroke can change speed or reverse without releasing. Much faster strokes go beyond the normal maximum, up to 600 lines per second. Circular page-scroll recognition is disabled; V2 remains selectable.
- Screenshot opens the native macOS selection and moves the pointer even with mouse follow off. After a triple tap, hold the mouse button and move to select the area, then release to capture. Finishing or cancelling restores the previous mouse-follow choice.

**Lights**, highest priority first

| Light | Shows |
| --- | --- |
| Updating | Blinks orange while loading or updating the device code |
| Disconnected | Orange while unavailable |
| Calibrating | Keep it still with no buttons pressed for two seconds |
| Sleeping | Off after a minute on the desk; pickup restores the light |
| Scrolling | Cyan |
| App review | Green for app review; purple for VS Code file staging |
| HUD | Green |
| Recording | Red while recording; briefly shows blue when a click is sent |
| Pointer | Blue while the pointer follows; briefly dims when a click is sent |
| Idle | Off |
<!-- /wand:controls -->

## User options

Wand Receiver is a background Mac app. Its wand icon in the menu bar provides:

- **Control version → V2 · Hold to scroll**: hold Bottom and start left/right for
  horizontal scrolling, or up/down for vertical scrolling. Continue in circles;
  release to stop. A plain hold scrolls a scroll area or drags a confirmed
  draggable target; an unknown target keeps scrolling.
  To drag, tap Bottom, then press again and keep it held. Release to drop.
  Short taps retain their existing mouse behavior.
- **Control version → V1 · Pointer** restores the previous Bottom gestures. The exact
  pre-V2 implementation is also saved at `controls-v1.0.0`; see `control-versions/`.
- **Options → Review with nods and shakes** is off by default. When enabled,
  an up-and-down motion goes next and a side-to-side motion goes previous in
  Review changes or Stage files. Every clear direction change makes a step. It replaces only their circles and flicks.
- **Options → Rotation-independent controls** keeps screen directions upright while
  rotating the wand. Flick scrolling is available only in Control V1.

The existing 220 ms tap-versus-hold cutoff is unchanged. No movement buffer is added.
Scrolling uses the pointer position captured at press. Native dragging requires an
explicit tap-then-hold. HUD, speech, VS Code review and two-button scrolling are unchanged.
The browser demo still shows Control V1; V2 needs the native receiver.

## How it works

1. **Puck.js.** Espruino JavaScript on the wand reads the gyro and three buttons, sends raw pointing samples to the Mac and decides each button gesture.
2. **Bluetooth UART.** Short text lines carry raw gyro samples (`@RAW`), calibration and tuning (`@ZERO`), legacy pointer reports (`@WAND x,y,buttons`), HUD angles (`@NAV`), scrolling (`@SCROLL`), Bottom edges (`@BOTTOM`), Middle presses (`@MIDDLE`), Top presses (`@STT`) and light changes.
3. **Wand Receiver.** A background Mac app (Swift, CoreBluetooth) filters raw pointing samples with the same sensitivity and noise rejection, posts ordinary pointer, click and wheel events, sends HUD commands to Agentic Mouse and Top presses to Agent Flow over same-user local sockets, and sends the recording state back to the wand.
4. **Lights.** The wand shows its mode on the Puck’s RGB light; Agent Flow’s recording notifications keep it red while recording.

The Puck also advertises as a Bluetooth mouse, but macOS pairing stalled, so the receiver switches mouse reports to the UART link. On every connection the receiver checks the device code’s version and the bridge’s SHA-256; it uploads only what differs, one statement at a time, because one large command ran the Puck out of memory.

### Needs

<!-- wand:dependencies -->
- [Agentic Mouse](https://ethansk.github.io/agentic-mouse/): Draws the HUD and runs its cards. Public source includes wand support.
- [Agent Flow](https://ethansk.github.io/AgentFlow/): Records and pastes dictation. The public build accepts its mouse controls; wand input isn’t published yet.
- [Espruino](https://www.espruino.com/): JavaScript firmware on the Puck.js. Public. The first upload uses the Espruino Web IDE.
<!-- /wand:dependencies -->

Without Agentic Mouse and Agent Flow wand support, pointing, clicking, dragging and scrolling still work; Middle and Top have nothing to talk to.

The wand’s main HUD uses ordinary Enter, like the physical mice. Native wand integration is supplied as incremental patches under `integrations/agentic-mouse/`; it is not on Agentic Mouse’s public main yet. The latest installed native delta, [`wand-chat-keys-review-toggle.patch`](integrations/agentic-mouse/wand-chat-keys-review-toggle.patch), adds repeatable Keys actions, the review-mode toggle and its floating hint, and the native new-chat adapter. The new-chat adapter still needs Agent Flow and receiver orchestration; that shortcut is not yet complete.

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
| Puck fine aim | 35% gain below 2°/s | Full gain from 18°/s; Sense direct also stops tiny motion |
| Noise zone | Up to 1.2°/s | Measured during calibration |
| Sensor | 104 Hz requested | About 50 Hz fully processed in a recent measurement |
| Bluetooth interval | 15 ms requested |  |
| Button-jolt guard | 50 ms after a press, 70 ms after a release | Motion in the guard is dropped, not replayed |
| Cold start | 96 ms settling | Skipped when the sensor is still warm |
| Gyro sleep | After 1 s idle | Accelerometer stays at 1.6 Hz for pickup; off on disconnect |
| Hold | 220 ms | Longer presses count as holds |
| LOW movement delay | 0 ms |  |
| HIGH stop-to-click | 200 ms still | One click after deliberate movement; no repeat while still |
| Double-click window | 0.3 s | Read from the Mac’s setting |
| Scrolling | Horizontal × 1.4 | Mac wheel gain 0.8 |
| V3 held scrolling | 1.6 lines per degree, up to 120 lines/s | Strokes faster than 120°/s rise to 1200 lines/s |
| HUD button report | After 80 ms | So the mouse and HUD buttons together can become a scroll |
| Reports | Every 30 ms | While the HUD or scrolling is active |
| Calibration | 2 s still, no buttons pressed | Kept across reconnects |
<!-- /wand:tuning -->

</details>

## Status

<!-- wand:status -->
- Installed: receiver158 and the Sense dashboard enforce a persisted ten-minute temporary sensor capture, followed by deletion two hours later. Reconnecting or restarting does not extend the window. Byte caps remain and deliberately saved references are excluded. Both live recorders report matching deadlines; source, resources, Bluetooth and firmware8 were verified. All253 Wand,17 Control Stones and4 shared checks passed, including expiry, restart and cleanup tests. Click and pointer behavior are unchanged.
- Installed: receiver1.2.152 build157 preserves brisk-stop evidence across brief Bluetooth delivery gaps only when the sensor intervals remain continuous. Fresh stop confirmation, genuine sensor-gap rejection, the slow precision path, pointer filtering and the blue click cue are unchanged. All253 Wand,17 Control Stones and4 shared checks passed; installed source, resources, Bluetooth and firmware8 readback verified. The saved slow-aim exercise keeps its precision protection; physical reliability remains for user review.
- Installed: receiver1.2.151 build156 uses the visible pointer stop after a recent brisk move, tolerates a brief settling tail and measures speed from sensor time. Sent clicks briefly dim the blue light or show blue from another mode, then restore current status. Slow precision timing, pointer filtering and firmware8 stay unchanged. Signed source, bundled resources, Bluetooth and firmware8 readback verified; all253 Wand,17 Control Stones and4 shared checks passed after installation. Live fast-stop clicks and their blue-light commands were observed; physical click feel and blink visibility remain for user review.
- Installed: receiver1.2.150 build155 fixes the fast-stop click integration: motion-intent heartbeats no longer erase brisk-move evidence, and a residual stop count without visible pointer travel no longer cancels it. Slow approach keeps the normal200 ms pause. The actual filter and click call order now reproduce the old wait and pass with the correction. Signed installed source and resources match; Bluetooth and firmware8 readback verified. All252 Wand,17 Control Stones and4 shared checks passed after installation. Physical click feel remains for user review.
- Installed: receiver 1.2.149 build154 uses the physical release frame to stop replaying obsolete stroke motion after a stalled Bluetooth batch. Existing timing, pointer filtering, fast-stop clicking and held-scroll behavior are preserved. This fixes a reproduced delayed-frame path; the observed fresh post-scroll motion still needs a separate recoil decision. Signed build and source readback match;252 Wand,17 Control Stones and4 shared checks passed. Button-wake Bluetooth reconnection is verified with saved firmware8. Ethan chose immediate pointer movement; no post-scroll recoil suppression was added.
- Installed: receiver 1.2.148 build153: a larger, brisk pointer move can click as soon as fresh stillness samples confirm its stop; slow precision aiming retains the existing 200 ms pause. Brief pauses, missing data and scroll-release motion cannot trigger the quicker path. Pointer motion, smoothing, gain and plain tap-to-exit are unchanged. Focused and saved slow-reference checks pass; Bluetooth, the signed installed program and saved firmware8 were verified; physical feel is pending.
- Installed: Agentic Mouse 1.0.315 build 321 fixes one-click unlocking after a value adjustment or missing navigation message. Copy/Paste can proceed to Enter without closing the HUD. All 1,250 native tests pass, with 4 skipped; physical button reliability remains unconfirmed.
- Installed: receiver1.2.147 build152 restores plain tap-to-exit without a click. Automatic stillness clicking remains enabled. The earlier quiet long-hold stop is retained only behind the disabled quietMouseHold flag; the withdrawn early-stop and dark-light additions have been removed. Scroll sensitivity, double/triple shortcuts and ordinary pointer timing are unchanged. Bluetooth, saved firmware8 and the disabled flag were verified. All250 Wand,17 Control Stones and4 shared checks passed, including legacy Puck storage. Physical feel remains for user review.
- Installed: receiver1.2.145 build150 adds dim/bright Sense mode-light feedback and the bounded eight-second RGB demo. The demo ran once and restored normal status in the same Bluetooth session. Receiver147 scroll/click behavior, calibration and saved firmware8 are preserved. Physical light preference remains unverified.
- Installed: Agentic Mouse1.0.314 build320 fixes the wand-home YouTube rewind and Forward guards, and keeps incoming movement from shortening the selection spring. Build318 Zoom placement and screenshot-window recovery remain. The1,248 native tests pass; Ethan confirmed wand YouTube rewind now works. Physical animation preference remains open.
- Superseded by receiver152: Installed: receiver1.2.142 build147 adds a long mouse-button hold begun in follow mode, without a scroll gesture, to stop follow on release without clicking. Existing taps, scrolling, dragging and screenshot shortcuts remain unchanged. Bluetooth reconnected; local checks pass. Physical quiet-hold acceptance is pending.
- Installed: receiver 1.2.141 build146 increases page-scroll output from1.3x to1.7x, including low speeds. The flick-and-hold curve, timing, horizontal swipe strength, pointer filter and both click behaviors are unchanged. Bluetooth reconnected and focused checks passed; physical sensitivity acceptance is pending.
- Receiver1.2.138 build143: page scrolling is30% more sensitive, with the existing gentle low-speed curve, cumulative flicks and1560 output lines/second ceiling. Sideways swipes, pointer motion and stroke timing are unchanged. Physical sensitivity acceptance pending.
- Installed: Agentic Mouse 1.0.310 build 316 adds Brightness to the home HUD’s second layer, between Utility and the unchanged third-layer Zoom. Build 315’s restored dragging is retained. The installed app and rendered layout were checked; physical Brightness use remains unverified.
- Installed: receiver 1.2.137 build 142 and Agentic Mouse 1.0.309 build 315. Clear sideways flicks can start before the 220 ms hold threshold; ordinary taps, page scrolling and dragging keep their timing, and accepted short swipes stay separate from click shortcuts. No pointer delay was added. Faster Back/Forward and abrupt-stop feel still need physical confirmation.
- Installed: Agentic Mouse 1.0.308 build 314 adds built-in left/right window snapping to the Magnet card. Repeating at an occupied screen half moves the window to the neighbouring display. Existing HUD layout and wand controls are retained; standalone snapping apps stay installed. Focused geometry, cancellation and readback checks passed; physical cross-monitor acceptance remains unverified.
- Installed: receiver 1.2.136 build 141 and Sense firmware 8. The first wireless update completed, the wand restarted over Bluetooth, and the receiver confirmed firmware 8 with calibration and the update key preserved. Startup and ordinary disconnection pulse white every 275 ms until connection or the existing one-minute dark timeout. Receiver-restart colour cycling and the short sleep warning are unchanged. The first update attempt stopped before authorization; package and key checks now run outside the input thread, with the live connection rechecked before authorization. Interrupted wireless updates can still require USB recovery.
- Installed: receiver 1.2.135 build 140 and complete Sense firmware 7. Bluetooth works with USB removed, confirmed by live input and user feedback. Calibration and the update key are preserved. Page scrolling uses fine pixel output, sideways native gestures end at wrist stop, and the approved 300 ms exit-click window preserves double and triple shortcuts. All 247 receiver tests pass. The first wireless firmware transfer and physical acceptance of the latest scrolling remain unverified. The reviewed single-bank bootloader can require USB recovery after an interrupted update.
- Receiver140 prepared: verified single-bank updater policy for the actual0.6.1 bootloader, explicit USB-recovery acceptance required. Receiver139 pixel scrolling is installed. Firmware6 is installed but its long Bluetooth identity is truncated; packetized firmware7 repair is being prepared.
- Receiver1.2.134 build139 prepared: V3 pages use precise pixel output at the existing20ms cadence for smooth slow scrolling. Native sideways stroke endings and300ms exit-click cancellation are retained. Wireless host prepared; complete Sense6 still needs its first USB installation and hardware verification.
- Receiver1.2.133 build138 prepared: native sideways swipes end on the existing wrist-stop detection; only the exit-follow click waits300ms and double/triple cancel it. Agentic Mouse313 is installed with Utility Select all→Backspace→Copy, higher HUD sensitivity and dragging-direction Spaces. Complete Sense6 firmware and wireless host updater prepared; physical USB/BLE acceptance pending.
- Prepared, not installed: the Sense wireless application updater has checked USB provisioning, exact-board update requests, bounded handoff, post-update confirmation and explicit result acknowledgement. Host tests use fake Bluetooth; real wireless transfer, interruption recovery and power-cycle acceptance still need hardware checks. Current pointer and scroll controls are unchanged.
- Receiver 1.2.132 build137 installed and reconnected over Bluetooth: gentler low-speed page input, retained boost from repeated page flicks, scrolling fallback for custom app surfaces, bounded app/role diagnostics, and immediate exit-follow click. Physical WhatsApp acceptance remains unverified; native horizontal stop-ending is a separate follow-up.
- Installed receiver 1.2.131 build 136 restores ordinary wheel events for vertical and diagonal page scrolling and doubles the fast-end maximum to 1,200 lines per second. Pure horizontal held swipes retain native history gestures and the stronger 135 curve. Installed source, resources, settings and Bluetooth readiness were verified. Initial physical feedback reports stronger page scrolling but too much speed at the low end and a drop after repeated flicks; further tuning is in progress.
- Receiver 1.2.130 build 135 increases deliberate horizontal swipes to five times the previous 134 strength after physical feedback. Vertical and diagonal scrolling, fine pointing, clicks and follow restoration are unchanged. Native receiving apps still decide scroll or history navigation. The stronger setting needs physical confirmation.
- Receiver 1.2.129 build 134 increases horizontal-only native swipe distance, easing in up to 2.5 times the shared rate. Ordinary vertical and diagonal scrolling, pointer tuning, click timing and follow restoration are unchanged. Native phases still let the receiving app decide scrolling or history navigation. Physical Back/Forward acceptance remains unverified.
- Installed receiver 1.2.128 build 133 and Agentic Mouse 1.0.306 build 312: current controls now use HUD button, mouse button and speech button, retaining wire aliases and marked older tutorial recordings. The wand HUD selection outline now moves continuously between the centre, ring and outer cards, with input timing unchanged. Green HUD light, the original normal scroll feel and stronger high-speed scroll range are preserved. Signed installation, source/resources and Bluetooth readiness were verified; physical animation feel remains for confirmation.
- Installed receiver 1.2.127 build 132: the active HUD light is green, including when mouse follow is also on. Existing loading, scrolling and review colors remain. Device simulation verifies the light priorities, and the installed resources and connection were checked. The corrected high-speed-only scrolling is preserved; physical light-color acceptance remains pending.
- Installed receiver 1.2.126 build 131 adds a high-speed-only V3 scroll extension. The entire original speed curve is retained through 120 angular units/s, including its 120-line/s plateau; only stronger strokes rise smoothly toward 600 lines/s. Every tested ordinary sample and tick matches the original, and strong-stroke, direction, release and lost-telemetry checks pass. Installed binary, resources and connection were verified; fresh physical feel remains for confirmation.
- Installed receiver 1.2.125 build 130 restores the original V3 scroll-speed curve after physical feedback that 129 altered the normal feel. The boost began before the old cap and could affect ordinary strokes. Follow-state restoration, native scrolling and all pointer settings remain. A revised high-speed-only extension is still being prepared; it is not installed.
- Installed receiver 1.2.124 build 129: ordinary V3 scrolling retains its fine and normal speed and increases the strong-stroke maximum from 120 to 600 lines per second. Motion-profile checks cover ordinary speed, stronger strokes, reversals, released buttons and lost telemetry. Installed binary, signature, resources and Bluetooth readiness were verified. Pointer tuning and click behavior are unchanged; physical scrolling acceptance remains pending.
- Installed receiver 1.2.123 build 128: a completed page scroll restores the mouse-follow choice from before scrolling. Off stays off; on stays on. Held-scroll and chord release checks passed. Installed source and signature, Bluetooth readiness, calibration, settings and Agent Flow were checked; physical follow-state acceptance remains pending.
- Installed receiver 1.2.122 build 127: held and chord scrolling send native precise two-axis scroll gestures. Applications own scroll-container and edge-navigation decisions. Release, pause, disconnect, drag takeover and shutdown end or cancel the gesture; a delayed short tap cancels it, and a two-button chord retains ownership until its own release marker. Native event and lifecycle checks pass. Existing sustained-hold behavior and pointer tuning are unchanged. Chrome and Codex history acceptance still needs a physical test.
- Installed Agentic Mouse 1.0.305 build 311: New Codex chat replaces Screenshot at the same home-ring position, with no duplicate outer card. Native screenshot triple-click and the physical mouse layouts remain unchanged. Zoom keeps its existing outer position. Signed installed source, settings and rendered layout checks passed; physical activation remains to be tried.
- Installed receiver 1.2.120 build 125: review circles retain their learned size across pauses and about-faces, so a tiny wobble cannot become a new reverse gesture. A near-complete smaller circle can establish a smaller size; the first loop after a dramatic size reduction may only relearn it. Private slow recordings and synthetic pause, noise, reversal and size-change checks pass. Installed executable, source, resources and settings were verified. The receiver reconnected ready over Bluetooth after waking; fresh physical acceptance remains pending. Pointer smoothing, quiet stopping, gain, clicks and saved firmware are unchanged.
- Installed Agentic Mouse 1.0.304 build 310 uses wider two-line review pills, a centred dot between hints, and the labels Hold to stage selection and Double-click for Stage files mode. Rendered review, stage, creating-chat and repeat-hint variants pass; fresh physical acceptance remains separate. Installed native signature, source and settings checks passed; 1,190 native tests passed with four optional tests skipped.
- Installed receiver 1.2.119 build 124: review circles retain slow motion above the calibrated sensor-noise floor rather than the larger HUD speed floor. Direction and startup-noise checks prevent false turns. Closed-HUD double-click right-click remains installed from build 123. Pointer quiet stopping, smoothing, sensitivity and physical mouse behavior are unchanged. Fresh physical acceptance is pending. All 229 Wand tests and 17 Control Stones checks passed; the installed receiver is ready over Bluetooth with settings and calibration preserved.
- Installed receiver 1.2.117 build 122 restores raw input during the initial Bottom-held stroke, before the existing tap/hold decision. Active Bottom scrolling is routed before the HUD-only input filter. An open unheld HUD permits follow-on stop-to-click, while an actively held HUD control owns that gesture. All 228 Wand checks passed; the installed source and executable were verified, and Ethan confirmed both normal held scrolling and HUD-open clicking work. Other gesture acceptance is separate.
- Installed receiver 1.2.116 build 121 restores quiet stopping by disabling the newer sub-threshold fine-motion bypass. The existing roughly 8 ms smoothing, speed-based sensitivity, orientation correction, held precision and single-shot click signal are unchanged. Pure-motion regression checks pass; fresh physical stillness acceptance is pending.
- Installed: receiver 1.2.115 build 120 and Agentic Mouse 1.0.303 build 309. Ordinary HUD actions keep the HUD open, so you can select as many times as you want; a double click closes it, and every open page’s centre says “Double click to close”. The wand home ring is grouped: Keys, the app card and Utility at the top, with Back beside Forward. Space moves beyond Enter, New Codex chat sits beyond Utility, and Zoom is a third layer beyond it. Adjustment arrows follow each card’s real direction, including left and right for Spaces. The centre-and-left click added in build 119 is removed. Native and receiver checks pass; physical acceptance is pending.
- Installed receiver 1.2.109 build 114 removes circular continuation from Switch App: held app choosing now follows normal horizontal movement and reverses directly. Double-click centring resets the pointer lane and synchronises the centre with queued native input; its focused regression checks pass, while physical centring acceptance remains pending. The receiver reconnected ready over Bluetooth, with settings, calibration, saved Sense firmware and Agent Flow preserved. The larger outer labels are prepared separately in the native HUD update.
- Fine-motion bypass superseded by receiver 121: Installed receiver 1.2.108 build 113 and Agentic Mouse 1.0.299 build 305 restore the old click signal, the speed-based aiming curve and coherent tiny movement above about 1 deg/s. Only tiny slow movement uses the approved up-to-60 ms confirmation; normal pointing retains roughly 8 ms smoothing. Short Bottom taps use their physical duration. The wand HUD has related outer actions and the held Switch App exception. Local tests and installed signature, version, settings and process checks passed. The saved Sense firmware and current gain are preserved. The native app's launch safety check has cleared. The receiver is ready over Bluetooth, live HUD and held Switch App lifecycle reports were observed, and Ethan reports the installed wand is working well. This is general physical acceptance, not a claim that every gesture has been tested.
- Installed receiver 1.2.106 build 111 restores mouse follow after a completed scroll is released, even if it was off before. Current pointing, scroll detection, button-release safety and menu fixes remain. Full local checks pass; the receiver reconnected ready over Bluetooth with settings preserved. Real user scroll-release events were observed enabling mouse follow again.
- Installed receiver 1.2.105 build 110 keeps connection heartbeats, stop-to-click, button safety and gesture deadlines running while menus are open. Sense orientation correction rejects unreliable gravity readings during jerks, twists and near-vertical poses. The existing roughly 8 ms smoothing, quiet stopping and no historical replay remain. Local checks passed. Live menu and physical pointing checks remain pending; faster firmware e still needs USB.
- Installed Agentic Mouse 1.0.298 build 304 passed the full native checks, but Ethan subsequently reported intermittent HUD opening and mouse-exit failures and changed Switch App behaviour. Current diagnostics have been captured; the cause and fixes are not yet verified. A ready process or socket alone does not establish working button input.
- Installed: Review changes and Stage files switch within the same pending Better Git selection and include the current file. No files are staged by switching. Better Git 1.2.135 is released and active; receiver 1.2.96 is installed with settings preserved. Receiver and Mini checks pass. The device remained asleep during installation; physical gesture acceptance remains pending.
- Installed: double-click Middle toggles Review changes and Stage files without staging. The floating indicator names the other mode. A single click cancels and exits after at most 300 ms; holding for half a second still stages the selection and stays in that mode. Pointer movement is unchanged. Receiver, native interaction and timer checks pass; physical button acceptance remains pending.
- Installed: triple Bottom starts screenshot selection; the HUD Screenshot action uses one Bottom tap, movement and the existing stop-to-click detector to finish. Double-tap centering waits up to 300 ms to distinguish a third tap. Pointer movement is not buffered. Recording red takes priority over mouse blue, and loading blinks orange. Complete saved bytes and clean startup with calibration passed; physical screenshot acceptance remains pending. Superseded: hold Bottom to select the area and release to capture.
- Installed: each circular Wand HUD wedge has its own masked glass backing, clearer text and a gentle selection lift. Gaps and space around the wheel stay transparent. The armed dotted outline moves; Reduce Motion keeps it static. Native rendering and interaction checks passed; physical Copy/Paste acceptance remains pending.
- Installed: the Review changes and Stage files indicators say “Hold to commit selection”. Selection is the current term for the pending group; holding stages it without making a Git commit. Native tests and both rendered indicators passed.
- Installed: all three grip buttons turn the wand off; any single grip button wakes manual or automatic sleep. The wake press is consumed until every button is released. Five-minute automatic deep sleep and the two-blink cue are unchanged. Saved bytes and clean startup verified; physical any-button wake acceptance pending.
- Installed: shared click and hold cues distinguish a card action from held wheel or wand adjustments. Copy/Paste names Space explicitly. Native checks and rendered layout inspection passed; physical gesture acceptance is pending. Superseded on the wand: Space is its own outer card beyond Enter.
- Installed: held Switch App adjustment shares the normal HIGH mouse sensitivity calculation, including fine movement and orientation correction. Other HUD controls keep their existing angular input. Native and receiver checks pass; physical feel is awaiting acceptance.
- Installed: the complete saved program includes the corrected Bottom press, calibration restore and button-wake sleep. Clean startup was verified before reconnecting the receiver, with no code re-upload. A full five-minute sleep/button-wake cycle was observed on 24 October; physical battery-removal remains unverified.
- Installed: radial text is larger, with gentle card-aligned tilt only when it earns more readable space. The visible wand HUD stays anchored while Agent Flow changes its panel; reopening refreshes recorder clearance. Native tests and rendered layout checks passed; physical acceptance is pending.
- Installed: larger mixed-case radial labels, a continuous liquid centre-to-ring transition, and ordinary Enter in the wand home HUD. Native layout, morph continuity and key-output checks passed; real-device feel remains for user acceptance.
- Installed: the wand HUD is a radial wheel with Switch App in the centre and the other available actions around it. Native checks and installed visual inspection passed; physical selection feel still needs acceptance.
- Installed: Bottom hold scrolls a scrolling surface or drags a confirmed draggable target. Unknown or late target results stay on the scrolling path. Native lifecycle checks passed; physical app coverage is pending.
- Installed: waking restores the mouse-follow choice from before rest. Manual choices and recording pauses take precedence. Native checks passed; physical acceptance is pending.
- Control V3 replaces circular page scrolling with straight-drag velocity: continue while held still and reverse with another stroke. Automated lifecycle checks pass; physical acceptance is pending.
- Installed: Wand Receiver 1.2.79 emits plain single-button clicks with no modifier flags. Ordinary clicks cannot accumulate an OS double-click count. Synthetic event checks pass; the reported Codex new-window symptom still needs a physical check.
- Review navigation uses a redesigned spatial corner detector with learned noise tolerance. Reversible quarters, rough squares, slow motion and simulated device traces pass automated checks; physical acceptance is pending.
- A minute of confirmed desk rest turns the lights off and keeps low-rate pickup sensing. Pickup or a button restores the light. Rest never stops dictation or dismisses the open HUD.
- Receiver reconnection now rejects echoed upload requests and failed-runtime ready markers. Updating, disconnected and calibration bridge states use orange; recording alone uses red.
- Wand-only VS Code shortcuts expose change review and file staging beside Switch App. Automated checks cover their input; physical acceptance is pending. Superseded: they sit beyond the app card in the outer layer.
- HIGH stop-to-click uses a 200 ms rest interval. Automated timing checks passed; physical acceptance is pending.
- Wand Receiver has a menu-bar Options menu. Optional first-flick scrolling in V1 passes automated checks; physical gesture acceptance is pending.
- Shared orientation correction and full Middle double-tap dismissal pass automated checks; physical acceptance is pending.
- Held scrolling now stays locked until release; Bottom double tap recenters the pointer. Automated checks passed; these changes still need a physical check.
- Ethan confirmed the latest native pointing feels much smoother; the other experimental gestures still need a physical check.
- Held positioning clicks on release and resumes prior high sensitivity after 300 ms. Ethan confirmed the still-hand tolerance feels good.
- Ethan confirmed automatic pickup and put-down both work on receiver 1.2.35.
- HIGH dwell, held rough circles and VS Code review pass automated checks; physical acceptance is pending.
- End-to-end latency, accuracy and battery life haven’t been measured.

Receiver 1.2.153 (158) · device code `wand-7e734a872bfe` · bridge `ec5338c6` · updated 31 October 2026.
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
| [`docs/`](../docs) | The GitHub Pages website; `docs/sim/` holds the in-browser simulation |
| [`data/`](data) | Synced Agentic Mouse HUD labels, the import lock and the vendored-file lock |
| [`tests/`](tests) | Device, simulation, manifest and website checks |

## Run the checks

Requires Python 3.10+ and Node.js 22+; there are no npm dependencies.

```sh
python3 scripts/build.py --check   # generated files match wand.json and the sources
python3 scripts/vendor.py --check  # Three.js and fonts match their lock
python3 scripts/check.py           # website checks only
node --test tests/*.test.*          # device code, receiver and HUD ports, manifest, site
npm --prefix .. run check          # repository-wide checks, including privacy
npm run serve
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
[Control Stones](../control-stones/README.md) contains the Sense hand-controller component and live sensor debug window.

## How-to videos

The [How To gallery](https://ethansk.github.io/magic-wand/how-to/) has twelve short narrated
guides, with captions, transcripts and links to individual actions. These are illustrations of
Control V2, not physical test recordings. [Tutorial maintenance](tutorials/README.md) explains
question lookup and the reproducible render pipeline.

<!-- Previously the repository root; this component and its source paths now live under magic-wand/. Published docs remain at ../docs/. -->
