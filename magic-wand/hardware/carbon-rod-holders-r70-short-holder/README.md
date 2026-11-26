# R70 key holder: short holder, nearer right key, round edges

R70 starts from the printed R69 holder, which fitted and clicked well. It makes eight changes. The CAD and native deposition checks below distinguish geometric fit from an untested physical trial.

| Part | File | Change |
| --- | --- | --- |
| Key holder | [`Key_Carrier-assembly.stl`](exports/Key_Carrier-assembly.stl) | Shorter, right upper key 2 mm nearer, rounded lower edge, rebuilt battery spring |
| Touch paddle | [`Touch_Paddle-assembly.stl`](exports/Touch_Paddle-assembly.stl) | Stronger joints between the arms and the hinge barrel |
| Two-post bar | [`DFR_Post_Bar-assembly.stl`](exports/DFR_Post_Bar-assembly.stl) | Tapered ribs aimed at a snug nominal 3 mm hole |
| OP1 retainer | [`OP1_Lid_Stop-assembly.stl`](exports/OP1_Lid_Stop-assembly.stl) | None: R69's file, byte for byte |

The plate has nine pieces: these four, one hinge pin, the centre clip and its spare, and the two touch-board clips. The snug pin and the two socket backing strips are no longer printed every time. Their files are unchanged, and the R69 plate still prints them.

## 1. Shorter holder

