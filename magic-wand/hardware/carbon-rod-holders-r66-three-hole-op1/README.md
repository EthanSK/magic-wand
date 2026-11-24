# R66 three-hole OP1 seat with a plug opening

R66 returns to the one-piece R63 board deck, with its three separate socket holes, the deck support under the board and the existing slide-in top retainer (`OP1_Lid_Stop`). There is no loose seat and no wide underside bay. The only new opening is a small one at the end of the board seat, through which the white plug and its lead pass. The R64 finger guards, compact pin hinge and rod grip are kept. The outer battery rail now tapers, and an exterior backing on the rear rod socket removes a knife edge that sliced badly.

[View the assembly](../carbon-rod-holders/assembly/?version=r66&component=keys&view=op1_clips) · [Generator](design66.py) · [CAD checks](checks66.py) · [Slice audit](audit66.py) · [Kit plate](kit66.py) · [Guide](guide66.py)

## Fit the wired OP1

The plug passes through the opening. The board itself is always seated from the open top face.

1. Leave the black switch and the top retainer off. Unplug the white plug from the bare board.
2. Tip the plug so its lead hangs straight down. Raise it from below, beside the installed rod and inside the right finger guard, up through the opening at the end of the board seat.
3. Above the holder, turn the plug upright and push the board's fixed white housing onto it.
4. Lower the board straight down. Its three metal sockets drop into the three holes while the housing and plug sink into the opening. The lead follows them down through the opening.
5. From underneath, press the lead up into the open channel beside the rod. Fit the switch, then the paddle and finally the top retainer.

Removal plays the same five motions in reverse.

**What the prewired option allows:** the harness stays attached to the wand, but the plug must be unplugged from the board while it threads up. Two other routes were measured and do not work:
- A board whose plug is already mated cannot be lowered from above, because the lead would have to thread through the closed deck. The opening is a closed hole from 7.7 to 9.2 mm in height.
- The mated plug cannot be pushed up into a seated housing from below. Straight up, it overlaps the full-length rod by 1.01 mm³ and the carrier by 12.82 mm³.

## Checks

The CAD checks bind every report to the exported carrier's SHA-256 and recheck the routes, the seat and the stops ([op1-route.json](exports/op1-route.json)).

| Check | Result |
| --- | --- |
| Plug opening | 3.91 mm³ of R63 material removed, nothing added in the OP1 zone |
| Tipped plug through the closed deck | 0.75 mm clear; R63 cleared it by only 0.026 mm |
| Tipped plug past the board's end stop | 0.45 mm clear |
| Tipped plug elsewhere in the holder / full-length rod | 0.784 mm / 2.135 mm clear |
| Turning, lowering, seated lead and fitted keys | No contact, including the lead throughout its turn |
| Three socket holes | Clear radius 1.739 mm each, the same as R63 at all three heights |
| Board support within 0.10 mm | 159.95 mm², against 160.25 mm² on R63; switch and plunger zones unchanged |
| Board end stop | 93.1 % of R63's engagement; left, right and front stops unchanged |
| Key routes | 336 poses with no obstruction; both socket backer sweeps clear |

The [battery report](exports/battery.json) measures the rails every 0.5 mm along Y:

| Battery rail | Extent along Y (mm) |
| --- | --- |
| Inboard (rod side) rail, full depth | 20.5 – 43.5 |
| Outboard rail, full depth | 21.5 – 32.5 |
| Outboard lip under the pack | 21.0 – 34.0 |
| Outboard wall, any depth | 21.0 – 40.5; rounded with a 0.38 mm edge, then it rises into the deck |

The spring leaf keeps its preload. Its rounded root retains 46.6 mm³ of the earlier 47.9 mm³. R64 anchored one removable bed tie on the outboard wall at X −24.0. That tie moves under the root post at X −22.68 and is 2.4 mm tall. With the pouch pushed 0.3 mm off the deck, the inboard lip retains it by 7.83 mm³ and the outboard lip by 4.45 mm³.

The [socket backing report](exports/socket-backing.json) covers the rod socket change. R63's rear socket is the tapered seat for the split rod collet. Near the bed face, its right-hand wall thinned to a knife edge, and the first R66 native slice started a 0.15 mm² outer-wall fragment there with nothing beneath it. An annular sector adds 21.84 mm³ outside that wall only. A first version, 0.03 mm from the seat, touched the collet in its last 1.0 mm of tightening travel, so the backing now stands 0.19 mm off. Native slices of both versions had no completely unsupported starts.

