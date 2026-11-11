# R28 DFRobot touch board

[Watch the assembly](../carbon-rod-holders/assembly/?version=r28&component=keys).

The bought DFRobot DFR0030 V2 board (22 × 30 mm) is the centre key's touch
face. It sits in a tray on R27's OP1 click: the same rear-loading OP1 slot,
rear keeper, snap hinge, stops and 0.48 mm plunger travel. The three-key row
is at the bottom. The gold pad is at the bottom end and the Gravity plug at
the top end.

## Layout

- All four Choc centres are 21.1 mm from the centreline. The lower pair moves
  out 2.4 mm each from R27. The upper pair moves out 8.05 mm each and stays
  21.35 mm behind the lower row. The tray is 24.2 mm wide, leaving 0.7 mm
  beside each 16.6 mm reference cap.
- When released, the tray's front edge is at Y −8.75 mm, in line with the
  Choc cap fronts. Across the full press it stays at least 0.41 mm inside the
  flat bottom.
- At the hard stop the board is at Z 20.25–21.85 mm. Its released top is
  23.72 mm, against R27's 23.40 mm. The Gravity plug envelope reaches 28.0 mm.

## Board fit

The board slides in from the top under two side rails until it meets the
fixed end stop at the bottom edge. A 24 mm piece of 1.75 mm filament through
two rear ears holds it in. When released, that pin clears the upper keycap
tops by 0.44 mm. The rails allow 0.24 mm at each side and 0.2 mm above the
board. The floor is 0.85 mm below the board, with an open window under the
plug and over the hinge arms.

To service it, unplug the Gravity lead, push the pin out sideways and slide
the board out towards the top. The tray stays on the wand. Squeeze the hinge
arms through the floor window to lift the tray off.

## Checks

The [geometry checks](exports/geometry-checks.json) sample the full click
and release, snapping on the empty tray, the whole board slide, the pin
slide, the lead slack, the stop contacts and the bottom-edge alignment. All
overlaps are zero.

All six finger guard runners are present. The middle-left runner ends at
Y 12 before the moved upper-left socket. The outer-left runner runs at
X −28.3 around the outside of that socket.

These numbers are estimates: the board's 1.6 mm thickness, the Gravity
plug, the parts under the board, the OP1 parts and the Choc cap outline. The
SOURCE files are rear face down, like R26. They have not been sliced or
printed, and fit and touch response are untested.

Regenerate with `python3 assembly28.py` through the geometry budget runner.
