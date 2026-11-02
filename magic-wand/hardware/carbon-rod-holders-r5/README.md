# Carbon-tube holders R5

Five bought Choc keys and an integrated battery cradle on one slide-on carrier,
plus the separate lightweight XIAO Sense holder. Choose **one** of the three
carrier variants; each Bambu project contains that carrier and one XIAO holder.
These are dimensional print prototypes, not physically accepted production parts.

## Closer keys: changes from R4

- Lower key centres are 18.5 mm apart instead of 20 mm.
- The upper pair spans 47 mm instead of 50 mm, with the centre battery/thumb gap retained.
- Rows are 20.5 mm apart instead of 22 mm. Every pair of key centres is closer.
- The full-size illustrative caps retain at least 1.9 mm edge clearance. Actual purchased cap dimensions and travel still need the physical test.
- Deck bridges and webs follow the new centres. Inner upper braces sit below the sockets, keeping the same battery reserve, flat socket seats and sliding rings.
- The separate XIAO holder is unchanged. All three battery variants remain available; the viewer compares against the preserved R4 front-battery model.

## Retained R4 changes from R3

- Three lower keys and two upper side keys retain the same arrangement. The upper
  middle stays available for the battery and thumb gap.
- Mounting-plane height is 11.12 mm from the rod axis, versus 14.1 mm in R3:
  **2.98 mm closer**. The front battery floor is 5.6 mm from the axis, versus
  11.5 mm: **5.9 mm closer**.
- Complete 8.4 mm bearing rings slide over the nominal 8 mm tube. Both ends
  have lead-ins. The carrier stays adjustable along the rod: do not bond it
  to the tube. Set light drag with a removable liner inside one ring, as below;
  the unlined rings remain free guides. Nominal clearance alone gives no drag.
- The hot-swap socket has a broad flat floor and a shallow locating recess.
  R3's two printed annular pads are removed. The socket's bosses face the switch.
- The socket is located by its back face on the floor, retaining at least
  2.48 mm of pin insertion at the smallest documented socket height.
- The switch uses its factory clips in a 1.2 mm mounting lip and a flat flange-bearing surface. Main rails are 2.5 mm across and main roots 3.2 mm across; deck bridges and deep thin webs
  connect the outer seats, with two walls supporting each socket floor. This is reinforcement, not a measured strength claim.
- A separate 3 mm wiring corridor runs beside the rod. The XIAO frame is
  byte-identical to R2, including USB facing -Y toward the near sleeve opening
  and its existing over-the-tube-end wire route.
- Ordinary mouse scroll zooms. The explicit, remembered wand override makes
  scroll turn instead; it applies to all scroll input while enabled because
  browser wheel events do not identify the physical input device. Drag modes,
  keyboard modes, timing and the shared wand input module are preserved.

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
required around the rings and beneath the socket floors; labelled support
enforcers are print-only helpers, not physical pieces or negative CAD holes.
The XIAO holder retains its support-free R2 recipe. Remove all supports from
key openings, socket recesses, wiring corridor and ring bores before fitting.

1. Print a tube coupon (8.2, 8.4 or 8.6 mm bore) and a key coupon
   (14.0, 14.1 or 14.2 mm opening) from `exports/fit-coupons/` in the supplied
   orientations. Use the same material and settings as the carrier. Coupon
   STLs and a centre-key-with-rings test piece are provided; they are not part
   of the paired sliced projects. The centre piece uses the same carrier geometry
   and tests the key/tube interface together before the full carrier.
2. Insert the socket through the empty key opening, centred at the temporary
   offset (-2.5, -4.824) mm; lower it below the lip, slide it into alignment,
   then lower it into the flat recess. This route is checked for the bare socket.
   Solder the left tab through the opening and the right tab from the open side,
   route the wires sideways, then install the switch. A pre-soldered socket and
   its wire bends have not been verified through this loading route.
3. Support the socket floor directly while pressing the bought switch into
   its factory clips and socket. Check latch engagement and full key travel.
4. Fit the complete carrier on the bare tube end before mounting components
   that would block that end. Check every ring for free axial travel, then
   tune its sliding drag with the removable one-ring liner below.
5. Test the full carrier progressively before use: key presses, thumb pull,
   twist, repeated slide-on/off and wire access. Check for whitening, cracks,
   flex or a cap striking the frame. Do not load the LiPo pouch as a thumb rest.

## Adjustable slide and finger comfort

- Keep the nominal 8.4 mm bores. Put one thin vinyl-tape wrap **inside one
  ring** (y -12 or 11.5), adhesive facing the printed plastic, trimmed flush
  with no lump over the lead-in. Add or remove liner layers after the bore
  coupon trial to get a deliberate hand slide. Do not stick the carrier to
  the rod. No extra printed part or purchase is required.
- One compliant contact absorbs print variation; the other rings guide the
  carrier without binding. Check the complete carrier too: isolated bore
  coupons cannot prove all printed rings line up. Check drag again after a day.
- Light axial drag cannot also guarantee strong resistance to twisting: the
  key presses act much further from the rod than the ring contact. With the
  index finger supporting the width and the middle finger wrapping the
  other side, the hand supports key loads. Check for rotation during real
  use; if it slips, review a separate sliding anti-rotation guide rather than
  tightening the rings hard against the thin carbon tube.
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
socket assembly path, battery reserve, the continuous tube corridor and full
ring bands. `slice-clearances-*.json` checks prepared normal meshes, actual
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
`magic-wand/hardware/carbon-rod-holders-r5/preview/`. The viewer reads the same
exported meshes, offers all three options and the unchanged R4 comparison,
and can hide the caps to reveal the sourced switch and socket geometry.
`package_release.py` builds the checked portable archive with source dependencies.
Older revisions bundled under `source/` are historical comparisons and dependencies;
their original fit reports are not current approval of the bought parts.
