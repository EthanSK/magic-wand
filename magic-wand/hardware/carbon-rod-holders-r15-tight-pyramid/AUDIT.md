# R15 printability audit

Current checkpoint: the strengthened-spine CAD, geometry, both actual slices, strength screens, layer regressions, images and CLI reopening checks have passed. Repository-root checks and the independent final artifact review have completed. The carrier remains a gated first physical experiment, not a guaranteed print or a full-set approval. No hard RAM cap or host-pressure gate is used. The exact per-pose export completed at about 547 MiB peak on its worker; this observation is not a future memory guarantee.

Audit date: 2026-11-06. Implementation: Claude Opus 5.5. Primary verification: Codex. The initial independent Opus review identified the corrections below. Those corrections are implemented and the scoped independent artifact review supports the clearly labelled complete-carrier experiment with its measurement and physical-test gates. This is not full-set readiness.

## Decision and scope

R15 targets the existing Choc V1 switch/socket interfaces and inferred 17.5 x 16.6 mm caps. Saker Mini switches and 18 x 18 mm caps are not qualified by this revision; they need a separate fit and spacing revision.

The exact prepared carrier is proposed as the first bounded physical experiment. The four-part project is prepared for subsequent trials only. Full-set readiness, physical print quality, fit, helper removal, strength, fatigue, battery retention and comfort remain false/unverified. Do not infer a guaranteed print from a valid mesh, successful slice or screening threshold.

Recipe: Bambu P1S, 0.4 mm nozzle, PETG, 0.2 mm layers, 3 walls, 20% infill, automatic support off and no brim. Bambu Studio 02.08.02.61. The embedded process base is 0.28mm Extra Draft @BBL X1C, with the listed 0.2 mm overrides and 10000 mm/s² default acceleration retained. Effective global and per-object overrides are registered in each portable project. CLI reopening/re-slicing was checked separately; GUI open/save and other printer/material recipes were not tested.

## Intended change

- R means revision. Lower centres sit at X 0 and ±18.7 mm; upper centres at X ±9.35 mm, Y 17.8 mm. Compared with R14: lower pitch +0.3 mm, row spacing -1.5 mm, each upper key 0.15 mm outward.
- Reviewer N11 is resolved for orientation only. Choc caps are longer along the stem-post axis. verify_geometry.py finds the sourced switch mesh's two 1.2 x 3.0 mm post footprints 5.7 mm apart along X, and Adafruit's 5737 underside photo shows both stem sockets along the wider cap side. The reference is now 17.5 mm (X) x 16.6 mm (Y); Earlier references put the longer side on Y. Under the new inferred orientation, R14's nominal X gap would be about 0.9 mm before sideways play; that is not a measurement of the bought caps. The nominal gap is 1.2 mm on both axes.
- Cap size is inferred, not measured. The 17.5 x 16.6 mm comes from the same-family Adafruit 5111 listing; the 5737 page gives no dimensions, and a scaled photo estimate (about 18.2 x 17.3 mm) is unreliable. The screen keeps independent 3 mm travel, a 0.4 mm side allowance on every cap side and a 0.4 mm minimum residual gap; the achieved minimum is 0.4 mm. Measuring a real cap mounted on a switch is a pre-print gate.
- The frame edge below the bottom row is recessed to Y -7.9 from R14's -13.8, 0.4 mm behind the inferred cap fronts. The face cannot sit further back because it carries the switch flange land to Y -7.5. Below a softened bumper face (Z 8.7-10.8), a 45-degree chin recedes 1.7 mm to Z 7.0, ending 2.1 mm behind the cap fronts. A shelf at Z 7.0-8.7, reaching back to Y -4.5, restores depth under the switch housing. Above the centre clip crown, a V-shaped notch opens 3.15 mm at the front face. A concave groove would need supports on the bed face, so it is not provided.
- The leading clip moves from Y -12 to -6.1, with the same friction-spring profile. Its fixed crown edge between the ties has a 0.5 mm front chamfer; the free arms are checked unchanged. Fixed diagonals and a spine carry the clip into the key rails and the central socket floor. A second tapered spine joins the rear clip crown to both upper floor fronts (reviewer N12).
- Reviewer N13: every named helper-contact face sits 0.07-0.1 mm from Bambu's layer-middle sampling planes; the requirement is at least 0.04 mm. print_project.py asserts this and records it in print-checks.json, reducing boundary sensitivity for this checked 0.2 mm recipe. Actual empty layers are checked after export and CLI reopening; other slicer versions, placements and profiles remain unqualified.
- The inferred grip has the rod along the palm, the index finger curled under the lower edge (pad against the bumper/chin, partly in the centre notch) and the thumb pressing the keys from above. Actual hand posture and comfort need the physical trial.
- Preserve five bought switch/socket interfaces, all 20 mounting lands, the separate sliding battery cage above toward the tip, external wires and upward USB. Battery, gate and sensor exported bytes match R14. R14 remains unchanged.

