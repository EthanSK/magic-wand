# Carbon-rod holders R13: printability repair candidate

This revision repairs the R12 print workflow and reinforces local fixed parts. It is a **coupon-first prototype**, not a physically accepted production print. R12 remains preserved; its old slice-clearance pass did not require supports to clear working openings.

## Changes kept local

- Keep five keys and their bought switch/socket interfaces, 18.5 mm pitch, 20.5 mm rows and the 25.4 mm clear thumb region.
- Keep the 7.9 mm relaxed clips for an 8 mm rod, their 30-degree gaps, external wiring, upward USB and separate battery cage above the keys toward the tip.
- Print rod axes vertically so bores have no circular roof and clip bending lies in the layer plane. This creates broad starts elsewhere; labelled exterior CAD walls support them, with deliberate gaps. Automatic slicer supports and brim are off.
- Add fixed outboard load rails beside every key, preserving switch lands and the complete nominal/maximum socket routes. Scan the whole key-to-clip path: the earlier 2.76 mm² bottleneck grows to at least 11.37 mm² in the CAD. This is a geometry screen, not a measured breaking force.
- Thicken the four fixed joints between key rows from 1.2 to 2 mm below the existing mounting plane. Trim a detached 0.27 mm old corner remnant; retain the actual rounded rear posts, key positions and bought interfaces.
- Battery crossbars grow from 1.4 to 2 mm diameter. A far-end frame and three longitudinal tracks shorten open cage bridges. The far clip moves 2.2 mm within the separate module; assembly placement is recalculated to retain the 8 mm minimum key-frame gap.
- Battery guide outside walls grow from 0.8 to 1.6 mm, with outside diagonals into the roof posts. The gate gains a thicker central grab bar; its sliding wedge dimensions stay unchanged. Print the gate on its original broad face, with the extra grab bar upward.
- Sensor outer rails grow from 1.2 to 2 mm outward; fixed diagonal roots grow from 1.6 to 2.1 mm diameter, below the PCB bearing plane. The long fixed rails between clips grow locally from 1.25 to 2 mm, stopping before the free spring arms.

## Files and checks

- `cad.py`, `parameters.json`: editable source composed from frozen R12/R7 interfaces.
- `exports/*-assembly.stl`: physical part meshes in assembly coordinates.
- `exports/*-SOURCE-REQUIRES-PREPARATION.stl`: normal part meshes in checked print orientations. These bare STLs do **not** contain the print helpers.
- `exports/*-PRINT-HELPER-assembly.stl`: explicit sacrificial printing walls. They are not assembly components and must be removed.
- `exports/AFTER-KEY-TEST-Holder-R13-sliced.3mf`: complete prepared project, including labelled print helpers. Use its exact orientation/settings; do not re-enable automatic support.
- `verify_geometry.py`: final exported one-body, bought-part, complete socket/gate/cell routes and assembly checks.
- `verify_slice.py`: actual G-code with bead-width footprints through all working spaces; exact prepared normal mesh comparison; whole-print starts including helpers, backing from actual previous-layer bead footprints; every project’s actual layer views and their hashes.
- `strength_audit.py`: final STL sections and actual bead-track counts at likely snap points in every part, with load directions and required physical tests. This does not predict breaking force.
- `start_audit.py`, `side_gap.py`, `working_spaces.py`, `deliverables.py`: directly-beneath backing, actual helper-to-part bead gaps, shared nominal/maximum working spaces and unambiguous source/trial names.
- `qualify.py`, `overhang-decisions.json`: fail closed on any broad overhang or slicer warning without an explicit bounded-trial decision. `full_set_ready` remains false pending physical trials.
- `exports/r12-negative-control.json`: the same strict all-bead checker rejects the old delivered slice. Its adapted region definitions are a regression control, not a re-release of R12.

