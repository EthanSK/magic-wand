# Print V4 candidate — 410 mm helix wand, both hands

This revision restores the original crossed helix and continuously tapered wand silhouette. It preserves Print V2 and V3 unchanged. Weight reduction comes from hollow interiors and thinner walls. No firmware or installed hardware is changed. Printed strength, fit, spring force and comfort remain unverified.

## Complete project and variants

- **Complete:** `Print-4-complete-left-right-helix-410mm.3mf` contains **both left- and right-hand handles**, one matching lower shaft, one upper shaft, head base and cover, bottom cap, battery sled, three socket inserts and three keepers: **14 instances**. Choose one grip for a working wand; the other parts are shared, as in V2.
- **Keep the printed V2 grip:** `Print-4-upper-only-helix-410mm.3mf` contains four replacement upper parts. Its lower shaft mates at 140 mm. Reuse the printed grip, cap and existing buttons.
- **Individual new grips:** `Print-4-left-handle-comparison.3mf` and `Print-4-right-handle-comparison.3mf` permit inspection and mass comparison of either hand separately.
- **Small trials:** `Print-4-compact-button-fit-test.3mf` and `Print-4-slim-bayonet-fit-test.3mf`. Try them before the full print. The coupon checks the slim joint; the old full-size grip joint remains unchanged.

Projects live in the repository's `magic-wand-3d-models/` directory. The new 160 mm grip and old 140 mm grip use different lower shafts; do not mix them. Both assembled versions end at 410 mm. Purchased switches, sockets and caps are not printed parts.

## Requirement checklist

| Request | Modelled change and evidence |
| --- | --- |
| Keep the original wand appearance | Original counter-wound 90/72 mm pitch helix, 1.2 mm ridge height. Real mesh probes confirm it exists. Original/new assembled views are available in the preview. |
| No waist or joint bulges | Core diameter continuously decreases from 24.84 mm at the grip joint to 19.8 mm at the middle seam and 17.9 mm at the head neck. Profile sampling rejects outward steps. Helix ridges are decoration on that taper. |
| Add 70 mm | 410 mm overall, compared with 340 mm V2. Both lower-shaft variants end at the same height. |
| Make the shafts lighter | 1.2 mm long-span skins with larger interior cavities; annular joint reinforcement stays inside the taper. Minimum wire route remains 10.4 mm. |
| Keep the grip thickness, hollow the inside | Original outer grip feel and oval loop, 1.2 mm grip shell and 1.6 mm loop shell. Battery supported by thin webs and an open ladder sled, not a filled block. |
| Raise buttons and adjust thumb | All buttons initially raised 20 mm; thumb then lowered 8 mm relative to that. Final centres: thumb 129, index 111, middle 85 mm. Grip and loop raised 20 mm. Side angles retained and mirrored. Purchased-cap travel envelope clears the loop in both hands. |
| Smaller button fittings | 16.4 × 16.4 × 6.6 mm open inserts recess directly into 16.8 mm openings, with small rear stops/front lips; 14.8 × 14.6 × 1 mm socket keeper. No 24 mm platform, enclosing cube or printed keycap. Original socket/post holes and alignment preserved. |
| Fit-and-rotate at every shaft connection | Three 38° push-and-twist joints, including the former plain middle connection. Entry, cam, stop and locked pull checks cover both slim joints. Old grip mating interface preserved. |
| Head joins smoothly | Head neck and upper shaft core both 17.9 mm diameter. No extra external collar. |
| Softer diamond point | Sims-style faceted head, 40 × 37 × 58 mm, nominal 1.2 mm edge/tip rounding. |
| Cover cannot pull sideways | Two captured flared dovetail feet; an upward diagonal slide clears, but sideways pull engages shoulders. Shallow detent retains the cover. |
| Remove unnecessary diamond side holes | Old optional tape slots removed. Cables run down the internal passage. |
| Keep the Sense stable | Upper edge pockets, four seats, corner guides and a lower spring release clip. PCB resting, stop, released-pivot and flexed-clip clearances checked. |
| USB and solder access | USB-C points upward and stays exposed. Rear battery-pad cavity, side pad space and forward wire route retained. Plug and solder-space probes clear both head halves. |
| Enough cable space | At least 10.4 mm main route and 6 mm forward route near the PCB. Eight individual wires, or six with shared button ground, are planned. Actual insulated wires must still be trial-fitted. |
| Bottom battery access | Removable twist cap retains its previous mating shape. Open sled and loose guides use a provisional 20 × 6 × 40 mm envelope; actual cell product is not verified. |
| Both hands in the delivered project | Both grips are actual build instances in the complete 3MF, checked against its archive contents. A separate right STL alone is insufficient. |

## Buttons and assembly

Use the purchased [Kailh Choc hot-swap socket](https://thepihut.com/products/switch-sockets-for-kailh-choc-compatible-keys-10-pack) and [slim caps](https://thepihut.com/products/black-kailh-choc-slim-key-caps-x-10-pack). The [CPG135001S30 socket drawing](https://cdn-shop.adafruit.com/product-files/5118/5118-Choc-Socket.pdf) defines the retained footprint. The preview cap is a 17.5 × 16.6 × 5.2 mm reference block, not an exact underside model. Orient its 16.6 mm side across the insert, and trial full travel with the actual cap.

Seat the bare socket in its pocket, slide the keeper over it, solder two wires to the socket terminals, then fit the switch and purchased cap. Secure the wire inside the printed body so pulling does not load the terminal. The keeper is an electrical-socket retainer, not a decorative cap. The recessed insert is held by rear stops and small front lips; those lips need a PETG flex trial.

Fit empty joints first: push at the entry orientation, turn 38° to the stop, and leave enough cable slack for the rotation. The geometric cam contact is deliberate; an overlap measurement there does not mean a rigid collision-free joint or prove the printed detent force. Remove the head cover by lifting along its sloped rails past the detent. Release the lower board clip before pivoting the PCB out of the upper pockets.

## Weight and print checks

`exports/print-comparison.json` records actual slicer estimates with the same P1S 0.4 mm PETG, 0.2 mm layers, three walls and 20% infill used for the V2 comparison. Supports and brims are included. Geometry volume is not used as a substitute for matched print mass. The complete plate includes two grips; compare equal contents.

Both handles use normal supports from the build plate. Protected contacts and sampled line/arc extrusion paths are checked to keep support out of the hollow grip, wire branches, battery space and board/USB cavity. A support blocker alone would not establish this. Head-cover external support is removable. These are slicer checks, not a physical-print test. No printer job is started.

## Rebuild

Keep the frozen adjacent `../v2/` sources defining the old mating interface and reference model.

```sh
python -m pip install -r requirements.txt
python -B wand_cad.py --out NEW_DIRECTORY
python -B wand_cad.py --check
python -B check_geometry.py
python -B print_projects.py --out NEW_PROJECT_DIRECTORY --slice
python -B check_sliced_paths.py --out NEW_REPORT.json
python -B verify_release.py --check
```

Use unused destinations. Omit `--slice` to create editable layouts only. The prepared projects register their process overrides so Bambu retains the settings on loading. Open the local `preview/` through a repository HTTP server to compare original/new, both hands, the retained grip, twist joints, board cradle, compact buttons and hollow handle.
