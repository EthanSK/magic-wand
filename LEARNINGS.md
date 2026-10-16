# Verified lessons

## The public sources reproduce the installed wand exactly

The runtime version is `wand-` plus the first 12 hex digits of the SHA-256 of the device program
from its `// Adjust only` line; the bridge revision is the SHA-256 of the compacted bridge. With the
original statement splitter and compactor, the imported sources reproduced the private upload
commands, runtime, boot image and bridge byte for byte (16 October 2026). Keep those algorithms in
`scripts/device_build.py` unchanged unless the receiver changes with them: the receiver compares
both identifiers on every connection. `tests/manifest.test.mjs` recomputes them.

## Running Espruino code outside the Puck

The bridge patches the live device with `Function.replaceWith` and finds its targets through
`E.internal.watches`, `Puck['#onaccel']` and `NRF['#onconnect']`, matching callbacks by their source
text. A host must expose those lookups and give every top-level device function a forwarder whose
`replaceWith` swaps the target and whose `toString` returns the target’s source. Replacing a global
name is not enough: the pin watch still holds the old function. The test sets a stale global
`onMoveButton` to prove the bridge patches the watched callback.

Values created inside a Node `vm` context have that context’s prototypes, so
`assert.deepStrictEqual` rejects an equal array from it; copy with `Array.from` first.

The bridge keeps the gyro on for one second after a gesture. A test that expects the sensor off
must advance past that grace; the base program alone switches it off immediately.

## Aim to gyro in the demo

The page only posts the visitor’s aim while it changes. Deriving a rate from a long-stale sample
spreads the next movement back across the pause and loses most of it. The worker anchors the
previous aim just before each new one after a pause, then averages the rate over 50 ms.

## Three.js versions

The three@0.186.1 npm package has no `build/*.min.js`, and the GitHub `r186` tag has none either.
three@0.185.1 includes them, and its files are byte-identical to the copies Agentic Mouse vendors,
so the site pins 0.185.1.

## Hidden recording indicator

An explicit flex display overrides the browser’s default hidden-attribute style. The recording
chip needs its own `[hidden] { display: none; }` rule, like the HUD and fallback wand. Check the
rendered idle state as well as the hidden property: the simulation can be correct while the
recording light is still drawn.

## Held pointer precision

Apply held sensitivity to the existing pointer scale before fractional counts are accumulated.
Scaling integer reports instead drops small movements. The pointer path runs after the HUD and
scroll branches, so a held Bottom gain leaves their angular navigation and wheel gains alone.
The gesture tests compare both pointer axes across temporary entry, clutch and real dragging at
fine, medium, fast and reverse speeds; released-button follow retains its original gain.

## HIGH and LOW pointer gestures

HIGH is released-button follow; LOW is a plain Bottom hold for one-third-speed positioning,
not a left-button drag. LOW release clicks at the endpoint. If HIGH preceded the hold, suppress
pointer motion for 300 ms, then continue HIGH. From off, LOW release returns to off. The
pause is a pointer-path deadline rather than a resume timer, so it cannot reopen a mode after
the user switches to the HUD or exits. Tap-then-hold remains the distinct real drag; dropping resumes prior HIGH after the same pause.

## Loading a larger motion callback

Replacing the motion callback in one statement ran the actual Puck out of memory while both
old and new bodies existed. First replace its body with a tiny function retaining the
`var g=a.gyro` discovery marker, then load the tested replacement. Function.replaceWith keeps
the callback object and scope, including calibration. A separate pure angular-slack helper
also keeps the largest statement small. The final staged upload completed without OUT OF MEMORY;
an idle device health query after the upload returned no error flags. A ready marker alone
had appeared after earlier partial failures, so verify the actual callback marker and settings.

## Angular tolerance and residual drift

The pointer uses radial displacement tolerance instead of stacking another rate dead zone.
Re-centre quiet rates even when the anchor is at the circle edge; otherwise leftover bias can
keep pushing after a deliberate sweep. Tests cover drift from rest and after motion, fine
aim, both sensitivity modes, diagonals, curves and the 300 ms release pause. This is
simulated-noise coverage; Ethan confirmed the noise rejection feels good on 16 October 2026; this does not establish an optimal hand-noise threshold.

The release pause was shortened from one second to 300 ms after physical feedback that the wait felt too long. Preserve the accepted angular tolerance and gain curve while tuning only this pause. Actual dragging releases the native left button, then restores prior HIGH after the same pause; it must not send an extra endpoint click.

## Bound event targets to real displays

Clamp both the current event location and its proposed target to actual CGDisplayBounds before
posting relative motion. Sending an unbounded target can leave invisible excess beyond an edge,
so reversing feels stuck. Clamp to the nearest real display rectangle rather than a union bounding
box, which includes gaps between staggered monitors. Native tests cover repeated outward motion,
immediate reversal, negative coordinates, gaps and recovery of an old offscreen location.

## Preserve tap entry and held entry separately

Middle's opening press is delayed 80 ms on the device to allow the scroll chord. The receiver
therefore measures the 220 ms physical hold against the remaining 140 ms. A short entry release
leaves the HUD latched; a held entry parks navigation, presses and releases the selected card,
then resumes navigation. Clear the pending entry when a chord begins. Existing open-HUD holds
still operate the card instead of navigating. Native routing and demo pipeline tests cover both.

