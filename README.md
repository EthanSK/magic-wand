# Motion controllers

One repository for Magic Wand, Control Stones and future controller projects. Each component owns its firmware, tools, tests and instructions.

| Component | Source and setup | Scope |
| --- | --- | --- |
| Magic Wand | [magic-wand/](magic-wand/README.md) | Puck firmware, Mac receiver, website and tutorials |
| Control Stones | [control-stones/](control-stones/README.md) | XIAO Sense hand controller, USB/Bluetooth sensor viewer and wiring |
| Shared checks | [shared/](shared/README.md) | Repository-wide privacy checks |

The [published Magic Wand website](https://ethansk.github.io/magic-wand/) keeps its existing address and is served from `docs/`.

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

Read [AGENTS.md](AGENTS.md) for shared rules, then the component instructions. The root commit-and-push rule applies to all components.

<!-- Previously Magic Wand sources, tests, scripts and instructions lived at the repository root; they now live in magic-wand/. -->
