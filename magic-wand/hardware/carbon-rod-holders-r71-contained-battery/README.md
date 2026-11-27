# R71 key holder: battery inside the holder, spring clips, eased hinge

R71 starts from the printed R70 holder. The final geometry has CAD checks and two checked A1 mini PETG slices, including reopening and re-slicing the saved archive once. Both contain the reshaped spring clips. Nothing in R71 has been physically printed or fitted.

| Part | File | Change |
| --- | --- | --- |
| Key holder | [`Key_Carrier-assembly.stl`](exports/Key_Carrier-assembly.stl) | Battery inside the outline, new rail, re-routed left guard arm, mirrored rear shoulder |
| Touch paddle | [`Touch_Paddle-assembly.stl`](exports/Touch_Paddle-assembly.stl) | Hinge journals 0.07 mm lower top and bottom |
| Touch-board clips | [`DFR_Clip_Left-assembly.stl`](exports/DFR_Clip_Left-assembly.stl), [`DFR_Clip_Right-assembly.stl`](exports/DFR_Clip_Right-assembly.stl) | Spring clips: a 2.0 mm frame with two leaf arms and feet that press the board down |
| Two-post bar | [`DFR_Post_Bar-assembly.stl`](exports/DFR_Post_Bar-assembly.stl) | Ribs keep their full size for three layers; a third ledge under each head |
| Three wires, OP1 retainer | [`Gravity_Wires-assembly.stl`](exports/Gravity_Wires-assembly.stl), [`OP1_Lid_Stop-assembly.stl`](exports/OP1_Lid_Stop-assembly.stl) | None: R70's files, byte for byte |

The plate has the same nine pieces as R70: these, one hinge pin, the centre clip and its spare.

## 1. Battery

R70's pouch stood 12.45 mm behind the holder. In R71 it ends level with the rear face.

| | R70 | R71 |
| --- | --- | --- |
| Pouch, across | X -21.25 to -9.45 | X -27.45 to -15.65 (6.2 mm outward) |
| Pouch front | Y 21.90 | Y 9.45 (12.45 mm down the holder) |
| Pouch top | Z 7.22, against the deck | Z 4.17, 3.10 mm under the deck |
| Behind the rear face | 12.45 mm | 0.00 mm |
| Held by the rail | 14.55 mm | 16.05 mm |
| Rail outside the pouch | 3.3 mm | 0.9 mm |
| Lowest point of the rail | Z 2.37 | Z -0.68 |

**What limits it.** A 27 mm pouch that ends at the rear face lies under the upper-left hot-swap socket and reaches the gap between the two left sockets. Three things hang under the deck there, read from the fitted models:

| | Underside |
| --- | --- |
| Socket bodies | Z 5.60 |
| Their tape margin | Z 5.20 |
| Stated solder-and-wire allowance on the socket terminals | Z 4.37 |

The allowance is two blocks over the pouch: the inboard terminal of the upper-left socket (X -18.73 to -16.33, Y 12.38 to 15.66) and the rear terminal of the lower-left socket (X -26.36 to -23.08, Y 7.28 to 9.68). The pouch is 11.8 mm wide and the free width between the upper-left socket's two terminals is 9.6 mm, so it cannot pass beside them. Three pad ribs keep the pouch's top 0.15 mm under the allowance; with its 0.05 mm play the nominal pouch is 0.20 mm under it, 1.03 mm under the tape margin and 1.43 mm under the sockets.

**Other places tried.** The pouch was slid forward at four heights and four sideways positions until it met the fitted switches, sockets, tape margins or solder allowance, and again with R70's guard left where it was ([battery.json](exports/battery.json)):

| Pouch top | Under the deck | Least behind the rear face | Same, with R70's guard |
| --- | --- | --- | --- |
| Against the deck (R70) | 0.05 mm | 12.15 mm | 12.15 mm |
| Under the three switch posts | 1.15 mm | 9.65 mm | 9.65 mm |
| Under the tape margin | 2.17 mm | 6.25 mm | 6.25 mm |
| Under the solder allowance (R71) | 3.10 mm | 0.00 mm | 4.05 mm at R71's sideways position |

