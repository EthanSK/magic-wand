# R59 slide-on finger guards and lengthwise battery sleeve

**Status: fit trial. The CAD checks and both native slices pass. Physical fit, strength, and click feel still need a trial.** Bought-part sizes are model estimates unless stated.

R59 changes the key holder, adds two finger guards and a battery cap, and revises the OP1 retainer, the pin clip and the two touch-board post clips. The paddle (R58), hinge pins and post bar (R57) are unchanged.

## What changes

| R58 finding | R59 |
| --- | --- |
| Guard supports rise toward the upper row and block the lower sockets. Only the right side has an outer arm to the bottom edge. | The built-in guard, its legs and arms are removed. Each side gets a separate guard that slides onto two rails under the front rim. Left and right are mirror images, with the outer arm where the R58 right arm was. |
| The battery tray sticks out 8.85 mm on the left and its top flexes. | The pouch lies along the rod in a sleeve inside the holder's own width. Every sleeve wall runs fore and aft from the rear face. |
| Small parts were missing from the plate. | One plate carries the complete kit across 15 separate printed positions, including both post clips, the pin, its clip and a spare. The optional snug pin and two socket backers are included. |
| What are the two flat strips for? | They back a lower socket from the side while its switch is pushed in. With a guard off, hold the socket up with a fingertip. Use a strip if the guard is already fitted. Both still pass on the R59 holder, guard on or off. |
| The Gravity plug almost fits; the wires are pushed. | The pin clip's grip stood level with the top of the touch board, directly behind the board's socket. Its front is 0.95 mm lower and the rest 0.5 mm lower. |
| A broken piece jammed the click, and the slide-in OP1 retainer felt fragile. | Each tower stem spreads its load into a wider, rounded root. The inner corners are relieved to keep the retainer clear through a press. |
| The touch-board clips felt fragile. The source of the broken piece is uncertain. | Both post clips are 1.4 mm thick, up from 0.8 mm, with the same snap shape. |

## Why the guards are separate parts

The holder prints rear face down. A guard held only at the front edge would be laid down before the arms that hold it, so it cannot be printed as part of the holder without support. A guard that is its own part prints flat and can hang from the front edge.

## Finger guards

- A flat shelf 1.8 mm thick under each lower key, underside at Z −0.5 (the R58 rest plane), printed finger side down.
- Two arms at the front edge slide onto two dovetail rails under the front rim, X ±27.6 and ±14.6, Y −9.2 to −1.5. The rails widen 0.4 mm per side toward the rear, so the guard wedges on by hand. A nose on each arm meets the rim as the hard stop.
- The side toward the upper row is open. The lower socket's sideways loading path still passes behind the arms and above the shelf with a guard on (0 mm³ against all 336 inherited switch, socket and loading poses).
- Sliding on from the front over 14 mm: 0 mm³ against the holder and fitted parts. Seated, the wedge overlap with the rails is 0.016 mm³.
- The shelf covers 50.7 mm² of the right socket's 51.1 mm² plan area, and 50.0 mm² of the left.
- Calculated for 10 N at the rear edge: 0.4 mm of bend, 13 MPa. The socket loading path is 1.27 mm above the shelf. Per 3.25 mm of width the shelf's section modulus is 1.76 mm³; an R58 beam was 1.60 mm³.
- The wedge fit and the rail strength are not tested.

## Battery sleeve

- Micron 72217, 27 × 11.8 × 3.9 mm, in a 28.1 × 12.9 × 4.55 mm space at X −22.3 to −9.4, Z 0.65 to 5.2, starting at Y 10.6. The wire lane beside the rod starts at X −8.5.
- The pouch slides in from the rear with the rod in place: 0 mm³ over 29 mm, and 0 mm³ seated against holder, fitted parts, rod, wire lane, OP1 lead and both guards.
- The sleeve is 22 mm long and the pouch 27 mm, so the pouch end stands 5.45 mm past the rear face. A separate slip-on cap covers it and reaches 7.55 mm past the rear face. Its inboard side is open for the leads, so the bought plug stays outside. It clicks over a 0.25 mm ridge under the sleeve floor. The click is not tested.
- The sleeve is open under the upper-left socket's loading path. That socket loads from below with the battery out. No other key path is affected.
- Holder left edge: X −38.85 in R58, −30.77 in R59, which is the bank's own edge.
- Which end the leads leave and their slack are not confirmed on the bought pack.

## Mass and printing

- Solid PETG at 1.27 g/cm³, not sliced weight: R58 holder with tray 12.29 g; R59 holder with rails and sleeve 10.95 g; two guards 2.30 g; cap 0.49 g. The removed built-in guard was 0.75 g.
- Print proxy (area that starts with nothing under it, bridges included): 97.5 mm² for R57, 120.3 mm² for R58, 96.3 mm² for R59. Nothing starts in mid-air beside the bank seams.
- The left outer underside base tab moved from X −24.5 to −26.2 because the left sleeve wall now stands at the old station. The left inner tab roots in the sleeve floor.

