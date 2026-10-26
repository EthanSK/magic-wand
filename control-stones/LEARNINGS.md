# Control Stones learnings

## Acknowledgement is not evidence that a sensor is still sampling

2026-10-26: `Fingers::sample` returned early when BMI160 data-ready bits were
clear but retained the cached sensor address. `rescan` only configured entries
without an address. A device acknowledging I2C while no longer sampling could
therefore remain silent indefinitely. A host simulation of this exact state
fails against the prior production driver and recovers with the one-second
measurement watchdog. The same regression verifies that the healthy thumb is
not reinitialised and that a returning sensor can recover without a board reset.

Keep channel discovery, successful measurements and recovery diagnostics
distinct. Deselect the mux between sensor operations, and report fresh firmware
health separately from motion. The triggering physical cause of the observed
intermittent readings remains unproven; this test does not diagnose soldering,
power integrity, pull-ups or a permanent short.

## Keep an external bus fault from blocking the internal sensor

2026-10-24: Seeed nRF52 core 1.1.13's `Wire` implementation waits for TWIM
events without deadlines. Calling it for an external sensor from the same
loop as the built-in sensor can therefore stop both telemetry streams when
an external transfer stalls. This is a verified source hazard, not proof of
what caused any particular physical wiring fault.

`firmware/imu_debug/timed_i2c.h` bounds each external TWIM0 wait to 20 ms,
disables DMA before abandoning a transfer, and releases/recovers the bus.
The built-in sensor stays on Wire1. Start Bluetooth before scanning external
sensors, so an unavailable external sensor does not prevent radio startup.
Expose timeout counts in telemetry rather than silently treating them as
valid readings. The host test covers successful transfers, NACK, timeout and
subsequent recovery; physical intermittent wiring still needs hardware tests.

## Leave the bootloader's serial port for the uploader

The original Sense's bootloader keeps its XIAO product name but uses USB
product ID `0x0045`. A name-only serial reader can open it during an upload,
causing the uploader to report a busy port. Exclude that product ID from the
reader, and require the uploader's `Device programmed` result plus fresh
telemetry before declaring an installation successful. A zero uploader exit
code by itself has previously accompanied a failed upload.
