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

HIGH clicks once after meaningful travel and 200 ms after confirmed rest. Entry, continued
stillness and small sub-threshold motion never re-arm the click. Reset on every control, recording
or mode edge. A short Bottom tap now exits HIGH without clicking.

The shorter rest interval changes only click timing, not motion filtering. Preserve the
bounded intent lease so ongoing subpixel movement cannot click early; quiet heartbeats
must not postpone a confirmed stop. Native and browser tests cover the 200 ms boundary,
resumed movement, no repeat at rest, and no click on mode entry or exit.

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


## Keep HID limits out of UART movement

The HID mouse fallback needs its byte-sized 127-count cap; the UART text protocol does not.
The accumulator, pump and native parser must agree on the wider bound, or fast sweeps are
silently discarded. Keep exact filter-state equivalence tests below the old cap and separate
wide-travel tests above it, including display clamping and invalid-packet rejection.

Do not call dt/(tau+dt) equivalent to 1-exp(-dt/tau): it changes filter response and can add lag.
Private scalar state, cached lookups and gating an already rate-limited telemetry helper retain
the original equations; changing those equations needs separate validation and delay approval.

## Move expensive pointing math off the interpreter

The 104 Hz chip setting did not imply 104 completed callbacks: the previous live
run delivered 960 callbacks over 41.216 seconds (about 23.3/s). Cached lookups alone
did not resolve the rough physical feel. Native `@RAW` handling therefore keeps
the accepted exponential filter, directional evidence, slack and gains while the
Puck sends calibrated-axis configuration and raw samples. Retain the fallback
filter for other hosts; do not enable raw mode until the receiver is ready.

Keep a single clamped cursor point across all lines in one Bluetooth delivery.
Consecutive CGEvent posts need not be reflected in a fresh cursor query immediately;
re-querying between frames can overwrite travel from the same delivery. Reset that
point at the next delivery so physical mouse movement remains respected.

Ethan reversed the held-only 90 ms experiment again: LOW now defaults to zero
buffer, with a click at release and the existing 300 ms post-click pause intact.
Do not re-enable a movement buffer from an earlier approval.

The statement compactor splits on top-level semicolons, not on closing braces.
Put an explicit semicolon after a conditional block that frees old functions
before a following replacement function literal. Otherwise both remain one REPL
statement: Espruino must allocate the replacement before executing the free,
which can produce OUT OF MEMORY or an EOF parse error. The native upload test
checks that freeing and replacement occupy different generated statements.

Native pointing delivered about 49–51 samples per second in repeated five-second
active windows, versus the prior 23.3/s. Ethan confirmed it felt much smoother.
A brief 208 Hz trial stayed around the same delivered rate; retain 104 Hz rather
than spending power on a higher setting that does not improve actual throughput.
Reset the connection deadline when a new load starts so recovery gets its full
time budget instead of inheriting an almost-expired connection attempt.

## Experimental wrist-roll compensation

Native mouse pointing can opt into `orientationCompensation` in the receiver's
local `feature-flags.json`. Absence or false preserves the original fixed axes.
Refresh the flag outside the raw-motion path; gravity observations reuse the
existing 10 Hz IMU telemetry, without adding packets or a pointer buffer.

For the current mount (shaft along sensor Y, neutral face-up along Z), normalize
gravity's X/Z projection and rotate the bias-corrected angular rates before the
existing filter and gain. This preserves the screen's vertical gain and LOW gain.
Horizontal heading projects onto the shaft-perpendicular axes with a cosine
loss as the tip rises. Correct by length(gravity)/length(projected gravity),
capped at 2x, before the nonlinear speed curve; correcting final pixels leaves
the acceleration curve using the wrong speed. Vertical 1.4x and held 1/3 gains
remain screen-space values applied afterward. The expanded test covers 1,296
roll/elevation/speed/direction/held combinations, nonzero bias, flag-off equivalence,
stationary input, invalid acceleration and the near-vertical fallback. It does
not prove physical acceptance or arbitrary three-dimensional tracking. Retain
the last usable basis during obvious acceleration shocks or when the shaft is
nearly vertical. Pointer, HUD navigation, held card operations, review and chord scrolling
share this basis. UART navigation and scrolling contain cumulative angular coordinates:
transform each new increment, not the entire historical total, or changing wrist angle
rotates old travel and jumps the selection. Undo transport signs and horizontal scroll
boost before projection, then restore those screen-space settings afterward.