## Current digital verification

The exact current CAD sources, geometry report and both prepared projects are hash-bound. The original and CLI-reopened projects pass actual opening, normal/helper agreement and whole-print start checks. Both strength screens pass; all 20 weak-point rows and the continuous key-to-clip load paths are assessed. The nine layer-audit regressions pass. Images, overhang decisions and qualification are regenerated from these files. Repository-root checks passed on the owning Mac after the Fleet source upload timed out before tests began, including privacy and both components. The existing two-test-worker setting was retained. Independent Opus artifact review completed read-only; primary verification checked the actual hashes and executed the recorded runs.

The carrier has 54 explicit normal/whole-print overhang cases in each project. All 74 battery/sensor cases match the earlier reviewed case rows exactly, and their geometry remains byte-identical to R14. The battery and gate overhang PNGs are byte-identical to the first R15 review and R14. The sensor PNG differs from the first R15 review (bcbe0ac7 prefix) and matches R14's current image (096b817d); its 14 case rows are unchanged and both Codex and Opus re-inspected the current image during final review. Reusing those exact cases does not transfer an old decision to a changed row.

## Geometry and actual paths

| Part | Functional spaces scanned | Broad patch rows, normal-part scan | Minimum helper side gap |
| --- | ---: | ---: | ---: |
| Key_Carrier | 34 | 27 | 0.7203 mm |
| Battery_Holder | 10 | 30 | 0.7361 mm |
| Battery_End_Gate | 1 | 11.3700 mm² | 10.8025 mm² |
| XIAO_Rod_Holder | 6 | 8 | 0.7275 mm |

All 51 main-project functional spaces and all 34 carrier-trial spaces have zero detected all-bead violations. Scans include normal model, explicit CAD helpers, slicer support/interface/transition and brim/raft paths; there is no removable-support exclusion. Actual neighbouring/top paths and project-normal/helper mesh agreement are checked so an empty or misplaced scan cannot pass.

The scans cover each switch, nominal and maximum socket, full nominal/maximum socket loading path, mount opening, unloaded rod bore, both clip gaps, external wires, cage reserve and complete cell loading, guide slots and gate removal, PCB, USB and sensor wire access. Geometry also checks 16 complete battery poses, all 20 flange corner lands, cap movement and unchanged free spring arms.

Both prepared projects and their reopened copies have no detected floating or missing printed components. Backing comes from actual prior-layer bead footprints, with conservative covered area and residual patches; an unprinted mesh sliver or nearby sideways bead is not credited. The nine saved layer-audit regressions passed. Numerical guards and sample spacing are not manufacturing tolerances.

## Overhang, warning and cleanup decisions

Every reported broad patch has an explicit snapshot-specific decision: 128 main-project cases and 54 carrier-trial cases (182 total) across normal and whole-print scopes. These are bounded physical-trial decisions, not claims of full backing. See overhang-decisions.json and each overhang-review.json for exact patch area, coverage, residual bounds and required test.

Current trial slice: 27 partial overhang rows with 227.601 mm² residual unbacked area, 2 support-backed islands (the lower outer floors, 10.986 mm² residual), no floating or missing components, and a minimum helper side gap of 0.7203 mm. The previous candidate had 22 rows, 219.5 mm² and 4 islands; R14 had 24 rows, 297.9 mm² and 9 islands. Eight changed case rows in each project were reviewed against the new toolpath views; only exactly unchanged complete case rows retain previous decisions.

- Bumper top chamfer and chin: the second-layer 45-degree growth strip is 11.19 mm² along the 53.4 mm bar. Inspect edge quality and adhesion. An earlier chin with a 0.25 mm lip neck printed as a vanishing sliver, leaving three unbacked lip starts. The chin now begins at Z 8.7 and the neck is at least 0.85 mm; those rows are gone.
- Lower floor starts are only partly backed (69-71% outer, 41% at the centre right edge). Inspect the complete spine-to-wing gap and all floor edges for sag before fitting a socket.
- Upper floors (trial layer top 25.4): the left floor's inner part now grows from the fixed rear spine. Its aid-backed outer part is 57% backed with 4.36 mm² residual (previously 33% and 12.09 mm², with a free 5.15 mm tongue). The right floor is no longer an island: 60% backed, 6.71 mm² residual, joined to the spine. Watch both floors from print height 25.2 to 26.4 mm and abort on curl or shift.
- Closing the rows makes some retained fixed row diagonals nearly flat along Y. Lower rear posts/walls and row webs produce 12 bridge-like shoulder patches at print heights 15.8, 16.6, 16.8 and 18.0 mm, with 79.175 mm² residual area. The separately helper-backed rear C face at 17.8 mm is not counted as a row-web bridge. Inspect every span and both end bonds before loading the upper keys. The retained 14.1 mm switch-window roofs use ordinary wall/gap-fill paths, not a guaranteed bridge recipe; the approximately 4.47 mm socket-wall spans also need a real PETG trial.
- The rear C face has a split exterior cap and an actual one-empty-layer gap at its checked start. Keep its curved partial shoulders separate from the row-web assessment and remove the cap halves outward without levering the spring arms.
- Cage crossbars/hoops span existing side/centre stringers with 12.8 mm support-centre spacing. Their actual bridges, guide shoulders and slot back walls are separate physical checks; do not load or compress a pouch cell until they pass.
- Sensor rail starts and late V diagonals have exterior backing. Cut its fixed-rail ties before peeling aids, then inspect the whole crown/diagonal junction.

