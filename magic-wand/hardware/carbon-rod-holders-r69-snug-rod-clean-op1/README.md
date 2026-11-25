# R69 snug rod grip, short hinge, low retainer and a clean OP1 seat

R69 answers the first fitted R68 print. Three parts change: the key holder, the touch paddle and the OP1 retainer. The battery rail, key positions, hinge pins, centre clip, post bar, board clips and backing strips are R68's. R69 passes the two native-slice checks described below. The assembled print is now a good fitted reference overall, with the limitations below.

[View the assembly](../carbon-rod-holders/assembly/?version=r69&component=keys&view=pin_hinge) · [Holder](design69.py) · [Paddle and retainer](hinge69.py) · [CAD checks](checks69.py) · [Slice audit](audit69.py) · [Kit plate](kit69.py) · [Guide](guide69.py)

## Fitted reference — 25 November 2026

Preserve R69 as the good physically assembled baseline. The hinge and click feel much better, the battery slides in well, and the overall design was accepted. This is qualified user feedback, not a measurement of every clearance or proof of strength.

Remaining observations: the touch board has some play on its locating posts; removing the sacrificial base beside the battery rail can tear a small hole from the carrier; and fitting the black key sockets is fiddly but was achieved. The thin-looking paddle-arm/barrel junction should be assessed for reinforcement. A shorter battery rail and closer key rows are requested for the next iteration, preserving the improved click.

