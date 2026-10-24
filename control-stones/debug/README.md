# Control Stones sensor test

This test is isolated from the existing Magic Wand/Puck runtime. It reads the original XIAO nRF52840 Sense's built-in LSM6DS3 and external BMI160 sensors through a TCA9548A, over USB or Bluetooth. The viewer includes an optional hold-to-move pointer test; it never sends clicks.

## Firmware

`../firmware/imu_debug/imu_debug.ino` uses Seeed nRF52 core 1.1.13 and Seeed Arduino LSM6DS3 2.0.7. Compile for `Seeeduino:nrf52:xiaonRF52840Sense`.

The firmware generates JSON lines roughly every 20 ms, sent over open USB serial and subscribed Nordic UART BLE. `ax`, `ay`, `az` are acceleration in g; `gx`, `gy`, `gz` are rotation speed in degrees per second; `ms` is the board clock. `sensor` is `hand` or `finger`; finger packets include the physical mux `channel`. Acceleration includes gravity. Rotation speed is not absolute orientation. Actual receive rate depends on the transport.

`finger_sensors.h` uses the external D4/SDA and D5/SCL bus (`Wire`), separate from the built-in IMU (`Wire1`). It selects one mux channel at a time, accepts BMI160 chip ID 0xD1 at 0x68 or 0x69, and checks configuration readback. Sensors run at 100 Hz with ±4 g and ±1000 degrees/s; telemetry is read at about 50 Hz. Missing channels are periodically rescanned. Power and wiring must follow the [wiring notes](../docs/wiring-notes.md); the driver cannot prove a correct physical connection from a label or a lit LED.

## Idle power mode

`firmware/imu_debug/sense_power.h` owns the Sense-only power policy. ST AN5130 section 5.6 supplies the hardware activity/inactivity behavior: after approximately 4.92 seconds below the movement threshold, acceleration sampling drops to 12.5 Hz and the gyro enters Sleep mode. Movement restores the configured active rate. The accelerometer is configured for ±4 g and a 62.5 mg slope threshold; both sensors retain 416 Hz active sampling. These are initial prototype settings, not a tuned gesture detector.

The built-in IMU's INT1 signal wakes the FreeRTOS reader task. The task blocks between readings rather than busy-spinning. Active telemetry is nominally 50 frames/s; with no connected finger sensor, idle telemetry is 1 frame/s, with gyro values shown as zero and explicitly labelled Idle. With a detected finger sensor, the task keeps polling at 50 Hz so finger movement is not missed while the hand rests. Bluetooth remains connected. External BMI160 power management is not implemented. Battery savings and first-gesture wake latency still require physical measurement.

Battery voltage uses the original Sense's battery ADC, a 3.0 V reference, 12-bit resolution and the 1 MΩ / 510 kΩ divider. The divider enable stays LOW, and charging current stays at the core's default 50 mA. `charging` reads the active-low charger-status input. Percentage is a heuristic voltage curve, not a measured capacity or runtime prediction; charging and load affect it. This is not a fuel gauge and cannot reliably distinguish a disconnected battery from a powered charger node.

## Viewer

Run `python debug/server.py` with Python, `pyserial`, and `bleak` installed, from the project folder. Open `http://127.0.0.1:8769/`. The server binds only to localhost, finds one Seeed USB device automatically, and scans for one device named Control Stones with the Nordic UART service. It leaves the original Sense bootloader (USB product ID 0x0045) alone so the uploader can own its serial port. It prefers fresh Bluetooth samples, falls back to USB, reconnects after removal, rejects invalid samples, and marks stale data instead of displaying it as live. Multiple matching Bluetooth devices are not selected arbitrarily.

Install the Python dependencies from `debug/requirements.txt` in a virtual environment. The page, receiver and firmware are retained project source, not temporary generated previews.

Toolchain downloads and builds for this session are on the SD card under `AgentScratch.noindex/control-stones-debug/`, including the Python environment and Arduino CLI configuration. Source stays here. No existing Wand or Puck source was modified.

## Current verification

- Firmware compilation passed; 50,680 bytes of flash and 7,696 bytes of RAM.
- USB enumeration confirmed the connected original Sense.
- Parser accepted a complete sample and rejected incomplete, non-object, non-finite, and boolean axes.
- The first upload did not receive a bootloader acknowledgement. A reported zero exit code from the vendor uploader did not mean a successful upload.
- After two quick presses of physical Reset and accepting the macOS accessory prompt, the device entered its bootloader (USB product ID 0x0045). The second upload reported `Device programmed`.
- Real six-axis samples were observed from the USB device and in the browser, with changing values and fresh timestamps.
- Bluetooth-and-battery firmware compiled (126,148 bytes flash / 14,552 bytes RAM) and uploaded successfully after detecting bootloader USB product ID 0x0045 and sending directly with the vendor uploader.
- Fresh Bluetooth samples and battery ADC readings were observed. The charge-status input reported charging with USB connected. Charging current, capacity and remaining runtime have not been measured. External sensors were not wired or verified at that earlier check.
- The subsequent sleep firmware compiled and uploaded successfully. Register readback confirmed the sleep configuration and real telemetry reported the hardware Idle state.

## Finger channels and mouse test

To avoid the multiplexer pins on the opposite side: thumb uses SD2/SC2, index SD3/SC3, middle SD4/SC4, ring SD5/SC5 and little SD6/SC6. Channels 0, 1 and 7 are unused. The firmware, viewer and wiring diagram use this mapping.

The viewer shows the internal Sense sensor and one selected external gyro together, each with its own rotation and acceleration values and history. Matching graphs share their vertical range. The external selector starts at channel 2 and can show channels 3–6; these are labelled by channel rather than assuming the sensor is already mounted on a finger. Select a **Mouse sensor**, keep it still and choose **Calibrate while still**. Calibration averages 50 readings; a hand sensor already in idle sends fewer readings. Adjust the horizontal/vertical axes and their inversion to suit the actual mounting. Hold **Hold to move mouse**, or hold Space/Enter while that button is focused. Release, lose focus, or stop renewing the hold for 0.6 seconds to stop movement. Fresh packets are required; duplicate USB/BLE packets, stale gaps and device-clock resets do not replay movement. A local per-run token protects mouse commands against unrelated websites. The reader's Python needs macOS Accessibility access; the page reports when it is unavailable without prompting or changing settings.

The BMI160 build compiled (129,292 bytes flash / 14,624 bytes RAM). Eight host tests cover packet validation, channel numbering, calibration, hold expiry, duplicate/stale samples, connection status, bootloader exclusion and command access. The firmware upload reported `Device programmed`; the installed build then sent changing six-axis thumb readings on channel 2 over Bluetooth, alongside the built-in hand sensor. The browser displayed both as live, and a brief hold/release test returned pointer control to off. The user's preferred pointer directions, calibration and battery-only operation with this build still need hands-on acceptance. Only one external sensor was connected; channels 3–6 have not been physically tested. Uploading this build over Bluetooth is not implemented. Earlier verification above describes the previous hand-only installed build.
