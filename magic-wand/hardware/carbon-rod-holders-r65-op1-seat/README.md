# R65 OP1 board seat

R64 opened an underside insertion path for the wired OP1 but removed much of its integral board seat. The physical R64 print exposed a large opening at that position. In the exported carriers, support within 0.10 mm of the board fell from 160.25 mm² on R63 to 73.21 mm² on R64. The old area-only check allowed almost all of it to lie on one side.

Face-on and underside photos of the R64 print show the central opening between the four keys and fine strands of filament across it. The photos do not establish whether an edge also broke off.

The replacement must support both sides of the board and the switch where the paddle presses. With the switch removed, the PCB must still enter from below with its white connector and lead attached beside the installed rod. The print trial and meshes for [R64](../carbon-rod-holders-r64-under-entry/) are preserved for comparison.

## Fit the wired OP1

1. Leave the removable black switch and the upper retainer off. With the printed seat outside the holder, lower the wired PCB onto it. Its three metal sockets go through the holes in the seat.
2. Bring the loaded seat up from below at the open end beside the carbon rod. Slide it into the holder with the white connector first, then lower it onto its two bearings.
3. Fit the black switch and assemble the paddle. Slide the original upper retainer over the board. It keeps the board down and prevents the seat from lifting over its stops. To remove the board, take off the retainer and switch, then reverse the guided slide.

The fourteen-piece plate includes the new seat, both hinge pins, the spare pin clip, the two touch-board clips and the remaining R64 fittings. The seat has a small breakaway grip at its closed end. [View the assembly](../carbon-rod-holders/assembly/?version=r65&component=keys&view=op1_clips)

## Checks

The revision covers the existing requirements for underside entry, attached wires, the OP1 sliding retainer, click travel and the complete key-holder kit. [Mechanical measurements](exports/support.json) cover the PCB contact areas, seat-to-carrier bearings, retention, loose-board loading and the route past the installed rod and keys. The [extrusion check](printed_seat.py) measures actual sliced plastic on each side and beneath the click point, with R63 and the failed R64 slice as controls.

| Positive extrusion 0.10 mm below the PCB | R63 | R64 | R65 |
| --- | ---: | ---: | ---: |
| Board support, left half (mm²) | 79.32 | 72.64 | 88.94 |
| Board support, right half (mm²) | 79.35 | 0.21 | 91.51 |
| Support within the switch footprint (mm²) | 45.06 | 16.80 | 44.89 |
| Distance from the press point to the nearest plastic (mm) | 0.00 | 1.20 | 0.00 |

The R65 seat has 2.72 mm² of deposited plastic in the small rectangle directly beneath the plunger. The printed carrier supports the seat on both sides, with 110.06 mm² on the left and 19.24 mm² on the right. The modeled load and removal path clears the full-length rod by 0.915 mm. Hand fit, click feel and durability require the physical parts.

Both native slices passed all 69 insertion and removal checks. The independent review traced the carrier's floating-region warning to anchored runs. All fourteen parts had zero completely unsupported starts. The print-only file contains the same machine instructions as the reviewed primary archive.

[Slice cross-sections](exports/print-mechanisms/op1-seat-comparison.png) · [Slice measurements](exports/print-mechanisms/printed-seat.json) · [Independent review](exports/print-mechanisms/review.json) · [A1 mini PETG plate](exports/print-mechanisms/R65-Complete-Key-Holder-A1-mini-PETG-print-only.3mf)
