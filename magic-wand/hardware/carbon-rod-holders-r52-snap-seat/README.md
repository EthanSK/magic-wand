# R52 lift-in OP1 board and rounded click dome

R52 is a full nine-piece set for the carbon-rod Magic Wand mouse. The key carrier has two lifting tabs to hold the OP1 board. The DFRobot paddle has a wider rounded contact underneath and a closer-fitting hinge.

## Parts on the two plates

| Plate | Pieces to keep |
| --- | --- |
| Clips and holders | Two DFRobot post clips, XIAO holder and keeper, battery cradle and sliding lid, and the wire clip |
| Key carrier and paddle | Key carrier with integral OP1 retaining arms, and the hinged DFRobot paddle |

On the first plate, the two small matching clips sit next to each other at the front left. Each is about 10 mm long and 5 mm wide. The two loose post clips hold the gold DFRobot touch board on its paddle. Keep both. The hinge takes a smooth metal sleeve (3 mm OD × 2.1 mm ID × 12 mm), an M2 × 20 mm socket screw and an M2 nylon-insert locknut. The four outer Choc switches and their keycaps are bought parts.

The printer recording shows the battery cradle coming off the sheet on both the seven-piece run and its shorter first retry. The seven-piece run stopped at layer 156 of 165. Its two clips, cable clip, XIAO holder and keeper, and battery lid reached their planned heights. Their fit still needs checking on the cooled parts. The [revised battery-only plate](exports/print-recovery/README.md) widens the six outside pads and supports the tray floor across its width. It takes the same sliding lid.

The original [editable seven-piece plate](exports/print-accessories/Clips-and-holders.3mf) and [file sent to the printer](exports/print-accessories/Magic-Wand-R52-Clips-and-Holders-print-only.3mf) preserve that run for comparison. The A1 mini slice uses a 0.4 mm nozzle and PETG. The seven functional pieces have at least 10.36 mm between their print paths. [Toolpath and heater checks](exports/print-accessories/separation-and-machine.json) · [Sliding lid openings](exports/print-accessories/lid-openings.json)

The [editable key-carrier and paddle plate](exports/print-mechanisms/layout.3mf) and its [checked printer file](exports/print-mechanisms/Magic-Wand-R52-Key-Carrier-and-Paddle-print-only.3mf) use the same printer and filament. The [cleanup guide](mechanisms-print.md) identifies the outside supports and the two OP1 arms to keep. [Carrier cleanup map](exports/print-mechanisms/carrier-cleanup.png) · [Paddle cleanup map](exports/print-mechanisms/paddle-cleanup.png)

## Assembly

All rod references use the [full 500 mm carbon tube](../carbon-rod-holders/exports/carbon-stock-tube.stl). The complete assembly view shows both ends.

1. Leave the paddle and the four outer keys off. Plug the lead into the OP1 board and route its free end out of the carrier.
2. Lift the two rounded tabs about 1 mm. Start the board from the open side at the angle shown in the guide, settle it into the recess, then lower the pegs into the board holes.
3. Fit the OP1 switch. Slide the metal sleeve into the paddle, lower the paddle between the hinge cheeks, pass the axle screw through and fit the locknut. Check for free movement.
4. Fit the DFRobot touch board over its two posts and seat one printed clip on each. Fit the outer switches and caps last so the hinge hardware remains accessible during assembly.
5. Click at the centre and both lower corners. Each press should click once and spring back. Check that the board stays seated, its lead is free and all four key switches fit. These are physical checks on a cooled print.

Select **Keys → OP1 board clips** in the assembly viewer for installation and removal. **Keys → Axle assembly** shows how the sleeve, screw and locknut fit. [Assembly guide data](exports/assembly-guide.json)

The [mechanical notes](mechanical-notes.md) give the clearances, the hardware references and the limits of the click model. [Mechanical fit checks](exports/mechanical-fit.json) · [Button alignment checks](exports/contact-misalignment.json)

## Editable sources

Use the repository's guarded geometry runner with the existing Wand CAD environment. Generate the two print meshes with `build52.py`, check them with `mechanical_checks52.py` and `contact52.py`, and regenerate the assembly guide with `guide52.py --register`. With the local assembly server running, `node verify_guide52.mjs` checks the viewer against the files it serves.

On the mechanisms plate, cut and withdraw the two-post spring frame before fitting the OP1 board. The frame crosses the open wire-loading approach. Remove the exterior props before testing key 2’s cap, which needs that space to travel. The wire passage through the carrier stays clear. [Measured clearance and removal instructions](mechanisms-print.md)
