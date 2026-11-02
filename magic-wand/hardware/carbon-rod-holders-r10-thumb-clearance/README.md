# Carbon-rod holders R10 — thumb clearance and battery above the keys

Four normal print parts: the five-key carrier, separate sliding battery cage,
removable end gate and USB-up XIAO holder. R9 is preserved. These are print
prototypes; physical fit, force, strength and comfort remain unverified.

## Thumb opening

The two lower side keys move outward, with no projecting inner thumb bar.
Their spacing is derived from the actual printed socket-floor and seat reach,
not only the narrower illustrative keycaps. The row of three retains its
18.5 mm pitch; row spacing stays 20.5 mm.

The target is a 30 mm opening: a 28 mm design thumb and 1 mm on each side.
A primary NIOSH study reports male thumb breadth of 24.4 mm mean, standard
deviation 1.6 mm, n = 855 (US firefighters measured in 2009–2012). Mean plus
1.645 SD is approximately 27.0 mm under a normal approximation; 28 mm rounds
that upward. This is a design allowance, not a reported percentile, universal
male average or proof of comfort.

[Hsiao et al. 2015, DOI 10.1177/0018720815594933](https://stacks.cdc.gov/view/cdc/201534/cdc_201534_DS1.pdf):
Table 2 on PDF page 5; Appendix A on PDF page 17 defines width at the first
proximal knuckle from the finger base. Source statistics and reasoning are in
ergonomics.json; chosen width and margins are in parameters.json.

The geometry report checks the entire rectangular rest region against the
final frame, switches, sockets and illustrative caps, from the nominal 8 mm
rod crown upward. The rod itself remains the thumb support. Socket interfaces
remain sourced from R7. Rounded rear posts have a small closed floor foot
where widened diagonals cross them, preventing microscopic enclosed seams.
No new thumb shelf or inward bar is added.

## Battery above the keys

The battery stays at +Y, toward the tip/computer and above the key carrier.
Turning the keys does not move it into the grip. It remains its own sliding
component and can face either side of the rod. Its entry gate faces the tip,
so loading the cell does not require passing through the keys.

Lift the small gate away from the rod, slide the insulated battery in from
the tip end, then replace the gate. Wedges grip the printed guides outside
the pouch. The open floor and three roof hoops retain it without tape. The
split stop leaves space for the two leads toward the keys. The provisional
30 x 22 x 6 mm cell reserve has 0.8 mm side allowance and 0.6 mm above.
Do not force, squeeze or use a swollen/damaged pouch.

The normal gate has 0.1 mm total intended wedge interference; an easier-fit
gate and the preserved R7 rod coupons are included. Sliding force, retention,
comfort and fatigue need real print trials. Unplug or leave lead slack before
moving modules; reorder from a bare tube end.

Wires stay outside the carbon tube. USB faces the tip/computer. The XIAO
board rests on thin edge ledges with existing soft tape retention; tape-free
retention here is for the battery. Bought board, connector and illustrative
caps/loom are not print parts. Exact Sense underside and solder bends remain
unmeasured.

## Viewing and printing

Serve the repository root and visit
magic-wand/hardware/carbon-rod-holders-r10-thumb-clearance/preview/.
Both key orientations keep the battery above. Gate removed shows its loading
end. Scroll zoom and endless free rotation keep the shared viewer controls.

exports/Holder-modular-sliced.3mf contains all four normal parts on one plate:
PETG, P1S 0.4 mm nozzle, 0.2 mm layers, 3 walls, 20% infill. Reslice for another
printer. Remove supports from seats, bores and gate guides before assembly.
Printed-parts mass stays separate from supports/brim in mass-modular.json.

With the pinned requirements.txt, run cad.py, verify_geometry.py,
print_project.py --slice --scratch /your/scratch, verify_slice.py,
measure_mass.py, build_preview.py, then package_release.py --out /your/delivery.
Keep the portable source tree intact; the archive includes frozen dependencies
and licences.

The geometry checker covers the thumb opening, five sourced socket routes,
maximum socket sensitivity, flange lands, load joints, free spring arms,
cell/gate loading and 16 above-keys poses. Complete cell loading is checked
past the keys too. The slice audit checks exact final STLs, model bead
clearances and support-backed starts. None of those proves physical strength,
gate retention, electrical function or comfort.
