# R44 joined finger-rest trial review

The digitally checked trial is the main Key_Carrier alone:
`exports/key-holder-only/R44-Key-Holder-Only-print-only.3mf`,
SHA-256 `92aa2fbb89d0bd3de18292a2c7c4d28cf0c7234ebfedf4372b8d9ccf97141fa2`.
Estimate: 7604 seconds (about 2 hours 7 minutes), 17.15 g,
including native support, cuttable pads and the Smooth-timelapse tower.
The complete nine-part assembly remains in the viewer; this job does not
print the touch bracket, its clips or the other holders.

## Geometry, scale and assembly

- The four outer Choc seats are R42 + 1.42 mm, 0.30 mm below R43.
  Reference cap tops are Z21.34; the released touch top remains Z21.6416.
  Two keys are the top row and three are the bottom row.
- Rounded spines join the old contact rows; a new middle branch on each
  side joins the inner leg and outer return. Contact bars are 1.90 mm
  diameter. A 2.30 mm right riser joins usable central frame stock; the
  matching left landing is occupied by the socket and solder route.
- Both complete new members and all their pre-union bonds are checked.
  Protected OP1, hinge, stop and rod geometry changes only by numerical
  residue (3.1e-14 mm3). Complete lowered switch/socket/solder routes
  remain in the actual opening checks.
- Exported rod and OP1 reference meshes agree with source bounds, seated
  transforms use unit scale, and the viewer uses raw millimetres. The rod
  is 8 mm diameter. Each viewer keycap follows its own switch pose through
  `assembly-data.mjs` composition, including the whole-rod view.
- The closest metal socket-barrel gap is 0.900 mm. The other two are about
  0.902 and 1.163 mm. The fixed white housing is 2.565 mm clear; its lower
  fitted plug has only 0.3135 mm at the rod shoulder, despite the -25 degree
  board yaw. `reference-clearance.png` shows the end-on distinction.
- Bought PCB/connector envelopes and mounted cap height are photo-derived
  estimates, not physical measurements. The displayed relationship needs
  the matching R42-or-later lower-seat DFRobot bracket. R41 is 0.95 mm higher.

## Actual initial and reopened paths

Both `initial-audit.json` and `slice-audit.json` passed with empty failure
lists. Each names its own archive hash. `reopen-checks.json` confirms the
same effective settings and object recipes; `print-only.json` confirms
unchanged reopened G-code in the selected print package. The trial review
binds the six current drivers and every retained artifact. `print-checks`
records the selected reopened slice, not the initial archive.

- All 209 layers checked; no floating or missing printed components.
- First-layer contact 1035.446 mm2, and all eight pad ties joined.
- All working and loading/removal routes passed. Supports remain excluded
  from the rod grip, clip mouths and complete hinge bores.
- Weakest complete critical section: 0.9127
  against the unchanged 0.9 gate. The right complete rest is
  0.9178; the left is
  0.926.
- All six selected roof/enforcer regions pass their actual backing and
  gap checks, including both new middle branches. Support removal
  reachability is 0.99865
  centrally and 0.99732
  at the guards. This is a fragmented-support access model, not a physical
  demonstration of easy cleanup.
- Actual startup waits for 245 C nozzle and 60 C bed, preserves the checked
  A1 mini routines and ends with heater targets off. Smooth timelapse and
  its wipe tower are enabled. Actual deposition is inside the 180 mm bed;
  the tower is over 76 mm clear of the carrier/support footprint.

## Independent review and findings

Independent Claude Opus 5.5 reviewed the frozen source, current geometry,
original screenshot, actual first slice, support settings and scale evidence.
Its scoped follow-up accepted the repaired first archive after reading its
full audit and verifying source hashes. It viewed the clearer current
middle-branches image and confirmed that the viewer composes moving caps.
The parent separately verified the final reopened archive's own full audit,
recipe equality, source/export bindings and byte-identical packaged G-code.
Opus did not review the final reopened archive; its reported first-archive
coverage is not presented as that final check.

### 1. Fixed — R1/R2 guard attachment underfill [Claude Opus 5.5]

**Severity / priority:** High — P1; blocked the rejected trial.

**Change required / fix effort:** Small, about 5–10 lines plus re-slicing — plate44.py, single44.py.

**What happened:** Two old guard attachment sections became underfilled in
R44's actual slice. The early new-member checks alone did not catch them.

**Example:** Actual deposited coverage was 0.7039 and 0.7373 at the worst
layers. A two-archive same-geometry probe found identical failures before
and after the member-shaped selectors, ruling those selectors out as the
measured cause. The exact path-planning cause remains unproven.

**Fix:** Selected variable-width Arachne walls as an actual global process
setting, retained local member-shaped solid-fill settings and added both
whole root witnesses to the early gate. This was a new whole-carrier wall
setting. Both complete final audits now pass those roots at 0.9396/0.9209;
no witness or threshold was reduced.

### 2. Fixed — Complete right finger-rest underfill [Claude Opus 5.5]

**Severity / priority:** High — P1; blocked the earlier slice.

**Change required / fix effort:** Small local process repair plus re-slicing — plate44.py.

**What happened:** Join-only settings left a section between the joins
underfilled even though the individual attachments passed.

**Example:** The complete right member's actual worst-layer fraction was
0.8838. A complete-member witness caught this; checking only attachment
volumes would have missed it.

**Fix:** Added narrowly expanded, member-shaped native selectors for the
complete new members, retaining solid fill and variable-wall settings,
then explicitly enabled the global wall process as described above. This
extends the established pattern of native join selectors in R43 plate43.py
and R44's existing attachment selectors, using the member shape rather than
filling a large bounding box. Final right-member coverage is 0.9178.

Confirmed R44 finding attribution: Codex 0, Opus 2, shared 0; both fixed.
These are slice failures found before printing, not diagnosed causes of
any earlier physical failed print.

## Manual checks and physical boundary

The parent loaded R44 Keys, its underside and complete-rod views in the
live viewer, verified paused step-one startup, checked the cap-height view
and left the new underside available. The clear rear view shows joined
spines and middle branches on both sides. The existing normal Studio
window on the preferred top-right screen loaded the exact selected file
and showed 209 layers, 17.15 g and 2h7m. One GUI instance remained. Studio
was activated immediately for its checked import warning; previous focus
restoration was attempted without moving or fullscreening the window.

No Send/Start or heating command was issued. Wait until Ethan confirms he
is home, the failed plate/nozzle are clear, the plate is seated and hands
are away. Fit, solder clearance, support removal, PETG layer strength,
snap force, fatigue and comfort remain physical trial checks. The fingertip
sphere test covers Y -0.5 through 11.5 only; it does not prove comfort in
every part of the guard. The roughly 17 mm left supported branch and the
sloping riser need particular physical inspection after cleanup.
