# Magic Wand R50 targeted feet

The nine functional parts and their assembly come from [R48](../carbon-rod-holders-r48-edge-click/README.md). The upright touch-board bracket keeps the wider feet from its retry. The key holder uses the removable cradle, front and rear shelves, and tabs from [R49](../carbon-rod-holders-r49-wide-feet/README.md) after some key-holder support came loose. The specific support was not identified. The other parts keep their R48 bed contact, including the native brims on the battery door and XIAO keeper.

[Print-only plate](exports/Magic-Wand-R50-Targeted-Feet-print-only.3mf) · [Editable plate](exports/R50-layout.3mf) · [Plate preview](exports/plate.png) · [Verification and slice comparison](exports/verification.json)

Use Standard (100%) on the A1 mini with the 0.4 mm nozzle, external red Flashforge HS PETG Metallic and textured plate. The first-layer perimeter and fill remain at 20 and 30 mm/s. The key holder uses the stock wall speeds away from its locally protected regions. Its acceleration limits, the upright bracket settings, overhang and bridge speeds, the 8 mm³/s material flow limit and Smooth timelapse are retained. Flashforge publishes general guidance for the [exact red metallic spool](https://www.flashforge.com/products/hs-petg?variant=43140414636110).

| Native slice | Estimated time | PETG |
| --- | ---: | ---: |
| R48 wide bracket | 4 h 33 min | 41.34 g |
| R49 wide feet on all components | 5 h 16 min | 48.29 g |
| R50 targeted feet, slower key-holder walls (comparison only) | 4 h 39 min | 42.14 g |
| R50 targeted feet, normal key-holder walls (reopened, selected) | 4 h 28 min | 42.14 g |

Generate the editable file with `prepare50.py R50-layout.3mf`. Add `--control` to reproduce the slower comparison. Use the existing R45 native-slice and R47 reopen helpers on the selected file. `check50.py` runs the key-holder, other-hardware and strength phases using the prepared R48 CAD work directory, then packages the audited G-code. Keep the control slice in the sibling `control/initial.gcode.3mf` for the final time comparison.

Studio retains its key-holder floating-region warning. Its shelf and cradle are modeled as separate breakaway parts that carry the overhangs. The digital checks cover their actual printed paths and removal routes. The physical trial will establish how well the feet adhere and how cleanly the supports release.
