# R17 printability and physical acceptance

Candidate: `exports/R17-A1-mini-PETG.gcode.3mf`, SHA-256
`d110a43a1153f0ef095cb5e9e054bee555330169fccb3aeef60ab375cad6d2ba`.
Independent Claude Opus 5.5 review and a focused post-repair follow-up cleared a
monitored complete-part trial, with one nonblocking short-bridge issue below.
No physical fit, strength or lifetime acceptance is implied.

## Per-part coverage

| Part | Working spaces and complete routes | Print and likely weak points |
|---|---|---|
| Battery holder | Conservative LP402025 reserve, loading route, sprung gate, rod bore/slits and wires | Continuous channel, ring roots/skirt, ramped gate guide, six fused anchor necks |
| Battery end gate | Guide, detent and removal route outside pouch reserve | Broad-face spring legs and free slit, two anchor necks; force unmeasured |
| XIAO holder | Official rounded board outline, tilt/slide loading, all fourteen provisional wire exits, USB, component/underside reserves, plate grooves, rod bore/slits | Corner ledges, widened rails, keel, posts, far fingers, ring roots and six anchor necks |
| XIAO top retainer | Insertion/removal, board-corner contacts, component and solder clearance | Grooves capture plate, spring detents, two anchors; short second-layer spring bridge needs physical inspection |

The successful R16 key carrier is unchanged and absent from this repair plate.
Actual solder, wire gauge, assembled Sense underside and bought cell dimensions
remain unmeasured. Catalogue geometry cannot establish their physical fit.

## Bound evidence

- `exports/manifest.json`: exact source, mesh and unchanged-key hashes.
- `exports/geometry-checks.json`: geometry, loading sweeps, rod-arm freedom,
  all modelled component and wire regions. Passed for the final manifest.
- `exports/anchors.json`: labelled removable meshes and neck plans.
- `exports/R17-A1-mini-PETG-print-checks.json`: four-part layout, recipe,
  effective settings and exact prepared archive hash.
- `exports/slice-clearances.json`: actual CLI bead footprints in working spaces,
  all fused neck layers, section/track/load-path probes and classified broad
  overhangs. No working-space violations, floating or missing components or
  unclassified broad overhang rows. Neck centre-line coverage is 1.0; the
  minimum gap elsewhere is about 0.991 mm. The short spring bridge below is
  outside the broad-overhang detector's coverage; the pass does not erase it.
- `exports/roundtrip-checks.json`: delivered archive reopened/re-sliced once;
  effective settings and modifier bounds match. New paths independently pass,
  although normalized G-code is not byte-identical after mesh float rewriting.
- `exports/view-checks.json`: current selected views bound to final STL hashes.
- `exports/trial-slice-checks.json`: compact public record of the actual GUI
  archive, settings and completed actual-path check. Raw job/device records stay
  private. A GUI sliced-file export omits source meshes; its paths were audited
  against the reviewed geometry at its original placements. G-code object IDs
  were mapped by verified path bounds, not assumed to survive a reload.

Battery body sections from 4 to 28 mm form one connected island on all 120
sampled layers, compared with R16's median nine. This improves the load path;
it is not a measured breaking-force improvement.

## Independent review disposition

The initial review identified missing complete wire-exit coverage, a flat guide
cap above air and rigid retention without a designed spring. The final repair
uses continuous pad-to-external wire corridors, a guide cap growing inward at
about 0.2 mm per layer, free spring legs and small detents. The focused reviewer
confirmed these changes against the actual slice. Reset-button clearance is
only nominally 0.23 mm; lateral board movement and actual solder require a check.

One nonblocking defect remains in the top retainer: its bed-side 0.2 mm relief
narrows the 0.85 mm spring arms to about 0.45 mm, which the slicer omits on layer
one. Layer two spans about 3.5 mm across a 0.2 mm air gap to the bump islands.
The reviewer explicitly accepted this for a monitored trial: the bridge is short,
later arms print about 0.9 mm wide, and the 0.55 mm slit exceeds the nominal
0.25 mm spring movement. Check both bump tips and free arm movement after cooling;
use removable tape if retention is poor or a tip is damaged. This is not a claim
of measured clip force, fatigue life or reliable first-layer bridging.

The unrelated modified R16 archive is preserved and excluded from this delivery.
Two archived-R16 tests fail against that existing local mismatch; the committed
R16 archive contains its registered G-code. R17 does not depend on that modified
archive. No unrelated full software test rerun is required for this CAD delivery.

## GUI and physical trial

The final project was opened and re-sliced in the existing Bambu Studio instance.
Studio reset normal 0.6 mm travel lift to 0.4 mm Auto; this was corrected before
export and send. The actual GUI archive keeps A1 mini 0.4 mm, textured PEI, Generic
PETG, 255 C / 70 C, 0.2 mm layers, three walls, 20 percent infill, fused anchors,
no automatic supports and the checked local slow modifier.

The GUI send selected the external PETG spool, timelapse, bed levelling and flow
calibration. The printer accepted the job, entered preparation and the live
camera was resumed and observed live. This dated start record is not live job
status and does not prove extrusion, adhesion or completion.

Both the archive metadata and GUI report the instant/traditional-timelapse
surface-quality warning. It may introduce surface marks; it is not evidence that
recording is disabled. Smooth mode has different travel/tower requirements and
was not substituted during this trial. A playable recording remains unverified.

After cooling, cut anchor necks flush from the flange side at fixed faces. Do not
lever against flexible ring arms. Check adhesion through the complete height,
anchor cleanup, rod grip and removal, battery fit without pouch compression,
board/solder/wire clearance, accessible reset/USB, gate and plate retention, and
repeated handling without cracks. These physical acceptance checks remain open.
