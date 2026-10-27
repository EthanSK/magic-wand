# Lightweight wand studies

Seven separate experiments composed from Sunny’s **Print V18 / S410-R14** (`e53e8de`), including its slimmer grip and matching direct seated loop arms. V18 and all earlier deliveries remain unchanged. These studies are not a new accepted print version.

- **Diamond net:** three crossed pairs of diagonal bands, four continuous axial rails, and the slimmest loop rim in this set.
- **Open helix:** the original two spiral paths with four axial rails and larger open spans.
- **Cross braced:** two crossed pairs of diagonal bands divide those spans into smaller cells.
- **Leaf shell:** longer curved windows, the full raised spiral strips, and a slimmer loop. This is the more enclosed comparison.
- **One wide spiral:** one 8 mm main band, with deeper backing near the hand.
- **Two wide spirals:** two 7 mm main bands with deeper backing.
- **Broad diamond frame:** two 10 mm main bands and fuller 3.4 mm connecting bands.

The last three are Ethan’s wider-strand middle ground between Diamond net and Leaf shell. The main bands taper to 62% of their starting width towards the tip, and their backing depth tapers towards 1.3 mm. Original joint collars and supporting axial rails remain full. A fuller 15 × 10.4 mm loop uses 1.45 mm skin. These add supporting material compared with Diamond net; this is geometry evidence, not proof against snapping.

The first three deliberately explore Ethan’s new “wireframe net” request. They trim the original broad helix skirts in eligible regions; Leaf shell preserves them. Solid collars, both handed control mounts, battery guides and loop locking interfaces retain the baseline geometry. The original four retain the V18 head; the three new options use the open sensor cradle below. Decorative pattern and openness are separate from tested strength.

## Review and print

Run a local HTTP server from the repository root and open `magic-wand/hardware/printed-loop-wand/lattice-study/preview/`. The default view compares the three reinforced options between Diamond net and Leaf shell. Compare the original four or one beside V18, change hand, remove the loop, turn, move and zoom. Pointer, wand-scroll and keyboard input reuse the existing immediate camera controls. Arrow keys use the selected control; Home resets the view.

Each `Print-Lattice-<name>-complete.3mf` in `magic-wand-3d-models/` includes both handed stems and one shared set of other parts: **12 build instances** for the original four, or **11** for the three open-cradle options (their cover is omitted). The clearly labelled `one-left` subset has **11** or **10**, respectively, and is the basis for every mass row. Those archives include editable geometry, prepared PETG settings and sliced paths; no print has been sent.

The process is P1S 0.4 mm, generic PETG, 0.2 mm layers, three walls and 20% infill. Normal supports are enabled for the open shafts and grips. The new cradle lies on its back, with manual support patches on its low back only and no automatic support under bridges. Its board, solder, USB and wire interiors are excluded. Automatic head supports filled functional gaps even with blockers, so do not turn them on without repeating the sliced-path checks. Support landing-source guards protect the hollow interiors; the loop retains root-only manual supports. Remove supports before assembly. Do not disable them merely to reduce the estimate.

The loop rim changes from V18’s 18 × 12 mm section and 1.45 mm skin to 13.5–15 × 9.6–10.4 mm and 1.15–1.2 mm skin. Local seating arms remain full-sized. Stem/shaft wall thickness stays at 1 mm, with the existing deeper rails; the principal body saving comes from larger openings rather than thinner joint walls.

The viewer reads the canonical [mass comparison](exports/mass-comparison.json), showing printed parts and supports separately. These are slicer estimates, not weighed objects. Hardware, battery, bought switches, sockets, caps and wires are excluded. The provisional battery envelope is unchanged.

**Fit, strength, fatigue, comfort and actual print quality remain unverified.** Start with the V18 joint/loop/button fit coupons, then a candidate shaft or small section before printing a whole wand. A connected watertight mesh is not proof against snapping. Diamond net is the most slender rim; Open helix exposes the largest spans; Cross braced adds more intersections; Leaf shell keeps more enclosure.

## Lighter open sensor holder

The new options replace the 40 × 37 mm decorative diamond shell and sliding cover with one **29.7 × 18.7 mm open cradle**. The original lower bayonet, bridge spring clip, short-edge board pockets and corner guides are retained locally. Two rounded, narrowing prongs continue upward around the sensor instead of a thick cap. Total assembly length remains 410 mm. PCB, central solder space, USB plug and forward-wire clearances are checked on the exported solid and sliced paths.

The board is exposed in this prototype. The cradle still needs a physical retention, clip-flex and plug-insertion test. Reducing the upper printed material moves the design towards Ethan’s “weight near the hand” preference; the complete hardware’s balance has not been measured. No ballast or additional battery holder is added.

## Editable source and checks

`variations.json` owns the candidate dimensions. `wand_cad.py` loads V18 as a library and changes eligible surface cutters, the outer loop section and, only for the three reinforced options, the sensor holder. It preserves each complete root arm rather than clipping it at a thin tangent, which would create a detached sliver. Shared cap, sled and switch-plate STLs are referenced directly from V18 and checked by hash. The original four also reference its head and cover. The manifest explicitly lists which shared parts each option omits.

Use the Python dependencies in `../v18/requirements.txt`. Supply new output directories; keep large build output on your chosen scratch disk. All projects are sliced again when this regeneration command is run.

```sh
python wand_cad.py --out /path/to/new-geometry-output
python verify_models.py --out /path/to/new-export-checks.json
python print_projects.py --out /path/to/new-sliced-projects
python check_sliced_paths.py --out /path/to/new-sliced-checks.json
python verify_release.py
```

After regeneration, replace `exports/` and the fourteen prepared projects together, rerun the exported-solid and sliced checks, update the release receipt with `verify_release.py --record-new`, then run the repository checks. Keep this study separate from later numbered models; changing the pinned baseline requires rebuilding and rechecking every candidate.

`exported-model-checks.json` checks actual STL connectivity, hardware regions, wire clearance, the full released loop turn/slide and sampled radial material gauges. The reported gauge is a sample at retained member centres, not a global minimum or a load rating. Exact source interfaces use a 0.03 mm³ symmetric-difference limit; differently triangulated STL surfaces allow a bounded 0.75 mm³ residual after 0.001 mm simplification and 0.0001 mm vertex rounding.

`sliced-clearances.json` samples straight and arc extrusions at 0.5 mm spacing through wire, battery, socket, clip, cam and loop-airflow routes. It includes support features. External removable supports may occupy lattice gaps. These checks do not measure force or certify a finished print.