## Closing a wand HUD is a session boundary

A hidden panel must not retain navigation, an app-specific mode, a delayed card click or
a held action. Use one complete close path for Middle double-click, pointer takeover,
context loss and navigation timeout. The old timeout dismissed the panel but retained
the receiver session, while the old double-click path entered app-specific mode.
Reject positive context heartbeats after explicit close until a fresh Middle press:
a queued heartbeat is not permission to reopen the HUD. Native tests compile the actual
receiver methods against inert transports and verify complete close, late-input rejection,
delayed-click cancellation and deliberate reopening. The reported extra Codex window
has not been reproduced by those synthetic tests; its exact trigger remains unproven.

## Detect rest at the sleeping sensor rate

The physical resting wand reported about 1.055 g and several milli-g of variation.
The old fixed 0.97–1.03 g gate and 0.004 g anchor tolerance rejected those readings.
Allow the measured sensor bias and compare pickup magnitude with the learned rest
magnitude. Quiet evidence still requires low rotation and a stable anchor.

Use four observations spanning 1.8 seconds for rest confirmation, including at
1.6 Hz. Eighteen observations took over ten seconds in low-power mode. Persist
only the confirmed gravity reference; re-evaluate current state and timestamps
after reconnect. Manual mouse activation must rearm return-to-reference detection.
Learning an idle reference during recording does not itself stop the recording.

## Confirm rest from a window, at any placement angle

The active gyro stream adds accelerometer noise that did not appear at the slow
idle rate: a still device produced isolated changes above the old 0.012 g anchor
threshold and gyro samples above 0.3 degrees per second. Do not reset all quiet
evidence for one such reading. Judge scatter, sustained drift and RMS rotation
over an elapsed-time window. A new desk angle need not match a saved gravity
vector or include a detectable impact. Regression fixtures include actual
stationary active-rate samples. This classification window never buffers pointer
movement. An IMU alone cannot distinguish a perfectly supported hand from a desk.

## Keep pointer-ordering hypotheses separate from physical symptoms

A source-level asynchronous-position race and a synthetic passing regression are
not proof of the cause of a reported stop/restart jump. A persistent posted-point
reconciliation experiment passed its pure tests but Ethan reported worse feel,
so it was reverted. A subsequent live trace showed occasional stale position
reads across closely spaced notifications, but the observed automatic clicks
stayed at the current position. Do not claim those reads caused the reported
symptom, or re-enable that experiment as an accepted fix. Retain the working
receiver until a new physical reproduction supports a narrower change.


## Retain a held scroll through a pause

Once LOW circular scrolling is recognized, pause expiry and straight-motion
heuristics must not return the same held gesture to pointer movement. Forget
stale headings on pause so resuming cannot invent a large turn, but retain the
scroll latch until release or explicit mode cancellation. Native and simulation
regressions cover the pause, long straight motion, release and suppressed endpoint
click. Pin wheel-event locations for both circle and chord gestures to their
captured target. Physical feel remains a separate acceptance check.

Bottom double-tap recentering is recognized only on a short second release;
a held second press remains the existing drag. Recenter the pointer on the main
display without changing sensor calibration, and reset dwell evidence so the
warp cannot cause an automatic click.


## Pace code uploads after the GATT acknowledgement

