# R80 touchpad repair

[View the fitted touchpad and assembly sequence](../carbon-rod-holders/assembly/?version=r80&component=keys&view=pin_hinge) · [A1 mini PETG repair plate](exports/print-mechanisms/R80-Touchpad-Repair-A1-mini-PETG-print-only.3mf)

The R79 board could rock on its two posts. Fine loose strands inside the printed holder also made the short click feel stiff. Removing the strands helped, but some resistance remained. The point that rubbed on the physical print is unknown.

## What to replace

The repair plate contains a two-post bar, the slide-in OP1 retainer and two separate flat board clips. Reuse the fixed key holder, moving touchpad, hinge pin and pin clip. The flat board clips are the same easy-to-fit parts used in R79.

- **Board fit.** Lift the touch board off. Push the two-post bar up through the underside of the loose paddle until it seats. Each post has two wider bearing surfaces and a small spring that yields as it enters the hole. Lower the board onto both posts with the white connector underneath. Slide the flat clips onto the narrow necks. The head height and post spacing match R79.
- **Click travel.** Hold the assembled paddle down and slide the new retainer along both rails. Each lower hook now has an opening beneath it and more room fore and aft. The side walls carry the load around the openings. The hinge, switch contact and upper catch retain the fitted travel.
- **Cleanup.** Free the four parts from their disposable pads and lift out any loose strands before assembly. Check for a smooth click and return at the centre and both lower corners. If a clean assembly still sticks, compare the same press with the retainer withdrawn while keeping the OP1 board seated.

## Fit evidence

DFRobot lists two nominal 3 mm mounting holes. The actual finished holes and their spacing on the fitted board have not been measured. The bearing surfaces and spring accommodate some variation. In a straight full press the modeled clearance beneath the hooks increases from 0.54 to 0.92 mm. The upper catch engages at the same angle. Clip force, long-term spring behavior and click feel still need a physical trial. [DFRobot DFR0030 specifications](https://www.dfrobot.com/product-78.html)

- [Editable parts](design80.py) and [CAD dimensions and contact checks](exports/posts80.json)
- [Full and tilted press, return and retainer insertion](exports/click-comparison.json)
- [Measured spring travel through the existing paddle and the nominal board holes](exports/print-mechanisms/paddle-passage.json)
- [Printed arm sections](exports/print-mechanisms/load-sections.json) and [support and layer checks](exports/print-mechanisms/layers.json)
- [Independent review of both native slices](exports/print-mechanisms/review.json)

The affected requirements are `dfrobot-post-fit`, `flat-board-clips`, `r79-board-post-play`, `hinge-small-friction-relief`, `hinge-low-keeper` and `r79-stiff-click-result`.
