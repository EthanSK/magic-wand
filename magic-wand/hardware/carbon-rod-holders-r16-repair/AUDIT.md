# R16 audit record

Implementation: one continuing Fable author session for all three repairs (2026-11-08), revised after the
independent Opus review, the parent's measurements and the second Opus review of the XIAO seat,
ligament, records and cooling. Final affected-artifact review: Claude Opus 5.5; parent source
review, record verification and publication are recorded below.
Every number below is from the exact files named here; none of it is a physical result. The R15
batch's physical failures (XIAO upper end in bits, carrier backplate snapped, uncomfortable lip,
rattling cell) override R15's earlier digital passes.

## Exact deliverables

| File | SHA-256 |
| --- | --- |
| `exports/R16-A1-mini-PETG.gcode.3mf` (sliced, all four parts, Bambu Studio 02.09.01.70 offline CLI) | `8afab7971a9e0b2be91e67ce96772cd254594bdf28cf83d7082942a21e580e45` |
| `exports/manifest.json` | `66637d2bd87fd880ed5248f52757d8a70ed3db7c7d2fcbf381fbf79a26ec375c` |
| `exports/geometry-checks.json` | `80d375d62b85a68d9ddd250023e23aeebe0cc057753451573225a6c4cd339ceb` |
| `exports/slice-clearances.json` | `219f5746e400857f2304b6b9328221800880b9cf2d4e20551176047cdf39a300` |
| `exports/arm-stiffness-screen.json` | `244924b0aa3e294dae299a576392962b09705a08d3c0bb286d877a8147ede464` |
| `exports/roundtrip-checks.json` | `276abc9c8d00c956cd877a438f935684e1e94c6732a175ac5c802f76f9ef92a3` |
| `exports/delivery-checks.json` | `2e8d176f323e60ee6397c3f882b42a666c09dcba1c19780c7a0274deac201baa` |

| Part (normal STL) | SHA-256 | CAD solid volume (mass at 1.27 g/cm³) | Print height |
| --- | --- | ---: | ---: |
| Key_Carrier | `2dab77208d18cde474d206ac90c9bb345d315751fa23769fd27e74df5eb4d2f0` | 4091 mm³ (5.20 g; R15 4249) | 35.2 mm |
| Battery_Holder | `d89953fbf16be4a342b78fb6f8129380b3adab91bda031b52e737f483d2018a1` | 2583 mm³ (3.28 g; R15 2037) | 35.6 mm |
| Battery_End_Gate | `480d0bbfa64c43e8516e5c840fd743f864267646a7281aadad27bea7d70ce9cc` | 130 mm³ (0.17 g) | 1.6 mm |
| XIAO_Rod_Holder | `00a21c72ca20ced4851caf6b496eb4d7ff5740cfc8cd6f362870de00ce58fb60` | 1380 mm³ (1.75 g; R15 777) | 28.4 mm |

Two different masses, kept apart: the CAD solid masses above (10.40 g for the four solids at the
stated 1.27 g/cm³ density) and the slicer's filament estimate for the plate, 9.50 g at 20 %
infill with 3 walls (178 layers, no slicer warnings). Effective settings read back from the
sliced archive: A1 mini 0.4 nozzle, Generic PETG @BBL A1M, 0.2 mm layers, 3 walls, 20 % infill,
255 / 70 C, 20 mm/s first layer, no support, no brim, elephant-foot compensation 0, fan 40-90 %,
overhang/bridge fan 90 % above 10 % overhang, minimum layer time 12 s. Override registration
restored after the CLI export.

The slicer was run offline with `--datadir` in task scratch and a process-private
`HOME`/`CFFIXED_USER_HOME`, because macOS window-state restoration for the app bundle had
blocked the headless process behind a modal after an earlier crash (a `layer_config_ranges.xml`
experiment; that file is not used). The user's preferences and saved state were not touched.

## Repairs after the second review (author run006)

