# R17 battery and XIAO holder repair

R17 is a replacement trial for the detached battery holder and the too-tight XIAO
nRF52840 Sense holder. It preserves the successful R16 key carrier and does not
include a key carrier on its repair plate. Earlier revisions remain unchanged.

**Status: independent review cleared a monitored complete-part trial. The repair
plate has been submitted through Bambu Studio with timelapse, bed levelling and
flow calibration enabled. Physical fit, adhesion, strength, fatigue and comfort
remain unverified. This is a start record, not a live status feed.**

## What changed

- Battery: a continuous open U-channel replaces the thin chevron lattice. Across
  120 sampled body layers, the cross-section is now one connected island; R16 had
  a median of nine. The body has a 1.2 mm floor with a thicker central load path,
  open top and retaining side flanges. The PKCell LP402025 reserve, end gate,
  wire routes and free rod-clip arms are preserved. The end gate now uses free
  sprung legs and small detents, rather than a rigid interference wedge.
- This is a deliberate visual trade-off: the battery holder is plainer and about
  0.42 g heavier by full-solid CAD volume. It retains an arrow-like end opening,
  with shallow outer chevrons rather than R16's through-wall decorative lattice.
  The new shape is not physically proven.
- XIAO: each rail moves 0.8 mm outward, increasing nominal allowance beyond the
  17.78 mm board from 0.31 to 1.11 mm on each side. Corner ledges and stops locate
  the rounded board independently of those wider rails. Solder-access regions
  and provisional 1 mm wire corridors are checked at all fourteen pad rows,
  continuously out to the external route. Actual solder and wire sizes are unknown.
- A separate removable top plate slides in from the near end through rigid
  grooves, with a sprung detent. Fixed far-corner fingers and the removable
  plate overhang bare board corners beyond the solder pads. The printed finger
  underside is nominally 0.3 mm above the PCB; real retention is untested.
- Bed anchors: each printed object includes a labelled `REMOVE AFTER PRINT`
  normal part. Short fused necks connect it to fixed faces. The main holders use
  0.8 mm / four-layer anchors; the two flat retainers use 0.4 mm / two-layer
  anchors. These replace a slicer brim, which is intentionally disabled.

## Failure evidence and limits

The previous retry's recording shows the battery's upper lattice becoming ragged
before the whole holder moves off its footprint. At detachment the wide brim
remains on the bed. This supports addressing both the weak upper structure and
the connection between the holder and its bed-adhesion aid. It does not prove
the initiating cause, a nozzle strike, exact peel force or the physical fracture
surface. A 0.1 mm brim separation was configured; it was not a fused structural
base. The functional rod bore is intentional and must not be filled.

The replacement anchor necks are continuous in the actual G-code, with a roughly
1 mm bead gap away from the necks. Physical anchoring and easy cleanup remain
unverified. The 0.6 mm travel lift reduces contact exposure; it does not prove a
curled or poorly bonded print cannot be struck.

## Parts and files

The plate contains `Battery_Holder`, `Battery_End_Gate`, `XIAO_Rod_Holder` and
`XIAO_Top_Retainer`, each with its corresponding removable anchor.

- [Prepared sliced archive](exports/R17-A1-mini-PETG.gcode.3mf)
- [Editable layout](exports/R17-A1-mini-PETG-layout.3mf)
- [Assembled reference including the unchanged key carrier](exports/assembled-view.png)
- [Battery views](exports/Battery_Holder-overview.png)
- [XIAO and removable top bar views](exports/XIAO_Rod_Holder-overview.png)
- [Audit and acceptance plan](AUDIT.md)

`*-assembly.stl` files show the cleaned functional part in assembly coordinates.
`*-SOURCE-REQUIRES-PREPARATION.stl` files alone omit the necessary labelled bed
anchors and checked recipe. Use the prepared project rather than treating a
bare STL as the checked print setup. Do not confuse the retained working key
carrier with a missing part of this repair plate.

## Print setup

Bambu Lab A1 mini, 0.4 mm nozzle, textured PEI, external-spool Generic PETG,
0.20 mm layers, three walls and 20 percent infill. The inherited recipe reads
255 C nozzle / 70 C bed. Initial outer/infill speeds are 20/30 mm/s. Automatic
support, prime tower and slicer brim are disabled because the project supplies
its own clear-of-hole anchors. A local slow modifier protects the closing
battery gate-guide region. Normal travel lift is 0.6 mm.

