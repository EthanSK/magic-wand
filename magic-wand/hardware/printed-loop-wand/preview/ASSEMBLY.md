# Shared assembly playback

Accessory viewers share `assembly-timeline.mjs` and `assembly-controls.mjs` through
the optional `assembly` argument to `installViewTools`. Existing callers keep
their camera, pointer, keyboard and scroll behaviour; no animation or new controls
appear without a model-specific recipe.

Pass `{host, steps, onFrame}`. Each step has `duration` in seconds, `title` and
`caption`. `onFrame({index, fraction, ...})` evaluates the complete pose from that
state. Do not accumulate translations from earlier frames: a user can scrub
backwards, jump to any step, replay or change recipes. The returned
`controls.assembly` exposes `setSteps`, `play`, `pause`, `dispose` and `timeline`.
The player stops at the last pose and pauses when the document becomes hidden.

Keep assembly instructions with the owning model. R19's `preview/assembly-recipe.mjs`
provides XIAO and battery sequences; its `assembly19.py` derives reference meshes,
the loading pivot, tilt and travel from CAD. It reads the actual assembly STL
exports rather than maintaining another editable geometry copy. Regenerate
`exports/assembly-guide.json` after a relevant CAD change; its hash binding is
checked by `tests/assembly-r19.test.mjs`.

Use Three.js groups for moving assemblies so reference electronics follow the
same transform as the board. Keep the user's camera independent from playback.
Plain canvas animation uses no audio/video element or media-session registration.
Old models need their own checked motion recipe; never attach R19 instructions
to a different revision merely to make its Play button appear.

No printable mesh, slicer profile or printer command changes when the guide plays.
Illustrative latch movement and catalogue electronics are not physical acceptance.