1. **XIAO seat and stops, outline-aware.** The board is now the official plain outline,
   20.955 x 17.78 mm with R1.905 corners (parent's measurement of the plain STEP; the fitted
   header configuration is not derived from it and remains unknown), seated with its near end at
   Y 1.3 and its underside at Z 8.8. The earlier ledges at X 8.0-8.2 and the 45-degree tab from
   the rail were false positives against a rectangular board: with the real corners the near
   ledge lost all contact at +0.3 mm of axial play and the USB-plug push travelled 1.44 mm before
   meeting the tab. Smallest suitable change: each corner now has an L-shaped end cradle joined
   to its rail. Ledges are 1.0 mm thick from the rail in to |X| 7.3 under the first 1.0 mm (near)
   or 1.3 mm (far) of the board; the near ledge keeps its 45-degree lead from the rail (the lead
   runs under the board edge to Y 4.2), the far ledge and far stop run continuously from the bed.
   The near stop is a 45-degree face in plan tangent to the corner arc offset by 0.3 mm, because a
   flat face reaching |X| 7.3 at Y 1.0 cannot be printed at 45 degrees or less in this
   orientation; the two faces form a self-centring V. `verify16.py` sweeps the rounded outline
   against the final mesh: lateral play 0.31 mm to each rail; free travel by bisection 0.43 mm to
   the near V when centred and 0.12 mm when hard against a rail, 0.38 mm centred and 0.35 mm
   offset to the far stops (the far stops meet the corner arcs, not the straight end); every
   value agrees with the analytic model within 0.006 mm. Ledge directly under the board (the
   0.05 mm below the board plane, exact booleans) at the nominal seat and 25 poses over the full
   play: 2.07 mm² (near) and 1.31 mm² (far) per corner when seated nominally, minimum 0.91 mm² at
   each near corner and 0.72 mm² at each far corner over the play (screen 0.3 mm², at least
   0.4 mm of extent). Pushed 0.2 mm past its travel the centred board meets both near faces (0.13 mm³
   each) and both far faces (0.07 mm³ each); against a rail it meets one face of each pair first,
   as a V and a corner-arc contact must. New working spaces: the rounded board, the union of nine
   reachable poses 0.1 mm inside the rails and stops, the USB plug body beyond the holder, and
   top-side pad access (board footprint + 0.25 mm, 2.5 mm up) all have zero bead violations in
   the actual G-code and zero final-mesh intersection; the 1.5 mm keepout under the board centre
   (|X| <= 4) is distinct from every contact feature and untouched. Surviving printed material,
   complete layer scans of the final slice: near ledges 0.825 of 0.855 mm² in the 0.45 mm under
   the board plane over the 4 layers under the board (96.5 %), far ledges 0.815-0.822 mm² over 6
   layers (95-96 %), V tabs 0.963 of 0.992 mm² over 11 layers (97 %), far blocks 2.02-2.04 of
   2.09 mm² over 4 layers (97-98 %); ledge root into the rail 3.9 mm section with 5 tracks. On
   the stated castellation assumption (7 pads per edge at 2.54 mm pitch, centred) the near ledge
   lead tip alone reaches the first pad: the mean area within 0.05 mm of the board plane is
   0.027 mm² per side in the CAD, about 0.03 mm² in the printed beads (at most 0.17 mm² over
   the independently inspected DXF land extent). The previous 1.005 mm³ value was material
   within 1 mm below all 14 assumed pads, not contact beneath each first pad. Per-side volumes
   in that deeper band are 0.186 / 0.021 / 0.231 / 0.065 mm³ for pads 0 / 1 / 3 / 4; the latter
   three lie 0.54-0.76 mm below the board. `verify16.py` now records every pad in both depth
   bands. Solder the wires on the top pads and keep contact undersides flat. Between the
   cradles, the actual minimum clearance is 0.536 mm at the edge struts and 1.84 mm under
   |X| <= 4; the cradles intentionally contact the board. The rails at X 9.2 already demand
   flush castellations.
   Upward USB, the external wire route, both rod fits, the struts, keel and gusset reinforcement
   and the spring arms are unchanged. The parent's suggested numbers were checked rather than
   copied: ledge inner |X| 7.3 (suggested ~7.4) under 1.0-1.3 mm of the ends (suggested within
   1 mm; the far ledge takes 1.3 mm because it has no print lead to worry about and stays
   0.6 mm clear of the assumed pads); the near-end gap is 0.3 mm normal to the V faces, which is
   0.42 mm of axial travel, not a 0.3 mm flat gap.
