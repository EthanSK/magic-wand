# Hardware prototypes

Prototype names preserve a complete interaction setup, not just the circuit.

## Prototype V1

The original three-button Puck.js wand is **Prototype V1**. The immutable baseline
is the Git tag `prototype-v1.0.0`; its settings are in `prototypes/v1.json`.
Work on main and use a separate profile for the next physical prototype. Do not move
this tag or silently reinterpret V1's button positions, colours or gestures.

To inspect this historical source without a new worktree, export it from the `magic-wand/` component directory:

```sh
git -C .. archive --format=tar --output=/tmp/magic-wand-prototype-v1.tar prototype-v1.0.0
```

Extract the archive into a separate scratch directory and read its `BUILDING.md` and `wand.json` before building. Create a Git worktree only if Ethan explicitly requests one. Restore the
matching device program, bridge and native receiver together; preserving only
one component is not enough. Actual flashing or installation belongs in the
local hardware workflow and must not be performed from this public repository.

The local private archive additionally preserves the installed receiver bundle,
its exact resource files, calibration and enabled feature flags. Private device
settings, calibration, binaries and local paths are intentionally not published.

This baseline preserves behaviour and recovery information; it is not a claim
that every experimental gesture has been physically accepted. Ethan subsequently confirmed table pickup and put-down both work; the acceptance
record is kept in `v1.json` without moving the original baseline tag.
