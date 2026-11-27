# R74 key holder

[Open the key holder](../carbon-rod-holders/assembly/?version=r74&component=keys) · [See how the battery comes out](../carbon-rod-holders/assembly/?version=r74&component=battery&view=battery_removal)

The battery can slide right through the holder. It goes between the two rails from the rear, with its leads outside. The side spring grips the installed pouch. To remove it, disconnect it and slide it either way, pushing on the wrapped end. The guide uses the nominal 27 × 11.8 × 3.9 mm Micron 72217 pack. Its actual wrap, leads and solder joints still need a fitted trial.

The battery-side finger guard has two rounded branches and three roots joined to the carrier. The outer root starts at the same place on the rim as its counterpart. It turns under the prewired black socket, which slides in from the outside. Copying the other side’s slope directly would put the guard inside the seated socket. The inner branch meets the deck beside the battery lane. Each branch ends inside the holder.

Four unused cutouts are closed. The larger holes under each key receive the switch’s moulded locating posts and the round bosses on the black socket. The metal contacts enter the socket through its bosses. The DFRobot paddle, its click travel and the rest of the nine-piece kit use the R73 parts.

## Verification

- [Editable carrier](design74.py) and [exported carrier mesh](exports/Key_Carrier-assembly.stl).
- [Export measurements](exports/fit74.json). The nominal battery swept through about 111 mm³ of rigid R73 material. In R74 the measured overlap is below 0.001 mm³, with the side spring’s contact preserved. All 336 key-fitting poses and the seven OP1 routes clear the carrier. The complete rod and fitted centre assembly also clear the battery path.
- [Guard and plate measurements](exports/design74.json). The guard leaves at least 0.18 mm to the checked left-key fitting paths. The opposite guard stays in its previous position. Grip, printed strength and comfort require a physical trial.
- [Saved plate and independent re-slice](exports/print-mechanisms/review.json). The nine-piece A1 mini PETG plate passed all 80 groups of clearance checks in both slices. A local wall setting at the lower-left socket removes a tiny loop that would have started in midair. The checks found no floating starts or generated support. A [5.21 mm bridge on the inner guard](exports/print-mechanisms/guard-review.json) bonds at both ends. Its printed finish still needs inspection.
- [Editable plate](exports/print-mechanisms/layout.3mf) and [print-only file](exports/print-mechanisms/R74-Complete-Key-Holder-A1-mini-PETG-print-only.3mf).
