# R14 printability and strength audit

## Decision

Digital checks support a **bounded full-carrier experiment**, not physical acceptance or an unconditional full-set print. Claude Opus 5.5 completed an independent review of the exact print files and a follow-up review of the expanded evidence, accepting the full-carrier trial as a bounded experiment. Both reviews and the final primary review are complete; the exact CAD, meshes, helpers and prepared 3MFs stayed unchanged during the evidence refinements.

The first file is `exports/trial-Key_Carrier/PRINT-FIRST-Pyramid-Key-Test.3mf`. It contains the complete lightweight five-key carrier with its real new neighbours, joints and full height, plus labelled sacrificial exterior walls. `exports/AFTER-KEY-TEST-Pyramid-Holder-R14.3mf` contains the four finished parts and their required aids, for use only after successful physical trials. Bare source STLs omit those aids.

## Changed design and limits

Two upper keys now sit at X +/-9.2, Y 19.3 mm above three lower centres at X -18.4/0/+18.4, Y 0. The upper pair moves inward 13.8 mm each. Default viewer orientation is two toward the tip, derived from CAD parameters into the actual initial HTML control. The earlier wide thumb opening is explicitly superseded.

Reference caps are 16.6 by 17.5 mm, not measured bought-part dimensions. Independent 3 mm vertical strokes and provisional 0.4 mm allowance on every side of every cap retain at least 1 mm between swept boxes. Nominal gaps are 1.8 mm. This is a conservative candidate screen within its assumptions, not proof of minimum possible spacing, actual wobble or physical noncontact. Actual cap size, wobble, combinations of full presses and grip comfort must be tested.

R13 bought interfaces and fixed reinforcements remain. The new exported battery holder, gate and sensor are byte-identical to R13; `exports/design-differences.json` binds that comparison. All four parts are still checked in the new prepared project.

## Exact prepared recipe

Bambu Studio 02.08.02.61; P1S, 0.4 mm nozzle, PETG, 0.2 mm layers, 3 walls and 20% infill. Automatic supports off and no brim. Every build instance and effective per-object override is checked. CLI export drops changed-key registration; the generator restores metadata only after asserting the actual sliced values match. Reopening/re-slicing embedded settings preserves effective values and passes actual-path checks. GUI open/save and other printer/material recipes remain unverified.

Rod axes print vertically. All real extrusion types, including ordinary-model CAD helpers, are included in the opening scans. Helper contacts leave one empty actual 0.2 mm layer. Ordinary sideways helper clearance is separately checked against same/adjacent-layer bead widths with a 0.5 mm conservative requirement and full sampling guard; deliberate fixed-rail cut tabs are the named exception to sideways separation, not to functional-space scans.

## Per-part coverage

| Part | Functional openings and routes checked | Broad partial-overhang cases | Smallest conservative helper gap | Weak-point decision |
|---|---|---:|---:|---|
| Key_Carrier | Both rod bores/slits, external wire bus; all five nominal/max sockets and complete loading paths; switches and mounting openings. | 48 | 0.5201 mm | All five complete key-to-clip paths >=11.37 mm² CAD and >=10.80 mm² printed material at scanned sections; each added rail checked separately. Rim/floor/posts/stops and four row joints have actual section/track decisions. |
| Battery_Holder | Both rod bores/slits, both wire buses, full cell reserve/loading, guide slots and complete upward gate route. | 60 | 0.7361 mm | 2 mm crossbars/stringers, 1.6 mm guide outside walls, braces and clip radial tracks checked; bridge sag and pouch-safe retention require trials. |
| Battery_End_Gate | Rod clearance and wedges against cage guides/cell reserve, gate travel, intended interference and retention stops in assembly. | 0 | No helper | Both 1.2 mm sliding necks and central grab bar checked in the broad-face-down orientation; empty gate cycling required. |
| XIAO_Rod_Holder | Both clip bores/slits, PCB, upward USB and external wire route; populated underside remains unmeasured. | 14 | 0.7275 mm | Fixed 2 mm rails, 2.1 mm roots, axial rails and clip radial tracks checked; free lower spring arms unchanged. |

All four final meshes are single watertight bodies. Five full nominal/maximum socket routes, switch lands, full independent cap envelopes and 16 battery-above-key poses/loading paths pass. Free clip arms, rigid rod corridors, external wire paths and upward USB remain checked. Numeric guards are not manufacturing tolerances.

## Bridges, backing and removal

The report lists 170 snapshot-specific broad-overhang decisions across the main and first-trial projects. Every reported case, including normal-part and whole-print/helper starts, has an explicit feature, reason and required physical test in `overhang-decisions.json` and each project’s `overhang-review.json`. The saved actual-path layer views cover every affected layer. Fresh reports quantify backed fraction, residual area and residual component bounds for broad patches and backed starts. Unknown cases, stale sources/settings/projects or warnings fail qualification.

