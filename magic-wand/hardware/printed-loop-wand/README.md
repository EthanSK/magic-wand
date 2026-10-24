# Printed loop wand

A fully printed body for the current three-button Puck.js wand: three interchangeable loop
handles that plug onto one shared shaft and tip with a push-and-twist lock.

**Status: first print set, not yet printed.** The model geometry is generated and checked
(closed solids, fit on the bed, no unintended collisions, joint keyed and retained in the model).
Printed fit, strength, comfort, balance and mass are not measured. Every clearance here is a
starting value for PETG on one printer profile, not a tolerance that works everywhere.

This is a mechanical body only. It is not a new controls version or prototype profile; the
existing three buttons and their roles are unchanged.

## What's here

| File | Purpose |
| --- | --- |
| `dimensions.json` | Every editable dimension (mm). Change values here, then rebuild. |
| `wand_cad.py` | The one parametric geometry source. Builds, exports and checks everything. |
| `requirements.txt` | Pinned geometry toolchain (manifold3d, trimesh, numpy). |
| `exports/*.stl` | Binary STL per printable part, already in print orientation. |
| `exports/assembly.glb` | All three assemblies side by side, with a Puck case reference. |
| `exports/manifest.json` | Hashes, sizes, print notes, transforms and every check result. |
| `preview/` | Browser preview of the three options, the joint and a section view. |

## Two pieces, more prints

Ethan asked for a wand in two pieces where the wand end plugs into the handle. Those are the
two assemblies:

1. **Handle** (one of three) with its button pod. Swappable.
2. **Wand**: lower shaft, upper shaft, tip cradle and cap, glued once into one piece.

The wand is about 360 mm long, longer than the 256 mm bed, so it prints as four parts joined by
glued half-laps (long flat overlaps, not threaded stems). After gluing it behaves as the single
second piece.

Default overall length is 500 mm, butt to cap, matching the existing roughly 50 cm wand. Change
`overall.length` to resize the shaft.

## Handles

All three share the spine, socket, button rail and wire route; only the loop differs. The
loop is a 22 mm wide bar with 45° chamfers. Opening sizes are measured from the model's
mid-plane section.

| Handle | Opening (length × height) | Intended grip |
| --- | --- | --- |
| Round | 38 × 38 mm | Mug-style loop for two fingers; thumb on the buttons. |
| Oval | 101 × 31 mm | Long D-loop around four fingers, so the wand stays on a relaxed hand. |
| Angled | 100 × 47 mm (deepest at the palm) | Raked loop for a less bent wrist while pointing. |

Comfort is untested; these are three distinct starting shapes to try, not ergonomic claims.

## The twist-lock joint

The lower shaft ends in a 13 mm spigot with three pins. The handle has a matching socket.

- **Keyed entry.** The pins sit at 10°, 190° and 280° (measured from the button side, clockwise
  seen from the tip). The uneven spacing only lines up with the socket's entry slots one way,
  so the Puck and buttons always end up on the same side.
- **Push in.** Hold the shaft with the Puck turned 38° anticlockwise from upright and push it in
  until the spigot end meets the socket floor. The floor is the axial stop.
- **Twist.** Turn the shaft 38° clockwise (seen from the tip) until the Puck is upright. Each pin
  rides a ramp, crosses a small ridge (0.15 mm interference by default) and drops into a
  shallower pocket (0.05 mm), pulling the spigot onto the floor. The ridge is what should resist
  turning back; the end of the groove stops over-twisting.
- **Retained.** In the locked position each pin sits under a 6.5 mm thick retaining wall, so the
  shaft can't pull straight out.
- **Release.** Twist back 38° past the ridge, then pull.

The ridge and pocket rely on PETG flexing very slightly. Only the real print shows if that
feels like a click, a firm stop or nothing, so the coupons come first.

A plain friction taper would be simpler but can't key the Puck's orientation or resist
rotation, so it isn't included. If every coupon fails, a taper is the fallback.

### What the model checks (exports/manifest.json → checks.joint)

- At the entry angle the spigot slides fully home with zero overlap.
- It can only be pushed in within ±2° of the entry angle; every other angle collides.
- Through the twist, the only overlap is the cam: at most 0.15 mm along the axis.
- Locked, every coupon variant rests on the 0.05 mm pocket.
- Pulled 0.6 mm outward when locked, or twisted 6° past locked, the parts collide.

These prove the geometry does what's described. They don't prove the printed parts will.

## Print set

All parts are exported in print orientation, sitting on z = 0. Supports aren't expected on any
part; horizontal bores use flattened teardrops so their tops bridge 1–3 mm instead of arching.
Brims help the long thin shafts stay down. No slicing was done for this set.

Print in this order:

| # | Part | On the bed | Notes |
| --- | --- | --- | --- |
| 1 | `coupon-male` | Flat +X face | The real shaft spigot and pins, 28 mm long. |
| 2 | `coupon-female-a/b/c` | On its side | Real handle socket and 14 mm of button rail. 0.05 / 0.15 / 0.30 mm cam ridge; 1, 2 or 3 notches on the back. |
| 3 | `coupon-puck-ring` | Flat | The tip pocket and rim, 6 mm tall. |
| 4 | `shaft-lower`, `shaft-upper` | Flat +X face | 183 mm each. Brim recommended. |
| 5 | `tip-cradle`, `tip-cap` | Pocket up / cap top down | |
| 6 | `button-pod-pilot` or `button-pod-blank` | Top down | Pilot holes mark the three button centres. |
| 7 | `handle-round`, `handle-oval`, `handle-angled` | On its side | 140 mm long. Start with one. |

Handles and shafts print with layers along their length, which is usually the stronger
direction for bending. Wall and infill settings are yours to choose; nothing here has been
strength tested.

## Tip and Puck

The tip cradle holds the Puck.js v2.1 in its stock case, flat, with its top facing the button
side, matching the website model and the device code's axis mapping. The case is documented as
36 mm × 12.5 mm; the pocket is 36.6 mm and was not checked against a real case.

- The cap ring presses over the cradle rim and overlaps the case edge by 1.5 mm. The centre stays
  open, so the light and the Puck's own button remain exposed.
- Thumb notches on both sides lift the case out to reach the battery.
- A notch at the front of the rim marks the forward direction. The pocket is round, so turn the
  case to match the current wand before closing the cap, then check the pointer directions.

## Wiring

The three buttons and ground are four wires, as in [BUILDING.md](../../BUILDING.md):

Puck case → rear notch in the cradle → groove under the cap → 5 mm bore through both shafts →
spigot end → connector bay behind the socket floor (12 mm × 17.5 mm) → 6 mm channel → wire hole
in the rail → inside the button pod.

A 3 mm wire path through the whole route clears every part in the model. To swap handles
without re-soldering, put a small four-way inline connector in the bay; the mated connector must
pass the socket floor opening, 9 mm round with a peak (about 9 × 10.9 mm). No connector is specified. Thread the shaft wires
before fitting their connector.

## Button pod

The pod slides onto the dovetail rail from the back of the handle until it meets the stop, and a
short piece of 1.75 mm filament through its back end pins it to the rail. The pod has a 13 mm
wide, 10 mm deep cavity. The real switch sizes are unknown, so there are no switch holes:
`button-pod-pilot` has 2 mm pilot holes at the Bottom, Middle and Top centres (22 mm apart,
Top nearest the shaft); `button-pod-blank` has none. Measure the switches, then drill out, or set
`pod.height`, `pod.button_pitch` and the cavity size in `dimensions.json` and rebuild.

## Fit checklist

Coupons first:

- [ ] Male coupon enters each female coupon at one angle only and slides home without force.
- [ ] Twisting 38° clockwise: resistance rises, then it settles. Note click, stop or nothing.
- [ ] Locked: a firm pull doesn't separate them. Note any wobble.
- [ ] Twisting back releases with deliberate force, then it pulls out.
- [ ] Pick the best of a, b and c and set `joint.cam.crest_interference` to match. If all are loose
      or tight, adjust `joint.bore_clearance`, `joint.slot_clearance` or the cam values and reprint.
- [ ] The stock Puck case drops into the ring coupon, sits flat and lifts out with the notches.
- [ ] A printed pod slides onto a female coupon's rail without binding or rattling.

Then the full parts:

- [ ] Glue the shaft half-laps and the tip with the flat +X faces down on a flat table. Glue
      strength on PETG is untested.
- [ ] Each handle: reach to all three buttons, loop comfort, wrist angle while pointing.
- [ ] Balance and weight with the Puck fitted.
- [ ] Pointer directions after mounting the Puck in the cradle.

## Rebuild and check

```sh
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python wand_cad.py          # rebuild exports/
.venv/bin/python wand_cad.py --check  # rebuild in memory, compare byte for byte, run every check
```

The build is deterministic: rebuilding with the pinned toolchain gives identical bytes.
`npm run check` (repository root) also verifies the exports against the manifest and checks
every STL is a closed mesh, without the Python toolchain.

## Preview

Serve the repository root and open the preview (it reuses the website's Three.js):

```sh
python3 -m http.server 8850 --bind 127.0.0.1   # from the repository root
```

Then open `http://127.0.0.1:8850/magic-wand/hardware/printed-loop-wand/preview/`.

## Known limits

- Nothing has been printed. Fit, strength, comfort, balance and mass are unmeasured.
- The Puck case size, switch sizes, button spacing and wire bundle size are documented or assumed,
  not measured.
- The cam relies on small elastic interference; PETG may creep and loosen it over time.
- The spigot stops on a socket floor ring about 1.6 mm wide, narrow so the connector can pass;
  its wear is unknown.
- Overhang figures in the manifest are a simple face-angle count, not a slicer's verdict.
