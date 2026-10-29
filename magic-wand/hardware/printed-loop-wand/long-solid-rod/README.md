# Long solid wand — 500 mm

A thin, solid printed rod with external wiring, preserving all earlier wand designs.
The original purchased carbon-fibre tube is 500 mm long, 8 mm outside and 7 mm
inside. This prototype matches its length and maximum body diameter, then tapers
to 5.8 mm. It does not claim the stiffness or strength of carbon fibre.

## Files

- `Long-Solid-Wand-500mm-8mm.3mf`: sliced Bambu P1S PETG project, three parts on one plate.
- `exports/*.stl`: individual printable sections; `manifest.json` contains their hashes,
  geometry, print-to-assembly transforms and source/dependency fingerprints.
- `preview/index.html`: interactive assembled, separated-part and gyro-mount views.
- `wand_cad.py`, `print_projects.py`, `verify_models.py`: reproducible editable source.
- `checks.json` and `print-project.json`: delivered-mesh, clearance and sliced-project results.

The lower and middle sections are 182 mm tall, and the upper section is 192 mm.
Their two 28 mm overlapping half-laps make a 500 mm assembly. The lap faces have
0.2 mm clearance. Retain them with suitable adhesive and/or external tape; they
are not a screw or quarter-turn connection. Dry-fit first and avoid forcing the thin lap.

The sensor frame is integral with the upper rod, with two reinforced side rails
and diagonal webs. It retains the existing board slot, USB/solder/wire clearances
and release clip. The local frame is wider than the thin rod because it holds
the actual board. Remove the board before flexing the clip or assembling wiring.
Buttons, battery and wires attach outside; the old loop grip and battery housing
are not included. The preview's orange line is only an illustrative wire route.

## Print and verification

The saved project uses a 0.4 mm nozzle, 0.2 mm layers, four walls, 5 mm brim and
per-object 100% rectilinear infill. Its global 20% setting is overridden by those
three object settings. Supports are disabled. The final slice reports no warnings.
Estimated filament: about 17.82 g in the parts, 18.03 g total including brim/startup.
These are slicer estimates, not measured printed weights.

Delivered STLs are closed, consistently wound and single connected solids.
Cross-sections confirm a solid tapered body without a wire bore. The checks cover
lap interference, board and connector voids, board removal, clip release, layer
starts and sampled actual extrusion paths through the sensor mount.
The clip check subtracts a 0.001 mm seated-clip margin to exclude float32 STL
boundary roundoff; it does not change the CAD's 0.06 mm release clearance.

**Not yet physically printed or load-tested.** A 500 mm PETG rod this thin can
flex and the joints need physical validation. Do not treat geometric reinforcement
as a demonstrated strength rating. Print the upper section first to check board fit
and the release clip before printing/assembling the whole rod.

## Regenerate

From this directory, with Python, numpy, trimesh and manifold3d available:

```sh
python wand_cad.py --out /path/to/new-build/exports
python print_projects.py --exports /path/to/new-build/exports --out /path/to/new-build/projects
python verify_models.py --exports /path/to/new-build/exports \
  --archive /path/to/new-build/projects/slice/Long-Solid-Wand-500mm-8mm.3mf \
  --out /path/to/new-build/checks.json
```

Use a new output directory each time. The project recipe uses the existing
`shard-tube-r2/print-settings` and `v20` portable 3MF writer. The CAD composes
`thin-rod-study/wand_cad.py`, which in turn reads the existing V20 and lattice
sources. These dependencies stay editable and earlier variants stay intact.
Serve the repository root over HTTP to use the preview and its shared Three.js
and viewer-input modules.
