# R48 edge click

The bottom row has three controls. Its centre control is a DFRobot DFR0030 touch board that pivots on the snap hinge at the opposite end. Pressing the free end operates the plunger on the separate OP1 mouse-switch board underneath it. The key carrier, touch-board hinge, removable print supports and battery mount were revised after the [R47 physical trial](../carbon-rod-holders-r47-bottom-click/PHYSICAL-TRIAL.md).

The plunger centre moves from 6.5 mm to 1.65 mm behind the free edge. The OP1 board turns from 19° to 20.5° under the touch board. Its screw centres remain 17.9 mm apart. The four Choc switches retain their R47 height and spacing.

The centred straight alternative leaves the bare white housing 2.4 mm above the rod, but its fitted plug overlaps the rod by 7.82 mm³. Raising the board 1.25 mm gives the plug 0.55 mm clearance from the rod, while the connector assembly still overlaps the uncut clips by 10.22 mm³. Moving the board 6 mm sideways places the switch off centre. The diagonal layout clears the fitted plug and keeps the click in the middle.

The adjustable stop sits to the left of the switch opening. The three right finger-rest ribs connect to the deck around the connector. A rounded shoulder backs the rod clip beside the plug, and two runners under the OP1 eyelet carry its load into the deck. Both sides of the triangular bracket window widen into their rigid roots before the flexible hinge arms begin. The internal slope under the OP1 connector pocket continues until each layer has material beneath it. The original fixed-length slope ended early after the switch moved towards the edge.

The nominal lever arm is 37.87 mm on a 39.52 mm paddle. In an ideal hinge, pressing at the board edge needs about 13% less fingertip travel and about 15% more force than R47 for the same switch. The new position places the mechanical click directly under the fingertip. The force a person feels also depends on switch tolerances, hinge friction and preload.

## Assembly and fit trial

Use the DFRobot view for the OP1 board, touch-board clips, hinge and stop screw. Connect the OP1 harness to the board. Feed its free wires through the 4.16 mm wide rounded slot that begins directly on the plug axis, then lower the connected OP1 board into the centre slot. The socket, pins and lead face down. Pinch the empty bracket’s two snap arms just enough for their pivot tabs to enter the hinge holes. The short central prong between the two hinge arms limits how far they can be squeezed during assembly. Leave it in place. The printed arms start 7.34 mm apart and the receivers hold them at 6.80 mm. The fixed side guides limit sideways drift if one tab seats first. Release the arms, check that both tabs have entered their holes, then seat the wired DFR0030 on the bracket posts and fit its two matching post clips. Check the lead stays clear through the short click and release. The printed spring roots load across layers during installation. Squeeze only until the tabs clear the receivers and check both tabs stay seated after release. The switch should click and return freely before the backup stops touch. The modelled connector envelope and click setting require a check with the bought parts.

With the real switch installed, press near the three-key edge. If the stop prevents a click, turn its screw in a little and try again. Check that the switch releases when you lift your finger. The screw head and the plastic backup feet both show in the DFRobot assembly animation.

The complete print includes the key carrier, DFRobot bracket, two post clips, XIAO holder and keeper, Micron 100 mAh battery holder and sliding panel, and twelve-wire cable clip. The coloured cradle, separate front and rear supports, and bed tabs in the cleanup view are disposable. Support the rigid carrier as you withdraw each grip along the direction shown. Levering against a finger-rest rib can break it. The rod and electronics are hardware references in the viewer.

## Micron battery cassette

The two-piece replacement fits one Micron 100 mAh cell. The listed cell measures 27 × 11.8 × 3.9 mm and weighs 2.05 g. Lower the cell into the open tray and guide the leads through the end opening. Slide the patterned cover into its rails until the catch engages. For a swap, hold the tray and pull the solid front edge of the cover towards the wire end. The rounded catch flexes in its side groove as the cover comes out. Keep the wires clear of your grip. [Micron battery specifications](https://www.micronradiocontrol.co.uk/lipo_1s.html)

The model leaves 0.55 mm on each side and 0.65 mm above the nominal pouch. The catch engages the rail. The middle of the cover is 0.8 mm thick, with 1.1 mm sliding edges. The R47 assembly remains available for the wider PKCell battery.

## Rebuild

Run the scripts in a fresh Python process with the same geometry dependencies as R47. Use the repository’s printability-audit geometry runner and a private scratch directory for intermediate files. The native slicer requires Bambu Studio and its A1 mini profiles. Slicing runs headlessly.

1. Run `build48.py SCRATCH`. The carrier, cap and full CAD checks go in `SCRATCH/stage`. Their R47 internal filenames are retained for compatibility with the standing-carrier generators. The receipt separately identifies R48 and checks the forward switch.
2. Run `battery48.py SCRATCH/battery48` to build the Micron cassette and its matching slider.
3. Run `native48.py ACTION SCRATCH` for `layout`, `slice`, `reopen`, `carrier`, `others` and `finish` in that order. Use isolated native scratch for slicing and reopening. Consult the native driver for the per-part manifest required by the other-parts audit.
4. Generate the assembly guide from the final CAD and complete-plate audit with `guide48.py`, then run `native48.py seal SCRATCH`. The print-only package preserves the reviewed machine paths. Physical fit, click feel and ease of cleanup require a printed assembly.