Sideways position does not help; height decides. At the tape-margin height a fully inside pouch would put 6.3 mm³ of itself into the solder allowance, on the two joints. If the real joints and wires lie flatter than the stated allowance, `SOLDER_Z` in `design71.py` is the one constant to raise; the pouch then sits up to 0.93 mm higher.

**Rail.** Both walls, both lips and the pad ribs start at Y 20.40, where R70's rail started. The upper-left socket still comes up from below in front of them, and the strip of deck behind that socket stays free for its tape and wires. The outer wall is one rigid 0.83 mm wall, 1.6 mm inside the bank's side so the rounded lower edge runs past it. The spring is a tongue cut into the inboard wall with R70's section, lever and preload (1.04 × 2.36 mm, 8.25 mm, 0.21 mm). Lips carry 77.0 mm² of the pouch (R70 69.8). The pad ribs bear on 57.5 mm² of its top; two of them cross the lightening windows under the key.

**Nose.** The pouch's front 10.95 mm runs forward of the rail, under the taped socket. It stops 0.05 mm from the left guard's top arm, which crosses the nose at the pouch's mid height. Pushed 0.2 mm further it meets that arm.

**Order.** Sockets, tape, switches, then the pouch. The upper-left socket's loading route passes through the place the pouch then takes, and the lower-left socket slides 0.23 mm past its nose, so the pouch comes out before either left socket is changed. With the pouch out, all 336 key and socket poses are clear.

**Removal.** 76% of the pouch's underside is open, including an 11.8 × 9.95 mm window in front of the rails. Press a fingertip there and slide the pouch back until its end can be held. Nothing is pulled by the leads and there is no cover.

## 2. Left finger guard

R70's left top arm crossed under the place the pouch's nose now takes, and the crown's rear bar lay under it. With R70's guard unchanged the pouch would stand 4.05 mm behind the holder.

- The arm keeps its root in the deck and its first 3.9 mm (to Y 18.37).
- From there it runs down beside the pouch (centre X -13.78, 0.55 mm from the pouch's side, past the rail's own 0.47 mm width allowance), turns round the nose and reaches the crown from the front.
- The crown's hub moves 2.7 mm toward the lower row (Y 10.2 to 7.5). Its three bars keep their far end, their height and their section.
- No member is lower than before: the left guard's lowest point is Z -0.51 in both revisions. Sections are R62's 1.32 and 1.26 mm radius. Both lower rails and the closed outer tip are untouched.
- Printing slopes are like R70's: the arm's steepest descent is 52.7° from the print axis (R70 54.8°), and its sideways run to the hub rises 7.0° over 4.75 mm (R70 7.2° over 8.7 mm). Cut into 0.2 mm layers, no island starts on nothing, and the arm and bars overhang at most 1.2 mm² in a layer (R70 1.5 mm²). The largest overhang, 2.9 mm², is the rail wall closing over the free end of the spring tongue, a 3.8 mm bridge between two strips of that wall.

The crown now ends 0.69 mm in front of the pouch's nose. Of the 34.6 mm² of plan the guard no longer covers, 21.7 mm² lies under the pouch; the rest is the arm's old path, and the arm covers 22.6 mm² of new plan. Without a pouch the strip behind the crown is open, as the space under the upper-left socket always was.

## 3. Rear outline

Seen from above, R70's left rear shoulder was larger than its right one. The left bank's plate behind Y 24 is cut to the mirror image of the right bank's outer outline (left-only area 26.38 to 0.03 mm²). This removes 97.9 mm³ and adds nothing. A 2.95 mm roof strip stays over the battery's outer wall. Only the outline is mirrored: nothing is taken from the left key's backplate inside it (checked, 0.0 mm³).

