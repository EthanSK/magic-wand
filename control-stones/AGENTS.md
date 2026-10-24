# Control Stones

Inherit the shared rules in ../AGENTS.md.

- Ethan is left-handed. Make the primary Control Hand / Control Stones design and test assumptions left-handed: glove, strap and ring layout, finger access, sensor placement and motion interpretation. Confirm actual mounting and coordinate conventions before changing axes; do not blindly negate them. Keep any right-hand variant explicitly separate. User-requested — 2026-10-24.
- Keep all existing sensors supported. Do not contaminate the Puck JavaScript, replace the V1 profile, or change the installed Wand receiver when adding Sense or other sensors.
- Keep device-specific firmware and transports separate; share only code with the same verified behavior.
- Maintain `docs/wiring.html`, originally created by Opus, as the wiring diagram. Do not maintain a competing diagram. Keep unverified connections marked.
- Keep USB identity stable and avoid redundant resets. Do not change macOS accessory security without an explicit request.
- This directory stores source. Run authorized physical installations through the private hardware workflow, never silently flash from this checkout.
