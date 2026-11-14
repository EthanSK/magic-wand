# R39 holder repair candidate

This review candidate composes R38 and the unchanged R25 XIAO / R22 cable holder. It is not a physically accepted design or a cleared print file.

## Changed parts

- The touch bracket has 2 mm tall flexible arms, 1.5 mm curved root transitions, a broader root fan and a centre squeeze stop. Arm bending thickness stays 1.2 mm. The root fillet shortens the free bending span, so the revised estimate includes that stiffening; it is not a measured fatigue limit. The existing tab axis stays in place.
- Fixed hinge supports have another 0.8 mm above their bores. Their outer top remains flat; the hole itself is deliberately teardrop-shaped for rear-face-down printing.
- The front deck edge has a true 0.5 mm circular relief. The six rounded protective beams remain separate from the electrical contacts.
- The battery door is 1.3 mm shorter, with 1.9 mm side guides and a 0.55 mm catch tooth. Press the central tab away from the battery while inserting or removing it. Its sprung bar is free in the assembled position; it does not squeeze the cell.
- The door prints with its flat outside face on the bed and the catch facing up. This avoids a floating catch.

The Choc V1 seats remain 14.1 mm squares with 0.2 mm corner radii; a narrowed or drooping opening is not intentional. The larger outside shoulders are deliberately curved. Viewing left/right depends on the assembled view, not the build-plate axes.

## Assembly viewer

Run `assembly39.py` with the existing CAD dependencies, then `assembly39.py --register`. The shared viewer reads the generated guide. Keep prior versions selectable. R39 contains the Grove Touch Sensor / OP1 assembly, separate XIAO and battery retainers, all twelve cable entry/removal paths, a battery catch cutaway, a finger-rest underside view and the complete rod arrangement. DFRobot DFR0030 remains the separate R35 assembly; the two sensor boards do not share mounting holes.

`complete-assembly.json` is the source for the seven-part print list. The wide battery door and XIAO keeper are both included. Loose battery spacers remain excluded from routine batches, following the existing requirement.

## Verification and limits

The generated geometry report measures clearance, engagement and complete movement paths. Beam strain and force numbers are rough calculations, not measured PETG strength. The source is retained for comparison against the failed print; the exact revision of the broken physical arm was not confirmed.

Use `plate39.py OUTPUT_DIRECTORY` to prepare a new plate. It keeps the R37 temperature recipe at 245°C nozzle / 60°C bed, first-three-layer gentle startup, timelapse and normal plate levelling. Key/bracket outer walls are capped at 40 mm/s and inner walls at 65 mm/s, with 1000/1500 mm/s² acceleration; the bracket has four walls and solid infill. Wall-crossing avoidance is enabled; existing wipe and cooling remain. Unchanged parts retain their recipe. These changes address risks; they do not guarantee a good physical print.

Slice the finished plate and run `audit39.py ARCHIVE SCRATCH REPORT`. Temporary supports are retained for the carrier's real ledges and must be removed before assembly. Supports, bridge roofs, first-layer pad ties, clear switch/rod/cable passages and flexing arm roots need the actual deposited-path audit and independent printability review before printing.

Fine strings can come from nozzle residue, moisture, temperature and travel between parts. Wall-crossing avoidance and wiping reduce some strings; extra heat is not a blanket cure. See [Prusa's stringing guidance](https://help.prusa3d.com/article/stringing-and-oozing_1805). Dryness and the nozzle condition have not been newly verified for this candidate.

## Local review status

The model and its complete animations are available for review. The actual slice succeeded without warnings at 245/60 °C; the deposited-path audit remains a separate gate. Do not start this candidate until its current report passes. The earlier R37-family arm failed physically, and R39 has not yet been printed.
