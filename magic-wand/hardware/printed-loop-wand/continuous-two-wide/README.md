# Two wide spirals — one upper shaft

The existing Two wide spirals design remains available. This candidate combines its two upper shaft pieces into **one 206 mm printable part**, with open lattice across the former centre joint. The P1S profile allows 250 mm of print height. The crossed wide bands continue along the whole shaft. The finger loop uses the same detachable lift, turn and catch as the earlier design, on either handed grip.

The shaft narrows gradually to an 8.5025 mm core radius at the tip instead of 8.95 mm. To keep a continuous taper, the tip bayonet and its open sensor cradle are both reduced to 95% of their former width. **Use this candidate's cradle with its shaft:** the older head connector is a different size. The grip-side bayonet, button areas, loop and board's corner pockets and spring clip are preserved. A 10.4 mm wire route remains. The open cradle leaves the board exposed.

The complete 3MF includes both handed grips and one shared set of other parts (10 build instances). The optional one-left file contains one complete left wand (9). Both are sliced for the existing P1S 0.4 mm PETG profile, 0.2 mm layers, three walls and 20% infill. The shaft uses automatic supports with an interior support-landing blocker. The cradle lies on its back with manual low-back supports; remove supports before assembly.

The source and exported-solid checks cover the old grip interface, loop paths, board clip and pockets, the scaled tip joint's entry/turn/stop, the wire route, the former seam openings, connected meshes and floating layer starts. The sliced-path report checks wire, battery, buttons, loop and cradle clearances, including supports. Small support feet on the build plate outside the open back are reported separately. **These checks do not prove physical fit, clip flexibility, strength or print quality.** Test the cradle and fit pieces before the full print; no print has been sent.

## Rebuild

Install the dependencies in `../v18/requirements.txt`. Use new output directories and the designated scratch disk for large generated files. The checked existing Two wide spirals components are referenced from `../lattice-study/exports/two-wide`, not copied as a new maintained source.

```sh
python wand_cad.py --out /path/to/new-geometry
# Copy the checked outputs into exports/, then:
python verify_models.py --out /path/to/exported-checks.json
python print_projects.py --out /path/to/sliced-projects
# Copy the checked projects and reports into place, then:
python check_sliced_paths.py --out /path/to/sliced-checks.json
python verify_release.py
```

The `exports/release.json` receipt records the source, generated meshes and project hashes. After updating generated outputs and reports, regenerate it with `verify_release.py --record-new /path/to/receipt.json`, copy that receipt to `exports/release.json`, and run the repository's checks. Keep the older lattice studies and their files unchanged.
