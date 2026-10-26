# Wand Print V2 — 340 mm diamond mug wand

Print V2 is the shorter mug-loop wand with three separate Choc switch mounts and an enclosed XIAO Sense board. It freezes the reviewed CAD revision V17. This is a mechanical print version; it does not change the firmware's control versions or the original Prototype V1 baseline.

## Open the print files

- [Print-2-diamond-mug-wand.3mf](../../../../magic-wand-3d-models/Print-2-diamond-mug-wand.3mf): full Bambu project with left/right grips and one shared set of shaft and head parts. There are fourteen printable instances. Choose one grip for a working wand; the second grip is for comparing hand positions. This saved project needs slicing before printing.
- [Print-2-diamond-head-fit-test.3mf](../../../../magic-wand-3d-models/Print-2-diamond-head-fit-test.3mf): revised head and cover only, about 1 hour 9 minutes and 14.21 g PETG in the recorded slice. Test this before a complete print.
- [Interactive assembly preview](preview/index.html): serve the repository root over HTTP and open this file. It uses the repository's vendored Three.js library and loads the actual exported geometry. “Board retention” highlights the clip and guides; “Thumb clearance” isolates that switch assembly.

On GitHub, use **Download raw file** for a 3MF. Earlier print files remain unchanged.

## Shape and fit

The wand is 340 mm long. Its faceted diamond head is 40 × 37 × 58 mm. The original mug loop and grip taper remain; the thumb mount now faces sideways and sits 2 mm farther out, leaving 5 mm minimum clearance from the loop. The right grip mirrors this change. The actual socket cassette and a conservative 20 × 20 × 10 mm keycap envelope also clear the loop.

The head has four rear board seats, four short corner guides, two upper edge pockets and a lower release clip. They are built into the printed head; no separate screws or extra clip are required. The long solder-pad edges remain open.

1. Slide the diamond cover diagonally up and out.
2. Route the wires first, leaving slack for inserting the board and turning the head bayonet.
3. Slide the USB end of the board under the two upper retaining lips, with USB-C facing the tip.
4. Tilt the lower edge onto the seats and gently press it past the lower clip.
5. To remove the board, press the centre of the lower clip towards the handle, tilt the lower edge out and withdraw the upper edge.
6. Slide the cover down and inward. Its small rail detent retains the cover independently of the board.

The PCB reference is 21 × 17.8 × 1.6 mm in a 1.9 mm slot, with 0.2 mm side/end clearances. These are design inputs, not measurements of a particular board. A thinner revision may need a thin nonconductive shim at an unobstructed seat. Keep pressure off components, the USB socket and solder joints.

The clip's rear bridge is 0.8 mm thick and intended for PETG. A geometric release check deflects its centre 1.3 mm; this does not predict force, print quality or fatigue life. Print the head-only trial and check the actual board, headers, solder joints and USB cable before a full print. The 12 × 6 mm USB-plug envelope and 6 mm central rear soldering space clear digitally.

## Buttons, wires and battery

Each 24 mm button pad accepts a printed carrier for a Kailh Choc V1 switch and a CPG135001S30 bare hot-swap socket. Slide its keeper in, solder two wires to the socket terminals and provide cable strain relief on the housing. The carrier/keeper can still need temporary tape during prototyping.

The main tunnel is 10.4 mm across. Eight wires means six separate button wires plus two battery leads. Sharing the button grounds is optional and reduces this to six wires including the battery pair. At the board cradle a 6 mm forward passage clears the release tongue. Actual wire diameters and connector bodies still need checking.

The lower handle holds a removable battery sled behind a bottom twist cap. The battery envelope remains provisional: 20 × 6 × 40 mm in a 22.6 × 9 × 49 mm chamber. Measure the actual cell, protection board and leads before printing; do not compress the cell. Tape holds the battery to the sled.

Use this version's matching 16 mm bayonet parts, not the earlier 13 mm joints. The keyed middle shaft joint still needs adhesive or temporary tape if loose. Leave slack for the approximately 38-degree head/grip bayonet turn.

## Source and rebuilding

The editable generator is [wand_cad.py](wand_cad.py). Its [frozen reference helpers and dimensions](reference/) preserve the taper, loop and joint recipe without depending on another checkout or private working directory. All twelve STL files and assembly coordinates are in [exports](exports/). The [print recipe](print_projects.py) includes the layouts, support blockers and saved [print settings](print-settings/).

From the repository root, using a virtual environment with `requirements.txt` installed:

```sh
python3 magic-wand/hardware/printed-loop-wand/v2/wand_cad.py --check
python3 magic-wand/hardware/printed-loop-wand/v2/check_geometry.py
python3 magic-wand/hardware/printed-loop-wand/v2/verify_release.py --check
npm run check
```

New artifacts require an unused output directory:

```sh
python3 magic-wand/hardware/printed-loop-wand/v2/wand_cad.py --out ~/Downloads/wand-v2-new-geometry
python3 magic-wand/hardware/printed-loop-wand/v2/print_projects.py --out ~/Downloads/wand-v2-new-projects --slice
```

After editing CAD, review and update the tracked exports before running the print recipe, which reads `exports/manifest.json`. `--slice` requires Bambu Studio; omit it for unsliced layouts. The recipe preserves raw CLI slices and writes separate `-prepared.3mf` copies with registered process overrides. Review changed sources and exports together, then write a fresh release record with `verify_release.py --record-new <unused-path>` and update the tracked record in the same checked commit.

The saved setup is Bambu P1S, 0.4 mm nozzle, Generic PETG, 0.2 mm layers, three walls and 20% infill. Select the actual loaded material. Brown translucent volumes are support blockers, not printed plugs; leave them attached.

## Verification boundary

The twelve meshes are closed single solids. Digital checks cover board stops and released removal, the cover path, rear solder clearance, wire entry, USB access and both thumb-to-loop gaps. The STL exports reproduce the reviewed V17 geometry byte for byte. The release record checks hashes across source, exports, preview, settings and both Bambu projects.

Physical fit, strength, clip feel, battery fit and ergonomics remain unverified. No firmware, receiver, installed hardware or printing job is changed by this release.
