# R62 · Compact hinge and gentle bottom finger guards

[Finger side](../carbon-rod-holders/assembly/?version=r62&component=keys&view=finger_rest) · [Hinge and plug](../carbon-rod-holders/assembly/?version=r62&component=keys&view=pin_hinge) · [Battery](../carbon-rod-holders/assembly/?version=r62&component=battery)

The shoulders behind the upper keys return to the original holder outline. At the centre of each upper key they extend 1.85 mm. A narrow tongue supports the hinge cheeks and leaves the nominal three-wire bend in its existing position. The battery slides into the same raised friction-fit rails as R61.

The round supports rise gradually from the bottom of the key holder. Both outside roots remain integral. The sockets and their backing strips still load from the side. The key orientations and hinge axis match R61.

The bottom root enters at 21.1° in side profile, compared with 50.8° on R61. The top enters at 52.6°. The bottom transition runs 14.5 mm along the holder and the top runs 10.8 mm. Each of the six supports contains a continuous 2.1 mm round core to within the mesh measurement tolerance.

The carrier uses 0.705 cm³ less modeled material than R61 (5.8%). The nearest edges of the nominal wire turn and hinge barrel are separated by 0.47 mm along the length of the holder. All 336 sampled key positions and both side-loading backing strips clear the printed carrier in CAD.

## Build and check

Run these commands in this directory with the project's Wand CAD dependencies available.

1. Run `python3 design62.py` for the printable carrier and insertion sweeps, then `python3 profile62.py` for the guard cross-sections and shoulder dimensions.
2. Run `python3 kit62.py fit` to check the wired board, hinge swing and switch contact. Run `python3 guide62.py --register` to generate the viewer with the new carrier and the compatible R61 assembly parts.
3. Run `python3 kit62.py layout PLATE/layout.3mf`, slice the layout with the native A1 mini PETG workflow in `../carbon-rod-holders-r45-open-keyways/slice45.py`, then run `python3 kit62.py audit PLATE`. Reopen and re-slice the same layout for the second check.
4. After independent review, run `python3 kit62.py release PRIMARY REOPENED`. The complete kit includes the carrier, paddle, both board clips, post bar, OP1 retainer, both backing strips, two pin fits and two pin clips.

The 12-piece layout uses a 0.20 mm PETG profile. On the original and reopened native slices all 62 clearance checks pass, including the upper-right latch and printed hinge bores. No first extrusion starts in midair. The six disposable ties give 20.13 mm² of contact with the carrier, with the hinge bay clear. Bambu Studio still flags possible floating regions on the carrier. The three single-ended spans in the evaluated toolpaths correspond to existing R61 deck features.

Opus approved one monitored fit trial. Watch both rear shoulder ledges for curl and the right side of the holder for lifting, especially as the holder grows taller. The rear ledges step out up to 1.08 mm per layer and five of the six ties are on the left. Check the upper-right key latch and the real wire bend when assembling the kit.

Finger comfort, guard strength, base release and fit with bought hardware require a physical trial.
