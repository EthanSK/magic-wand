# R67 diagonal battery corner and a clean front saddle

R67 is the exact R66 carrier with three small regions removed and nothing added. The three-hole OP1 deck, its top retainer, the compact pin hinge, the finger guards, the rod grips and the R66 socket backing are all unchanged.

[View the assembly](../carbon-rod-holders/assembly/?version=r67&component=keys&view=op1_clips) · [Generator](design67.py) · [CAD checks](checks67.py) · [Slice audit](audit67.py) · [Kit plate](kit67.py) · [Guide](guide67.py)

## What changed

**Battery corner.** Seen from below, the battery side of the holder used to end in a square outer corner at the rear (bed) face. A diagonal cut replaces it. The cut runs from the outer edge at Y 40.0 to X −22.6 at the rear face, 28° from the rod. Its top and bottom edges are rounded at 0.4 mm. The leaf spring and its shoe, the front 1.85 mm of the spring's root post and the post's pouch-side face are unchanged. The rod-side rail still runs the full length.

| Outer edge of the battery side (X, mm) | Y 38–40 | Y 41 | Y 42 | Y 43 | Rear face |
| --- | --- | --- | --- | --- | --- |
| R66 | −24.55 | −24.55 | −24.55 | −24.55 | −24.44 |
| R67 | −24.55 | −24.03 | −23.49 | −22.96 | −22.64 |

**Three strips beside the front saddle.** These were real plastic, not a viewer artefact. R33 had three rounded finger-guard ribs on each side, running from the outer rails to the front rod saddle. R60 replaced those guards and removed the old ribs only outboard of |X| 9.3. On the left, that left the inner ends of the three ribs hanging from the saddle's side wall, ending in air at X −10.8. They held nothing up, and R61–R66 copied them unchanged. R67 removes these stubs (67.7 mm³) up to the saddle face and the rod ring. The ring, its stem and the guard beside them are unchanged ([saddle report](exports/saddle.json)). On the right, the matching position holds different material that is joined to the deck. It shares only 4.8 mm³ with a mirror image of the stubs and is left alone.

**White plug entrance.** The R66 deck opening is unchanged above a 0.7 mm 45° lead-in on its underside edge. The lead-in guides the plug into the hole as it is pushed up from below, instead of letting it catch on a square edge. The lead-in ends 1.43 mm below the board seat, so the three socket holes, the board support and all four board stops are exactly R66's.

## Fitting the white plug from below

The sequence is R66's: unplug the white plug, tip it so its lead hangs down, and raise it beside the installed rod, inside the right finger guard, through the opening. Turn it upright above the holder, push the board onto it and lower the board into its three holes.

- **Clearance for the modelled plug:** 0.75 mm through the deck, 0.45 mm past the board's end stop, 0.78 mm to the rest of the holder and 2.14 mm to the full-length rod.
- **Sliced route:** both native R67 slices pass the insertion and removal checks for the modelled plug and lead. The plug size is estimated from photos. The opening needs a physical fit check with the actual connector.
- **Plug evidence:** the plug comes from the Endgame Gear OP1 Universal Switch Set (EGG-SP-U1). The project has no dimensioned drawing of the plug, so the 3.1 × 6.2 × 3.65 mm plug is a photo estimate, not a measurement.
- **Hand access:** from 4 mm below the rod axis up to the deck, the free space round the plug's path is only 3.16–5.3 mm in radius, with the rod and fitted keys in place. A fingertip cannot follow the plug through that last 11 mm. Push it up by its body with tweezers, or feed it until it can be gripped above the holder.

**Not possible with this deck:**

- A board with its plug already mated cannot go in from below. Pushed straight up into the seated housing, the mated plug overlaps the rod (1.01 mm³) and the holder (12.82 mm³).
- The mated board cannot be lowered from above either, because its lead would have to pass through the deck. The opening is a closed hole from 7.7 to 9.2 mm in height. Avoiding that would need an open slot through the board deck, which would weaken it.

## Checks

The CAD checks bind every report to the exported carrier's SHA-256 ([carrier.json](exports/carrier.json)).

