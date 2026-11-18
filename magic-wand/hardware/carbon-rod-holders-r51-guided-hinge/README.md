# R51 touchpad hinge and battery lid

The next prototype uses the changed key holder, the DFRobot touch-board bracket and the sliding battery lid. Reuse the existing XIAO holder and keeper, battery cradle, cable clip and the two DFRobot board clips.

## How the touchpad fits

The two-key row is at the top. The gold pad clicks at the three-key end. Fit the OP1 and route its wire, then fit the axle **before the outer switches and caps**. The outer keys block sideways access to the screw and locknut once installed.

1. Slide a smooth metal sleeve, 12 mm long with 3 mm outside diameter and 2.1 mm inside diameter, into the orange bracket.
2. Lower the reinforced bracket between the two fixed cheeks. Insert an M2 × 20 mm socket screw through both cheeks and the sleeve. Fit an M2 nylon-insert locknut. The sleeve takes the clamping load. Check that the bracket rotates freely and has no perceptible rattle.
3. Connect the DFRobot lead. Seat the board over the two posts and fit the two existing printed clips. Fit the four outer Choc switches and caps.
4. Press the middle and both lower corners of the copper pad. Each should click, return freely and feel steady. If it binds, check bore roundness and clearance before tightening anything further.

The bought OP1 button has a rounded top. The viewer shows an illustrative crown at the modelled peak height. The printed bracket has a small 1.1 × 0.6 mm flat contact face that presses the button. Its real contact point and click travel still need a physical check.

The metal hardware is additional to the printed parts. The triangular roots, fixed hinge cheeks and central bearing are permanent. The previous revision's thin outside guides and adjustable stop screw have been removed. The integral travel limits are part of the bracket.

## What was checked

- [Mechanical fit and click travel](exports/mechanical-fit.json) covers the bought-part envelopes and reference travel. Real click feel, finished bore dimensions and repeated-use durability need a physical test.
- [Unchanged parts](exports/reused-parts.json) compares the R48 native toolpaths with the successful wide-pad retry, checks the joints on those paths, and checks each retained solid for narrow necks. The cable clip reference mesh was cleaned of zero-area triangles. Its volume and real faces are identical.
- [Lid geometry](exports/lid-checks.json) and [native print paths](exports/lid-slice-checks.json) cover the new feather pattern, rails, latch, and twelve open windows across all four layers of the central sheet. The standalone lid slice is a window check.
- [Assembly guide](exports/assembly-guide.json) uses the same print meshes and checked click poses. The default **Keys** view fits the OP1, hinge, DFRobot board, four Choc switches and their caps. **Axle assembly** shows the sleeve, screw and locknut up close. **Complete rod assembly** starts with the bare rod, builds the holders and slides them into place. Double-click the orientation gizmo to restore the default view at the current step.

The generators in this directory use the existing Wand CAD dependencies. Generate the parts with `build51.py` and `lid51.py`, check them with `mechanical_checks51.py` and `audit_reuse51.py`, then run `guide51.py --register`. Use the repository's guarded geometry runner for CAD generation and mechanical checks. Verify the guide over the running viewer with `node verify_viewer51.mjs`.

## Three-part A1 mini trial

The [editable plate](exports/print/trial.3mf) contains the key holder, DFRobot bracket and battery lid. The [sliced print file](exports/print/Magic-Wand-R51-Changed-Parts-print-only.3mf) is for the 0.4 mm nozzle and red PETG. Bambu estimates 18.93 g and 2 hours 26 minutes. The [heater check](exports/print/machine-check.json) confirms 245 °C nozzle and 60 °C bed when printing the first part. The [packaging check](exports/print/print-only.json) verifies that the file preserves the checked toolpaths.

Nine disposable supports sit outside the key holder and reach underneath the finger rest. The [toolpath check](exports/print/joined-audit.json) found no support beads in the OP1 lead exit, finger-contact surfaces or axle opening. The [battery lid check](exports/print/combined-lid-paths.json) found all twelve feather-shaped windows open through all four layers of the centre panel.

Use the [two-sided removal picture](exports/print-trial/printed-supports.png) to distinguish the printed part (red), removable support (teal) and bed brim (tan). Remove the brim first. Each outside prop has a clear outward pull in the model. Two small areas by the left outer switch may still need trimming.

The thinnest sliced opening for the 3 mm sleeve is close to its diameter. Try the smooth sleeve by hand before assembling the hinge. Its printed fit, support removal and the side-to-side feel of an actual click need a physical trial.

The [removal checks](exports/print-trial/support-removal-checks.json) cover the nine feet and their pull directions. The [support comparison](exports/print-trial/support-comparison.json) records the unsupported control and the selected slice. Run `reproduce51.py <build-directory> --compare exports/print/trial.3mf` to recreate and compare the editable layout. Run `release51.py exports/print/paths.gcode.3mf exports/print/trial.3mf exports/print/joined-audit.json <output-directory>` to package the checked slice.
