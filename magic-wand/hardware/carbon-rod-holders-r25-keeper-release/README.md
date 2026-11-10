# R25 XIAO lift-release trial

R25 tests a matched XIAO holder and keeper. The holder's ridge keeps a
gradual entry ramp and has a short vertical face on the release side.
The keeper has the original board prongs and tooth, plus a rounded edge
for lifting the spring tab with a fingernail. The board, USB opening and
rod still sit in their original positions.

[Watch the full assembly](../carbon-rod-holders/assembly/?version=r25&component=xiao)
or [see the catch from the side](../carbon-rod-holders/assembly/?version=r25&component=xiao_latch).
Slide the keeper in with the tooth facing the holder. Give it a light pull
to check the catch. To remove it, lift the rounded tab and slide the keeper
back along the grooves. The board lifts out after the keeper is removed.

The CAD route has about 0.19 mm of travel before the tooth touches the
stop, where it has 0.26 mm of vertical engagement.
The animation uses about 0.8 mm of lift at the rounded edge. The drawings
do not measure how much force the printed catch takes or how it will wear.
The new keeper also seats in the R22 holder. That pair still releases
over the original sloped ridge.

## Print and fit

The two-part trial plate uses the A1 mini PETG recipe with a 255°C nozzle
and 70°C textured bed. It uses removable holder pads, an outer brim on the
keeper and the disposable Smooth timelapse tower. Studio's preview and
re-slice were checked against the exact plate. The stop core is filled on
two layers, the spring slit stays clear, and the nail edge has material
in all three tested layers. Check the printed stop and lift edge with
the actual board and wires before relying on it for handling.

The sources are `catch25.py`, `plate25.py` and `assembly25.py`. Export with
`catch25.py`, slice with `plate25.py --scratch <directory>`, then use the
same directory with `--check`. `fit_print25.py` checks the stop, slit and
lift edge in both the delivered archive and the reopened Studio slice.