## Held circles and release-jolt buffering

Rough loops belong only to a plain Bottom LOW hold. HIGH, real left-button dragging, HUD navigation
and the two-button scroll chord are excluded. Direction-of-travel turning recognises ovals and radius
drift without requiring exact closure. Two-count heading segments, 0.6 net-turn consistency and a
1.5-radian corner limit passed independent rough and integer-quantised traces in both directions;
these are tested starting values, not physical optimums. Two low-turn windows avoid flickering on
an oval's flatter side; a sustained straight run still exits promptly.

LOW pointing became immediate in receiver 1.2.24 after Ethan rejected the earlier 90 ms
release-jolt buffer. He explicitly approved restoring it only for held LOW aiming in 1.2.26; waiting for stillness before a click does not require delaying visible
motion. The installed receiver now uses that held-only 90 ms buffer. HIGH and real dragging remain immediate. The ordered UART Bottom-up
edge precedes its synchronous endpoint click; consume that pair after a recognised scrolling hold,
then disarm on the next physical press. Carry a locally clamped point through a native drain batch
because posted CGEvents need not update the system cursor synchronously.

## HIGH dwell and desk inference

HIGH clicks once after meaningful travel and 450 ms without a pointer report. Entry, continued
stillness and small sub-threshold motion never re-arm the click. Reset on every control, recording
or mode edge. A short Bottom tap now exits HIGH without clicking.

The Puck's raw accelerometer divisor is 8192 per g; gyro is 134 per degree/second. On the desk,
Puck.accelOn(1.6) disables the gyro. Cap active IMU telemetry at 10 Hz while keeping the accepted
104 Hz pointer request. Learn a rest pose only while idle; confirm pickup over multiple samples;
require return/contact followed by quiet accelerometer variation and gyro rate before set-down.
Require three further quiet seconds before sending one ordinary Top tap during Agent Flow
recording, and cancel on pickup or any control. A still supported hand remains an unavoidable
ambiguity without a contact sensor. These checks are simulated evidence, not physical acceptance.

## Reuse app-specific staging transactions

Keep app identity and HUD ownership in Agentic Mouse. The receiver learns `vsCode` from its same-user context lease and adapts Bottom’s vertical angular travel to existing Better Git review requests. Do not fabricate Corsair input, change physical mouse mappings or maintain a second staging algorithm. Green identifies app review; purple identifies file staging; both yield to the scroll chord.

VS Code URI delivery can reorder callbacks. Tag every gesture with a fresh identifier and ordered sequence; buffer gaps before finishing, retire completed identifiers, and cancel on lost focus or a missing heartbeat. Four native Mini cases exercised changes/files in both directions, deliberately delivered finish before a missing heartbeat, checked the exact Git index and verified Undo. The signed Agentic Mouse and Marketplace Better Git installs were verified separately from physical gesture acceptance.

## Reconnect must re-enable idle pickup sensing

Disconnect turns the sensor off while retaining a valid calibration. On reconnect, `sleepGyro` must explicitly restore the 1.6 Hz accelerometer even when `gyroAwake` is already false. Returning early in that state leaves automatic pickup blind until the first button press. Device tests cover readable and fragmented bridges, reconnect, retained bias and the idle sensor rate. The correction was applied through the current UART owner without another reconnect.

## Slow intentional movement and dwell

Keep a short directional-evidence window separate from the radial pointer tolerance. The previous 350 ms recentering erased a steady 0.5 degree/s turn indefinitely. The new bounded scalar window passes that trace at both 35 and 104 Hz while retaining the existing 0.3-degree/s-per-axis drift test. This threshold cannot identify arbitrarily slow movement separately from sensor bias.

Use the existing IMU heartbeat for the moving/resting hint. Quiet heartbeats must not keep resetting the dwell timer: only the moving-to-rest transition starts the rest delay. A missed heartbeat expires rather than suppressing clicks forever. Keep the accepted pointer gains unchanged. The LOW release-jolt buffer was disabled in 1.2.24, then restored with explicit held-only approval in 1.2.26.

Free the old motion callback before allocating replacement filter code. Adding helpers before releasing that body exhausted the physical Puck's memory even though host tests passed. Keep the filter state to five scalar values and use the existing telemetry message. A successful ready marker alone does not prove a complete upload; read back the actual filter and motion callback and inspect fresh error flags.

## A partial live patch must not look ready

A successful final print is not proof that every preceding REPL statement installed: FIFO_FULL
and OUT OF MEMORY can leave the motion callback at its temporary no-op while button watches
still respond. Load the complete compact bridge through the receiver's statement loader instead
of a multi-kilobyte ad-hoc maintenance command. Retain the previous bundle and bridge for recovery.
Validate the callback's expected motion marker and reject a later ready marker after an actual
interpreter failure. Keep orange until validated completion; do not use a five-second timer.

At 208 Hz, test helpers that simulate a duration must derive their sample count from the selected
rate. A hard-coded 104 sample count halves simulated elapsed time and falsely fails the unchanged
300 ms release pause. Retain fixed-rate traces separately to compare outputs at equal times.