The manufacturer specifies **two nominal 3 mm mounting holes** on the [DFR0030 board](https://www.dfrobot.com/product-78.html/); no finished-hole tolerance is stated. R69 retains the earlier shaped posts (2.25 × 2.52 mm), deliberately narrower to accommodate uncertain hole spacing. Their fit is distinct from the hinge pin fit. A closer future fit must account for board pitch and printed PETG tolerances without forcing the board.

The two hinge rods are alternative fits, not two required axles. The flat socket backing strips are optional temporary tools for supporting the black sockets while pressing the switches; they are not battery covers. The OP1 sliding retainer and touch-board two-post bar remain functional parts.

For key assembly, the current guide seats and secures the prewired black sockets first, then presses in the switches from above while backing each socket from below. Keep pressure off the finger-guard beams. Remove temporary backing strips afterward.

## What changed and why

### 1. Hinge: closer to the touch board, no rear web

**What the flat, pointed piece was.** It was a web on the paddle behind the hinge barrel. The paddle prints upside down with its board seat on the bed. R64 lowered the barrel so the three touch leads can leave the plug straight over it, which left the barrel starting 3.3 mm above the bed. The web carried those first layers down to the bed. It was a print aid that looked like a wire rest.

**What replaces it.** Both side beams now run at full height into a post on the barrel, and the barrel top between the posts is flat. The first barrel layers bridge 7.65 mm between the two posts. The right beam used to be a low strip; it is now the mirror of the left one, which also stiffens that side of the paddle.

**Distances from the top edge of the touch board:**

| To | R68 | R69 |
| --- | --- | --- |
| Front of the hinge barrel | 4.07 mm | 2.77 mm |
| Pin centre | 7.37 mm | 6.07 mm |
| Rear end of the paddle | 11.35 mm | 9.37 mm |
| Rear of the bearing blocks | 10.42 mm | 9.12 mm |
| Rear of the modelled leads | 9.20 mm | 9.92 mm |

The pin line moved 1.3 mm. The overall holder length remains unchanged because its rear extent carries the battery rail and rod platform. It cannot move further with this plug: the barrel now clears the mated plug by 0.59 mm. A barrel at board height would need a gap in front of it for the leads to turn in, which puts the hinge further back, so the lowered barrel stays.

**Lead route.** The three leads rise over the barrel between the two posts and turn right behind the right post. They can also lie over the right beam.

**The two triangular blocks behind the bearings stay, shorter.** The holder prints standing on its rear face. Each bearing block grows from a 45° buttress; without it the block would start in mid-air. The buttresses now end 3.3 mm before the rear face instead of running to it. Removing them needs the holder to end right behind the hinge. That would shorten the battery rail by about 8 mm, so it is not done here.

### 2. White plug: the guard arm and a rib stood in its path

- **Guard arm.** The right finger guard's top arm ran from the deck in toward the rod and only then out to the guard. That inward bow stood beside the opening. The arm now leaves its root downward and runs straight out, bowed away from the rod. Below the deck, the room on the guard side of the plug's path rises from 3.44–6.02 mm to 6.5–8.4 mm.
- **Rib root.** A 33 mm³ rib root hung from the right side of the front rod saddle, touching nothing else. It is the twin of the left stubs R67 removed, and it stood on the rod side of the same path. It is removed.
- **Window.** One rounded window, 10.30 × 9.8 mm (R53: 8.28 × 7.32 mm), with a 7 mm rounded mouth for the lead and a lead-in on its underside edge. The wider mouth removes the old triangular corners where the plug pocket met the wire opening; the outer board stops and both retainer rails stay.
- **Result in CAD.** The route is selected for hand access first, then plug clearance. The largest plug that passes is the estimate plus 1.00 mm on every side (R68: plus 0.27 mm). The plug rises beside the rod sleeve at X 8.0, Y 12.5 with its wide side along the rod.

The plug size is still a photo estimate of 3.1 × 6.2 × 3.65 mm, not a measurement. The printed R68 passed it only with force.

**Why R68's checks passed.** They tested one fixed line for the estimated plug with 0.75 mm round it, and a turn in free air above the holder. They did not ask how much room a hand has below the deck or how much larger than the estimate the real plug may be. R69's checks report both, beside the R68 values.

### 3. Retainer: low posts, longer paddle legs

**Geometric cause reproduced in CAD.** The retainer's two towers stood 16.5 mm high, 1.2 mm under the paddle plate. A full press takes 0.94 mm of that at the towers. With the hinge end lifting in its open bearings and the paddle rolled or shifted, the plate reaches the towers. The check reproduces this on the R68 parts.

**Change.** The hook that limits paddle lift moves down. The paddle gets two legs with a foot at 12.9–14.35 mm. The retainer gets two posts 15.05 mm high, and its plate is cut back under the legs. This explains one way the fitted click can be obstructed; it does not isolate every physical jam.

| | R68 | R69 |
| --- | --- | --- |
| Room over each post at rest | 1.20 mm | 2.65 mm |
| Far-end press, hinge lifted, rolled and shifted | touches the retainer | 0.245 mm clear |
| Lip over the paddle's hook | 0 mm | 0.5 mm each side |
| Paddle lift before the hook stops it | 1.50° | 1.13° |

The click itself is unchanged: contact at 0.003°, case stop at 1.31°, 0.82 mm of plunger travel. The contact bar is not lengthened. It already stops on the switch case with the plunger flush, so a longer bar would not add travel.

**Strength.** The low posts extend across the complete plate cutout, with a 0.28 mm floor. The weakest CAD section is 4.266 mm² on each side, compared with 4.320 mm² before. This restores the load path without putting a high plate back under the moving hook. The native bead-envelope section is at least 3.76 mm², compared with 4.31 mm² before. Its taller outer stem carries the load across the whole notch. These section measurements do not establish printed strength or fatigue.

**Seating.** The retainer still slides in under the two rails and latches on the left. The right rail covers 7.0 mm of its tine and the left 15.7 mm. The right rail cannot run further back: its wall would stand in the upper-right keycap's travel.

### 4. Rod grip: the earlier rings are back

R58, R60, R61 and R62 share one bore from the front face to Y 32.65: a 7.8 mm split ring, a saddle and an 8.0 mm ring. R58 is the fitted reference that gripped. R63 bored everything to 8.55 mm and added a loose wedge collet, and the grip has felt loose since.

R69 restores that bore exactly, ring for ring. Behind it the R63 bore and rear funnel stay, so the bed-face end is 9.9 mm wide and cannot pinch the rod.

| Zone | R62 | R68 | R69 |
| --- | --- | --- | --- |
| Front split ring, Y 9.25–19.75 | 7.80 mm | 8.55 mm | 7.80 mm |
| Rear ring, Y 29.25–31.75 | 8.00 mm | 8.55 mm | 8.00 mm |
| Behind the rings, Y 33–37 | 8.36 mm | 8.55 mm | 8.55 mm |
| Bed-face end | 8.36 mm | 9.90 mm | 9.90 mm |

**About R62.** The printed R62 would not slide onto the rod and broke. Its two rings are nominally the same as R58's. What R62 added was an 11 mm tail at 8.36 mm ending on the bed face, where the first layers print tight. R69 does not have that tail. The physical cause is unconfirmed; the fitted report also described warping. R69 keeps the restored rings separate from the wide bed-face funnel.

**The loose rod grip is no longer printed.** The kit has twelve parts. The holder keeps the tapered rear socket, and the R64 collet file still fits it.

### 5. OP1 seat: three holes and one window

- **The horseshoe slit and the fourth hole** were a sprung locator leaf from R53 with a nose for the board's front eyelet. A second leaf stood at the rear eyelet; R66 cut through it with the plug route, which left the slit, the pointed corner and the serrated edge. Both pockets are filled level with the seat and both noses are removed.
- **The stick under the deck beside the window** was R53's print backing for the rear leaf. It is removed.
- **The board is still located** by its three sockets in the three holes and by the pocket walls, as before. The noses were looser than the pocket.
- **Kept:** the thin ribs along the right edge behind the right rail. They are the print backing that the rail grows from.

Board support under the switch is unchanged and the whole seat grows from 160 to 173 mm².

### 6. Key deck

The small window in the strip between the key rows on each side came from R58, when the upper keys moved 1.4 mm toward the lower row. No switch, socket, clip or loading path uses it. Both are filled.

## Checks

Every report names the R68 value beside the R69 one and is bound to the mesh hashes it measured ([summary](exports/checks.json)).

| Report | Result |
| --- | --- |
| [hinge](exports/hinge.json) | Distances above; the inherited click, lift, assembly and edge-press sweeps pass on the R69 parts; the barrel bridge is 7.65 mm on two bed posts |
| [keeper](exports/keeper.json) | 18 far-end press poses clear the retainer by at least 0.245 mm; the same poses touch on R68 |
| [op1](exports/op1.json) | Four openings inside the board outline: three holes and the window. Plug margin 1.00 mm (R68 0.27 mm). Seated board, sockets, housing, plug and lead clear the holder |
| [rod](exports/rod.json) | The bore matches R62 within 0.001 mm up to Y 31.75; the nominal 8 mm rod overlaps the rings by 15.2 mm³, as in R62 |
| [carrier](exports/carrier.json) | 336 key poses and both backer sweeps clear; the battery box and everything outside the changed zones match R68 |
| [source](exports/source-reproduction.json) | All four meshes rebuild byte for byte |

**Mass (PETG, solid):** holder 13.16 → 13.17 g, paddle 1.94 → 1.88 g, retainer 0.34 → 0.29 g, rod grip 0.18 → 0 g. Total 15.622 → 15.334 g.

**Native checks.** Both the primary slice and a fresh slice made by reopening that actual sliced archive pass all 69 loading and working-space routes. Both contain all twelve fittings, no completely unsupported starts and no slicer supports. The base seam measures 22.31 mm², with no base contact in the hinge bay. The cheek-support cleanup uses one shared boundary away from the layer planes; the section report and adjacent-layer images check the formerly affected layers. The narrow wall corner beside the plug window was removed completely; the retainer pad is 29 × 39 mm to retain the proven contact area after lowering its posts.

The native keeper floor is one 0.2 mm layer from the nominal 0.28 mm shape, leaving more room than the conservative CAD floor.

The published plug motion also clears the actual beads in 282 poses; the free-air turn clears all deposited samples by a 2.3994 mm lower bound. All three lower socket bores retain at least 1.642 mm clear radius for the nominal 1.3 mm sockets. The actual new retainer clears the holder and paddle beads in all 50 published insertion/removal poses. Its small CAD latch contact is identical to R68's, with no added contact.

**Independent review:** Claude Opus 5.5 completed the original review, the scoped retainer/cheek follow-up and the final OP1-window review. The final pair shows no former low bridges or upper-ramp loops and was approved for one monitored fit trial. The hash-bound [per-part review](exports/print-mechanisms/review.json) records the four closed findings, measured limits and physical checks. The first monitored R69 print completed on 25 November 2026. Final-layer images showed all twelve kit positions occupied; both heater targets were off at completion. Base release and assembled fit have not been checked.

The slicer's general floating-regions notice remains; its exact trigger is unspecified. The final carrier has five one-anchor runs: four at inherited locations and one 3.012 mm inner perimeter near the right rail end at layer 155, whose four neighbouring loops still have two anchors. The reviewer accepted these for observation during the trial. The widened opening also retains the pocket end walls and two shoulders where the narrower wire mouth meets the window; those hold the board corners and are not obsolete locator teeth.

**Physical unknowns.** Grip force of the printed rings, the real plug size, the barrel bridge in the upside-down paddle print, click feel with the new hook, and base removal all need the printed parts.

The manual browser playback check was unavailable because the browser debugger could not attach. Source validation and automated actor/morph continuity checks cover the generated guide; they do not establish the rendered result.

## Regenerate

Run from this folder in the established CAD environment, with the R69 down to R62 holder folders on the Python path:

```
python3 design69.py                      # holder, paddle, retainer and lead meshes
python3 checks69.py                      # five CAD reports; exits non-zero on failure
python3 audit69.py click                 # click-fit.json
python3 guide69.py                       # viewer guide (--register / --current publish it)
python3 evidence69.py                    # source reproduction
python3 kit69.py DEST/layout.3mf         # complete 12-piece plate and layout.frame.json
python3 ../carbon-rod-holders-r45-open-keyways/slice45.py DEST/layout.3mf DEST/OP1-hinge.gcode.3mf
python3 audit69.py audit DEST            # deposited-bead routes, bases, seat, rod rings
python3 evidence69.py --slice-only DEST  # published connector motion against the native beads
python3 sections69.py DEST               # keeper, rod and adjacent-layer views
python3 audit69.py release PRIMARY REOPENED
```

`design69.py` refuses to run unless the R68, R63 and R62 holders match their published SHA-256 hashes.

## Requirements

| Requirement | Where it is met |
| --- | --- |
| `hinge-no-wire-perch`, `wire-clearance` | Rear web removed; paddle ends 9.37 mm from the board edge; leads over the barrel |
| `hinge-low-keeper`, `op1-slide-retainer`, `guided-paddle` | Low posts and paddle legs; far-end press poses; inherited click sweeps |
| `op1-hand-entry`, `op1-board-bearing` | Guard arm and rib root moved out of the path; one window; three holes and seat support kept |
| `op1-clean-seat` | Locator pockets, noses and backing rib removed; R66 route cuts refilled |
| `rod-grip`, `rod-split` | R58–R62 rings restored; open bed-face end |
| `key-deck-clean`, `key-access`, `open-print-passages` | Strip windows filled; 336 key poses clear |
| `guard-contact`, `guard-coverage`, `guard-lower-blend` | Crown bars, lower rails and blends unchanged; only the top arm rerouted |
| `battery-rail-pre-taper`, `battery-fit` | Battery box identical to R68 |
| `complete-key-kit`, `separate-loose-parts`, `spare-parts` | Twelve parts with both pins and the spare clip; the collet is retired with its job |
| `base-release` | Holder bed face and R64 panel unchanged |
