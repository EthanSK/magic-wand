# R33 crosswise finger guards

[Watch the assembly](../carbon-rod-holders/assembly/?version=r33&component=keys).

Six rounded ribs run from the outside rails to the rigid rod saddle. The
finger-contact sections run crosswise and sit lower than the saddle. The two
outside rails remain as attachment points. The branches rise from both ends
in the rear-down print orientation, leaving only the middle of each rib to
bridge. The rod position and the spring clip openings are inherited from R32.

The DFRobot bracket has two openings beside the centre pusher. The bracket's
hinge arms, clips, pusher and travel stops keep their R32 geometry. The OP1
board retains the 25° position and cable access from underneath. See the
[R32 hardware notes](../carbon-rod-holders-r32-complete-assembly/) for the
dimensions, source drawings and physical-fit limits.

The [plate list](complete-assembly.json) includes the four key assembly parts,
XIAO holder and keeper, battery holder and door, patterned battery spacer and
12-wire clip. The print uses the A1 mini 0.4 mm profile, textured PEI and
Flashforge Metallic HS PETG at 250 °C nozzle and 60 °C bed. Remove the labelled
tear-away pads and the brims before assembly. The wipe tower serves smooth
timelapse.

- [Sliced A1 mini plate](exports/R33-Complete-A1-mini-PETG.gcode.3mf)
- [Editable Bambu Studio project](exports/R33-Complete-A1-mini-PETG-layout.3mf)
- [Original and reopened print checks](exports/print-checks.json)

Both slices passed the ten-part plate checks. The six saddle joints have
at least six consecutive 0.2 mm layers of connected paths across the bond.
Both crossbar windows have open centres and printed rims. The longest new
rib bridge is 7.4 mm. The print estimate is 1 h 46 min and 17.22 g.

`assembly33.py` regenerates the edited parts, [geometry checks](exports/geometry-checks.json)
and matching viewer data. Use `--make-current` to set the viewer default.
Prepare the plate with `../carbon-rod-holders-r32-complete-assembly/plate32.py
--source . --scratch <directory> --slice --filament-profile "Flashforge HS PETG Metallic"`.
Run `audit33.py` with the sliced archive, that scratch directory and a report
path. Run CAD and slicing through the repository's geometry budget runner.

Physical fit, rib flex and comfort need a printed trial.
