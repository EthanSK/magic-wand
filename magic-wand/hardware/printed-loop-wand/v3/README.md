# Print V3 candidate — lightweight 410 mm wand

This mechanical prototype preserves Print V2 unchanged. It adds 70 mm overall, smooth slim shafts, three push-and-twist joints, a rounded diamond with a captured sliding cover, and an optional taller hollow grip with compact button inserts. Firmware is unchanged. Physical fit, flex, strength and comfort remain unverified.

## Choose the matching set

- **Full left-hand revision:** `Print-3-full-left-raised-buttons-410mm.3mf`: one left grip, matching lower shaft, upper shaft, head, cover, cap, open battery sled, three small socket inserts and three keepers. Thirteen instances. Purchased switches, sockets and keycaps are not printed.
- **Retain the printed V2 handle:** `Print-3-upper-only-410mm.3mf`: only the longer replacement lower/upper shafts, head and cover. Four instances. Reuse the V2 handle and bottom cap; its button positions stay unchanged.
- **Small trials:** `Print-3-slim-bayonet-fit-test.3mf` and `Print-3-compact-button-fit-test.3mf`. Test these before the complete grip. The coupon proves only the small joint; the full-size handle joint keeps its V2 mating geometry.

Projects are in the repository's `magic-wand-3d-models/` directory. The two lower shafts are different: the new grip joins at z=160 mm; the existing V2 grip joins at z=140 mm. Do not mix them. Both assembled versions end at 410 mm.

## Shape and weight

The 10.4 mm wire route stays open. Long upper spans have 1.6–2.6 mm nominal walls, with short reinforced collars at joints. The slender spans reach 13.6 mm diameter; the new middle/head collars are 17.9 mm. The head's neck matches that diameter, avoiding the old step. The diamond remains 40 × 37 × 58 mm; its edges and point have a nominal 1.2 mm rounding.

The new grip keeps the external thickness and loop shape, extends the grip section by 20 mm, and raises the loop with that extension. Index/middle button centres move from 91/65 to 111/85 mm. Thumb moves up 20 mm then down 8 mm relative to that, from 117 to 129 mm. Side angles stay 90° for thumb and −35° for fingers, mirrored for the right grip.

The grip has a modelled 1.2 mm shell; the loop has a 1.6 mm shell. These cavities exist in the CAD rather than relying on infill settings. Thin radial webs support the battery guides; the removable sled is an open ladder. Battery dimensions remain provisional: a 20 × 6 × 40 mm reference cell, with room for leads and loose spacers. Verify the actual protected cell and leads; do not compress it.

`exports/print-comparison.json` records slicer estimates against V2 with the same P1S 0.4 mm PETG material, 0.2 mm layers, three walls and 20% infill. Geometry volume alone overstates mass savings because the original includes sparse infill. Supports/brims and the cover's removable external support are included in project estimates. No physical mass or print time was measured.

## Compact button inserts

The old 24 mm platforms and 20 mm enclosing boxes are removed. Each open-sided insert is **16.4 × 16.4 × 6.6 mm** and recesses directly into a **16.8 mm** grip opening. Two internal stops take the inward push; small front lips retain the insert. Press the lips aside to remove it. Those lips and their PETG flex need a real trial.

The keycap footprint is [17.5 × 16.6 × 5.2 mm](https://thepihut.com/products/black-kailh-choc-slim-key-caps-x-10-pack); orient the 16.6 mm dimension across the insert. The cap covers the insert face in plan. The preview uses a black reference block, not a printed cap or an exact underside model. Check full key travel on the actual cap before printing the complete grip.

Switch aperture, plastic-post clearances, socket-boss holes and their centres retain V2's geometry. The [Kailh Choc hot-swap socket](https://thepihut.com/products/switch-sockets-for-kailh-choc-compatible-keys-10-pack) remains the electrical contact. Its [CPG135001S30 drawing](https://cdn-shop.adafruit.com/product-files/5118/5118-Choc-Socket.pdf) is the footprint reference. Fit the bare socket in the insert, slide the small keeper above it, solder the two wires to its metal terminals, then install the switch and purchased cap. The keeper is a socket retainer, not a keycap. Secure the wire inside the grip so pulling does not load the socket terminals.

## Head and assembly

Push each shaft joint in at its entry orientation, then turn 38° to the stop. The slim joints have three lugs, a cam and a shallow retaining pocket. Intentional cam contact is distinguished from unwanted collision. Feed cables with enough slack for the turn; fit and join the empty pieces first. Eight individual wires still need only one 10.4 mm tunnel; the board cradle has the retained forward 6 mm route.

The cover has two flared dovetail feet behind narrower mouths. At rest it clears; a sideways pull meets retaining shoulders, while an upward diagonal slide clears. Lift along the rails to remove it past the detent. The former side holes were optional tape slots, removed here because the board has a clip cradle. USB access remains open. The upper board pockets, four seats, corner guides and lower release clip remain, translated 70 mm with the head.

## Generate and verify

Keep the adjacent frozen `../v2/` sources: they define the existing handle interface and the comparison geometry.

```sh
python -m pip install -r requirements.txt
python -B wand_cad.py --out NEW_DIRECTORY
python -B wand_cad.py --check
python -B check_geometry.py
python -B print_projects.py --out NEW_PROJECT_DIRECTORY --slice
python -B verify_release.py --check
```

All export destinations must be unused. `--slice` uses installed Bambu Studio; omit it to generate editable layouts only. The right-hand grip STL is generated too; choose it instead of the left grip when arranging a right-hand project. Open `preview/index.html` through the repository's local HTTP server for original/new and retained-handle comparisons, joint views, board retention and a hollow-grip section.

The prepared process values are registered so Bambu retains the 0.2 mm / three-wall / 20% settings on loading. The final handle uses normal supports from the build plate, with protected internal contacts. Its slice no longer reports unsupported regions; inspect normal support removal and controlled bridging on the physical trial. The small switch trial is particularly useful for socket/keeper fit and the new print orientation. Never interpret a successful slice or mesh check as proof of printed strength. No printer job is started by these tools.