- It stays 0.19 mm outside the seat taper and 1.85 mm from the lengthwise split.
- It does not extend past the bed face.
- All 57 collet insertion poses are clear of it, and it adds no interference during the 1.5 mm push-in stroke.
- Outside its small box, 630 sections show at most 0.0006 mm² of change from retriangulation. A point-to-surface diagnostic reaches 0.14 mm only at an internal surface sheet at X = 12.7, which encloses no material.

The CAD click and hinge fit is identical to R64 and R65 ([click-fit.json](exports/click-fit.json)).

**Demonstrated limits.** The modelled plug is 3.1 × 6.2 mm, estimated from photos rather than measured. The checked route clears it by 0.75 mm through the deck but by only 0.45 mm past the board's end stop. These clearances apply to the modelled plug and its illustrated orientation. The fit of the actual connector needs a physical check. The lead shape shown in the viewer while the plug turns is illustrative, because a real lead flexes. Hand fit, click feel, battery retention and strength need the physical parts.

## Monitored fit trial

Both native Bambu slices have all 13 pieces, three open socket holes and plastic directly below the switch. The sliced seat supports 158.39 mm² beneath the PCB, compared with 158.67 mm² on R63 and 72.85 mm² on R64. The A1 mini print file contains the reviewed PETG machine instructions.

A further check used the lead meshes loaded by the viewer at 51 positions in each motion. Both the above-holder turn and laying the lead into its channel cleared the carrier, full-length rod and fitted keys. The test covers the illustrated wire shape.

Watch the start of the tapered outer battery lip at about 10 mm of print height. Studio flags floating regions. Both slices have zero completely unsupported starts, but at layer 49 one outer-wall line runs 4.63 mm from the free tip toward its anchor. Inspect the lip for sag or strands before inserting the pouch. Retention, connector insertion and repeated clicks still require a physical trial.

[13-part PETG plate](exports/print-mechanisms/R66-Complete-Key-Holder-A1-mini-PETG-print-only.3mf) · [Sliced OP1 seat](exports/print-mechanisms/op1-seat-comparison.png) · [Independent review](exports/print-mechanisms/review.json)

## Regenerate

Run the commands from this folder in the established CAD environment, with the R66, R65, R64, R63 and R62 holder folders on the Python path:

```
python3 design66.py                      # carrier and guide lead meshes
python3 checks66.py                      # CAD reports; exits non-zero on failure
python3 audit66.py click                 # CAD click and hinge fit
python3 guide66.py --current             # viewer guide; registers R66 as the default
python3 kit66.py DEST/layout.3mf         # complete 13-piece plate and layout.frame.json
python3 ../carbon-rod-holders-r45-open-keyways/slice45.py DEST/layout.3mf DEST/OP1-hinge.gcode.3mf
python3 audit66.py audit DEST            # deposited-bead routes, bases, seat and starts
python3 audit66.py release PRIMARY REOPENED
```

`design66.py` refuses to add the backing unless the pre-backing carrier matches the SHA-256 that was proven on the native slice. Run the slice audit on both the primary and the reopened slice before the independent review and release.

## Requirements

| Requirement | Where it is met |
| --- | --- |
| `op1-board-bearing` | One-piece R63 deck with three socket holes and an end opening only; see the OP1 checks |
| `battery-outer-taper` | Tapered, rounded outboard rail; the inboard rail, spring and root are kept |
| `viewer-version-reload` | Steady amber "Reload to see new version" button in the shared viewer styles |
| `assembly-sequence`, `assembly-annotations`, `viewer-assembly` | Animated insertion and removal with notes for each step |
| `battery-against-deck`, `battery-fit`, `base-removal` | Battery report and the moved bed tie |
| `rod-grip`, `rod-split` | Socket backing report; the collet seat and the split are unchanged |
| `only-changes` | Compared with R63 on R64's guards and hinge, only the OP1 opening, battery taper and socket backing change. Compared with R64, R66 also keeps 14.1 mm³ of R63 material that R64 cut for its under-entry lead lane |