| Check | Result |
| --- | --- |
| Only the three regions changed ([subtraction](exports/subtraction.json)) | 78.12 mm³ removed: 9.01 at the corner, 67.68 at the saddle and 1.43 at the lead-in. The volume removed equals the cutters' total. On 313 sections the export matches R66 minus the cutters within 0.0007 mm² |
| Battery ([battery](exports/battery.json)) | Leaf and shoe preload unchanged, pouch slides in and out clear, lip retention unchanged (7.83 / 4.45 mm³) |
| Spring root post | 41.7 of R66's 46.6 mm³ kept, 10.0 mm² joined to the deck |
| Saddle | Rod ring, stem and guard volumes unchanged; the same free piece is present from R60 to R66 and absent in R59 |
| OP1 ([route](exports/op1-route.json)) | All R66 route, drop, lead, retainer and stop gates pass. Board end stop 93.1 % of R63's, as in R66 |
| Key routes | 336 poses with no obstruction; both socket backer sweeps clear |
| Click and hinge ([click-fit](exports/click-fit.json)) | Overlaps within the R66 limit; contact before the case stop |

**Base ties.** The diagonal removes the corner where two R66 bed fins were rooted. The fin under the spring-root post moves from X −22.68 to −22.4, and the fin on the battery roof plate moves from X −23.8 to −22.0. Heights and thickness are unchanged.

**Printing.** The new face leans 28° from vertical as it rises from the bed, so it needs no support. The bed contact at the battery corner falls from 14.1 to 8.2 mm².

**Demonstrated limits.** These are CAD and slice checks only. Hand fit of the actual plug, battery retention, click feel and strength need the printed parts.

## Qualified fit-trial plate

[Complete 13-piece A1 mini PETG plate](exports/print-mechanisms/R67-Complete-Key-Holder-A1-mini-PETG-print-only.3mf)

Two native slices pass the deposited-path checks. The independent Opus review approves one monitored fit trial, not physical acceptance. Both slices retain the known floating-regions notice. The reviewed layer records show no completely unsupported starts. The outboard battery lip begins with the same 4.63 mm one-ended run as R66 and needs watching during a trial.

- [Independent review](exports/print-mechanisms/review.json), [parent follow-up evidence](exports/print-mechanisms/review-dispositions.json).
- The current source regenerates the exact reviewed carrier, byte for byte ([source reproduction](exports/source-reproduction.json)).
- The plug's turn above the holder clears all 3.02 million deposited samples by a conservative 2.3995 mm, including bead width and height. A deliberately misplaced plug hits the actual deck, confirming the coordinate frame and obstruction check.
- Additional deposited sections at 7.3, 7.6 and 7.95 mm show all three lower socket bores open, with clear radii at least 1.6416 mm for the 1.3 mm hardware radius.
- Cut all six base fins flush, three on each side of the exposed rim. Cut the two battery-corner ties before peeling; do not twist against the spring-root post.

Some inherited report keys retain R66 names. For R67 battery-root values use `diagonal_corner.root_post_mm3.r67`, and for the OP1 entrance use `lead_in`. These fields identify the actual current and reference geometry explicitly.

## Regenerate

Run the commands from this folder in the established CAD environment, with the R67, R66, R65, R64, R63 and R62 holder folders on the Python path:

```
python3 design67.py                      # carrier: the R66 export minus the three regions
python3 checks67.py                      # CAD reports; exits non-zero on failure
python3 audit67.py click                 # CAD click and hinge fit
python3 guide67.py --current             # viewer guide; registers R67 as the default
python3 kit67.py DEST/layout.3mf         # complete 13-piece plate and layout.frame.json
python3 ../carbon-rod-holders-r45-open-keyways/slice45.py DEST/layout.3mf DEST/OP1-hinge.gcode.3mf
python3 audit67.py audit DEST            # deposited-bead routes, bases, seat and starts
python3 evidence67.py PRIMARY REOPENED   # source reproduction, free-air turn and lower bores
python3 audit67.py release PRIMARY REOPENED
```

`design67.py` refuses to run unless the R66 carrier matches its published SHA-256.

## Requirements

| Requirement | Where it is met |
| --- | --- |
| `battery-outer-taper` | Diagonal outer corner; the rod-side rail stays full length |
| `battery-fit`, `battery-friction`, `battery-against-deck` | Leaf, shoe, lips and pouch path unchanged; see the battery report |
| `lightweight-strength`, `assembly-annotations` | Unloaded saddle stubs removed |
| `op1-board-bearing` | R66's three holes, deck support and top retainer unchanged; lead-in below the deck only |
| `rod-grip`, `rod-split` | Rod ring and saddle unchanged |
| `base-release`, `base-removal` | Two fins moved onto the remaining corner material |
| `only-changes` | Three subtractions from R66, proven section by section |