2. **Lightening-window ligament.** The turned upper-left key's window is mirrored, so its flat
   edge faced the side-post hole's teardrop peak at 0.79 mm. That edge alone is set back 0.45 mm
   (window Y -7.0 to -2.65 in the key frame, 11.4 mm² instead of 12.8 mm²); no hole, key position,
   pitch, row spacing or teardrop direction changed. `verify16.py` measures every key's actual
   window-to-hole distances on the final section through the thinned backplate: 1.204 mm on the
   four unturned keys (window point to the side-post hole circle) and 1.236 mm on the turned key
   (set-back edge to the teardrop peak); all other holes are at least 2.24 mm away. The lower-row
   layer scan through the bays is unchanged (63.7 mm² minimum, 93 % printed).
3. **Record corrections.** `parameters.json` `arm_bonding` now states the measured 46-47 degrees
   (skirted) and 56 degrees (plain) and the resulting free arcs of 121-122 and 131 degrees; the
   skirt description no longer calls the free arc unchanged. The all-key ligament claim is
   replaced by the per-key measurements above. Board support and travel claims use the outline
   sweep above. The header caveat appears once, in `parameters.json`, and names the rails, end
   bars, near gussets, diagonal struts and cradles. Statements that a toolpath "prints without
   sag" are gone: the teardrop peaks make the hole roofs 45-degree overhangs instead of flat
   bridges, and whether anything sags is a physical result. CAD solid mass and the slicer's
   filament estimate are recorded separately above. Force, retention, comfort, fatigue, the cap
   size, the cell and the header configuration remain unverified.
4. **Roof cooling.** `band_speeds` now also totals extruded path length per feature and fan level.
   In the carrier's slow bands the paths the slicer classifies as overhang wall (207 mm) and
   bridge (100 mm) print at 90 % fan (M106 S229); gap fill (353 mm), inner walls (1564 mm), outer
   walls (1030 mm) and solid infill (465 mm) print at the profile's 40 % minimum (S102), because
   these layers run longer than the filament profile's 30 s `fan_cooling_layer_time`; the battery
   bands show the same pattern (86 mm at 90 %, 94 mm of gap fill at 40 %). The recipe text now
   says so instead of implying that the overhang/bridge fan covers the bands. A proportionate,
   portable, local improvement was evaluated by slicing an experiment copy outside `exports/`
   with 5 wall loops inside the band modifiers only (`project16.py --out-dir --band-wall-loops 5`):
   it removed the bridges (100 -> 0 mm carrier, 47 -> 0 mm battery), turned them into overhang
   walls (207 -> 253 mm) and inner walls at 40 %, and raised the carrier's 40 % gap fill from 353
   to 512 mm. Rejected; the delivered recipe is unchanged. Fan levels are filament-profile
   settings and no global cooling change was made unasked; `fan_min_speed` is the lever if the
   roofs droop. The inspect-and-trim step stays. Digital evidence does not predict PETG droop.
5. **Assembly order.** Recorded in `parameters.json` (`bay.assembly_order`) and the README: fit,
   wire and Kapton-tape every socket while the carrier is off the rod; press each switch in from
   above while supporting its socket from below; slide the carrier onto the rod last. The
   lower-middle socket's underside sits 1.6 mm above the 8 mm rod surface and 1.4 mm above the
   8.4 mm rigid corridor (`geometry-checks.json`); the pins are not structural. Kapton/board tape
   were already authorised; no new approval question.
