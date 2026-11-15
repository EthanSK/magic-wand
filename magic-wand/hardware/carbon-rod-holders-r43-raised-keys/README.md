# R43 — raised outer keys

The four outer Choc seats rise 1.72 mm. Their nominal released keycap tops
are 21.64 mm above the rod centre, matching the DFRobot touch top at 21.6416 mm.
The two-key row remains the top and the three-key row the bottom. The OP1,
rod, touch bracket, hinge and stops keep their R42 positions.

## Why the OP1 stays at this height

The gold cylinders in the underside view are the OP1 socket barrels. Their
closest nominal rod gap is 0.90 mm. The white harness plug beside the rod
has only 0.3135 mm. Lowering that whole assembly by 0.15 mm leaves about
0.198 mm at the plug; lowering it by 0.30 mm leaves about 0.089 mm.
These are reference-envelope CAD gaps, not measurements of the physical kit.

R42 already lowered the DFRobot seat by 0.95 mm. R43 aligns the outer keys
to that touch surface by raising their seats, with no extra centre mechanism.

## Sources and assembly

- `holder43.py` composes R42's fixed mechanism with connected outer seat platforms.
- The complete Choc socket, wiring, insertion and cap-travel spaces move with their keys.
- The mounting collars retain the original bought Choc interface. Additional
  underside manufacturing cutters preserve each whole nominal socket envelope.
- `assembly43.py` exports the solids and derives every animation frame from
  the existing assembly recipe. Choc switches and sockets move together.
- `complete-assembly.json` retains all nine assembly parts. Other holders are unchanged.
- `plate43.py` preserves the checked A1 mini external-spool PETG recipe,
  native supports, rod/hinge exclusions, cuttable pads and Smooth timelapse tower.
- `carrier_checks43.py` checks the new key routes and full seat-to-frame bonds
  against the trial's own deposited plastic, composing unchanged R42 probes.
- `single43.py` filters the build list to **Key_Carrier only**, slices it,
  audits its own paths, reopens and re-slices once, then audits that archive too.

Run CAD/export generation and slicing through the repository's
`.agents/skills/printability-audit/scripts/geometry_budget.py`, using disposable
scratch. `assembly43.py` writes exports; `single43.py OUTPUT RETAINED` requires
fresh output/retained directories. Neither sends a print command.

## Trial boundary

The main carrier alone is the intended next physical trial. Its supports,
adhesion pads and timelapse tower are necessary helpers, not extra functional
wand components. The touch bracket and post clips retain their separate R42
print evidence; they are present in the complete assembly viewer, not this job.
The stated flush alignment needs the matching **R42/R43 lower-seat touch
bracket**. An older R41 bracket holds the touch board about 0.95 mm higher;
do not treat a trial with that older bracket as a test of the displayed alignment.

Digital checks cannot establish physical fit, solder clearance, cleanup,
PETG strength, fatigue or comfort. Keep the printer stopped until the user
confirms the failed plate and nozzle are clear, the plate is seated, and
hands are away. See `REVIEW.md` for the final checked artifact and findings.

## Checked single-holder file

`exports/key-holder-only/R43-Key-Holder-Only-print-only.3mf` is the selected
main-carrier-only trial. The initial and reopened archives both passed their
own complete path audits. The selected file contains the reopened G-code
unchanged. Its estimate is 7324 seconds and 17.03 g including supports and
the Smooth-timelapse tower, using the existing 245 C / 60 C PETG recipe.
The complete nine-part assembly viewer remains available independently.

The CAD key_2 bond-volume diagnostic does not subtract the final small
underside relief and is an upper bound, overstated by at most about 1 mm3.
The print audit intersects every bond witness with the actual final solid;
its measured minimum printed fraction for that bond is 0.9651. Use those
actual deposited sections, not the nominal CAD volume, for this trial.
