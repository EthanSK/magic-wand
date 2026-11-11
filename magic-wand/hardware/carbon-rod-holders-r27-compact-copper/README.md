# R27 compact copper keys

[Watch the assembly](../carbon-rod-holders/assembly/?version=r27&component=keys&keyView=copper).

The three-key row is at the bottom. The outer two keys move inward by
2.8 mm each from the wide R26 DFRobot layout, back to 18.7 mm from the
centreline. The same removable copper cap moves 3.55 mm towards the
two-key row. The two upper keys move back by 3.55 mm and outward by 3.7 mm
each to clear the switch board's loading path.

The carrier has a straight bottom edge across the lower row, with
rounded corners. Turn the OP1 board around so the short end is 0.75 mm
inside that edge and the plug points towards the two-key row. The board,
sockets and lead slide in from that end. A keeper held by a short piece
of 1.75 mm filament stops the board sliding back out. Push the switch
into the board from above once the keeper is pinned. To service the
board, lift the switch out before sliding the board back.

The foil carrier, cap and lead use the same geometry as
[R26's copper option](../carbon-rod-holders-r26-dfrobot-centre/#removable-copper-insert-preview).
The [geometry checks](exports/geometry-checks.json) cover the bottom
edge, OP1 board and switch insertion, keeper and pin, and full click
and release. The OP1 hardware dimensions are fit estimates. This is a
CAD preview. The R27 parts still need slicing and a physical fit and
touch test.

Regenerate the preview with `python3 assembly27.py`.
