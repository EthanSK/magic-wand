# Motion controllers

One repository for Magic Wand, Control Stones and future controller projects. Each component owns its firmware, tools, tests and instructions.

| Component | Source and setup | Scope |
| --- | --- | --- |
| Magic Wand | [magic-wand/](magic-wand/README.md) | Puck firmware, Mac receiver, website and tutorials |
| Control Stones | [control-stones/](control-stones/README.md) | XIAO Sense hand controller, USB/Bluetooth sensor viewer and wiring |
| Shared checks | [shared/](shared/README.md) | Repository-wide privacy checks |

The [published Magic Wand website](https://ethansk.github.io/magic-wand/) keeps its existing address and is served from `docs/`.

The current [carbon-rod holder test prototype](magic-wand/hardware/carbon-rod-holders-r16-repair/README.md) has five keys, a separate sliding battery cage and a XIAO board holder. Use the [current 3D viewer](magic-wand/hardware/carbon-rod-holders/preview/) and the revision’s print and assembly checks before a physical trial.

## Development

```sh
npm run check                          # All component checks and repository privacy
npm test                               # Component test suites
npm run build                          # Regenerate component outputs
npm run check --workspace magic-wand    # Wand checks only
npm run check --workspace control-stones # Stones source checks only
npm run serve                          # Serve the published website locally
```

These workspace commands do not require installing dependencies. Toolchain prerequisites are documented by each component. Component checks do not flash or reconnect hardware.

Tests run locally for now. GitHub test workflows are disabled; GitHub Pages still publishes the website independently.

Read [AGENTS.md](AGENTS.md) for shared rules, then the component instructions. The root commit-and-push rule applies to all components.

<!-- Previously Magic Wand sources, tests, scripts and instructions lived at the repository root; they now live in magic-wand/. -->

## Agent instructions

Shared rules are in `AGENTS.md`; component rules are in each component's `AGENTS.md`. All reusable skills live at the repository root in `.agents/skills/`. Claude Code 2.1.277 and later can read AGENTS.md directly when there is no overriding CLAUDE.md. The root `.claude/skills` is only a symbolic link for Claude's separately documented skill discovery, not another maintained skill directory.

<!-- Previously magic-wand/.agents/skills; skills are centralized in root .agents/skills. -->

## Licence

Original Magic Wand software uses [Ethan Source-Available No-Sale Terms 1.0](LICENSE).
You may use and modify it for yourself and share it without charge; selling it
requires Ethan's written commercial licence. Control Stones, shared code,
contributed material and hardware keep their existing terms.
[LICENSING.md](LICENSING.md) defines the scope and preserved notices.