6. **Regenerated receipts and the final-project roundtrip.** All sources, meshes, images, the
   layout, the actual slice, the audit, the arm screen and the guard receipts were regenerated
   from the current sources, and the final slice (not the earlier `46a0...` project) was
   inspected layer by layer at the cradles. `roundtrip16.py` reloads the exact delivered
   `R16-A1-mini-PETG.gcode.3mf` (never the layout) in the offline CLI with a process-private
   `HOME`/`CFFIXED_USER_HOME`, `--datadir` and `TMPDIR` in task scratch, re-slices it into
   scratch and checks: the same four part meshes (vertex arrays equal), the same plate settings,
   the same modifier parts with the same settings and the same effective placement (modifier
   mesh through component and build transforms: world Z 15.7-17.1 and 33.5-35.5 mm on the
   carrier, 33.3-34.7 mm on the battery holder, in the layout, the delivered and the re-sliced
   archive alike; the CLI rewrites the `matrix` metadata as a composite on export, which is
   recorded, not compared), and the same `slice16` audit on the re-sliced G-code against the
   registered normal STLs: zero working-space violations, no floating or missing layer starts,
   the same feature list, identical band speeds and fan levels, identical ring bonding and
   tracks, path-scan minima and band path lengths within 2 %. The re-sliced G-code is not
   byte-identical (the CLI rewrites mesh floats; path sample counts differ by 4 of 376 000 and
   one gap-fill total by 0.1 mm), so the receipt records equivalence, not identity. GUI
   reopening is not available in this offline headless environment; the CLI reload of the
   delivered archive is the roundtrip performed. Re-sliced artifacts stay in task scratch; their
   hashes are in `roundtrip-checks.json`.

## Repairs after the first review (author runs004/005), still in force

1. **Bay-roof and gate-cap print recipe.** Bambu modifier parts (boxes over each part's
   footprint) at print heights 16.0-16.8 and 33.8-35.2 mm on the carrier and 33.6-34.4 mm on the
   battery holder, each extended 0.3 mm so every layer whose middle lies in the band is covered.
   Requested: walls 15, gap fill 12, solid infill 20, bridges 12, overhang walls 8-15 mm/s.
   Verified in the actual G-code (`band_recipe_actual`, XY printing moves only): carrier
   16.2-16.8 mm walls 8-15, gap fill 12, solid infill 20, bridges 12, overhang walls 10-12 mm/s;
   carrier 34.0-35.2 mm walls 8-15, gap fill 12, overhang walls 12 mm/s; battery 33.8-34.4 mm
   walls 10-15, gap fill 12, bridges 12, overhang walls 10-12 mm/s. Fan as in finding 4 above.
   Reference layers at 5-6 mm print the same features at 35 mm/s with 89-90 % fan. The reviewed
   baseline printed these roofs at 98-106 mm/s walls and 62 mm/s gap fill.
2. **XIAO board support.** Superseded by run006 finding 1. The 1.6 mm diagonal struts (rail at
   Y 14 to keel at Y 6, about 47 degrees in print) remain; the complete layer scan of the
   rails/keel/strut region gives a minimum section of 17.2 mm² (93 % printed) over 118 layers.
   **Tape across the board and rails is a required prototype step**; nothing printed holds the
   board down.
3. **Socket retention.** No printed hooks (they would be thin walls loaded across layers). **A
   polyimide (Kapton) strip across each socket underside and its wires onto the backplate is a
   required prototype step**: it holds the socket on its bosses while the switch is pushed in,
   insulates the solder from the carbon rod and relieves wire strain. The switch pins locate but
   do not retain. A 0.4 mm tape zone under every socket body and its legs is a working space with
   zero bead violations; the 6 mm straight insertion from below and the socket bodies are clear
   for all five keys.
4. **Record corrections.** Bay-roof heights are 16.2-16.6 mm (upper) and 34.0-34.4 mm (lower);
   the battery patch is the guide end cap over the slot (about 2.4 x 6.2 mm per side, held by the
   outer wall and bottom ledge, inner top corner chamfered 1 mm). Ring arms: the crown is bonded
   to the saddle down to 47 degrees above the equator on the carrier mid ring and the battery
   near ring, 46 degrees on the XIAO near ring (radial sections); the plain far rings are bonded
   to 56 degrees by their end bars/plate. `arm_stiffness16.py` (stated curved-beam assumptions,
   reproducible) screens the skirted arms at about 2.3x (3.6 mm bands) and 3.0x (2.4 mm XIAO
   band) the stiffness of a plain arm with the same root; the far rings are within 5 % of an
   R15-like arm. Real slide force, fatigue and comfort are unmeasured.
