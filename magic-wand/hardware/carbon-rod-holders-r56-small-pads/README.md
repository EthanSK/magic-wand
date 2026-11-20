# R56 complete hinge kit with smaller removable pads

The left and right DFRobot clips each use a 12 × 12 mm pad. The sliding hinge cap uses 30 × 14 mm, the two-post bar uses 30 × 17 mm, and the OP1 board retainer uses 28 × 39 mm. Each has its own narrow tear tabs and a separate spot on the plate. The tall key holder uses the R55 open hinge bay with the removable tabs on the rear rim. The paddle and timelapse tower retain their original pad sizes. [Tray map](exports/tray.png)

## Connecting the hinge

The short D-shaped axle is built into the back of the DFRobot paddle. With the paddle sleeve over the OP1 switch, lower both axle ends straight into the open seats on the key holder. Slide the separate hinge cap forward from the rear until flush. The two-post bar fits under the paddle and the two small clips attach the DFRobot board to those posts. [Paddle underside](../carbon-rod-holders-r53-guided-op1/exports/review/R53-paddle-underside.png) · [Complete assembly](../carbon-rod-holders-r53-guided-op1/README.md#assembly)

## Print files and checks

- [Plate source](plate56.py), [editable 3MF](exports/layout.3mf) and [verified print-only file](exports/R56-Small-Pads-Complete-Hinge-print-only.3mf)
- [Actual deposited base areas](exports/wide-bases.json), [re-slice receipt](exports/reopened.json) and [independent review](exports/review.json)

Generate the editable layout with `plate56.py` and slice with the saved A1 mini profile. `verify56.py` checks the native archive. Reopen and slice once again into the `reopened` folder, then use `verify56.py --release` with the bound review. The active pieces keep the R53 meshes and their fitting routes. The smaller pads and the fit still need a physical trial.
