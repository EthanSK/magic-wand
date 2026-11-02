# Carbon-rod holders R9 — aligned keys and slide-in battery cage

Four normal print parts: the five-key carrier, independently sliding battery
cage, small removable battery end gate and USB-up XIAO holder. R8 is preserved.
These are dimensional print prototypes; physical fit, force and comfort remain
unverified.

## Changes

- The two side keys now align with the outer columns of the row of three:
  both use X centres ±18.5 mm. Overall key-holder width drops by 10 mm.
  Row spacing stays 20.5 mm. Illustrative caps leave a 20.4 mm central gap;
  actual thumb reach and cap clearance still need a physical trial.
- The old battery-driven inner rear braces and projecting thumb crossbar are
  removed. Short bridges, diagonals and the existing under-row rails carry
  the keys. Socket recesses, factory switch retention and rounded contacts
  remain. A proper 180-degree rotation reverses the layout without mirroring
  the socket handedness.
- Wires stay outside the carbon tube. The XIAO no longer has the old internal
  lead turn cut. Its white USB reference is at +Y, toward the tip/computer,
  away from the keys. The green rectangle represents the bought board; neither
  green PCB nor white connector is a print part. The board rests on edge
  ledges and uses the existing soft tape retention; the tape-free change below
  is for the battery. Exact Sense underside components and solder bends remain
  unmeasured. The red external loom is illustrative, not an exact wire harness.
- The separate battery cage has an open ladder floor and three thin roof
  hoops. It reserves the same 30 × 22 × 6 mm pouch envelope, with 0.8 mm side
  allowance and 0.6 mm above. Nothing deliberately squeezes the pouch.

## Battery loading, without tape

1. Pull the small end gate straight out, away from the rod.
2. Slide the insulated battery through the open end until it reaches the split
   far stop. The central opening there leaves room for its two leads.
3. Press the gate back into its two external guide channels. Its shallow wedges
   act on those guides, outside the cell space. The gate bar closes the entry.
4. Route the leads through the open end/side windows, with slack and strain
   relief. Keep the carbon tube bare where the modules slide. Unplug or reroute
   before reordering or turning the modules; do not pull on battery terminals.

The default gate has 0.1 mm total intended wedge interference. An idealized
fitted gate verifies the loading route; that is not a measured insertion or
retention force. An easier-fit gate is in `exports/fit-coupons/`; try it only
if the default binds, then check it cannot work loose. Print the preserved R7
spring coupons for rod fit too. Do not use a swollen/damaged pouch, force a
cell into the cage or make it the thumb rest.

## Viewer and print project

Serve the repository root, then visit
`magic-wand/hardware/carbon-rod-holders-r9-slot-cage/preview/`.
Try both key orientations, either battery end/side and the spacing control.
`Gate removed` shows the end gate lifted clear. Scroll zoom and endless free
orbit retain the same shared viewer controls.

`exports/Holder-modular-sliced.3mf` contains all four normal parts on one plate.
It uses the existing PETG, P1S 0.4 mm nozzle, 0.2 mm layers, 3 walls and 20%
infill recipe. Reslice for another printer. Gate broad faces print flat; the
other parts retain their checked layer directions. Remove print supports from
seats, clip bores, the cage and gate guides before assembly. Model/support/brim
mass estimates remain separate in `exports/mass-modular.json`.

## Checks and rebuilding

`geometry-checks.json` binds the final source/manifest and checks five sourced
switch/socket seats, maximum-size loading sensitivity, four flange lands,
connected load joints, spring-arm freedom, battery reserve and 32 reversible
poses. It also checks the complete battery insertion with the gate removed,
the fitted gate's full insertion path, both end stops, USB direction and the
external loom staying outside the rod. Gate preload is reported separately.
`slice-clearances-modular.json` audits actual model beads and support-backed
starts against the final normal STLs. Neither report establishes physical
strength, sliding force, gate retention, electrical function or hand comfort.

Use the pinned Python `requirements.txt`, then run:

```sh
python cad.py
python verify_geometry.py
python print_project.py --slice --scratch /your/scratch/r9
python verify_slice.py
python measure_mass.py
python build_preview.py
python package_release.py --out /your/delivery/folder
```

Keep the portable source tree intact. The archive includes the frozen R7/R2
interfaces, transitive CAD helper and licences needed to rebuild it. Bought
switch/socket provenance and nominal-vs-measured limits remain documented in
[R7](../carbon-rod-holders-r7-spring-clips/README.md#bought-part-identity-and-reference-accuracy).
