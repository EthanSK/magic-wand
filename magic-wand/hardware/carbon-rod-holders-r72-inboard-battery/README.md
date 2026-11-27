# R72 key holder

[Open the key holder in the assembly viewer](../carbon-rod-holders/assembly/?version=r72&component=keys).

The nominal 27 × 11.8 × 3.9 mm Micron pouch sits 8 mm closer to the carbon rod. Its installed height and fore-aft position match R71. At the next tested position, 0.5 mm further inward, the retaining spring would lose working space beside the rod sleeve. The outer silhouette of the key banks keeps the R71 top taper.

The two roots of the battery-side finger guard sit 14 mm apart. Its outer branch curves around the black socket's side-loading path. The upper arm rounds the front of the pouch to stop it sliding too far. A short rounded strut connects the far end to the deck between the keys. It backs the curved stop during printing and leaves the socket insertion path open. The other eight printed pieces use their existing sources and assembly motions.

Slide the battery into the rails from the open rear end, with the connector and leads clear of the spring. Fold the removable base away at the five narrow fin necks. Four are on the underside and one is on top. The hinge bay stays open.

## Files

- [Carrier mesh](exports/Key_Carrier-assembly.stl)
- [Assembly guide data](exports/assembly-guide.json)
- [CAD dimensions and insertion checks](exports/fit72.json)
- [Nine-part print file](exports/print-mechanisms/R72-Complete-Key-Holder-A1-mini-PETG-print-only.3mf)
- [Sliced plate review](exports/print-mechanisms/review.json)

The carrier comes from `design72.py`. The build plate comes from `kit72.py`; the animation comes from `guide72.py`. The independent slicer checks in `audit72.py` and `sections72.py` read the deposited paths. `release72.py` packages those exact printer instructions after review. Battery fit, spring pressure and comfort require the printed sample and fitted hardware.
