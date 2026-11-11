# R26 DFRobot centre click

This first-fit revision uses the DFRobot DFR0030 Gravity Digital Capacitive
Touch Sensor V2 above the OP1 mechanical switch. The four outer switches
are Choc V1. The two lower Choc centres move outward by 2.8 mm each. The
upper centres stay 18.7 mm apart and 17.8 mm behind the lower row. The
published DFR0030 outline is 22 × 30 mm. Its edge thickness, cable housing
and the stock OP1 board use estimated fit envelopes. The OP1 board
slides in on edge rails and is held by a removable latch, so its mounting
holes do not set the fit. See the [OP1 clearance assumptions](../carbon-rod-holders-r23-hybrid-centre/parameters.json).

[Watch the assembly](../carbon-rod-holders/assembly/?version=r26&component=keys).
Choose **Fit Choc switches and caps** to see the four Choc sockets and
switches go in. The **Component** menu includes the XIAO, battery, cable
clip and the disposable timelapse wipe tower.

## Print set

[Open the sliced A1 mini PETG plate](exports/R26-DFRobot-OP1-Latch-A1-mini-PETG.gcode.3mf)
or [open the editable Studio layout](exports/R26-DFRobot-OP1-Latch-A1-mini-PETG-layout.3mf).
Bambu Studio estimates **1 h 22 min and 12.0 g** including the wipe tower.
The plate uses a 0.4 mm nozzle, textured PEI, and external PETG at
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
- **OP1 board latch**. The centre blade stops the PCB moving forward. The
  two arms hook below the carrier ears and sit in guides that take the
  forward load. The plug and lead pass below the blade.

For an upgrade from the first R26 plate, print the revised key carrier and
OP1 board latch. The DFRobot paddle and front keeper fit this carrier.

Use the existing [R25 XIAO holder and lift-release keeper](../carbon-rod-holders-r25-keeper-release/),
the [R22 battery body and the door that fits](../carbon-rod-holders-r22-integrated-guard/),
and the 7 mm-bore cable clip from the R22 or R23 plate. The clip was
designed for a bundle equivalent to twelve 1.5 mm wires. Use a shared
return where the wiring allows it, or check the finished bundle against
the actual clip. The optional patterned battery spacer has its own
[R24 file](../carbon-rod-holders-r24-patterned-spacer/).

## Assembly

1. Push the OP1 switch into its socket board. Slide the assembly into the
   carrier from the tip, with the plug facing forward. Spread the latch
   arms, lower them into the carrier slots, then release both arms. Solder
   the four Choc sockets before seating them from underneath.
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
5. To remove the OP1 board, lift off the paddle, spread the two latch arms
   and lift the latch out of its slots. Slide the OP1 board out by the tip.

The Gravity sensor needs 3.3 V, ground and a separate digital input on the
XIAO. Use the sensor's S, + and − markings. The OP1 switch is a passive
contact wired separately. This print set makes no firmware changes.

## Verification

- [CAD fit](exports/geometry-checks.json) checks the DFR0030 and OP1 board
  insertion, both retainers, snap-in/removal motion, click travel and wire
  route. It checks that the OP1 latch stops the board moving forward and
  that the latch itself cannot lift out without spreading its arms.
- [Bead check](exports/slice-clearances.json) checks all four parts, the
  carrier's tear-off ties, four Choc socket roofs, and every opening. Snip
  off the four carrier pads and peel the two brims. The flat OP1 latch
  prints directly on the plate. The paddle has a small exterior tree
  support clear of its slide and pin paths.
- [Reopen check](exports/roundtrip-checks.json) verifies settings and re-runs
  the bead checks on the regenerated toolpaths.

The first print checks the real board fit, free OP1 click and release,
PETG hinge flex, and the lead's slack with the rest of the harness fitted.
The lower runners block the sampled straight-up fingertip paths. The upper
socket area still has exposed terminals for wiring and service.

## Removable copper insert preview

[Watch the compact insert assemble and click](../carbon-rod-holders/assembly/?version=r26&component=keys&keyView=copper).
The 18 × 17.3 mm cap keeps the stock OP1 click. Stick 0.07 mm copper tape
to the insert and slide it in from the hinge end while the cap is off.
The rails support the insert beneath the 1 mm insulating cover. Once
the cap snaps on, the fixed hinge stops the insert's tab from withdrawing.

The lead goes over the hinge between the two upper keys. Unplug it at
the fixed connection, lift off the cap, and slide the insert out for
service. The connection shown is illustrative. The touch circuit can
sit elsewhere on the wand, so its board size does not set the cap size.

The nominal foil-to-cover gap is 0.10 mm. The preview leaves out a pressure
spring. Fit, foil adhesion, and detection through the actual cover still
need a physical test. The preview meshes are separate from the four-part
DFRobot print plate.

[Model source](copper26.py) · [Fit checks](exports/copper-insert-checks.json)

[DFRobot dimensions and pin labels](https://wiki.dfrobot.com/dfr0030/) ·
[Endgame Gear OP1 stock switch boards](https://www.endgamegear.de/en-de/op1-universal-switch-set-2x-switch-pcbs-14-switches/GAMO-1112.html)
