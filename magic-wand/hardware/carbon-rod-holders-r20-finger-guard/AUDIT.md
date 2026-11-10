# R20 final digital audit — 10 November 2026

The repaired four-part delivery passes the source/export, actual-toolpath,
per-member, reload/re-slice and assembled guard-route checks below. The first
independent Opus 5.5 review identified two pre-trial concerns; Fable 5.2 repaired
them. The scoped independent Opus 5.5 follow-up found no remaining blocker for
a controlled prototype fit trial. It reviewed the final source, bound results
and updated views without new geometry probes. No physical fit, grip, fatigue,
strength, comfort, adhesion, cleanup or saved-video result is claimed.

This is a snapshot of the exact files below. The JSON reports are canonical for
measurements; the artifact regression tests reject stale source, mesh, checker,
project, route and roundtrip identities. Private prompts, photos and raw logs
are not part of the delivery.

## Identity

| Item | SHA-256 |
|---|---|
| Sliced project `R20-A1-mini-PETG.gcode.3mf` | `e4208007036bd96445c72094a4980838b76dc9cb19c27f3af7798723bdd06f89` |
| Layout `R20-A1-mini-PETG-layout.3mf` | `d33648a6ca2f1cb75e8c4bc3c5a58417084ccfef33f1dd04f3613e19c9cd4727` |
| `Key_Carrier` print STL | `d9ffa43656a44add8a81fade5d2ead5f8a1f2c9524c0680786a9827aa3881d57` |
| `Battery_Holder` print STL | `51f3142cc251291813a4820f92aecc9aa46cf1b7b753fc557e659e6bbfe03f7e` |
| `XIAO_Rod_Holder` print STL | `7b839a6f549308dcb82baf1b9cfa1836c4d3309a1686e08451d41626a5878b30` |
| `Finger_Guard` print STL | `8f1f5508ce5752e30a2c4badc352259215722d17fc42c000eded8f64b426287c` |

`manifest.json` binds editable sources, normal and assembly STLs, transforms,
unchanged reusable parts and superseded mesh identities. The R19 battery door,
XIAO keeper and selected cell spacer are reused and are not on this plate.
Battery and XIAO geometry stayed byte-identical during the strength repair.

## Review disposition

| Original concern | Final change and evidence | Remaining boundary |
|---|---|---|
| 1. Guard relied on thin end rims; whole-layer area added separate islands | Rear rim 1.0 to 1.8 mm, front 1.2 to 1.8 mm, with 2.0 mm sloping rear-root braces. Actual beads connect edge to keel in 9 rear and 11 front layers on both sides. All six bay centres have 1.8 / 2.2 mm connecting rims. Every rail retains at least 2.781 of its designed 3.0 mm2 section. | Real finger load, removal and fatigue remain untested. Rails still bend across print layers. |
| 2. Six lower windows aligned through the previously failed backplate level | Those six cuts are removed; four upper and two shoulder windows remain. Across 76 mesh layers the lower board level loses no area or connected pieces versus R16. The weakest mesh layer remains R16's 63.67 mm2. All 43 window-reduced print layers retain at least 95.8 percent bead coverage of their section. | The upper board level retains 72.9 percent of R16 locally; this is disclosed material removal, not a measured strength margin. Test the carrier before moving wired keys. |
| Guard tie access | Ties moved to bay centres away from rail roots; cutter-corridor part volume falls from 1.6–1.7 to 0.41 mm3. Actual ties remain continuous in both pad layers; pads stay at least 0.987 mm from part beads elsewhere. | Snip ties; do not peel or lever on rails. Release and tip adhesion are untested. |
| Tiny guard keel void | Crown wedge radius increased 0.2 mm past the inner apex; rebuilt STL remains one watertight body with source drift below 0.02 mm3. | No physical cause or failure was inferred from the former digital sliver. |
| XIAO travel coverage | Restated seated, axial-stop and ±0.25 mm lateral board poses between the new cheeks, now among the 67 actual-bead working-space checks. | CAD free play is about ±0.32 mm; the declared travel check is narrower. Real solder and wire shape are unmeasured. |
| Basket description | README explicitly shows a separate removable basket. Only the end rims run edge-to-keel; the rails run along the rod to avoid broad unsupported bridges. | It covers the three lower keys, not the two upper ones. |

`member-checks.json` records mesh sections. `slice-clearances.json` repeats the
member measures on real extrusion footprints, not only the source geometry.
The repaired guard has 65 intervening layers of seven separate members; those
areas are not added together as proof of its transverse load path.

