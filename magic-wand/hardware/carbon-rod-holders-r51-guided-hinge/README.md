# R51 touchpad hinge and battery lid

The next prototype uses the changed key holder, the DFRobot touch-board bracket and the sliding battery lid. Reuse the existing XIAO holder and keeper, battery cradle, cable clip and the two DFRobot board clips.

## How the touchpad fits

The two-key row is at the top. The gold pad clicks at the three-key end. Fit the OP1 and route its wire, then fit the axle **before the outer switches and caps**. The outer keys block sideways access to the screw and locknut once installed.

1. Slide a smooth metal sleeve, 12 mm long with 3 mm outside diameter and 2.1 mm inside diameter, into the orange bracket.
2. Lower the reinforced bracket between the two fixed cheeks. Insert an M2 × 20 mm socket screw through both cheeks and the sleeve. Fit an M2 nylon-insert locknut. The sleeve takes the clamping load. Check that the bracket rotates freely and has no perceptible rattle.
3. Connect the DFRobot lead. Seat the board over the two posts and fit the two existing printed clips. Fit the four outer Choc switches and caps.
4. Press the middle and both lower corners of the copper pad. Each should click, return freely and feel steady. If it binds, check bore roundness and clearance before tightening anything further.

The metal hardware is additional to the printed parts. The triangular roots, fixed hinge cheeks and central bearing are permanent. The previous revision's thin outside guides and adjustable stop screw have been removed. The integral travel limits are part of the bracket.

## What was checked

- [Mechanical fit and click travel](exports/mechanical-fit.json) covers the bought-part envelopes and reference travel. Real click feel, finished bore dimensions and repeated-use durability need a physical test.
- [Unchanged parts](exports/reused-parts.json) compares the R48 native toolpaths with the successful wide-pad retry, checks the joints on those paths, and checks each retained solid for narrow necks. The cable clip reference mesh was cleaned of zero-area triangles. Its volume and real faces are identical.
- [Lid geometry](exports/lid-checks.json) and [native print paths](exports/lid-slice-checks.json) cover the new feather pattern, rails, latch, and twelve open windows across all four layers of the central sheet. The standalone lid slice is a window check.
- [Assembly guide](exports/assembly-guide.json) uses the same print meshes and checked click poses. Select **Axle assembly** under **Keys** to see how the parts go together. Choose **Battery holder** to see the new lid.

The generators in this directory use the existing Wand CAD dependencies. Generate the parts with `build51.py` and `lid51.py`, check them with `mechanical_checks51.py` and `audit_reuse51.py`, then run `guide51.py --register`. Use the repository's guarded geometry runner for CAD generation and mechanical checks. Verify the guide over the running viewer with `node verify_viewer51.mjs`.
