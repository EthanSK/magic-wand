# R19 printability and physical acceptance

Authoring checks, plus independent Claude Opus 5.5 review and a scoped review of
the corrections, accepted the final geometry and slice as a digitally checked
candidate. Seven findings and their dispositions are at the end. Nothing here
has been printed, and no real R19 Studio export has been audited. A digital pass
does not prove strength, fit, pouch safety, spring force, fatigue or clean tear-off.

## Exact artifacts

- CLI slice `exports/R19-A1-mini-PETG.gcode.3mf`, SHA-256
  `8e3b08b5a52cc97aca47152f09dc0b80dba43d238d29714636ca9b7007107d35`.
- Layout `exports/R19-A1-mini-PETG-layout.3mf`, SHA-256
  `14612441d7f8d27fbf8b66826fee1bf45b3a73e6e4b1de59964e5abc73c845e0`.
- `Battery_Holder` print STL `4319800ff7cc512b63d352a3d291bf8403eca331f873c6e0116c44b9ab1baa9b`.
- `XIAO_Rod_Holder` print STL `7efef5ada69c6668f4b9a105de5e6d155afbcd2d41f9327666b33f4f2952fce6`.
- Door, keeper and spacers are byte-identical to R18. `holder19.py` asserts this
  on every export and records the hashes in `exports/manifest.json`.

## What passed

| Check | Result |
|---|---|
| Single watertight body, each part | Pass |
| Working spaces, CAD (cell, door route, wires, board poses, USB, reset, pads) | No overlap above the 0.002 mm3 screen |
| Working spaces, actual beads in the CLI slice | No violations on any part, helper ties included |
| Floating or missing layer starts | 0 on all seven parts (178 battery and 142 XIAO layers) |
| Classified overhang rows | 0 unclassified; 0 partial rows on either holder |
| Ring material below Z 3 against R16 | Symmetric difference under 0.05 mm3, all four rings. This stops below the crown joints, so it does not cover the changed support; see ring support below |
| Fitted interfaces against R18 | 0.0 mm3 difference in door slots, catch bar, XIAO cradle, grooves, ledges, hoop underside |
| Door float at -0.15 / 0 / +0.15 mm | Same catch, release and pack-clearance values as R18 |
| Short features (door and keeper teeth) | Present in every intended layer |
| XIAO board underside, CAD, every pad row, both sides | At least 1.108 mm below the board (R18 1.655 mm), except at R18's unchanged near-ledge lead-in, 0.5 mm at rows 0 and 1 as in R18. No material added beyond R18 above Z 7.8 under any pad |
| XIAO board underside, actual beads, rows 1 to 6, both sides | Highest bead leaves at least 1.112 mm. Row 3 is mostly over a window (7 beads) and row 6 has none. Row 0 is covered by the working-space bead audit |
| Cross-bar roots, actual beads | All 12 roots: bar, rail and keel form one printed island in every strip layer |
| Tear-off ties | 6 per holder, on 6 battery and 4 XIAO pads; continuous beads on both layers; the pads print separately in every anchor layer; bead gap away from ties at least 0.987 mm |
| Tie landing and cutter access | Solid material behind each tie: battery at least 2.49 mm; XIAO upper side 4.4 mm, lower side 4.68 mm, hoop top 1.6 mm. Cutter corridors are clear except an inherited 0.149 mm3 sliver beside each lower XIAO side tie |
| One reopen and re-slice | Same audit passed; normalized G-code differs |
| Studio-export adapter source binding | Matching R19 accepted; mismatched R18 rejected |
| Studio-format adapter fixture | Full audit passed with the exact R19 G-code from before the review corrections, in a synthetic meshless container; no real R19 GUI export checked |
| Adapter on the final CLI archive | Passed, with the CLI archive standing in for an export. This is not a real Studio export |

The slice retains `not_support_traditional_timelapse` warnings at levels 2 and 3,
as R16, R17 and R18 did. This is not a warning-free slice.

## Load paths

R18's whole-panel section screens do not apply to an open design. They were
replaced with measurements in `exports/load-paths.json`, and with member-by-member
bead scans in `exports/slice-clearances.json`.

