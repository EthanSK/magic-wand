# Verified lessons

## The public sources reproduce the installed wand exactly

The runtime version is `wand-` plus the first 12 hex digits of the SHA-256 of the device program
from its `// Adjust only` line; the bridge revision is the SHA-256 of the compacted bridge. With the
original statement splitter and compactor, the imported sources reproduced the private upload
commands, runtime, boot image and bridge byte for byte (16 October 2026). Keep those algorithms in
`scripts/device_build.py` unchanged unless the receiver changes with them: the receiver compares
both identifiers on every connection. `tests/manifest.test.mjs` recomputes them.

## Running Espruino code outside the Puck

The bridge patches the live device with `Function.replaceWith` and finds its targets through
`E.internal.watches`, `Puck['#onaccel']` and `NRF['#onconnect']`, matching callbacks by their source
text. A host must expose those lookups and give every top-level device function a forwarder whose
`replaceWith` swaps the target and whose `toString` returns the target’s source. Replacing a global
name is not enough: the pin watch still holds the old function. The test sets a stale global
`onMoveButton` to prove the bridge patches the watched callback.

Values created inside a Node `vm` context have that context’s prototypes, so
`assert.deepStrictEqual` rejects an equal array from it; copy with `Array.from` first.

The bridge keeps the gyro on for one second after a gesture. A test that expects the sensor off
must advance past that grace; the base program alone switches it off immediately.

## Aim to gyro in the demo

The page only posts the visitor’s aim while it changes. Deriving a rate from a long-stale sample
spreads the next movement back across the pause and loses most of it. The worker anchors the
previous aim just before each new one after a pause, then averages the rate over 50 ms.

## Three.js versions

The three@0.186.1 npm package has no `build/*.min.js`, and the GitHub `r186` tag has none either.
three@0.185.1 includes them, and its files are byte-identical to the copies Agentic Mouse vendors,
so the site pins 0.185.1.