The carrier has no bonded cut tabs at the finger rest. Its split clip cap and floor walls leave outward removal routes and measured sideways gaps; remove cooled aids in short sections while holding fixed material, never by levering springs or floors. Sensor ties are deliberate exceptions to the side-gap screen only; every tab still participates in the functional-space scan. Physical cleanup remains unverified.

The original CLI slice reports the Key_Carrier cantilever warning; the reopened full project reports the Battery_Holder cantilever warning. Both exact warning texts have explicit bounded-trial decisions in overhang-decisions.json. They are retained, not physically disproved. The cage and sensor have separately assessed partial bridges/shoulders regardless of which object Bambu selects for its warning. Do not enable generic automatic support over the checked recipe.

## Likely snap-point screening

Sections below are actual exported-mesh ray measurements and surviving G-code track clusters. They are local screening values, not force ratings or material simulations. Continuous key-to-clip paths are additionally scanned through intervening layers, including the revised lower front start. Both floor spines are scanned over their entire crown-to-root span with 230 front and 295 rear native mesh rays and actual extrusion tracks at every intervening printed layer. This catches narrower sections between the original convenient probes. The fixed crowns were widened locally; free spring arms and functional bores stay unchanged. The new full-span minima are about 1.36 mm with at least two tracks, against the retained 1.25 mm geometric screen and 0.02 mm allowance; these are screening values, not proof of toughness.

| Part / feature | Minimum sampled section | Minimum surviving tracks |
| --- | ---: | ---: |
| Key_Carrier: Switch-opening side rims | 1.1500 mm | 2 |
| Key_Carrier: All five socket floors including leading edges | 1.2000 mm | 3 |
| Key_Carrier: Outboard fixed key load rails | 3.2000 mm | 3 |
| Key_Carrier: Recessed lower front bumper | 2.9200 mm | 7 |
| Key_Carrier: Rear clip to upper floor spine | 1.3589 mm | 2 |
| Key_Carrier: Front clip ties to fixed rails | 2.4451 mm | 5 |
| Key_Carrier: Front clip to central floor spine | 1.3605 mm | 2 |
| Key_Carrier: Four fixed joints between key rows | 2.0000 mm | 5 |
| Key_Carrier: Fixed rear socket posts | 1.9000 mm | 5 |
| Key_Carrier: Fixed socket-side stops | 1.3500 mm | 3 |
| Battery_Holder: Reinforced roof crossbars | 2.0000 mm | 5 |
| Battery_Holder: Reinforced floor crossbars | 2.0000 mm | 5 |
| Battery_Holder: Outside gate-guide walls | 1.6000 mm | 4 |
| Battery_Holder: Outside guide diagonal braces | 1.5826 mm | 4 |
| Battery_Holder: Centre roof stringer | 2.0000 mm | 4 |
| Battery_End_Gate: Both sliding-wedge narrow ends | 1.2400 mm | 3 |
| Battery_End_Gate: Central grab bar | 1.8000 mm | 5 |
| XIAO_Rod_Holder: Fixed outside PCB rails | 2.0000 mm | 5 |
| XIAO_Rod_Holder: Fixed front diagonal root sections | 3.2134 mm | 6 |
| XIAO_Rod_Holder: Axial rails beside the rod | 2.0000 mm | 4 |

| Key | Minimum whole-path mesh area | Minimum actual printed area |
| --- | ---: | ---: |
| 1 | 11.3700 mm² | 10.8025 mm² |
| 2 | 22.5346 mm² | 21.5144 mm² |
| 3 | 11.3700 mm² | 10.8043 mm² |
| 4 | 15.8765 mm² | 15.0840 mm² |
| 5 | 16.4826 mm² | 15.5288 mm² |