A GATT write acknowledgement does not mean Espruino has parsed the received
JavaScript. The device reported FIFO_FULL during a bridge upload, followed by
undefined local variables in partially received functions. The receive stream also carried XOFF/XON control bytes. Honor XOFF by pausing
queued writes until XON; a fixed delay alone is insufficient while a function
is parsed. Pace write chunks by 10 ms while the receiver is not ready. Retain immediate dispatch after it
is ready; this delay applies to installation, not pointer samples or gestures.
Recover through the existing Bluetooth owner and preserve a successful sensor
zero. Source tests cannot reproduce the device's UART input capacity.


## First-flick scrolling is an explicit option

Classify the shared, rotation-corrected angular rates, before pointer sensitivity or pixel rounding.
A sharp upward cue with enough angular travel arms one slow downward return; the return posts
positive native wheel lines (scroll up). Do not wait for repeated cycles. While capturing the
gesture, keep the pointer at the original target and suppress the HIGH dwell click. Cancel on
button input, HUD entry, pointer exit, option-off, sideways movement or an excessive return speed.
This is a gesture classifier, not a movement buffer; ordinary pointing remains unchanged with
it off. A single brief spike or slow pointing alone must not start scrolling.

The Options menu and file refresh must share one flag store and preserve unrelated keys.
Recording uses steady red only when no higher-priority mode is active. Mouse mode stays blue.
Clear a legacy recording blink timer when replacing the bridge; do not recreate it.


## Control V2 preserves short taps and separates explicit dragging

Control versions are distinct from hardware prototypes. V1 retains the prior exact source tag
and local installed snapshot; V2 changes Bottom holds while keeping its short taps. The
existing 220 ms tap/hold cutoff separates these paths. Never let the firmware's legacy hold
click or drag reports leak into the native V2 path. A raw zero-button frame between release
and the queued firmware click must not clear suppression; wait for that click's down/up.

The original V2 used Accessibility to choose between scroll and native drag. Ethan
replaced that behavior on 19 October: a plain hold must always scroll, including over
text or controls that do not expose a scroll area. Remove the hit-test fallback;
its negative result could turn intended scrolling into unwanted text selection.
Capture only the pointer position for wheel delivery and keep it fixed until release.

The existing double-tap recognizer identifies a second press within 300 ms. A second
press held beyond the existing 220 ms cutoff selects native dragging; a short second
release still recentres. Keep that intent separate from the text or window below the
pointer. Physical-up reconciliation and the telemetry watchdog must release either
path. Native handler tests cover a plain hold, a tap-then-hold drag, release, and a
later plain hold returning to scroll. No new pointer buffering is involved.


Control V2 hold scrolling uses positive angular Y for native wheel lines, so page content
follows the wand like touch dragging. Keep this sign local to V2; V1, wheel chords and
physical-mouse scroll settings retain their existing direction.


## End held input from physical state, not only its release edge

The V2 host previously depended on one `@BOTTOM 0` edge and put its teardown behind
current app/chord conditions. A missed edge could leave host-held scrolling or dragging
active even when raw samples reported the physical button up. End a hold unconditionally
on its release edge, and reconcile against physical bits in raw motion and the existing
IMU heartbeat. Discard a recovered release sample before movement and clear the target.
Renew a held-input lease only from actual button samples; if they disappear, release the
native drag and stop scrolling. Late telemetry alone must not start the hold again.
Tests drop the explicit release and exercise the actual raw handler, plus native drag
teardown and lease expiry. This proves the failure path, not the original physical cause.


## Bottom double tap is a global pointer escape

Recognise physical Bottom double taps before app-specific, HUD, scrolling or native-button
gates. Mode cleanup between the two taps must not erase the recogniser. A short second
release closes the full HUD and review session, cancels scrolling and native drags, clears
held pointer state, centres on the main display and explicitly enables mouse follow on
both host and device. Discard queued old click reports until the next physical Bottom
press. Keep long second presses as holds. Connection resets still clear the recogniser.


## Continue vertical scrolling with either circle direction

