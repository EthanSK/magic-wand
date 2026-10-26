# Print V6 candidate — side buttons raised 14 mm

This revision moves only the side-button pair upward by 14 mm relative to V5. Thumb stays at 129 mm; the upper side button moves from 111 to 125 mm, 4 mm below the thumb, and the lower side button moves from 85 to 99 mm. Their 26 mm spacing, side angles and radial placement stay unchanged. Both handed handles are included. All V5 mechanisms, the helix/taper and thin top-slide plates remain. All earlier versions remain unchanged. Physical PETG fit and strength remain unverified.

## Files and contents

- `Print-6-complete-left-right-top-slide-410mm.3mf`: both handed grips plus one shared set of shafts, head halves, battery cap/sled and three thin plates. **11 instances**. Choose one grip for a working wand.
- `Print-6-one-left-wand-410mm.3mf`: exactly one complete left wand, **10 instances**, used for the mass comparison.
- `Print-6-upper-only-helix-410mm.3mf`: four replacement upper parts for a printed 140 mm V2 grip. Its existing button fittings remain unchanged.
- `Print-6-top-slide-button-fit-test.3mf`: one plate and a small receiver coupon. Test the bought socket, switch, cap and two wires here before printing the grip. Remove the coupon's accessible normal supports first.
- `Print-6-slim-bayonet-fit-test.3mf`: the unchanged slim shaft-joint trial.

The complete new grip joins at 160 mm; the retained V2 grip joins at 140 mm. Use its matching lower shaft. Both assembled alternatives end at 410 mm. Purchased hardware is not included as printable mesh parts.

## What changed at the buttons

| Feature | V2 | V4 | V5 |
| --- | --- | --- | --- |
| Separate fitting | 20 × 20 × 6.6 mm cassette plus keeper | 16.4 × 16.4 × 6.6 mm cassette plus keeper | One rounded 16.4 × 17.2 mm plate, 1.3 mm face thickness; 2.5 mm total including small rear feet |
| Surround | 24 mm square platform | 16.8 mm opening with internal stops/lips | Rounded 17.4 × 19 mm surround built into the wand, with a backed socket recess |
| How it fits | Platform and separate cassette | Radial push into the grip | Slide **downward 8.4 mm from above** into captured tracks; bottom stops prevent further descent |
| Separate printed keeper/cap | Keeper | Keeper | None. Bought keycap remains the press surface |
| Opening into hollow core | Large local opening | 16.8 mm window | 6.4 mm teardrop cable outlet behind the backed recess |

The V5 face is not substantially narrower than V4: a 14 mm switch opening and its supporting rim still have to fit. The depth and separate keeper have been removed. Compared with V2, the plate face is about 29% smaller in area and the visible 24 mm platform is gone. The rim blends into the curved grip rather than forming an enclosing box.

The 14 mm square in the thin plate is the standard switch aperture. It is occupied by the bought Choc switch, then covered by the bought slim keycap. It is not an empty 14 mm passage through the wand. The socket seat is integrated into the wand behind it, with a floor, footprint clearances and two short retaining catches. The 6.4 mm wire outlet leads from that recess into the main hollow core.

## Assembly — no glue

1. Try the small fit coupon first with the exact purchased Choc socket. Remove accessible support and check the sliding clearance before wiring.
2. Solder the two wires to the bought socket's terminals and insulate them. Feed them through the small cable outlet and secure them so pulling cannot load the terminals.
3. Seat the socket in the integral wand recess. The short catches retain it. This fit needs a real trial; do not force a socket into an undersized printed pocket.
4. Slide the **empty thin plate** down from above by 8.4 mm. Its rear feet enter the guides and reach the bottom stops. It cannot pull straight outward.
5. Press the bought Choc switch through the plate into the socket, then fit the purchased cap. The switch body in the recess also prevents the plate lifting. To remove the plate, remove the switch first, then lift the plate upward.

This is not a complete switch/socket cassette sliding in already assembled. Only the thin mounting plate slides; the bought switch presses into its socket afterwards. The source and preview distinguish that order. No decorative printed cap or loose printed keeper needs gluing.

Top-slide motion is checked in both hands, including the neighbouring plate/cap envelopes. The socket and lower switch housing envelope clear at rest. Side pull and downward movement encounter retaining geometry. These checks do not simulate PETG force, socket contact force or an exact purchased cap underside.

## Mass comparison

`exports/one-wand-mass-comparison.json` compares exactly one complete V1 mug wand, one V2 left wand and one V6 left wand. It gives printed-parts mass separately from removable supports/brim and total filament. The matched reference uses P1S 0.4 mm PETG, 0.2 mm layers, three walls and 20% infill. Grips use normal supports; other parts retain their geometry-specific support strategy. Electronics, battery, bought switches, sockets, keycaps and wires are excluded.

The original V1 project's 0.28 mm/two-wall estimate is recorded separately, since that was a different print setup. These are sliced filament estimates, not measurements of a physical print. The full both-hand plate is never used as one wand's weight.

## Retained features and checks

- Original 90/72 mm counter-wound 1.2 mm helix and continuously decreasing shaft core; no waist or external joint collars.
- 1.2 mm shaft/grip skins and 1.6 mm loop shell, with internal annular joint reinforcement. Minimum main wire route 10.4 mm.
- Grip/loop exterior retained, with thin battery webs and open ladder sled. Removable bottom twist cap; provisional 20 × 6 × 40 mm battery envelope, actual cell still unverified.
- Index/middle centres 125/99 mm, thumb unchanged at 129 mm. Both side buttons move up 14 mm from V5, keeping 26 mm spacing, original side angles and radial positions, mirrored for the right hand.
- All three shaft connections push-and-turn 38°. Old printed grip mating geometry remains unchanged.
- Head neck matches the 17.9 mm shaft core. Sims-style 40 × 37 × 58 mm diamond has nominal 1.2 mm edge/tip rounding.
- Head cover lifts along captured flared rails; a side pull is blocked. Old side tape slots remain removed.
- Sense upper pockets, corner guides, four seats and release clip retained; USB points upward and remains exposed, with rear battery-pad and side solder clearance and a 6 mm forward wire route.
- Watertight/single-body meshes, mechanical clearances and sampled sliced extrusion paths are checked. Both grips are actual build instances in the complete project. No hardware has been contacted and no print has started.

## Rebuild

Keep the adjacent frozen `../v2/` dependencies. Use unused destinations for outputs.

```sh
python -m pip install -r requirements.txt
python -B wand_cad.py --out NEW_DIRECTORY
python -B wand_cad.py --check
python -B check_geometry.py
python -B print_projects.py --out NEW_PROJECT_DIRECTORY --slice
python -B check_sliced_paths.py --out NEW_REPORT.json
python -B compare_mass.py --v1 V1_SINGLE.3mf --v2 V2_SINGLE.3mf --current V6_SINGLE.3mf --out NEW_MASS_REPORT.json
python -B verify_release.py --check
```

Open `preview/` through a repository HTTP server for assembled, original/new, handed, slide-in plate, board and hollow-grip views. The black cap and switch-body shapes are purchased-hardware references, not additional printed parts.
