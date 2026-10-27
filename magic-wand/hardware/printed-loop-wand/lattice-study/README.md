# Lightweight wand studies

Four separate experiments composed from Sunny’s **Print V18 / S410-R14** (`e53e8de`), including its slimmer grip and matching direct seated loop arms. V18 and all earlier deliveries remain unchanged. These studies are not a new accepted print version.

- **Diamond net:** three crossed pairs of diagonal bands, four continuous axial rails, and the slimmest loop rim in this set.
- **Open helix:** the original two spiral paths with four axial rails and larger open spans.
- **Cross braced:** two crossed pairs of diagonal bands divide those spans into smaller cells.
- **Leaf shell:** longer curved windows, the full raised spiral strips, and a slimmer loop. This is the more enclosed comparison.

The first three deliberately explore Ethan’s new “wireframe net” request. They trim the original broad helix skirts in eligible regions; Leaf shell preserves them. Solid collars, both handed control mounts, battery guides, board/head clearances and loop locking interfaces retain the baseline geometry. Decorative pattern and openness are separate from tested strength.

## Review and print

Run a local HTTP server from the repository root and open `magic-wand/hardware/printed-loop-wand/lattice-study/preview/`. Compare all candidates or one beside V18, change hand, remove the loop, turn, move and zoom. Pointer, wand-scroll and keyboard input reuse the existing immediate camera controls. Arrow keys use the selected control; Home resets the view.

Each `Print-Lattice-<name>-complete.3mf` in `magic-wand-3d-models/` includes both handed stems and one shared set of other parts: **12 build instances**. The clearly labelled `one-left` subset has **11** and is the basis for every mass row. Those archives include editable geometry, prepared PETG settings and sliced paths; no print has been sent.

The process is P1S 0.4 mm, generic PETG, 0.2 mm layers, three walls and 20% infill. Normal supports are enabled for the open shafts as well as the grips. Support landing-source guards protect the hollow interiors; the loop retains root-only manual supports. Remove supports before assembly. Do not disable them merely to reduce the estimate.

The loop rim changes from V18’s 18 × 12 mm section and 1.45 mm skin to 13.5–15 × 9.6–10.4 mm and 1.15–1.2 mm skin. Local seating arms remain full-sized. Stem/shaft wall thickness stays at 1 mm, with the existing deeper rails; the principal body saving comes from larger openings rather than thinner joint walls.

The viewer reads the canonical [mass comparison](exports/mass-comparison.json), showing printed parts and supports separately. These are slicer estimates, not weighed objects. Hardware, battery, bought switches, sockets, caps and wires are excluded. The provisional battery envelope is unchanged.

**Fit, strength, fatigue, comfort and actual print quality remain unverified.** Start with the V18 joint/loop/button fit coupons, then a candidate shaft or small section before printing a whole wand. A connected watertight mesh is not proof against snapping. Diamond net is the most slender rim; Open helix exposes the largest spans; Cross braced adds more intersections; Leaf shell keeps more enclosure.

## Editable source and checks

`variations.json` owns the candidate dimensions. `wand_cad.py` loads V18 as a library and changes only eligible surface cutters and the outer loop section. It preserves each complete root arm rather than clipping it at a thin tangent, which would create a detached sliver. Shared head, cover, cap, sled and switch-plate STLs are referenced directly from V18 and checked by hash.

Use the Python dependencies in `../v18/requirements.txt`. Supply new output directories; keep large build output on your chosen scratch disk.

```sh
python wand_cad.py --out /path/to/new-geometry-output
python verify_models.py --out /path/to/new-export-checks.json
python print_projects.py --out /path/to/new-sliced-projects
python check_sliced_paths.py --out /path/to/new-sliced-checks.json
python verify_release.py
```

After regeneration, replace `exports/` and the eight prepared projects together, rerun the exported-solid and sliced checks, update the release receipt with `verify_release.py --record-new`, then run the repository checks. Keep this study separate from later numbered models; changing the pinned baseline requires rebuilding and rechecking every candidate.

`exported-model-checks.json` checks actual STL connectivity, hardware regions, wire clearance, the full released loop turn/slide and sampled radial material gauges. The reported gauge is a sample at retained member centres, not a global minimum or a load rating. Exact source interfaces use a 0.03 mm³ symmetric-difference limit; differently triangulated STL surfaces allow a bounded 0.75 mm³ residual after 0.001 mm simplification and 0.0001 mm vertex rounding.

`sliced-clearances.json` samples straight and arc extrusions at 0.5 mm spacing through wire, battery, socket, clip, cam and loop-airflow routes. It includes support features. External removable supports may occupy lattice gaps. These checks do not measure force or certify a finished print.
