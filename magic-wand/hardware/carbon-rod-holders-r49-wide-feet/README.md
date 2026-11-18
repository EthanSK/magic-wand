# Magic Wand R49 wide feet

R49 is the nine-piece R48 Magic Wand assembly on a revised A1 mini plate. It uses the same [assembled model and animations](../carbon-rod-holders-r48-edge-click/README.md). The printed hardware dimensions and installed positions come from R48.

[Print-only 3MF](exports/Magic-Wand-R49-All-Components-Wide-Feet-print-only.3mf) · [Editable Studio project](exports/R49-Wide-Feet-layout.3mf) · [Plate preview](exports/plate-preview.png) · [Verification](exports/verification.json)

The irregular, removable feet fill the space around each part. The DFRobot bracket retains both of its original tear-off ties. The XIAO keeper and battery door use thin feet connected at their outer edges. The key holder rides on a larger tear-off pad. Its cradle and front shelf each have an opening through the rib, with their original contact surfaces over the overhangs. The rear shelf has room to slide out past the key-holder pad.

The native slice estimates 5 h 16 min and 48.29 g. It uses the red Flashforge HS PETG Metallic profile with the textured plate on the A1 mini, 0.4 mm nozzle and 0.20 mm layers. The first object prints at 245 °C with a 60 °C bed. Smooth timelapse uses the small separate wipe tower.

The source is the [R48 wide-pad editable plate](../carbon-rod-holders-r48-edge-click/exports/wide-pad-retry/R48-Wide-Pads-layout.3mf). Run `prepare49.py` with that file, a new editable 3MF path and a JSON report path. Reopen the native slice with the same Studio version, then run the hardware and key phases of `audit49.py` using the R48 checked source directory. The reports follow the selected slice.

The native slicer still warns about floating regions in the key holder. The selected slice has no new unsupported roof strokes against the checked trial limits. All three support withdrawal paths pass on the selected G-code.

After the bed cools, lift the key-holder group, release the centre cradle, and slide out the front shelf and then the rear shelf. Peel the key-holder feet before fitting the touch-board cable. The first physical trial checks bed adhesion and removal effort.