## 4. Hinge

The printed R70 hinge clicked but felt slightly stiff. The tightest place in the CAD is the pair of journals: 0.15 mm fore and aft, 0.035 mm above and below. Each journal is now 0.07 mm lower top and bottom, so that becomes 0.105 mm. Fore-aft and sideways play are unchanged, and the click sweep gives R70's contact angle, stops and travel. Which surface rubbed in the hand is not known.

## 5. Touch board

**What R70's native slice showed.** The posts print upright in 0.2 mm layers, and R70's ribs taper from the paddle seat up. Only the first layer printed 3.049 mm across; the layer above it is about 3.00 mm. A 3.0 mm hole was gripped by 0.05 mm in the first 0.2 mm only, so any clip that let the board rise 0.2 mm let the hole leave the grip. The CAD rib tips are about 0.18 mm further out than the printed beads; CAD squeeze figures are not the printed fit.

**Posts.** Each rib now keeps the section of R70's first printed layer for 0.6 mm (three layers) before it tapers to R70's size at the board's top. Shaft, neck, head, wings and height are unchanged, and the ribs still pass the paddle's passages.

| Layer above the seat | R70 native reference | R71 actual native, both saved slices |
| --- | --- | --- |
| 0 to 0.2 mm | 3.049 mm | 3.0455 mm |
| 0.2 to 0.4 mm | about 3.00 mm | 3.0274 mm |
| 0.4 to 0.6 mm | about 2.96 mm | 3.0274 mm |

The author's expected 3.049 mm on all three layers was a source-based prediction. Actual variable-width toolpaths differ, so the native measurements above govern. Across the complete measured 0.20 mm frame-limited board rise plus a 0.05 mm checking margin, the smallest enclosing diameter stays 3.0274 mm. That is positive interference against the documented nominal 3.0 mm hole; the earlier draft reached 2.995 mm within its allowed lift. A 3.1 or 3.2 mm real hole would still clear the ribs. These measurements do not establish physical friction or fit.

