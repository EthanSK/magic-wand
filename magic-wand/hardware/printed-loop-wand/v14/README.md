# Print V14 — implemented lift-and-left-turn handle lock

The detachable loop now has actual cam tracks, spring preload and a positive reverse-turn catch. Its final position and orientation remain the same as V13. Both handed stems accept the same loop. This is implemented CAD and prepared print geometry, not the earlier explanatory diagram.

## Attach and release

Viewed from the wand tip toward the grip:

1. Align the loop at a **12° clockwise offset**, with both feet below their entry tracks. Press the release tab outward away from the shaft while engaging the mount.
2. Lift the loop **22 mm** along the entry tracks.
3. Turn it **left 12°** (anticlockwise). The tracks rise another **0.6 mm**, drawing the feet onto the cam seats. Release the tab at the end stop so its catch seats.
4. To remove: press the tab outward, turn **right 12°**, lower **22 mm**, then move the loop away. Wiring and controls remain in the stem.

Closed upper stops support normal tip-up load independently of the latch. The locked bayonet also blocks straight downward withdrawal with the catch released; the reverse turn is required first. The spring catch prevents that reverse turn until released. Its 0.62 mm seated deflection envelope provides radial preload to take up play; the full release envelope is 2.3 mm. The nominal 0.463 mm³ tooth overlap is confined to the compliant spring and clears in its seated deflection envelope. It is not rigid interference in the mount. The nominal tooth still presses against the seat throughout the measured rigid radial float (clear through 0.35 mm, captured by 0.4 mm), so that float cannot simply bypass the preload. Force, feel and fatigue require a printed trial.

**Print the V14 stem and loop as a matching pair.** Their mounts do not interchange with V13. The changed meshes are the two stems, loop and two small mount-test pieces. All thirteen other meshes, including shafts, head, cover, battery cap and switch plates, have identical hashes to V13. The 410 mm length, original raised counter-wound helix, taper, Art Nouveau leaf openings, reinforcement, 49/39 mm upper/lower loop reach, button positions, board retention, USB access, battery and wire routes are retained. Button plates and the head cover keep their own assembly directions.

## Bambu projects

- [Complete: both handed stems plus one shared set of the remaining parts](../../../../magic-wand-3d-models/Print-14-complete-left-right-top-slide-410mm.3mf). Choose one stem for one wand.
- [Exactly one left wand](../../../../magic-wand-3d-models/Print-14-one-left-wand-410mm.3mf), used for the mass estimate.
- [Small cam-lock mount test](../../../../magic-wand-3d-models/Print-14-detachable-loop-fit-test.3mf). Test this before printing the full matching stem/loop.
- Retained interfaces: [switch-plate test](../../../../magic-wand-3d-models/Print-14-top-slide-button-fit-test.3mf), [shaft-bayonet test](../../../../magic-wand-3d-models/Print-14-slim-bayonet-fit-test.3mf), [upper replacement for a retained V2 grip](../../../../magic-wand-3d-models/Print-14-upper-only-helix-410mm.3mf).

## Checks and weight

Both hands pass seated rigid-clearance checks, the full upward-entry and 12° turning route, released lowering and outward removal, bought-keycap and battery-cap clearance. Checks also cover radial/upward/downward capture without the latch, reverse-turn capture with the latch seated, the left-turn end stop and the separate single-mount test. All eighteen meshes are watertight, consistently wound single bodies. Existing helix, taper, board/USB/wire, head-cover, switch and shaft-joint checks remain. Six prepared P1S 0.4 mm PETG projects slice without reported warnings. Protected sliced-path checks include both entry tracks, several positions along each cam turn and every aperture interior, with supports and first-layer adhesion included. Exterior support below the track entrances must be removed before fitting; it lies outside the internal passages. The flat loop uses manual support at its roots with no brim.

Exactly one left wand estimates **77.003 g printed PETG**, compared with V13's **76.718 g**: **0.285 g more**. Supports/brim add **4.619 g**; total slicer filament is **81.72 g** including startup/rounding. Hardware remains unweighed: the allowance is **2.997 g** for an 80 g complete wand or **22.997 g** for the 100 g ceiling. These are slicer estimates, not weighed assemblies.

Physical fit, spring/cam force, breaking load, impact resistance, fatigue and comfort remain unverified. Test the small mount, remove supports and try a gentle load/flex trial first. The battery envelope remains provisional at 20 × 6 × 40 mm.

## Source and preview

Install [requirements.txt](requirements.txt) and use fresh output directories:

```sh
python -B wand_cad.py --out NEW_GEOMETRY_DIRECTORY
python -B check_geometry.py
python -B print_projects.py --out NEW_SLICE_DIRECTORY --slice
python -B verify_release.py --check
```

The CAD imports the retained V2 reference sources. [Preview](preview/): Lift and turn shows the raised entry pose; switch to Loop attached to see the final position. Cam track close-up displays the actual receiver transparently around the matching foot and catch. Compare shows V13 beside V14. Both hands and all retained mechanical views are available. Reference board, battery and bought keycaps are not printed parts. Earlier revisions are preserved.
