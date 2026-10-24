# Control Stones

An experimental hand controller in the Magic Wand repository. The original Puck wand remains unchanged.

- [Profile](profile.json): hardware and current scope.
- [Live sensor window](debug/README.md): setup, USB/Bluetooth readings, battery estimate and idle behavior.
- [Wiring diagram](docs/wiring.html): interactive HTML fragment originally made by Opus.
- [Wiring evidence](docs/wiring-notes.md): pin details and unresolved hardware checks.

The built-in Sense sensor has been read over USB and Bluetooth. Hardware idle and wake states have both been observed. Wake latency and current savings have not been measured. External finger sensors and mouse control are not implemented yet.

The diagram is an HTML fragment for the Codex visualization viewer, not a standalone web page. The debug window is served by the local Python reader; it uses real sensor values and never simulates a connection.
