# R43 raised-key trial review

The selected digital first-fit trial is the main key carrier alone:
`exports/key-holder-only/R43-Key-Holder-Only-print-only.3mf`, SHA-256
`f99bb492ac574f441f07f98d5525e7ce1f12f14f10c6b38ba847e71eb52a7bd8`.
Its estimate is 7324 seconds (about 2 hours 2 minutes) and 17.03 g, including
native support, cuttable adhesion pads and the Smooth-timelapse wipe tower.
Only Key_Carrier is a functional printed part in this job.

The parent reviewed the five sources, complete assembly recipe and current
exports. Independent Claude Opus 5.5 reviewed the changed geometry, actual
first slice, both user screenshots and the assembly height comparison. A
scoped follow-up confirmed the local clearance repair on the new first
slice. Opus finished before the final reopened reports appeared; the parent
separately verified the reopened archive, all own-path checks, matching
settings/object recipes and byte-identical packaged G-code. No Fable call
was made during this revision's review.

## Checked geometry and assembly

- The four outer Choc seats rise 1.72 mm. Nominal keycap tops are 21.64 mm
  above the rod centre; the released touch reference reaches 21.6416 mm.
  This is reference-model alignment, not a physical height measurement.
- The rod, OP1 assembly, touch bracket, hinge and stop positions are fixed.
  Their protected CAD geometry differs by only numerical residue (3e-14 mm3).
- Complete bought switch/socket and solder loading routes move with their
  seats. All 36 key-space early checks and the complete path audit pass.
- Both Choc switches and sockets move together in every animation pose.
  The complete viewer keeps all nine assembly parts and earlier revisions.
- The OP1 gold socket barrels remain nominally 0.90 mm above the rod. The
  neighbouring white harness plug has only 0.3135 mm clearance; lowering the
  entire assembly another 0.15 mm reduces that plug clearance to about
  0.198 mm. The screenshot alone cannot measure the real hardware gap.
- Displayed flush alignment requires the matching R42/R43 lower-seat touch
  bracket. An older R41 bracket puts the board about 0.95 mm higher. This
  carrier-only job does not manufacture the matching bracket or its clips.

## Actual final slice

Both initial-audit.json and slice-audit.json pass without failures. Their
hashes, source/checker bindings, layout and selected archive are retained in
trial-review.json. Reopen-checks.json confirms identical effective settings
and per-object recipes; print-only.json binds the packaged G-code.

- All 209 carrier layers were checked. No floating or missing components
  were reported; all eight first-layer pad ties are joined. First-layer
  contact is 1044.633 mm2.
- All nominal working and complete loading/removal routes are checked
  against the actual bead footprints. Native support is absent from the
  rod grip, clip mouths and snap-hinge bores.
- The weakest complete critical section has a minimum deposited fraction
  of 0.9128 against the unchanged 0.9 gate. Raised-seat bonds range from
  0.9534 to 0.9651. The complete reinforced web reaches 0.9563.
- Required support roof backing, vertical/sideways gaps, pad cleanup and
  removal access pass. Reopened support removal reachability is 0.99900
  for the central openings and 0.99687 for the outer finger guard; this
  does not prove easy physical removal.
- The recipe retains the 0.2 mm support gap. New platform-edge partial
  overhangs are connected strips roughly 1.4 mm wide, not detached starts.
  A 0.29 mm2 island starts on support. The local socket relief additionally
  leaves about 0.48 mm2 of connected lip reaching about 0.3 mm past the
  preceding layer. Opus found no blocking repair issue; underside finish
  and small-nub cleanup remain physical trial checks.
- Effective startup commands wait for 245 C nozzle and 60 C bed, retain the
  checked A1 mini machine routines and finish with heater targets off.
  Smooth timelapse and its tower are enabled. Actual deposition stays
  inside the 180 mm bed, with over 76 mm tower clearance.

## Review findings

### 1. Fixed — Remove the socket-corner fin [Claude Opus 5.5]

**Severity / priority:** High — P1; blocked the initial ready-file claim.

**Change required / fix effort:** Small, roughly 5–10 lines — holder43.py,
single43.py.

**What happened:** The intersecting scaled and straight-axis socket cutters
left a 0.055 mm underside fin. Its outer-wall beads entered the maximum
key_2 socket and the soldered-socket insertion route.

**Example:** The rejected slice recorded 19 outer-wall samples in each
route, near assembly (28.716, 3.65, 9.337). Light sections of the exported
solid established the fin; the strict actual-path audit caught its beads.

**Fix:** Removed that non-interface corner below Z9.6 while retaining the
mounting collar above Z11.64 and its load path. Expanded the early check to
all 36 key spaces. This follows the established pattern of local socket
relief in the R22 carrier and R43's other socket-approach relief, while
keeping nominal spaces and acceptance thresholds unchanged. Both final
initial/reopened audits pass.

### 2. CAD bond-volume diagnostic omits the relief [Claude Opus 5.5]

**Severity / priority:** Low — P3; reporting limitation, no established
printed collision or failed material section.

**Change required / fix effort:** Small, roughly 1–5 lines — holder43.py.

**What happens:** The nominal seat_bonds CAD volume omits subtraction of
the final relief. Its key_2 value is an upper bound, overstated by at most
about 1 mm3. The deposited-material audit already intersects that witness
with the actual final solid, so it does not credit removed material.

**Example:** The CAD report lists about 161.30 mm3 for that bond. The
independent mesh inspection identified the small removed overlap; the
actual final path audit measures a minimum printed fraction of 0.9651.

**Fix:** Documented the bound and retained the actual-solid deposition
measurement as this trial's acceptance evidence. Subtract the relief when
the CAD diagnostic is next regenerated; do not interpret this bound as an
exact surviving volume. This follows the established pattern used by the
actual-solid intersection in carrier_checks43.py and its R42 checker.

Confirmed finding attribution for R43: Codex 0, Opus 2, shared 0. The tiny
remaining nub and short lip are physical-finish observations, not additional
confirmed bugs or a demonstrated cause of previous failures.

## Manual checks and physical boundary

The parent loaded the current R43 key assembly and complete rod assembly
in the live viewer, checked paused step-one startup, selected the height
comparison, and saved the displayed current alignment. The normal existing
Studio window loaded the selected R43 print-only file and showed 209
layers, 17.03 g and 2h2m. One Studio GUI instance was present. The preferred
external screen was disconnected; the already-authorized MacBook fallback
was used without fullscreen or resizing.

Extra native preview clicks could not verify foreground ownership and were
not sent. Detailed GUI layer scrubbing remains unverified; it is not a
substitute for the retained complete actual-path audits. Newer foreground
app choices were preserved. No Send/Start, heating or hardware command was
issued.

Physical fit, solder clearance, support cleanup, layer bonding, snap force,
fatigue and comfort remain unverified. Wait until Ethan confirms he is
home and the failed plate/nozzle are cleared, the plate is seated and his
hands are away. These digital results support a controlled first fit after
that confirmation; they do not guarantee success.
