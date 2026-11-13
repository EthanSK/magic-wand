# R37 Grove touch with adjustable OP1 stop

R37 follows the [R36 Grove assembly](../carbon-rod-holders-r36-grove-touch/README.md).
The centred upper and lower Grove screws, single snap hinge, contact
surface, key heights, OP1 board and service routes carry forward. The
bracket adds one adjustable hard stop, and the left cable window has
a little more clearance for the longer press.

The Grove seat sits 0.9 mm lower than the R35 DFRobot seat. The key
carrier keeps the R35 height to preserve room for the rod clip to flex
during installation and for the underside guard ribs under finger
load. A 0.5 mm drop of the guard geometry clears the rod at rest in CAD.
That static check leaves clip flex, print tolerances and loaded
clearance untested. A 1 mm drop already intersects the rod in CAD.

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

The [print-only receipt](exports/print-only.json) links the download,
its exact G-code bytes, and the original audited archive. Print-only
packaging removes the editable mesh data and references, so its outer
archive checksum differs. The editable plate matches the input
checksum in the [slice record](exports/print-checks.json).

The eight-part plate estimates 1 h 48 min and 17.87 g of Flashforge HS
PETG Metallic. The checked profile uses a 250 °C nozzle and 60 °C
textured plate. Remove the local OP1 connector support and the labelled
tear-off pads before assembly. Both matching holder keepers are included.

## Regenerate and check

Run `assembly37.py`, then `plate37.py <output-directory>`.
Run `audit37.py <sliced-archive> <output-directory> <report>` on the
original and the reopened slice. Register the viewer with
`assembly37.py --register` once both pass.

## Solid-pad retry

This separate A1 mini plate keeps all eight R37 parts and their matching
keepers. The 0.4 mm solid pads increase bed contact while keeping the
original narrow cut points. Snip each tie with flush cutters while
supporting the part. The flat keeper and door use 6 mm outer brims and
the patterned battery spacer uses a 5 mm outer brim. Peel those from
the outside after the plate cools. The cutouts in the spacer itself
remain open.

| Part | Previous pad area | Solid pad area |
| --- | ---: | ---: |
| Key carrier | 383 mm² | 1,092 mm² |
| Grove touch bracket | 118 mm² | 350 mm² |
| XIAO holder | 303 mm² | 631 mm² |
| Battery holder | 363 mm² | 886 mm² |
| Cable clip | 20 mm² | 70 mm² |

Layer 105 at 21.0 mm adds a 45 mm/s and 1,000 mm/s² cap to ordinary
model paths through Studio's height slowdown. The emitted G-code also
requests Y-axis limits of 120 mm/s and 1,000 mm/s², including travel to
the wipe tower and camera position. The G-code restores standard
limits after final parking. If a run is interrupted above the
transition, turn the printer off and on before running a standalone
calibration, since its normal ending may have been skipped. Leave the
printer in Standard speed mode for this trial.

The first-layer profile and 250/60 °C PETG temperatures carry forward.
Studio estimates 2 h 26 min and 18.93 g. Actual time may be longer
because the added Y limit is applied by the printer. The original and
reopened slices passed the connection, opening and support checks.
Physical adhesion, pad removal and the firmware's motion response
remain to be observed.

- [Print-only retry](exports/solid-pads/R37-Solid-Pads-A1-mini-PETG-print-only.3mf)
- [Editable retry plate](exports/solid-pads/R37-Solid-Pads-A1-mini-PETG-layout.3mf)
- [Exact print receipt](exports/solid-pads/print-only.json)
- [Motion audit](exports/solid-pads/motion-audit.json)
- [Original slice audit](exports/solid-pads/audit.json) and [reopened slice audit](exports/solid-pads/reopened-audit.json)

Run `solid_pad_plate.py <output-directory>` to reproduce the layout
from the checked R37 plate.

## Gentle-start retry

The solid-pad trial was stopped at layer 9 after raised and rough areas
developed in the first few layers. The recording cannot establish whether
surface contamination, nozzle snagging, cooling or inconsistent feed
started the failure. Both temperatures matched their targets at 250/60 °C.

