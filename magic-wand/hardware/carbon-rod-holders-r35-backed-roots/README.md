# R35 reinforced mounts

[Watch the complete assembly](../carbon-rod-holders/assembly/?version=r35&component=keys).

The R34 two-part test was stopped at layer 38 after the key carrier developed a
tangle at its centre. The slice shows a C-shaped rod clip printing on its own
beside the deck. All four perforated pads attached to the deck. The failure
photo shows the body and pads still in place, with loose filament at the clip.
The footage does not resolve the first contact or movement.

R35 joins the clip crown to the deck with two tapered side braces and a longer
centre brace. The DFRobot bracket uses a thin crossbar to join its front feet
from the first layer. The original rod opening, flex arms, board positions,
keepers and connector paths are retained. The ten-part plate includes the two
DFRobot post clips, XIAO holder and keeper, battery holder and door, 0.4 mm
spacer and twelve-wire cable clip.

The OP1 connector opening also had a ledge that started printing above empty
space. A small removable support backs its first perimeter at 15.8 mm print
height. Break up and peel the support through the outboard connector opening.
Pick out the remaining interface and inspect the connector, screw and wire
paths before seating the board. Remove the labelled adhesion pads and brims.
Physical support removal, rod grip and switch travel are first-fit checks.

- [Checked print-only project](exports/R35-Reinforced-print-only.3mf)
- [Editable Studio layout](exports/R35-Complete-A1-mini-PETG-layout.3mf)
- [CAD fit checks](exports/geometry-checks.json)
- [Original slice audit](exports/audit.json)
- [Reopened slice audit](exports/reopened-audit.json)

The 0.4 mm A1 mini slice uses 250 °C nozzle, 60 °C textured PEI and Smooth
Timelapse. The estimate is 1 h 47 min and 17.99 g with the wipe tower. The
deposited paths pass 212 early connection checks. The first OP1 ledge is backed
by the support interface. The working-space audit describes the finished
assembly after the connector support is removed. The physical trial should
also check the carrier overhangs at 18.6 and 40.0 mm and the bracket at 28.2 mm.

Run `assembly35.py` to regenerate the meshes and matching guide, then
`plate35.py <output-directory>` to slice. Run `audit35.py <archive>
<output-directory> <report>` on the resulting archive.
