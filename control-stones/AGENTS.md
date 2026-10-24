# Control Stones

Inherit the shared rules in ../AGENTS.md.

- Ethan is left-handed. Make the primary Control Hand / Control Stones design and test assumptions left-handed: glove, strap and ring layout, finger access, sensor placement and motion interpretation. Confirm actual mounting and coordinate conventions before changing axes; do not blindly negate them. Keep any right-hand variant explicitly separate. User-requested — 2026-10-24.
- Keep all existing sensors supported. Do not contaminate the Puck JavaScript, replace the V1 profile, or change the installed Wand receiver when adding Sense or other sensors.
- Keep device-specific firmware and transports separate; share only code with the same verified behavior.
- Maintain `docs/wiring.html`, originally created by Opus, as the wiring diagram. Do not maintain a competing diagram. Keep unverified connections marked.
- Use actual distinct wire insulation colours for the current build: red positive power, black GND, green SDA data, yellow SCL clock. Do not substitute labelled or sleeved lengths of the same colour. This supersedes the earlier request to omit yellow; keep completed orders as historical facts rather than rewriting them. The current materials plan is in `docs/wiring-notes.md`. User-requested — 2026-10-24.
- Keep USB identity stable and avoid redundant resets. Do not change macOS accessory security without an explicit request.
- This directory stores source. Run authorized physical installations through the private hardware workflow, never silently flash from this checkout.
