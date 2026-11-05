# R13 printability and weakness audit

Status: **audited test-first candidate, accepted for the small key/clip trial**. This is not a physically accepted full set. The release gate requires a consistent source/project/checker snapshot, every actual opening clear, supported starts, measured helper gaps, explicit overhang decisions and independent review. Physical cleanup, fit, sag, toughness, fatigue, retention and comfort remain unverified.

## What the R12 evidence establishes

R12's checker excluded support features from the decision that made its report pass. The delivered archive contained support in every rod bore, all five switch/socket areas, the battery reserve and PCB space. It assumed removal would succeed without demonstrating that removal. The corrected all-bead checker rejects that preserved archive in **48 of 51** adapted working regions. These regions include R13's expanded maximum socket, wire and gate routes; this is a negative control, not a new R12 qualification.

The exact file, material, printer settings and cleanup outcome of the failed physical print were not recovered. Support obstruction is established in the delivered digital project. PETG fusion, residue, bridge sag, first-layer effects or dimensional error may have contributed physically, but none is a confirmed diagnosis of every reported hole.

## Local model changes and weak-point screening

| Part | Changes and preserved interfaces | Remaining physical test |
|---|---|---|
| Five-key carrier | Keep five seats, 18.5 mm pitch, 20.5 mm rows and 25.4 mm thumb clearance. Add fixed outboard load rails to bypass the two thin switch rims that formerly formed the upper-key connection. Ramp their leading undersides; retain full nominal/maximum socket and switch routes. Fixed row joints grow from 1.2 to 2 mm below the mounting plane. Trim a detached 0.27 mm corner remnant outside the rounded rear post. The socket floor remains locally 1.2 mm over the rod cut and 1.38 mm elsewhere; bought-interface rims and stops remain measured thin interfaces. | Real socket/switch insertion, the 14.1 mm mounting-opening bridges, smaller stop/rear-wall bridges, helper release, upper-key pressing and full-height adhesion. |
| Battery holder | Crossbars grow from 1.4 to 2 mm, with three longitudinal stringers and a bed-facing far frame. Centre-to-side bridge support spacing is 12.8 mm. Outside gate walls grow from 0.8 to 1.6 mm with outside diagonal braces. Far clip moves 2.2 mm to share bed contact. The separate battery remains above the keys toward the tip. | Crossbar droop and bonding, complete cell loading, guide/gate sliding and retention without pouch pressure. |
| Battery end gate | Grab-bar depth grows from 1.6 to 2.7 mm outside the cell and guides. Sliding wedges stay at their bought-fit dimensions, including nominal 1.2 mm narrow ends and 1.6 mm depth. Its original broad face is on the bed, with the extra grab bar upward. | Cycle the empty gate first. Pull the centre, not a narrow wedge; stop if a guide binds or whitens. |
| XIAO rod holder | Fixed outside rails grow from 1.2 to 2 mm and fixed diagonal ribs from 1.6 to 2.1 mm. The middle axial rails grow from 1.25 to 2 mm, ending before the free clip arms. USB remains toward +Y and wires external. The late fixed diagonals receive their own printing aids before the C face starts. | Full-height print, helper removal, rod sliding, actual populated-board underside, solder bends, USB lead strain and root bonding. |

All six almost-closed clip profiles retain their intended free arms and 30-degree gaps. Relaxed 7.9 mm bores remain the default for the nominal 8 mm rod; 8.0 and 8.1 mm coupons only bracket fit. Geometry does not establish interference force or fatigue life. Never snap a nearly closed clip sideways over the rod or force an undersized print.

`strength-checks.json` records final STL ray sections, actual distinct bead-track counts, layer direction, load cases and required physical tests for the parts present in each project. It scans the entire key front-anchor/ramp and connection to the floor, including each full-depth added rail. A sample count is not a bead count. The report is a geometric/process screen, not a force simulation or a guarantee that nothing can snap.

## Print strategy and accessible helpers

The prepared recipe remains Bambu P1S, 0.4 mm nozzle, PETG, 0.2 mm layers, three walls and 20% infill. It is a controlled test recipe, not proof that the failed physical print used that machine/material. Automatic supports and brim are off globally and on every object. Rod axes are vertical to avoid circular bore roofs and put clip bending in the layer plane; the small gate prints flat.

Normal/tree, automatic/manual and blocker trials routed supports through working spaces and were rejected. The candidate uses labelled ordinary-model CAD printing aids outside those spaces. They back the socket floors, deep front webs, late clip faces and sensor diagonals. These aids are absent from bare assembly STLs; use the prepared projects for trials.

The actual contact recipe leaves one empty 0.2 mm layer below named first faces. The small-gap exception applies only below that face; a wall continuing above it regains ordinary clearance. Helpers grow on the layer grid with at most 0.25 mm sideways growth per 0.2 mm layer. Sideways clearance is generated at 0.9 mm and checked from real bead widths against a conservative 0.5 mm requirement with a 0.025 mm numerical guard. Each whole print, including the helpers, is checked for missing components and unsupported starts.

After cooling, cut the deliberate small ties at fixed outside rails, then cut/peel the exterior aids outward in short sections. The axial shells are split into two outside halves. A whole half can be blocked by a diagonal, so removal may require cutting the accessible 0.8 mm wall into shorter sections. Physical tool access and release remain unverified. Do not lever through a bore, pull a spring tip or pry on the socket floor. Stop if removal needs force on a functional thin part.

## Every overhang needs a decision

The layer audit records every broad unbacked component above 2 mm², including partial overhangs on an otherwise connected part. `overhang-decisions.json` contains explicit, snapshot-specific judgments; `qualify.py` rejects unknown or obsolete cases, stale reports and unreviewed slicer warnings. These decisions permit only bounded physical trials. They never make `full_set_ready` true.

