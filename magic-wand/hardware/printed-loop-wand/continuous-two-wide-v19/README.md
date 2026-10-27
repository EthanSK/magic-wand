# Continuous two-wide spirals on Sunny's V19 grip

This prototype keeps Sunny's V19 grip, controls, battery parts and slim solid removable finger loop unchanged. The two upper shaft sections are one 206 mm print with wide crossing spirals and openings across the previous joint. The tip core narrows to 8.055 mm radius (16.11 mm diameter), compared with 8.95 mm (17.9 mm diameter) on V19. The sensor cradle and its connector are matched to this narrower tip; do not mix this shaft or cradle with the old V18/V19 tip connectors.

Sunny’s newer V20 rounded loop fits the same grip and is available as the separate `Print-20-replacement-loop-only.3mf` project. The projects in this folder retain the V19 loop, so print one or the other, not both for one wand.

The complete Bambu project contains both handed grips and one set of shared parts; the one-left project contains one left-hand wand. The checked P1S profile has 250 mm usable height. Both use PETG, 0.2 mm layers and three walls; the V19 loop retains its 100% infill, while other parts use the existing 20% preset. The cradle lies on its open back with supports only on the low back. Remove supports before assembly. One left wand is estimated at 45.949 g of printed parts plus 3.958 g of support and brim; electronics and battery are additional.

Geometry and actual sliced-path checks cover the shaft, wire routes, board space, both V19 grips and their detachable-loop paths. They do not prove physical fit, connector strength, spring force, print quality or comfort. Test the matching connector and the V19 loop and switch fit tests before relying on a full print. No print has been sent.

To reproduce, use the dependencies in `../v19/requirements.txt`; run `wand_cad.py --out` in a new scratch directory, copy checked exports into `exports`, run `verify_models.py`, `print_projects.py`, `check_sliced_paths.py` and `check_v19_grip_paths.py`, then record and run `verify_release.py`. The V19 parts are referenced from their canonical source, not maintained as a second copy.
