# Verified lessons

Ethan renamed the three grip buttons on 30 October 2026: Bottom is now the mouse button,
Middle the HUD button and Top the speech button. Lessons below keep the names used when they
were recorded.

## Temporary gestures must preserve newer recording choices

A triple-click starts by remembering mouse follow before its first tap. If recording
starts or stops before the third tap, blindly restoring that remembered snapshot
undoes the newer recording pause or resume. Advance the pending snapshot through the
same recording transition, including its pre-tap follow state and desk-rest memory.
The receiver-method regression covers both transitions between taps; ordinary
recording, HUD and pickup tests still pass. Screenshot ownership also uses its own
instance of the existing dwell detector so previously accumulated travel cannot end
a fresh selection immediately. These checks establish simulated state transitions,
not physical screenshot acceptance. Verified 25 October 2026.

## Tapered printed prototypes need profile-specific joints

The tapered profile reverses the twist-lock's male/female placement so its long parts
can stand on their wider ends for printing. It retains the cam clearances but is a
separate matching set, not interchangeable with earlier grips. Keep this explicit in
the profile and render its opposite insertion/turn direction; a shared slider must
not assume every physical joint turns the same way. Shape checks cover the seam
radius, two rib starts, shelf mirroring and continuous wire path. A full-width top
platform also needs surface probes on the exported left, centre and right zones;
a symmetric bounding box alone does not prove a common flat top. Physical fit and
upright-printed strength remain separate checks. Compare spiral cost by slicing the
same dimensions with the ribs disabled, using identical settings, rather than
assuming the decoration makes a large difference.

