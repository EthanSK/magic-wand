# R26 DFRobot centre click

This first-fit revision uses the DFRobot DFR0030 Gravity Digital Capacitive
Touch Sensor V2 above the OP1 mechanical switch. The four outer switches
are Choc V1. The two lower Choc centres move outward by 2.8 mm each. The
upper centres stay 18.7 mm apart and 17.8 mm behind the lower row. The
published DFR0030 outline is 22 × 30 mm. Its edge thickness, cable housing
and the stock OP1 board use estimated fit envelopes.

[Watch the assembly](../carbon-rod-holders/assembly/?version=r26&component=keys).
Choose **Fit Choc switches and caps** to see the four Choc sockets and
switches go in. The **Component** menu includes the XIAO, battery, cable
clip and the disposable timelapse wipe tower.

## Print set

[Open the sliced A1 mini PETG plate](exports/R26-DFRobot-A1-mini-PETG.gcode.3mf)
or [open the editable Studio layout](exports/R26-DFRobot-A1-mini-PETG-layout.3mf).
Bambu Studio estimates **1 h 19 min and 11.2 g total**, including the wipe
tower. The plate uses a 0.4 mm nozzle, textured PEI, and external PETG at
255 °C nozzle and 70 °C bed for the first printed layer. Keep bed levelling
and timelapse enabled when sending it.

- **Key carrier**. Two integral spring arms hold the hinge. Two short posts
  limit how far the paddle can depress the OP1 plunger.
- **DFRobot paddle**. The two side rails grip the edges of the board, leaving
  the gold touch surface exposed.
- **DFRobot front keeper**. A roughly 16 mm piece of 1.75 mm filament through
  the paddle and keeper holes holds the board in. Remove the pin to swap the
  board. Slide the rod through the two carrier rings before mounting the
  fully wired wand.

Use the existing [R25 XIAO holder and lift-release keeper](../carbon-rod-holders-r25-keeper-release/),
the [R22 battery body and the door that fits](../carbon-rod-holders-r22-integrated-guard/),
and the 7 mm-bore cable clip from the R22 or R23 plate. The clip was
designed for a bundle equivalent to twelve 1.5 mm wires. Use a shared
return where the wiring allows it, or check the finished bundle against
the actual clip. The optional patterned battery spacer has its own
[R24 file](../carbon-rod-holders-r24-patterned-spacer/).

## Assembly

1. Push the OP1 switch into its socket board. Slide the assembly into the
   carrier from the tip, with the plug facing forward. A small removable
   strip of tape across the board edges keeps it seated. Fit the four
   Choc sockets from underneath along their shown routes.
2. Slide the DFR0030 into the paddle with gold face up and the connector
   facing the tip. Put the front keeper in and push the filament pin across.
3. Pinch the two hinge arms, lower the paddle until the pin and hole centres
   line up, then release the arms. Plug in the Gravity lead and leave a
   loose loop at the tip so the lead can move as the paddle clicks.
4. Press the centre of the gold face gently with power disconnected. Check
   that it clicks, releases and lands on the two stops before the switch
   bottoms out. Then clip the lead into the harness. The stops set 0.48 mm
   of travel at the nominal OP1 plunger. Squeeze the same arms to lift the
   paddle off for service.

The Gravity sensor needs 3.3 V, ground and a separate digital input on the
XIAO. Use the sensor's S, + and − markings. The OP1 switch is a passive
contact wired separately. This print set makes no firmware changes.

## Verification

- [CAD fit](exports/geometry-checks.json) checks the DFR0030 and OP1 board
  insertion, keeper, snap-in/removal motion, click travel and wire route.
- [Bead check](exports/slice-clearances.json) checks all three parts, the
  carrier's tear-off ties, four Choc socket roofs, and every opening. Snip
  off the four carrier pads and peel the two brims. The paddle has a small
  exterior tree support clear of its slide and pin paths.
- [Reopen check](exports/roundtrip-checks.json) verifies settings and re-runs
  the bead checks on the regenerated toolpaths.

The first print checks the real board fit, free OP1 click and release,
PETG hinge flex, and the lead's slack with the rest of the harness fitted.
The lower runners block the sampled straight-up fingertip paths. The upper
socket area still has exposed terminals for wiring and service.

[DFRobot dimensions and pin labels](https://wiki.dfrobot.com/dfr0030/) ·
[Endgame Gear OP1 stock switch boards](https://www.endgamegear.co.uk/en-gb/accessories/op1-universal-switch-pack)