## Click side (`click-fit.json`)

- **Gravity plug.** The plug and lead come with the DFR0030 board (3-way PH 2.0 mm); they are not printed. Modelled as a nominal 8.0 × 4.8 mm housing with 3.6 mm behind the socket and three wires; the socket position is a photo estimate, not a measurement. Room under the plug before it meets the pin clip: 0.3 mm with the R57 clip, 1.25 mm with the R59 clip. Plugging in and pulling out over 9 mm, and the press and 6° lift sweep, give 0 mm³. The board, post height and click bar did not move.
- **Left hole.** Two candidates: the left post hole in the paddle and the left hinge hole in the holder. The CAD openings are mirrored (0.0003 and 0.0 mm³ difference). Both hinge cheeks accept a 3.2 mm toolpath gauge, and both board-post holes pass their deposited-path checks. The wall starts are closer to the insertion face on the left. This may matter if the seam bulges in the physical print. The cause of the previous print's uneven hole remains unknown.
- **Stop retainer.** Stem root section 2.2 → 4.2 mm², section modulus 0.25 → 0.49 mm³. The sideways gap to the paddle is 1.07 mm and lift stops at 0.884 mm at the button. The press stroke clears with 0.6 mm of side shift. All 30 reachable poses in the hinge-play check clear, with a smallest sampled gap of 0.202 mm. It still needs the paddle held down while it slides in.
- **The step under the retainer track** is the OP1 board's own slot, left open at the front because the board's true length is unknown. Slide the retainer into the upper ledge, under the two rail lips. The assembly guide labels the board ledge and the retainer track.
- **Post clips.** 1.4 mm thick, 1.75 times the arm section. 0.8 mm of the 2.2 mm post neck is left free, so the board can sit up to 0.8 mm high. Which arm broke is not known, and no strength was measured.

## Native slice and deposited paths

Bambu Studio sliced the 15-part plate and the separate sacrificial stabilising tower. The same layout was reopened and sliced again. Both sets of paths were checked with `verify59.py`.

- The plate slices without path conflicts once the small parts stand clear of the stabilising tower's brim.
- Passed on the deposited paths: part separation, every pad's first-layer area, every key and socket route at its fitted position, both guards sliding onto their rails, the battery sliding in, the pin and sleeve gauges, and both board clip mouths and bores. The paths contain zero support moves and zero completely unsupported starts on the 15 parts.
- The holder keeps the broad adhesion pad with six thinner ties. The checked joined area is 24.15 mm², down from 24.79 mm² for R57. No sacrificial base attaches in the hinge bay. The contact area measures the sliced geometry. Removal force still needs a physical check.
- Bambu Studio reports a generic floating-regions notice for the holder on both slices. The deposited paths show zero completely unsupported starts. Opus traced four printed candidate regions to backed beads, and eight thin candidates to regions with no extrusion. The fit trial still needs a first-layer and adhesion check.
- The cap's first version failed this audit: its detent notch left a 0.3 mm wall that did not print. The tongue is now 0.9 mm with 0.6 mm left at the notch.

## Assembly guide

The guide shows the guards sliding on and off, the battery loading beside the rod, and the order for seating the touch board and OP1 retainer. The full 500 mm rod view uses the same updated key assembly. Dry-fit the Gravity plug with slack before seating the touch board. After releasing the base, trim and file the tie under the rear of the battery sleeve flush (under 0.1 mm) before fitting the battery or cap. Check how the guards seat and stop if the retainer or board clips crack.

The [A1 mini PETG print file](exports/print-mechanisms/R59-Complete-Key-Holder-A1-mini-PETG-print-only.3mf) uses the reviewed primary slice. Its estimate is about 3 hours and 26 g. The [slice review](exports/print-mechanisms/review.json) records the exact checks and fit-trial observations.

## Build order

Fresh process each, through the guarded geometry runner with the Wand CAD environment.

1. `carrier59.py` writes the holder, both guards, the cap, the pouch reference and `carrier.json`, and copies them into `exports/`.
2. `build59.py` writes the retainer, pin clip and two post clips.
3. `checks59.py` writes `click-fit.json`.
4. `guide59.py` copies the unchanged R58 meshes and results into `exports/` and writes `exports/assembly-guide.json`. `--register` adds it to the catalog as `r59`.
5. `plate59.py LAYOUT.3mf`, then the saved headless A1 mini slicer.
6. `verify59.py PLATE_FOLDER` checks the deposited paths. Reopen the same layout and repeat checks.
7. `release59.py PLATE_FOLDER REOPENED_FOLDER` packages the reviewed primary file after its independent review.
