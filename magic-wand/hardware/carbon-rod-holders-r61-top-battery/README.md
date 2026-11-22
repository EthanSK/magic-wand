# R61 · Upper battery cradle and flat touch face

[Key assembly](../carbon-rod-holders/assembly/?version=r61&component=keys) · [Finger side](../carbon-rod-holders/assembly/?version=r61&component=keys&view=finger_rest) · [Battery loading](../carbon-rod-holders/assembly/?version=r61&component=battery) · [Full rod](../carbon-rod-holders/assembly/?version=r61&component=whole)

The lower finger guards remain part of the printed key holder. Curved round beams blend the finger-contact surface into the front and rear supports on both sides. The socket pin orientation, outside loading path and slide-in backing strips are the same as R60.

The integral friction-fit cradle is 11 mm farther along the rod. The printed rails project above the broad key banks. The end of the nominal battery projects about 15 mm beyond their top edge, including about 4 mm exposed for removal. Slide the wrapped 27 × 11.8 × 3.9 mm cell in lengthwise with its lead outside. The cell's lead exit and actual grip still need a physical fit check.

## Touch board and hinge

1. Fit the two-post bar to the loose paddle. Hold the DFR0030 with its flat gold face up and its white socket underneath. Plug in the three-wire Gravity lead while the board is loose.
2. Turn the lead out to the right through the open side in front of the hinge. Lower the board over the two posts. Slide one small clip onto each post.
3. Lower the paddle onto the OP1 switch. Slide the printed pin through the three aligned holes and press the centre clip into the pin groove. Hold the paddle down and slide the OP1 retainer over the switch board.
4. Press and release the centre and corners. Leave slack outside the hinge so the cable can follow the paddle. The wire bend, plug envelope and sensitivity in the assembled device need checking with the bought parts.

The hinge axis moves 11 mm along the rod. The paddle keeps its original board seats and contact bar. Its lowered right bridge gives the socket, mating plug and wires a top-open path. The guide shows the two sides of the DFR0030 using approximate electrode outlines from the manufacturer's photos. DFRobot documents capacitive operation and does not provide separate sensitivity ratings for each face. [DFRobot product and photos](https://www.dfrobot.com/product-78.html)

## Reproducing the model

In the project's Wand CAD environment, run `design61.py` for the printable/reference solids, then `fit61.py` for installation and hinge sweeps. Run `guide61.py --register` to regenerate the assembly guide. The guide shares the checked solids and hinge pivot with the model.

For a fit-trial slice, run `plate61.py layout.3mf`, slice with `slice45.py`, then run `audit61.py PLATE_FOLDER`. Repeat for the reopened layout. Use `release61.py PRIMARY REOPENED` with the hash-matched independent review. The 12-part layout includes both board clips, two hinge-pin fits, a spare centre clip and both lower socket backing strips.

## Fit evidence

The two lower return beams reach a maximum centreline slope of about 52°, compared with about 83° on R60. The key pins keep their previous orientations. All 336 sampled key positions and both socket-backer sweeps clear in CAD. The modeled wired board clears the fitted keys and OP1 retainer during a click, including the checked sideways offset. The extended tail keeps the rod bore and the parallel wire passage open.

The native 0.20 mm PETG slice has 62 checked loading and clearance routes. Both the side-running lead and the plug clear the paddle and holder at all 24 sampled lowering heights. The three spring measurements leave an opening of 11.66–11.67 mm against the battery's nominal 11.8 mm width. A physical trial is still needed for comfort, breakaway force, grip and electrical response.

The six breakaway fins contact the rim. The scanner measures 19.96 mm² of deposited joint next to the detachable base and zero in the hinge bay. A raw outline scan also counts plastic on both sides of folds within the permanent part. Its unclassified area is kept in the report for comparison.
