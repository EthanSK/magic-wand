# Print V16 — recessed switches without square surrounds

All three switch mounting planes sit **3.4 mm farther inside** the existing curved stem. The projecting square surrounds are removed. Two small relieved side clips and lower stops hold the thin mounting plate. The bought socket retains its existing alignment and the plate remains 16.4 × 17.2 mm with a 14 mm switch opening, smaller than the purchased 16.6 × 17.5 mm keycap. There is no separate printed keycap, square housing or keeper. Wires carry no mechanical retention load.

## Assembly and small test

Print the [matching switch-pocket test](../../../../magic-wand-3d-models/Print-16-recessed-switch-button-fit-test.3mf) first. It has the actual curved pocket and a flat backing. Seat the wired bought socket in its backed recess. Spread the two small side clips gently, seat the plate radially inward and release them over its rear feet. Fit the bought Choc switch and keycap. Remove the plate by spreading the clips and withdrawing it outward; the old long top-slide guides are superseded. Check fit and full key travel before printing both stems. PETG stiffness, retention force, fatigue and real hand comfort are unverified.

The side arms are 0.8 mm thick with approximately 5.6 mm free length and relief behind them. Geometry checks use a 0.65 mm tip-spreading envelope; this is not a measured or guaranteed flex specification. If the small test binds, adjust its clearance before committing to a complete print.

## Print orientation

The thin plates now print **broad face down**, with rear feet upwards. Their print height is 2.5 mm, versus V15's incorrect upright 17.2 mm. Actual STL bed contact is 85.33 mm². The matching pocket coupon also lies flat. Battery rails retain their broad-side-down orientation, the loop stays on its broad face and the diamond cover retains its supported crown-down orientation. Tall shafts/stems remain upright for their curved cells and bayonet details. All six prepared projects use P1S 0.4 mm PETG, 0.2 mm layers, 3 walls and 20% infill, with geometry-specific support settings.

## Complete projects

- [Complete: both left- and right-handed stems plus one shared set of remaining parts](../../../../magic-wand-3d-models/Print-16-complete-left-right-recessed-switch-410mm.3mf). Choose one stem per wand.
- [Exactly one left wand](../../../../magic-wand-3d-models/Print-16-one-left-wand-410mm.3mf).
- [Switch fit test](../../../../magic-wand-3d-models/Print-16-recessed-switch-button-fit-test.3mf).
- [Retained loop-lock test](../../../../magic-wand-3d-models/Print-16-detachable-loop-fit-test.3mf) and [shaft-joint test](../../../../magic-wand-3d-models/Print-16-slim-bayonet-fit-test.3mf).
- [Unchanged upper replacement for a retained V2 handle](../../../../magic-wand-3d-models/Print-16-upper-only-helix-410mm.3mf). This subset does not gain the new switch pockets.

## Preserved design and evidence

The 410 mm length, continuous taper, complete original raised counter-wound helix, Art Nouveau cells, higher control positions and angles, rounded diamond, clipped Sense cradle, upward USB, solder clearance, battery cap and 10.4 mm main wire bore remain. Both hands are included. The V15 recessed lift-and-left-turn loop attachment is unchanged: insert at a 12° clockwise offset, lift 4 mm, turn left 12° through a 0.6 mm cam rise and let the catch seat. Directions are viewed from the tip. Release outward, reverse turn, lower and withdraw. No handle brackets remain on the bare wand.

Fourteen of eighteen exported meshes match V15 byte for byte. Only the two stems, switch-plate print orientation and matching switch-pocket test change. Earlier revisions remain unchanged. The battery envelope remains provisional at 20 × 6 × 40 mm; measure the actual cell.

One left wand estimates **75.226 g printed PETG**, 0.913 g less than V15. Supports/brim add 3.632 g. Bought switches, sockets, keycaps, board, battery and wires are unweighed. Allowance to a 100 g complete wand is 24.774 g; 80 g all-up is not established.

[Interactive preview](preview/) opens with the loop attached. Compare shows V15 beside V16. The Recessed switch close-up separates the plate to expose the pocket; black keycaps in assembled views are bought reference parts. Exports include mesh, fit, orientation, mass and sliced-clearance reports. Geometry and slicing do not establish physical acceptance.

Install requirements.txt, then use new output folders with wand_cad.py, check_geometry.py and print_projects.py. verify_release.py checks the recorded sources and prepared projects.