| Measure | Battery | XIAO |
|---|---|---|
| Most islands in a layer | 5 | 3 |
| Smallest island | 4.65 mm2 | 4.40 mm2 |
| Least widest inscribed core of any island | 1.30 mm | 1.99 mm |
| Least whole-layer section | 17.2 mm2 | 14.8 mm2 |
| Worst layer-to-layer overlap of an island | 0.80 | 0.86 |
| Longest unbraced run | 9.4 mm | 8.6 mm |
| Cross bar strip, plastic actually printed | at least 98% (7.7 of 7.8 mm2) | at least 94% (6.2 of 6.6 mm2) |
| Smallest actual printed area of any island | 4.52 mm2 | 4.07 mm2 |

The inscribed core is the widest circle that fits inside an island. It measures
bulk, and is not the thickness of the thinnest wall or neck. Those are listed here.

| Named thin section | Thickness | Bead centres across | Carries |
|---|---|---|---|
| XIAO hoop outer leg, each side | 1.2 mm | 3 | Hoop bar and lip |
| XIAO hoop inner leg, each side | 1.4 mm | 3 | Hoop bar and lip |
| Battery door-slot outer wall, each side | 1.2 mm | 3 | Door side load |
| Battery catch-bar ligament, Y -13.7 | 0.5 mm | 2 | Door tooth catch, unchanged from R18 |
| Battery catch-bar ligament, Y -13.3 | 0.75 mm | 2 | Door tooth catch, unchanged from R18 |

A separate scan looks for places where an island is joined only by a connection
narrower than 1.18 mm:

| Where | Y range | Layers | Narrowest |
|---|---|---|---|
| Battery catch bar | -13.3 to -13.7 | 3 | 0.5 mm |
| Battery corner links where the ring gussets start | -8.3 to -8.9 | 4 | 0.17 mm |
| Battery near-ring lead-in skin | -9.7 to -14.1 | 23 | 1.01 mm |
| XIAO, one layer at a cross-bar cap | -1.7 | 1 | 1.16 mm |

Every island in every layer is connected downward to the bed. Each rod ring walks
down to the bed through real members and reaches both sides of the holder:

| Ring | Reaches both sides at Y | Smallest total section on the way | Crown joint at Z 4.6 |
|---|---|---|---|
| Battery near | -7.9 | 27.7 mm2 | 42.4 mm2 |
| Battery far | 16.7 | 35.9 mm2 | 50.0 mm2 |
| XIAO near | -1.5 | 41.0 mm2 | 14.9 mm2 |
| XIAO far | 22.3 | 161.8 mm2 | 21.4 mm2 |

### Local free-span screen

This is the worst single run between member merges, scored as cantilever tip
movement per newton. It resets at every merge, so it describes one R19 member. It
is not the stiffness of the holder, not comparable between revisions, and not a
measured force. For that reason no R16 or R18 figure is given.

| | Worst run | Free height | Screen |
|---|---|---|---|
| Battery | Y 1.3, X 6.2 to 11.9 | 8.4 mm | 0.057 mm/N |
| XIAO | Y 7.3, X 5.9 to 12.0 | 7.2 mm | 0.023 mm/N |

No claim is made that R19 is stiffer than R16 or R18. R16's battery lattice broke
during printing, although what started that failure was never established.

## Ring support

Bore, slit and ring section match R18. How much of each ring is bonded to the body
does not, because the support was cut down as Ethan asked.

| Ring | Free arc, R18 | Free arc, R19 |
|---|---|---|
| Battery near | 122 degrees | 144 degrees |
| Battery far | 131 degrees | 136 degrees |
| XIAO near | 121 degrees | 121 degrees |
| XIAO far | 131 degrees | 131 degrees |

A longer free arc generally makes a clip softer. The independent review's relative
beam screen put the battery rings about 8% (near) and 3% (far) softer. That is a
comparison between revisions, not a force. Rod grip, slide and fatigue are
unverified. Support was not added back to chase a force figure that cannot be
established digitally. Ring width was not halved: that would save about 0.08 g and
the ring sections are retained while the surrounding support is reduced.

## Cell support