The final artifact test enforces a 0.5 mm3 cutter-corridor ceiling on every
guard tie using the source-bound anchor report. This tightens the delivered
regression guard beyond the CAD helper's permissive 3.0 mm3 generation screen
without rebuilding identical toolpaths solely to change that helper constant.

## Layer measurement correction

The first new bead checker compared material to the mesh at the layer edge.
At assembly Y −7.1 that coincided with a step face: it measured 121.70 mm2
instead of the layer-middle 74.29 mm2. The same 70.98 mm2 of bead material is
95.5 percent of the correct section, not 58.3 percent. `members20.py` now uses
layer middles, the established `slice16.layer_section/path_scan` convention.

The inherited saddle also uses 20 percent sparse infill; an unchanged saddle
layer is 77.9 percent filled. The 80 percent material screen applies to every
section reduced by the new windows, while the minimum actual material across
all 176 layers is checked separately: 61.01 mm2 against R16's 63.67 mm2 mesh
minimum. These are explicit digital screens, not a failure-force calculation.

## Actual delivered slice

Bambu Studio 02.09.01.70 CLI; A1 mini, 0.4 mm nozzle, textured PEI, Generic PETG,
0.2 mm layers, three walls, 20 percent infill and 0.6 mm Normal lift. The actual
commands use resolved official machine templates, wait unconditionally for
255 C / 70 C before object printing, and switch both heaters off at the end.
Estimate: 78.62 minutes and 12.68 g total, including adhesion pads and the
disposable timelapse tower; objects and pads account for 10.91 g.

| Object | Working spaces | Floating or missing starts | Pad ties |
|---|---|---|---|
| Key_Carrier | 49 | none | continuous |
| Battery_Holder | 11 | none | continuous |
| XIAO_Rod_Holder | 67 | none | continuous |
| Finger_Guard | 4 own spaces, plus assembled-route check below | none | continuous |

All final source meshes and labelled pad meshes match their sliced counterparts.
No component support, brim or skirt is generated. The six partly backed key
regions are inherited bay-roof regions, retained with their local slow bands;
actual band speeds pass. All eight rod rings retain at least three radial tracks.
Each upper band is directly backed by previous-layer beads; the guard's front
band remains close to its 90 percent digital screen. PETG droop still needs a
real print. Digital clearance does not establish slide force or fatigue.

Smooth timelapse has an actual separate wipe tower. Its bead footprint, including
its base, is X 116.56–135.70, Y 16.55–35.71 mm on the 180 mm bed, over 39 mm from
every holder and pad. No slicer warning remains. Timelapse must also be enabled
in each send dialog; only a real job producing a playable file verifies capture.

## Full assembly-route and reload checks

`guard_paths20.py` checks 77 poses at 0.25 mm steps over 19 mm against 33 assembled
references: both R16/R20 key holders, bought switches/sockets and the stated
solder, tape and wire allowances. No reference intersects the actual final guard
beads after pad removal. A deliberate 1 mm carrier intrusion is detected in
1,038 samples, guarding against an empty or misplaced scan. The same check
passes on the independently re-sliced archive. Full pose results are retained in
`guard-path-checks.json` and `guard-path-roundtrip-checks.json`.
This is the complete modelled 19 mm approach beside the keys. Other installed
modules elsewhere on the rod are outside that check; clear the approach before
fitting the guard.

`roundtrip20.py` reloaded the exact delivered G-code archive and sliced it again.
Effective settings, all three slow modifiers and their world bounds remain
identical. The actual-bead, member and route checks pass again, with 255/70 C
waits and no warnings. The rewritten G-code differs, so checks were repeated
rather than claiming byte identity. This is a CLI reload, not a Studio GUI
export or a sent job.

## Validation and physical trial

Fourteen CAD regressions and all three artifact regression tests pass. The
latter bind sources, meshes, geometry/member/view evidence, final commands,
actual-bead checks, route checks and the exact archive roundtrip. The earlier
repository-wide suite still has two preserved failures caused by an unrelated
edited R16 archive; it is not the R20 delivery and was not changed here.

Before a physical trial, compare the wired wand against the README's explicit
allowances. Test key-carrier rod insertion and twist grip before moving wired
keys. Check guard installation without wire scraping, finger comfort, rim/rail
handling, XIAO solder/wire and USB fit, cell stop/door/spacer fit and pad release.
A rigid fingertip-ball screen is not a real soft finger. None of the digital
passes establishes that every print or physical assembly will succeed.