`gentle_start_plate.py` keeps the eight parts, wide solid pads, narrow ties,
brims, functional openings and removable OP1 support. It limits ordinary
walls and fill to 40–60 mm/s, travel to 120 mm/s and print acceleration to
1,000 mm/s² from the early layers. The first-layer extrusion stays at
20/30 mm/s. The bed-axis limit starts on layer 1, and the 45 mm/s height
limit remains above 21 mm. This avoids the previous layer-2 jump to about
106 mm/s walls and 5,000–10,000 mm/s² acceleration.

The part fan stays off for three layers, then uses 50–60% cooling with
60% overhang cooling. The battery door bridges on layer five, so extending
the fan-off period through that bridge would introduce a sagging risk.
Filament-specific retraction is
1 mm at the existing 30 mm/s. The project uses the Generic PETG A1 mini
preset with these explicit filament overrides. The 250/60 °C recipe is retained within
the [filament manufacturer's range](https://www.flashforge.com/products/hs-petg?variant=43140414636110).
Fine stray threads can come from ooze, moisture, nozzle residue or
retraction. Their presence alone does not identify the cause of detachment.

Before the next physical trial, verify a clean, dry, correctly seated
textured plate, a clean nozzle, sufficient filament and free spool/tube
movement. The drying history and feed condition remain unverified.
Observe the actual first layer and stop if the lines fail to stick or curl
upward. Sliced checks cannot prove adhesion or finished-part strength.
After a cancellation, the added bed-motion limit can remain active. A new
sliced print restores its startup limits. Power-cycle before a standalone
calibration or manual movement following an interrupted gentle-start run.

- [Gentle-start print-only file](exports/gentle-start/R37-Gentle-Start-A1-mini-PETG-print-only.3mf)
- [Gentle-start editable layout](exports/gentle-start/R37-Gentle-Start-A1-mini-PETG-layout.3mf)
- [Gentle-start slice checks](exports/gentle-start/audit.json)
- [Reopened slice checks](exports/gentle-start/reopened-audit.json)
- [Early motion and cooling checks](exports/gentle-start/early-motion.json)
- [Gentle-start print receipt](exports/gentle-start/print-only.json)

Studio estimates about 3 h 16 min and 18.93 g. Run
`gentle_start_plate.py <new-output-directory>` to regenerate the layout.

## Standard-motion PETG retry

`standard_retry_plate.py <new-output-directory>` retains the solid pads,
narrow ties, local OP1 support and seven functional parts. It omits the
routine loose battery spacer. The XIAO keeper and battery end door remain
included. Holder geometry is unchanged.

The first layer uses 20/30 mm/s extrusion and 500 mm/s² acceleration.
Layers two and three cap printed paths at 60 mm/s and both moving axes
at 1,000 mm/s². Layer four restores the machine's Standard motion limits.
The previous 21 mm height slowdown is removed. The finished G-code is
checked for both transitions, including support and wipe-tower paths.

This trial uses 245 °C nozzle and 60 °C bed, 1.2 mm retraction at 35 mm/s,
an 8 mm³/s flow limit and 50–90% part cooling after three layers.
Overhang cooling is 100%. These settings are a stringing trial for
Flashforge HS PETG Metallic. Moisture, feed resistance and the physical
cause of the previous upper-layer failure remain unverified.

After slicing and running `audit37.py`, package the checked archive with
`standard_retry_plate.py <output-directory> --package <sliced-archive>`.
The print-only package preserves its G-code bytes. Opening an editable
project in Studio can reset the wipe tower into the key carrier, so any
editable re-slice needs another placement and toolpath check.

- [Standard-motion print-only file](exports/standard-retry/R37-Standard-PETG-retry-print-only.3mf)
- [Editable source plate](exports/standard-retry/R37-Standard-PETG-retry-layout.3mf)
- [Slice checks](exports/standard-retry/audit.json)
- [First-three-layer motion checks](exports/standard-retry/early-motion.json)
- [Exact print receipt](exports/standard-retry/print-only.json)

The estimate is 1 h 58 min and 18.62 g. Sliced clearances and connected
paths are checked. Adhesion, finished strength and component fit still
depend on the physical trial.
