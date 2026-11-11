# R30 DFRobot hole-mount bracket

[Watch the full assembly](../carbon-rod-holders/assembly/?version=r30&component=keys).

[See the snap hinge detail](../carbon-rod-holders/assembly/?version=r30&component=snap_hinge).

R30 replaces [R29](../carbon-rod-holders-r29-dfrobot-snap-arms/)'s tray with
a small orange bracket. Two posts on the bracket go up through the two
mounting holes in the DFR0030 V2 board. A printed clip snaps onto each post
above the board. The edge walls, lips, end stop and filament board keeper
are gone.

The two fixed supports and the flexible bracket arms are 2 mm closer to
the two-key end. The shift keeps the roots under the DFRobot board and
preserves the 0.48 mm switch stroke. The purple OP1 keeper and its
filament pin are removed. Slide the OP1 board into its slot, fit the
microswitch, then tape the rear of the board to the holder with removable
nonconductive tape. Keep the tape clear of the switch and connectors.

In the viewer, **Keys · full assembly** and **Keys · snap hinge detail**
are listed next to each other. The detail uses the same bracket mesh, the
same pinched mesh and the same poses as the full assembly, with the key
holder cut away round the supports.

## Board

| | Value | Source |
| --- | --- | --- |
| Outline | 22 × 35 mm | 22 mm published. A distributor sheet and the product photos support 35 mm, while the maker's text says 30. |
| Holes | 3.0 mm nominal | published. Photos suggest 3.2–3.4. |
| Hole pitch | 15.5 mm, checked over 15.0–16.0 | photos |
| Hole centres | 24.1 mm from the gold-pad end | photos |
| Thickness | 1.6 mm | assumed. There is room for up to 1.8 mm at the clip. |

The gold pads are at the three-key end and the connector at the two-key
end. The released board's pad edge lines up with the Choc cap fronts.

## Retention

| Part | Size |
| --- | --- |
| Seat rails | X 8.6–10.6 each side, under the board edges |
| Post | 2.25 mm across the pitch × 2.52 mm along the board, through each hole |
| Neck | 1.7 mm diameter, 1.0 mm long above the board |
| Head | same section as the post, chamfered top, 1.8 mm above the touch face |
| Clip | 0.8 mm thick, 3.6 × 4.0 mm, 0.1 mm snap on each jaw |

The posts are narrow across the pitch, so the board has 0.375 mm clearance each
way at the nominal pitch. Along the board the nominal clearance is 0.24 mm. The board
sits on the rails and pads. The clips stop it lifting, and the post heads
stop the clips. The post section is round on one side and pointed on the
other. Printed rear face down, each post is a horizontal boss with its point
underneath, like a teardrop hole.

To remove the board, unplug the lead, push both clips towards the gold pads
and lift the board off. That uncovers the pinch pads. Pinch them to lift the
bracket off.

## Checks

The [geometry checks](exports/geometry-checks.json) sample:

- the click stroke with the board and clips fitted
- the bracket's pinched lowering and the arms springing back
- a straight lift without pinching, which the support holes stop
- the board lifting off the posts, and the fit at 15.0–16.0 mm pitch
- the clips sliding off, and the clip, seat and hole capture contacts
- the lead, the stops and the front alignment

These are estimates: the board length, hole pitch and position, thickness,
any parts near the holes or under the board, the Gravity plug, the OP1
parts, the Choc cap outline and PETG stiffness. CAD fit covers 15–16 mm
pitch with the published 3 mm holes. The first printed fit still needs to
check the actual board, hinge flex and clip retention.

## First-fit plate

- [Sliced A1 mini plate](exports/R30-DFRobot-Hinge-A1-mini-PETG.gcode.3mf)
- [Editable Bambu Studio project](exports/R30-DFRobot-Hinge-A1-mini-PETG-layout.3mf)
- [Toolpath and round-trip checks](exports/print-checks.json)

The plate contains one key holder, one bracket and two clips. Bambu Studio
estimated 1 h 21 min and 11.73 g of PETG with smooth timelapse. The actual
startup commands wait for 255 °C at the nozzle and 70 °C at the textured
PEI plate before the first object.

The original and reopened slice have no Studio warnings. Both have
clear working openings, continuous starts and attached tear-away pads.
There are four pads on the carrier and two on the bracket. The small
wipe tower is a timelapse helper and clears the closest part by 22.99 mm.
The existing Choc pockets have some exposed bridge edges that may need
light cleanup. Check that the Choc parts slide freely and test the clip
and hinge fit on the first print.

Generate the CAD with `python3 assembly30.py` and slice it with
`python3 plate30.py --scratch <directory>` through the geometry budget runner.
