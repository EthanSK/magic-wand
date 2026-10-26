# Print V8 — lower ergonomic loop, higher controls and air to the hand

V8 / S410-R4 keeps the 410 mm crossed-helix wand and continuous taper. It corrects the V7 loop height, control relationship and ventilation direction. Both handed grips are included in the complete project. Earlier versions remain unchanged. This is a PETG mechanical candidate; physical comfort, cooling, strength and assembled mass are unverified.

## Requested corrections

| Requirement | V8 implementation | Evidence |
| --- | --- | --- |
| Loop at the bottom | Removed V7’s 20 mm loop uplift; lowest loop surface is about 3 mm above the butt, retaining cap clearance | Source path and assembled V7/V8 comparison |
| Higher buttons, clear of the loop | Every centre moves up 10 mm: thumb 139 mm, upper side 135 mm, lower side 109 mm above the butt | Both hands’ insertion paths and pressed-cap clearance |
| Preserve the useful spacing | Upper side remains 4 mm below thumb; side pair remains 26 mm apart; angles and radial placement stay unchanged | Manifest and fit report |
| Ergonomic mug shape | High index-side root at 126 mm; upper arm slopes down away from the pole, with a lower return near the butt | Assembled views; comfort still requires handling |
| Air reaches the contact face | Four rounded loop ports run from the outside through the inner finger-contact surface along local inward normals, rather than sideways through the broad faces | Eight unobstructed CAD probes and sliced-path checks across both hands |
| Vent the grip too | Three contact-facing grip outlets have separate outside intakes; shaft flute holes remain | Solid probes and sampled sliced extrusion checks |
| Preserve the wand | Original helix, taper, captured diamond cover, board retention, upward USB and cable routes retained | Mesh, taper, joint, board and cover checks |
| Complete project | Both left/right grips are actual build instances, plus one shared set of the remaining parts | 3MF build-list checks: 11 instances |

The thumb’s bought-cap envelope clears the loop throughout the checked stroke by at least 4.33 mm. The loop remains an 18 × 12 mm hollow section with a 1.2 mm skin. Its roots remain reinforced; they are excluded from the hollow core. Each loop port is approximately 7.8 mm wide by 6.5 mm tall, with rounded sloping upper edges. The grip and shaft skins remain 1.0 mm, with local joint reinforcement. The 10.4 mm main wire route remains.

The preview’s **Air to hand** view uses blue arrows for passage direction and amber patches for the inner contact surface. These annotations are not printable parts and do not claim measured airflow. Openings are not waterproofing; secure insulated conductors away from them.

## Mass: exactly one wand

The reference P1S PETG slice estimates **75.821 g of printed parts** for one left wand, including a 35.993 g grip. Removable support/brim adds 3.886 g; total consumed filament is 79.80 g including startup/rounding. V7 was 75.688 g of printed parts: this ergonomic correction adds about 0.13 g, rather than claiming another mass reduction. Earlier matched-setting baselines were V1 124.190 g and V2 126.621 g.

The aim remains under 80 g fully assembled where practical, with 100 g as the ceiling. Battery, board, switches, sockets, caps, wires and insulation are unweighed. Their allowance is **24.179 g** to remain at 100 g, or **4.179 g** to remain at 80 g. The 80 g assembled target is not established. Do not use the both-hand plate’s mass as one wand or count discarded support as finished mass.

## Print projects

- `Print-8-complete-left-right-top-slide-410mm.3mf`: **11 instances**, both grips and one shared set of the remaining parts. Choose one grip for one working wand.
- `Print-8-one-left-wand-410mm.3mf`: **10 instances**, exactly one wand for comparison.
- `Print-8-upper-only-helix-410mm.3mf`: four upper replacement parts for an already printed V2 grip. This does not apply the V8 handle/button changes, and the 75.821 g figure does not describe that combination.
- `Print-8-top-slide-button-fit-test.3mf`: thin plate and receiver coupon.
- `Print-8-slim-bayonet-fit-test.3mf`: slim joint coupon.

The normal full-wand shafts, head, cover, cap, sled, plates and coupons retain their V7 meshes. The retained-old-grip compatibility shaft separately corrects a decorative clearance that unnecessarily flattened part of its helix near the new higher button region; its mating interface is unchanged.

## Assembly and limits

Seat and wire the bought socket in the thin rounded plate, then slide the plate down 8.4 mm directly into the integral grip guides. Insert the bought Choc switch and keycap afterward: the switch blocks plate lift. Remove the switch before lifting out the plate. There is no separate printed cap, keeper or glue.

The three shaft joints push in and turn 38 degrees. Leave cable slack before twisting. The diamond cover has captured flared rails and lifts diagonally upwards; retaining shoulders block sideways removal. The board USB end enters fixed upper pockets, then its lower end clips past the bridge spring. USB stays exposed upwards. Side pads, battery pads and the forward wire route retain clearance.

The battery chamber retains a **provisional 20 × 6 × 40 mm cell envelope**. Actual battery fit is not established; measure the cell before printing the complete grip. Test the socket and joint coupons first. Inspect thin PETG walls, loop roots, head clip and cable insulation before loading the handle. Digital clearances and slicing do not establish layer adhesion, fatigue, impact strength, skin comfort or cooling.

## Rebuild and checks

Keep the adjacent frozen `../v2/` dependencies and install `requirements.txt` in a virtual environment. Give each rebuild a new unused output location.

```sh
python -B wand_cad.py --out NEW_EXPORTS
python -B wand_cad.py --check
python -B check_geometry.py
python -B print_projects.py --out NEW_PROJECTS --slice
python -B check_sliced_paths.py --out NEW_PATH_REPORT.json
python -B compare_mass.py --v1 V1_SINGLE.3mf --v2 V2_SINGLE.3mf --previous V7_SINGLE.3mf --current V8_SINGLE.3mf --out NEW_MASS_REPORT.json
python -B verify_release.py --check
```

Prepared projects use P1S 0.4 mm PETG, 0.2 mm layers, three walls and 20% infill in the remaining locally thick regions. Hollow spaces are designed into the CAD. Grips use normal supports and internal blockers, including the contact-facing port mouths and the vertical support-source regions above them. The release rejects object warnings and samples sliced extrusion through wire, board, battery and air-passage interiors. CAD checks cover all 15 meshes, both grips, insertion paths, cap stroke, board/cover capture, taper, helix and head-layer islands. No hardware is contacted and no print is started.
