# R40 crosswise OP1 fit trial

R40 turns the OP1 mouse-switch PCB through 90 degrees across the rod. It composes R39's repaired hinge, rounded finger edge and battery catch. Earlier revisions remain available in the assembly menu.

## Geometry and bought parts

- The OP1 PCB's 30 mm direction runs across the rod; its 10 mm direction runs along it. The board underside is 8.8 mm above the rod centre, 1.3 mm lower than R39. Its three socket barrels, white connector, plug, mounting screws and switch turn with it.
- The two upper Choc keys move outwards by 3.2 mm each. The lower three controls retain their alignment. Choc seats, rod clips and hinge-axis height stay unchanged. The released touch surface is about 0.52 mm higher because the shorter click lever needs a different rest angle.
- A new continuous OP1 lead route starts at the real plug outlet. Connect it from underneath before refitting the upper keycaps. The lead envelope is provisional; actual cable diameter, stiffness and solder still need a fit trial.
- The adjustable stop remains an M2 × 4 screw. Start with a light setting and verify that the actual switch clicks and releases before the hard stops touch. The OP1 board's own mounting screws are a different size, M1.6 × 4.

The OP1 board model comes from the Endgame Gear OP1 Universal Switch Set, EGG-SP-U1 / PER-EGG-01645. PCB and connector sizes are photo-derived; no official dimensioned PCB drawing was available. The touch board in this assembly is the Seeed Grove Touch Sensor 101020037, Pi Hut 103326. DFRobot DFR0030 remains a separate R35 option with different mounting holes.

## Complete print and assembly

`complete-assembly.json` owns the seven-part build list:

| Group | Printed parts | Source |
| --- | --- | --- |
| Keys | Key_Carrier, Grove_Touch_Bracket | R40 |
| XIAO | XIAO_Rod_Holder, XIAO_Near_Keeper | Unchanged R25 |
| Battery | Battery_Holder, Battery_End_Door | Unchanged body and R39 lower catch |
| Cables | Cable_Clip_12_Wire | Unchanged R22 |

Both retainers are included. Loose flat battery spacers are excluded. The generated guide contains key installation, hinge squeeze/drop/release, stopped click and return, all twelve cable entry/removal routes, battery release, the XIAO keeper and the complete rod arrangement. It opens paused at the first step.

## Print preparation

`plate40.py` retains the red Flashforge HS PETG Metallic recipe: 245°C nozzle, 60°C bed, gentle first three layers, 40 mm/s outer and 65 mm/s inner walls on the carrier/bracket, and a four-wall solid bracket. A short web reinforces the shared left finger-support junction below the key seat; its actual printed section is audited. Smooth timelapse and its wipe tower remain enabled. Normal bed levelling remains part of startup. The tower is waste for nozzle wiping during timelapse moves, not a wand component.

Remove the labelled bed-pad ties and generated supports before fitting electronics. Supports enter the board/rod passages and are deliberately not treated as clear until cleanup. Break them into small pieces through the empty board opening or outwards beside the left guard; do not lever against a thin arm. Check screw holes and arm movement after cleanup.

The tested Python 3.14 dependencies are in `requirements.txt`; install them in a separate Python environment. Bambu Studio and its official A1 mini profiles are also needed for slicing. Run `assembly40.py` to regenerate the meshes, geometry report and guide. `assembly40.py --register` selects the revision in the shared catalog. Prepare a fresh directory with `plate40.py OUTPUT`, slice it with the established Bambu CLI workflow, then run `audit40.py ARCHIVE SCRATCH REPORT` against that preparation's staged exports. Heavy jobs run serially through the repository's geometry runner. Reopen and re-slice the portable archive once after geometry and settings settle.

## Verification boundary

The selected fit-trial package is `exports/print-trial/R40-Complete-A1-mini-PETG-reopened.gcode.3mf`. Its own current deposited-path audit passed for all seven parts. Use `exports/readiness.json` for its exact hash and the independent review disposition. The initial archive and reports are explicitly labelled `superseded`; their paths differ and their older audit does not cover the final reinforcement interfaces.

The retained editable layout is a preparation reference. The fresh layout generated during the reopen check was disposable and was not retained; its reported hash therefore differs. The reopened, self-contained package retains the actual audited geometry and effective settings. Re-slice and audit again after any edit.

The independent review permits an experimental fit trial, with the local unsupported strips, narrow key-clip wall and real hardware margins explicitly retained as trial risks in `REVIEW.md`. This is not a production-ready or guaranteed-success claim.

Physical fit, support removal, switch adjustment, PETG strength, fatigue and finger comfort remain unverified. These checks cannot guarantee a successful print. No physical print is started by the generators or auditors.
