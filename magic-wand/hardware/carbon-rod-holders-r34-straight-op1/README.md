# R34 straight OP1 board

[Watch the assembly](../carbon-rod-holders/assembly/?version=r34&component=keys).

The OP1 mouse-switch board runs parallel to the rod and sits 7.45 mm to
its right to clear the underside connector. The board's underside stays
9.2 mm above the rod centre. The DFRobot touchboard remains centred on
its rear snap hinge. The bracket pusher meets the switch in its new
position, and the two travel stops limit the touchboard's movement.

The six crosswise finger guards and their rod and edge attachments
carry over from R33. The optional [battery spacer](../carbon-rod-holders/assembly/?version=r34&component=battery)
uses 15 angular vents while keeping the same 0.4 mm thickness and
outside shape. The [complete plate list](complete-assembly.json)
includes the keeper clips, battery door and 12-wire cable clip.

- [Sliced A1 mini first-fit plate](exports/R34-Complete-A1-mini-PETG.gcode.3mf)
- [Editable Bambu Studio project](exports/R34-Complete-A1-mini-PETG-layout.3mf)
- [Original and reopened print checks](exports/print-checks.json)

The ten parts slice at 250 °C nozzle and 60 °C textured PEI with Flashforge
HS PETG Metallic. See the
[Metallic Red material reference](../carbon-rod-holders/flashforge-hs-petg-metallic-red.md)
for the exact SKU, published limits and heat tests. Studio estimates
1 h 44 min and 17.0 g, including the
wipe tower for Smooth Timelapse. The original and reopened slices passed
the checks for working openings, guard and stop joins, and all 15 spacer
vents. Remove the labelled pads and brims before assembly.

On the key carrier, approach the narrow ties from the pad side and cut
their exposed middles. The two ties beside the opening have carrier
material directly behind them. Leave a small stub for cleanup to keep
the cutter away from the wall. On the 0.4 mm spacer, flex the brim
to peel it away while supporting the spacer.

The sliced pusher tip retains at least 95.7% of its checked section.
The model gives the switch 0.48 mm of travel before the stops touch.
The [Omron drawing](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/5389/D2FC_Datasheet_EN.pdf)
allows up to 0.50 mm before the switch clicks. Confirm the installed
switch clicks and releases without forcing the bracket against the stops.

`assembly34.py` regenerates the edited meshes, [fit checks](exports/geometry-checks.json)
and matching animation assets. Prepare the plate with
`../carbon-rod-holders-r32-complete-assembly/plate32.py --source . --scratch <directory> --slice --filament-profile "Flashforge HS PETG Metallic"`.
Run `audit34.py` on the sliced archive through the repository's geometry
budget runner. Fit of the actual electronics, hinge flex and comfort
need a printed trial.

## Pad-area retry

The first full R34 print detached during printing. The recording shows a
rear central part moving before loose extrusion appears. It does not
establish whether the pad peeled, a tie broke or the nozzle struck it.

The [pad-area retry](exports/retry/R34-Pad-Retry-print-only.3mf)
keeps the ten functional parts, their orientations and their positions.
The DFRobot bracket's two removable pads grow from 38.41 to 55.07 mm² of
combined contact area, a 43.4% increase. Their outer radii increase from
2.4 to 2.9 mm, with the inner edge and thin breakaway ties preserved.
The pads stay 0.4 mm thick.

- [Editable retry plate](exports/retry/R34-Pad-Retry-A1-mini-PETG-layout.3mf)
- [Complete archived project and toolpaths](exports/retry/R34-Pad-Retry-A1-mini-PETG.gcode.3mf)
- [Retry print checks](exports/retry/print-checks.json)
- [Original retry slice audit](exports/retry/audit.json)
- [Reopened retry slice audit](exports/retry/reopened-audit.json)

Both slices passed the working-opening, deposited-joint and first-layer
checks with no slicer warnings. The closest material envelopes remain
5.25 mm apart, including the specified brims. The retry uses the same
250 °C nozzle, 60 °C bed and Smooth Timelapse settings, with an estimate
of 1 h 43 min 49 s and 17.0 g. Adhesion and removal still need a physical
trial. A larger pad is a controlled change, and does not prove the cause
of the previous failure.

The bracket itself has two small first-layer contacts totalling 7.13 mm²
in the mesh and 6.87 mm² in the deposited paths. Its sections remain
separate through 7.7 mm and join across the body at 7.8 mm. Watch this
early stage on the retry. If it moves, inspect whether the round pads
lifted too or remain attached with broken ties. Fable 5.2's review
approved the physical trial with this distinction recorded in the checks.

`retry34.py <scratch-directory>` regenerates this plate and records the
source hashes, new pad area and unchanged tie overlap. Remove its pads
using the same accessible thin ties described above.

The print-only package opens the checked toolpaths directly. Its G-code
matches the audited archive byte for byte. Use the editable plate when
changing geometry or settings, then slice and check it again.

## Two-part perforated-pad test

This diagnostic plate has just the key carrier and DFRobot hinge bracket.
Their functional meshes, poses and pad tie geometry carry over from the prior
plate. Each of the six 0.4 mm tear-off pads has two 2.6 mm holes. Net CAD pad
contact area increases from 227.03 to 382.81 mm² on the carrier and from 55.07
to 118.43 mm² on the bracket. The bracket pads clear the touchboard space.

Configured speeds and acceleration, 0.20 mm layers, 250 °C nozzle, 60 °C
textured PEI and Smooth Timelapse carry over. To correct two weak sections
found in the slice, the key carrier uses four walls instead of three from
38.8 to 41.85 mm, and the bracket outer wall lines widen from 0.42 to 0.44 mm
from 39.4 to 40.235 mm. Those changes are local to the upper ends.

The deposited paths preserve all 12 pad holes through both layers, join all
six pads and pass the critical-section and fit-space checks. The print-only
file contains the audited toolpaths. The separately re-sliced editable file
also passed its audit. The estimate is 1 h 17 min and 11.60 g, including the
timelapse tower. Printed adhesion, fit and strength need a physical trial.

- [Print-only test plate](exports/perforated-pad-test/R34-Perforated-Pad-Test-print-only.3mf)
- [Editable test plate](exports/perforated-pad-test/R34-Perforated-Pad-Test-editable.3mf)
- [Pad dimensions](exports/perforated-pad-test/pad-geometry.json) and [hole checks](exports/perforated-pad-test/hole-checks.json)
- [Exact slice audit](exports/perforated-pad-test/audit.json) and [reopened slice audit](exports/perforated-pad-test/reopened-audit.json)