The independently reviewed CLI archive estimates 50 min 8 s and 6.29 g. The
actual GUI re-slice sent for the trial estimates 58 min 24 s including preparation
and timelapse, using 6.27 g. Both contain only the four repair parts and anchors.
Studio reset travel lift to 0.4 mm Auto on loading; it was restored to 0.6 mm
Normal before the final re-slice. The actual GUI paths passed the clearance,
anchor and local-speed checks against the reviewed geometry.

Timelapse is a printer-send option: enable it on every send and resume live camera
playback after the job starts. Studio warns that instant timelapse may cause
surface imperfections; this is not a statement that recording is disabled.
Recording was selected; a playable saved file remains a later verification.

## Remove anchors and assemble

1. Let the plate cool and remove the parts without bending a clip arm. Keep all
   cut-away plastic separate from functional parts.
2. Cut each short anchor neck flush at the fixed part face using side cutters,
   approaching from the flange side. Then lift/peel the detached flange away.
   Never lever a flange against a rod ring, a thin ledge or a retainer finger.
   Remove burrs from the cut sites; inspect for cracks before fitting anything.
3. Test the empty modules on the actual rod without spreading or forcing them.
   Check slide, adjustment and removal. The lower free arms are geometrically
   preserved, but neither the new roots nor printed clip force is proven.
4. Remove the battery end gate and gently slide the protected PKCell pack into
   the open channel. Its wires and protection end stay in their reserved route.
   Refit the gate only if it seats without squeezing or scraping the pouch.
   Optional soft tape can remove residual play; never force an oversized cell.
5. With the top plate removed, tilt the board's near end up about 6 degrees and
   slide the USB end about 2 mm under the far fingers. Keep the side wires outside
   the rails, then lower the near end onto its ledges. Slide the separate plate
   in from the near end; slide it out before lifting/removing the board. Confirm
   solder clears, the board does not rock and the reset button remains usable.
   Never force a binding board or plate; removable tape is the trial fallback.
6. Inspect the top plate's small spring tips and confirm both arms move freely.
   The slicer omits their thin first-layer relief, leaving a short second-layer
   bridge. Independent review considered this nonblocking for a monitored trial,
   but a damaged tip must not be relied on for retention; use tape instead.
7. Connect USB and inspect the external wires before attaching both modules
   beside the existing key carrier. Preserve space for connectors and actual
   solder bends; a catalogue envelope cannot verify the fitted wiring.

## Component basis

The battery reserve is inherited from R16: protected PKCell LP402025, manufacturer
maximum 20.5 x 27.5 x 4.3 mm. Those are pack-reserve numbers, not measured bought
cell dimensions. R17 keeps that conservative reserve rather than squeezing a
lithium pouch to eliminate every possible rattle.

XIAO references are Seeed's official [resource index](https://wiki.seeedstudio.com/SeeedStudio_XIAO_Series_Introduction/#seeed-studio-xiao-nrf52840-sense-open-source-materials),
Sense DXF and plain-board STEP. The derived rounded outline is 20.955 x 17.78 mm,
radius 1.905 mm and PCB thickness 1.25 mm. The plain STEP does not establish the
complete fitted Sense assembly, underside headers, actual solder or wire bends.
The source explicitly records the unmodelled IMU assumption. Verify the real
populated board against the fingers and cradles before accepting the fit.

## Reproduce

Use a CAD Python environment providing numpy, trimesh, manifold3d and matplotlib,
and the installed Bambu Studio profiles. Run heavy commands one at a time through
the repository's geometry runner. Pass private scratch with `--scratch`; do not
write slicer HOME, logs or device settings into the source tree.

Run in order: `holder17.py`, `anchors17.py`, `verify17.py`, `project17.py --slice
--scratch <scratch>`, `slice17.py`, `roundtrip17.py --scratch <scratch>`, then
`views17.py`. A recipe change invalidates the old slice/roundtrip evidence even
if the mesh is unchanged. The manifest and reports bind sources, meshes, projects
and images by SHA-256. Independent review and physical trials remain separate.
