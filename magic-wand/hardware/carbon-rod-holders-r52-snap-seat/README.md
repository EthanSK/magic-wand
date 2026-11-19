# R52 lift-in OP1 board and rounded click dome

R52 is a full nine-piece set for the carbon-rod Magic Wand mouse. The key carrier has two lifting tabs to hold the OP1 board. The DFRobot paddle has a wider rounded contact underneath and a closer-fitting hinge.

## R52 printer files

The key carrier and paddle reached layer 257. Hands-on inspection confirmed the four outer key openings were open. The hinge passages appeared filled, supports stuck, and the OP1 button failed to register reliably. Treat the R52 mechanism file as a comparison for the next redesign. The tower reinforcement below is a separate change to the slicer settings.

| Plate | Parts to keep | Connected first-layer area per part |
| --- | --- | --- |
| [Key carrier and paddle](exports/print-mechanisms/R52-Key-Carrier-and-Paddle-Reinforced-Tower-print-only.3mf) | Key carrier with integral OP1 arms, plus the hinged DFRobot paddle | 4,311 and 3,087 mm² |
| [Six separate accessories](exports/print-wide-accessories/R52-Six-Accessories-Reinforced-Tower-print-only.3mf) | Two DFRobot post clips, XIAO holder, XIAO keeper, sliding battery lid and cable clip | 3,165–3,778 mm² |
| [Battery cradle](exports/print-recovery/R52-Battery-Cradle-Reinforced-Tower-print-only.3mf) | Battery cradle for the existing sliding lid | 3,103 mm² plus a separate 3,116 mm² base for its removable support |

Each functional part has its own pair of removable 0.4 mm panels. The earlier R48 bracket used 2,849 mm². Both layers of the new bases have been checked in the selected and reopened printer files. The hardware, four key openings, two lifting arms and hinge remain on the same design. [Carrier and paddle cleanup](mechanisms-print.md) · [Accessory cutting map](exports/print-wide-accessories/wide-base-cuts.png) · [Battery removal](exports/print-recovery/README.md)

The smooth-timelapse tower is disposable. Its earlier wide brim gave the mechanism plate 3,460 mm² of bed contact, but the tower still came loose during the washed-sheet retry. The final recording frame before removal shows a gap at the foot of the tower, with the wide brim still on the sheet. Both functional pieces stayed on the bed through layer 257. New diagonal ribs join the tower to its own base. Keep the tower and its brim together when discarding them.

| Tower measurement from deposited paths | Key carrier and paddle | Six accessories | Battery cradle |
| --- | ---: | ---: | ---: |
| Connected bed contact | 3,623 mm² | 3,092 mm² | 3,297 mm² |
| Previous tower-to-base contact | 204 mm² | 150 mm² | 123 mm² |
| Reinforced tower-to-base contact | 533 mm² | 362 mm² | 513 mm² |
| Minimum first-two-layer clearance to another part | 7.79 mm | 4.15 mm | 4.85 mm |

The checks compare every layer joint through the bottom 3 mm, including a fresh slice from each saved layout. The new ribs increase the contact area at all fourteen joints. The smallest bed-edge margin is 3.43 mm. These measurements describe room and plastic overlap. Physical adhesion and the tower's strength over a full print still need a trial. [Mechanism tower](exports/print-mechanisms/tower-base.json) · [Accessory tower](exports/print-wide-accessories/tower-base.json) · [Battery tower](exports/print-recovery/tower-base.json)

After cooling, cut the six accessories free at the red marks in the map. Remove any original gold tear-off feet before fitting a part. The two matching DFRobot clips are each about 10 mm long with their original feet and 4 mm long after trimming. Keep both, one for each touch-board post. The hinge takes a smooth metal sleeve (3 mm OD × 2.1 mm ID × 12 mm), an M2 × 20 mm socket screw and an M2 nylon-insert locknut. The outer Choc switches and keycaps are bought parts.

The upright battery cradle came off the bed in the original [seven-piece run](exports/print-accessories/Clips-and-holders.3mf). A shorter retry also moved by frame 17 of its recording. Loose strands accumulated after both detachments. Physical adhesion of the latest larger bases is a separate trial. [Accessory first-layer measurements](exports/print-wide-accessories/wide-bases.json) · [Mechanism bases and supports](exports/print-mechanisms/wide-bases.json)

## Assembly

All rod references use the [full 500 mm carbon tube](../carbon-rod-holders/exports/carbon-stock-tube.stl). The complete assembly view shows both ends.

1. Leave the paddle and the four outer keys off. Plug the lead into the OP1 board and route its free end out of the carrier.
2. Lift the two rounded tabs about 1 mm. Start the board from the open side at the angle shown in the guide, settle it into the recess, then lower the pegs into the board holes.
3. Fit the OP1 switch. Slide the metal sleeve into the paddle, lower the paddle between the hinge cheeks, pass the axle screw through and fit the locknut. Check for free movement.
4. Fit the DFRobot touch board over its two posts and seat one printed clip on each. Fit the outer switches and caps last so the hinge hardware remains accessible during assembly.
5. Click at the centre and both lower corners. Each press should click once and spring back. Check that the board stays seated, its lead is free and all four key switches fit. These are physical checks on a cooled print.

Select **Keys → OP1 board clips** in the assembly viewer for installation and removal. **Keys → Axle assembly** shows how the sleeve, screw and locknut fit. [Assembly guide data](exports/assembly-guide.json)

The [mechanical notes](mechanical-notes.md) give the clearances, the hardware references and the limits of the click model. [Mechanical fit checks](exports/mechanical-fit.json) · [Button alignment checks](exports/contact-misalignment.json)

## Editable sources

Use the repository's guarded geometry runner with the existing Wand CAD environment. Run each OP1 geometry or fit-check command in a fresh process, as the original hardware configurator applies a relative offset once per process. Generate the two print meshes with `build52.py`, check them with `mechanical_checks52.py` and `contact52.py`, and regenerate the assembly guide with `guide52.py --register`. With the local assembly server running, `node verify_guide52.mjs` checks the viewer against the files it serves.

To reproduce the tower comparison, pass the new native slice directory and the matching previous wide-tower native archive to `tower_check52.py`. The previous three archives are under these same export paths in Git commit `c8255ed`. Keep Bambu Studio's native `native/slice.log` beside the new slice. The check reads placement warnings from the log as well as measuring the deposited paths.

On the mechanisms plate, cut and withdraw the two-post spring frame before fitting the OP1 board. The frame crosses the open wire-loading approach. Remove the exterior props before testing key 2’s cap, which needs that space to travel. The wire passage through the carrier stays clear. [Measured clearance and removal instructions](mechanisms-print.md)
