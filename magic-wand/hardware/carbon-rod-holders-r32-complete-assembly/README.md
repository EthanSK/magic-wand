# R32 Complete assembly

[Watch the assembly](../carbon-rod-holders/assembly/?version=r32&component=keys).
The version selects a matched set. **Component** switches between the keys,
XIAO holder, battery holder and cable clip. **Assembly view** opens the hinge
detail, keeper or patterned spacer within the corresponding component.

## OP1 board and touch bracket

The board drops onto two small locating shoulders with the two upper keycaps
removed. Fit the two kit screws through the eyelets, connect the plug from
below, then push the switch into its three sockets and refit the keycaps. The
board sits at the R31 height of 9.2–10.8 mm in the assembly frame. It is turned
25° around the switch actuator so that the white plug and cable exit beside
the rod. The opening accounts separately for the metal contacts, socket
barrels, white plug and wire bend.

The [Endgame Gear kit photos](https://endgamegear.com/products/op1-universal-switch-set)
give an estimated 30 × 10 mm outline and 17.9 mm eyelet pitch. Scaling the
eyelets against the two outer socket centres gives roughly 3.8–4.5 mm diameter.
The CAD checks 17.3–18.5 mm pitch with 3.6 mm holes. The board thickness is modelled at
1.6 mm, the sockets at 4.3 mm deep and the coupled connector at 5.9 mm deep.
The wire envelope is 2.6 mm in diameter and the side opening extends past it.
The [Omron D2FC-F-7N(60M) drawing](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/5389/D2FC_Datasheet_EN.pdf)
gives the offset pusher, terminal positions and 3.15 mm terminal length. The
CAD allows 3.5 mm for the pins and uses the [kit's M1.6 × 4 screw size](https://help.endgamegear.com/hc/en-us/articles/35993513355037-Mouse-Screw-Dimensions).
The first screw is offset within its eyelet to clear the switch. Its nominal
head clearance is 0.15 mm and it needs at least a 3.4 mm eyelet for a practical
fit. Tighten it gently into the PETG. The PCB, connector and wire envelopes
still need a physical fit with the bought kit.

The [R31 rear snap hinge](../carbon-rod-holders-r31-rear-hinge/) and DFRobot
bracket remain the same. The two flexing arms have 1.2 × 1.4 mm sections and a
free span of about 10.8 mm. The orange crossbar ties the rails together and
carries the pusher and stop feet. Diagonal ribs help print it front-down. The
six key guard runners are tall on edge to resist finger pressure while leaving
room for sockets and solder. A later weight pass can open the crossbar between
its loaded areas and evaluate lower crosswise guards with the same clearances.

## Complete plate

The [plate list](complete-assembly.json) specifies ten parts. The keys use a
carrier, touch bracket and two post clips. The XIAO uses its holder and near
keeper. The battery uses its holder, end door and patterned 0.4 mm spacer.
The last part is the 12-wire clip.

The A1 mini profile uses a 0.4 mm nozzle, textured PEI and
[Flashforge Metallic HS PETG](https://uk.flashforge.com/products/hs-petg-metallic)
at 250 °C nozzle and 60 °C bed. The first-fit plate uses the same temperatures
for the first and later layers. Remove the tear-away pads and brims before
checking the parts. The wipe tower is for smooth timelapse.

- [Sliced A1 mini plate](exports/R32-Complete-A1-mini-PETG.gcode.3mf)
- [Editable Bambu Studio project](exports/R32-Complete-A1-mini-PETG-layout.3mf)
- [Slicer, original and reopened toolpath checks](exports/print-checks.json)

Bambu Studio estimates 1 h 46 min and 17.24 g. Both slices finished without
warnings and passed checks for attached first layers, open working spaces
and critical cross-sections. The reopened project retained the settings and
regenerated some commands, so its paths were checked independently. The
upper Choc switch's two retaining lips retain their R31 geometry. Each of
the six reopened seat probes found at least 1.25 mm and three printed tracks.
The patterned spacer keeps all 27 openings.

See [geometry checks](exports/geometry-checks.json) for the PCB and plug
installation paths, click stroke and hinge clearances. The first physical
trial should check screw and plug access, the actual switch's click and return,
and the force needed to pinch and remove the bracket.

Generate the meshes and viewer data with `python3 assembly32.py`.
`assembly32.py --make-current` also sets the viewer default. Slice with
`python3 plate32.py --scratch <directory> --slice --filament-profile "Flashforge HS PETG Metallic"`
through the geometry budget runner.
