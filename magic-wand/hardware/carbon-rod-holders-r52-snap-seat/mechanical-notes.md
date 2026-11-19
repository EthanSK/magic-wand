# R52 hinge and OP1 seat

The four Choc interfaces, metal hinge stack, OP1 board, lead and DFRobot nest come from R51. The two changed printed parts are the key carrier and DFRobot bracket. Fit the board and axle before installing the four outside keys.

## Fitting the OP1 board

1. With the touch paddle removed, lift the two rounded crossbars about 1.1 mm. Both spring leaves grow from the same side of the raised edge around the board recess.
2. Feed the board with its connector attached from the open long side. Start at about 62° to the seated position and lower the board into the entry groove. Turn it nearly flat before the last sideways slide beneath the raised fingers. Route the flexible lead through its original exit.
3. Ease both fingers down. The two tapered pegs enter the board eyelets. The board sits on its original floor. The crossbars catch it if it starts to rise.
4. Fit the microswitch, replace the DFRobot paddle and sleeve, then fit the axle, locknut and outside keys. For board removal, remove the paddle, lift both fingers and reverse the board movement.

The fingers lift vertically. Both working beams are 15.4 mm long from the modelled root centre and 1.14 mm thick. A uniform-beam estimate gives roughly 0.92% surface strain at full lift. A tapered-beam calculation using the working width and thickness gives 0.85%. Real force, transverse nose twist, layer adhesion, fatigue and the ease of lifting the crossbars by hand require a printed trial.

## Pusher and hinge

The left fixed stop now meets the rigid underside of the paddle. This leaves the plugged board’s entry route open. A small fixed pad meets the original right heel.

The shallow rounded contact is 4.8 mm across, over the 2.9 × 1.2 mm reference plunger. The metal stack remains the M2 × 20 mm axle screw, 3 mm OD × 2.1 mm ID × 12 mm sleeve and M2 locknut. The paddle journal spans 11.84 mm. The two rounded thrust faces span 11.86 mm, leaving 0.14 mm nominal total end play with the cheeks clamped onto the sleeve, down from 0.40 mm in R51. Each thrust face reaches above and below the axle so a tilted paddle picks up opposite cheek faces. The 3.25 mm nominal sleeve bore has extra room at both diagonal regions where early native slices ran tight.

The editable model and assembly transforms are in [build52.py](build52.py). [mechanical_checks52.py](mechanical_checks52.py) checks the exported parts against the actual project hardware references. Physical click travel, switch registration, spring-back, wear and manufactured bore size remain unmeasured.

## Hardware evidence

The [Endgame Gear switch kit](https://endgamegear.com/products/op1-universal-switch-set) and the [Omron drawing](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/5389/D2FC_Datasheet_EN.pdf) are the retained references. The board outline, thickness, connector and wire use the [existing component model and reference notes](../carbon-rod-holders-r32-complete-assembly/README.md). Its 17.9 mm pitch and 4.05 mm nominal eyelets are photo-derived. The model checks eyelets down to 3.6 mm and pitch from 17.3 to 18.5 mm. The real button crown radius and the fitted cable's stiffness remain unknown.

## Export checks

Both assembly STLs reload as closed, consistently wound solids. R51 contains coincident surface edges at some socket cuts. The R52 exporter keeps the indexed topology when writing STL by separating coincident vertices by at most 0.00032 mm. The carrier uses 0.004 mm mesh simplification and the paddle uses 0.002 mm. The floor cut discards 0.451 mm³ of disconnected skin in total, with each remnant smaller than 0.11 mm³. These sub-layer corrections are separate from the functional changes to the matching parts.

The printed-path gauge for the final journal found a conservative 3.068 mm opening for the nominal 3.00 mm sleeve. With the cheeks seated against the sleeve ends, the geometry limits roll to 0.72°, compared with 0.99° in R51. Both exported cheek faces engage if the paddle rolls 0.2° farther in either direction. The five nominal press cases give 0.579–0.704 mm of button travel against the 0.48 mm design target.

The [combined play check](exports/contact-misalignment.json) tests 16 board-shift directions against the slot and socket barrels, with both available axial end positions at five paddle roll angles. The reference allows 0.35–0.50 mm of PCB translation in these directions. All 128 tested combinations depress the illustrative rounded button 0.572–0.704 mm. At the most crowded hard-stop pose, the housing and paddle are effectively touching (0.00046 mm³ overlap). This is inside the 0.001 mm³ mesh tolerance and leaves no measurable manufacturing margin at that extreme. Physical testing should include both lower corners with the locknut seated against the sleeve.

For the rear-edge print, the lower non-mating faces of the key floors have a stepped bevel. The analytic cut removes 21.004 mm³. It preserves the switch seats, tape lands, sockets and finger contact faces, with less than 0.000001 mm³ calculated protected overlap. Four shallow entry bevels remove another 13.447 mm³ beneath the square key openings. Three retaining lands remain on each affected edge. The top seat plane remains at the same height. Three purchased switch flanges retain the full R51 bearing area. The fourth retains 99.44% (14.63 of 14.72 mm²) after the spring-pocket relief. [Four-key bearing check](exports/key-bearing.json)

The frozen carrier and paddle are single watertight STL solids. [Dimensions and hashes](exports/dimensions.json) · [Mechanisms print checks and cleanup](mechanisms-print.md)
