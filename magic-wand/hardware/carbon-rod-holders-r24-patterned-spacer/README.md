# R24 patterned battery spacer trial

R24 adds one optional 0.4 mm spacer for the LP402025 battery. Its rosette
uses curved petals, dots and rays around solid webs and a continuous rim.
It stays within the old 0.4 mm spacer envelope and uses 16.3% less solid
material, a saving of about 0.044 g of PETG. Slide it along the floor before
the battery only if the pouch still fits freely.

[Watch the battery and spacer assembly](../carbon-rod-holders/assembly/?version=r24&component=battery_spacer).
The two leads pass through the central arch of the original battery door.
The standard door, easier door and working R22 XIAO prongs are included.
The [XIAO latch animation](../carbon-rod-holders/assembly/?version=r24&component=xiao_latch)
shows the original catch and release. R24 omits the separate figure-eight
cable clip. The upright wipe tower is a disposable Smooth timelapse helper.

## Print checks

The checked A1 mini PETG archive uses a textured plate at 70°C and a nozzle
at 255°C for the first object. Studio estimates 1 h 50 min and 18.87 g for
the full ten-part plate, including the prime tower and adhesion material.
The actual two-layer spacer has all 27 openings clear, with an outer-only
3 mm brim. The carrier's working holes, guard runners and support removal
areas were checked. Studio's reopened toolpaths differ slightly and passed
the same clearance and material checks. The physical print and spacer fit
remain unverified.

The source is `spacer24.py`. The exact plate comes from `plate24.py` with
the R23 and R22 exports. Run it with a fresh `--scratch` directory, then
run `--check` with that same directory. The print, slice and reopen evidence
is in `exports`. Flex the cooled plate to release the thin spacer gently
and check that the frame stays intact while removing the brim.
