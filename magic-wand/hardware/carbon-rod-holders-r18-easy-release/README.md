# R18 easy-release battery and XIAO repair

R18 responds to the physical R17 trial: the XIAO holder broke while its anchors
were being removed, the anchors were too strong, the battery moved up and down,
and the end gate's two legs were confusing. The battery's length and width fit is
kept. The key carrier was good and is not on this plate. R16 and R17 are unchanged.

**Status: independent review and digital geometry/slice checks passed. The first
R18 physical trial has started. Fit, release force, retention and strength remain
unverified until that print is cleaned up and fitted.**

## What changed from R17

- **Bed anchors.** Separate tear-off pads, 0.4 mm (two layers) thick, each with a
  pull tab. Each tie is 1.0 x 0.4 mm (0.4 mm2) against R17's 2.2 x 0.8 mm
  (1.76 mm2). A tie's resistance to bending out of the bed is about 17 times lower
  by section. Ties attach only to the battery end plate and to the XIAO rails and
  hoop, never a ring, ledge or clip arm. The door, keeper and spacers have broad flat faces on the bed; the independent review accepted these without helpers. Watch the thin spacer first layers.
- **XIAO cradle.** A continuous web joins rails and keel into one tray, printing
  as one connected section; R17 printed 3-5 separate islands. A fixed hoop over
  the USB end replaces the two far fingers. Its 2.7 mm deep shoulders sit over
  the bare board corners and clear the reset button by 1.08 mm (R17: 0.23 mm).
  Reset stays open from above. All 14 pads and side wire routes stay open.
- **XIAO near keeper.** Broad bar that slides into the R17 rigid grooves. One
  sprung tooth sits inside its outline. No first-layer relief, so R17's hidden
  bridge is gone.
- **Battery door.** One plate replaces the two-legged gate. Its wide ends sit in the slots; there is one sprung bar inside the outline and one centre tab. The 1.8 mm plate and extended tooth retain at least 0.25 mm nominal catch overlap across the full allowed Y movement.
- **Arrow roof.** The open top now closes to a 45-degree arrow at the near end. It
  is a printable connected opening, gives the door a rigid catch and ties the walls.
- **Anti-rattle spacers.** Three flat removable plates, 0.4 / 0.6 / 0.8 mm. They
  stop 2.2 mm short of the wire end on centre, away from the protection board.

The vertical reserve stays 4.9 mm. The catalogue maximum pack is 4.3 mm and the
nominal code thickness 4.0 mm, leaving 0.6 / 0.9 mm with no spacer. These are not
measurements of the bought cell.

## Orientation

Upright, far end on the bed, remains the choice. Lying the holders down lowers
them (battery 35.6 to 17.2 mm, XIAO 28.4 to 20.4 mm), but the rod clip arcs then
need 9-53 mm2 of support-dependent surface and would flex across layer lines.
Upright keeps the arcs in the layer plane with none. See
`exports/geometry-checks.json`. The door, keeper and spacers print flat.

## Plate

`Battery_Holder`, `Battery_End_Door`, `Battery_Spacer_0p4mm`, `_0p6mm`, `_0p8mm`,
`XIAO_Rod_Holder`, `XIAO_Near_Keeper`. Open
[the editable layout](exports/R18-A1-mini-PETG-layout.3mf) for editing, or use
[the checked Studio slice](exports/R18-SENT-A1-mini-PETG.gcode.3mf) for the sent
print paths. Keep [the CLI source slice](exports/R18-A1-mini-PETG.gcode.3mf) intact.
Spacers carry one edge
nick per 0.2 mm layer: 2, 3 or 4.

A1 mini, 0.4 mm nozzle, textured PEI, Generic PETG baseline, 255 C / 70 C, 0.2 mm
layers, 3 walls, 20% infill, Normal 0.6 mm lift, no support, no slicer brim. The
final Studio estimate was 1 h 4 min 23 s and 7.99 g, including all three spacers;
the separate CLI slice estimated 56 min 23 s and 8.01 g. Studio has reset travel
lift on reload before: check it again. Timelapse, bed levelling and flow-dynamics
calibration were enabled for this trial. Live camera Play must also be checked.

The public Studio archive removes only account metadata; its G-code, settings
and slice info are byte-identical to the audited sent file. See
[the hash binding](exports/sent-export-binding.json) and [audit](AUDIT.md).
Never save over the checked CLI source archive when opening a working project
in Studio: an observed GUI save left that path without G-code. Preserve the
source, and audit a separate final Studio export before sending.

## Cleanup

1. Let the plate cool, then flex it and lift each part from the end-plate or hoop side.
2. Support the holder at its solid end. Snip the two XIAO hoop ties rather than pulling on the hoop. Gently peel other pads one at a time; snip side pads or any tie that resists. Do not lever against rings, ledges, keeper lips or the hoop.
3. Trim any stub, about 1 mm long, with a blade or nail file. Inspect for cracks.

## Assemble

**Battery.** Lay the cell on a spacer, non-wire end first, and slide both in together
as a sled so the pouch does not catch on the spacer edge. Use the thickest spacer
that goes in without force. Never force it. Drop the door into the slots
until the tooth clicks under the arrow bar. To remove, push the centre tab outward
with a thumbnail from the cell side and lift the door by its top bar.

**XIAO.** Tilt the near end up about 6 degrees, slide the USB end about 2 mm under
the hoop, and lower it onto the ledges with wires outside the rails. Slide the
keeper in from the near end until it clicks over the ridge. Pull it by the ears to
remove it before lifting the board.

## Reproduce

Run through the repository geometry runner, in order: `holder18.py`, `anchors18.py`,
`verify18.py`, `project18.py --slice --scratch <scratch>`, `slice18.py`,
`features18.py`, `roundtrip18.py --scratch <scratch>`, `views18.py`.

Audit the separate final Studio slice with
`gui-audit18.py --project exports/R18-SENT-A1-mini-PETG.gcode.3mf --output <scratch>`.
The adapter explicitly checks each object label's full XY footprint against the
reviewed geometry before supplying mesh expectations missing from Studio's sliced-only export. It then runs the same full working-space and layer audit.
