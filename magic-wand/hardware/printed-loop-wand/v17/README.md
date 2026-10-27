# Print V17 — smooth lower handle attachment

V16's lower handle had a permanent blunt end below its separate diagonal mounting bridge. Those were final printed material, not removable supports. V17 removes both and carries the curved lower return directly into a rounded housing around the lower stud. The stud collar is enclosed by that housing; the recessed lock remains unchanged.

**Only the universal removable handle needs reprinting.** Both handed V16 stems and every other assembled wand part are byte-identical. Sixteen of eighteen mesh files match V16; the changed files are the loop and its small matching coupon. Earlier revisions remain unchanged.

## Projects

- [Replacement handle only](../../../../magic-wand-3d-models/Print-17-replacement-loop-only.3mf), already placed flat with the PETG support settings.
- [Complete project: both handed stems and one shared set of remaining parts](../../../../magic-wand-3d-models/Print-17-complete-left-right-recessed-switch-410mm.3mf). Choose one stem per wand.
- [One left wand](../../../../magic-wand-3d-models/Print-17-one-left-wand-410mm.3mf).
- [Small cam-lock test](../../../../magic-wand-3d-models/Print-17-detachable-loop-fit-test.3mf), [switch test](../../../../magic-wand-3d-models/Print-17-recessed-switch-button-fit-test.3mf), [shaft-joint test](../../../../magic-wand-3d-models/Print-17-slim-bayonet-fit-test.3mf), and [upper replacement for a retained V2 stem](../../../../magic-wand-3d-models/Print-17-upper-only-helix-410mm.3mf).

## Attachment and fit

Mounts remain at 42 and 132 mm. Viewed from the tip toward the grip, start 12° clockwise from the final loop position, insert the pegs, lift 4 mm and turn left 12° along the 0.6 mm cam rise. Release the catch at the end stop. To detach, press the tab outward, turn right, lower 4 mm and withdraw. Pins and the release mechanism leave with the loop; the bare wand retains only recessed openings.

The new curved return has a minimum centreline bend radius of about 7.57 mm. Its rounded root encloses the complete lower stud collar. Geometric checks verify zero material in the rejected hanging-toe region, zero collar volume outside the curved housing, both-handed entry/locking/release routes, independent upper/radial/downward stops, reverse catch and cap/button clearance. Physical PETG force, strength, fatigue and hand comfort remain unverified. Test the small lock before committing to a long print.

## Retained design and printing

The 410 mm tapered wand, complete raised helix, Art Nouveau openings, higher button positions, recessed switch mounts, flat switch plates, clipped Sense cradle, upward USB, rear solder clearance, 10.4 mm bore, thin battery guides and twist cap are retained. The loop stays in the same plane and retains its greater upper/thumb reach. Its lower return is reshaped to eliminate the exposed connection, without shifting the controls or the two locks. The battery envelope remains provisional at 20 × 6 × 40 mm.

Seven prepared Bambu projects use P1S 0.4 mm PETG, 0.2 mm layers, 3 walls and 20% infill. The loop lies on its broad face; manual support is limited to mounting roots, with its ventilation passages protected. Thin switch plates remain broad face down. One left wand estimates **75.048 g printed parts** plus **3.443 g removable supports/brim**. Electronics, battery, wires, switches, sockets and caps are unweighed. This is 0.178 g less printed PETG than V16.

[Interactive preview](preview/) opens with the loop attached. Lower join shows the actual attached root. Compare shows V16 beside V17. Geometry validity, clear sliced paths and estimated material are separate from physical acceptance.

Install requirements.txt, generate wand_cad.py into a new output directory, and use check_geometry.py, print_projects.py and verify_release.py for regeneration and verification. Saved exports include the fit, mass, orientation and actual sliced-clearance reports.