Cross bars and keel cover 47% of the bay at the cell plane, 271 mm2. The largest
open circle under the cell is 6.4 mm across. Nothing under the pouch is higher than
R18's floor plane. The cell reserve is stopped by the roof, floor, both walls
and the end stops; the door closes the remaining direction.

## Risks to check on the first print

1. **The open holders may flex while printing.** See the local free-span notes
   above. Watch the walls and bars through the upper half of the print.
2. **Upper-layer ladder behaviour.** The independent review counted 20 flat 0.43 mm
   outer-wall crossings above 20 mm that R18 did not have, on the slice before the
   corrections. Nothing in the audit starts over air, but watch them.
3. **Less bed contact.** First-layer area falls from 190.8 to 143.1 mm2 (battery)
   and from 178.2 to 164.3 mm2 (XIAO). Pads are unchanged in type. Moving the XIAO
   ties reduced removable-pad area from 324.94 to 294.54 mm2 (about 9%) versus
   the earlier R19 layout; the holder's own 164.28 mm2 contact area was unchanged
   by that correction. Actual adhesion is unverified.
4. **The battery end frame is 1.2 mm against R18's 2.0 mm plate**, and it carries
   six ties. Support it while removing pads. Tie release force is unmeasured.
5. **The cell or spacer could catch on a bar** while sliding in. Bars have a 0.4 mm
   lead-in, but sled behaviour is unmeasured.
6. **Pouch on bars.** Pressure and sag over the windows are unmeasured, including
   for the thinner spacers. The cell must still go in without force, and the pouch
   must not be squeezed.
7. **Rod clips.** The battery rings have longer free arcs than R18, as above.
8. **In-use strength of the thin sections, walls and bars is unmeasured**,
   especially if the wand is dropped or the holder is pulled off the rod.

R18's own limits still apply: bought cell thickness unmeasured, spacer choice by
hand, door and keeper forces are beam estimates only, and real solder, wire gauge
and the populated Sense underside are unmeasured.

Acceptance still required: clean removal without cracks, door and keeper operation,
cell held without rattle or squeeze, board, wire, USB and reset access, rod grip,
slide and durability, comfort and tip balance, and a weighed holder pair if the
real saving matters.

## Independent review and what was done

One independent review examined the design, followed by a scoped correction
review. Both primary and independent assessments accepted the final geometry
and slice as a digitally checked candidate. The correction review found no new
geometry or slice defect; its two reporting notes were corrected without changing
any model or G-code.

| Finding | What was done |
|---|---|
| F1. The Studio-export adapter's hash check was bound to R18 | Fixed: it now binds to R19's slice receipt. Matching R19 accepted, R18 rejected. No real Studio export has been checked |
| F2. XIAO cross bars lost about 1.1 mm of clearance under the solder pads | Fixed: outer bars lowered under the pad rows, with connected roots kept under the rails. New CAD and actual-bead regression checks on every row and both sides. The gap is 1.108 mm, not R18's 1.655 mm |
| F3. Two upper XIAO side ties landed on a 1.2 mm leg beside a window | Fixed: moved to print Y 15.8 on the solid band, with 4.4 mm of solid material behind them. Still six narrow ties, in four pads, which print separately |
| F4. Whole-body stiffness comparisons were not supported | Blanket comparisons removed, including an incorrect comparison added during correction. The free-span figure is R19-only and labelled a local screen |
| F5. "Clip arcs unchanged" overclaimed | Corrected: bore, slit and section match, free arcs differ and are listed. Grip and fatigue stay unverified |
| F6. "Thinnest island" reported an inscribed core, not a minimum thickness | Row renamed. Named thin sections and a neck scan added |
| F7. Smaller XIAO pad area was not disclosed | Added the 324.94 to 294.54 mm2 comparison beside adhesion risks and in the README; actual adhesion stays unverified |

The battery geometry did not change in these corrections. Review origin totals
are Codex 0, Opus 6, shared 1, with seven unique findings addressed. The apparent
hairline slits in the top-down XIAO drawing were probed: no gap of 0.01 mm or more
was found at the sampled layers, so they are plot artefacts rather than mesh cuts.