For Ethan's printed wand, "like DNA" and "criss-cross" mean two ribs winding in
opposite directions and meeting at crossings, not two same-direction helix starts.
Check measured rib angles and crossing sections. Compare surfaces immediately
beside mating faces; extra distance behind a face includes normal helix travel.
The generator's failure result must include profile-specific geometry checks.
When the strands have different pitches (Ethan's "one goes faster than the other"),
derive crossing test heights from their relative angular rates. Equal-pitch test
heights no longer identify crossings. Verify actual mesh crests both apart and at
the crossings; different pitch values in JSON alone do not verify the printed pattern.
Skip the twist-lock's air gap in decorative spiral travel. With tight pitches,
advancing the helix across that empty gap visibly offsets its crests at the two
faces. Compensate the shaft phase for the gap while leaving the joint geometry
unchanged; verify the actual face sections still align.
The spiral mug handle composes the existing full-hand loop with the same tapered grip
and spigot, rather than reusing the legacy mug's incompatible socket. Compare the
actual joint solids and wire route. For two complete wands on one plate, count two
lower shafts, two upper shafts and two XIAO holders as well as the two handles.

## The public sources reproduce the installed wand exactly

The runtime version is `wand-` plus the first 12 hex digits of the SHA-256 of the device program
from its `// Adjust only` line; the bridge revision is the SHA-256 of the compacted bridge. With the
original statement splitter and compactor, the imported sources reproduced the private upload
commands, runtime, boot image and bridge byte for byte (16 October 2026). Keep those algorithms in
`scripts/device_build.py` unchanged unless the receiver changes with them: the receiver compares
both identifiers on every connection. `tests/manifest.test.mjs` recomputes them.

The bridge statement compactor drops comment-only lines, so keep its `//` comments on separate lines: an inline comment survives joining and hides the rest of that generated statement. Exercise both readable and compacted input. The short-lived centre-held/left-press click (removed 2026-10-30) exhausted the saved Puck image's existing size margin; joining adjacent declarations and statements with all other Terser compression and name mangling disabled kept the image inside the unchanged calibration/storage budget. Preserve callback-discovery markers and verify the complete saved startup after changing that syntax packing.

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

## Website presentation must retain the control-version boundary

The home-page demo runs Control V1, while the illustrated tutorials show V2 and the
current receiver offers later controls. A visual redesign must keep those limits
beside each surface, even when longer status and control notes move into disclosures.
Build the headline, controls, light legend and version notes from their canonical
manifests; do not maintain a second hand-edited set in the HTML. The demo's light
legend uses the same displayed light state as the wand illustration. Desktop and
phone checks verified that feedback, disclosures, guide search and video playback;
they do not establish physical wand behavior. Verified 27 October 2026.

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

On the 24 October cold-start recovery, the expected runtime identifier was present while
the registered button and motion callback lookups returned no match. Forcing the base runtime
upload over that partial state restored a button callback, but the subsequent motion patch
hit OUT OF MEMORY and an EOF parse error. Runtime identity alone is therefore insufficient
startup health evidence. Inspect actual registered callbacks and retain the earlier
console-recovery path before choosing another full upload.

A later saved-program reload was followed by the Puck becoming unreachable over Bluetooth.
The receiver restart and reload request were logged, but device reboot completion was not
observed. Local scans saw other devices, not this Puck; a second Mac's scan lacked permission
and was not negative radio evidence. The cause of the missing callbacks and later radio loss
was not established; neither proves the repository refactor caused it. Preserve this distinction
and the saved program. A lit LED proves power, not a working radio or ready motion program.

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

Distinguish receiver replacement from a complete saved-device update when
reporting installation time. The maintenance sender uses acknowledged
writes and additional pacing, so a whole saved module takes much longer than a
Mac app swap. Prepare builds and verification inputs before stopping the receiver;
do not rewrite device code for receiver-only changes. Removing pacing or increasing
payloads is an unverified transport change, not a free speedup: preserve flow control,
complete saved code, calibration and readback verification. Measure the interrupted
interval separately from build/test time.

The receiver and saved-program console now share `WandUART` packet sizing.
Bound packets by both CoreBluetooth write limits and the Puck.js 2v27 UART's
50-byte value capacity (MTU 53 minus three bytes). The acknowledged limit alone
can report 512 bytes because it includes long writes; it does not establish
that the UART supports a 512-byte value. Keep acknowledged writes, XOFF/XON,
and the existing installation pacing. On the installed receiver, the negotiated
single-packet limit was 50 bytes and a 1,024-byte read-only challenge returned
the expected length and CRC32. All four saved program checksums were unchanged.
This verifies packet integrity on that connection, not full-install time savings.


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

Keep the focus outline as one animatable shape across the centre and ring, rather
than changing view identity and fading it. Test very small steps at both ends of
the morph as well as coarse intermediate frames: a full inward pull just below
the ring endpoint produced a visible 14-point jump. Ease the pull itself with
the morph. For readable radial labels, measure whole lines against the wedge at
each height and cache the resulting plan; rectangular fitting alone made long
labels shrink the whole wheel. Keep a cold-plan timing check alongside renders.

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

## A visible HUD owns its placement until it closes

The wand presenters previously polled Agent Flow window bounds every 250 ms and moved their panels whenever those bounds changed. Startup/transient recorder windows could therefore move an active target. Capture recorder clearance once per visible HUD lifetime, share the placement helper with the review indicator, and refresh on reopening or display reconfiguration. This is a visual anchoring policy; it adds no pointer buffering. Synthetic regressions cover large/compact/disappearing recorder frames while an anchor remains active. A live Agent Flow start was not forced during ongoing dictation.

## Tilt only where it earns readable space

A wedge-aligned title should remain upright and use a gentle exact card angle.
Prefer flat text when the tilted result is not both 1.5 pt and 10% larger; tall
slanted paragraphs remain flat. Measure each final rotated text box against the
actual wedge and keep the normal physical-mouse grid untouched. Cache the final
plan so pointer-focus updates do not redo the typography search.

## Component source and published assets have separate roots

The monorepo keeps Wand source under `magic-wand/` and the published site under root `docs/`. Use `scripts/paths.py` for those roots; resolve tutorial source records against the component and rendered `docs/` records against the repository. Run root `npm run check` to include all components and the repository-wide privacy scan. Moving files must leave device/receiver bytes and rendered media unchanged.

Private output guards must cover the repository root, not just the component root. The replay report path check resolves paths before writing and permits only external locations or the explicitly ignored root/component `work/` folders; its regression test includes another component and the published site.

Component checks are narrower than the monorepo gate: the root check command runs repository-wide privacy scanning before all components. Setup docs and error hints must name the working directory explicitly after source moves. Shared privacy scanning prunes dependency and generated-build directories; component syntax checks examine owned source rather than installed Python packages.

## Automatic calibration and deeper standby (2026-10-24)

The base connection callback clears its calibration while starting a new measurement. A known runtime or ready marker alone therefore does not establish usable motion after reconnection. The receiver now stores validated calibration offsets per physical device and conditionally restores them after its normal ready handshake. Never publish those private per-device records. Corrupt, mismatched or out-of-range records are rejected.

Deep standby is a small separately loaded power policy so it does not replace the working base program or motion bridge. After five minutes of confirmed rest, the receiver requests radio/sensor/light shutdown only when no button, scroll, recording or explicit HUD/review is active. Retained GPIO watches wake advertising on any custom grip press. The first press wakes the device while disconnected; it must not emit a speech or pointer action. A reconnect restores the recorded pointer choice and calibration. Ordinary disconnected indication goes dark after one minute.

The installed policy loaded successfully alongside the existing bridge, with calibration intact. Synthetic checks covered all three wake buttons, radio/sensor/light shutdown, retained offsets, duplicate loading and disconnected timeout. A subsequent receiver stop/start retained the accepted offsets and resumed real movement reports. Physical five-minute sleep and button wake remain unverified. Do not describe reference power figures as measured battery life.

An in-source version guard does not make retransmission safe: the Puck still parses the entire incoming body before skipping it, and a warm runtime can have much less free RAM. A second full power-policy transmission exhausted memory. Check the version and callable entry point with a short, separate command first; request the full policy only when it is absent. Receiver 1.2.82 passed this real reconnect path with the existing policy reused and no reload error. The regression test exercises both installed and missing-policy responses.

## Complete saved startup (2026-10-24)

The previous device had a compressed interpreter snapshot and two old boot images consuming nearly all its storage. Its current base image matched the generated source, but the bridge and power additions only lived in RAM. After backing up every saved byte, the checked installation removed the old snapshot and obsolete image in a reset interpreter, kept the verified base, and wrote the complete bridge, power policy and self-contained startup. A final compaction happened before loading flash-backed functions. The immutable code is packed before the writable calibration record so routine calibration replacement does not move running code.

Every saved payload was checked by length and checksum. A clean saved-program boot was inspected before the receiver was started: the full image marker, current bridge, power policy and valid calibration were already present. Receiver 1.2.83 then connected without uploading a runtime or bridge. This verifies the saved startup path; it does not claim a repeated physical battery removal or measured battery life.

The HID module is included in the saved startup, so no old interpreter snapshot or online module fetch is required. The build uses pinned Terser with compression and name mangling disabled; ASCII output preserves the byte offsets used by Storage writes. The complete payload and its manifest are reproducible from the readable sources, not maintained as another source copy.

## Passive Switch App navigation has no held-input timeout

Ethan calls the armed Switch App outline “dotted”. Unheld movement may navigate
away from it without operating an action; a later Middle hold still operates
the armed app switcher. This passive session must not inherit either end’s
held-input watchdog, because a quiet pause or desk sleep is not dismissal.
Bottom-held scrolling or dragging parks passive navigation; restarting from
a fresh origin avoids replaying that movement into the HUD. The native and
receiver regressions cover pauses, the next real hold and Bottom isolation.
Installation and physical acceptance are tracked separately from source tests.

## Local task ledgers are not public source

Per-chat outstanding-item ledgers live in the Git-ignored root `.outstanding-items/`
directory and may contain private workspace references. The repository privacy scanner
excludes only that root directory; equally named folders inside components remain scanned.
A synthetic boundary test verifies both cases, and the ledgers must never be staged.

## Switch App uses the shared HIGH mouse calculation

Held Switch App used unscaled angular travel while the pointer used speed-adaptive
sensitivity. The receiver now exposes unrounded HIGH output from the same sample,
before Bottom's LOW multiplier. A cumulative optional mouseX field is consumed only
by the native held Switch App branch. Existing angular navigation and other wheels
remain independent; legacy packets still work. The native tracker rebases when the
metric changes, preventing a discontinuity from becoming an app switch.

HUD-only motion must still produce raw samples when mouse follow is off. A dedicated
flag lets the receiver calculate shared sensitivity and then return before posting
any pointer event. Tests exercise both that boundary and unchanged normal/LOW math.

During full saved-program maintenance, stop the live handlers before verification:
an existing handler error can otherwise abort a readback. Use the built-in CRC32
checked against the host implementation rather than a long interpreted hash loop.
Wait for the receiver process to exit after launchctl acknowledges its removal.
Saved startup, bridge and power files are verified before restarting the receiver.

## Printed wand slicing: model geometry is not a print verdict

The first loop-wand meshes pass solid, collision and joint checks, but Bambu Studio 2.8.2 still
flags pin floating regions and rail/socket cantilevers. Inspect the real slice and enable
removable support where needed; the face-angle summary alone does not establish a support-free
print. Test the mating coupons before claiming printed fit.

Bambu CLI profiles must be fully resolved rather than raw bundled files with `inherits`.
When packaging a local 3MF with altered process values, register those keys in the process
slot of `different_settings_to_system`. Otherwise Studio can load the named system preset
and discard the values even though the original CLI slice used them. Verify by opening and
saving through Studio, then reading back the actual settings. This caught supports changing
from enabled to disabled; the corrected round trip retained supports and the brim.
The same override registration applies to infill: a CLI slice stored 20%, but Studio
resolved the named Extra Draft base preset to 15% on opening. Register layer height,
walls and infill alongside support/brim values, compare the saved Studio copy with
the prepared configuration, and keep the generator's required-key check.


## A released Bottom must not leave an orphaned native drag

The V2/V3 receiver handled physical-up recovery only while its held-scroll state
was active. After teardown, a stray legacy button-down packet could reach the
ordinary pointer router, leave the native left button down, and evade later
physical-up recovery. The native handler regression reproduces that state; it
is not proof that it caused a particular user-reported incident.

In V2/V3, the native hold owns dragging; late firmware button-down frames cannot
start it. Physical-up recovery releases a native left button even after the hold
was cleared, and ending a hold clears its dragging flag. Keep short-tap mode
changes, explicit tap-then-hold dragging, contextual target selection, and Middle
HUD/Top speech independent. Native regressions exercise missing releases, late
packets, repeat teardown and later holds; real-device acceptance is separate.


## Screenshot selection is an explicit drag target

The receiver receives the native screenshot-active state but previously routed
Bottom through the ordinary contextual scroll/drag probe. A screenshot overlay
is not an ordinary scroll target. While screenshot selection is active, Bottom
parks the HUD, skips that probe and posts native left-down immediately; raw
motion draws the rectangle and physical release posts left-up. Normal holds
retain their existing classification cutoff. The native contextual-hold test
failed before this change and passes afterward; actual capture still needs a
physical check.


## Cancel the device button before clearing its drag state

The motion bridge's `setMouseFollow` replacement cleared the `dragging` flag
without queuing a button-up. After a mode or recording change, the later physical
release no longer entered the drag branch and `sentButtons` could remain one.
Emit the up before clearing the gesture. Tests exercise both follow values with
readable and statement-split saved bridges and verify later frames stay released.
V1 also releases orphaned native downs on a physical-up sample after its release
edge, while leaving a real held drag alone during switch debounce.

Receiver battery reads use existing built-in APIs through the existing BLE owner;
they do not require a second connection or a volatile firmware helper. Preserve
sample age and describe the Puck's CR2032 estimate separately from runtime.


## Wand input in the printed-model viewer

The receiver classifies a browser web area as scrolling, so a plain Bottom hold
reaches the 3D preview as wheel events. Mapping every wheel event to camera
distance made intended model manipulation zoom instead. The viewer now uses
one Turn/Move/Zoom controller for drag, wheel and keyboard input, with Turn as
the default and deliberate zoom controls. Only the canvas captures scrolling.
No receiver changes or automatic recognition of arbitrary 3D viewers is implied.

Reset framing uses the actual model bounds and viewport aspect ratio; a fixed
distance clipped the long shafts in a tall Codex panel. Tests project all box
corners in wide and narrow viewports, and browser checks cover both XIAO handles,
legacy Puck models, modes, joint controls and a narrow layout. Physical wand
comfort and multitouch remain separate from those browser checks.


## Native movement needs relative distance as well as position

The receiver created mouse-move and drag events with an absolute destination
but left their delta fields at zero. A passive session event tap observed
153 receiver movement events with zero deltas while physical-mouse movement
reported nonzero deltas. Preserve both the destination and the actual clamped
movement in mouseEventDeltaX and mouseEventDeltaY. The native constructor test
checks move, left/right drag, display-edge movement and no movement. Live
notification dismissal still requires a physical check.

A notification banner is a native drag target inside a scroll container. Its
Accessibility subrole must take precedence over that ancestor when choosing
Bottom hold behaviour. Send ordinary mouse events; do not turn a drag into a
separate Close action. Explicit tap-then-hold and screenshot selection retain
their existing paths.


## Manual power chord and sleep warning (2026-10-24)

The all-three-grip power chord is consumed before the actual registered Bottom,
Middle and Top handlers. Latch it until every button is released. Any single grip button
wakes either manual or automatic standby; consume that wake press without
triggering its ordinary mouse, HUD or recording action. Consume
that first automatic-wake press until release too, otherwise a three-button wake
can immediately turn the wand off again. Regression checks cover both sequences.

A centre-held/left-press click chord (2026-10-30) was removed the same day.
Ethan: “I don't want to do that because it's too hard.” It also clicked before a
third press could complete this all-three standby chord. Do not reintroduce a
two-button click chord; the wanted manual click is a double HUD (left/Middle) click.

All three LEDs blink on/off twice at 100 ms per phase before deep standby. A grip
press cancels an automatic warning; an intentional manual power-off chord is not
cancelled by its own held buttons. The complete saved image was verified by length
and checksum, loaded from a clean interpreter with calibration, and reconnected
without code upload. Physical button feel still needs user acceptance. The prior
five-minute rest, disconnect and button-wake cycle was observed before this change.

Persist the base through the same syntax-only minifier as the other saved parts;
its readable source remains canonical. The cold-boot test restores line breaks
before top-level declarations only for the simulator's replacement-function shim.
No pointer timing or sensor rates changed.


## Review-mode double-click and native request identity (2026-10-26)

Middle clicks in Review changes and Stage files are separate from the normal HUD
click handler. A first short release waits at most 300 ms (explicitly approved)
for a second press. Only a second short release toggles; holding either press
for 500 ms still stages the selection once and stays in the selected mode. Ignore
duplicate releases, cancel superseded timers, and keep pointer movement immediate.

Agentic Mouse owns the selected review mode and acknowledges it through its
existing selection context. Each toggleReview request needs a fresh transport
identity: reusing the previous persistent identity makes later toggles look like
duplicates to the native receiver. Tests exercise alternating modes, native
acknowledgements, duplicate edges, late timers, and a held second press. These
checks do not establish physical button acceptance.


## Review mode changes preserve the live selection (2026-10-26)

Review changes and Stage files share Better Git's existing selection. Do not end
and begin the wand transaction just to toggle its mode: cancellation discards
the membership, while finishing stages it. Send a `mode` packet with the same
transaction ID and the next sequence. If no navigation has created a transaction
yet, send `begin` then `mode`, without a `step`; this includes the current file
without moving to another one. Better Git 1.2.135 adds this protocol.

Reset only the review-circle geometry across a mode switch, keeping the NAV
stream, heartbeat and tracking intact. The existing hold-to-commit ends the same
selection normally. Tests cover both directions, first-motion-free switching,
packet identity, cancel, and one final commit.

## Hollow print geometry still needs sliced-path checks (2026-10-26)

The lightweight Print V3 grip passed solid and wire-route tests, but its first tree-support slice routed support branches through the hollow grip and button cable space despite internal support-contact blockers. Checking only blocker presence did not protect the finished route. Per-object normal supports from the build plate eliminated those internal paths and the unsupported-region warnings in the final P1S PETG slice. The recorded 0.5 mm-step path scan covers the grip, shafts, battery reference, button outlets, board, solder and USB clearances; it does not prove printed fit or strength. Keep the support type in the portable 3MF recipe and inspect the sliced extrusion paths after geometry/support changes. Compare actual slicer mass under matching material/layer/wall/infill settings: a percentage reduction in solid CAD volume overstates the gain against a sparsely filled old model.


## Preserve visible print identity while hollowing (2026-10-26)

The V3 candidate removed the original helix and used narrow spans between wider joint collars. That failed the requested lighter-wand revision even though its mechanisms passed geometry checks. V4 restores the two counter-wound 90/72 mm ridges and continuously decreasing shaft core, with thicker annular joint anchors inside the silhouette. Verify actual rib material, sample the shaft-radius profile, and compare assembled original/new views before delivery. These checks establish geometry, not printed strength.

A complete V4 project contains both handed grips as build instances, plus one shared set of other parts, matching V2's contents. A right-hand STL beside a left-only 3MF does not satisfy that requirement. Verify the opened archive's build list. The project-specific print-design skill and component instructions retain this explicit user correction.


## Check triangle output after coincident Boolean seams (2026-10-26)

Raising the V6 side-button pair left the right grip as one valid Manifold body, but the extracted triangle soup contained unpaired edges at coincident Boolean seams. A 0.00001 mm simplification before grip mesh extraction restored closed exported surfaces without changing fit dimensions; all thirteen non-grip meshes remained byte-identical to V5. Keep actual triangle watertightness and edge-count checks, rather than accepting Manifold status alone. Do not move a requested feature or enlarge its clearance just to hide an export seam. This establishes the generated geometry, not printed strength.


## Handed ventilation and complete-wand mass budgets (2026-10-26)

The V7 button angles mirror for handed grips, while the established crossed helix does not. Recompute ventilation angles against each grip's actual button keepouts and the common rib geometry; simply mirroring the left hole positions can cut the right-hand helix. Check that holes connect through the skin, leave continuous ribs and roots, and remain clear in the actual sliced extrusion paths.

A target for a complete wand includes the board, battery, bought switches/sockets/keycaps, wires and insulation. V7's matched PETG slice estimates 75.688 g for printed parts, leaving 4.312 g for unweighed hardware at an 80 g target or 24.312 g at a 100 g ceiling. Do not describe the print-only estimate or waste-inclusive filament use as a verified all-up weight. Local hollowing/clearance tests and sliced mass do not establish PETG strength or a weighed result.


## Hollowing can expose previously supported board-pocket lips (2026-10-26)

The first hollow V7 head remained a single watertight body, yet its upright PETG slice flagged floating regions at the upper board-pocket lips. Narrow sloped struts removed the sampled layer islands. Enabling normal support cleared the slicer warning but routed support through the cable and USB passages despite contact blockers. The finished V7 retains the hollow V6 shell and original support strategy, with narrow sloped struts for the upper board-pocket lips; slimming and ventilation remain in the handle and shafts. A warning-free slice alone is insufficient: keep the layer-island guard and inspect the actual extrusion paths through all functional clearances. These checks do not establish physical strength.


## Ventilation follows skin contact; assess the whole grip layout (2026-10-26)

V7's loop bores crossed its broad X faces rather than its inner contact edge, and its 20 mm loop uplift placed the loop too high relative to the controls. V8 uses each loop station's inward normal in the YZ plane for outside-to-contact passages, rear grip outlets near the fingers, and separate outside intakes. The viewer's arrows and amber contact markers distinguish the functional direction from decorative perforation. Solid probes verify the four loop passages in both hands; this is not a cooling measurement.

The revised loop removes the 20 mm uplift and uses an upper arm rising toward the index-finger attachment. All buttons shift up 10 mm while retaining their 4/26 mm vertical spacing and original side/radial placement. Judge the assembled loop, fingers and control relationship together; checking button coordinates alone did not establish the intended fit. PETG comfort and reach remain physical acceptance tests.

A port-mouth support blocker did not prevent a normal-support column descending through the lowest outside opening: the first two slices each contained 13 sampled support points in that passage per hand. Blocking the support landing-source regions above the ports removed those points in the third slice, with all protected paths clear and no object warnings. Keep side support available around these narrow shadows. Inspect actual sliced extrusion; a contact blocker is not a guarantee that the space below it stays empty. This is slicer evidence, not a physical print result.

## Upper reach is not a request to change orientation; detachable open frame (2026-10-26)

The user rejected V8's sloping-arm interpretation. Their correction refers to how far the high/thumb region projects from the wand, with a tucked lower return, while retaining the loop plane and button angles. V9's centreline reaches approximately 49 mm in the high region versus 39 mm in the lower region; its plane remains YZ and button coordinates remain unchanged. The preceding V8 interpretation is superseded by this correction.

V9 separates the universal finger loop from both handed stems. Two captured dovetails retain it radially, an integrated side tongue blocks lifting, and a geometric 1.8 mm tongue-deflection envelope clears the 22 mm release slide without touching the bought cap envelopes. Buttons, battery and wiring stay in the stem. These checks establish CAD clearance/capture, not PETG release force, durability or physical acceptance; use the new loop-mount coupon first.

The requested large diamond framing replaces the small shaft/grip flute apertures. Designated open bands have 3 mm strips with 2 mm inward depth, retain the original raised crossed helix and remove about 57–64% of their unwrapped surface area. Keep solid local joint, battery, control and loop-mount regions. Whole-wand surface openness, structural loading and cooling are different quantities; do not imply this band-area fraction is a measured weight reduction or verified strength.

A whole-plate sampled-path check previously projected a neck probe at z 352.5–374.8 mm into the sliding cover, whose physical lower extent is 376.25 mm. After rearranging the plate, that imaginary region hit a neighbouring part's walls/brim. Clip the neck probe to each part's actual axial extent rather than attributing neighbouring extrusion to nonexistent cover material. Preserve all actual board, USB, wire, frame, loop and new mount-slide probes; the final V9 checks found no extrusion in those protected passages.

## Open braid rejected: preserve the solid spiral and supporting tube (2026-10-26)

The user rejected the V9 open diamond frame, despite its manifold and clearance checks. The request is to retain the original continuous body and raised spiral, then lighten it with separate holes/slots; not to use the helix itself as the void pattern or sole load-bearing braid. V9 is archived as a rejected experiment, not the current print recommendation. V10 restores the hollow tube's continuous 1 mm skin around separate narrow slots, keeps the complete raised helix strips and three 3.2 mm longitudinal supporting lands, and retains local solid hardware/joint zones. Four elongated loop slots replace the little bores. Geometry checks now sample both the crest and edges of each original spiral strip, the axial lands, and independent slot passages. These checks still do not certify physical PETG strength.

The V10 slot checker initially extended 2 mm beyond the bare tube wall and counted five normal-support samples near radius 15.14 mm against a wall radius near 13.17 mm. Those samples were exterior removable support, not extrusion through the actual slot. Check through the skin and interior with a 0.3 mm exterior allowance; distinguish nearby support from a blocked passage. Narrow support-source shadows reduced total support, while the actual wall, axial lands and complete spiral-strip checks remain intact.

## Broad windows need a coherent supporting shell

The user rejected the sparse V10 slots after rejecting the V9 unsupported-braid interpretation. These corrections require a more open, regular perforation architecture while retaining full decorative spiral strips and independent support. V11 uses broad curved hexagonal cells with four 3 mm wide meridional lands, with 1 mm grip skin and 1.4 mm shaft depth, solid local hardware/joint zones and short cell connections. Its loop opens through the inner contact and broad faces. This is the user's design direction; no physical strength or aesthetic acceptance is implied by the checked candidate.

Nonlinear cylindrical cutter warps need a positive orientation and adequately subdivided faces. A first reversed warp produced negative cutter volumes; a coarse cap then left disconnected interior fragments. Positive-orientation, full-depth refined cutters exported as eighteen closed single-body meshes. Keep actual mesh and disconnected-body checks rather than trusting only the solid-kernel status. Spiral probes also need to respect the existing button/mount clearances: compare against the previous actual part instead of inventing material in a deliberately cut interface.

V11's initial flat-loop slice left first-layer support/brim film inside the broad-face vents even with contact/source blockers. Expanded blockers alone did not eliminate it. Normal manual supports enforced only at the two mounting roots, with no brim on that wide flat loop, cleared all sampled opening interiors; the complete prepared plate still sliced without reported warnings. Keep this per-object setup with the model and check extrusion paths including first-layer adhesion. This is slicer evidence, not a measured print/adhesion or strength result.

## Curved windows and actual reinforcement

The user's V12 refinement asks for slightly smaller handle holes, flowing Art Nouveau curves, smoother thicker connecting rails and the retained silhouette/spiral. V12 has 12.3% less total grip aperture area, smaller curved loop ports, 3.6 mm rails and 1.6/1.8 mm final grip/shaft depths. Reinforcement must survive all later booleans: V11's grip core subtraction trimmed its nominal 1.4 mm rails to the 1 mm skin. Adding V12 rails after hollowing and subtracting hardware clearances separately leaves actual added material; 24 final-solid probes compare old void/new material. This does not establish PETG force or impact strength.

Nonlinear warping of slender curved cutter caps left radial STL edges shared by four faces, despite the solid kernel reporting NoError. Rounding and simplifying the 2D outline alone did not fix it. Native radial loft cutters, assembled from short hull sections, produced closed single bodies; an inner radial keepout preserves the earlier cut depth and joint anchors. Check exported edge incidence, winding and body count as well as kernel status. All eighteen final V12 meshes pass. Keep native cutter protection and full interface checks together.

## Detachable loop seats upward under an upright wand (2026-10-27)

The user corrected V12's top-entry loop mount: the finger loop must slide upward relative to the wand to attach and downward to remove. When the loop is held and the tip points upward, downward wand load moves the loop upward relative to the stem. Closed upper track ends must carry that load even with the release tongue deflected. The latch instead prevents deliberate-release-direction withdrawal. Keep this direction separate from the top-slide button plates and head cover.

Reversing only the receiver creates a downward entry corridor through the wider lower body and can cut the retained spiral. V13 puts the mount sweep outside the maximum body/spiral radius along that corridor and connects the receiver backs to the stem. Check the complete downward slide, outward removal after release, battery cap and bought keycaps in both hands, plus radial capture, the upper hard stop with latch released and downward capture with latch engaged. The small mount coupon must include the reversed free-end release tab. These are CAD collision/capture checks, not physical load or fatigue certification.

The first V13 slice left support/transition/interface extrusion in the lower mount entry route. Reversing an open-top track introduces a closed upper roof; normal supports can occupy that new route even when the wider internal bore remains clear. Include a slightly expanded track-shaped blocker through the roof landing source and check all extrusion types in both hands. Keep the roof bridge and the small coupon subject to physical testing.

A track-profile blocker alone left two support-transition samples under the lower stop roof. Exclude the entire closed-stop roof source, not only the dovetail footprint. Twelve other flagged samples were at assembly z 3.4–9.6 mm, below the receiver’s 9.7 mm lower edge: these are exposed removable supports, not an internal track obstruction. Clip the internal-track probe to the actual receiver extent; retain complete model/cap release-motion checks and tell the builder to remove exterior supports before assembly.

## Lift-and-turn loop requires implemented CAD and positive capture (2026-10-27)

The user asked to implement the tightening mechanism, not stop at an explanatory concept. V14 keeps V13's final loop orientation and hollow shape, but adds 22 mm upward entry at a 12-degree clockwise offset, followed by a 12-degree left turn through 0.6 mm of cam rise. The reverse-turn catch is a radial spring; its nominal small tooth overlap is intentional preload, not a rigid-part clearance. Verify rigid solids separately, the seated spring envelope and the fully released spring envelope. Force, fatigue and printed tolerance remain physical tests.

Both handed stems must clear the complete turning and lowering route, bought keycaps and battery cap. Check upper/radial/downward capture with the catch released, reverse-turn capture with it seated, and a separate single-mount coupon. The single coupon has one lower capture surface, so its positive-volume threshold is distinct from the two-mount assembly. Both exported meshes and the prepared print projects remain required.

Rotating the lower receiver envelope initially touched the retained loop skin at its inner cut plane. Flare only the lower neck's outer mouth, keeping the inner dovetail capture and upper catch shoulder intact. Keep the full original helix and all other shared parts unchanged. Verify native cutter volume before booleans: an incorrectly wound flare outline made the cutter invalid and emptied the stem; closed-mesh/body and switch-capture checks caught that failure.

A spring tooth can appear to preload at the nominal pose yet do nothing if the complete rigid handle can float outward farther than its interference. V14 probes both rigid capture and nominal tooth contact through the available radial travel. The final tooth remains in contact through 0.35 mm of free radial float, while rigid capture is reached by 0.4 mm. Seated and released spring envelopes remain separately collision-free. This establishes geometric preload, not actual force or fatigue.

## Detachable handle must leave a normal wand (2026-10-27)

V14’s geometric lock worked but its external receiver housings remained on the bare stem. The user rejected that accessory-off state. A complete design review must include both attached and detached configurations; a working mechanism alone does not satisfy the product’s use without its accessory.

V15 moves the receivers inside the existing stem surface. The removable loop carries the enlarged pegs, roots and release spring. A recessed keyhole route shortens the lift to 4 mm before the retained 12-degree cam turn. Keep the external silhouette, original decorative helix and both hands. The receiver reinforcement must be cut by the existing window voids so it does not obstruct ventilation internally, and checked against the actual original exterior mesh rather than a differently sampled local loft. Keyhole entries locally interrupt the rear axial land; check the reinforced pocket floor separately, while retaining the original raised helix material. These are geometry and manufacturing checks, not physical lock-force or strength verification.

The V15 five changed mount parts use 0.001 mm simplification before canonical 0.0001 mm-grid STL export. Native closed booleans can otherwise leave collapsed seam triangles after coordinate quantisation. Verify the exported watertight meshes and reproduce their hashes from the portable CAD; thirteen shared meshes retain their previous bytes. Direct receiver-versus-original-surface checks prove no protruding mount material; the assembled rear mount region is checked with a 0.01 mm surface envelope to separate numerical surface residuals from actual brackets.

A broad manual support enforcer around the new lower mounting root entered the existing hand-contact vent despite its support blocker. Split the enforcer into the small stud/inner-root region and the lower anchor region, away from the aperture. Inspect support and interface paths through the actual vent, not only the lock and wire channels.

## Borderless switch mounts and actual print orientation (2026-10-27)

V15 retained projecting rectangular pocket surrounds and rotated XY switch plates upright, contrary to the user's intent and the orientation comment. V16 keeps the purchased socket alignment, moves the switch/plate/socket inward 3.4 mm and removes the exterior square perimeter. Two short side arms and lower stops retain the plate. Relief behind the arms is essential: a nominal clip fused to the underlying curved stem cannot flex. Check the deformed clip envelope and the full radial route, along with hard stops and the complete bought keycap stroke. These establish geometry, not PETG clip force or fatigue; a small matching curved coupon is included.

Print the thin plate with its broad front face on the bed and rear feet upwards. Check the actual exported 2.5 mm height and bed-contact triangles. The mesh report's downward-flat area counts ceilings above the bed, so it is not a bed-contact measurement. A whole-assembly scale is also not a general outward tolerance envelope for concave tabs: it translates their inner edges and can report false residuals. Retain the exact control features and expand only the original tube surface for the separate bare-handle attachment check.

- 2026-10-27 — Verified deeper-switch interference: after moving pockets inward, hidden detachable-loop reinforcement was unioned after the switch clearances and filled part of the right thumb socket seat. Subtract control pockets and clip relief from that reinforcement before union, and check every socket and switch in both handed stems. The sliced extrusion check detected ordinary wall paths inside the right socket despite the earlier left-only component check. Geometry and toolpath clearance remain distinct from physical fit.

## Check the attached handle silhouette, not only its mechanism (2026-10-27)

The V16 lower loop left a permanent toe below a separate bridge. V17 removed that toe but replaced it with a rounded U return and a visible gap around the small stud; the user rejected that interpretation too. The current requirement is matching direct inward arms at both ends, broad shoulders seated in recessed wand openings, and substantial captured pegs that lock by an upward lift and short turn. The bare wand must remain usable without projecting mounts. Preserve this explicit correction over the older curved-return interpretation. V18 keeps the 10.4 mm route and the battery cap while reducing the grip core diameter by a further 1.6 mm. Geometry and slicing do not certify strength or comfort.

## Native input can stall independently of the wand transport (2026-10-27)

A live Agentic Mouse sample proved that its main thread was waiting for a
Corsair device-enumeration reply. Both physical mice stopped because the same
thread dispatches their input. This did not establish a wand Bluetooth fault.
Keep potentially blocking vendor requests on the bounded worker recorded in
`integrations/agentic-mouse/icue-hang.patch`, retain C buffers until actual
completion and reject queued requests while the worker is stuck. A responsive
main thread after installation does not prove iCUE reconnection or lighting
recovery; those require separate evidence. Do not change the Puck or receiver
just to publish a native input fix.

## Display roles and window identity are separate checks (2026-10-27)

The Split layout incident retained the saved display identifier; the attended
native probe instead reproduced rejected Chrome windows whose WindowServer and
Accessibility titles differed among identical frames. Resolve the main external
workspace role from live screens, while preserving the runtime display identity
and geometry guards against changed-display writes. For windows, the existing
unique public Accessibility main-window fallback must also handle a nonempty
unmatched title. Never guess between remaining candidates; skip a nonstandard
popover with no matching standard window frame. The native delta is preserved in
`integrations/agentic-mouse/display-role.patch`. Automated and attended native
checks do not establish physical mouse acceptance or authorize changing another
app's saved display layout.


## Lightweight studies must preserve full roots and support landing clearance (2026-10-27)

When thinning a detachable loop, preserve each complete direct seating arm. Clipping the old root at a tangent to the narrower tube left a real detached sliver (about 0.015 mm³); keeping the full root region removed it without discarding material as mesh cleanup. Check actual exported STL components as well as the source solid.

Open shaft variants need their own support strategy. Enabling normal supports with only the old small wire-bore blocker allowed descending support columns into the route. Extend the blocker over the hollow interior's support landing sources and check actual straight and arc extrusion samples, including support features. The lattice-study reports cover seven candidates and both handed stems; slicer clearance does not establish physical print quality or breaking strength. Keep exploratory studies separate from numbered models so a concurrent collaborator's next version cannot overwrite them.


## Open sensor cradles need a different print-support strategy (2026-10-27)

Automatic support in a slim open cradle filled its wire passage upright, and its board slot when laid flat, despite support blockers. The checked lattice-study projects lay the cradle on its back and use manual landing patches on the low back only. Keep the board, USB, wire route and central solder space in the sliced-path checks; do not re-enable automatic head supports without repeating them. The only allowed solder-space samples are removable support feet within 0.4 mm of the build plate, at least 0.5 mm outside the actual local back surface. Record them separately rather than hiding them among clear channels. These are toolpath checks, not a physical retention or spring-flex test.

Comparison viewers must request fresh manifests and estimates and key STL URLs by their recorded hashes. Browser caching otherwise showed old weights alongside new geometry. Offer print links only when the project hash matches its sliced-clearance receipt.

## Continuous lightweight shaft (2026-10-27)

The two upper sections of Two wide spirals fit as one 206 mm print in the checked P1S profile's 250 mm height, allowing openings across the former middle joint. Keep the original grip-side lock and detachable loop; the narrowed tip uses its own matching scaled cradle connector. Check the real sliced wire route and cradle clearances after changing this joint. CAD and sliced paths do not establish physical strength, fit or retention.

Porting that shaft to V19 requires its new grip connector and the unchanged V19 solid loop, cap and controls; V18 and V19 stem joints are not interchangeable. Scaling the tip connector to 85% passed the solid checks but left an empty layer in Bambu's slice. A 90% connector sliced without warnings and retained the checked wire and board routes. This does not prove physical connector strength.

## A sharper tube with a wider tip holder (2026-10-27)

Ethan clarified that the tube should taper more sharply while the XIAO stays at the tip; the holder may be wider than the tube. The sharper study keeps the 10.4 mm design bore and uses a separate sleeve around a 12.4 mm tube tip. Scaling the old connector was not a fundamental limit on taper. A channel assembled from many overlapping small rectangles triggered Bambu's `ZFiller` error; replacing it with a smooth sector removed that diagnostic in isolated and complete slices. A support enforcer under the sleeve also put support into the turn channel, so the checked layout stops that enforcer above the channel and probes its entry and turn path in the actual G-code. Neither slicing nor geometric capture proves physical fit, joint strength or retention.
## Keep ergonomic anchors independent of mechanism convenience (2026-10-27)

V18 removed the lower tail but kept the old elevated locking mounts, raising the visible bottom of the loop and leaving an unwanted gap. The user reiterated that the loop belongs at the butt and controls follow it as a group. Freeze the butt reference and button offsets as design inputs, then fit the mechanism around them. Do not let an older receiver position become an ergonomic requirement. The user also explicitly replaced the thick hollow loop with a slim solid band and requested a 5–10 mm grip reduction. An oval battery zone can preserve cell width while reducing hand-contact depth; distinguish those measured axes from a circular diameter reduction. CAD clearance and slicer mass still do not establish physical comfort or strength.

## Sweep broad rotating locks locally (2026-10-27)

A global convex hull around every pose of a rotating shoulder/head can fill the intended concave sweep and erase a retaining lip or thin the inner pocket floor. In the slimmer V19 trial, insertion remained clear but radial capture was weak and a floor probe entered the overcut. Hull only adjacent half-degree poses, union those local sweeps and test the full route, independent capture stops and actual floor material. Reset inherited mesh face relations before simplifying/exporting Boolean seams. These are geometry checks, not PETG strength measurements.

Bambu retains the `Sparse infill` extrusion-feature label even for an object configured at 100% infill. Identical geometry with a 20% versus 100% loop setting deposited 5.378 versus 7.444 g in the loop, while the feature label remained. Verify the object's setting and actual extrusion evidence; the label alone does not establish density.

## Smooth accessory transitions without changing fitted seats (2026-10-27)

V19's slim band met its wider fitted pads through a separate angular hull. The user requested a slightly wider loop and smooth edges. V20 uses a solid 9 × 4 mm band with 1.4 mm rounded edges and a continuous quintic 23 mm flare into the original seats, replacing the separate bridge. Both handed stems and all sixteen non-loop meshes retain identical STL bytes; only the loop and foot coupon change. Full lift/turn/removal, cap and control clearances still pass. Matched PETG slicing estimates 63.260 g versus V19's 61.305 g printed parts per left wand. Preserve the approved ergonomic anchors and interface geometry during cosmetic blending. These checks establish geometry, compatibility and sliced material, not physical fit, strength or comfort.

## Check loading paths and final combined solids (2026-10-28)

The main Shard lower assembly had a real 6.7 mm diaphragm at Z6.3..13 blocking the cell and sled, despite earlier seated-cell checks passing. It was normal model extrusion, not support. Full insertion checks must start outside the open cap and sweep the complete sled as well as the cell. R2's final exported meshes pass continuous conservative loading sweeps and 161 actual poses per hand. The nominal 20 × 6 × 40 mm cell is still provisional; physical fit and the real lead exit remain separate.

Structural material unioned after the switch cuts partly refilled post/pin clearances. R2 cuts the switch body, post/pin holes, offset socket floor relief and cable corridors from the final union of shell, rails, receivers and all neighbouring seats. Test all six seats and the socket's actual installation route. The purchased socket includes solder tabs: a centred offset-entry/alignment route was required, rather than assuming its nylon body could drop straight in. The bought switch's own clips retain an integral lip; removing the switch leaves the socket serviceable, with no fictitious independent latch.

The prior handle's nominal full route did not show a rigid collision, but its 0.22 mm per-surface fit, thin retaining features and 2.7 mm floating print-band offset were poor manufacturing assumptions. Do not conflate nominal motion with physical assembly. R2 uses broader captured hooks, a real common 9 mm bed plane and a separate indexed keeper. Check the complete loop, whole locked loop+key, hardware, cap and release path on both final exported stems. The cap must be removed during handle travel. Printed fit, force, wear and load capacity are unverified.

Canonical STL rounding exposed coincident Boolean seams in the final grip. A 0.01 mm surface simplification made the exported STL closed with every edge shared twice; then all functional checks were repeated on those exported meshes. Viewer and 3MF normal geometry now derive from those same checked STL triangles. Never validate one mesh and deliver another independently rounded vertex array.

The unchanged open cradle still needs its original back-flat/manual low-back printing supports. Multiple unsupported orientations produced actual floating starts. Keep clearly labelled print-support helpers distinct from functional cut geometry, and inspect actual support extrusion against all working passages. Do not change the established upper silhouette merely to satisfy an invented support-free preference.

A cropped fitting coupon needs its own first-layer check. R2's isolated switch lip had a cantilever, while a short actual grip section printed without floating starts. Its outer brim then crossed the crop-exposed service opening; the upper receiver coupon's brim also entered its open half-bore. Disable brim on those two cropped grip coupons and verify the sliced paths again. Keep full-grip brims separate; “no supports” alone does not establish a clear first-layer opening.

Full loading clearance and no floating starts still do not prove sensible unsupported roofs. A later layer-area review caught a residual 0.6 mm annulus between the cap core ending Z11.4 and general hollowing starting Z12.0. Its crescent roofs could require roughly 22.6 mm bridge chords even though the rectangular cell route was clear. A final radius12.2 cylinder over Z11.3..12.1 joins those cavities with overlap, preserves the actual threaded region, and leaves the lower hook's retaining lands and all motion stops. Review broad unbacked areas rather than treating a warning-free slice as manufacturing acceptance.

## Retina CAD viewers and small openings (2026-10-28)

A Three.js canvas with a device pixel ratio above 1 and `setSize(width, height, false)` can render outside its CSS viewport unless its display width and height are explicitly constrained. In the slim-loop comparison this made models appear cut off even though the labels and data loaded; check the actual rendered screenshot on the target display, not just the DOM.

A clear opening core with zero extrusion samples is meaningful only after confirming that neighbouring paths actually reach that region. The slim-loop study checks nearby path samples as well as intrusions, but those checks and warning-free slicing do not prove a bridged opening will print cleanly or a thin band will resist repeated flexing.

## Frozen native releases and public comment provenance (2026-10-28)

A native release patch can include private historical task identifiers in unchanged or removed comments. Preserve the exact raw patch privately as installation evidence, then derive the public archive by normalizing only the identified comment annotations in both retained before and after sources. Apply the derived patch without fuzz and compare every resulting file with the equivalently normalized frozen source. Keep the raw and public hashes distinct; never change executable code, the signed candidate or later canonical source to sanitize a publication.

An isolated copy on a volume whose name contains spaces exposed existing test helpers that pass `new URL(...).pathname` directly to Swift or Python. That value retains `%20`, so child processes reported missing source files even though the files existed. Use `fileURLToPath` when maintaining those helpers; a failed path lookup is not evidence of a firmware regression. For this publication, the required full gate runs from the canonical project path. Keep raw failed-run evidence separate from the final gate result.


## Sense: compare power deadlines against a current clock reading

The first Sense control installation connected and calibrated, then entered deep sleep while USB was still attached. A grip press brought it back with the System OFF wake reason. The loop captured `now` before commands refreshed `hostAt`; subtracting a newer timestamp from that older unsigned value looked almost 49 days old. Ending that session could similarly refresh `offlineSince` after the captured time and immediately satisfy the five-minute sleep test.

Refresh the clock after command/session transitions and use the bounded `wandElapsed` helper for short deadlines. A future tick counts as zero elapsed time; a real counter wrap still advances normally. The compiled C++ regression checks both the future-tick case and wrap, plus a genuine five-minute timeout. The corrected saved image then reconnected with its per-device calibration restored and sustained real USB pointer reports. A full intentional five-minute sleep/wake cycle and battery-powered Bluetooth remain separate physical acceptance checks.

## Sense: finish framing before callbacks can reset the connection

The native framer is mutable Swift state. Dispatching a rejected identity from inside its mutation could close the connection and reset the same framer recursively. Collect complete lines first, then dispatch them after framing finishes. Ignore callbacks from an earlier Bluetooth peripheral, and bound connection discovery time so a failed fallback cannot remain pending forever. USB command write failures must end the session rather than silently lose a sensor/sleep command or replay partial commands later. Source type-checking and canonical-program tests cover the implementation; arbitrary physical radio failures are not proven by those tests.


## Sense: verify radio startup and reset observer sessions on receiver restart

The radio needs an explicit one-peripheral, one-vendor-UUID service configuration that fits the core’s reserved SoftDevice RAM. The checked configuration uses one vendor UUID, a 2 KiB attribute table and the existing maximum-bandwidth connection profile. Record the return from stack startup, UART service registration and advertising data/start calls; expose those states over the existing USB diagnostic path. After this configuration was installed, USB readback reported stack ready, UART success and advertising active, and the Mac then discovered and received 397 real Bluetooth sensor packets. USB-powered radio testing alone does not prove battery-powered operation or native automatic fallback.

A receiver process restarts its numeric session counter. The dashboard observer must treat a new live boundary as a new local session even when that counter is again 1; otherwise the browser can reject the restarted sequence as old data. A searching boundary clears the mapping too. The regression covers a sequence of 900 followed by a restarted receiver’s sequence 1. The observer remains read-only and never takes hardware ownership.

## Sense: measure the transport before retuning motion (2026-10-29)

A 90-second passive Bluetooth capture of firmware c (dashboard observer, no second owner)
showed host arrival groups roughly every 30 ms. Restricting cadence estimates to adjacent
active frames in one session gave about 18% missing readings and a largest device-time gap
of 112 ms. These are estimates from received timestamps, not a sensor-side loss counter;
arrival groups alone do not establish the negotiated Bluetooth interval. The
Adafruit core's `BANDWIDTH_MAX` allows three queued notifications and `notify()` waits up
to 100 ms for a slot; meanwhile the IMU's data registers were overwritten. Firmware d sends
from its own task and merges unsent readings into the next frame; the receiver replays them
at their times. The same capture showed 286.7 deg/s clipping at the Puck's 245 deg/s
setting. Before d, macOS had not applied the advertised 15 ms preferred interval; d requests
it after connection, as Espruino does. Its effect is unmeasured until d is installed.

The Sense and Puck.js v2 use the same LSM6DS3TR-C. Espruino documents "divide by 134"
(full scale / 32768), but at 245 deg/s one count is 8.75 mdps (114.29 per deg/s). The first
Sense builds converted to 134 per true deg/s, which made the pointer 17% faster than the
Puck and every canonical threshold 15% tighter physically. Convert to Puck counts and put
requested extra sensitivity in an explicit gain, not in the unit conversion.


Keep queued readings within one button/sensor/session epoch. Snapshot button masks and
press counters together with a run, clear obsolete motion at each boundary, and reject an
older failed send after that boundary. One sender owns every BLE UART write, including
identity/battery/link reports, because a split notification can otherwise interleave lines.
Tests cover rejected cross-boundary retries and tuning after repeated maintenance reloads;
these source checks do not establish physical radio performance.

## Sense: the tuned pointer filter hid slow motion and zero error (2026-10-29)

Running the unchanged Puck filter and a direct conversion over two passive firmware-c Bluetooth
captures (restored gain) showed the tuned path passing 85–91% of total travel but only 8–26% of
motion below 2°/s; in 41% of the mixed capture's readings a direct pointer moved and the tuned one did not.
Its 0.2° slack delayed the first count of a steady 2°/s turn to 173 ms and swallowed 0.5–1°/s
entirely. The same filter is what made stop-to-click possible: hand tremor and a 0.2–0.5°/s
zero error kept direct counts flowing in that initial unfiltered path. Tuned stop
detection kept dwell and screenshot settling usable. Receiver 112 tried the posted-count stop
path described below; Ethan rejected its physical feel, so113 keeps the111 tuned stop signal. Both captures also implied about 18% missing sample intervals in firmware c
(not a sensor-side loss counter) and arrived in observed bursts every 30 ms; those transport limits are separate from the filter.

## Sensor motion is not evidence of actual pointer use (2026-10-29)

The observer's short in-memory history and a manually timed capture could contain
unused or sensor-only periods. Keep bounded private rolling readings automatically
while the receiver observer is running. Tag them with actual posted pointer event
and distance counters, follow/pause/recording state and pointer path. Select real-use
analysis intervals only from increasing posted travel in the same session; missing
context, resets and paused intervals establish no use. Never infer use merely from
gyro activity or a follow flag, and never label sensor logs as screen video. Writer
queues and rotation stay outside native input delivery, with explicit loss/error
metadata. Tests use private temporary files and exercise rotation, privacy and
actual-use selection; physical movement acceptance remains separate.

## Wand HUD packets need ordered delivery (2026-10-29)

macOS gives same-user Unix datagram sockets a small receive queue (`net.local.dgram.recvspace`
was 4096 bytes on Ethan's Mac, about 25 HUD packets). The receiver streams HUD motion every 30 ms and
used to ignore refused sends, so a briefly busy Agentic Mouse could silently lose a release's `park`
or `choose`; a lost `park` also left a held aim that later expired and closed the new page. This is a
concrete mechanism for "hold-aim-release on Utility sometimes does nothing", not a proven cause. The
receiver now resends refused state-changing packets unchanged and in order for at most one second
(native handling ignores repeated ids and sequences) and never queues motion; Agentic Mouse ends a live
held aim when its release arrives without the `park`.

## Sense pointer jaggedness has three measured parts (2026-10-29)

Recorded real pointing with firmware c over Bluetooth (about 16,000 follow readings):
- About a third of readings sat at or below the 2 deg/s stop boundary, and the hard on/off
  gate crossed about 5 times a second. A continuous knee keeps the stop without the jumps.
- Readings arrive 2–4 at a time every 30 ms (about 15% estimated missing). Each burst moves the
  pointer at once. Spreading bursts out would need roughly 20–30 ms of delay; only about 8 ms is
  approved, so this needs firmware d's 15 ms connection request, USB, or Ethan's decision.
- Per-reading change during slow pointing was about 5 counts rms, and 8 ms smoothing reduced it
  only to about 5.2: mostly hand tremor, not sensor noise. Removing more needs longer filtering.
Firmware c always sends one reading per frame, so merged-run replay never ran on it. Late
backlog (over 75 ms behind the best delivery) is now dropped from normal pointing, and a
pointer step never covers more than 25 ms. Simulation is not hand-to-screen latency.

## Menus pause default-mode timers; Puck and Sense readings compared (2026-10-29)

- Opening the receiver's menu-bar menu runs AppKit's event-tracking run-loop mode. A
  `Timer.scheduledTimer` stops there, so the Sense heartbeat stopped, the board ended its
  session after its 2 s host timeout (orange, no readings) and the receiver reconnected when
  the menu closed. The Puck has no host heartbeat, so it never showed this. Session-critical
  timers use `WandRunLoop.commonTimer`; the same applies to recording refresh, dwell clicks,
  held-button safety and gesture deadlines. Both repeating and one-shot timers keep their
  existing intervals. Main-queue work and dispatch timers already run. The regression also
  checks that a one-shot deadline fires once during tracking and is not replayed on close.
- An Oct 17 Puck diagnostic trace (receiver 1.2.37, about 26 s, raw readings) and recorded Sense
  pointing (firmware c, about 6 minutes) compared in true deg/s at equal spacing: slow-aim
  jitter 3.8 vs 3.4 deg/s and still noise 0.6 vs 0.8 deg/s. Units and spacing were normalized,
  but the motions, mounting and software versions were not a controlled paired experiment:
  these numbers do not establish equal hardware noise or rule out Mac scheduling. They do
  show different delivery and filtering. Puck notifications usually held one reading, with
  a median 15 ms gap (about 49 readings per second overall), while firmware c usually
  delivers three readings in bursts with a median 30 ms gap. Replaying the same
  Sense readings through the receiver gave 7.3 slow-aim direction reversals per second on the
  direct path versus 4.1 through the Puck's tuned filter, whose 0.2 degree slack hides tremor
  at the cost of slow-speed delay. A smaller slack trades delay for smoothness and needs Ethan's
  approval; it is not implemented.
- Gravity is sampled from one reading every 100 ms. Sense samples taken during a jerk, twist or
  near-vertical pose flipped the orientation basis by more than 30 degrees about every 27 s of
  pointing. Strict Sense acceptance (0.9-1.1 g, away from vertical, rotation at most 45 in
  program units) left 2 of 15 such flips and needs no waiting.
- Five isolated single-reading spikes of 40-170 deg/s occurred in about 37,000 Sense readings,
  none at button edges, with block data update already on. A filter that confirms these
  against both neighbours needs the next reading (lookahead). That extra delay is not
  implemented without approval; these traces alone do not prove data corruption.

## Scrolling returns to mouse follow again (2026-10-29)

The brief follow-off-after-scroll rule was an intentional user reversal, not a sensor or
gesture change. Ethan found that scrolling needs only a small stroke and a hold, so the wand
is not offset afterwards. A released completed scroll enables mouse follow again from either
prior state, with no follow-off confirmation state or frame suppression left behind.

## Held Middle on a wheel card adjusts it (2026-10-29)

Wedge selection used to treat every Middle hold as aiming, so a hold that began on Zoom
slid the outline to neighbouring wedges instead of changing Zoom. The native controller
now asks the coordinator, without pressing, whether the outlined card is a wand-adjustable
wheel (`wandAdjustableControl`), presses it on Middle down and consumes the gesture's later
click or release once it has adjusted. A press with no adjustment still resolves through the
same click/held-release rules, from the press already down, so dual cards never act twice.

## Posted-count stop-to-click experiment, reverted after physical feedback (2026-10-29)

The direct Sense pointer kept stop-to-click on the tuned filter's counts and intent, so the
two disagreed. A replay of recorded use through the real receiver classes, matching 128 of 134
logged clicks, showed both failures Ethan reported: visible stops without a click (the tuned
counts never armed, or kept trickling while the pointer was frozen by the quiet stop) and early
clicks while the pointer still crept or wobbled, which then disarmed the real stop on a small
target. In that replay, using the posted counts clicked every qualifying stop about 200 ms
after it, never during visible motion. Clicks were already plain left down/up events at the current position.


The replay result above did not establish acceptable physical feel. Ethan subsequently
reported that receiver112 was more erratic and explicitly requested the old click behaviour.
Receiver 113 retains 111's tuned counts and intent for stop-to-click; do not restore the
posted-count change merely because its synthetic check passed. New fine aiming is tested
against that retained stop signal, including coherent slow approach followed by one settled
click. Ethan reports113 working well; that is general feedback, not exhaustive gesture coverage.

## Sense: classify short Bottom releases in device time (2026-10-29)

A host hold timer can fire before a short physical release arrives over Bluetooth. Fixing
only the virtual button handler left a second host scroll-release path that could re-enable
mouse follow. Both layers now consult the physical duration: the virtual handler restores
a short tap's pointer classification, and the native held-scroll release rejects a short tap
as a completed scroll. Preserve the physical cutoff; do not hide transport timing by raising it.
Synthetic late-release and long-hold checks pass. Live readback also observed a 179 ms physical
tap leaving follow off. Keep actual button duration separate from arrival delay and genuine
long presses.

## Small-motion tuning needs real-use replay and physical feedback (2026-10-29)

Matching gyro chips do not establish matching host delivery or processed motion. Replay the
current-reading pointer and the retained stop signal together on bounded real-use captures.
Check still-hand creep, back-and-forth wobble and coherent slow approach, not only total
travel. A lower fine-motion floor improved slow response but crept while still; the selected
floor reduced frozen slow motion while posting nothing in the still-hand portion and
retaining all 228 baseline clicks in that recording. Do not generalise those capture metrics
to guaranteed accuracy or end-to-end latency. Keep approved tiny-motion confirmation separate
from normal-movement smoothing, and never replay historical pointer displacement.


## Preserve button edges independently of HUD visibility (2026-10-30)

A HUD close could clear the bridge's held flag before the physical release. The release was then omitted, and the receiver could consume the next gesture's release as belonging to the prior double click, leaving a held state that also blocked pointer motion. HUD visibility must not overwrite physical-held state. Retain the pending edge on the bridge, clear stale double-click ownership at a fresh down, and cover close-while-held followed by release and a new hold in the host regression. The regression passed and the matching receiver was installed. This proves a software failure path; it does not diagnose an electrically unobserved physical press.
## Mechanical previews need correct depth ordering (2026-10-30)

The carbon-rod accessory preview's painter-sorted triangles showed the rod through the board and hid purchased caps behind the frame, despite correct non-intersecting meshes. A per-pixel depth buffer over the actual exported triangles corrected those occlusion artefacts. Keep the preview's visibility evidence separate from the solid collision and sliced-path checks; attractive or opaque-looking reference parts do not prove fit.


## 2026-10-30 — Stale cursor reads between receive batches moved the pointer back

- Evidence: a passive posted-cursor capture showed own mouseMoved events 0.1 ms apart going 2103,746 → 2113,737 → 2134,719, then a +9,−8 move landing at 2112,738: the stale 2103,746 plus that delta. No click was involved. 51 of 222 captured own moves started from such a stale origin, all of them points the receiver had itself just posted.
- Cause: posted CGEvents reach the cursor asynchronously, and each separate `receiveText` batch read `CGEvent(source:nil).location` afresh. The per-batch `deliveryPoint` carry did not cover consecutive batches.
- Guard: `WandPointerOrigin` remembers the receiver's own posted points for 0.25 s. A system cursor equal to one of them is our lag, so motion continues from the latest posted point; any other location (physical mouse, warp, another app) is adopted at once. Recenter keeps its own settle. Only `currentPointerOrigin()` reads the system cursor. No delay, buffer, smoothing or replay. `tests/native-pointer-origin.test.mjs` replays the captured sequence through the real methods and fails with the old origin.
- Separately, the 300 ms stop-to-click repeat was disabled after Ethan requested less extra pointer behaviour. The captured movement-only jump did not establish repeat clicks as its cause.

## 2026-10-30 — Screenshot completion must not restore a hidden HUD

- The receiver parked its HUD for native screenshot capture, but unconditionally restored `hudSession` at capture end even when Agentic Mouse had already hidden it. That invisible session suppressed stop-to-click on every subsequent frame.
- Restore only a HUD whose native context remains active. Reuse the existing freshness check to close an expired, unheld HUD session during ordinary pointer frames as well as at the next Middle press; a missing callback must not require a special gesture to recover.
- Keep a real visible HUD's click suppression. The inert native screenshot regression covers both callback orders, actual pointer frames recovering the stale session, and a visible HUD still blocking clicks. Reverting each fix independently makes the corresponding regression fail.
- Log the click blocker when it changes, rather than printing every sample or attributing a missing generated click to application focus. Keep this diagnostic state distinct from physical-device acceptance.


## 2026-10-30 — Coherent tiny motion can still be unwanted drift

The fine-motion bypass let a directionally consistent, sub-threshold rate bypass the
quiet-stop floor after about 60 ms. A bounded synthetic replay of a broad sweep followed
by a 1.25 +/- 0.15 program-unit rate produced 231 counts during the quiet tail; removing
only the bypass produced zero, with the same first response to normal-speed movement.
Receiver 121 restored that floor while retaining the existing roughly 8 ms causal
smoothing, speed curve, gain, orientation correction, late-reading bound and original
tuned single-shot stop-to-click signal. Rates below the floor are intentionally suppressed,
including deliberate extremely slow aiming. Do not silently restore the bypass from an
older positive slow-motion trace: confirm both stationary behavior and physical aiming.

Regression tests must isolate the quiet tail after smoothing settles. Counting the tail
of an earlier fast stroke as successful fine aiming gives a false positive. Keep math
replay, captured-use replay and fresh physical acceptance separate; a synthetic quiet
trace is not proof that the user's hand was physically still.

A later offline comparison kept fractional pointer counts across quiet-floor
crossings without lowering the floor. It recovered a small amount of narrated
slow movement but also increased output in the still-like part of the same
recording. That was not a clean improvement, so it was not installed. Keeping
the floor unchanged alone does not prove a fractional-motion change is safe;
compare deliberate motion and independently labelled rest before shipping it.


## 2026-10-30 — Held scroll must receive the stroke before the hold deadline

The V3 controller accumulated input from the first held reading, but the raw-mode device callback suppressed the first 220 ms when follow was already on. A quick stroke followed by a still hold could therefore leave the controller with no starting stroke. The captured longer holds did not establish this as their cause; keep the reproduced edge case separate from the original field report. A virtual Sense reproduction produced zero raw reports during 192 ms of movement; controller-only simulations had missed this upstream loss. Enable early raw reporting only for native V2/V3 held scrolling; keep the existing no-output-before-hold rule. Separately, process an active Bottom scroll or drag before rejecting a HUD-only raw flag, so follow-off input is still usable by its owning gesture. Regression tests cover the virtual device boundary, unchanged V1 suppression and the actual native raw routing.

Ethan also changed the intended visible-HUD policy: showing the HUD must not suppress ordinary follow-on clicks. Gate on active HUD operation, not visibility, at both click arming and timer firing; follow-off, held Bottom, recording pause and screenshot ownership remain separate gates. The earlier ghost-HUD fix remains useful recovery, but its visible-HUD click suppression is superseded.

Physical follow-up: Ethan confirmed that normal held scrolling and follow-on clicking with the HUD open both worked on receiver 122. This does not establish every other gesture or the cause of each earlier failed scroll.

## 2026-10-30 — Slow review circles and input floors

Review uses `@NAV`, not the direct mouse lane. The ordinary HUD radial speed floor erased steady rotations below 1.2 degrees/second before the spatial circle classifier received them. Review now keeps its measured calibration noise floor but bypasses that larger HUD floor. This applies only while review tracking is selected; normal HUD navigation, direct-pointer quiet stopping, smoothing and gain retain their own behavior.

When removing a preprocessing floor, retest the complete input path, not only the downstream classifier. Full device-model replay exposed startup tremor being interpreted as an initial turn. Learning lateral noise from opening packets and requiring a complete initial segment fixed those cases. Tests cover slow clockwise/anticlockwise loops, reversals, stationary tremor and ordinary HUD rejection. Below the calibrated noise floor, intent remains indistinguishable from sensor noise; do not promise arbitrary-speed detection.


## 2026-10-30 — Retain the circle scale through a slow stop

Private slow-use replay reproduced the installed classifier's emitted step signs and packet positions. Four steps contradicted the surrounding circular geometry: a redirected pause reset the run with zero previous extent, or a chain of small about-faces retained only its latest tiny extent. A fraction of a degree of wobble could then qualify as a new reverse gesture. Keep the known spatial size across these internal restarts; do not infer a new tiny gesture merely because the old one paused. Better Git receives the resulting direction unchanged, so fix the classifier rather than reversing commands downstream.

Keeping the maximum size forever also blocks a genuinely smaller next circle. A bounded spatial sample can reduce that retained size only when it describes a near-complete, coherent smaller circle above the learned noise floor. In the drastic large-to-small regression, the first loop can establish the smaller size; subsequent loops must count in the correct direction. Clear that sample on accepted steps and mode resets. Do not add pointer buffering, replay, gain changes or a global linear-motion filter for this review-only problem.

Use private labelled raw recordings for observed regressions and publish only synthetic analogues. The pause-wobble fixture covers false reversals, a deliberate opposite circle and small noise loops; the resize fixture covers both directions and multiple radii. Replay agreement is not physical acceptance, and geometry-derived labels are inference rather than a human label for every packet.


## 2026-10-30 — Native scrolling needs a complete gesture lifecycle

Discrete line-wheel events do not carry the scroll phases Chromium uses for
trackpad-style edge navigation. Ordinary held and chord page scrolling now use
precise pixel events with CoreGraphics began/changed/ended/cancelled phases;
semantic HUD wheel commands and physical mice keep their existing paths.
Local AppKit conversion verifies both axes, a fixed gesture anchor and no
synthetic momentum. A process-targeted WindowServer delivery probe also preserved
the precise flag and all four phases at its own windowless AppKit receiver. This does not prove a particular app accepts synthetic
history swipes; that still needs a physical application check.

Cancel before a native drag, action pause, lost telemetry, reset or shutdown.
A physically short tap whose release arrives late must cancel any open native
scroll instead of ending it as an accepted history gesture. The new lifecycle
regression failed before that correction and passed afterward. Keep pointer
filters, sensitivity, click timing and the existing hold controller separate
from the native event transport. Log one begin and one end or cancellation,
never every movement.

The device reports `@BOTTOM 0` before its two-button chord's `@SCROLL E`.
When no held-scroll session is active, Bottom release must leave the chord's
native gesture alone until that end marker. The ordered regression cancels
prematurely before the ownership guard and ends normally after it.


## 2026-10-30 — Restore the scroll choice captured before a temporary hold

A mouse-button press can temporarily turn follow on before a two-button chord begins.
Capturing the state at chord start alone therefore loses an off choice. Capture it
on the first mouse-button down, before the temporary enable; retain that value if
the gesture becomes a chord. Only a completed physical scroll release restores it.
An ordinary tap, drag, cancelled gesture or late short release keeps its own rules.
The release regression exercises both prior choices and both raw/edge arrival orders.
This supersedes the older always-enable release policy, not its historical record.


## 2026-10-30 — A high-speed extension must preserve the whole old curve

The first larger scroll range passed all existing motion profiles but started its
boost at 60 angular units/s, below the old 75-unit cap boundary. Those profiles
peaked below the changed range, so passing them did not establish unchanged
ordinary scrolling. Ethan reported that the normal feel had changed and the
original curve was restored. Compare the full previous speed mapping, including
the old cap plateau, when adding a stronger-stroke extension. Retain physical
feel acceptance separately from the mathematical and motion-profile checks.

## 2026-10-30 — Horizontal native swipes need their own measured gain

Ethan saw the native Back/Forward edge indicator start without completing the
gesture. The held-scroll path used the vertical speed for horizontal output;
the independent chord already had a horizontal multiplier. A horizontal-only
gain now increases deliberate held strokes while fine strokes retain the old
mapping. Fade the gain out before the diagonal boundary so crossing that
boundary does not create a speed discontinuity. Vertical and diagonal output
must match the old path sample for sample, including the high-speed extension.

Test the held controller and native transport together: first output timing,
both directions, reversal, release, lost telemetry, precise event phases and
no added buffering or replay. A larger synthetic event distance does not prove
that a receiving app accepts a history swipe. The app still owns that choice;
real horizontally scrolling content also receives the larger horizontal gain.
Keep physical Back/Forward acceptance separate from these checks.


## 2026-10-31 — A generic app boundary is not a draggable surface

A custom scrolling list may expose `AXList → AXWindow` without an `AXScrollArea`.
The old classifier returned drag at the window boundary, which could consume a
scroll gesture as a mouse drag. Treat generic window/app boundaries as unknown
and keep the scrolling fallback. Only positive draggable roles or the explicit
tap-then-hold gesture select a native drag. Keep bounded app-bundle/role/error
telemetry for diagnosis, without window titles, messages or field values.
The regression harness verifies this fallback; it does not prove which native
or browser WhatsApp surface caused an earlier user report.

## 2026-10-31 — Retain each deliberate same-direction page flick

The old restroke temporarily kept the prior speed but replaced it with the new
stroke's smaller peak as deceleration began. Each qualified same-direction page
stroke now captures its prior speed once and adds its own increment, capped at
the page limit. Do not add an increment per sample or bank resting noise. Tests
cover repeated equal flicks, holding still, tremor, reversal, fresh holds and
release. Horizontal history swipes keep their separate curve and lifecycle.


## Sense wireless updater: keep the handoff and result observable

A successful authorization does not establish that the board entered its bootloader.
Keep a deadline from GO to disconnect, then a separate connection/transfer deadline.
While the updater owns the Bluetooth central, stop ordinary USB discovery and normal
reconnection so a newly booted application cannot claim a second session before the
transfer result is processed. Treat an activation-write error as a failure, even if
a later disconnect arrives. The executable fake-Bluetooth test runs the actual link
and transfer classes through these boundaries; it is not physical radio evidence.

The receiver's status file previously cached only ordinary connection state, so
updater progress and refusals could disappear despite calls to `status()`. Include
the exact serialized update status in that cache key. A restarted receiver also has
no in-memory record of an earlier transfer: permit an explicit board/running/target
matched acknowledgement for either installed or not-installed pending results.
Never initiate a transfer or clear an earlier result merely because a board
reconnects, and retain the failure when acknowledging an unsuccessful attempt.


## 2026-10-31 — Verify transport length and bootloader behavior from real limits

BLEUart.write can report the caller's full length even though the characteristic
notifier clips it to its configured maximum length. Extending identity JSON beyond
that length broke Bluetooth identification while USB still worked. Split control
messages in the existing sender task by the negotiated payload limit, keep each
line contiguous, and test with a fake transport that reproduces the truncation.
USB success does not qualify the Bluetooth identity path.

The bundled Sense bootloader file labelled 0.6.2 contains version 0.6.1. Both
reviewed versions compile single-bank DFU and erase the running app before receiving
its replacement. A conservative half-size image cap is not a backup bank. State
USB recovery requirements explicitly; keep source review, actual board identity,
successful wireless transfer and interruption recovery as separate evidence.

## 2026-10-31 — Prepare firmware packages away from live input

The first wireless request reached its challenge state after a three-second
preparation gap, then the unchanged telemetry watchdog disconnected it before
authorization. The same firmware reconnected; no image transfer had started.
Package decoding and key reads now run outside the main input queue. Completion
rechecks the exact connection generation, board, transport, key confirmation and
fresh battery before authorizing anything. Cancellation keeps the worker slot
occupied until it returns, so reconnects cannot accumulate readers or reuse an
old result. Logs distinguish worker time from return-to-main time.

The next physical attempt prepared in about 12 ms and completed the firmware-7-to-8
wireless update, including Bluetooth reconnection and durable result confirmation.
That proves this tested path; it does not establish which individual operation
caused the earlier gap or prove recovery after an interrupted transfer.

## 2026-10-31 — Early sideways intent must own the short release

Five clean recorded swipes first emitted native scroll events 224–230 ms after
the held packet arrived. The existing 220 ms hold gate, followed by the output
tick, explains that start delay; it does not establish a stop-classifier failure.
The receiver now permits only a clear first horizontal stroke to qualify early,
after the target is resolved to scrolling. Ordinary taps, page scrolling and
dragging retain the original gate, with no new pointer delay.

Early qualification must also consume the press through release. Otherwise a
sub-220 ms swipe can be cancelled as a tap or join exit-click, double-click or
triple-click handling. Clear those recognizers at qualification, suppress the
endpoint click, preserve completed-scroll follow restoration, and reset on the
next hold. Native phase, release, drag, page, tremor and knock regressions passed;
26 short context presses rejected the early path in approximate recorded-input
replay. Missing historical calibration and gravity timing limit that replay;
faster physical Back/Forward and abrupt-stop acceptance remain unverified.

## 2026-10-31 — Page sensitivity must not retune gesture recognition

When the current flick-and-hold behavior feels right and only page sensitivity
needs increasing, scale the page output curve and its cumulative ceiling together.
Keep stroke thresholds, average, reversal/recoil handling and the separately
tuned horizontal history gesture unchanged. Receiver 143 uses 1.3 times page
output and a 1560 lines/second output ceiling. Replay checks compare identical
input histories: every stroke, reversal and added flick occurs at the same time;
horizontal events remain identical. This is synthetic regression evidence;
physical preference for the stronger speed still needs user confirmation.