Control V2 recognises a bend in rotation-corrected angular movement after a vertical
start. Map the first U-turn winding to the meaningful starting vertical direction.
Later consistent opposite winding reverses scrolling without releasing; choosing the
initial U-turn side alone must not reverse it. As soon as the initial direction is known,
integrate two-axis angular distance with that sign before and after recognition,
so sideways arcs scroll and the returning half of a loop does not reverse the page.
A pause retains continuation only for the same physical hold. Release, mode cancellation
and lost button telemetry clear it through the existing held-input lifecycle.
Use angular rates before pointer sensitivity, ignore still-hand noise and retain the
captured wheel target. Native traces cover both starts and windings, uneven speed,
sideways arcs, pauses, release and deliberate winding reversals. Physical feel remains unverified.

For winding changes, ignore tangent cusps and require at least three opposite heading
segments accumulating 30 degrees. Matching-direction segments clear the reversal
evidence; stale evidence expires. This is shape evidence, not a pointer or wheel buffer.
Tests cover repeated reversals, both initial sides and vertical directions, uneven
speed, oval shapes and alternating wobbles.

A flat-bottomed or paused U reproduced a wrong-way wheel event before full circle
recognition: the candidate path still used signed vertical movement. Never pass that
returning-leg sign through after acquiring the starting direction. The same arc-length
gain now spans candidate and confirmed states; constant-speed bins verify no gain step.
The old implementation fails the paused/flat U regression, and the corrected one passes.


## Finish page scrolling in mouse follow

A physical release ending a qualified scroll hold or the two-button page-scroll chord
explicitly enables mouse follow on both host and device. Keep the current pointer
position; do not reuse the global recenter action. Reset dwell evidence and clear the
legacy release pause so returning to pointing cannot immediately click.
Short taps, native drag releases and watchdog cancellation are different exits. They
must not acquire this activation just because they share a cleanup function. Pass the
resume intent explicitly on physical release; a lost-telemetry timeout only stops input.
Native lifecycle and device-to-simulator tests cover initially-on and initially-off states.

## Reuse review sessions from wand-only home cards

Keep the two extra review cards out of physical mouse cell enumeration and decoding. Render and navigate the same extended middle row only when VS Code is frontmost. The HUD publishes the selected held review mode; the receiver retains ownership of angular conversion, shared circular continuation and ordered Better Git requests. A physical Middle release finishes immediately; hidden HUD, stale navigation or lost app context cancels. Do not introduce another hold delay after Middle is already qualified. One seven-degree step reuses one review ratchet.

## Automatic table rest can stop active dictation

The native receiver previously sent a synthetic Top press after a quiet table-rest interval. Receiver traces proved AUTO_RECORDING_STOP_REQUEST immediately preceded recording stopping while Agent Flow retained the same PID. Do not diagnose that as an app restart. Rest detection now owns pointer power only and ignores samples while the explicit HUD session is open; intentional Top input remains the speech route. Do not use an idle gap between dictated messages as permission for an installation.


## UART source echo is not a runtime response

A cancelled partial REPL command can restore echo. Searching an echoed handshake for
`WAND_NEEDS_CONFIG` triggered an unnecessary full upload and exhausted device memory.
Reapply quiet input after clearing the command, match standalone response markers, and
reject a ready marker after an actual upload error. Tests execute the receiver's actual
marker handler against echoed source, duplicate markers and a failed load. Keep base
runtime failures separate from bridge failures, and preserve calibration when reusing
an unchanged runtime. A small verified light-function replacement can avoid reloading
the entire bridge during a receiver update.

## Review tap identity and visible selection

Each activation needs a new transport identity after a completed navigation gesture.
Reusing navigation's completed ID made the HUD deduplicate a real selection tap. Test
the actual transport method, not a stand-in generator. Keep selected Review and Stage
cards bright and retain their non-activating badge when the main HUD is visible or
hidden. Anchor that badge above the recorder's actual floating window when available;
exclude the normal Agent Flow Dashboard from placement and leave room when hidden.
Rendered SwiftUI checks do not establish physical wand acceptance.


