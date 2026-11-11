# R34 straight OP1 board

[Watch the assembly](../carbon-rod-holders/assembly/?version=r34&component=keys).

The OP1 mouse-switch board runs parallel to the rod and sits 7.45 mm to
its right to clear the underside connector. The board's underside stays
9.2 mm above the rod centre. The DFRobot touchboard remains centred on
its rear snap hinge. The bracket pusher meets the switch in its new
position, and the two travel stops limit the touchboard's movement.

The six crosswise finger guards and their rod and edge attachments
carry over from R33. The optional [battery spacer](../carbon-rod-holders/assembly/?version=r34&component=battery)
uses 15 angular vents while keeping the same 0.4 mm thickness and
outside shape. The [complete plate list](complete-assembly.json)
includes the keeper clips, battery door and 12-wire cable clip.

- [Sliced A1 mini first-fit plate](exports/R34-Complete-A1-mini-PETG.gcode.3mf)
- [Editable Bambu Studio project](exports/R34-Complete-A1-mini-PETG-layout.3mf)
- [Original and reopened print checks](exports/print-checks.json)

The ten parts slice at 250 °C nozzle and 60 °C textured PEI with Flashforge
HS PETG Metallic. Studio estimates 1 h 44 min and 17.0 g, including the
wipe tower for Smooth Timelapse. The original and reopened slices passed
the checks for working openings, guard and stop joins, and all 15 spacer
vents. Remove the labelled pads and brims before assembly.

On the key carrier, approach the narrow ties from the pad side and cut
their exposed middles. The two ties beside the opening have carrier
material directly behind them. Leave a small stub for cleanup to keep
the cutter away from the wall. On the 0.4 mm spacer, flex the brim
to peel it away while supporting the spacer.

The sliced pusher tip retains at least 95.7% of its checked section.
The model gives the switch 0.48 mm of travel before the stops touch.
The [Omron drawing](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/5389/D2FC_Datasheet_EN.pdf)
allows up to 0.50 mm before the switch clicks. Confirm the installed
switch clicks and releases without forcing the bracket against the stops.

`assembly34.py` regenerates the edited meshes, [fit checks](exports/geometry-checks.json)
and matching animation assets. Prepare the plate with
`../carbon-rod-holders-r32-complete-assembly/plate32.py --source . --scratch <directory> --slice --filament-profile "Flashforge HS PETG Metallic"`.
Run `audit34.py` on the sliced archive through the repository's geometry
budget runner. Fit of the actual electronics, hinge flex and comfort
need a printed trial.