Reproduce with the pinned `requirements.txt` environment, running `cad.py`, `verify_geometry.py`, `print_project.py --slice --scratch <external-scratch-directory>`, `verify_slice.py`, then `strength_audit.py`. Build the representative test with `print_project.py --slice --coupon --scratch <another-external-scratch-directory>` and audit it with `verify_slice.py --exports exports/fit-coupon --project exports/fit-coupon/PRINT-FIRST-Key-Clip-Test.3mf` (paths relative to this revision). Also run `test_start_audit.py`, `qualify.py` for every project, `reopen_project.py --scratch <new-external-scratch-directory>`, `review_views.py --exports <project-export-directory>` for every project, `audit_views.py`, `compare_revision.py` and `build_preview.py`. Complete-part trials use `print_project.py --slice --only Key_Carrier`, `--only Battery_Holder Battery_End_Gate` or `--only XIAO_Rod_Holder`, each with a fresh scratch directory; use `--coupon --bore 8.0` or `8.1` for bore brackets. Regenerate explicit per-case decisions after an affected slice; the qualifier rejects unknown cases instead of approving them automatically. Bambu Studio CLI is required. Run repository-root `npm run check` before committing. Keep large slicer scratch outside the checkout under the shared scratch policy.

## Print and remove helpers

Prepared recipe: Bambu P1S, 0.4 mm nozzle, PETG, 0.2 mm layers, three walls, 20% infill. Keep the prepared object overrides. The generator restores the changed-key registration in the actual CLI-exported archive and asserts that values have not changed; the saved layout alone is insufficient. The reopen check covers the repaired exported file via CLI; GUI open/save remains separately unverified. Automatic support and brim must remain off. These settings are a test recipe, not confirmation of the printer or material used in the failed physical print.

The orange outlines in the saved layer views identify CAD helper sections. The helper walls are outside rod bores, clip gaps, switch/socket spaces, cell loading space and the board/wire route. Helpers are generated on the actual 0.2 mm layer grid; named contacts leave one empty layer, verified from real lower extrusion. Sideways clearance is generated at 0.9 mm and remeasured from actual bead widths with a 0.5 mm conservative requirement and 0.025 mm numerical guard. These are process checks, not proof of physical release.

After cooling, hold the fixed frame close to the helper being removed. Cut the deliberate small ties at the fixed outside rails first; they are not spring connections. Grip and cut/peel the exterior walls outward in short sections. Each axial C wall is split into two outside halves. Diagonals can prevent a complete half from sliding out rigidly, so removal may require cutting its accessible 0.8 mm wall into shorter pieces; physical access and release remain trial-dependent. Never pull using a thin spring tip, lever through a rod hole, pry against a socket floor or force the cell. Remove all walls before loading hardware. If a wall is fused or needs force on a spring, stop: the coupon has failed and the contact recipe needs revision.

The CLI can flag a floating cantilever where an ordinary-model CAD wall deliberately stops below the part. That warning must be assessed using the actual whole-print backing/bridge views and physical trial; it is not erased or treated as an automatic pass.

## Coupon-first acceptance

Use `exports/fit-coupon/PRINT-FIRST-Key-Clip-Test.3mf` first: one sourced central key seat with the new outboard load rails, its retained diagonals and both complete clips. It uses the final orientation and helper recipe; it does not cover side-key joints or full-height bed stability. The 8.0 and 8.1 mm bore variants only bracket fit; they do not change the 7.9 mm default. Slide from a bare rod end and never force an undersized trial.

After the small test, use the complete-part trial projects under `exports/trial-*` for the full-height carrier, battery cage with gate, and sensor holder. A full-size lightweight part preserves the real load path and print height. Before accepting the full set, check:

1. All helpers release without tearing a bearing face, spring or socket floor. Every bore and slot is visibly open, with no stringing or residue.
2. Slide the clips on from a free rod end. They must slide with light friction without cracking or whitening. Do not snap them sideways over the rod or force an undersized print.
3. Insert a real socket and switch through the full intended route; confirm the key operates and the floor/posts do not bend during ordinary pressing.
4. Load the real battery and gate, confirm retention without pressure on the pouch, and check the cage bridges for droop or weak joints. Grip the new central bar to remove the gate.
5. Check actual populated-board underside, solder bends and USB lead clearance, then sensor retention. Those dimensions are not established by a bare PCB reference.

Physical helper removal, bed adhesion, PETG bridge sag, force, fatigue, cell retention, grip comfort and complete assembled hardware acceptance remain unverified. Passing CAD and G-code checks cannot establish that nothing will snap.
