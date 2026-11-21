# R57 mechanical notes

Millimetres, R53 assembly frame: rod along Y through X = Z = 0, +Y toward the two-key row, +Z up. Every figure is a design value from the source. The scripts have not been run, so none is yet confirmed by a mesh, a check or a slice.

## Hinge

- Axis at Y 29.3, as R53, so the 33.1 mm lever to the click button and the two crowns are unchanged.
- Pin: 3.0 diameter, 21.8 long, 0.5 taper at each end, one flat 1.2 from its centre to lie on the bed. A 1.9 diameter waist, 1.5 long, in the middle.
- Holder cheeks: |X| 7.4 to 11.5, from the deck to Z 20.5, on the print bed at the rear face. Hole 3.5 diameter at Z 16.5. Solid plastic round the hole: 1.6 behind (the first eight layers), 2.25 above, 1.9 in front, the whole cheek below.
- Paddle barrel: |X| up to 7.1, hole 3.6 diameter. 1.5 of solid above the hole (on the bed), 1.2 below the closing flat, 1.5 behind.
- Both holes lie flat in their prints. Each is round on the side that prints first and closed by two 45° faces and a 0.9 wide flat on the side that prints last, so neither needs support. The flat sits 0.3 beyond the round. Every hole mouth has a 0.6 tapered entry.
- At rest the pin lies on the bottom of the cheek holes and the paddle hangs on top of the pin. Those two contacts are the round, first-printed sides of the holes.

### Fit bracket

| | Cheek hole | Barrel hole |
| --- | --- | --- |
| Nominal gap all round a 3.0 pin | 0.25 | 0.30 |
| Pessimistic opening (hole 0.25 small, 0.30 sag on the flat) | 3.25 × 3.25 | 3.35 × 3.35 |
| Pessimistic pin (0.15 large) | 3.15 | 3.15 |
| Spare in the pessimistic case | 0.10 | 0.20 |

`verify57.py` gauges the sliced holes with a 3.2 rod. If a printed hole is tight, twist the pin through once; each cheek hole is 4 mm long.

### Play, by design

- Up and down and fore and aft at the hinge: 0.55 (0.85 toward the closing flats). Under a finger the paddle settles onto the round sides.
- Sideways at the hinge: 0.3 each way between barrel and cheeks. The sleeve on the switch and the lid towers still guide the front, as in R53.
- Pin end float: 0.55 each way (clip in a 2.0 slot, 1.2 clip in a 1.5 waist). The pin ends stay 0.05 inside the outer cheek faces and at least 2.4 stays in each cheek.

### Pin clip

- 1.2 thick peg, printed on its side. Two 0.98 legs with a 1.95 slot for the waist and a 1.7 mouth, so each leg opens 0.1 as it passes. A 0.6 slit above the slot makes the legs about 5 long.
- Its wide top stops on the paddle behind the slot and stands level with the top of the touch board for pinching.
- The paddle can ride up the full hinge play without the waist reaching the mouth.

### Fitting order

The pin goes in sideways. An upper key switch (X from 13.5, up to Y 28.85) and its cap sit in that path, so the pin is fitted before one upper key and that key comes out to remove it. The same was true of the R52 axle screw. Moving the axis clear of the keys would leave too little plastic behind the hole.

## Paddle top

- Flat top at Z 19.3, printed top down, as R53.
- The board touches: the pad end (Y −8.65 to 7.5), a rail along each long edge (|X| 8.6 to 10.6, to Y 20.5), a land round each post hole (|X| 5.9 to 8.6, Y 12.6 to 18.1) and the barrel top behind Y 25.75.
- Open under the board: |X| under 8.6 from Y 7.5 to 25.75, except the two lands. This covers the Gravity pin tails for a 30 mm or a 35 mm board.
- Two struts from the rails to the barrel sit 2.0 below the board. They print as 5 to 6 mm bridges.
- The rails are 2.0 wide and 4.0 deep.

## Posts and clips

- Same shaft (2.25 × 2.52), neck (1.7) and head as the earlier posts, so both existing clips fit. Neck 2.2 long, head top 3.0 above the board (it was 1.8).
- With the 0.8 clip: a board raised by 0 to 1.3 can be clipped. The earlier 1.0 neck accepted 0 to 0.15.
- With the 2.0 tall clip: a board that sits flat is held with 0.2 of float.
- Largest plausible part under the board: a SOT-23 package at 1.45, a pin tail at 2.0. Both now fall in the open zone.
- Print the bar on its front edge so the layers run along the necks.

## Not changed

Key openings, rod clips, OP1 pocket, locating fingers, lid rails, lid, sleeve, crowns, click travel and the R55 open-bay base. `checks57.py` compares the holder with R53 outside the yoke and repeats the R53 click and route checks.

## Open questions

1. Which side of the bought touch board carries parts, and how tall they are.
2. Real hole size after printing, especially the cheek holes with their closing flat facing forward.
3. Feel of the looser hinge at the pad. The sleeve should hide most of it.
4. Clip snap force on a 1.9 waist.
5. The R56 click itself has not been tried on the bench yet.
