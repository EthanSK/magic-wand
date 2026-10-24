# Control Stones

The Control Stones hand-controller component in the motion-controller monorepo. The original Puck wand remains unchanged.

The primary design and test target is the **left hand**. See the [mounting and coordinate checks](docs/wiring-notes.md#left-hand-mounting-and-test-target) before designing a holder or interpreting motion. The debug window currently shows raw sensor axes, not calibrated hand directions.

- [Profile](profile.json): hardware and current scope.
- [Live sensor window](debug/README.md): setup, USB/Bluetooth readings, battery estimate and idle behavior.
- [Wiring diagram](docs/wiring.html): interactive HTML fragment originally made by Opus.
- [Wiring evidence](docs/wiring-notes.md): pin details and unresolved hardware checks.

The built-in Sense sensor has been read over USB and Bluetooth. Hardware idle and wake states have both been observed. Wake latency and current savings have not been measured. The current firmware is installed, and the BMI160 thumb on mux channel 2 has sent live readings over Bluetooth. Channels 3–6 remain unverified on hardware. The viewer includes an optional hold-to-move mouse test; pointer directions and calibration still need the user's hands-on check.

The diagram is an HTML fragment for the Codex visualization viewer, not a standalone web page. The debug window is served by the local Python reader; it uses real sensor values and never simulates a connection.

<!-- Previously prototypes/control-stones; promoted to the top-level Control Stones component at Ethan's request. -->

Run `npm run check --workspace control-stones` from the repository root for source syntax and profile checks. This does not compile firmware or verify hardware.
