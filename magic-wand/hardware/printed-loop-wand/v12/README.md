# Print V12 — flowing leaf windows and fuller rounded rails

V12 refines V11 rather than replacing its silhouette. Rounded leaf-shaped openings and gentle S curves give the perforated shell an Art Nouveau direction, while keeping the complete original raised counter-wound spiral. The grip's total opening area is about 12.3% smaller. The detachable loop's individual contact openings shrink from nominal 10 × 21 mm to 8.8 × 19.5 mm; its broad-face openings shrink from 5.6 × 19 mm to 5 × 17.5 mm. These curved profiles are not rectangles.

Four continuous axial rails widen from 3 to 3.6 mm. Their actual final depth increases from 1 to 1.6 mm in the grip and from 1.4 to 1.8 mm in the shafts, with 0.38 mm rounded inner corners. The grip's rails are added after hollowing so the reinforcement survives cavity subtraction. The loop skin increases from 1.2 to 1.45 mm. Added rail depth stays inside the established taper; the shell remains hollow.

## Retained design

The 410 mm length, continuously narrowing shaft, 90/72 mm counter-wound helix pitches and 1.2 mm ridge height are retained. The rounded diamond, clipped Sense cradle, upward USB access, captured sliding cover, 10.4 mm wire route, battery guides, three thin top-slide switch plates, old lower joint and slim upper twist locks are retained. Both handed stems retain their control positions: thumb 139 mm, upper finger 135 mm, lower finger 109 mm. The detachable loop stays in its existing plane and at the butt, with upper/lower centreline reach 49/39 mm. It releases with the side tab and a 22 mm upward slide, without unplugging controls.

## Print projects

- [Complete project: both handed stems and one shared set of other parts](../../../../magic-wand-3d-models/Print-12-complete-left-right-top-slide-410mm.3mf). Choose one stem for a working wand.
- [Exactly one left wand](../../../../magic-wand-3d-models/Print-12-one-left-wand-410mm.3mf), used for the mass estimate.
- [Upper replacement for the retained V2 grip](../../../../magic-wand-3d-models/Print-12-upper-only-helix-410mm.3mf).
- Test coupons: [button plate](../../../../magic-wand-3d-models/Print-12-top-slide-button-fit-test.3mf), [detachable loop](../../../../magic-wand-3d-models/Print-12-detachable-loop-fit-test.3mf), [bayonet](../../../../magic-wand-3d-models/Print-12-slim-bayonet-fit-test.3mf).

## Weight and checks

Exactly one left wand estimates **75.875 g printed PETG**, compared with V11's **70.754 g**: an increase of **5.121 g / 7.24%** for the smaller openings and reinforcement. Supports/brim add **4.465 g**; total slicer filament is **80.44 g**, including rounding/startup. Without the optional loop, printed parts estimate **64.560 g**. Hardware is unweighed: 4.125 g remains for the 80 g all-up aim, or 24.125 g for the 100 g ceiling. The all-up target is not verified.

All eighteen exported meshes are consistently wound, watertight single bodies. Checks cover both hands, wire/USB/board clearances, switch insertion paths, retained joints and cover capture, complete spiral material, actual reinforcement in final solids and no sampled shaft-window layer islands. All six prepared projects slice without reported warnings. The flat loop uses no brim and manually enforced support only at its mounting roots. Sliced extrusion checks include supports and first-layer adhesion across all aperture interiors and protected routes.

These checks establish geometry and sampled slicer clearance. They do not establish PETG breaking force, drop resistance, latch fatigue, comfort or printed fit. Print and flex a small sample before relying on the slender shell. The battery envelope is still provisional at 20 × 6 × 40 mm; measure the actual cell before committing the grip print. No physical print is started automatically.

## Rebuild and view

Install [requirements.txt](requirements.txt) in a local virtual environment. The source imports the unchanged V2 reference geometry. Keep released outputs immutable and use fresh output directories:

```sh
python -B wand_cad.py --out NEW_GEOMETRY_DIRECTORY
python -B check_geometry.py
python -B print_projects.py --out NEW_SLICE_DIRECTORY --slice
python -B verify_release.py --check
```

Serve the repository and open [the interactive comparison](preview/). Compare shows grey V11 beside coloured V12. Select either hand; use Window structure or Hollow handle for the reinforced open shell, and Loop profile for its curved apertures. The black bought keycaps and blue board are references, not print parts. V11 and earlier releases remain unchanged.
