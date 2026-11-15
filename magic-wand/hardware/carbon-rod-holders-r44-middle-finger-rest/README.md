# R44 — joined middle finger rest

The four outer Choc seats are 0.30 mm lower than R43, at R42 + 1.42 mm.
Their reference keycap tops are Z21.34 mm; the released DFRobot touch top
stays Z21.6416 mm. Two keys are the top row and three are the bottom row.
The rod, OP1 assembly, touch board, hinge and stops keep their R42 positions.

## Finger contact

Rounded spines join the three existing finger-contact rows on each side.
A fourth middle branch joins the inner leg to the outer return on each
side, closing the large front contact gap without adding a panel. The
contact bars have 0.95 mm radius (1.90 mm diameter). A slightly thicker
sloping right riser joins usable central frame stock; the left socket and
its wiring route occupy the corresponding left landing. All additions are
cut by the complete bought-part, socket, solder, hinge and wiring spaces.

The CAD sphere probe is only a comparison of gaps. It does not establish
physical comfort or strength. Whole new members and their pre-union bonds
remain in the actual deposited-material audit; checking just their union
would hide weak attachments.

## Scale and the diagonal OP1

`reference44.py` compares the exported guide STLs in their seated animation
poses with the CAD envelopes, including their unit scales. The rod diameter
is 8 mm. The three OP1 metal socket barrels have minimum rod gaps of about
1.163, 0.900 and 0.902 mm; the 0.90 mm figure is the closest point, not a
uniform separation beneath all three barrels.

The fixed white connector housing has about 2.565 mm minimum clearance.
The lower fitted harness plug has only about 0.3135 mm at its inner corner,
even with the board yawed -25 degrees. Most of that plug is beside the rod,
but its inner corner still approaches the curved rod shoulder. The
`exports/reference-clearance.png` end-on projection shows that distinction.

PCB/socket/connector sizes and mounted keycap height remain photo-derived
reference estimates, not measurements of the actual bought hardware. See
R32's hardware provenance. Matching R42-or-later lower-seat DFRobot parts
are needed for the displayed height relationship; an older R41 bracket
holds the touch board about 0.95 mm higher.

## Reproducible sources

- `holder44.py`: joined rests, adjusted key seats, final socket relief and full CAD checks.
- `assembly44.py`: printable exports and all nine parts in the complete assembly viewer.
- `reference44.py`: source/export scale comparison and rod-clearance diagram.
- `plate44.py`: established A1 mini external-spool PETG recipe, local native support enforcers, protected rod/hinge spaces, cuttable adhesion pads and Smooth timelapse tower.
- `carrier_checks44.py`: complete working routes and actual material at every changed load path.
- `single44.py`: the main Key_Carrier alone, initial slice, full audit, one reopened re-slice and its own full audit, then a package with byte-identical G-code.

Use the repository printability-audit geometry-budget wrapper and disposable
scratch for generation and slicing. Run `assembly44.py` to generate exports;
`assembly44.py --register` selects this version in the existing viewer.
`single44.py OUTPUT RETAINED` requires fresh output directories. These
sources never send or start a print.

The single-carrier process uses variable-width (Arachne) walls across the
whole part. The new member-shaped selectors retain solid fill locally;
all earlier root bonds remain required, with no relaxed coverage threshold.
This is a process-setting repair, not a change to bought-part dimensions.

## Physical trial boundary

Only the main key carrier is selected for the next physical trial. The
complete assembly viewer still contains the matching touch bracket, clips,
battery, XIAO holder, keepers and cable clip, without adding them to this job.
Native support, cuttable pads and the Smooth-timelapse tower are helpers.

Do not send, heat or start until Ethan confirms he is home and the failed
plate and nozzle are clear, the plate is seated and hands are away. Digital
checks do not guarantee physical fit, PETG bonding, support removal, snap
force, fatigue or comfort. See `REVIEW.md` for the selected archive and
completed review evidence.
