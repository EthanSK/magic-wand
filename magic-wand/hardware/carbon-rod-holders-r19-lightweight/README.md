# R19 lightweight battery and XIAO holders

R19 answers one physical complaint about the successful R18 print: the wand tip
is too heavy, and the flat backs of the two holders are a poor use of plastic.
R18 and every older revision are unchanged. The key carrier is not reprinted.

**Status: digital geometry, slice checks and independent Opus review of the
corrections passed. Seven review findings are addressed in [the audit](AUDIT.md).
Not printed; no real R19 Studio export checked. Fit, retention, strength and
cleanup are unverified. Ethan was still testing R18 fit when this was designed,
so any fit change he finds still needs to be applied.**

## How much lighter

Same PETG recipe for both revisions, read from the actual sliced G-code. Tear-off
pads and purge are excluded, because they do not stay on the wand.

| | R18 sliced | R19 sliced | Change | R18 CAD solid | R19 CAD solid |
|---|---|---|---|---|---|
| Battery holder | 3.448 g | 2.404 g | -1.044 g (-30.3%) | 3.821 g | 2.599 g |
| XIAO holder | 2.398 g | 1.745 g | -0.653 g (-27.2%) | 2.620 g | 1.928 g |
| **Both** | **5.846 g** | **4.149 g** | **-1.697 g (-29.0%)** | 6.441 g | 4.527 g |

The door, keeper and three spacers are the same R18 meshes, byte for byte, so they
are not counted as savings. Sliced figures are filament fed, not a weighed part.
Full numbers are in [the mass comparison](exports/mass-comparison.json).

The whole plate falls from 8.01 g and about 56 minutes to 6.30 g and about 47
minutes on the CLI estimate, including all three spacers.

## What changed

**Open floor instead of a flat back.** Each holder's floor is now a ladder of
arrow-headed windows: a central keel, the side walls or rails, and three cross
bars. Each bar grows at 45 degrees from both sides, meets in the middle and closes
into a 1.2 mm strip. Windows point toward print-up, so nothing starts over air.
See [the top-down view](exports/open-floor-plan.png): the broad white areas are
open windows; fine hairline marks are plot artefacts, not designed slits.

Diagonal ribs were tried first and dropped. They only join at their far end, so
the side walls would have stood unbraced for roughly 24 mm during printing, by
calculation from that layout. The bars tie wall to keel inside the layer, and the
longest unbraced run measured on the final meshes is 9.4 mm.

**Rod rings.** Bore, slit and ring section match R18. The support around them is
what got cut down, as Ethan asked. The battery's near-ring saddle narrows to
1.8 mm wide, and short 45-degree gussets carry the ring crowns to the last bar, so
each near ring has a triangular support on both sides. Far rings sit on the frame
or V-bars at the bed.

Less support means less of each battery ring is bonded to the body. The free arc
grows from 122 to 144 degrees at the near ring and from 131 to 136 at the far ring,
so those clips will not behave exactly like R18's. Rod grip and fatigue are
unverified. The XIAO rings keep R18's 121 and 131 degrees. Ring width was not
halved: narrowing both battery rings from 3.6 to 2.4 mm would save only about
0.08 g, so the ring sections are retained while the surrounding support is reduced.

**Battery holder.** Walls 1.6 to 1.3 mm. Roof flanges beyond the arrow roof become
two retaining teeth per side. The end plate becomes a 1.2 mm frame with a large
window. Door slots, catch bar and the 4.9 mm bay are unchanged.

**XIAO holder.** Rails drop 0.6 mm between the board corners. The hoop shoulders
get windows and the bar is 0.3 mm lower. Lower corners of the keeper posts are
chamfered. Ledges, grooves, posts above the groove floor, the hoop underside, USB,
reset and wire routes are unchanged.

The cross bars pass under the board's solder pads, so they are held low there. They
leave at least 1.1 mm below the board, against about 1.66 mm in R18, and still run
on under the rails to root in them. At the two near-end pad rows, R18's unchanged
ledge lead-in still comes within 0.5 mm, as it did in R18. Real solder and wire
heights are unmeasured.

## Plate and print

`Battery_Holder`, `Battery_End_Door`, `Battery_Spacer_0p4mm`, `_0p6mm`, `_0p8mm`,
`XIAO_Rod_Holder`, `XIAO_Near_Keeper`. Open
[the editable layout](exports/R19-A1-mini-PETG-layout.3mf); the
[CLI slice](exports/R19-A1-mini-PETG.gcode.3mf) is the audited source. Do not save
over it in Studio.

A1 mini, 0.4 mm nozzle, textured PEI, Generic PETG, 255 C / 70 C, 0.2 mm layers,
3 walls, 20% infill, 0.6 mm Normal lift, no support, no slicer brim. Same as R18.
Studio has reset travel lift on reload before: check it again. Timelapse is
enabled in the send dialog, not in this archive.

Tear-off pads are unchanged in type: 0.4 mm thick, 1.0 x 0.4 mm ties, six per
holder, on six battery pads and four XIAO pads. The battery's side ties moved
0.3 mm inward to the narrower frame. The XIAO's upper side ties moved onto the
solid band below the hoop window, so they do not pull on a thin leg.

Moving the ties reduced XIAO removable-pad area from 324.94 to 294.54 mm2
(about 9%) versus the earlier R19 layout. The holder's own 164.28 mm2 contact
area did not change in that correction. Adhesion with the smaller pads still
needs a physical trial.

## Cleanup

Same as R18. Let the plate cool, flex it, and support the holder at a solid end.
Snip the two XIAO hoop-top ties rather than pulling on the hoop. Peel the other pads
one at a time and snip any that resist. The battery frame is thinner than R18's
end plate, so snip rather than peel if a pad holds on. Never lever on a ring,
ledge, keeper lip, bar or wall. Inspect the bars and walls for cracks.

## Assemble

As R18. Slide the cell and spacer in together as a sled, non-wire end first, using
the thickest spacer that goes in without force. The bars have a small lead-in, but
if the sled catches on a bar, stop and lift its leading edge rather than pushing.

## Reproduce

Run through the repository geometry runner, in order: `holder19.py`, `anchors19.py`,
`verify19.py`, `loadpath19.py`, `project19.py --slice --scratch <scratch>`,
`slice19.py`, `features19.py`, `roundtrip19.py --scratch <scratch>`, `views19.py`,
`mass19.py`. `gui-audit19.py` audits a final Studio export against this source
slice. Its source-receipt guard accepts R19 and rejects the R18 archive. The full
audit passed on a synthetic meshless Studio-format fixture holding the exact R19
G-code from before the review corrections, and again on the final CLI archive.
Neither is a real Studio export. A real R19 Studio export has not yet been checked.