5. **Direct backing.** `band_start_backing` takes the first true band layer by its layer middle
   and credits only beads directly under the current footprint (no 0.25 mm expansion): carrier
   mid ring 95.5 % (first band top Y 12.5), battery near ring 93.9 % (Y -14.4), XIAO near ring
   94.5 % (Y -2.8); the 90 % screen is unchanged.
6. **Section plane and complete scans.** `layer_section` and `path_scan` take the layer middle at
   Y + 0.1. Complete intervening-layer scans: saddle and crown over 87 layers, minimum 26.2 mm²
   (97 % printed); inter-row strip over 16 layers, minimum 131 mm² (78 %); shoulder root regions
   over 37 layers each, minimum 7.9 / 8.1 mm² (84 %); lower row through the bays over 75 layers,
   minimum 63.7 mm² (93 %); XIAO rails/keel/struts over 118 layers, minimum 17.2 mm² (93 %);
   battery lattice over 141 layers, minimum 40.5 mm² (95 %); the eight cradle scans in run006
   finding 1. Every backplate hole has a 45-degree peak toward the finger side so its roof is
   printed as 45-degree overhangs rather than a flat bridge.
7. **Cell loading.** Non-lead end first from the gate end; the leads trail and leave through the
   13 mm centre between the gate stubs. The guide end cap's inner top corner is chamfered 1 mm
   where the grab bar passes and its band is slowed (finding 1). Nominal play against the
   manufacturer maximum pack: 0.7 / 0.5 / 0.6 mm; nothing touches a seated cell.

## Working spaces: every bead type

All working spaces across the four parts have zero bead violations (model walls, infill, gap
fill, bridges; the G-code has no support, brim or skirt features): rod bores (7.9 mm clip
diameter) and both clip gaps of every holder; the five switches, nominal and maximum sockets,
31-pose straight socket insertions from 6 mm below, tape zones, plate openings, clip reliefs and
cap-travel envelopes; the external wire bus; the cell reserve, 45 mm cell loading route,
61-pose gate removal route, both gate slots and the lead exit; the rounded board, its nine-pose
travel union, the USB receptacle and plug body, top-side pad access, the external wire route
and the 1.5 mm clearance band under the board centre. Final-mesh checks agree: worst
intersection < 0.002 mm³; cap envelope gap 0.40 mm (screen 0.40; cap size still inferred).

## Layer starts against actual previous beads

The automated layer-start scan reports no floating or missing printed components. Every broad
partially unbacked row has a
class and the slicer's actual features inside the patch:

| Part | Layer top | Area | Class | Actual features (speeds in the slow band) |
| --- | ---: | ---: | --- | --- |
| Key_Carrier | 1.0 mm | 2.4 mm² | internal shell transition inside a solid region | Floating vertical shell |
| Key_Carrier | 16.4 mm (x2) | 27.9 / 26.6 mm² | upper bay roofs: 14.1 + 15.6 mm spans | Bridge 12, Overhang wall 10-12, walls 8-15 mm/s |
| Key_Carrier | 18.0 mm | 2.0 mm² | 45-degree shoulder face | Outer wall |
| Key_Carrier | 18.8 / 19.0 mm (x3) | 2.1-2.3 mm² | internal shell transitions | Floating vertical shell |
| Key_Carrier | 34.2 mm (x3) | 27.9 mm² each | lower bay roofs at the print top | Overhang wall 12, walls 8-15, gap fill 12 mm/s |
| Battery_Holder | 1.2 mm | 2.0 mm² | internal shell transition | Floating vertical shell, sparse infill |
| Battery_Holder | 34.0 mm (x2) | 12.2 / 12.3 mm² | guide end cap over the slot, corner chamfered | Bridge 12, Overhang wall 10-12 mm/s |
| XIAO_Rod_Holder, Gate | - | - | no rows | - |

The five bay roofs are still 14-16 mm spans printed across air with 0.15-0.2 mm of housing
clearance: inspect every opening edge against a bare switch housing and trim before fitting.

