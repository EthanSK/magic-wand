# Hardware prototypes

Prototype names preserve a complete interaction setup, not just the circuit.

## Prototype V1

The original three-button Puck.js wand is **Prototype V1**. The immutable baseline
is the Git tag `prototype-v1.0.0`; its settings are in `prototypes/v1.json`.
Use a separate branch and profile for the next physical prototype. Do not move
this tag or silently reinterpret V1's button positions, colours or gestures.

To recover this source, create a separate checkout with:

```sh
git worktree add ../magic-wand-prototype-v1 prototype-v1.0.0
```

Read that checkout's `BUILDING.md` and `wand.json` before building. Restore the
matching device program, bridge and native receiver together; preserving only
one component is not enough. Actual flashing or installation belongs in the
local hardware workflow and must not be performed from this public repository.

The local private archive additionally preserves the installed receiver bundle,
its exact resource files, calibration and enabled feature flags. Private device
settings, calibration, binaries and local paths are intentionally not published.

This baseline preserves behaviour and recovery information; it is not a claim
that every experimental gesture has been physically accepted. Table pickup and
put-down still require Ethan's final physical check.
