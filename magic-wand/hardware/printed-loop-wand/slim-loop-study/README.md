# Slim detachable loop studies

These are three **unprinted prototypes** for the 410 mm Shard Tube R2, based on
`c945772`. The existing R2 model is unchanged. The loop uses the same two
recessed hooks and separate keeper; remove the battery cap before attaching it,
slide the loop upward into the receivers, then rotate the keeper 90 degrees.
It fits either the left or right R2 grip in the digital checks.

* **Slim:** 7.6 × 3.4 mm band, solid.
* **Petal:** 7.6 × 3.4 mm band, three long openings.
* **Leaf:** 8 × 3.6 mm band, four long openings.

The R2 reference is 9 × 4 mm. The openings pass through the finger-contact
surface, leaving material either side. The attachment roots remain full size.
The wand shaft, XIAO tip, switch mounts and battery setup are the existing R2.

## Print and check

Open a matching `Slim-Loop-*-one-left-light.3mf` for one wand or
`Slim-Loop-*-complete-both-hands.3mf` for both grips in Bambu Studio. Projects
are in the repository's `magic-wand-3d-models/` folder. These were sliced for a
Bambu P1S, 0.4 mm nozzle, PETG and 0.2 mm layers. The loop is printed solid;
the unchanged XIAO cradle uses marked, removable support. Check the actual
filament preset, plate layout and preview before sending to the printer.

The digital model and sliced path checks do not prove comfort, strength or
physical fit. Print a loop and the R2 attachment fit tests first; check that the
openings are clear, the hooks and keeper fit without force, and the grip does
not crack when flexed. Do not rely on a thin prototype to support valuable
electronics until it has passed a physical test.

## Rebuild

`wand_cad.py` generates the editable mesh and interface checks, using the
canonical R2 generator; `print_projects.py` creates and slices the Bambu
projects with the R2 print settings. `check_slices.py` checks functional
clearances and layer starts; `check_openings.py` checks the centres of the new
openings. `package_results.py` packages the successful projects and compares a
newly sliced R2 baseline. All output directories must be new; store large
scratch results outside the repository. Requires the project's CAD Python
environment and Bambu Studio. The comparison viewer reads the committed
manifests and can be served from the repo root.

PETG weights and print times are estimates from the slicer, not measurements;
they exclude purchased hardware, battery, sensor and wires. See
`exports/mass.json` and `exports/projects.json` for the precise comparison.