The retained screening floors are 8 mm² mesh and 5 mm² printed area. The rear spine raises the upper-key paths from about 11.4 to 15.9-16.5 mm². The chin notches the front 1.7 mm of each front-clip tie; its measured section there is 2.4451 mm with five tracks, against a 2.4 mm screen. The shelf rejoins it behind the chin, where the measured section is 4.5288 mm with six tracks. The new bumper, ties and spines are not a measured bending-equivalent replacement for the removed deep webs. Every listed load case needs a real inspection and repeated assembly/pressing trial. Stop on whitening, cracks, splitting, excess bending or unreasonable force.

A targeted actual-bead check resolves reviewer Q1 without changing the model. At rear assembly Y 13.7 (print top 21.6 mm) and front Y -3.9 (print top 4.0 mm), the centre ray crosses two nominal 0.42 mm outer walls with an internal unfilled interval of about 0.527/0.529 mm. Conservative nominal bead-union coverage totals about 0.839 mm, within 1.367/1.371 mm mesh sections; these neck layers are not solid-filled. At rear Y 15.7 and front Y -2.5, variable-width gap infill covers essentially the full ray section. The existing report's median-width bead-envelope minima, 1.1438 mm rear and 1.2703 mm front, are descriptive summaries, not filled-material measurements or strength screens. This four-ray check retained all G-code parser state, sampled only print layers 4.0/5.4/21.6/23.6 mm at 0.025 mm steps, and used native section rays plus each sample's actual width. It does not model bonded plastic or breaking force. Treat the hollow necks and layer bonding as explicit first-trial risks: inspect both spines after aid removal and repeated key presses; stop on splitting, whitening or excessive bending.

## First physical trial

1. Gate: mount a real cap on a switch. Confirm its longer side runs along the stem posts (X) and measure both sides and the sideways play. If they exceed 17.5 x 16.6 mm or 0.4 mm per side, widen the pitch before printing. Confirm the prepared P1S/PETG recipe and per-object settings in Bambu Studio. Check the preview for one empty layer under the rear clip and every socket floor. Print the complete five-key carrier first, retaining its real neighbours, joints, height and aids.
2. During the print, watch both upper floors from print height 25.2 to 26.4 mm; abort on curl or shift. After cooling, inspect adhesion, the chin/shelf, all bridges, row webs, floors, diagonals and bores. Cut/peel aids outward without levering thin parts. Reject window sag, fused aids, damage or droop in a functional opening.
3. Slide clips from a bare rod end. Fit all five real sockets, switches and caps without forcing. Press each key and neighbouring combinations through full travel and ordinary sideways movement; no cap contact is acceptable.
4. Hold normally with the index finger at the lower edge. Check for poking, clip contact, twisting and excess bending. Firm upper-key presses must not lift or open the front clip. Inspect all fixed paths, both spines, the notched tie fronts and the springs after repeated pressing. Comfort and fatigue are user/physical acceptance gates.
5. Only after the carrier passes, trial the full cage, empty gate and sensor. Inspect crossbar sag, guides and bonds, gently verify cell loading/retention without pouch pressure, then populated-board underside and upward USB/external wires.

## Exact projects and receipts

| Project | SHA-256 |
| --- | --- |
| exports/AFTER-KEY-TEST-Pyramid-Holder-R15.3mf | `9f25eee3fe57fa92ccb9cde722090a8f46e81d46c670537431cd0de62dd42501` |
| exports/trial-Key_Carrier/PRINT-FIRST-Pyramid-Key-Test.3mf | `627e9df4f4a97286bc09ad8af1c3f87f38e7f1f7eae6d6f0e845bfd86341b578` |

The CAD manifest records complete editable source dependencies and normal mesh hashes. Geometry, actual slice, strength, overhang, image, reopen, overview, scene and delivery receipts bind their own checkers and exact inputs. check_delivery.py and the Node integration guard reject stale or missing proof. Reproduce using README.md; never update a pass flag by hand.

## Final independent review

The initial separate read-only Opus 5.5 review identified N11 (cap orientation/measurement gate), N12 (the free upper-left floor tongue), N13 (slicing-mid-plane sensitivity) and N14 (the unfinished lower-edge/clip relief). The original confirmed-finding attribution is Codex 0, Opus 2, shared 0; N11 was an open fit gate and N13 hardening, counted separately. Opus implemented the corrections. Current geometry, actual paths, backing decisions and strength screens support the revised bounded carrier experiment, with the mounted-cap measurement still required before printing.

The scoped independent Opus 5.5 recheck supports the gated complete-carrier first experiment. It confirmed the source/receipt agreement, final affected layer images, cap gate, floor-spine repair, helper phase guard and lower-edge geometry. It did not execute commands or recompute hashes. Primary verification checked those hashes, completed the runs and resolved the four-ray bead question as a disclosed physical-trial risk. The minor reused-image provenance wording was corrected. No physical fit, comfort, release, strength, fatigue or retention claim follows from the digital checks.