## Independent pointer, review and speech lanes

Review changes is Ethan's “eyes mode”; Stage files is his “bang mode” / “!” whole-file selection. Keep those searchable names beside the adapter, not as a new implementation of Better Git. Review selection hides the main HUD while preserving the selected-mode heartbeat. Circle input is separate from Bottom's scroll recognizer: screen-clockwise produces next ratchets, anticlockwise previous, only with VS Code frontmost and Bottom released. Idle selected sessions send existing keepalive packets rather than silently expiring after a pause. Middle exits and finishes the existing Better Git selection; Bottom/recenter and speech do not clear it. Missing context or app focus stops review input.

Developer patches must queue complete statements individually with quiet-console prefixes and installation pacing. One unpaced multiline UART command can lose parser bytes even when a later ready marker prints. Verify both the registered button callback and the sensor callback after a patch; a matching source hash alone is insufficient proof of intact callbacks.

## Review selection needs explicit finish classification

Middle used to finish the Better Git selection on its first button-down, so a double click could not own the finish action. The receiver now keeps the existing transaction open while classifying that Middle gesture: one click cancels and exits; a double click sends the existing finish request, stages the set and exits. Pause only review navigation during this classification; Bottom pointing and Top dictation are independent. Clear the pending button state and review stream on reconnect so a stale release cannot finish a later selection.

A published or installed extension version is not proof of live activation. The real VS Code Running Extensions view showed Better Git 1.2.129 while 1.2.130 was installed, explaining the missing Eyes indicator. Check the running version after the supported update action. The wand reuses Better Git's selection, hunk navigation and exact Undo; its own input adapter must permit a new collection direction after backtracking to a single endpoint.

Seven final native Mini tests passed together, along with 156 non-GUI Better Git tests and 70 wand checks. Better Git 1.2.131 passed its Marketplace publisher/public Gallery/archive verification and was installed from Gallery. The Extensions view’s Restart Extensions action activated 1.2.131, confirmed in Running Extensions and the new activation log; a prior Developer: Restart Extension Host had retained the older selected version. Receiver 1.2.61 reconnected with the existing bridge unchanged. Wait for the authoritative Agent Flow idle acknowledgement before either restart; Agent Flow itself stayed running. Physical gesture acceptance remains separate.

## Committing a set keeps its selected review mode

Middle long-press stages through the existing Better Git finish request, then arms a
fresh transaction in the same selected mode. Keep the button latch through release,
even after the timer fires, so held movement cannot change either working set. A short
Middle tap cancels and exits without staging. The badge says `(hold to commit set)`.
A delayed timer is handled by the same once-only classifier on release. Receiver tests
cover frozen input, one finish, no held-motion replay and cancellation.

A quick mostly-vertical nudge after rest produces one next/previous ratchet when it
settles for 120 ms. Circle recognition takes precedence, so its opening arc never
becomes an extra nudge. Circle pauses reset that path before a new nudge; holding
Middle resets and suppresses both through the same navigation gate. This gesture
classification does not buffer pointer motion. Tests cover both directions, repeated
rest, noise, diagonals and a nudge after circling.

## App-specific pages retain their navigation owner

The app-mode context callback formerly sent another `navigate` command after entry
had already resumed navigation. Its new identity competed with the live navigation
hold, so Agentic Mouse correctly failed closed; the receiver then logged `context
ended` and dismissed the new submenu. The callback now updates context only. Keep the
entry/release path as the one owner of navigation startup, as for the other submenus.
An actual-callback regression test checks the unchanged navigation-command count.

## Horizontal and vertical circle continuation share one recognizer

The first deliberate Bottom-held stroke selects the dominant screen axis and direction. Keep that axis fixed until release; both axes then share arc-length gain, first-U direction retention and confirmed winding reversal. Accumulate acquisition travel once, and send wheel steps only on the chosen native wheel axis. Transposing the input trajectory must produce identical step counts, including pauses, reversal and stop-on-release. Tests also run actual raw receiver input through the native axis router.

