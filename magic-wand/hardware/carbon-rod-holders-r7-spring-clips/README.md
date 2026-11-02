# Carbon-tube holders R7 — spring clips

Five bought Choc keys and an integrated battery cradle on one slide-on carrier,
plus the separate lightweight XIAO Sense holder. Choose **one** of the three
carrier variants; each Bambu project contains that carrier and one XIAO holder.
These are dimensional print prototypes, not physically accepted production parts.

## Open spring clips: changes from R5

- Both the key/battery carrier and the separate XIAO holder now use nearly closed curved clips, with a 330-degree curved sweep before tip rounding. Rounded ends leave an approximately 1.3 mm relaxed gap underneath the rod.
- The default relaxed inside diameter is 7.9 mm for the nominal 8 mm tube. This asks each side to move about 0.05 mm radially. It is a starting fit, not a measured clamping force.
- The curved arms taper from a 1.6 mm upper root to 1.0 mm near their free ends. The lighter XIAO clips use 1.4 mm roots and a 2.4 mm axial width; the carrier clips are 3.6 mm wide.
- Rigid surrounding structure keeps its larger 8.4 mm corridor. Roots join above the rod so the lower arms can flex. The rear battery variant uses the same lower-opening clips, not mirrored clips.
- Slide the holders on from the bare tube end. The small slit provides spring compliance; it is not wide enough for sideways snap-on installation. Do not force it sideways over the tube.
- The five keys remain at the R5 spacing: 18.5 mm lower pitch, 47 mm upper span and 20.5 mm between rows. The centre thumb gap, all three battery positions and flat socket seats remain.
- The rear battery support passes outside the flexible arms; its far clip is moved 3 mm along the rod to clear the end rail.
- The viewer compares against the preserved R5 front-battery model with closed rings. The XIAO USB direction remains toward the near opening.

## Retained close-fitting structure

The mounting plane remains 11.12 mm from the rod axis, 2.98 mm closer than R3.
The front battery floor remains 5.6 mm from the axis, 5.9 mm closer than R3.
The hot-swap socket has a broad flat floor, shallow locating recess and at least
2.48 mm documented pin insertion. The bought switch's own clips engage the
1.2 mm mounting lip. Main rails are 2.5 mm across and main roots 3.2 mm across;
bridges and deep thin webs support each seat. These are structural design choices,
not measured strength. The separate 3 mm wiring corridor remains alongside the rod.

## Battery positions

| File | Position | Trade-off |
|---|---|---|
| `Carrier_front.stl` | Above middle key, close to rod | Familiar thumb gap; a separate brace takes thumb pressure |
| `Carrier_rear.stl` | Behind the rod | Open front gap; adds thickness on the finger side |
| `Carrier_lower.stl` | Down the tube below the keys | Clears the upper gap; makes the carrier longer |

The cell is retained with tape through the cradle eyes, not clamped or used
as a load-bearing thumb stop. Provide slack and a soft lead bend; the actual
wrapped cell and solder/wire arrangement still need a physical trial.

## Bought-part identity and reference accuracy

