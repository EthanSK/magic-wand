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

## Circular scrolling without an input buffer

Candidate circle motion passes through immediately. Only a deliberate closed, consistently turning
loop consumes pointer reports and becomes native wheel lines. Apply it only to released-button
HIGH follow; physical Bottom edge reports also exclude LOW, whose mouse-button mask is zero.
The Puck retains its accepted motion filter and sample rate; the Mac classifies existing reports.
Native and JavaScript traces match for both directions. Tests reject incomplete curves, small
noise and sharp rectangular lassos; pausing, a radial exit or a button restores pointing.
This is regression evidence, not physical acceptance or a measured latency improvement.
