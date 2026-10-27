# Print V19 — solid band at the butt, substantially slimmer grip

The removable handle is now a **solid 7 × 4 mm band**, replacing V18's thick hollow 18 × 12 mm section. It has softened edges and local reinforcement at the fitted locking ends. The prepared print uses **100% infill for the band and its matching foot coupon**; the other parts retain 20% infill.

The handle and all three buttons move **28 mm down together**. Lower/upper mount centres are 14 / 104 mm from the butt. The handle's lowest point is 9.2 mm above the butt, leaving 6.2 mm above the visible cap flange for attachment/release clearance. Thumb, index and middle remain at +7 / +3 / −23 mm relative to the upper mount: 111 / 107 / 81 mm absolute. Both handed stems use the same group offsets and mirrored angles. [Frozen design principles](../magic-wand/hardware/printed-loop-wand/v19/design-principles.json) and the project skill make the butt reference and control relationships explicit inputs; a coupling revision must not move them as a side effect.

## Grip size

Hand-contact depth is **5 mm smaller than V18** throughout the checked 30–111 mm grip area. At 42 mm height, the body changes from 25.45 mm round to **24.6 × 20.45 mm oval**, excluding the raised helix. The battery requires the retained width. Above the cell it becomes round: at 96 mm height, **18.71 mm instead of 23.71 mm**. The cap flange remains 30 mm. These are axis measurements, not a claim of a 5 mm reduction in every direction around the cell.

The main bore stays 10.4 mm. The compact upper grip requires the small three-lug bayonet at the grip joint too; all three new joints fit inside a continuous taper. There is no added joint collar. The original solid counter-wound helix, curved leaf windows, rounded supporting rails, diamond head, clipped Sense cradle, upward USB access and captured cover remain.

## Handle and battery-cap locks

Both handle ends go directly into matching recessed seats. Fit the two pegs with the handle 12° clockwise viewed from the tip, lift 4 mm, turn left 12° along the 0.6 mm cam rise and let the catch seat. To remove, release the tab outward, turn right, lower and withdraw. The bare wand has recessed openings and no projecting handle mounts. Small switch clips have hidden root ties and positive upper/lower stops; no square surround or printed keycap is added.

The short battery cap has its own three-lug turn lock and a retaining floor, clearing the low handle entry. The provisional 20 × 6 × 40 mm cell has a checked 20.4 × 6.4 × 42 mm clearance envelope. Rear corners of the thin battery sled are relieved to fit the oval cavity. Measure the actual cell before printing; its purchased dimensions remain unverified.

## Prepared projects

- [Complete — both handed stems and one shared set of remaining parts](Print-19-complete-left-right-solid-band-butt-grip-410mm.3mf). Select one stem per wand.
- [One left wand](Print-19-one-left-wand-410mm.3mf).
- [Small handle-lock fit test](Print-19-detachable-loop-fit-test.3mf), [switch fit test](Print-19-recessed-switch-button-fit-test.3mf), and [shaft-joint fit test](Print-19-slim-bayonet-fit-test.3mf).
- [Solid handle only](Print-19-replacement-loop-only.3mf), for a matching V19 stem.
- [Upper replacement for the old V2 stem](Print-19-upper-only-helix-410mm.3mf), a separate retained-stem configuration.

**The V19 stem, cap, sled, loop and lower shaft form a revised assembly; do not mix their interfaces with V18.** Earlier revisions remain unchanged. The complete project always includes both hands.

## Verification and material

Eighteen exported meshes are closed, consistently wound and each one connected body. Checks cover both hands, purchased switch/socket clearance, switch capture and released insertion, both handle locking routes, independent hard stops, catch/preload, battery-cap insertion/turn/capture, cell/sled space, USB/board/cover fit, the bore, helix material and retained rails. Sliced path samples check working holes and cable routes separately.

One complete left wand estimates **61.305 g printed parts**, plus **3.574 g removable support/brim**, using P1S 0.4 mm PETG, 0.2 mm layers, 3 walls and the part-specific infill above. V18 estimated 72.411 g printed parts. Electronics, cell, wires, switches, sockets and purchased caps are additional and unweighed. The solid band prints with its broad plane horizontal, using removable support beneath the narrower band between the wider locking ends. Thin switch plates stay broad face down.

Physical strength, PETG fatigue, force, fit and comfort need a print test. Print the small lock and switch tests first. [Interactive preview](../magic-wand/hardware/printed-loop-wand/v19/preview/) includes the old/new comparison, both hands, the bare wand and the actual assembled handle. Install requirements.txt, rebuild wand_cad.py into a new directory, then use check_geometry.py, print_projects.py and verify_release.py to reproduce the checked files.
