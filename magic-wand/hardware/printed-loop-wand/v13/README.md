# Print V13 — upward-seating detachable finger loop

The loop now attaches by sliding **upward 22 mm relative to the wand**, into closed upper track ends. To remove it, press the side release tongue outward, slide the loop **downward 22 mm**, then move it away. When the tip points upward and the loop is held, downward wand load seats the mount against the upper stops. The stops carry that load independently of the release tongue; the tongue prevents downward withdrawal.

Both mount tracks and the latch direction are reversed. Their entry sweep sits outside the retained spiral and clears the battery cap. The receiver backs connect the tracks to the stem. V12's loop shape, curved leaf openings, 3.6 mm rounded rails, 1.6/1.8 mm grip/shaft reinforcement, 410 mm length, taper, full raised helix, button positions, thin switch plates, head/cradle/USB and battery/wire routes remain. The shafts, diamond, cap and other shared parts have identical mesh hashes to V12.

**Print the V13 stem and detachable loop as a matching pair.** They do not mate with the former V12 loop/stem mounts. The changed meshes are the two handed stems, loop and two small mount coupons. Button plates still slide from above; the diamond cover retains its own captured upward removal path.

## Projects

- [Complete: both handed stems plus one shared set of the other parts](../../../../magic-wand-3d-models/Print-13-complete-left-right-top-slide-410mm.3mf). Choose one stem for one wand.
- [Exactly one left wand](../../../../magic-wand-3d-models/Print-13-one-left-wand-410mm.3mf), used for the mass comparison.
- [Small upward-seating loop test](../../../../magic-wand-3d-models/Print-13-detachable-loop-fit-test.3mf). Try this before printing the full matching stem/loop.
- Unchanged interfaces: [button coupon](../../../../magic-wand-3d-models/Print-13-top-slide-button-fit-test.3mf), [bayonet coupon](../../../../magic-wand-3d-models/Print-13-slim-bayonet-fit-test.3mf), [upper replacement retaining a V2 grip](../../../../magic-wand-3d-models/Print-13-upper-only-helix-410mm.3mf).

## Evidence and limits

Both hands have no seated overlap, clear downward release and outward removal paths, clear battery-cap/keycap paths, radial capture, downward latch capture and positive upper-stop interference with the latch geometrically released. The small coupon is checked separately, including its backing and reversed release tab. All eighteen meshes are watertight, consistently wound single bodies. Existing board/USB/wire, switch, head-cover, shaft-joint, taper, spiral and aperture checks are retained. Six prepared P1S 0.4 mm PETG projects slice without reported warnings. Sampled extrusion checks include supports and first-layer adhesion in protected routes and all opening interiors. Remove the external support beneath the lower track mouth before fitting; that support is below the receiver, outside its internal sliding passage. The flat loop uses manual support at its two mounting roots and no brim.

One complete left wand estimates **76.718 g printed PETG**, compared with V12's **75.875 g**: **0.843 g more**. Supports/brim add **4.872 g**, with **81.69 g total slicer filament** including startup/rounding. Hardware remains unweighed: 3.282 g remains for the 80 g all-up aim or 23.282 g for the 100 g ceiling. These are slicer estimates, not measured complete-wand weight.

Physical load capacity, PETG breaking force, latch force/fatigue, printed tolerances and comfort remain unverified. The battery envelope remains provisional at 20 × 6 × 40 mm. Use a small fit and load trial before relying on the mount. No physical print is started automatically.

## Rebuild and inspect

Install [requirements.txt](requirements.txt), then use fresh output directories:

```sh
python -B wand_cad.py --out NEW_GEOMETRY_DIRECTORY
python -B check_geometry.py
python -B print_projects.py --out NEW_SLICE_DIRECTORY --slice
python -B verify_release.py --check
```

The source imports unchanged V2 reference geometry. Serve the repository and open [the interactive preview](preview/). Loop mount direction shows the downward released pose, upward attachment arrow and closed upper stop. Compare shows V12 beside V13. Both hands, attached/detached/off states and all existing mechanical views remain available. Bought caps, board and battery references are not printed parts. Earlier releases are preserved.
