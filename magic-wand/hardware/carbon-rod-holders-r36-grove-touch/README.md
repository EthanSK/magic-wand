# R36 Seeed Grove touch

For the next complete plate, use [R37 with the adjustable OP1 stop](../carbon-rod-holders-r37-adjustable-op1/README.md).

This candidate fits Seeed Grove Touch Sensor **101020037**, sold by Pi Hut
as **103326**, with the existing OP1 centre click. The two-key end is the
top in the assembly viewer. Both mounting screws are on the rod centre
line, one towards each end of the board. The thumb pad is slightly right
of centre because of the PCB layout. The connector faces the rod side
of the board and exits left of the rod, opposite the OP1 board.

## What fits

- Seeed's drawing and original Eagle board give a 20 × 20 mm body,
  1.6 mm thickness, and two Ø2.2 mm holes at 20.0 mm pitch. Including
  the two mounting tabs, the board occupies about 24.2 mm along the rod.
- The stock Grove cable plugs in before the board is lowered onto
  the bracket. Feed the free wire ends through the left opening and keep
  slack for the hinge. Remove both screws and lift the connected board
  before unplugging. Fit two M2 × 4 mm pan-head screws, no wider than
  3.8 mm across the heads. The underside moulded plug, latch, and wire
  flex still need a first-fit check.
- The Grove seat is 0.9 mm lower than the R35 DFRobot seat. The four
  Choc seats and OP1 stay at R35 height. A 1 mm rigid drop of the guard
  geometry starts to overlap the rod. The left cable pocket clears the
  existing ribs, rod braces, hinge supports and OP1 seats.
- The actual print list in [the BOM](complete-assembly.json) includes
  both matching holder keepers and the optional battery fit spacer.
  The two DFRobot-only printed clips have been replaced by the M2
  screws. The Grove module, screw and switch meshes are assembly
  references.

## Touch and click

Connect SIG, 3.3 V and GND to the XIAO touch input, supply and common
ground. The white NC lead can remain unused. The exposed electrode
should report touch for the full hold and clear on release. The separate
OP1 plunger provides mechanical click. At first fit, verify the plug
seats, the lead has slack, the snap arms release without excessive
force, and the switch clicks before the two stops engage and opens again on release.
The model measures 0.43 mm of travel to the stops. Omron specifies
0.3 ± 0.2 mm to operate for its 60M switch, so verify the installed switch
with a continuity meter before relying on it. Test sustained
touch and release at 3.3 V before depending on the assembly.

[Pi Hut exact product](https://thepihut.com/products/grove-touch-sensor?variant=40357140857027) ·
[Omron switch travel](https://components.omron.com/system/files/2024-07/datasheet_pdf/B152-E1.pdf) ·
[Seeed sensor and Eagle files](https://wiki.seeedstudio.com/Grove-Touch_Sensor/) ·
[Seeed Grove mechanical drawing](https://files.seeedstudio.com/wiki/GroveSystem/images/20_20dip.png)

## Checked print files

- [Print-only A1 mini project](exports/R36-Grove-print-only.3mf)
- [Editable Bambu plate](exports/R36-Complete-A1-mini-PETG-layout.3mf)
- [Original toolpath audit](exports/audit.json) and
  [reopened toolpath audit](exports/reopened-audit.json)
- [CAD clearance measurements](exports/geometry-checks.json)
- [Assembly animation](../carbon-rod-holders/assembly/?version=r36&component=keys)

Opus and a separate GPT review checked the model and sliced plate.
Both original and reopened toolpaths passed, including the nearby
printed walls around the connector and the two screw pilots.

The eight-part plate estimates 1 h 48 min and 17.81 g with the tested
Flashforge HS PETG Metallic recipe, 250 °C nozzle and 60 °C textured plate.
The toolpaths include the smooth timelapse tower. Enable Timelapse in
the print dialog and start the live camera after the send. Snip away
the marked pads and remove the local OP1 connector support from the
outboard opening before fitting the electronics.

## Regenerate

Run `assembly36.py` in the established CAD environment to export the
print meshes, clearance results and assembly animation. Run
`plate36.py <output-directory>` to slice the full A1 mini PETG plate.
Run `audit36.py <sliced-archive> <output-directory> <report>` to check the
actual paths. Use `assembly36.py --register` to add the guide to the shared
viewer. The exported guide contains a separate snap hinge view and an
exploded sequence for the board and both screws.