Backing counts and a recorded 0.2 mm gap do not mean an entire broad area is backed. The gap describes only the credited beads at the required lower layer; it is not the minimum helper-to-part separation, which the adjacent-layer side-gap checker measures separately. The key webs at 4.0 mm have about 105 directly-beneath samples under small interior caps within a 41.3 mm² broad region. A sensor shoulder at 26.2 mm has only two such samples within a 12.53 mm² region. Neither is called fully supported: the remaining borders/bridges are visible in the actual-layer sheets and require the named full-size physical trials. These receipts do not quantify a percentage of helper-backed area.

The key trial covers the 14.1 mm mounting-opening bridge, the socket floor, smaller stop/rear-wall bridges and both complete clips. Full-size lightweight trials preserve the actual upper-key joints, cage guides, sensor roots and print heights. A trial that passes may become the usable part; it does not imply another duplicate full-size print is required.

Slicer floating-region/cantilever warnings are retained. Ordinary CAD aids deliberately stop below the part and are not typed as algorithmic supports. Their real backing is checked independently, but the warnings also cover residual bridge/adhesion risk and must not be erased or called physical success.

## Evidence and reproducibility

- `manifest.json`, `geometry-checks.json`: editable-source and exact normal-STL hashes; one closed body per normal part; bought-part routes, clip-arm preservation, thumb opening and 16 battery-above-key configurations.
- `print-checks.json`, `slice-clearances.json`: actual prepared normal/helper mesh comparisons; all model, support, interface and brim bead footprints across every working space; actual helper separation and whole-print starts.
- `start-audit-regressions.json`: eight cases prevent sideways backing credit, accepting two empty layers, overlooking a real missing floor, inventing an early floor, crediting an entire boundary face from one corner bead or accepting an unprinted mesh sliver as backing.
- `strength-checks.json`, `overhang-review.json`: measured sections/track counts and explicit per-case bounded-trial judgments. Physical flags remain false.
- `reopen-checks.json`, `reopened-clearances.json`: the actual delivered archive has its changed-setting registration restored and verified. The complete project is reopened and re-sliced by Bambu CLI using embedded settings only; all global configuration values, effective object values and actual paths are compared. GUI open/save remains untested.
- `*-slice-views.png`, `*-overhang-views.png`, `*-overview.png`: actual layer paths, every reported broad-overhang layer and exported model/helper overviews. Every project's receipts bind its slice images and contact sheets to that exact project and audit. Purple previous-layer paths, rather than the grey previous mesh outline, establish backing.
- `overview-checks.json`: binds all four overview images to the exact source normal/helper assembly meshes, main project, manifest and rendering script.
- The root integration test binds the exact models, seven trial projects, checkers, helpers, reports and negative control. Run root `npm run check` before committing; repeat affected generation/checks after changes.

Start with the small 7.9 mm key/clip trial. If it will not slide lightly from a bare rod end, stop and use the bore-bracket trials rather than forcing it. Verify helper release, switch/socket insertion, bridge droop and key operation. Then test the complete carrier, cage/gate and sensor projects. Print height, retention, comfort and repeated flexing remain real-part acceptance gates. Populated PCB underside and exact wire/solder bends are unmeasured.

## Independent assessment

Opus 5.5's initial R12 assessment confirmed the support-exclusion and cleanup-evidence problems. Its first R13 review did not approve that candidate and identified further backing, contact-gap, stability, coverage and test-piece problems. Those findings drove the stricter checks and local repairs.

The final Opus 5.5 recheck independently inspected current hashes, meshes, embedded settings, actual paths and images. It verified the repaired key load path, exported setting registration, actual-bead backing, per-project image freshness and print-first naming. It accepted the 7.9 mm small key/clip test conditionally, with nothing physically verified. The full carrier trial must wait for clean helper release, acceptable switch-opening sag and no rim/rail splitting in that small test. The cage/gate and sensor trials need the helper-release result; a key-specific opening failure alone does not block those separate trials.

The recheck also identified the missing overview-image receipt. A subsequent reporting-only repair added `overview-checks.json` and its integration assertions, corrected the coupon rail description and made partial-backing limitations explicit. No CAD mesh, helper geometry, settings or toolpaths changed after that final Opus artifact review. The primary agent checked this reporting change separately; it is not new physical evidence. The measured helper side-gap minimum of 0.52 mm is close to the 0.5 mm screen, so clean release remains the first real-part gate.

Gemini 3.8 Flash High supplied an advisory pass while support-routing trials were unresolved. Its exterior-aid alternative was investigated. It did not run CAD/slicing checks; unverified physical-fusion claims and suggestions changing the clip contact profile were not adopted as facts.

## Research: why a hole can close

Support is only one mechanism. Check material in the actual slice separately from thermal sag, first-layer squish, small-hole compensation, seams/blobs/stringing, gap filling and mesh/export errors. No numerical path scan predicts the final thermal shape.

- [Prusa support material](https://help.prusa3d.com/article/support-material_1698): contact distance and geometry affect support and removal.
- [Bambu tree-support implementation](https://github.com/bambulab/BambuStudio/blob/master/src/libslic3r/Support/TreeSupport.cpp): source for generation; a blocker is not evidence of empty final paths.
- [UltiMaker support settings](https://support.ultimaker.com/articles/Knowledge/1667417606331): the support-distance/removal trade-off, not validation of this PETG recipe.
- [Prusa elephant-foot compensation](https://help.prusa3d.com/article/elephant-foot-compensation_114487): first-layer widening can reduce openings.
- [OrcaSlicer precision settings](https://github.com/OrcaSlicer/OrcaSlicer/wiki/quality_settings_precision): hole compensation and slicing gap-closing settings are distinct mechanisms to inspect, not settings to change blindly.