[DFRobot specifies two nominal 3 mm holes](https://www.dfrobot.com/product-78.html), without a finished-hole tolerance. The real size and pitch of the purchased board remain unmeasured.

**Head.** A third ledge is added on the round side of the neck, level with the two side wings. The clip then bears on 0.84 mm² of ledge instead of 0.57 mm².

**Clips.** The frame is the whole R59 clip, 2.0 mm thick, with a 1.6 mm spine and a 1.0 mm rear bar behind it. Two arms run forward from the rear bar at the clip's top face and end beside the post in feet that stand 0.4 mm below the frame.

- Pressed down on its front half, between the two feet, the clip slides on 0.2 mm under the head and snaps round the neck like the R59 clip.
- Pressing the rear bar does not work: a free clip rests on its feet and its rear edge with the open end 0.59 mm up, and only 0.2 mm is free under the head.
- Let go, and the arms lift the frame 0.2 mm against the head's three ledges while the two feet press the board down. The arms stay bent 0.2 mm.
- A board that lifts must bend the arms further; after 0.2 mm the frame is in the way, as with the first R71 clip.
- A board that sits up to 0.2 mm high leaves the arms more bent instead of jamming the clip.

**Spring arms.** The first spring clip, retained in the earlier comparison slices, had straight arms that met the rear bar at a square corner. Pressing it flat bends each arm 0.4 mm, which a beam estimate puts at 4.4 to 5.5 % surface strain at that corner. The final saved pair contains leaves: thinner, longer, 1.8 mm wide at the root, and stepped one layer at a time under the root.

| | First spring clip | This clip |
| --- | --- | --- |
| Arm | straight, 0.8 × 1.0 mm | leaf, 0.6 mm thick (three layers); 0.8 mm wide beside the frame, 1.8 mm at its root |
| Lever, rear bar to the heel of the foot | 3.3 mm | 4.6 mm |
| Under the root | square corner, 1.0 mm high | three steps: 0.8, 1.0 and 1.2 mm thick |
| Bending strain pressed flat (0.4 mm) | 5.5 % | 2.0 % |
| Bending strain seated (0.2 mm) | 2.7 % | 1.0 % |
| Where the CAD estimate is largest | at the square corner | in the plain strip; 1.9 % at the first step, 0.7 % at the rear bar |
| Hold-down per clip | about 4.5 N | about 1.3 N |
| Press to fit, per clip | about 8.9 N | about 2.6 N |
| Arm root moment on the rear bar, pressed flat | 14.7 N·mm, bar 0.7 mm deep | 6.1 N·mm, bar 1.0 mm deep |
| Clip | 5.9 × 6.9 × 2.4 mm | 5.9 × 8.2 × 2.4 mm |

How to read the table:

- Strain is surface strain from bending for the stated deflection, integrated along the exported arm ([carrier.json](exports/carrier.json), `clips.*.arm`). It needs no material figure.
- This table and `carrier.json`'s `largest_strain_in_the_plain_arm` describe the source plan, not every printed bead. The native profile below reports the actual sliced peak separately. Neither includes notch effects or proves strength.
- A bent arm tilts its foot, so the heel bears. Both columns load the heel. The first clip's own report loaded the middle of the foot and gave 4.4 % and 2.2 %, 3.2 N and 6.3 N; the same integration reproduces those figures.
- Forces assume a modulus of 2000 MPa and scale with it.
- Friction on the feet is not in the table. With a coefficient of 0.3 it adds about 0.9 % in the plain strip while a clip is slid back pressed flat, and takes the same away while it is slid on. To remove a clip it only has to be pressed lightly.
- For reference only, [Bambu's PETG Basic data sheet](https://store.bblcdn.com/s1/default/cb94589bf7994fdcbfa833badefae9cd/Bambu_PETG_Basic_Technical_Data_Sheet.pdf) lists a bending modulus of 1950 ± 50 MPa and a bending strength of 75 ± 3 MPa for specimens printed flat. The loaded filament was not tested. No elastic limit, creep figure or strength is claimed for the printed arm.
- 1.3 N a clip is about 27 times the weight of the 5 g assumed for the board with its plug and wire (not weighed). PETG held bent relaxes with time. The frame stops a lift at 0.2 mm whatever the spring does.

The clip stays 0.3 mm inside the board's edge. Its rear end is 6.0 mm behind the post axis, 1.3 mm further than the first spring clip's, on the face of the board that is turned away from its connector. The board model is a plain plate; that face of the real board was not inspected. It prints top face down: frame and arms on the bed, then the root steps, the feet last, no bridge. Each clip's inner foot presses the board 0.3 to 1.1 mm inboard of the paddle's land, so about 0.7 N bears on a short unsupported strip of the board.

Two things were tried and dropped. A sloped clip top prints as 0.2 mm steps. A spring tongue under a lower ledge has to climb a whole layer step as it slides in, and two printed steps meet head-on.

The clips hold the board down; sideways location is still the ribs' job. For a hole above 3.05 mm the board is located sideways only by the clips' pressure, which is now about 2.6 N across both clips. The flat 1.4 mm clip still fits the new posts.

## 6. Base release

R70's fins were hard to pull from the plate and left stubs. In R71 every fin has one neck, 0.02 mm from the holder's face and 0.45 mm long, and is full width from there to its post on the plate. Necks are 1.26 mm wide (three bead lines), and 0.84 mm on the fin under the rail's heel.

**Break order.** The neck is the smallest section on each fin (the plate end is 1.35 to 2.03 times as large), so the fin should break beside the holder and stay on the plate. At most 0.47 mm of it can stay on the holder. An earlier R71 draft also necked the plate end to the same width; a fin that broke there would have left 1.5 mm on the holder.

| | R70 | R71 |
| --- | --- | --- |
| Fins | 5 | 5 |
| Section at the holder | 22.74 mm² | 21.93 mm² |
| Section at the plate | 25.84 mm² | 30.60 mm² |
| Fins full width at the holder | 3 | 0 |
| Holder's own first layer | 197.6 mm² | 193.3 mm² |

The three tall fins each go from 8.16 to 6.05 mm² at the holder. Panel, feet, buttresses and fin heights are R70's. Nothing is attached at the hinge, over the open pouch lane or on a lip. The native sections realise this break bias: the plate end is at least 1.3267 to 1.9893 times the holder neck, depending on the fin. Break force, actual break location and holding through a real print remain unmeasured.

## Checks

Every report puts R70 beside R71 and is bound to the mesh hashes it measured ([summary](exports/checks.json)).

| Report | Result |
| --- | --- |
| [battery](exports/battery.json) | Limits read from the fitted models; pouch clear of switches, sockets, tape and solder allowance seated and on its way in; routes; seat; removal; the placement table |
| [carrier](exports/carrier.json) | Unchanged zones match R70 section by section; guard cores present, no old arm left, nothing lower; mirrored outline; click; post layers against R70's slice; clip poses, ledges and the click sweep; spring-arm strain against the first spring clip, open slots and print layers; rounded edge; no print layer starts on nothing |
| [base](exports/base.json) | Nine pieces; one neck per fin beside the holder, smaller than the fin's plate end; three of R70's fins were full width at the holder |
| [source](exports/source-reproduction.json) | All seven meshes rebuild byte for byte |

**Mass (PETG, solid):** holder 11.37 → 11.51 g.

**Not known.** The real pouch's size and lead exit. The real solder joints and wire runs on both left sockets: the pouch lies under them, and flat taped wires are assumed. How firmly 16 mm of rail holds a pouch whose nose is free. The spring force. The feel of a rail 3 mm lower. The arm as a front stop under a hard push. How the re-routed arm prints. The touch board's real thickness, seating height, hole size and pitch. The clips' real force, how long it lasts and how they print. How much bend the printed arms take before they set. What stands on the upper face of the real board under the longer clip. The source of the hinge friction. Base adhesion and where the fins really break.

## Native print qualification

The complete plate has nine separate parts, including both board clips and one spare hinge-pin clip. The saved settings are A1 mini, 0.4 mm nozzle, Generic PETG, 0.2 mm layers, with support generation disabled. Estimate: about 2 hours 53 minutes.

- Primary native archive SHA-256: `9bc93a9aa17bd0a4e3214409128429b11cdcf2bc8ad4a2f1823732f34c716785`.
- Reopened and re-sliced archive SHA-256: `61ea65e44df19fbd2f3ecf32873888199d6f0333394cb32cf16de82ecf9ac6e8`.
- Both pass the full deposited-path opening, loading/removal, separation, first-layer, load-path and clip-retention checks. Zero support moves and zero wholly unsupported starts were found.
- Both contain the final clip meshes (`9edacc6f…` and `f8e743ea…`). The spring slots and spaces under the arms remain open. Each foot has 0.20 mm nominal interference with the seated board; the rigid frame limits board rise to 0.20 mm.
- At the six-layer root stations the measured sections are about 2.09–2.19 mm². The narrower three-layer leaves, the root-step transition and all twelve layers of each foot column are connected. The additional [spring-section report](exports/print-mechanisms/native-spring-arms.json) measures the outer outline and actual material separately, including toolpath gaps, and scans each loaded arm at 0.02 mm intervals plus both sides of its steps. It reports the largest sampled native bending factor rather than assuming the plain strip governs. These are geometric checks, not measured force, strength or bonding.
- Across 230 sections per arm, the highest native factor is at the flare of one arm per clip, 2.47 mm behind the post axis: up to 1.0416 times the source-plan peak. Scaling the source bend estimate by that factor gives about 2.14 % pressed flat, below the existing 2.19 % comparison limit (half the first clip's original reported estimate). Two transverse cuts per arm have separate pieces around small local bead pockets; the independent layer probe found pockets, not slits through the arms. These sections do not model notch effects or establish physical bonding.
- Native post diameters remain 3.0274–3.0455 mm over all three rib layers and through the complete allowed board rise plus the checking margin. The real board holes remain unmeasured.
- The pin and rod gauges, three OP1 holes, board support, connector-first entry, retainer and complete click/lift routes pass with the actual toolpaths. The carrier mesh is unchanged by the final clip repair.
- The OP1 support comparison retains its inherited `R69` panel label. That panel is measured from the current R71 archive; `printed-seat.json` binds the archive and records this label alias. R63 and R64 remain the historical comparison panels.
- Bambu still reports floating regions on the key carrier. Its unchanged guard/rail overhangs and spring-window bridge remain a physical trial item; selected native layers and the earlier independent review account for that warning. The reshaped clips have no new slicer warning.

The per-part review, reports and exact machine file are retained in `exports/print-mechanisms/`. Native and physical acceptance are separate: pouch retention, wiring, clip force/creep, hinge feel, base release and comfort need the actual trial.

Before pressing a clip, check its bed face: both arm slots must be open and the foot tops clean. Clear any thin skin before flexing it, and take it off the bed by the frame rather than levering under the arms. After fitting, check board wobble and look for whitening or cracks at the flare and first root step; compare the free standoff before fitting, after removal and after a day for permanent set.

## Regenerate

Run from this folder in the established CAD environment, with the R71 down to R62 holder folders on the Python path:

```
python3 design71.py                      # holder, paddle, post bar, clips; copies of the R70 wires and retainer
python3 checks71.py                      # three CAD reports; exits non-zero on failure
python3 evidence71.py                    # source reproduction
python3 guide71.py                       # viewer guide (--register / --current publish it)
python3 kit71.py DEST/layout.3mf         # complete nine-piece plate and layout.frame.json
python3 audit71.py DEST                  # deposited openings, routes and attachment
python3 sections71.py DEST               # sections and selected native views
python3 retention71.py DEST              # post, ledge, spring-foot and root stack
python3 arms71.py DEST                   # leaf layers, root steps and full foot columns
python3 evidence71.py --slice-only --slice DEST
```

## Requirements

| Requirement | Where it is met |
| --- | --- |
| `battery-contained-placement` | Pouch ends at the rear face; limits are the solder allowance above and the bank's side; rail 0.9 mm outside the pouch |
| `battery-against-deck` | Superseded by the newer contained-placement direction. The pouch rests on integral pads 3.10 mm under the original deck to clear the modeled socket joints; it does not touch that original deck |
| `battery-fit`, `battery-friction`, `battery-short-rail` | Rail of 16.05 mm with lips, pad ribs and R70's spring section and preload; open underside for removal; no cover |
| `guard-integral`, `guard-contact`, `guard-coverage`, `lower-finger-distance` | Round sections kept; nothing lower; crown 2.7 mm nearer the lower row; lower rails untouched |
| `bottom-edge-rounded` | 81% of the lower edge round, no station square (R70 84%) |
| `hinge-small-friction-relief`, `hinge-stability`, `guided-paddle` | Journal relief 0.07 mm above and below only; click values equal to R70's |
| `key-holder-top-taper-symmetry` | Left rear shoulder cut to the mirror of the right one; nothing added |
| `dfrobot-clip-preload`, `dfrobot-post-fit` | Spring clips press the board down (about 1.3 N a clip, estimated) with no free lift; actual native rib diameters remain 3.0274–3.0455 mm for three layers; post height unchanged; real holes not measured |
| `base-release`, `base-removal` | One neck on every fin, beside the holder, so the fin stays on the plate |
| `complete-key-kit`, `spare-parts` | Nine pieces with the spare clip |
