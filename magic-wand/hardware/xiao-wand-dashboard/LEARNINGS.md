# Sense diagnostic dashboard learnings — 28 October 2026

The existing Control Hand packets contain motion but no D8/D9/D10 button states. The installed Puck monitor also documents no raw IMU feed. Neither can establish live Sense button states. Keep this diagnostic protocol and sketch separate; reject other device packets instead of inventing released buttons.

A disconnected or silent stream is unknown, not released. Clear live button and axis presentation on disconnect or a 1.5-second gap. Do not integrate gyro motion across the missing interval. Cumulative board press counters can preserve a short press between received snapshots, but no dashboard can display an unreceived hold as current.

Browser device APIs need a user gesture and are not available in every embedded browser. Keep the labelled demo usable without hardware APIs, check capabilities visibly and provide opt-in readers. A successful simulated parser/transport test or sketch compile is not a physical-device test or firmware installation.


## Complete the hardware-to-page path, not only the page

The first dashboard ran in Demo and the diagnostic sketch was only compiled. USB enumeration and opening its port produced no wand packets. After authorised private installation, the vendor uploader reported Device programmed; 195 real USB packets and 66 real Bluetooth packets were received with all three button fields and IMU data. The board's three press counters subsequently increased. That establishes live telemetry, not physical user acceptance of every control. Battery-powered Bluetooth was later observed live after the disconnected battery was reconnected. An absent USB board alone does not establish battery power; check power and actual telemetry before blaming the reader.

A browser can retain the serial port while a separate installer/reader needs it. Release the browser reader and use one owner. The local reader removes device-picker friction and gives USB priority, with Bluetooth used after USB removal. Keep the HTTP dashboard available during work and distinguish waiting, incompatible/no packets, stale and live states.

A single hardware-counter increment must create an activity entry even when both received button states are released; a short click can occur between host polls. An unexpected browser Bluetooth disconnect also needs its own regression: referencing a serial-only error variable there raised an exception despite intentional-close tests passing. Both paths now have targeted tests.
