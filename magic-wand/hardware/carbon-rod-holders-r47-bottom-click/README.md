# R47 bottom click

R47 moves the OP1 click from near the hinge to the bottom of the DFRobot touch board, where the finger presses. The OP1 group moves 2 mm right, and the hinge moves 0.4 mm closer to the board. Everything else carries over from R46: the four Choc seats, the rod clips, the rounded finger rests and all four R46 middle-to-edge braces.

The complete nine-part R47 plate finished successfully on 17 November 2026, as reported by the owner. The owner reported damage during support removal on one half of the key holder. Assembly fit, click feel and hinge strength still need a hands-on check. [Physical trial record](PHYSICAL-TRIAL.md)

## What changed from R46

| | R46 | R47 |
|---|---|---|
| OP1 plunger, world X/Y (mm) | -1.6, 3.05 | 0.4, -2.27 |
| Plunger behind the touch board's front edge | 11.82 mm | 6.5 mm |
| Hinge axis to plunger (lever) | 28.10 mm | 33.02 mm |
| Hinge axis to board front edge | 39.92 mm | 39.52 mm |
| Board rear edge to hinge support | 2.97 mm | 2.57 mm |
| OP1 board yaw | 25° | 19° |

- **Click position.** The plunger now sits 6.5 mm behind the touch board's bottom edge, which puts the contact 0.836 of the way from the hinge to that edge (R46: 0.704). A finger at the edge moves only 1.20× the switch travel (R46: 1.42×) but needs 0.836× the switch force (R46: 0.704×). Whether this feels easier has to be tried.
- **Why not closer to the edge.** The harness plug under the far end of the OP1 board sits about 18 mm behind the plunger. Any plunger nearer the edge puts the plug over the middle rod-clip ring. At 2.5 mm from the edge (lever 37.0 mm) the plug opening removed 27 mm³ of that ring and split three right guard ribs; at 6.5 mm the ring is untouched.
- **Board seat.** The R46 board's holes fitted, but its body sat on the lower lip. The R47 board slot is open at the lower end, and a rounded chin below the bottom keys carries the board. The chin floor runs 1.2 mm past the modelled board end. Lengthening the board by 1, 2 or 4 mm still drops in with the same 0.025 mm³ graze, which the geometry checks report.
- **Harness.** Push the plug onto the board before fitting it. Board and plug then drop in together from above. The plug pocket stops 0.15 mm under the plug instead of running down through the rod clip. Before connecting the far end, thread the lead's free end down through the 30.5 mm² opening beside the rod channel; a round end up to 5.0 mm fits, and a three-wire 1.5 mm bundle needs 3.2 mm. Then press the lead up into its open underside groove.
- **Yaw.** The board turns 19° instead of 25°. At larger yaws, or at 20° with the 2 mm shift, the board's far corner comes within 0.6 mm of the upper-right Choc clip relief. At 18° or less the plug nears the rod.
- **Hinge.** The arms, tabs, roots, squeeze stop and supports move 0.4 mm towards the board, and the arm length is unchanged. A larger move would reach R42's pocket for the Gravity pin tails or shorten the arm, and a shorter arm raised the root strain that failed in hand assembly before.
- **Stops.** The longer lever moves the plunger 1.18× as far per degree, so three stop settings change:
  - the backup feet meet 0.055 mm sooner;
  - the adjustment-screw landing rises 0.05 mm;
  - the screw starts at 1.7 turns instead of 2.0.

  The switch clicks before the backup feet touch. The fully driven screw lands before the feet, and its softest setting stays below the switch's free height. Every one of these margins is smaller than one 0.2 mm layer, and the bracket's heel prints in its first layers, so elephant's foot could shift them by about 0.09 mm of plunger travel.
- **Guard legs.** The plug pocket cuts the deck ends of the R2 and R3 right guard legs. A rounded 0.95 mm-radius bar ahead of the pocket ties them, through R1, back into the centre deck.

## How the carrier is built

`build47.py` builds the carrier procedurally, in R45/R46's own order:

1. R44's procedural carrier at the R47 parameters (`holder47.configure`).
2. R45's standing repairs, run by R45's own generators on that body:
   - the left key-floor chamfer;
   - the four lower-floor lip reliefs;
   - the left guard-web buttress.

   R45's relief of the old OP1 ledge belonged to the old opening and is not applied.
