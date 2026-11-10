# R23 Centre Click

R23 gives the lower-middle mouse button a rounded hinged paddle over the stock
Endgame Gear OP1 socket board. The four surrounding Choc V1 positions and their
wiring routes come from R22. The board slides in from the front with the white
plug attached. The exposed end keeps the plug and cable bend accessible.

[Play the assembly guide](../carbon-rod-holders/assembly/?version=r23&component=centre).
The Component menu shows all three paddles, the four Choc keys, the XIAO
holder and keeper, both battery doors and the cable clip.

## Key Holder Guard

The six rounded runners beneath the keys now use 2.4 × 2.0 mm sections,
up from 1.6 × 1.4 mm on R22. They follow the same paths and leave an open
channel for the finger to reach the rod. The upper keys keep their existing
underside so the prewired sockets and wiring can still pass through.

## Fit the Centre Click

1. Seat the microswitch on the stock board and connect the white plug. Slide the
   assembly into the centre slot from the front. Use a removable strip of tape
   at the front to keep the board from backing out, leaving the plug accessible.
2. Fit the paddle between the two hinge sides. Slide about 22 mm of 1.75 mm
   filament through the holes. The paddle's two side stops transfer the force
   to the carrier at the end of the press.
3. Start with the shallow paddle during the unpowered fit trial. Press gently
   and check that the switch clicks, returns and opens the circuit on release.
   The three paddles set a nominal depression at the stop of 0.4, 0.6 and 0.8 mm.
   Use only a paddle that reaches its side stops before the switch itself
   bottoms out.
4. Use the [OP1 wiring guide](../xiao-wand-dashboard/README.md#op1-centre-click)
   to find the two contacts on the stock harness. COM goes to GND and NO goes
   to the existing D8 mouse input on the XIAO Sense.

The [manufacturer's EGG-SP-U1 page](https://endgamegear.com/products/op1-universal-switch-set)
identifies the socket-board kit. The board, connector and switch dimensions in
`parameters.json` are estimates from the vendor photos and the microswitch form
factor. The side rails assume a board near the stated width. The board's
hold-down, click travel, printed strength and comfort need a physical fit trial.

## Source and Checks

`holder23.py` exports the carrier, paddle variants and illustrative hardware,
then regenerates the assembly guide from those exports. `verify23.py` checks
the actual assembly meshes against the R22 key routes, rod, board insertion
and paddle motion. `project23.py --slice --support` builds the plate from the
checked meshes and six retained R22 parts. The two battery doors and XIAO keeper
are included. Optional flat spacers are omitted. The small timelapse wipe
tower and tear-off pads are print helpers.

The mesh and motion hashes are in `exports/manifest.json` and the assembly
recipe. `exports/slice-clearances.json` records the exact sliced openings,
rib coverage and first-layer checks.
