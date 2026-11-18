# R51 support and cleanup

The [three-part slice](../print/paths.gcode.3mf) takes an estimated 2 h 26 min and uses 18.93 g in total. The [native preview](printed-supports.png) shows the carrier in red, disposable supports in blue and the bed brim in tan. The holder prints on its rear edge, the bracket on its front edge and the lid flat.

Without supports, Bambu's toolpaths started 10 separate regions of the holder and two of the bracket in air. Turning the holder sideways increased its count to 20. The selected layout backs every region recorded by this test. It uses roughly 2.59 g for the nine exterior props and the ordinary supports on the two parts, excluding their brims. The [comparison](support-comparison.json) and [selected native checks](../print/joined-audit.json) record the actual paths.

## Remove the supports

1. Let the plate cool. Lift the parts and peel away the brim so the individual prop feet are free.
2. Hold the thick frame. Remove the ordinary blue support from the four outer switch openings towards their open faces. Trim a stubborn contact with flush cutters while the electronics are out.
3. Peel each of the nine long props outwards, holding each by its own round foot. The first pulls left and slightly towards the rear of the bed, the middle seven towards the front, and the last tall post right and towards the rear. The narrow finger rails should carry no levering force.
4. Inspect the left outer switch edge before inserting the switch. Small pieces can remain there. Dry-fit the screw and sleeve and check that the paddle swings freely before installing the electronics.

The [removal check](support-removal-checks.json) found a clear straight withdrawal for each prop after brim and ordinary support removal. A 0.8 mm loose-fragment simulation found a route out for 140,937 of 140,957 ordinary-support samples at a 0.2 mm grid. The remaining samples were at the left outer switch edge. All tested sensitive regions were clear, including the wiring, finger rest and axle bores. Physical cleanup and hardware fit are still to be tested on this print.

## Rebuild the selected layout

Run from the R51 directory in the project's CAD Python environment and external scratch workspace, under the project geometry budget. Choose a fresh output directory on the scratch disk. The optional native slice also needs Bambu Studio installed and a fresh AGENT_SCRATCH_DIR.

```sh
python reproduce51.py "$AGENT_SCRATCH_DIR/recheck" --compare exports/print/trial.3mf --slice
```

The three mesh inputs are in `exports/`. The R50 editable layout supplies the native process template. `orient51.py`, `plate51.py`, `spots51.py`, `props51.py` and `clearance51.py` build the selected orientation, painted support regions and exterior props. The release also uses the project path reader and the R45 headless slicer. [Support-free control](support-free-control.json) and [exterior prop positions](external-prop-paths.json) are the required measured inputs. The rebuild rechecks each prop position and all four native model/process resources against the selected editable layout. [Reference hashes](reproduction-check.json)

To inspect a new slice, use the matching frame and new archive together. These commands run after the rebuild above.

```sh
result="$AGENT_SCRATCH_DIR/recheck"
python support51.py "$result/R51-changed-parts.gcode.3mf" "$result/R51-changed-parts.frame.json" "$result/support.json" --roofs
python removal51.py "$result/R51-changed-parts.gcode.3mf" "$result/R51-changed-parts.frame.json" "$result/props" exports/print-trial/external-prop-paths.json
python preview_paths51.py "$result/R51-changed-parts.gcode.3mf" "$result/support-preview.png"
```
