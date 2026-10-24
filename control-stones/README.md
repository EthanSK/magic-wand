# Control Stones

The Control Stones hand-controller component in the motion-controller monorepo. The original Puck wand remains unchanged.

The primary design and test target is the **left hand**. See the [mounting and coordinate checks](docs/wiring-notes.md#left-hand-mounting-and-test-target) before designing a holder or interpreting motion. The debug window currently shows raw sensor axes, not calibrated hand directions.

- [Profile](profile.json): hardware and current scope.
- [Live sensor window](debug/README.md): setup, USB/Bluetooth readings, battery estimate and idle behavior.
- [Wiring diagram](docs/wiring.html): interactive HTML fragment originally made by Opus.
- [Wiring evidence](docs/wiring-notes.md): pin details and unresolved hardware checks.

The built-in Sense sensor has been read over USB and Bluetooth. Hardware idle and wake states have both been observed. Wake latency and current savings have not been measured. The current firmware is installed, and the BMI160 thumb on mux channel 2 has sent live readings over Bluetooth. Channels 3–6 remain unverified on hardware. The viewer includes an optional hold-to-move mouse test; pointer directions and calibration still need the user's hands-on check.

The diagram is an HTML fragment for the Codex visualization viewer, not a standalone web page. The debug window is served by the local Python reader; it uses real sensor values and never simulates a connection.

## Working Control Hand snapshot — 2026-10-24

Ethan confirmed this snapshot working, including Bluetooth. Verified on the
original XIAO nRF52840 Sense with a TCA9548A and one external BMI160 on channel 2:

- Internal and external six-axis readings appear together in the debug viewer.
- USB and Bluetooth telemetry work; the viewer prefers fresh Bluetooth data.
- The internal sensor retains its automatic idle/wake behavior.
- External I2C waits have deadlines and recovery rather than blocking forever.

The exact cause of the earlier stalled streams was not established. The new
guarded firmware restored both streams, but intermittent wiring faults have
not been deliberately induced. Channels 3–6, final hand mounting, pointer
directions and long-term battery life still need physical testing. The mouse
test is optional, off by default, and only moves while its button is held.

## Run the viewer on another laptop

Use Python 3.10 or later. These commands keep the installed runtime and its
dependencies outside the source checkout. Repeat the copy after updating the
repository; edit the repository sources rather than the installed copy.

```sh
git clone https://github.com/EthanSK/magic-wand.git
cd magic-wand/control-stones
STONES_RUN="$HOME/.local/share/control-stones"
mkdir -p "$STONES_RUN"
cp -R debug firmware "$STONES_RUN/"
python3 -m venv "$STONES_RUN/venv"
"$STONES_RUN/venv/bin/python" -m pip install -r "$STONES_RUN/debug/requirements.txt"
cd "$STONES_RUN"
"$STONES_RUN/venv/bin/python" debug/server.py
```

Open <http://127.0.0.1:8769/>. Close the reader on the previous laptop before
connecting from another one: the current firmware accepts one Bluetooth connection at a time.
Allow the new laptop's Bluetooth permission when requested. USB is another
way to receive readings. The pointer test currently requires macOS and
Accessibility permission for the reader's Python; viewing readings does not.

## Install the matching firmware

A Sense already running this snapshot does not need another upload merely
because the viewer is on a new laptop. For a new board, install Arduino CLI,
then run this from a separate terminal after the runtime copy above:

```sh
STONES_RUN="$HOME/.local/share/control-stones"
cd "$STONES_RUN"
SEEED_INDEX="https://files.seeedstudio.com/arduino/package_seeeduino_boards_index.json"
arduino-cli core update-index --additional-urls "$SEEED_INDEX"
arduino-cli core install Seeeduino:nrf52@1.1.13 --additional-urls "$SEEED_INDEX"
arduino-cli lib install "Seeed Arduino LSM6DS3@2.0.7"
arduino-cli compile --fqbn Seeeduino:nrf52:xiaonRF52840Sense --build-path build firmware/imu_debug
arduino-cli board list
# Replace this with the Sense's port from board list.
SENSE_PORT="/dev/cu.usbmodemXXXX"
arduino-cli upload --fqbn Seeeduino:nrf52:xiaonRF52840Sense --port "$SENSE_PORT" --input-dir build
```

Use a USB data cable. The upload normally enters update mode automatically;
two quick Reset presses are a fallback if it cannot. Require `Device programmed`
and fresh readings afterward, not only a zero command exit code. Keep the
reader stopped during upload, then start it again. Battery wiring and the
regulated sensor power connections are documented in the wiring guide above.

<!-- Previously prototypes/control-stones; promoted to the top-level Control Stones component at Ethan's request. -->

Run `npm run check --workspace control-stones` from the repository root for source, profile and host regression checks. The I2C deadline test uses a host C++ compiler when available. These checks do not compile firmware or verify hardware.