The holder ended 11.35 mm behind the hinge pin. It now ends 4.15 mm behind it, 7.20 mm shorter (rear face Y 43.65 → 36.45, 10.22 mm behind the touch board's edge instead of 17.42).

- Each bearing block is a plain prism standing on the rear face (30.3 mm² each on the bed; R69 9.2 mm² under a 45° buttress). The pin line, both bearings and the pin bore are R69's.
- The rear plateau, the buttresses and the tapered rear socket are gone. The bore gets a 0.9 mm mouth at the new face.
- The two rod rings are untouched, so the grip is R69's.

## 2. Battery

The pouch stays where it was, against the deck. With the shorter rail, 12.45 mm of it stands behind the holder (R69 5.25 mm) and 14.55 mm is held (R69 21.75 mm). It cannot move forward: the left guard is rooted in the deck directly in front of it.

The side spring was rooted behind the new rear face, so it is rebuilt: a 2.0 mm root on the new face, a lever of 8.25 mm (8.8), a leaf 2.36 mm high (3.03) and the same 0.21 mm preload. The computed stiffness is 0.945 of R69's. There is no cover.

## 3. Right upper key

The right upper key sits 2.0 mm nearer the lower row (centre distance 19.95 → 17.95 mm; cap travel envelopes 0.55 mm apart instead of 2.55 mm). The whole right bank above the deck moves as one block, so every inherited key space moves with it. Three things in that block belong to something else and stay put: the corner of the OP1 connector window, the root of the right guard's top arm and a small rib on the plate.

**The left upper key does not move.** Its prewired socket slides in under the deck from the outer edge. Moved 0.2 mm toward the lower row, that path already enters the left guard, which is rooted there. Following the right key would need the left guard reshaped; R70 does not do that. The two upper keys are therefore 2 mm out of line with each other.

## 4. Paddle joints

Each side beam met the hinge barrel through a post 1.5 mm long. A gusset now fills the corner between each beam and the front of the barrel, and the left post flares to the barrel behind as well. The section joining beam to barrel grows from 17.3 to 30.2 mm² on the left and from 11.1 to 15.9 mm² on the right. The right side gains less because the three touch leads turn behind its post.

The click sweep gives the same contact angle, case stop, lift stop and travel as R69.

## 5. Touch-board posts

The posts were 2.25 × 2.52 mm in holes of 3 mm nominal, so the board could shift 0.75 mm. Each post now carries two slim ribs inside the board thickness. With the post's own lower edge they make three contacts. The ribs taper, so the board starts easily and tightens as it reaches the paddle.

| Hole | Rib squeeze at the paddle | At the board top |
| --- | --- | --- |
| 3.0 mm | 0.207 mm | 0.107 mm clear |
| 3.1 mm | 0.124 mm | clear |
| 3.2 mm | 0.041 mm | clear |

The hole size is the maker's nominal figure (DFRobot DFR0030, "3 mm", no tolerance); the board was not measured. The hole pitch was read from photographs as 15 to 16 mm and the posts are 15.5 mm apart. If the real pitch is 15.0 or 16.0 mm, the two ribs receive unequal squeeze (see the pitch cases) ([posts](exports/posts.json)). The ribs are meant to crush or shave; the posts themselves are still 2.25 mm, so the board is never forced onto two rigid 3 mm pins. The neck, head and bar are unchanged and the existing clips fit in CAD. The bar prints upright with 0.42 mm flat rib crests. Native bead footprints enclose 3.049 mm at the seat, tapering to 2.728 mm at the board top, versus the nominal 3 mm holes. Actual printed friction, pitch and insertion force remain untested.

## 6. Round edges

The lower edge of both key banks was a square arris with a small foot. It is now a quarter round of 1.5 mm along the front, the outer corners, both outer sides and the rear shoulders. The upper edge gets 0.9 mm. The sloped rim in front of the lower-left key had a knife crest; it gets a 0.4 mm round.

Measured at 89 stations along both banks, 84% of the lower edge is round (R69: none). The rest is listed by cause: four stations where a guard rail enters the deck and keeps its full tube, nine where the face is not at that level (the socket entrance on the left, the sloped front rim), and one at the battery rail. No station is left square.

The exposed rear bank rims use a smaller 0.6 mm round so the first layer retains broad contact. Guard, battery-wall and standing-rib roots retain their full sections. The centre between the banks was already rounded in R62.

## 7. Base release

R69's holder was tied to its sacrificial panel by six fins. Three were rooted in the 1.2 mm roof over the battery, two of them over the open pouch space. That is a plausible source of the reported tear when pulled rather than cut; the actual fracture origin was not measured.

R70 has five fins and none on the roof over the pouch, on a battery wall or on a lip. The least plastic straight behind any fin is 2.4 mm (R69 0.9 mm). The two fins at the battery corner sit on a solid block and are necked to 0.84 mm beside the holder, so the weak section is in the fin.

| | R69 | R70 |
| --- | --- | --- |
| Holder's own first layer | 144.8 mm² | 197.6 mm² |
| Print height | 62.5 mm | 55.3 mm |
| Fins | 6 | 5 |
| Deposited base-to-part contact, full first 5 mm | 24.34 mm² | 23.96 mm² |

The same deposited-bead method covers all 25 attachment layers in both revisions. R70 retains 98% of R69's full base contact while moving the battery ties onto solid material and narrowing their release necks. Actual adhesion and clean removal remain physical trial checks.

## 8. Guard

No guard beam moved. The idea of more room between the guard and the base was not taken up.

## Checks

Every report puts the R69 value beside the R70 one and is bound to the mesh hashes it measured ([summary](exports/checks.json)). Where a gate describes a fault R69 had in the hand, it is run on R69 too and fails there.

| Report | Result |
| --- | --- |
| [hinge](exports/hinge.json) | Click, lift, assembly and edge-press sweeps pass with R69's values; 18 far-end press poses clear the retainer by at least 0.245 mm |
| [short](exports/short.json) | Rear face, bearing blocks and rod bore as above; the bore is R69's up to the new mouth |
| [battery](exports/battery.json) | The pouch seats and slides in against the rigid rail; only the spring shoe touches it; the rail in front of the new face matches R69 |
| [keys](exports/keys.json) | 336 key poses clear with the right key at its new place; the OP1 window, plug route and seat are R69's |
| [posts](exports/posts.json) | The ribbed bar passes the paddle's holes and matches the R57 bar outside the board thickness |
| [edges](exports/edges.json) | Station-by-station edge profile; nothing is removed further than the radius from the outline |
| [base](exports/base.json) | Nine pieces; fin roots and sections; the R69 plate fails the thin-root gate |
| [carrier](exports/carrier.json) | The centre, the left bank inside its rim and both guards match R69 section by section |
| [source](exports/source-reproduction.json) | All five meshes rebuild byte for byte |

**Mass (PETG, solid):** holder 13.17 → 11.37 g, paddle 1.88 → 1.91 g. The nine-piece plate uses 13.73 g of parts; R69's twelve used 16.49 g.

**Native evidence.** The delivery folder retains the actual deposition reports, mechanical sections and selected native layer images. Review and reopened-file results belong to the hash-bound per-part report; they are not physical fit or strength measurements.

**Physical unknowns.** Base release and adhesion; how firmly 14.55 mm of rail holds the pouch; the real size and pitch of the touch-board holes and the force to seat the board; the feel of the rounded edge; the strength of the right guard root now that the moved key's latch pass lies over its outer part (1.08 mm of deck under the pass).

## Regenerate

Run from this folder in the established CAD environment, with the R70 down to R62 holder folders on the Python path:

```
python3 design70.py                      # holder, paddle, post bar, lead and retainer meshes
python3 checks70.py                      # eight CAD reports; exits non-zero on failure
python3 guide70.py                       # viewer guide (--register / --current publish it)
python3 audit70.py click                 # click-fit.json
python3 audit70.py routes                # every route against the CAD meshes
python3 evidence70.py                    # source reproduction
python3 kit70.py DEST/layout.3mf         # complete nine-piece plate and layout.frame.json
python3 audit70.py audit DEST            # deposited-bead checks on a native slice
```

`design70.py` refuses to run unless the R69 holder matches its published SHA-256 hash.

## Requirements

| Requirement | Where it is met |
| --- | --- |
| `base-release` | Five fins on thick sections; necked fins at the battery corner; R69's plate fails the new gate |
| `battery-short-rail`, `battery-fit` | Rail 7.20 mm shorter; pouch place, lips, walls and preload unchanged; no cover |
| `hinge-stability`, `guided-paddle` | Gussets and left flare; click sweeps unchanged |
| `row-spacing`, `key-access` | Right key 2 mm nearer with all 336 poses clear; the left key's limit is measured and stated |
| `guard-contact`, `guard-coverage`, `guard-lower-blend` | No guard beam moved; rails keep their tubes where they enter the rounded edge |
| `bottom-edge-rounded` | 1.5 mm lower and 0.9 mm upper round on both banks, plus a 0.6 mm rear round |
| `dfrobot-post-fit` | Ribs target snug nominal 3.0 mm holes; native 3.2 mm holes remain clear; post height, neck and clips unchanged |
| `complete-key-kit`, `separate-loose-parts`, `spare-parts` | Nine pieces with the spare clip; the snug pin and both strips stay available from R69 |
| `rod-grip`, `op1-hand-entry`, `op1-clean-seat`, `hinge-low-keeper` | Unchanged from R69 and checked again |

## First print

The first monitored R70 plate finished on 26 November 2026. Final-layer camera images showed all nine kit positions occupied, with the main parts and small clips still attached to their bases. The printer reported completion without errors and both heater targets at zero. Thin travel strings remained over the paddle recess and between some pads.

Base removal, assembled fit, click feel, battery retention, touch-board insertion force, comfort and strength have not yet been physically checked. The camera establishes that the parts were present; it does not establish those fits.
