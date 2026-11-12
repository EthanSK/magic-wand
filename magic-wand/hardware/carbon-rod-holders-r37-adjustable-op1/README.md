# R37 Grove touch with adjustable OP1 stop

R37 follows the [R36 Grove assembly](../carbon-rod-holders-r36-grove-touch/README.md).
The centred upper and lower Grove screws, single snap hinge, contact
surface, key heights, OP1 board and service routes carry forward. The
bracket adds one adjustable hard stop, and the left cable window has
a little more clearance for the longer press.

## Set the switch travel

The purchased Endgame Gear OP1 Universal Switch Set contains seven
different switch pairs. The preferred switch colour in the project notes
does not identify the installed part. Omron's included 60M reference
specifies an operating height of 6.7–7.1 mm above the switch base, with
at least 0.20 mm of additional travel available once it operates.
R36's fixed stop leaves the reference plunger at 6.92 mm, so it can
miss a late-clicking switch. Extending a fixed stop for that late unit
could use up the overtravel of an earlier unit.

R37 uses an **M2 × 4 mm socket-head cap screw** with a 3.8 mm wide, 2.0 mm
tall head and 1.5 mm hex socket. It enters the underside of the orange
bracket. Its head meets the fixed key deck. Set it for the actual switch
before fitting the Grove board. The two outer stops catch the paddle at
the end of its mechanical range. Set the screw for the installed switch
before using the paddle. A straight hex key path through the deck would
run through the rod, so adjust the screw with the bracket lifted off.

1. Fit the OP1 switch in its socket with the assembly unplugged.
2. Turn the stop screw in until the head just touches the boss face.
   Then back it out **2¼ turns**. This gives the shortest available press.
3. Snap in the empty orange bracket. Use light pressure and check the
   switch closes and reopens with a continuity meter across COM and NO.
   If it does not close, lift the bracket off and turn the screw in
   **⅛ turn**. Repeat until the contact closes before the screw reaches
   the deck. A single extra ⅛ turn can provide margin if needed.
4. Check the switch releases and the screw remains firm, then fit the
   Grove board. Confirm the press again and check that the Grove signal
   stays active during a hold and clears when the thumb lifts.

If the contact stays closed at rest, fails to close and reopen consistently,
or the stop screw turns freely, check the fit before using the paddle.
Check the screw setting again after the first session or any switch swap.

The modeled hard-stop adjustment sweeps approximately 6.54–7.29 mm
above the reference switch base. Each ⅛ turn changes the plunger travel
by less than 0.05 mm in the model. This covers the published Omron
operating-position range on the modeled seat. Actual switch closing
height, print tolerances, retention and cable flex remain bench checks.

[Endgame Gear kit](https://endgamegear.com/products/op1-universal-switch-set) ·
[Omron D2FC mechanical drawing](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/5389/D2FC_Datasheet_EN.pdf) ·
[Socket-head screw reference](https://www.bossard.com/global-en/eshop/screws-and-bolts-with-internal-drive/hex-socket-head-cap-screws-fully-threaded/p/610/)

## Print files

- [Print-only A1 mini project](exports/R37-Adjustable-OP1-print-only.3mf)
- [Editable Bambu plate](exports/R37-Complete-A1-mini-PETG-layout.3mf)
- [Original audit](exports/audit.json) and [reopened audit](exports/reopened-audit.json)
- [Assembly animation](../carbon-rod-holders/assembly/?version=r37&component=keys)

The eight-part plate estimates 1 h 48 min and 17.87 g of Flashforge HS
PETG Metallic. The checked profile uses a 250 °C nozzle and 60 °C
textured plate. Remove the local OP1 connector support and the labelled
tear-off pads before assembly. Both matching holder keepers are included.

## Regenerate and check

Run `assembly37.py`, then `plate37.py <output-directory>`.
Run `audit37.py <sliced-archive> <output-directory> <report>` on the
original and the reopened slice. Register the viewer with
`assembly37.py --register` once both pass.
