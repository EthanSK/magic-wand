# Carbon-tube wand assembly blueprint

`manifest.json` is the assembly index and evidence record. It points directly to
the existing editable CAD, dimensions, bought parts and sliced mass receipts.
`derive.mjs` reads those sources at run time. Do not hand-maintain another copy
of their dimensions or regenerated weight totals.

## What is recovered

- The original tube is identified as AT Models / D-Pultrusion **510072**:
  nominal **8 mm outside, 7 mm inside, 500 mm stock length**. This does not prove
  the length of the tube currently in the hand. The old website description
  still mentions the Puck; it is not a current physical assembly survey.
- The intended Sense board is the **original XIAO nRF52840 Sense**, with
  LSM6DS3TR-C motion sensor, rather than a Plus or an MG24 replacement.
- `carbon-rod-holders-r2` is the **three-key CAD prototype**. Its full illustrative
  [assembly GLB](../carbon-rod-holders-r2/exports/Assembly-reference.glb) includes
  the tube, carrier, tip frame and reference bought parts. Its sensor frame
  uses the source's tip translation; this is a design position, not measured.
  Its inherited switch/socket reference was later corrected in R4; the preserved
  R2 model is historical geometry, not a recommendation to print untested seats.
- `carbon-rod-holders-r4` is the later **five-key prototype**, with front, rear
  or lower battery carriers. Its [preview](../carbon-rod-holders-r4/preview/index.html)
  and `cad.py` describe local accessory geometry. The short preview rod and
  coincident local origins do **not** define a complete 500 mm assembly.
- Ethan confirmed the current wand has **three keys, one small battery, one
  XIAO Sense and a carbon rod**, with the keys/grip estimated **8–10 cm from
  the bottom**. This is an authorised side-chat report, not a measured survey.
- No recovered record establishes the currently fitted holder revision,
  physical component positions, cut tube length, complete mass, balance point
  or moment of inertia. The default `physical-current` profile preserves this
  gap; it does not select the latest CAD automatically.

The manifest lists every assembly group, including wiring, solder, insulation,
tape/glue and connectors. Holder and carrier groups stay present even when
their construction is unknown. Identify a physically absent group explicitly
with a zero mass and evidence, rather than omitting it from the inventory.

## Weight evidence

The helper extracts model plastic from existing Bambu receipts; support,
brim, startup waste and bought parts are excluded. These are **slicer estimates,
not weighed parts**. Use `--profile r2-three-key`, `r4-front`, `r4-rear` or
`r4-lower` to see current source values. It verifies the source/geometry hashes
and matching sliced archive before using those receipts.

Supplier pages checked on 2 November 2026 identify the parts but do not supply
an unambiguous net mass for these exact fitted items. AT Models' bare
`Weight 0.200000` field has no stated unit or scope and is not used. Published
weights for other makers' LP402025 batteries are not interchangeable with the
PKCell purchase. See the exact source links in `manifest.json`.

## Reproduce or add physical measurements

From the repository root:

```sh
node magic-wand/hardware/assembly-blueprint/derive.mjs
node magic-wand/hardware/assembly-blueprint/derive.mjs --profile r4-front
node magic-wand/hardware/assembly-blueprint/derive.mjs --scenario illustrative-lengths
node --test magic-wand/hardware/assembly-blueprint/derive.test.mjs
```

The default output deliberately has `total_g`, `centre_of_mass_mm` and
`inertia_about_grip_x_g_mm2` set to `null` until the required evidence exists.
`known_subtotal_g` never means the total assembled weight. No generated report
is an editable source of truth; stdout can be saved as a dated receipt.
Per-part receipt values are rounded; their sum can differ from the receipt's
aggregate `printed_parts_g` by 0.001 g. Neither is a scale measurement.

Keep private evidence outside the public repository, and pass a JSON file with
`--measurements /path/to/private-measurements.json`. `--repo /path/to/repository`
supports running the same helper from a private draft directory. The shape is:

```json
{
  "evidence": "dated measurement note",
  "tube_length_mm": null,
  "tube_diameters_mm": null,
  "grip_pivot_mm": null,
  "components": {
    "sensor_board": {
      "mass_g": null,
      "centre_mm": null,
      "basis": "measured",
      "evidence": "scale resolution, included parts, measurement date"
    }
  }
}
```

Use one mass for each **whole group**: for example, all three switches,
not one switch multiplied again. Add entries for every manifest component.
Positions are `[X,Y,Z]` in millimetres: origin at the tube butt, +Y towards
the tip, +Z towards key faces. Move `grip_pivot_mm` to compare grip positions.
For physical tube geometry, supply `tube_diameters_mm` as
`{"outside":8,"inside":7,"basis":"supplier","evidence":"exact tube source"}`
only if that source genuinely identifies the fitted tube. Enter its measured
length separately. Record source uncertainty in the evidence.

The inertia calculation is about the X axis through the chosen grip. Bought
parts are point masses at their entered centres; optional
`intrinsic_x_g_mm2` adds a known part's own inertia. The tube uses the uniform
hollow-cylinder formula. Other parts' internal mass distributions are not
known; this is a rigid-body comparison, not a prediction of hand steadiness.

## What a shorter wand changes

The optional `illustrative-lengths` scenario reproduces the side-chat arithmetic
using **assumed**, not measured, density 1.6 g/cm³, a 4 g tip package, a 17 g
package exactly at a grip 90 mm from the butt, and the existing nominal 8/7 mm
tube dimensions. The 500 mm baseline and shorter candidates retain those same
packages. An additional endpoint envelope uses an 80–100 mm grip and 2.5–5.5 g
tip; it is not a statistical uncertainty or a measurement interval. The source
inputs live only in `manifest.json`; the helper computes the comparison.

For the same small mass moved along the tube, its resistance to turning about
the hand scales with **distance squared**. A uniform tube of unchanged
cross-section, turning about its butt, scales approximately with **length
cubed** (the small tube-radius term also remains). The helper can compare
measured alternatives without choosing an “optimal” length.

More inertia can resist a brief unwanted twist, but it also requires more
effort to start and stop; fatigue, grip mechanics and the user's movement are
not captured by that formula. A gyro reads rotation, so a long tube is not
itself an electronic amplification of its angular reading. These facts do
not establish that shortening the current wand will improve or worsen its
pointer stability. No cutting, sensor move or sensitivity change is approved
by this blueprint.