3. R46's four rounded braces at R46's stations, clipped by the R47 hardware routes.
4. The R47 chin and guard-leg landing.

The moved OP1 openings and every R47 route are then cut from the additions. On the R47 body, R45's generators reproduce R45's published chamfer, lip relief and web volumes. Three braces match R46 to 0.0001 mm³. The right deck return differs because the moved OP1 opening trims it, leaving a 14.06 mm³ base bond (R46: 14.90 mm³).

`check46.py` runs the same chain at R46's parameters and compares the result with R46's published carrier at every standing print layer.

## Reproducing

Run each geometry step through the repository's geometry budget wrapper. Pass the scratch directory as an argument; outputs go to `SCRATCH/stage` and `SCRATCH/build`.

1. `build47.py SCRATCH` composes the carrier and bracket cap and runs R44's inherited checks plus R47's. The intended inherited exceptions are:
   - R46's closed-slot front wall and bottom edge, both replaced by the open slot and chin;
   - R32-R46's from-below plug entry, replaced by pre-fitting.
2. `check46.py` is an optional comparison diagnostic. It does not prove exact reproduction of the old quantised R46 mesh and is not an R47 delivery gate.
3. `plate47.py BUILD SCRATCH` lays out the standing key-holder plate with R45's helper generators run on the R47 body. It rebuilds R42's OP1 seat solid-infill selectors around the moved seats and adds solid selectors for the new guard-leg landing and all three left rod-side guard joints. It also checks that the body written into the layout still prints as the checked carrier.
4. Slice `BUILD/R45-Key-Carrier-layout.3mf` with R45's `slice45.py`. Run it through the scratch wrapper; it never sends a job.
5. `review47.py BUILD/R47-first-slice.gcode.3mf` runs R46's helper-start, roof-stroke and contact screens and compares commanded material with R46's selected archive (`material47.py`).
6. `guide47.py SCRATCH PARTS` exports the parts and the assembly guide.

The internal layout and helper file names keep R45's names because the inherited slicing and audit tools expect them.

## Complete print package

The complete plate includes nine functional parts: the key carrier, DFRobot snap bracket, both matching post clips, XIAO holder and keeper, battery holder and end door, and the twelve-wire cable clip. Bought boards, switches, caps, rod and screws are assembly references, not printed objects. No loose battery spacer is included. The four named disposable helper owners and the Smooth timelapse tower are additional printing aids.

The selected native archive was reopened and resliced once, then checked independently from its own G-code. The A1 mini 0.4 mm/Textured PEI recipe commands 245 C nozzle and 60 C bed for the same external red HS PETG Metallic used for R46. Use the print-only package to preserve those paths. The send dialog still needs Timelapse, bed levelling, flow calibration and external-spool verification; select Silent speed on the real printer after startup and verify it after the layer-four acceleration reset.

`project47.py` composes the checked key/helper group, current bracket and both clips with the existing other parts and widened battery anchors. `audit47.py`/`screen47.py` check the carrier, load paths and whole helper withdrawal; `audit_parts47.py` checks the other eight parts and full bed spacing. `spaces47.py` supplements zero-point route rows with complete deposited-slab checks and compares nominal mounting-end contacts against the physically fitted R46 slice. `delivery47.py` checks the machine commands and inventory. `bundle47.py` seals the unchanged G-code and records the first-fit decision and physical limits.

The explicit left-joint fill restores minimum native coverage to 97.20, 95.55 and 95.02 percent. Moving the nearby OP1 cut-out changed the slicer's local fill even though the left joint CAD did not change. The raw nanometre construction fringe under the first chamfer layer remains reported separately; every designed chamfer slab is checked.

Support amount remains close to the successful R46 print, rather than being claimed as reduced: the helper estimate changes by about 0.01 g. Their rooted starts, contact patches and actual removal paths are checked. The cleanup animation shows individual pieces in native removal order, but PETG pull-off effort and residual nubs are unmeasured. Five short unanchored strokes and longer rooted bridges retain the R46 trial pattern; the maximum one-ended edge is 0.018 mm longer. These can still leave wisps or sag.

The OP1 mount is intentionally wider than the bare switch: it supports the board's two hole seats and clears the fitted plug and its lead. The former closed bottom lip is replaced by an open end and a rounded chin. A leaner cosmetic surround can follow a successful bought-board trial; the current board length and connector envelopes still include photo-based estimates.
