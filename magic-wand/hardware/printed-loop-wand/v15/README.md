# Print V15 — recessed detachable-handle attachment

The wand remains usable with the loop removed. The two receivers sit within the original curved stem surface; only small recessed keyhole entries and a catch opening remain. All enlarged locking pegs, roots and the release tab leave with the removable loop. Both handed stems accept the same loop. V14’s projecting housings are superseded.

## Fit and operation

Viewed from the tip toward the grip, hold the loop 12° clockwise from its final position. Press the release tab outward, place both pegs through the recessed entries, lift 4 mm, then turn left 12°. The cam rises another 0.6 mm; release the catch at the end stop. To remove, press the tab outward, turn right 12°, lower 4 mm, then withdraw the pegs sideways through their entry openings. Buttons, battery and wires stay in the wand.

The enlarged peg heads bear behind the original surface. Closed upper seats support normal tip-up load independently of the catch. Locked geometry captures radial and downward withdrawal, and the handle-carried spring prevents reversal. Reinforcement goes inward around the pockets, clear of the battery and central wire route. The small slot locally crosses a rear axial rail; the reinforced internal pocket provides the bypass. The original raised decorative helix remains intact.

Use the matching V15 stem and loop; they do not fit V14 mounts. Print the small test first and remove its exterior supports. Force, tolerance, comfort, strength and fatigue remain physical tests. The battery envelope remains provisional at 20 × 6 × 40 mm.

## Prepared projects

- [Complete: both handed stems and one shared set of remaining parts](../../../../magic-wand-3d-models/Print-15-complete-left-right-top-slide-410mm.3mf). Choose one stem per wand.
- [Exactly one left wand](../../../../magic-wand-3d-models/Print-15-one-left-wand-410mm.3mf).
- [Small recessed-lock test](../../../../magic-wand-3d-models/Print-15-detachable-loop-fit-test.3mf).
- Retained [switch-plate test](../../../../magic-wand-3d-models/Print-15-top-slide-button-fit-test.3mf), [shaft-joint test](../../../../magic-wand-3d-models/Print-15-slim-bayonet-fit-test.3mf), and [upper replacement for a retained V2 handle](../../../../magic-wand-3d-models/Print-15-upper-only-helix-410mm.3mf).

## Retained design and evidence

The 410 mm length, taper, complete counter-wound raised helix, Art Nouveau windows, final loop orientation, control positions, board cradle, USB access, head cover, battery cap and 10.4 mm main wire bore are retained. Thirteen of the eighteen meshes are unchanged from V14. Only the two stems, universal loop and two mount-test pieces change. Prior revisions remain unchanged.

The checks cover both handed bare-wand envelopes, intact original helix material, reinforced pocket floors, seated/released spring envelopes, radial entry, lift/turn/release paths, independent upper/radial/downward capture, reverse catch, end stop, button/cap clearance and all retained mechanical features. Geometry and slicer checks do not establish physical acceptance. Mass and final sliced-path results are in exports/.

One left wand estimates **76.139 g printed PETG** (0.864 g below V14). Supports/brim add 4.199 g. Without the loop, printed parts estimate 64.894 g. Electronics, battery, bought caps/switches/sockets and wires remain unweighed; allowance to the 100 g ceiling is 23.861 g.

## Source and preview

Install requirements.txt, then use fresh output directories:

```sh
python -B wand_cad.py --out NEW_GEOMETRY_DIRECTORY
python -B check_geometry.py
python -B print_projects.py --out NEW_SLICE_DIRECTORY --slice
python -B verify_release.py --check
```

[Preview](preview/) opens on the wand without its handle. Switch to Loop attached or use Compare for V14 beside V15 with the loop off. Cam track close-up shows the actual recessed receiver and matching peg/release assembly. Bought keycaps, board and battery are references, not printed parts.
