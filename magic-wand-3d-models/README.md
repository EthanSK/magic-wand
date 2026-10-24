# Magic Wand 3D models

Pull this repository, then open **[tapered-double-helix.3mf](tapered-double-helix.3mf)** in Bambu Studio.
It includes all four pieces arranged on one plate, with the printer and print settings saved.
[tapered-smooth.3mf](tapered-smooth.3mf) has the same shape without the two spiral ridges.
On GitHub, use **Download raw file** to download a 3MF.

## Two-print comparison

- **Print 1:** [original crossed pattern, 110 mm pitch](Print-1-crossed-110mm.3mf).
  This file is frozen from the committed first version; its source commit and checksum are
  recorded in `Print-1-crossed-110mm.json`.
- **Latest print:** [uneven crossed pattern, 90 mm and 36 mm pitch](tapered-double-helix.3mf).
  Its two opposite-winding strands turn at different rates: one makes 2.5 times as many
  turns, moving the crossings around the shaft. The pitch difference is now 54 mm,
  three times the previous 18 mm gap between the 90 mm and 72 mm strands.

The hole and platform are unchanged. Open the latest print for Ethan's new pattern, or
the frozen original for comparison. Clear the bed between jobs; these files are not
instructions to start two jobs together.

## Current prototype

- Continuous tapered body with **two raised spirals winding in opposite directions**, crossing
  each other. Ethan calls this the "criss-cross" or "like DNA" shape.
- One 54 mm flat button platform across the top. Its hole routes wires into the hollow shaft.
- Open holder for a bare XIAO board. Tape the board and battery on for this prototype.
- Four printable pieces form two detachable assemblies: the handle and the assembled shaft.
  Glue the shaft pieces together; the handle uses a push-and-twist joint.
- No battery compartment or guessed button mounting holes.

These are **prepared prototype print files, not a physically verified finished design**.
They were sliced for a **Bambu P1S, 0.4 mm nozzle, Generic PETG, textured PEI, 0.28 mm Extra Draft,
two walls, 20% infill, tree supports and 4 mm brim**. Select the actual loaded filament before printing.
Check the matching [joint coupons and XIAO holder](../magic-wand/hardware/printed-loop-wand/exports/)
first. Fit, comfort and printed strength are not yet tested.

The previous loop and plain handles use a different joint orientation; do not mix those pieces
with this tapered set. Other models and the full assembly guide are in the
[CAD folder](../magic-wand/hardware/printed-loop-wand/README.md).

## Source and maintenance

These 3MFs are generated exports. Edit the
[canonical dimensions and CAD](../magic-wand/hardware/printed-loop-wand/), not these copies.
After rebuilding the CAD, regenerate the print projects with Bambu Studio installed:

```sh
python3 magic-wand/hardware/printed-loop-wand/print_projects.py
# Use --bambu /path/to/BambuStudio for a non-default install.
# Use --scratch /path/to/scratch for temporary slicing files.
```

The saved print settings live next to the generator in `print-settings/`. They are the resolved
Bambu Studio 2.8.2 settings used for this prototype; they are not a promise of fit on another printer.
The output manifest records source and file hashes plus actual slicer estimates. The repository
tests reject stale projects, changed settings, mismatched exports and private paths in the archives.

```sh
python3 magic-wand/hardware/printed-loop-wand/print_projects.py --check
```
