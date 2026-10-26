# Print V7 — slimmer ventilated wand, both hands

V7 preserves the 410 mm wand, helix, continuous taper, raised button centres, bought Choc fittings, board retention and both hands. It makes the grip and finger loop slimmer, opens flute-like vents, and hollows the battery cap further while retaining the previously checked hollow head. Earlier versions remain unchanged. This is a PETG mechanical candidate; printed strength, comfort and assembled mass are unverified.

## Weight target and measured scope

The target is under 80 g fully assembled if practical, with 100 g as the ceiling. The reference P1S PETG slice estimates **75.688 g of printed parts for exactly one left wand**, versus 91.027 g in V6: **16.85% less**. The grip alone is 35.859 g versus 45.908 g, about 21.9% less. Removable support/brim adds 6.520 g; total consumed filament is 82.30 g including slicer startup/rounding. Do not call that waste part of the finished wand.

The actual battery, board, three switches, sockets, keycaps, wires and insulation have not been weighed. They must total no more than **24.312 g** for the assembled wand to stay at 100 g, or **4.312 g** for 80 g. The 80 g assembled goal is not established. The report excludes all those bought components and never uses the both-hand plate's weight as one wand.

## Changes from V6

| Requirement | V7 implementation | Check |
| --- | --- | --- |
| Slimmer grip | 1.6 mm less core diameter above the cap zone; gradual transition from unchanged bottom ring | Source radius and assembled comparison |
| Thinner finger loop | 18 × 12 mm section instead of 22 × 14 mm; same path family, inner rear contact curve retained | Both handed assembled views |
| Lighter hollow handle | 1.0 mm grip skin, 1.2 mm loop skin; open ladder battery sled and thin guide webs retained | Mesh/clearance checks and matched PETG extrusion mass |
| Flute-like air openings | Six 6 mm nominal grip openings per hand; ten 5.2 mm shaft openings; four 5 mm side-through loop holes | Solid probes and sampled sliced extrusion paths through the holes |
| Keep helix | Vent angles selected in the actual gaps between both ridges, with flared mouths and rounded 45-degree upper slopes | Rib material probes plus assembled view |
| Hollow other low-load areas | 1.0 mm shaft skins, shorter internal transitions and 1.2 mm cap floor; previously checked hollow V6 head retained | Joint, cover, board and wire checks |
| Keep fittings and controls | Thumb 129 mm, upper side 125 mm, lower side 99 mm; side angles/radial placement unchanged | Six plate insertion paths, cap clearance and socket fit |
| Keep complete project | Both left/right grips are actual build instances | Archive build-list checks |

The openings are ventilation, not waterproofing. Keep conductors insulated and secured away from the openings. No holes cross the battery cell region, loop attachment roots or twist-lock anchors. The 10.4 mm minimum main wire route remains. The flute openings are softly pointed teardrops rather than exact circles so their upper slopes print more cleanly upright. Their external mouths flare by 0.35 mm.

## Files

- `Print-7-complete-left-right-top-slide-410mm.3mf`: **11 instances** — both handed grips plus one shared set of other parts. Choose one grip for one working wand.
- `Print-7-one-left-wand-410mm.3mf`: **10 instances**, exactly one wand for comparison.
- `Print-7-upper-only-helix-410mm.3mf`: four replacement upper parts for an already printed V2 grip; this retains the old grip and its original weight/buttons. The 75.688 g figure does not apply to that option.
- `Print-7-top-slide-button-fit-test.3mf`: unchanged thin plate and receiver coupon.
- `Print-7-slim-bayonet-fit-test.3mf`: unchanged slim joint coupon.

V7 changes the two new grips, both lower-shaft variants, upper shaft and battery cap. The V6 hollow head shell and rail reinforcement are retained; small sloped struts now support its upper board pockets. The bought-hardware apertures, thin plates, ladder sled, old V2 reference grips and joint coupon are retained. A new complete V7 is the coherent lightweight version; the old head and mating hardware remain compatible.

## Assembly and retained features

The thin rounded button plate slides down 8.4 mm from above directly into integral grip guides. Seat and wire the bought socket first, then slide the empty plate into place; press the bought Choc switch into the socket and fit the bought keycap. The switch blocks the plate lifting. Remove the switch before lifting out the plate. No printed decorative cap, separate keeper or glue is required.

All three shaft joints push in and turn 38 degrees. Leave cable slack before twisting. The diamond cover has captured flared rails and lifts diagonally upwards; a sideways pull meets retaining shoulders. The board USB end enters fixed upper pockets, then the lower end clips past the bridge spring. USB points upwards and remains exposed; side pads, rear battery pads and the forward wire route retain clearance.

The battery chamber still uses a provisional 20 × 6 × 40 mm cell envelope. Measure the actual cell before a full print; the model does not establish product compatibility. Test the small socket/joint coupons and inspect the printed thin walls, loop roots and head clip before loading the handle. Geometric/slicer checks do not establish PETG force, layer adhesion, fatigue or drop resistance.

## Rebuild

Keep the adjacent frozen `../v2/` source dependencies and install `requirements.txt` in a virtual environment. Use new unused output locations.

```sh
python -B wand_cad.py --out NEW_EXPORTS
python -B wand_cad.py --check
python -B check_geometry.py
python -B print_projects.py --out NEW_PROJECTS --slice
python -B check_sliced_paths.py --out NEW_PATH_REPORT.json
python -B compare_mass.py --v1 V1_SINGLE.3mf --v2 V2_SINGLE.3mf --previous V6_SINGLE.3mf --current V7_SINGLE.3mf --out NEW_MASS_REPORT.json
python -B verify_release.py --check
```

The prepared settings use P1S 0.4 mm PETG, 0.2 mm layers, three walls and 20% infill in the remaining locally thick regions. Most spans are explicitly hollow; setting infill to zero is not a substitute for designed walls. The grips use normal supports with internal blockers; the head retains its prior print orientation and support strategy; sampled extrusion paths also check that supports do not enter wire/board/battery clearances or the air-hole interiors. No hardware is contacted and no print is started.
