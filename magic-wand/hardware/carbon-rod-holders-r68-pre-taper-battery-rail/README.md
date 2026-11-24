# R68 full battery rail

R68 is the R67 carrier with the battery's outer rail put back to its shape before the R66 taper. Nothing else changed. The three-hole OP1 deck, the plug lead-in and open plug route, the cleaned front saddle, the compact pin hinge, the rear socket backing, the rounded lower guards, the rod grip and the keys are all exactly R67's.

[View the assembly](../carbon-rod-holders/assembly/?version=r68&component=keys&view=op1_clips) · [Generator](design68.py) · [CAD checks](checks68.py) · [Slice audit](audit68.py) · [Kit plate](kit68.py) · [Guide](guide68.py)

## What changed

**Outer battery rail.** R66 tapered the outer (finger-side) battery rail. From Y 32 its wall and lip rose into the deck, which left the spring-root post exposed. R67 then cut the remaining corner at the rear face diagonally. R68 restores the full rail. The outer wall and its lip again run at full depth to the rear (bed) face, with the square corner around the spring-root post and the battery roof plate. The rod-side rail, the spring leaf and its shoe were never changed and remain as they were.

| Outer battery rail | R64 (before the taper) | R67 | R68 |
| --- | --- | --- | --- |
| Full-depth outer wall (Y, mm) | 21.5–43.5 | 21.5–32.5 | 21.5–43.5 |
| Outer lip under the pack (Y, mm) | 21.0–43.5 | 21.0–34.0 | 21.0–43.5 |
| Outer edge at Y 43 (X, mm) | −24.55 | −22.96 | −24.55 |
| Lip retention, pack pushed 0.3 mm off the deck (rod side / outer side, mm³) | 7.83 / 7.83 | 7.83 / 4.45 | 7.83 / 7.83 |
| Spring-root post (mm³) | 47.9 | 41.7 | 47.9 |

**How it is built.** The R68 generator does not rebuild the carrier. It takes the exact R67 export and replaces a single box around the outer rail with the same box from the R64 export, which was the last carrier built before the taper. The box is R66's rebuilt battery zone, raised to 1 mm above the roof plate so that it also covers R67's corner cut. Inside that box, R63, R64 and R65 are identical. The box restores nothing else: the material it holds outside the R66 and R67 changes is the same in R64 and R67.

**Battery fit.** The pouch slides in and out without touching anything except the spring shoe, whose 0.21 mm preload is unchanged. It still sits 0.05 mm clear of the deck and sticks out 5.25 mm past the rear face. The open end and the slot are R64's, so the pack is removed and its wire leaves the holder as before.

## Base ties

The carrier panel is R64's again. R63's two battery fins were rooted on the 0.8 mm lips, and that printed holder took heavy twisting to free at the battery entrance. R64 moved those two fins onto the solid outer corner: one under the outer wall foot (X −24.0) and one on the battery roof plate (X −23.8). R66 and R67 moved them inward only because their taper and diagonal had removed that corner. With the corner back, they return to R64's stations.

- No fin touches either lip. In CAD, fin material inside the holder is 0 mm³ at both lips, 1.89 mm³ under the corner and 2.46 mm³ above it.
- The R63 keep-clear box keeps every fin out of the pouch mouth and off the spring-root post.
- All six fins and their overlaps match R64's exactly, and the base builds as one piece.

## Checks

The CAD checks bind every report to the exported carrier's SHA-256 ([carrier.json](exports/carrier.json)).

| Check | Result |
| --- | --- |
| Only the rail changed ([restore](exports/restore.json)) | 77.62 mm³ restored. Outside the box, the export matches R67 on 313 sections within 0.0004 mm². Inside it, the export matches R64 on 114 sections within 0.0004 mm². The volumes agree within 0.001 mm³ |
| Battery ([battery](exports/battery.json)) | Rail, lips, leaf and shoe preload, root post, slide and retention all equal R64's |
| Base fins | Free lip ends clear; the two corner fins are joined to the restored corner; the panel is one piece |
| Saddle ([saddle](exports/saddle.json)) | R67's stub removal is kept; the rod ring, stem and guard are unchanged |
| OP1 ([route](exports/op1-route.json)) | All R67 route, drop, lead, retainer, lead-in and stop gates pass; board stops equal R66's |
| Key routes | 336 poses with no obstruction; both socket backer sweeps are clear |
| Click and hinge ([click-fit](exports/click-fit.json)) | Identical to R67 |
| Source ([reproduction](exports/source-reproduction.json)) | `design68.py` regenerates the export byte for byte |

In [saddle.json](exports/saddle.json) and [op1-route.json](exports/op1-route.json), `r68` holds the current carrier's values and `r66` the R66 reference.

**Printing.** The restored rail is R64's. In R64's native slices, both lips had no contact with the base, and the corner fins joined the holder by 4.42 mm² below and 3.21 mm² above. The bed contact at the battery corner returns from R67's 8.2 mm² to 20.1 mm². R68's own slices are checked by `audit68.py`.

**Demonstrated limits.** These are CAD checks only, and R68 has not been printed. The bought pack and the white plug are nominal sizes, not measurements. Battery retention, base removal at the corner fins, hand fit of the plug, click feel and strength need the printed parts.

## Regenerate

Run the commands from this folder in the established CAD environment, with the R68, R67, R66, R65, R64, R63 and R62 holder folders on the Python path:

```
python3 design68.py                      # carrier: R67 with the R64 rail restored
python3 checks68.py                      # CAD reports; exits non-zero on failure
python3 audit68.py click                 # CAD click and hinge fit
python3 guide68.py                       # viewer guide (--register / --current publish it)
python3 kit68.py DEST/layout.3mf         # complete 13-piece plate and layout.frame.json
python3 ../carbon-rod-holders-r45-open-keyways/slice45.py DEST/layout.3mf DEST/OP1-hinge.gcode.3mf
python3 audit68.py audit DEST            # deposited-bead routes, bases, seat and starts
python3 evidence68.py PRIMARY REOPENED   # source reproduction, free-air turn and lower bores
python3 audit68.py release PRIMARY REOPENED
```

`design68.py` refuses to run unless the R67 and R64 carriers match their published SHA-256 hashes.

## Requirements

| Requirement | Where it is met |
| --- | --- |
| `battery-rail-pre-taper` (supersedes `battery-outer-taper`) | The full R64 outer rail, wall and lip, to the rear face |
| `battery-fit`, `battery-friction`, `battery-against-deck` | Leaf, shoe, lips and pouch path equal R64's; see the battery report |
| `integrated-battery`, `battery-compact` | The same integrated slot; no new holder or clip |
| `base-release`, `base-removal`, `r63-base-fit` | R64's corner fins; both lips stay off the base |
| `op1-board-bearing`, `rod-grip`, `rod-split` | Unchanged from R67 |
| `only-changes` | One restore box, proven section by section against R67 and R64 |
