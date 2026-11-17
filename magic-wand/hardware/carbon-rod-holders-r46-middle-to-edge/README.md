# R46 middle-to-edge finger rests

The permanent carrier gains two rounded diagonal braces. Each runs from the middle of a finger rest through the next guard row to the outside edge. Two sloping returns join those rests to the deck. The right return thickens the existing landing. The left lands farther inward and forward so the lower-left window and the soldered socket stay usable. All four additions together occupy 103.01 mm³.

In the assembly guide, cyan is the finished carrier. The orange posts and crossbars come away with the print cradle. The cleanup view shows the removal order and the direction each piece can move. Remove the helpers before fitting the switches or rod.

The [underside comparison](exports/R45-R46-underside.png) and [left return detail](exports/R45-R46-left-return.png) use the generated meshes. Pale green shows material added to R45. The rounded finger-contact surfaces, switch locations, rod clips and diagonal OP1 position carry over from R45.

## Reproducing the plate

Use the R45 CAD and slicing environment. Run the following in a fresh working directory under the geometry budget and scratch-disk wrapper. Output directories passed to the generators are build directories, separate from the published package.

1. Run `plate46.py BUILD`. This composes the frozen R45 carrier and records the four new members, ten joint overlaps, and the intersection of new material with every working space.
2. Slice `BUILD/R45-Key-Carrier-layout.3mf` to `BUILD/R46-first-slice.gcode.3mf` with the inherited `slice45.py`. The internal layout filename follows the inherited plate generator.
3. Run the inherited `helper_starts45.py` and `roof_strokes45.py` on the first native archive. Run `review46.py BUILD` to check that archive and independently reopen, reslice, and check the resulting archive.
4. Review the roof, hardware-route, material, machine, and removal reports against the selected archive. After recording the physical-trial risks in `trial-review.json`, run `bundle46.py BUILD`. It seals the native toolpaths and regenerates the matching guide and comparison views.

The strength checks measure each new whole member and each pre-union joint against the deposited bead footprints. They also measure the connected material on transverse cuts at 25%, 50% and 75% of each member’s length. The original R44 references and the R45 replacement-web qualification stay in the audit. These checks do not measure breaking force, PETG adhesion, bridge sag or how easily the cooled supports detach.

## First physical trial

The final reopened slice is 209 layers, about 2 hours 39 minutes and 24.97 g including its removable cradle and timelapse tower. The working openings clear the actual deposited paths after the documented helper removal. The model is a trial, not a guarantee of fit or strength.

Nine straight bridges have backing at both ends and span up to 13.564 mm. Five very short strokes, up to 0.620 mm, lack backing at both ends; a separate one-ended sparse-infill run reaches 1.037 mm. These can sag or leave wisps. Later plastic is not counted as backing when those strokes are first deposited. The generic floating-region warning is retained and the exact residuals are recorded in `exports/key-holder-only/trial-review.json`.

The 16 November 2026 physical trial was stopped at layer 1 of 209, at 5 percent progress, after repeated low-angle camera views were interpreted as suspected raised, tangled extrusion. Those views did not establish the base's contact with the plate. The nozzle and bed had reached 245°C and 60°C. The first-layer toolpaths command Z0.2 mm and extrusion speeds of 20 or 30 mm/s; those values do not measure the real nozzle gap or establish adhesion. Cancellation, parked motion and both heater targets off were verified. The trial did not reach the new braces or establish their strength, support removal or hardware fit. Its initiating physical cause remains unresolved.

The subsequent retry used the same selected toolpaths. The operator confirmed its base was flat and staying attached; a later controller read showed `FINISH`, all 209 layers complete, no active errors and both heater targets off. On 17 November the operator reported a mostly successful carrier, with supports removable but some difficult contacts and remaining nubs. The OP1 mounting holes line up, but its board body overlaps the lower lip; the complete board seat still needs correction. The separate DFRobot bracket was absent from this key-holder-only plate, so hinge operation and the complete click mechanism remain untested. See [physical trial notes](PHYSICAL-TRIAL.md).