The new upper socket floors start at print layer top 32.8 mm with exterior aid beads one empty layer below. Actual bead-footprint measurement covers about 35% of the left upper broad initial patch and 64% of the right, not either complete face. At assembly Y 18.813, Z 4.5 mm, the left floor reaches X -1.6354 while its helper at Y 18.413 stops near X -6.0565, leaving about 4.42 mm toward the rod. Coverage also varies through the floor depth; the helper does not reach Z 5.25 mm. Inspect both entire floors, especially the left inner edge, for sag and damaged socket loading space. Bead counts alone do not measure this. Remaining spans/anchors are explicit bounded physical checks, not a fully supported-floor claim. The lower and upper mounting-opening roofs still span 14.1 mm between side lands (layer tops 21.0 and 40.4 mm). Rear walls and socket-side stops bridge about 4.47 mm between their floor and lip. These are bounded PETG trials; no support is placed inside the fit openings.

The unchanged cage uses established side and centre stringers, about 12.8 mm support-centre spacing; its first real near-floor bridge remains a physical check. The sensor’s late diagonals and C face have their own exterior aids. Do not infer backing from an unprinted mesh sliver or a bead off to one side. Nine saved layer-audit regressions exercise those failures.

The slicer’s Key_Carrier floating-cantilever warning is retained and explicitly assessed. Deliberately separated ordinary-model aid walls trigger that warning; independent actual whole-print-start and opening scans pass. This is not grounds for ignoring a new warning or predicting sag.

Hold a substantial fixed frame, cut the small fixed-rail ties, then cut/peel wall halves outward in short sections. New close neighbours do not authorize pulling through a bore or using a key floor as a lever. Diagonals may require cutting accessible 0.8 mm aid walls into shorter pieces. Rod bores, clip relief and hardware loading routes must be visibly clean before assembly. Physical access, release force and success remain unverified; stop if an aid fuses or removal loads a delicate member.

## Evidence and qualification

Per-project `print-checks.json`, `slice-clearances.json`, `strength-checks.json`, `view-checks.json`, `reopen-checks.json` and `overhang-review.json` bind the exact final project and source/checker/helper/image hashes. `exports/geometry-checks.json`, `design-differences.json`, `overview-checks.json`, `layout-comparison.json` and `delivery-checks.json` bind model/export/viewer receipts. `check_delivery.py` verifies the complete set, including the actual initial orientation control and permanent revision/hash pointer.

Codex inspected actual layout comparison, per-part overhang views and prepared geometry. Numerical opening and section scans cover all layers; this is not a force, fatigue, thermal-sag or material simulation. Independent review disposition is recorded below only after completion.

## Physical acceptance

Print the complete carrier first using the prepared recipe. Check bed adhesion, all bridge roofs/floors, every open hole and helper release before fitting hardware. Slide the clips from a bare rod end. Fit all five real switches/sockets/caps and press neighbours separately and together through full travel and ordinary sideways play. No cap contact, binding, cracks, whitening, layer splitting or excessive rail bending is acceptable. Check whether the centred upper keys reduce twisting and improve grip.

Only then proceed to cage/gate and sensor trials: inspect bridges, empty gate cycling by its centre bar, actual cell loading/retention without pouch pressure, real populated-board underside and lead clearances. Force, repeated use, fatigue, comfort, retention and complete assembled acceptance remain unverified. No message has been sent and monitoring remains stopped.

## Review disposition

- N7, Codex: fixed the viewer importing an obsolete 25 mm thumb-opening description; R14 owns its accurate pyramid description, generated initial orientation and HTML/renderer hashes. The final UI has source/HTTP checks, not a manual browser claim.
- N8, Opus: accepted the partial upper-floor backing as a nonblocking bounded-trial risk; expanded actual-bead area reporting and named the left inner-edge test. Codex measurement corrected the review's over-broad whole-right-floor backing statement.
- N9, Opus: expanded floor-specific section/track probes to all five keys. Existing rim and rail probes already covered all five, so that part of the initial observation was withdrawn.
- N10, Opus: hardened re-slice freshness guards for every checker dependency and coverage arithmetic for both partial overhangs and backed starts. All actual reports were already current; these assertions prevent future stale evidence passing. Targeted checks passed after this report-only hardening.
- Neighbouring fixed rails have intentional 0.2 mm nonfunctional slits and already join above. PETG may fuse those slits; fit and strength do not depend on their staying separate. Do not pry them open. Functional bores, clip gaps and hardware routes still require zero obstructing beads.
- Helper heuristics remain revision-specific. The sockets are not mirrored, so arbitrary sign mirroring is inappropriate; another layout requires new slices, complete evidence and review. No unmeasured cap fit, bridge sag, helper release or force is treated as established.

Measure the real caps before printing: the 16.6 by 17.5 mm footprint and 0.4 mm side allowance must contain their actual size/play. Widen pitch/rows if those assumptions fail rather than forcing neighbouring caps.
