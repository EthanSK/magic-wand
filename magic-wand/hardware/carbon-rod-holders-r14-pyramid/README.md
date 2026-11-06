# Carbon-rod holders R14: compact pyramid

Two keys sit centred above three, toward the tip in the existing key plane. This supersedes the outboard thumb pair and wide thumb opening. It responds to pressing the side keys twisting the wand and requiring a hard grip. R13 is preserved unchanged.

## Layout and interfaces

- Lower centres: X -18.4, 0, +18.4 mm, Y 0. Upper centres: X -9.2, +9.2 mm, Y 19.3 mm. The viewer defaults to two toward the tip.
- The upper pair moves inward 13.8 mm each from R13. Lower pitch reduces 0.1 mm and row spacing reduces 1.2 mm. The reference caps have 1.8 mm gaps; they are 16.6 × 17.5 mm illustrations, not measured purchased caps.
- Independent 3 mm vertical strokes with an added provisional 0.4 mm sideways allowance on each cap side retain at least 1 mm between swept boxes. Check real cap size, wobble and full presses before accepting this spacing.
- Preserve the five bought switch/socket seats, R13 fixed load rails and 2 mm row joints, external wires, upward USB, near-closed slide-on clips and separate battery above toward the tip.
- Battery holder, gate and sensor exported assembly meshes are byte-identical to R13. The complete set is still audited with the new prepared layout; no physical acceptance is implied.

## Review and print files

The permanent current-model viewer is `../carbon-rod-holders/preview/`. It follows the generated revision/hash pointer. `preview/` is the archived R14 viewer. `exports/layout-comparison.png` compares the actual old/new carrier exports with illustrative caps.

`cad.py` and `parameters.json` own the editable model, composed with frozen R12/R7 bought interfaces. Regenerated meshes and print/viewer files belong in the same checked commit. Bare `*-SOURCE-REQUIRES-PREPARATION.stl` meshes omit the labelled sacrificial print helpers and are not independently prepared print files.

The intended first trial is the complete lightweight five-key carrier, `exports/trial-Key_Carrier/PRINT-FIRST-Pyramid-Key-Test.3mf`. It preserves the new staggered neighbours, row joints and full print height. The complete four-part project is `exports/AFTER-KEY-TEST-Pyramid-Holder-R14.3mf`, for use only after the key trial succeeds. See AUDIT.md for actual qualification and remaining risks; filenames alone are not approval.

Prepared recipe: Bambu P1S, 0.4 mm nozzle, PETG, 0.2 mm layers, 3 walls, 20% infill, automatic supports off and no brim. Keep orientations and embedded object overrides. Bores print vertically. Exterior CAD walls intentionally back selected starts with one empty actual layer and measured sideways clearance. CLI reopening and re-slicing is checked separately; GUI open/save and another printer/material require verification.

## Reproduce

Use the pinned requirements environment and Bambu Studio CLI. Run `cad.py`, `verify_geometry.py`, `compare_revision.py`, `layout_views.py`, `print_project.py --slice --scratch <fresh-external-scratch>`, then `verify_slice.py` and `strength_audit.py`. Build the first trial using `print_project.py --slice --only Key_Carrier --scratch <another-fresh-external-scratch>` and run those audits with `--exports exports/trial-Key_Carrier` (plus its exact `--project` for the slice checker).

Run `test_start_audit.py`, `review_views.py --exports <each-project-directory>`, `reopen_project.py --exports <each-project-directory> --scratch <fresh-external-scratch>`, `audit_views.py`, snapshot-specific `qualify.py` decisions and `build_preview.py`. Do not reuse old overhang decisions for a new slice. Root `npm run check` is required before committing. Keep large temporary slicer data on the shared external scratch volume.

## Physical trial

Measure the real cap footprint/play before printing; widen spacing if it exceeds the stated references/allowance.

After cooling, hold a substantial fixed frame close to each helper. Cut the small ties on fixed outer rails first. Cut/peel exterior wall halves outward in short sections, without levering a spring, socket floor or bearing face. Some diagonals require cutting a wall into shorter sections; physical access and release are unverified. Stop on fused walls, damage, whitening, cracks or force needed at delicate parts.

Check every opening visually. Slide clips on from a bare rod end, never snap sideways. Fit all five real switches, sockets and caps. Press each key fully and with ordinary sideways movement, including combinations of neighbouring keys; caps must not touch. Test the two upper keys for twisting and grip comfort, then repeated presses for rail/joint bending or splitting.

For the later complete set, check cage bridges, cell loading and retention without pressure on the pouch, empty gate cycling using its central bar, real populated-board underside and upward USB/external lead clearance. Physical adhesion, bridge sag, cleanup, fit, breaking force, fatigue, battery retention and comfort remain unverified. No CAD or slice check guarantees that nothing will snap.

The 0.2 mm slits between neighbouring fixed rails are nonfunctional and may fuse; the rails already join above. Do not pry those slits open. Inspect both upper floors for sag, especially the left inner edge; partial backing is quantified in AUDIT.md.
