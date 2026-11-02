# Control Stones V2 — compact handheld and ring concepts

These are editable mechanical layout studies for one XIAO nRF52840 Sense,
one battery and physical buttons, in compact handheld and finger-ring bodies. It is **not print-ready**.
The V1 multi-sensor wiring, profile, firmware and installed hardware are unchanged.

Start with [the leading compact handheld](exports/handheld-overview.png) and
[the handheld beside the ring at the same scale](exports/handheld-v-ring.png).
The [ring comparison](exports/overview.png) and
[ring underside comparison](exports/underside-comparison.png) remain available.
The shared Control Stones board contains the planning/discussion card named
**Control Stones V2**; that card owns the user decisions and open questions.
This directory owns CAD geometry and its fit assumptions.

## Leading direction: very short, lightweight handheld

Ethan prefers an easy, casual body he can pick up and put down; a ring could
be finicky. The compact hollow handheld removes the ring and all extra shaft
length, using the same component envelopes. It is a starting layout, not proof
of the smallest possible size or weight. Both hands and button counts remain.

The hollow shell has a provisional soft-tie bridge beyond the board, so leads
can be captured away from solder pads. The slot and actual wire routes are
unverified; it does not retain or protect a cell by itself. Lid fastening,
switch mechanisms, insulation, protected battery retention, switch travel,
grounding when put down and actual grip strength/comfort still need design.

Same wrist rotation gives the same gyro input irrespective of rod length;
length also changes balance, inertia and tip travel. A shorter object can
still have ergonomic disadvantages. No pointer gain, firmware or installed
mouse behaviour changes are part of these models.

The geometry report separates concept plastic volume from hardware. Its
mass range uses assumed plastic densities only; it excludes board, battery,
wires, switches, final retention and slicer changes. It is not measured
complete-device weight. Thin concept walls are unqualified for strength.

## Ring comparison and shared handedness

- Left hand is primary. Right hand is an exact anatomical mirror.
- Wear on the index finger first; middle finger is an alternative to test.
- “One for each finger” remains a finger-fit variant question, not five
  simultaneously powered rings.
- Gold thumb-facing/outer-side pad is the normal mouse click. The far-side pad
  is purple. The third pad is below the finger.
- The four-button version splits the underside into two pads along the finger,
  with one tactile ridge. Keep it optional until a comfortable eyes-free reach
  test succeeds. Do not depend on independent ring-finger movement.
- The short band carries an electronics pod on the back of the finger. Its
  rounded lift-off cover, guard rims and USB opening are concept geometry.
  Lid fastening, switch mounting and electrical operation are not implemented.

Coordinate convention: Z is away from the back of the finger, +Y points toward
fingertips, and +X is the thumb-facing side on the left-hand model viewed
palm-down. Right-hand geometry mirrors X. This defines CAD, not sensor axes or
firmware motion mappings. Index/middle choices need actual reach and clearance
checks rather than simply relabelling a model.

## Evidence and fit assumptions

[Seeed's original nRF52840 Sense wiki](https://wiki.seeedstudio.com/XIAO_BLE/)
specifies the XY footprint and links its DXF and 3D resources. The DXF archive
was inspected; its drawing includes several views and no directly usable
whole-document part bound. The manufacturer-linked 3D archive is labelled
`XIAO-nRF52840 v15.step`, so it is not treated as proof of the Sense underside
assembly. The CAD uses the specified XY rectangular envelope, not a detailed
manufacturer solid or a measured assembled board.

`dimensions.json` is the editable source for component envelopes, finger size
and pod parameters. The assembled board height, battery, switch package and
finger opening are explicitly provisional. Shell and cap details are editable
in `ring_cad.py`. No battery capacity, runtime, press force or personal finger
measurement is claimed. No components have been selected or purchased here.

The reference envelopes fit without geometric intersections. That does not
verify the actual component fit. The current concept is bulky: inspect its
computed bounds in `exports/geometry-checks.json`, especially the pod height,
far-side button beside another finger and underside boss toward the palm.

Before a functional or print-ready design:

- Measure finger width/height at the wearing position and removal over the
  knuckle. Check adjacent-finger clearance and full bending without bridging
  a joint; check palm contact and accidental presses with a relaxed hand.
- Try each button without looking. Check ring rotation and click-induced
  pointer movement. Confirm an accessible far-side actuation method for each
  intended finger without relying on independent ring-finger motion.
- Select and measure a protected battery, switches, terminals, USB plug and
  board revision. Account for cell leads/expansion, insulation and underside
  sensor, solder and connector clearances. Do not compress the battery.
- Design retention, assembly access, strain relief and wire routes outside
  the skin bore. Current free space is not a checked route or strain relief.
  Keep the antenna area clear of metal and check radio performance.
- Make a separate unpowered sizing mock-up before detailed electronics fit.
  Check wall thickness, material, support removal, orientation and slicer paths
  before printing; no slicer qualification or physical testing has occurred.

## Rebuild

Use Python 3.11 or later and a virtual environment **outside this checkout**.
Install `requirements.txt`, then run from this directory:

```sh
python ring_cad.py
python verify_geometry.py
python render_preview.py
```

Generation never opens a hardware port, connects over Bluetooth, flashes a
board or changes receiver settings. Do not edit generated exports; change the
owning source and regenerate. The manifest fingerprints CAD source and input
parameters, and preview images derive from that manifest. Run the checks again
after any source change. The checks use assertions; do not run with Python `-O`.

## Exports and checks

- Eight separate ring and `Handheld_`-prefixed `Left/Right_3/4Button_CONCEPT.3mf` assemblies retain millimetre
  scale and named parts. They have **no printer profile or print instructions**.
  Bambu Studio may show a geometry-only import notice; accept geometry only.
  Do not slice/print the entire assembly: board, battery and switch envelopes
  are reference geometry, and all mechanisms/retention remain unfinished.
- Eight `.glb` models provide colour views in standard glTF metre/Y-up units.
- Each variant directory has individual millimetre STL meshes, including named
  reference envelopes. STL itself carries no units or material information.
- `manifest.json` supplies the views directly. `geometry-checks.json` records
  connected solids, watertight STL round trips, exact mirrors, non-intersecting
  reference envelopes, finger-bore clearance, GLB scale/axes and 3MF assembly
  scale/geometry. These are analytic checks, not comfort or printability tests.
- The four preview PNGs are reproducibly rendered
  technical illustrations of those meshes, not invented product images.

All concept views were visually inspected as technical renders. The initial
ring concept was imported in Bambu Studio on the MacBook Pro display, which
reported the same nominal model bounds. The later handheld import could not
be confirmed because the native path sheet stopped confirming input; its
rendered previews and analytic 3MF/GLB checks passed instead. No printing, firmware change, hardware installation or physical fit
acceptance was performed. The repository-wide `npm run check` is required
before a completed source commit; CAD generation/checks above are additional.
