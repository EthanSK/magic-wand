# R60 · Integrated finger guards and slide-in battery

The key holder, both finger rests and the battery cradle print as one piece. The R59 pin hinge, touch paddle, sliding OP1 board retainer, board posts and separate clips are reused. This is a fit-trial design.

[Inspect the finger side in the assembly viewer](../carbon-rod-holders/assembly/?version=r60&component=keys&view=finger_rest) · [Battery loading](../carbon-rod-holders/assembly/?version=r60&component=battery) · [Full 500 mm assembly](../carbon-rod-holders/assembly/?version=r60&component=whole)

## Lower keys and finger contact

Each lower socket has three rounded, 2.52 mm diameter runners to spread finger pressure across the exposed contacts. Two rounded supports return to the lower edge and a smaller rear arm reaches the solid deck between the key and rod. A fingertip rests on the smooth beams. Both sides mirror the same shape.

Feed a lower socket from its outside edge with the wires trailing outward. Lift it into its seat. The flat backing strip can temporarily slide in over the guard to support the socket while pressing in the switch. Slide the strip back out afterwards. The CAD checks both backing strips along their full travel and all 336 sampled key and socket positions.

## Battery

Slide the 27 × 11.8 × 3.9 mm wrapped pack lengthwise from the open end beside the rod. Leave the leads and plug outside. Two round-edged rails guide it. A flexible side wall has a smooth contact pad on the long edge. About 4 mm of the battery remains exposed for removal by the wrapped body. The wired end must face the opening for this arrangement. The actual lead exit, wrap variation and installed slack need a physical check.

The inboard side of the pack moved 4 mm toward the rod from R59. The pack passes below the three-wire channel. The revised floor extends about 0.92 mm farther down. The spring projects 0.21 mm into the nominal pack width, and the opposite wall leaves 0.07 mm of lateral room, giving 0.14 mm nominal deflection. There is 0.68 mm relief beside the spring. These dimensions describe how grip is intended to work. Printed force, fingertip comfort and repeated-load strength need a physical trial. First try a smooth, inert pack-sized dummy. It should hold when tilted and slide out by hand. Stop if it binds or marks the wrap.

The complete trial plate has 12 separately identifiable pieces. It includes the two printed board clips, a spare centre hinge clip, two hinge-pin fits and both backing strips. The stabilising tower and adhesion panels are disposable. The six breakaway fins meet the rim outside the battery pocket and hinge. Nip them from the outside and smooth the cut surfaces.

## Reproduction and checks

Run the scripts in the Wand CAD environment, keeping generated slice scratch outside the source directory. Run heavy geometry jobs through the project's printability-audit geometry runner.

1. Run `design60.py` to rebuild the integrated holder, pack reference and CAD fit measurements.
2. Run `guide60.py --register` to derive the viewer guide from the assembly and its reused meshes.
3. Use `plate60.py LAYOUT.3mf` to create the standalone A1 mini PETG plate, then run the existing `slice45.py` workflow.
4. Run `audit60.py PLATE_FOLDER` on the original and reopened layout slices. The checks cover individual first-layer pads, seam strength, unsupported starts, the complete hinge and socket routes, the battery opening and clearance around the spring. The backing-strip check requires both a clear insertion and a collision when the same strip is deliberately lowered into the beams.
5. Use `release60.py PLATE_FOLDER REOPENED_FOLDER` to package the independently reviewed slice. The release checks mesh, layout, review and archive hashes.

The final sliced spring opening is 11.66–11.67 mm across three sections near the middle of its contact pad. The pack's nominal width is 11.8 mm. The tapered stop at the far end builds up from the floor, keeping long unsupported strings out of the pocket. The rigid opening and backing strips clear the deposited paths.

[Complete PETG trial plate](exports/print-mechanisms/R60-Complete-Key-Holder-A1-mini-PETG-print-only.3mf) · [Per-part print audit and physical fit checks](exports/print-mechanisms/review.json)
