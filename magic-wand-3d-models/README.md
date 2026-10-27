# Magic Wand 3D models

**Latest candidate: [Print V17 — smooth lower handle attachment, both hands](Print-17-README.md).**

The curved lower return encloses its stud collar, removing V16’s exposed diagonal bridge and hanging toe. Only the universal removable loop needs reprinting; V16 stems still fit. One left wand estimates 75.048 g printed PETG. Physical fit and strength remain unverified.

**Previous candidate: [Print V16 — borderless recessed switches, both hands](Print-16-README.md).**

Square surrounds are removed, the bought switch/socket assemblies sit 3.4 mm deeper and the thin plates print flat. Two small side clips and lower stops retain the plates. The original helix, taper and recessed detachable-loop lock remain. Print the matching small switch test first; physical fit is unverified. One left wand estimates 75.226 g printed PETG, excluding bought hardware.

**Previous candidate: [Print V15 — recessed handle attachment, both hands](Print-15-README.md).**

The removable loop carries all pegs and release hardware; its receivers sit inside the original wand surface. With the loop off, the stem has no projecting attachment brackets. A 4 mm upward keyhole slide and 12° left cam turn lock the handle. The full raised helix, taper, controls and both handed stems are retained. One left wand estimates 76.139 g printed PETG; hardware and physical fit remain unverified.

**Superseded candidate: [V14 — projecting cam receivers](Print-14-README.md).** Its external housings were rejected for use without the loop.

**Previous candidates: [V13 — upward-seating loop](Print-13-README.md), [V12 — rounded reinforced leaf shell](Print-12-README.md), [V11 — broad curved cells](Print-11-README.md).**

**Previous candidate: [Print V10 — solid helix with independent slots and detachable loop, both hands](Print-10-README.md).**

The continuous supporting tube and complete raised spiral strips are retained. Separate narrow slots avoid the spirals and longitudinal lands; the loop has elongated slots and remains removable. One left wand estimates 76.072 g printed PETG with its loop or 65.902 g without. Hardware is unweighed. The V9 open-braid experiment was rejected and is not a current print recommendation.

**Previous candidate: [Print V8 — ergonomic lower loop, higher controls and air to the hand, both hands](Print-8-README.md).**

The loop sits at the butt, all controls move up 10 mm and its upper arm slopes down away from the index-side root. Loop ports now reach the inner contact surface. One left wand estimates 75.821 g of printed PETG; bought hardware remains unweighed.

**Previous candidate: [Print V7 — slimmer ventilated wand, both hands](Print-7-README.md).**

Slimmer hollow grip/loop and flute-like air holes. One left wand estimates 75.688 g of printed PETG, 16.85% less than V6; bought hardware remains unweighed.

**Previous candidate: [Print V6 — side buttons raised 14 mm, both hands](Print-6-README.md).**

The side-button pair is 14 mm higher, with its upper centre 4 mm below the unchanged thumb. Side angles and radial placement are unchanged. Thin top-slide button plates fit directly into rounded surrounds built into the wand. The crossed helix, continuous taper, hollow interiors and both handed handles are preserved. The upper-only alternative retains a printed V2 handle. Earlier versions remain unchanged. Physical fit and strength still need a trial.

**Previous candidate: [Print V5 — thin top-slide buttons](Print-5-README.md).** V6 changes the two side-button heights.

**Previous candidate: [Print V4 — helix wand](Print-4-README.md). Its cassette/keeper button fittings are replaced in V5.

**Earlier candidate: [Print V3 — 410 mm mechanical revision](Print-3-README.md).** Its smooth shafts and left-only complete plate were superseded by V4.

**Previous print: [Print V2 — 340 mm diamond mug wand](Print-2-README.md).**

Open the [full V2 Bambu project](Print-2-diamond-mug-wand.3mf), or start with the
[head and retaining-clip fit test](Print-2-diamond-head-fit-test.3mf). The
[editable CAD and assembly guide](../magic-wand/hardware/printed-loop-wand/v2/README.md)
are committed with the print files. The full project contains two grip choices and one shared
set of remaining parts; choose one grip for a working wand. Physical fit remains unverified.

## Earlier print projects

Pull this repository, then open **[two-spiral-wands.3mf](two-spiral-wands.3mf)** in Bambu Studio.
It includes two complete spiral wands on one plate: one straight grip and one full-hand mug loop.
All eight pieces, their arrangement and the PETG print settings are saved in the project.
Both handles use the exact same twist-lock and shaft parts. The shafts and holders are duplicated
so each handle can have its own complete wand.

For individual prints, [tapered-double-helix.3mf](tapered-double-helix.3mf) has the straight grip,
and [tapered-mug-double-helix.3mf](tapered-mug-double-helix.3mf) has the mug loop.
[tapered-smooth.3mf](tapered-smooth.3mf) has the same shape without the two spiral ridges.
On GitHub, use **Download raw file** to download a 3MF.

## Earlier two-print comparison

- **Print 1:** [original crossed pattern, 110 mm pitch](Print-1-crossed-110mm.3mf).
  This file is frozen from the committed first version; its source commit and checksum are
  recorded in `Print-1-crossed-110mm.json`.
- **Later V1 pattern:** [preferred crossed pattern, 90 mm and 72 mm pitch](tapered-double-helix.3mf).
  Ethan chose this earlier pattern over the tighter 90/36 mm experiment.
  The opposite-winding strands turn at different rates; one makes 25% more turns.

The hole and platform are unchanged. Open the latest print for Ethan's preferred pattern, or
the frozen original for comparison. Clear the bed between jobs; these files are not
instructions to start two jobs together.

## Earlier prototype

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

## Rebuild the earlier projects

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