## Micro circles without changing pointer gain

The review router discarded each sub-0.04-degree NAV delta, and its circle detector
dropped sub-0.015-degree segments instead of accumulating them. Preserve those
small increments until they form a heading sample; opposite jitter cancels. Review
ratchets retain the seven-degree distance scale for normal circles, with a bounded
turn contribution for tiny loops. Require travel on both axes and reject tiny local
curvature so a preceding real circle cannot amplify stationary wobble.

Held V2 scrolling keeps its quiet-rate guard and line gain while reducing the
heading segment, acquisition travel and minimum geometric extent. Synthetic tests
cover 0.15-degree review loops, 0.1-degree held loops, both directions, normal-size
ratchet equivalence, quantised input, straight creep and post-circle jitter. These
are input traces, not a measurement of the smallest reliable physical hand motion.
The device calibration, pointer filter, gains and motion-delay settings stay unchanged.

## Small review flicks follow their first lobe

Testing only the endpoint displacement rejected short up/down flicks that returned
towards the starting position. The review adapter now remembers the first qualified
vertical lobe, with a 0.3-degree threshold instead of 1.5 degrees. It still waits for
the existing 120 ms quiet endpoint, emits one step, then resets so the next flick
can go either way. Track maximum horizontal excursion to reject diagonal motion.
An actual circle ratchet suppresses the flick fallback; a weak curved candidate
which never emitted a circle step must not swallow an otherwise vertical flick.
Tests reproduce missed return strokes before the fix and exercise alternating
flick directions, curved flicks, circles, noise and the existing review lifecycle.
These are synthetic gesture checks; physical feel still needs acceptance.

## Keep the nod/shake review option independent

The optional review classifier accepts an outward-and-return motion on one screen
axis: either initial vertical direction means next, either horizontal direction
means previous. It preserves the selected option across gesture resets and checks
repeated gestures, slow input, noise, diagonals and circles separately. Its default
is false; installation must not change the user's existing feature-flags file.
Only review navigation uses this classifier. It does not alter mouse, HUD or speech.
The existing firmware navigation noise gate still applies; synthetic slow input
tests do not establish arbitrary slow physical-motion recognition.

## Review nods and shakes count each corner

The optional axis mode no longer waits for the movement to return mostly to its
starting point. After at least 0.3 degrees of travel, a confirmed 0.06-degree
reversal emits one step and starts tracking the opposite stroke. Continuing a
nod or shake therefore counts every corner rather than waiting for a neutral
reset. Tiny reversals do not repeat steps, and lateral movement around a rounded
turn rejects a circle. Quiet periods reset acquisition; the four-second bound
applies only before an axis is acquired, not to continuous review. Tests cover
long slow runs, both axes and starting directions, early reversal, noise and
circle rejection. Physical comfort remains a separate check.

## Tutorial freshness includes the animation

Narration text and control fingerprints are not enough to validate a video: a change to tap
timing can leave the same words while teaching a different gesture. Check the storyboard hash
as well as final media hashes. Derive scene timing from measured audio, but use short real-time
offsets for button patterns such as tap-then-hold.

## A running receiver may be outside its LaunchAgent

Restarting a LaunchAgent does not terminate a manually launched process holding the singleton
lock. Inspect the exact running receiver and launchd state. If the authorised restart needs to
replace an outside owner, recheck Agent Flow idle and terminate only that verified process;
then verify the new connected receiver and unchanged independent app processes.

## Review loops include sharp diamond and square corners

Ethan returned to clockwise-next and anticlockwise-previous, with the nod/shake
experiment disabled. The default review router no longer adds straight up/down
flick steps after a pause. A small polygon can place all its heading change in
one short sample: treating only that sample length as its turn radius rejected
valid diamond corners. Use the preceding straight edge as bounded supporting
travel for a sharp corner, while keeping the existing local guard for smooth
noise. Quantised circles, diamond loops in both directions and stationary noise
after real movement are separate regression cases. These synthetic traces do not
establish physical acceptance or prove the original asymmetric double-step cause.

