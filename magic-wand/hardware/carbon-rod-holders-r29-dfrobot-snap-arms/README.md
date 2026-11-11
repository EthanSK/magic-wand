# R29 DFRobot snap arms

[See the snap hinge close-up](../carbon-rod-holders/assembly/?version=r29&component=snap_hinge).

[Watch the assembly](../carbon-rod-holders/assembly/?version=r29&component=keys).

R29 is [R28](../carbon-rod-holders-r28-dfrobot-touch/) with the hinge turned
round. The key holder now has two fixed supports, each with a hole on R27's
hinge axis (Y 10.1, Z 18.5). The touch tray has two flexible arms, each with
a rounded tab pointing outwards. Pinch the two raised pads, lower the empty
tray between the supports and let go. Each tab springs into the hole beside
it. There is no loose hinge pin and the key holder does not bend.

The board rails, end stop, filament board keeper, rear-loaded OP1 board and
its keeper, click stops, front alignment, height, lead path and all six
finger guards are R28's. The OP1 keeper only holds the OP1 board, and the
filament board keeper only holds the DFR0030. Neither is part of the hinge.

## Snap joint

| Part | Size |
| --- | --- |
| Support | 2.1 mm wide (X 3.4–5.5), 3.45 mm long, top Z 20.0, on a foot over the solid deck |
| Hole | 0.9 mm radius, through, roof peaked for rear-down printing |
| Wall round the hole | 0.6 mm above and behind, 0.677 mm over the print-facing peak |
| Arm | 1.2 × 1.4 mm, 10.8 mm from root to tab |
| Tab | 0.7 mm radius, 0.7 mm into the hole, 0.25 mm tip chamfer |
| Pinch | 0.98 mm at the tab |

Pinching moves the arm vertices themselves in the guide. The same bend
function makes the squeezed CAD for the checks. The PETG estimate (modulus
2000 MPa) is in the [geometry checks](exports/geometry-checks.json): pinch
force and root strain at the pads. The board covers the pads, so slide it
out before removing the tray.

## Checks

The geometry checks sample:

- the full click with the board fitted
- lowering the pinched tray and letting the arms spring back
- a straight lift without pinching, which the hole roofs stop
- the board and pin slides, the lead, the stops and the front alignment

These are estimates: the board thickness, the Gravity plug, the parts and
pins under the board (the arms leave 1.25 mm below it), the OP1 parts, the
Choc cap outline and PETG stiffness. A diagnostic rear-down slice with
supports disabled flagged floating regions on the key holder. A checked
support layout and a printed flex and fit trial are still needed.

Regenerate with `python3 assembly29.py` through the geometry budget runner.
