# R57 pin hinge and longer touch-board posts

The CAD fit and native slice were checked for the Bambu A1 mini with PETG. The printed pin fit, clip retention and click feel still need a physical trial.

[Hinge assembly](../carbon-rod-holders/assembly/?version=r57&component=keys&view=pin_hinge) · [Full 500 mm rod assembly](../carbon-rod-holders/assembly/?version=r57&component=whole)

R57 changes the paddle hinge and the two touch-board posts of the carbon-rod Magic Wand mouse. The switch sleeve, the two crowns, the OP1 pocket and lid, the four key openings and the rod clips are the R53 design.

## What changed from R56

| R56 on the bench | R57 |
| --- | --- |
| The D-shaped axle, open seats and sliding cap needed more precision than the printer gives | A plain 3 mm printed pin passes through one hole in each holder cheek and one hole through the paddle barrel. Each hole is 0.5 to 0.6 mm larger than the pin. |
| Nothing obvious held the hinge together | A small clip drops into a slot in the middle of the barrel and snaps over a waist in the pin. The pin cannot slide out either way. |
| The post necks were too short to take the clips, because the touch board sat above the paddle | The clip neck is 2.2 mm instead of 1.0 mm. The paddle top is also cut away under most of the board. |

## Parts

| Body | Print | Job |
| --- | --- | --- |
| Key_Carrier | Yes, on the R55 open-bay base | Two cheeks, 4.1 mm thick, each with one 3.5 mm hole. At least 1.6 mm of solid plastic all round each hole. |
| Touch_Paddle | Yes | Barrel with a 3.6 mm hole and the clip slot. Board rests on the pad end, two edge rails and a land round each post. |
| Hinge_Pin | Yes | 3.0 mm × 21.8 mm, one flat to lie on the bed, tapered ends, 1.9 mm waist in the middle |
| Pin_Clip | Yes, plus one spare | Peg with two legs and a wide top to pinch |
| DFR_Post_Bar | Yes | The earlier posts with 2.2 mm necks |
| DFR_Tall_Clip | Optional, two | 2.0 mm thick clip for a board that sits flat |
| OP1_Lid, two 0.8 mm post clips | No, reuse | Unchanged |

## Assembly

1. Lower the OP1 board into its pocket and plug in the switch, as before.
2. Push the post bar up through the paddle, lower the touch board over the posts and slide a clip onto each neck. If the board sits flat and feels loose under the clips, use the two tall clips.
3. Lower the paddle so the sleeve goes over the switch and the barrel sits between the two cheeks.
4. Push the pin through one cheek, the barrel and the other cheek. Fit the pin before installing the upper key on the insertion side. The switch on that side crosses the pin's path.
5. Press the pin clip down into the slot in the middle of the barrel until it snaps.
6. Slide the OP1 lid in from the front.

To take the hinge apart, pull the clip up by its top, pull the upper key on one side, and push the pin out.

## Touch board height

The manufacturer's [DFRobot DFR0030 V2 photo](https://dfimg.dfrobot.com/enshop/image/data/DFR0030/20140710/_DSC0731_800x800.jpg.webp) shows the connector and surface-mount parts on the gold-pad side. Potential solder and connector pin projections below the board were checked against the earlier 1.5–2.0 mm estimate. The actual board-to-paddle gap has not been measured. The paddle now leaves everything open under the board except the pad end, a 2 mm strip along each long edge and a land round each post hole. The open zone leaves the connector pin tails clear in the two modelled board outlines. The two rear struts are 2 mm below the nominal board seat. If something still holds the board up, the necks accept a board raised by up to 1.3 mm with the existing clips.

## Build order

Run each script in a fresh process through the guarded geometry runner with the Wand CAD environment.

1. `build57.py` writes the meshes and `dimensions.json` to `exports`.
2. `checks57.py` writes `mechanical-fit.json` and fails if a route, clearance or the click travel is wrong.
3. `guide57.py` writes `assembly-guide.json`. It registers the guide only with `--register`.
4. `plate57.py LAYOUT.3mf` writes the editable plate. Slice it with the saved headless A1 mini script.
5. `verify57.py PLATE_FOLDER` checks the deposited toolpaths, including a 3.2 mm gauge through all three pin holes. Reopen and re-slice the same editable project and repeat the check in a `reopened` subfolder.
6. `release57.py PLATE_FOLDER` packages the checked machine instructions after review of the exact native archive.

## Fit-trial plate

[Printable 3MF](exports/print-mechanisms/R57-Pin-Hinge-A1-mini-PETG-print-only.3mf) · [Editable Bambu Studio project](exports/print-mechanisms/layout.3mf) · [Tray view](exports/print-mechanisms/tray.png)

The plate holds the key carrier, paddle, hinge pin, two pin clips including a spare, longer post bar and two optional tall clips. Each has its own pad. The OP1 retainer and the two standard board clips can be reused. The disposable timelapse tower has its own base.

[Mechanical fit](exports/mechanical-fit.json) · [Native opening checks](exports/print-mechanisms/fit.json) · [Re-slice receipt](exports/print-mechanisms/reopened.json) · [Independent printability review](exports/print-mechanisms/review.json)

[Mechanical notes](mechanical-notes.md) gives the dimensions, the tolerance bracket and the open questions.