- Tube: [ATModels 510072](https://www.align-trex.co.uk/carbon-fibre-tube-8mm-x-0-5metre-7mm-id.html),
  nominal 8 mm OD / 7 mm ID. No measured tube tolerance is available.
- Switch: [Adafruit 5113](https://www.adafruit.com/product/5113), Kailh Choc V1
  red CPG135001D01. See the [Kailh switch drawing](https://www.kailhswitch.com/Content/upload/pdf/201915927/CPG135001D01_-_Red_Linear_Choc.pdf).
- Socket: [Adafruit 5118](https://www.adafruit.com/product/5118), CPG135001S30.
  The [2017 drawing](https://cdn-shop.adafruit.com/product-files/5118/5118-Choc-Socket.pdf)
  specifies 13.15 mm overall length / 3.05 mm height; the
  [2024 drawing](https://www.kailhswitch.com/uploads/15927/files/CPG135001S30.pdf?rnd=101)
  changes these to 13.45 / 3.15 mm, with tolerances. The purchased revision
  has not been inspected. The supplied STEP is the older nominal shape;
  the recess has 0.3 mm outline allowance. This is not certification of every
  revision or printer. A maximum-size sensitivity sweep (13.55 × 6.95 ×
  3.25 mm) also passes, but is not official CAD for the newer revision.
  Use the key coupon with the actual socket.
- Caps: [Adafruit 5737](https://www.adafruit.com/product/5737), milky white slim
  Choc caps. Their external envelopes are illustrative. No exact underside
  CAD or full-travel measurement was recovered; a 3 mm illustrative stroke
  check is not proof of the purchased caps' travel.
- Cell: [PKCell 150 mAh, seller SKU105318](https://thepihut.com/products/150mah-3-7v-lipo-battery),
  LP402025. Retailer nominal size is 26 × 21 × 4 mm. The
  [manufacturer appendix](https://cdn.shopify.com/s/files/1/0176/3274/files/lp402025_150mah_3.7v_20190510.pdf?v=1677758450)
  gives maximum 27.5 × 20.5 × 4.3 mm. The viewer uses 27.5 × 21 × 4.3 mm
  to cover both sources. The cradle reserves 30 × 22 × 6 mm, plus 0.8 mm
  side clearance. Reserved wrapping space is a design allowance, not a measurement.

`references/` contains the actual community STEP switch and socket models from
[KiSwitch](https://github.com/kiswitch/kiswitch), pinned at
`aefcf65038d48d2666ff14530d482be3c350fa6e`, plus reproducibly derived collision
meshes. They are checked against the drawings; they are **not official Kailh
STEP or scans of a purchased batch**. Source axes are retained: pins at
(0, 5.9) and (5, 3.8) in the PCB top view. The flange underside is Z2.25.
See `references/provenance.json` for source hashes, bounds and conversion.

The source STEP header's machine-specific file path is replaced with its
basename; geometry is unchanged. KiSwitch's CC BY-SA 4.0 licence and KiCad
exception are preserved in `references/LICENSE-CC-BY-SA.txt`; the referenced
STEP and derived reference meshes retain that licence and attribution.

## Viewer controls

- Drag to rotate through complete turns in any direction. Free orbit can roll;
  Front, Top, Side and Iso return to a clear standard angle instantly.
- Right-drag, middle-drag or Shift-drag pans in any mode. The Pan button also
  works with a normal left drag. Scroll zooms toward the pointer; pinch zooms.
- Frame (F) fits the visible parts while retaining the angle. Reset view
  (0 or Home) restores the starting angle. R/P/Z select Rotate/Pan/Zoom; T/M remain supported.
- Keycaps, reference visibility and design changes retain the inspection view.
  Parts changes retain the angle and fit the selected part. Resize preserves
  the angle, target and relative zoom. Lighting follows the camera.
- The explicit wand override rotates scroll input, preserving the existing
  wheel gain; pinch still zooms. There is no inertia or added input delay.

## Printing and fitting

The paired projects use PETG, a P1S 0.4 mm nozzle preset, 0.2 mm layers,
3 walls and 20% infill. Open the selected `Holder-*-sliced.3mf` in Bambu Studio.
Do not send its G-code to another printer without reslicing for that printer.
The carrier prints with the key faces down. Normal removable supports are
required around the spring clips and beneath the socket floors; labelled support
enforcers are print-only helpers, not physical pieces or negative CAD holes.
The XIAO holder uses the retained print orientation; its changed clips are checked again in each sliced project. Remove all supports from
key openings, socket recesses, wiring corridor and clip bores before fitting.

1. Print a carrier spring coupon and a sensor spring coupon (7.9, 8.0 or 8.1 mm
   relaxed bore) plus a key coupon (14.0, 14.1 or 14.2 mm opening), from
   `exports/fit-coupons/`. Use the supplied orientations, PETG and the same
   layer/wall settings as the full holder. A flat-on-bed C would have different
   layer strength. Start with 7.9 mm; if it binds, try the next larger coupon.
   The centre-key-with-clips test piece checks the key and rod together.
   Coupons are separate STLs, not part of the paired sliced projects.
2. Insert the socket through the empty key opening, centred at the temporary
   offset (-2.5, -4.824) mm; lower it below the lip, slide it into alignment,
   then lower it into the flat recess. This route is checked for the bare socket.
   Solder the left tab through the opening and the right tab from the open side,
   route the wires sideways, then install the switch. A pre-soldered socket and
   its wire bends have not been verified through this loading route.
3. Support the socket floor directly while pressing the bought switch into
   its factory clips and socket. Check latch engagement and full key travel.
4. Fit the complete carrier on the bare tube end before mounting components
   that would block that end. Check for deliberate hand adjustment without scraping the tube. Tune
   the relaxed diameter using the coupons and regenerate, as below.
5. Test the full carrier progressively before use: key presses, thumb pull,
   twist, repeated slide-on/off and wire access. Check for whitening, cracks,
   flex or a cap striking the frame. Do not load the LiPo pouch as a thumb rest.

## Adjustable slide and finger comfort

- The default 7.9 mm relaxed bore is intentionally smaller than the nominal tube.
  No tape liner is required by this design. Test the coupons first: actual tube
  size, extrusion accuracy and PETG stiffness determine the sliding force.
- Choose the largest grip that stays where set while still sliding by hand.
  If 7.9 mm is too tight, set `rod.clip_diameter` to the successful larger
  coupon size in `parameters.json`, then regenerate and recheck the models.
  Do not glue the carrier to the rod or lever the slit apart for installation.
- Check the complete carrier too: isolated coupons cannot prove all clips line
  up. Repeat sliding, inspect for whitening/cracks, and check again after a day
  under load for relaxation. Clamp force, fatigue and long-term creep are untested.
- Light axial drag cannot also guarantee strong resistance to twisting: the
  key presses act much further from the rod than the ring contact. With the
  index finger supporting the width and the middle finger wrapping the
  other side, the hand supports key loads. Check for rotation during real
  use; if it slips, review a separate sliding anti-rotation guide rather than
  tightening the clips hard against the thin carbon tube.
- Four unused hanging legs under the outer front corners and the unused
  left floor spurs are removed. Their free ends did not support the floors;
  the deck bridges, webs and two floor walls carry those loads. Joint-overlap,
  bought-part clearance and print checks are repeated after removal.
- No extra curved corner-to-rod bridge or broad underside surface is added
  at this stage. Try the actual grip before deciding where that curve belongs.
  Clean support scars on finger-contact edges; comfort and slide force remain
  physical acceptance checks, not CAD claims.

## Verification and rebuilding

`exports/manifest.json` ties print STLs to their sources. `geometry-checks.json`
checks all five sourced switch/socket meshes, handedness, retention stops,
socket assembly path, battery reserve, open clip gaps, relaxed bores and an
idealized expanded 8 mm corridor. Intentional relaxed interference is reported
separately; that mathematical expansion does not simulate elastic force. `slice-clearances-*.json` checks prepared normal meshes, actual
model beads and support-backed layer starts. Removable supports in open
assembly regions are reported separately; physical removal remains unverified.
`mass-*.json` reports actual sliced part/support/brim estimates separately.
None of these receipts establishes strength, comfort or physical fit.

From this folder, with Python and Bambu Studio installed:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python reference_models.py
.venv/bin/python cad.py
.venv/bin/python verify_geometry.py
.venv/bin/python fit_coupons.py
.venv/bin/python print_project.py --option front --slice --scratch /your/scratch/front
.venv/bin/python verify_slice.py --option front
.venv/bin/python measure_mass.py --option front
# Repeat those last three commands for rear and lower, with separate scratch folders.
.venv/bin/python build_preview.py
.venv/bin/python render_options.py
node --test preview/wheel-input.test.mjs
```

Serve the repository root and visit
`magic-wand/hardware/carbon-rod-holders-r7-spring-clips/preview/`. The viewer reads the same
exported meshes, offers all three options and the preserved R5 comparison,
and can hide the caps to reveal the sourced switch and socket geometry.
`package_release.py` builds the checked portable archive with source dependencies.
Older revisions bundled under `source/` are historical comparisons and dependencies;
their original fit reports are not current approval of the bought parts.
