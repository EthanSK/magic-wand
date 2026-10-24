# Control Stones prototype

- Commit and push completed, checked work after every natural step. Use this Magic Wand repository and its existing remote. Never force-push or include unrelated changes.
- Keep all existing sensors supported. Do not contaminate the Puck JavaScript, replace the V1 profile, or change the installed Wand receiver when adding Sense or other sensors.
- Keep device-specific firmware and transports separate; share only code with the same verified behavior.
- Maintain `docs/wiring.html`, originally created by Opus, as the wiring diagram. Do not maintain a competing diagram. Keep unverified connections marked.
- Keep USB identity stable and avoid redundant resets. Do not change macOS accessory security without an explicit request.
- This public directory stores source. Run authorized physical installations through the private hardware workflow, never silently flash from this checkout.
