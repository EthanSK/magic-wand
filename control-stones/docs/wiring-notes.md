# Control Stones: one-hand wiring illustration (Opus version)

- **Author model:** Opus 5.5 (`claude-opus-5-5`), run through the Claude Agent SDK and invoked by Codex.
- **Illustration:** `docs/wiring.html`. This is an HTML fragment for the visualize surface, built with theme tokens, with no `<html>`, `<head>` or `<body>`.
- **Current status:** Source-checked wiring plan, not a measurement of the assembled hardware. The power choice now follows a vendor guide whose board photographs match Kunkune's purple BMI160/6DS3 board: regulated XIAO 3V3 to each sensor's 3V3, with VIN unused. CS and SA0 connect locally to 3V3 for I²C at address 0x69. Opus authored the original; Codex maintains subsequent requested updates. Delivered-board labels, shorts, pull-ups and first sensor communication still need physical checks.

## What the illustration does

- **Four build-stage tabs:**
  1. USB only
  2. One sensor (thumb, channel 2)
  3. Five sensors
  4. Battery

  Parts that come in later stages are drawn faded (ghosted). Wires appear only once their stage is reached.
- **Selecting a connection:** click any wire or pad chip (`CS`, `SA0`, `NC`, built-in IMU), or use the **Connection** dropdown, which works from the keyboard. The diagram then:
  - draws rings on both endpoints and fades everything else;
  - fills a card with: status, *from → to* endpoints, what the connection does, what to check, and the source.
- **Clearing a selection:** click blank diagram/page space or press Escape outside a form control. The dropdown also has a no-selection option. The detail card and dropdown remain usable without clearing the selection, and an empty selection is preserved when changing stages.
- **Status is shown by line style as well as label:**
  - solid = documented by a vendor or Bosch source
  - dashed = verify on the delivered board
  - × stub = leave unconnected
  - dotted = wireless
- **Net colours:** 3V3, GND, SDA, SCL and battery + each use a distinct theme series token. They are always paired with text labels.
- **Power is drawn explicitly** as separate 3V3 and GND rails from the XIAO to every finger board. This makes it visible that the mux switches data, not power.
- **Two layouts:**
  - wide (≥ 708 px): left-to-right signal flow
  - narrow (< 708 px, down to 320 px): stacked vertically

  In both, the SVG viewBox is sized from the measured container width.
- **Saved state:** the current stage and selection are kept through `window.openai.setWidgetState`.

## Wiring list (as drawn)