## Review steps are quarter-turns, not travel distance

Ethan's north-to-east, east-to-north and north-to-west examples specify one step
per rough quarter-turn. The older review detector still accumulated path length
with a seven-degree quota, so radius affected the number of jumps. Default review
now accumulates signed heading change, with a 90-degree quota and 20-degree
endpoint tolerance. The first partial turn can qualify without a complete loop;
subsequent continuous quarter-turns retain the angular remainder. A meaningful
reverse clears the previous direction's remainder; a straight about-face resets
acquisition instead of inventing a clockwise/anticlockwise step.

Retain the independent geometry/noise guards, prevent unqualified motion from
banking a backlog, and count at most one step per report. Verify exact counts,
not just nonzero output: smooth and rough north/east/west arcs, subdivided sharp
corners, immediate reversal, multiple radii/speeds, four steps per loop, and
post-motion jitter are all covered. The nod/shake experiment remains available
but disabled. These are synthetic input checks; physical acceptance is separate.

## Ordinary pointer clicks are not the wand's double-tap gesture

Mouse events created with a nil source can inherit current modifier flags. The
receiver also used nearby click timing to grow the OS click count, even though
Bottom's double-tap is already consumed as a recenter gesture by the wand router.
Emit ordinary pointer button down/up as explicit modifier-free single clicks.
This applies to direct clicks, dwell clicks and native drag endpoints; it does not
change Middle's controls or the device's double-tap classification. Tests construct
the actual native events without posting input and verify type, button, flags,
position and repeated single-click count. The intermittent Codex new-window
symptom stopped before this change; its exact triggering state was not captured,
so do not describe either possible path as a confirmed physical root cause.


## Desk sleep reuses confirmed rest, without closing the HUD

After 60 seconds of fresh, continuously parked observations, the receiver requests
LED-off sleep. Gyro and HUD-report timer stop; 1.6 Hz accelerometer pickup sensing
continues. Pickup or a physical grip switch clears sleep, restoring the current
mode's light and the HUD report timer without resetting its angular origin.
Recording, explicit HUD visibility and selected review state are not sleep-owned.
The native HUD watchdog must tolerate suspended NAV heartbeats during desk sleep.
A telemetry gap restarts the pre-sleep interval rather than proving desk rest.

A fixed 2.15-second rest window had a blind band: at 0.56-second sample intervals,
four samples span only 1.68 seconds and the fifth loses the oldest sample before
reaching the required 1.8-second span. Keep the shortest window that actually spans
1.8 seconds with at least four samples. Native regression cases cover 0.1–0.9-second
intervals, and the installed receiver confirmed desk rest after this correction.

## Review corner diagnosis needs point history

The old classifier accumulated packet headings with tolerance boosts. Noisy isolated
synthetic quarters could disappear even when the noiseless version passed. The new
spatial detector measures coherent strokes and turning, distinguishes straight
about-faces from curved reversals, and retains learned noise across gesture resets.
Keep reversible quarter, rough square/diamond, sparse/slow and device-model tests.
Very small paths near the noise floor can still miss; synthetic success is not
physical acceptance or a measured precision claim.

Review traces are opt-in, local and bounded. Capture delivered NAV points before and
after orientation correction, eligibility, decisions and queued requests; replay
with the canonical Swift implementation. Queuing a Better Git command does not
prove it executed. Live enabling, learned noise and rotated prefixes limit exact
replay comparisons. Never publish private captures or treat synthetic traces as the
user's recorded motion. See diagnostics/README.md for capture and replay controls.

## Held scroll continuation needs fresh button ownership

