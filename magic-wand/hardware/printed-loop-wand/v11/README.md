# Print V11 — ribbed shell and broad open cells

This candidate replaces V10's sparse narrow slots with broad rounded hexagonal windows. Four continuous 3 mm wide axial lands (1 mm grip skin; 1.4 mm shaft depth), the full original raised counter-wound spiral strips and short connections between cells support the perforated shell. The existing 410 mm taper, rounded diamond, 10.4 mm wire route, three top-slide switch plates, battery guides and detachable loop interfaces are preserved. Both handed stems are included.

The loop has three larger rounded hexagonal openings through its outer/inner contact faces, plus matching openings through its broad sides. Its original YZ plane and approximately 49/39 mm upper/lower outward reach are unchanged. The buttons stay at 139/135/109 mm with their previous angles and radial placement.

## Print projects

- [Both handed stems plus shared remaining parts](../../../../magic-wand-3d-models/Print-11-complete-left-right-top-slide-410mm.3mf). This contains both handed stems and one shared set of the other parts; choose one stem for a working wand.
- [Exactly one complete left wand](../../../../magic-wand-3d-models/Print-11-one-left-wand-410mm.3mf), used for the mass comparison.
- [Upper replacement retaining the printed V2 grip](../../../../magic-wand-3d-models/Print-11-upper-only-helix-410mm.3mf).
- [Detachable-loop fit coupon](../../../../magic-wand-3d-models/Print-11-detachable-loop-fit-test.3mf), [button coupon](../../../../magic-wand-3d-models/Print-11-top-slide-button-fit-test.3mf) and [bayonet coupon](../../../../magic-wand-3d-models/Print-11-slim-bayonet-fit-test.3mf).

## Evidence and limits

All eighteen exported meshes are closed, consistently wound single bodies. Checks cover both handed control insertion paths, retained old joints, the head cover/cradle, battery and wire routes, spiral material relative to the previous model, continuous axial lands, the larger apertures and released loop movement. Upright shaft cell walls and board pockets have no newly floating layer islands in the sampled 0.2 mm layers. Prepared P1S 0.4 mm PETG projects use 0.2 mm layers, 3 walls and 20% infill in thick local features. All six slice without reported warnings. The flat loop uses no brim and support enforcers only at its mounting roots; broad-face openings remain clear. Protected-route checks sample extruding straight and arc moves, including supports, across the interior outlines of all broad windows and the loop contact/broad-face openings.

One complete left wand estimates **70.754 g printed parts**, versus V10's **76.072 g**: **5.318 g / 6.99% less** under the matching settings. Supports/brim are **3.953 g**, giving **74.8 g total filament** including slicer rounding/startup. Without the optional loop, printed parts estimate **61.675 g**. Electronics, battery, bought caps/switches/sockets, wires and insulation are unweighed. The 80 g all-up aim leaves 9.246 g for them; the 100 g ceiling leaves 29.246 g. These are budgets, not verified assembled weights.

The battery envelope remains provisional at 20 × 6 × 40 mm; measure the actual cell before committing a handle print. Print the small mechanical coupons first. PETG force, drop/impact strength, repeated latch life, comfort and printed tolerances need physical testing. No print was started automatically.

## Architecture references

[Prusa's modeling guide](https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135) explains sloped overhangs, short bridges, printable wall widths and the need to test fit. This informed the sloped window roofs and continuous rails. A published [polymer isogrid cylinder study](https://sciforum.net/manuscripts/11174/manuscript.pdf) also reports unsuccessful support-free printing attempts; a lattice label alone is not proof of printability. V11's geometry and actual slicer output are checked independently. No external mesh was copied, and those sources do not establish this wand's strength.

## Rebuild and inspect

Install [requirements.txt](requirements.txt) in a local virtual environment. The CAD imports the retained V2 reference sources. Write all outputs to fresh directories, preserving released exports:

```sh
python -B wand_cad.py --out NEW_GEOMETRY_DIRECTORY
python -B check_geometry.py
python -B print_projects.py --out NEW_SLICE_DIRECTORY --slice
python -B verify_release.py --check
```

Serve the repository and open [the assembled comparison](preview/). Select either hand, Compare, Window structure, Hollow handle or Remove loop. The grey comparison is V10. The black keycaps and blue board in the viewer are purchased/reference components, not print parts. V9 remains an archived rejected experiment; V10 is retained unchanged for comparison.