The table covers the broad rows reported by the checker. Independent inspection also found a
small XIAO near-gusset root start at print height 16.8 mm: about 1 mm² per side, 1.37 mm from
previous support, 4.2 mm of outer wall at 10-16 mm/s and 90 % fan. This short bridge remains a
test-print inspection point at the gusset roots. The printed near V has about 0.35 mm axial
travel when centred, 0.20 mm at a 0.15 mm lateral offset, and 0.04 mm against a rail, due to
0.2 mm layer steps; far travel is 0.35-0.37 mm. These bead-derived values differ from the
explicitly labelled CAD travel above; real tolerance and fit remain unverified.

## Regression for the R15 failure

- Every skirted band's first true layer rests directly on previous beads (95.5 / 93.9 / 94.5 %,
  screen 90 %, no lateral credit; R15 XIAO far clip face 0.9 %).
- Lead-in skirts: 72 radial rays per ring at least 1 mm inside the sloped edge, every ray
  >= 1.01 mm of exported wall and >= 2 surviving tracks.
- Every ring keeps >= 1.0 mm exported wall at seven angles and >= 3 radial tracks at -55 / 90 /
  235 degrees in its midplane layer.
- Fixed features (exported section / actual tracks): carrier saddle neck 4.5 mm / 8; plate lip
  1.25 / 3; outer wall 1.2 / 3; thinned backplate 1.2 / 3. Battery chord 1.6 / 4; spine 5.4 / 4;
  guide walls 4.0 / 10 and 1.6 / 4; chevron bar 2.3 / 4. Gate wedge neck 1.5 / 2; grab bar
  1.9 / 5; stubs 2.5 / 7. XIAO rail 2.0 / 5; keel 3.0 / 5; end bars 2.6 / 7; ledge root into
  the rail 3.9 / 5. Screening sections, not breaking forces.
- The XIAO near cradles are the top of that print (21-24 mm): the final slice shows the ledge
  growing from the rail at 45 degrees, then the V tab growing at 45 degrees, as walls with gap
  fill, every layer resting on the previous one (path scans above).

## Design changes versus R15 that need Ethan's awareness

1. Carrier rings sit between the rows and at the tip end; none under the index finger.
2. The upper-left switch is rotated half a turn (socket outboard); electrically identical.
3. Skirted clip arms are stiffer than R15's (screen about 2.3-3x; unmeasured force). The lead
   angle (`arrow_ring.lead_angle_degrees`) is the lever if the slide feel needs changing.
4. Required prototype steps: Kapton under each socket, fitted with the carrier off the rod;
   tape over the XIAO board; top-side soldering of the board wires.
5. Battery holder 0.7 g and XIAO holder 0.8 g heavier than R15 (CAD solid).

## Physical gates still open

Mounted cap size and play (0.4 mm residual gap assumed); actual cell dimensions and lead/PCM end
bumps; the fitted Sense board's header configuration and its real pad positions; PETG sag on the
five bay roofs and the gate end caps even at the slow speeds and 40 % base fan; ring slide force
with the skirted arms; gate wedge feel; comfort of the rounded nose; the real seat of the board
on four 0.7-0.9 mm² corner contacts under tape; strength and fatigue of every joint. Stop on
whitening, cracks or excessive force. Further physical iterations should be expected.


## Final independent qualification

Claude Opus 5.5 independently inspected the exact `8afab797...` project, the changed normal and
assembly meshes, contact and travel through actual printed beads, rotated key ligaments, pad
and USB keepouts, cooling, local modifier placement and the saved CLI roundtrip evidence.
All 41 frozen mechanical files matched at the end of that pass. No new functional, fit or
print defect was confirmed; the per-pad and underside-clearance record corrections were then
measured on the unchanged delivered mesh and verified by the parent. Unchanged battery, gate
and ring coverage comes from the earlier independent passes.

The parent checked the regenerated interactive viewer and reviewed its source and resource
lifetime. A full root repository check passed, including 317 Wand tests, 17 Control Stones
tests, four shared tests, privacy and generated/vendor/tutorial checks. The final handoff is a
conditional test prototype. GUI reopen/save/reopen is untested; the live Studio project and
file picker were preserved. After any GUI re-save, inspect speeds at layers 16.4 and 34.2 mm.
The physical component and trial gates above still apply; no real print was started here.
