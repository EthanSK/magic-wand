# Licensing

## Magic Wand software

Ethan Sarif-Kattan's original Magic Wand software and documentation are offered
under [Ethan Source-Available No-Sale Terms 1.0](LICENSE).
You may download, use and modify the covered software for yourself or internally
within your organization, including at work, and share it without charge.
Selling the covered software, modifications, hosted access or paid bundles
requires Ethan's separate written commercial licence.

This is a custom source-available licence, not an OSI open-source licence.
The complete terms in LICENSE take precedence over this summary.

## Covered material

The licence covers only rights Ethan owns or is authorized to license in the
original Magic Wand software and its documentation:

- The `magic-wand/` component, except the exclusions below.
- The original Magic Wand website, simulator and generated device downloads in
  `docs/`, except bundled dependencies, fonts and excluded hardware material.
- Before the component split, the equivalent first-party `device/`, `receiver/`,
  `scripts/`, `data/`, `integrations/`, `tutorials/` and `tests/` directories,
  `README.md`, `BUILDING.md`, `SOURCES.md`, `BEHAVIOUR_CHECKPOINTS.md` and
  `wand.json` at the repository root, with the same exclusions.

A path being listed does not transfer somebody else's copyright to Ethan.
Explicit third-party terms and the exclusions below always take precedence.

## Material keeping its existing terms

The original project [MIT notice](LICENSES/retained-MIT.txt) continues to apply
to the following material, except any part carrying its own third-party terms:

- `control-stones/` and its former location `prototypes/control-stones/`.
- `shared/`, repository-wide agent instructions and `.agents/` skills.
- Hardware, mechanical designs, CAD, print projects and model previews, including
  `magic-wand/hardware/`, former root `hardware/`, `magic-wand-3d-models/`,
  hardware/model files copied into `docs/`, and hardware prototype material in
  `magic-wand/prototypes/` or former root `prototypes/`.
- The contributed instructions and lessons in `magic-wand/AGENTS.md` and
  `magic-wand/LEARNINGS.md`, and their former root locations.
- Contributed hardware tests matching `magic-wand/tests/printed-wand-*.test.mjs`,
  `magic-wand/tests/xiao-local-bridge.test.mjs` and
  `magic-wand/tests/xiao-wand-dashboard.test.mjs`, including their former root
  `tests/` locations.
- Other repository material outside the covered Magic Wand paths above.

These conservative exclusions preserve the existing offer for Sunny Whang's
contributions and the other controller and hardware work. They do not imply
permission to relicense another contributor's work. Changing the licence of
those contributions requires the relevant rights holder's permission.

Bundled dependencies and imported material keep their own notices and licences:

- Three.js in `docs/lib/` retains its MIT licence.
- Fonts in `docs/fonts/` retain their SIL Open Font License notices.
- Espruino modules retain `magic-wand/device/modules/LICENSE` (formerly
  `device/modules/LICENSE`).
- Reference hardware, images and other imported assets retain their individual
  notices, including the Creative Commons notices beside those files.

[SOURCES.md](magic-wand/SOURCES.md) records imported material and its provenance.
An earlier MIT attribution there describes the imported version; it does not
claim that an upstream project's current licence is still MIT.

## Earlier versions and commercial rights

The history's licence text may be replaced, but this cannot withdraw valid
permissions already granted under an earlier licence. Existing third-party and
contributor rights remain in force. The no-sale terms apply only to the rights
Ethan can offer under them; they do not make the complete repository or its
dependencies exclusively his to sell.
