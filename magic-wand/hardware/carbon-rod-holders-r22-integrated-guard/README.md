# R22: guard built into the key holder, curved shoulders, full-harness cable clip, every keeper reprinted

R22 responds to Ethan's comments on the R20 print. R16 to R21 and their exports are unchanged.

**Status: the R22 PETG job finished.** The key holder printed and its thin guard runners
snapped under finger pressure. The toolpaths include both battery doors.
[Fit observations](../../LEARNINGS.md#2026-11-10--identify-r22-retainers-by-their-fitted-parts)
record the possible mix-up with the XIAO holder and the later good cradle and pin fit.

[Open the assembly guide](../carbon-rod-holders/assembly/?version=r22) and choose a component in the dropdown.

## What is on the plate

| Part | What it is | CAD solid |
|---|---|---|
| `Key_Carrier` | **New.** Thin guard runners built in, curved shoulders, every top edge rounded. Replaces the R20 key holder **and** the separate R20 `Finger_Guard`. | 5.66 g (R20 holder 5.08 g + guard 1.66 g = 6.74 g) |
| `Battery_Holder` | **New.** The R20 holder plus a longer lead-in at the top of the door slots. Takes either door. | 2.47 g |
| `Battery_End_Door` | R19 standard door, byte-identical. Fits the R19, R20 and R22 battery holders. **Try this first.** | 0.34 g |
| `Battery_End_Door_Easy_Trial` | Trial door. The centre catch tooth is 0.15 mm shallower, so it hooks 0.25 mm instead of 0.4 mm. Easier in and out; holds less firmly. | 0.34 g |
| `XIAO_Rod_Holder` | R20 body, byte-identical. Not replaced (see below). | 2.07 g |
| `XIAO_Near_Keeper` | **R19 keeper, original-compatible.** Fits the R19 and R20 XIAO holders. R20 never printed one, which is likely why the board was not held. | 0.28 g |
| `Battery_Spacer_0p4mm/0p6mm/0p8mm` | R19 cell spacers, reprinted. | 0.27 / 0.41 / 0.54 g |
| `Cable_Clip_12_Wire` | **New.** Figure-eight clip sized for the full harness. Supersedes the R21 4 mm clip. | 0.17 g |

The plate includes the matching battery door and XIAO keeper, the trial door and three optional spacers.
The R20 `Finger_Guard` still fits the R16 and R20 key holders. The table lists solid CAD masses at 1.27 g/cm³.
The slicer's full-plate estimate, including the wipe tower, is in `exports/R22-A1-mini-PETG-print-checks.json`.

## Key holder

- **Guard.** Six thin runners (1.6 × 1.4 mm rounded section, 0.6 mm corner radius) are now part of the key holder. Each leaves the
  underside at 45° behind the lower sockets, runs forward 0.8 to 2.2 mm above the rod axis, under the socket band,
  and curves back up into the underside just before the 2.4 mm nose round.
  - No free ends, rings, keel or plate. Together the runners weigh 0.33 g.
  - The middle channel between the inner runners (X −16.4 to 12.1) stays open for index-finger contact with the rod.
  - Rigid fingertip probes of radius 5 to 8 mm, pressed straight up, are now blocked from the outer terminals of the
    lower-left and lower-right sockets. Without runners they reached those terminals.
  - The inner terminals near the rod are reachable as before: lower-left inner terminal, 7/9 to 3/9 of probe points
    reach it at R5 and R6, none at R7 and above. On the upper row, key 3's outer terminal is partly covered and key 4's
    outer terminal is open.
  - Probe sizes are stated assumptions, not hand measurements.
  - **Strength is the runners' weak point.** Each runner runs along the print's stacking direction, so a finger
    pushing up bends it across layer lines. Stated-assumption screen: a beam fixed at both ends, 18–25 mm between its
    bonds, I = 1.6 × 1.4³ / 12 ≈ 0.37 mm⁴, PETG interlayer strength 25–35 MPa. It reaches that stress at roughly
    4–10 N at midspan per runner. A firm fingertip on one runner is in that range: treat the runners as a trial part.
    Each runner prints as a thin 1.6 × 1.4 mm island until it rejoins the holder. The actual slice checks backing and
    the deposited material in each free span.
- **Socket loading with the sockets already soldered.** All five routes carry R20's stated solder-and-wire allowance on
  both terminals. Every route ends seated with zero rigid overlap against the exported holder.
  - Lower left and lower right: hold the socket about 2 mm below its seat and slide it in sideways from the outer edge,
    above the runners, wires trailing outward. Then lift it onto its two bosses. There is 0.35 mm of extra room below
    that slide.
  - Middle: straight up, as before.
  - Upper left and upper right: from below, but keep the socket about 1 mm away from the rod until it is 2 mm below its
    seat, then move it in and press it up. Pushed straight up, the stated solder allowance on the inner terminal would
    pass 0.4 mm into the rod ring arm. This also applies to the R16 and R20 holders, which share that geometry.
  - A tapered relief beside the upper-left socket lets the variable-width wall paths clear its inside corner.
  - Tape each socket as on R16. Press the tape ends onto the backplate with a flat tool. Keep pressure off the runners.
- **Shoulders.** The straight 45° shoulders between the rows are now a smooth cosine curve from the lower side edge to
  the upper side edge, tangent at both ends. Its steepest point is 44.4°, so every print layer still grows at 45° or
  less. Every top plan edge has a 0.6 mm round; the 2.4 mm round under the nose is unchanged.
- **Row spacing is unchanged at 17.8 mm.** Moving the upper row closer conflicts with the reference caps used by every
  holder (17.5 × 16.6 mm, with 0.4 mm play each). The table is in `geometry-checks.json`:

  | Upper row closer by | Cap gap | After 0.4 mm play per cap | R16 screen (≥ 0.4 mm) |
  |---|---|---|---|
  | 0 mm | 1.2 mm | 0.4 mm | passes |
  | 0.4 mm | 0.8 mm | 0.0 mm | fails |
  | 0.8 mm (17.0 mm, Choc pitch) | 0.4 mm | −0.4 mm | fails |
  | 1.0 mm | 0.2 mm | −0.6 mm | fails |

  The safest improvement under that screen is 0 mm. If the actual caps sit tighter than 0.4 mm of play, up to 0.8 mm
  is geometrically possible: the sockets would still keep 0.4 mm apart. That needs the mounted caps measured first.
  The change is one parameter (`row_shift_mm`).

## Battery

Slide the battery in end-first. Push its door straight down into the two end slots.
The XIAO keeper is a different part with small ears and slides along the XIAO holder.

The hard part of fitting the door is its centre catch tooth (X ±1.8 mm) riding over the 0.4 mm lip at the slot top,
plus the door plate entering the two side slots.
- R22 replaces the lip's 0.35 mm 45° chamfer with a lead-in 0.45 mm deep over the top 0.6 mm of the cell-side slot face.
  The tooth is pushed aside more gradually, and both side slots get a wider mouth.
- The lead-in stops 0.15 mm above the hook face under the lip, so the hold and the seated fit are unchanged.
- Rigid peak overlap while the door goes in: 0.82 mm³ (R20) → 0.70 mm³ (R22), and 0.36 mm³ with the trial door.
- The cell bay, teeth, spacers and floor are R20's. Residual pouch movement is a separate matter, handled by the spacers.

## XIAO

The R20 body is kept, because the board already sits almost flush and the R19 keeper was missing from the R20 plate.
Reprint the keeper and fit it: lay the board in (tilt the near end up, slide the USB end under the far fingers, lower),
then check that the board sits flat before sliding the keeper over the near end. If it rocks or sits high, stop and check where the solder is catching.

The two prongs keep the board down. The side ears ride in the grooves, and
the tooth under the spring tab catches the holder ridge. [Watch the side
section](../carbon-rod-holders/assembly/?version=r22&component=xiao_latch) to
see the click and release. The spring is joined to the rest of the keeper
outside the slice. Pull evenly on the side ears to remove it. The R22 toolpaths
include all five tooth layers. Physical catch engagement still needs checking.

Clearance under the board in the R20 body:
- 80% of the board area has at least 2 mm, and 47% has at least 3 mm.
- Half the pad band (outer 2 mm of each long edge) has at least 2 mm.
- The minimum is 0.34 mm, at the near ledges and leads that carry the board.

If underside solder lifts the board so the keeper cannot slide over it, a relief body is the next step. The clearance
map in `geometry-checks.json` gives its basis. No heavy shroud is added; stickers will cover the label.

## Cable clip (full harness)

Sized for 12 conductors at a conservative stated 1.5 mm insulation diameter. That covers 5 key signals, up to 5
separate key returns (switches go to GND with internal pull-ups, `wand_sense.ino` lines 10–14), and battery + and −.
- Layout: 9 wires on a 2.3 mm radius plus 3 on a 0.866 mm radius, giving a 3.05 mm envelope inside a 7.0 mm bore.
  Every wire is at least 0.45 mm from the plastic.
- Wires go in one at a time through a 1.7 mm rounded slit, which is 0.2 mm wider than a wire, so the arms need not flex.
- Snip off both print pads. Slide the rod loop on from a free end of the rod before feeding the wires.
- Actual wire sizes and the clip's grip on the rod still need a fit check.

## Questions from the R20 print

- **The "little thing sticking out" on the R20 guard** was its prop tab: a small bearing pad under the key holder's
  nose that braced the guard. It was not a latch. R22 has no separate guard, so it is gone.
- **The "random thing going up"** is the Smooth-timelapse wipe tower at x 120 / y 20. It catches nozzle ooze between
  photos and is discarded after printing. The R22 plate keeps it, apart from the parts.

## Files

- `holder22.py`: all R22 geometry and exports.
- `parameters.json`: every source dimension, including runners, routes, lead-in, trial door and clip.
- `verify22.py`: produces `exports/geometry-checks.json`.
- `assembly22.py`: produces `exports/assembly-guide.json` (schema 2, four modules with checked routes), plus reference
  meshes in `exports/guide/`.
- `test_holder22.py`: fast checks on the recorded results.
- `project22.py`, `anchors22.py`, `slice22.py`, `roundtrip22.py`: plate, pads and slicing (parent-owned).
- `AUDIT.md`: what was checked and what remains physical.

The print uses the A1 mini 0.4 mm nozzle, Generic PETG at 255 °C nozzle and 70 °C bed, 0.2 mm layers, 3 walls,
20% infill and 0.6 mm Normal lift. Variable-width walls (Arachne) fill the narrow beams on the key holder.
The plate uses Smooth timelapse with its separate wipe tower. Designed tear-off pads sit on the key holder,
battery holder, XIAO holder and clip. The other parts print flat without helpers.