Control V3 owns wheel velocity in a separate pure controller; the old V2 circle
recognizer remains available but is never called for V3. Capture a deliberate
straight stroke's speed before deceleration, retain it while the hand rests,
and replace it after a new coherent stroke, including an opposite direction.
Synthetic minimum-jerk strokes reproduced early-speed capture, tremor relatching,
recoil reversal and cross-axis leakage in the first controller. Measure a coherent
stroke, retain its peak averaged rate through deceleration, reject small recent
recoil and snap near-cardinal strokes to their axis. Use device intervals for rate
measurement and receiver time for transport gaps. The wheel-only rate average has
a 40 ms time constant; it does not buffer pointer movement.
A bounded wheel timer emits at the captured pointer anchor and cannot replay a
large delayed backlog. The existing physical-up reconciliation and button-sample
lease own cancellation; timer activity must never renew that lease. Native tests
exercise all directions, diagonals, reversal, quiet hands, release and telemetry
loss, including the actual receiver timer. This is synthetic verification, not
physical acceptance. Preserve explicitly labelled V2 tutorials against their
immutable control snapshot instead of claiming their footage demonstrates V3.

## A held HUD action owns pointer movement temporarily

Mouse follow and Middle's HUD navigation are independent, but the held card action
must not also move the system pointer. Ethan's "switch app button" is Middle
operating the selected Switch App card. Gate the common native pointer-posting
method for HUD entry holds and existing-card presses, including the period before
the hold qualifies. Keep angular navigation and card press/release delivery intact.
Return the unchanged pointer position rather than retaining movement for release.
An open, unheld HUD and independent review commit holds retain ordinary pointing;
cancellation clears the existing ownership flags. Native tests execute the real
handlers with inert mouse events, covering held sweeps, both horizontal directions,
release, context cancellation and review independence. Physical feel remains a
separate user check; the regression adds no pointer buffer or intentional delay.

## A recording pause preserves the mouse lane

Ethan's “stops moving the mouse ... afterwards it continues” means suppressing
pointer delivery during Agent Flow recording, not toggling its latched follow
state. Reuse the existing recording observer. Drop queued movement, reset the
motion filter and rebase the delivery point on both recording edges; never replay
speech-time travel on resume. Disable HIGH dwell scheduling and its timer callback
while recording so suppressed movement cannot create automatic clicks. The actual
receiver callback and event emitter are exercised with inert transports, including
prior-follow on/off and the existing held HUD guard. This does not prove physical
recording acceptance.


## Recording pause is a state change, not a permanent filter

Ethan wants recording to switch mouse follow off once, then allow explicit Bottom input
to turn it back on while dictation continues. A recording-state guard in the shared
movement emitter prevented that manual override. Use a separate pause state, clear it
on manual Bottom input, and keep the recording observer responsible only for its
one-time transition. Remember the prior follow state only until manual input overrides
it. Automatic desk pickup must not defeat that recording pause. Native inert tests
exercise start, manual override, explicit off, end restoration and queued-motion reset.

## Radial drawing and selection share a layout

The wand wheel uses one centre/ring ordering for navigation and drawing. Keep
angular and centre-return hysteresis in the navigator; do not overlay a radial
picture on the old grid hit map. Cache label geometry and measured typography
per layout/title set, not on every pointer update. Inspect crowded and odd-count
wheels as well as the default layout.

## Contextual holds must settle before input

A Bottom hold starts an off-thread, bounded Accessibility hit test. Only a
positive draggable target may select native drag before the existing hold
decision. Unknown or late results settle on scrolling; a token invalidates
results after release or a newer gesture. Preserve explicit tap-then-hold drag.
Inert receiver tests cover scroll targets, drag targets, unknown targets, delayed
answers and release. Synthetic success does not establish feel on every app.

## Rest must remember the user's mouse choice

A pickup event must not unconditionally turn mouse follow on. Remember follow
at confirmed rest, clear that remembered choice on explicit Bottom input, and
let the recording-start pause take precedence. If recording ends while the wand
is still resting, defer restoration until pickup. Keep HUD and recording state
out of rest ownership. Native tests cover prior ON/OFF and intervening choices.
