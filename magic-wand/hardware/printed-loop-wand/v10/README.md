# Print V10 — continuous solid helix body with separate slots

V10 / S410-R6 restores the supporting tube and the complete original raised spiral strips. The rejected open-braid interpretation is not used. Independent elongated slots remove material between the spiral strips, while three continuous longitudinal lands and local joint/hardware protection remain. The body is hollow inside; “solid” refers to the supporting skin and raised spiral, not a filled plastic core.

## Design and retained features

- Same 410 mm length, continuous taper and counter-wound 90/72 mm spiral pitches. Slots do not cut into either full spiral strip or use the spiral itself as the void pattern.
- Nineteen separate body slots: five in the grip, seven in each shaft. Each is approximately 4.6 × 12 mm, with rounded lower corners and a 45-degree upper roof for upright printing. Their angles follow available space between the complete spiral strips and three 3.2 mm uninterrupted supporting lands. Local joint, battery, button and loop-mount regions remain solid.
- The loop has four elongated rounded slots, approximately 6.8 × 14 mm, through its outer-to-inner contact face, replacing little bores. Its hollow 18 × 12 mm section and 1.2 mm skin retain continuous side edges and crossbars.
- Upper/thumb-region loop centreline reach is approximately 49 mm, lower return 39 mm. The original YZ plane and button angles are retained. The loop remains near the butt.
- Buttons stay at 139 / 135 / 109 mm from the butt, with unchanged radial placement and 4/26 mm spacing. Bought Choc switches/sockets/caps use the retained thin direct-slide plates.
- The universal loop attaches to either handed stem through two captured dovetails and an integral side release tongue. Press the tab outward, lift 22 mm, then move away. Battery, buttons and wiring remain in the stem. Small receiver pads remain on the back without the loop.
- Head, captured cover, board clips, USB/solder clearance, battery guides and 10.4 mm main wire route remain compatible. Shaft joints still push in and turn 38 degrees; leave wire slack.

## Print files

- `Print-10-complete-left-right-top-slide-410mm.3mf`: **12 actual build instances** — both handed stems, one universal loop and one shared set of the other parts. Choose one stem for a working wand.
- `Print-10-one-left-wand-410mm.3mf`: **11 instances**, one complete wand including its loop.
- `Print-10-detachable-loop-fit-test.3mf`: actual socket/release-foot coupons. Print this small fit test first.
- `Print-10-top-slide-button-fit-test.3mf`: retained switch plate and receiver coupon.
- `Print-10-slim-bayonet-fit-test.3mf`: retained slim joint coupon.
- `Print-10-upper-only-helix-410mm.3mf`: four upper replacement parts retaining a previously printed V2 grip. Whole-V10 mass and loop changes do not apply to that combination.

## One-wand mass and limits

Reference PETG slice: **76.072 g of printed parts with the loop**, or **65.902 g without**. The loop itself is 10.170 g. V8 was 75.821 g, so the complete detachable version is about 0.251 g heavier overall despite removing material with slots; the added attachment mounts offset the saving. Do not describe the whole assembly as lighter than V8.

Discarded support/brim adds 4.909 g; total consumed filament is 81.08 g including startup/rounding. Battery, board, switches, sockets, caps and wires are unweighed. With the loop, 23.928 g remains for that hardware to meet the 100 g assembled ceiling, or 3.928 g for 80 g. Without the loop, the allowance for 80 g is 14.098 g. Assembled mass is unverified.

Reference settings: P1S, 0.4 mm nozzle, PETG, 0.2 mm layers, three walls and 20% infill in remaining locally thick regions. Tube skin remains 1.0 mm, with locally reinforced interfaces. The loop prints on its broad side; carefully remove supports around its release tongue before testing. The six reference slices have no object warnings.

Digital checks cover 18 closed single-body meshes, the full spiral strip crests and edges, longitudinal lands, slot passages, captured mounts, released slide past bought caps, wire/battery/board/USB clearances, button insertion, head capture and monotonic taper. Sampled sliced-path checks cover actual interior routes, body slots, loop slots and mount slide channels. The portable rebuild matches all 18 mesh hashes.

These are geometry and slicing checks, not measured PETG strength, spring force, fatigue, drop resistance or physical comfort. Test the attachment coupon and handle/frame gently before relying on them. The battery envelope remains provisional at 20 × 6 × 40 mm; measure the actual cell before printing the complete grip. No print is started and no hardware is contacted.

## Preview and rebuild

Use **Loop attached / detached / off**, **Loop profile**, **Remove loop**, both hands, **Compare**, and **Hollow handle** in the preview. Board, battery, bought caps and airflow/contact markers are reference graphics, not printed parts.

Keep adjacent frozen `../v2/` dependencies and install `requirements.txt` in a Python virtual environment. Use new unused output destinations:

```sh
python -B wand_cad.py --out NEW_EXPORTS
python -B check_geometry.py
python -B print_projects.py --out NEW_PROJECTS --slice
python -B check_sliced_paths.py --out NEW_PATH_REPORT.json
python -B compare_mass.py --v1 V1_SINGLE.3mf --v2 V2_SINGLE.3mf --previous V8_SINGLE.3mf --current V10_SINGLE.3mf --out NEW_MASS_REPORT.json
python -B verify_release.py --check
```