| # | From | To | Status |
|---|------|----|--------|
| 1 | XIAO USB-C | Mac USB (programs and charges) | Documented (Seeed) |
| 2 | XIAO radio | Mac Bluetooth (BLE) | Built-in hand readings implemented; external finger support pending |
| 3 | XIAO built-in LSM6DS3TR-C | none (on the board) | Built in. Power is gated by P1.08 per Seeed |
| 4 | XIAO D4 / SDA (P0.04) | TCA9548A SDA | Documented |
| 5 | XIAO D5 / SCL (P0.05) | TCA9548A SCL | Documented |
| 6 | XIAO GND | TCA9548A GND | Documented |
| 7 | XIAO 3V3 (3V3_OUT) | TCA9548A VIN | Documented (Adafruit: power at the MCU's logic level) |
| 8 | TCA9548A RST | not connected | Leave open (pulled high on the board; ground = reset) |
| 9 | TCA9548A A0/A1/A2 | not connected | Leave open (pulled low on the board → 0x70) |
| 10 | TCA9548A SD*n* / SC*n*, *n* = 2..6 | Thumb / Index / Middle / Ring / Little board SDA / SCL | Documented (Adafruit: no pull-ups on the channels) |
| 11 | XIAO 3V3 rail | each finger board **3V3**; leave VIN unused | Matching-board vendor guide |
| 12 | XIAO GND rail | each finger board GND | Documented |
| 13 | Each finger board CS | same board's 3V3 | I²C mode; check no short to GND before adding local connection |
| 14 | Each finger board SA0 | same board's 3V3 | Address 0x69; check no short to GND before adding local connection |
| 15 | Each finger board INT1, INT2, OCS, SCX, SDX | not connected | Leave open (Bosch §4.1) |
| 16 | LiPo + (JST-PH) via the socket pigtail | XIAO BAT+ pad (underside) | **Verify polarity** |
| 17 | LiPo − (JST-PH) via the socket pigtail | XIAO BAT− pad (underside) | **Verify polarity** |

Notes on the wiring:
- Labels use silkscreen pin names and finger names only. The pin order in the diagram is schematic. It does not show physical pad positions, board rotation or sensor axis orientation.
- The 3V3 and GND rails can be spliced at the XIAO side. Do not wire XIAO 3V3 to both the VIN and 3V3 pads of a finger board.

## What the sources confirmed

- **Seeed XIAO nRF52840 wiki:**
  - D4 = P0.04 SDA and D5 = P0.05 SCL. 3V3 is `3V3_OUT` (an output). 5V = VBUS.
  - The Sense model has an LSM6DS3TR-C, with IMU power on P1.08 and its interrupt on P0.11.
  - Charging current is about 50 mA with P0.13 set high-impedance, and about 100 mA with P0.13 driven low.
  - It warns to keep P0.14 low when reading battery voltage and not to set it high while charging, or P0.31 can be damaged.
  - It does **not** state a 3V3 current limit, the IMU's I²C bus, or details of the non-Plus underside BAT pads.
- **Adafruit TCA9548A guide (pinouts page):**
  - RST is pulled high by default; connecting it to ground resets the chip.
  - A0–A2 are pulled low by default, giving 0x70 (range 0x70–0x77).
  - The SDn/SCn channels "do not have any pullups installed".
  - Power the board at the controller's logic level.
  - The Rev C schematic image shows upstream SDA/SCL pull-ups to VCC plus a RESET pull-up. The resistor values were not legible at that resolution.
- **Bosch BMI160 datasheet (BST-BMI160-DS000-09):**
  - VDD 1.71–3.6 V, VDDIO 1.2–3.6 V; absolute maximum 4.25 V; logic pins ≤ VDDIO + 0.3 V (Tables 1 and 5).
  - CSB has an internal pull-up of 75–150 kΩ to VDDIO (Table 26).
  - For I²C, Bosch recommends hard-wiring CSB to VDDIO; a rising edge on CSB switches the chip to SPI (§3.2.1).
  - Address 0x68 with SDO to GND, 0x69 with SDO to VDDIO (§3.2.3).
  - Do not connect unused INT1/INT2; unused secondary-interface pins are high-impedance (§4.1).
  - CHIPID register 0x00 reads 0xD1 (§2.11.1).
  - Typical current with accel and gyro both running is 925 µA.
- **Kunkune listing:** it says 3.3 V (1.71–3.6 V), "without an onboard regulator", I²C 0x68/0x69, and modes "configurable via the PS pin". The photographed board has no PS pad, so the listing text contradicts the photos in two places: the regulator and the PS pin.
- **[Spintend matching-board guide](https://spintend.com/products/bmi-160-module-for-diy-balanced-board-with-vesc):** its board photos match the purple BMI160/6DS3 layout in [Kunkune's listing](https://kunkune.co.uk/shop/arduino-sensors/bmi160-6-axis-motion-tracking-accelerometer-gyroscope-module/). The guide explicitly offers VIN with 5 V **or** 3V3 with regulated 3.3 V, choosing one. We use the latter. Its SA0-to-GND example selects 0x68 for VESC; our custom firmware can instead use 0x69 with SA0 high. This is matching-board documentation, not proof of the user's physical PCB revision.
- **Board photos (the inspected supplier image):**
  - Pads: VIN, 3V3, GND, SCL, SDA, CS, SA0 on one side, and OCS, INT2, INT1, SCX, SDX on the other.
  - Parts: a 5-pin SOT-23-style part marked `S2PG` (regulator-like, not identified), several capacitors, and four resistors marked `103` (10 kΩ).
  - The silkscreen seems to show the PCB is shared between a BMI160 and an LSM6DS3 ("I160" / "6DS3" with marker boxes).
- **Related vendor schematic (the inspected supplier image), not this exact board:**
  - Shows an ME6211C33 LDO from VIN to VDD (the 3V3 pad).
  - Shows four **3.9 kΩ** pull-ups to **VIN** on SDA, SCL, "CS" and "SA0".
  - Its net labels put "CS" on SDO and "SA0" on CSB, which looks swapped.
  - The resistor value differs from the 10 kΩ in the photos, so it was not used as proof.

## Verdict on the uncertain electrical wiring

1. **Finger-board power pad: use 3V3; leave VIN empty.** This follows the matching-board vendor guide rather than the unrelated schematic or Kunkune's contradictory prose. VIN feeds the board's regulator; 3V3 is the regulated rail. Never apply raw battery voltage to 3V3.
2. **CS: connect locally to 3V3.** Bosch recommends holding CSB at VDDIO from power-up for I²C. No CS wire needs to run to the controller.
3. **SA0: connect locally to 3V3, selecting 0x69.** All five sensors may share this address behind separate mux channels. Holding both CS and SA0 high also avoids depending on the apparent label swap in the unrelated schematic. With all power disconnected, first verify neither pad is hard-shorted to GND; stop if it is. On the first powered test, select channel 2 and verify 0x69 plus CHIPID 0xD1 before adding other sensors. The [Bosch datasheet](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmi160-ds000.pdf), §§3.2.1 and 3.2.3, defines these modes and addresses.
4. **Pull-ups: PROBABLY ADEQUATE, UNVERIFIED.**
   - The mux upstream side has pull-ups per Adafruit's schematic.
   - The mux channels have none.
   - The sensor boards appear to carry 10 kΩ resistors, but which rail they connect to is unknown.
   - Use the spare 4.7 kΩ resistors only where needed, and pull only to 3.3 V.
5. **Battery pads and polarity: VERIFY.** Solder the JST-PH socket pigtail to the underside BAT+/BAT− pads with the battery unplugged. Meter the polarity; JST-PH polarity is not standard across vendors.
   - Charging defaults to about 50 mA. Use 100 mA only if the cell's datasheet allows it.
   - Raw battery voltage must never reach 3V3, the sensor pads or any GPIO.
6. **XIAO 3V3 load: UNMEASURED.** Five BMI160s plus the mux should draw a few mA, based on Bosch's typical figures, but Seeed publishes no limit. Measure it.
7. **No promises** are made about simultaneous reads (the mux reads one channel at a time), runtime, or gesture firmware.

## Points to compare with the other illustration

- **Staging:** the build stages are the main control (four tabs). Earlier parts stay visible in later stages, and later parts appear faded in advance.
- **Power:** drawn as explicit rails, not as net-label flags.
- **CS and SA0:** explicit local 3V3 connections, with the unpowered short check and first-sensor scan still required.
- **Power pad:** 3V3 named explicitly using the matching-board vendor guide; VIN unused.
- **Interrupts:** INT1 is described as a possible future wake line, with no GPIO invented.
- **Two layouts:** wide and narrow, with no fixed-width viewBox scaling.
- **Accessibility:** the dropdown gives keyboard access to every connection, the detail card announces updates, and the SVG has a title and description.
- **Not included:** a printable wiring table inside the visual. The table above serves that purpose instead.

## Current channel mapping (24 October 2026)
User requested avoiding channels 0 and 1. Thumb 2, index 3, middle 4, ring 5, little 6; channel 7 spare. This is the maintained diagram.

## Left-hand mounting and test target

The primary Control Hand / Control Stones design is for the **left hand**, as requested on 24 October 2026. `profile.json` records that target. This is a design preference, not a claim that a mount has already been made or calibrated.

- Design glove/strap routing and printed ring holders around the left hand. Check thumb opposition, thumb/index/middle access, finger bending and wire slack on that hand; do not assume a right-hand layout fits by relabelling it.
- Put the hand reference sensor on the back of the left hand. Confirm the final board orientation and record the sensor-axis arrows, USB socket direction, and orientation of each finger board before defining motion directions.
- Keep the logical channel mapping above: thumb 2, index 3, middle 4, ring 5, little 6. It identifies fingers, not their left-to-right order on the drawing. The existing illustration shows electrical connections; its node positions are not a physical right-hand or left-hand template.
- The current firmware reads the IMU's own X/Y/Z axes; the reader and debug graphs preserve those values. No handedness transform or pointer mapping is implemented. Do not negate an axis merely because the wearer is left-handed.
- Before enabling gesture or pointer mappings, test the mounted left-hand assembly: rest palm-down, tilt toward fingertips and toward wrist, tilt toward thumb and toward little finger, rotate around the forearm, and flex each finger separately. Record which axes and signs respond, then define each sensor-to-hand rotation and the intended hand-to-screen mapping from those observations. Verify mixed movements as well as single-axis movements.
- If a right-hand variant is added, give it explicit mounting/calibration data and run the same checks separately; do not silently replace the left-hand default or reuse a guessed mirrored transform.

Physical mounting, calibration and the external finger tests remain pending. This clarification changes no wiring, battery connections or installed firmware.
