# Carbon-rod holders R8 — independent sliding modules

Three printable parts: the five-key holder, a separate battery holder and the
retained light XIAO Sense holder. The battery no longer determines the length
or orientation of the key holder. R7 and all earlier delivered models remain
unchanged. These are checked print prototypes; physical fit, force, fatigue
and comfort are unverified.

## Try either way

- Turn the key holder end-for-end around its outward-facing keycaps: three keys
  toward the tip with two side keys below, or the reverse. The mounting seats
  and compact spacing remain R7: 18.5 mm three-key pitch, 47 mm two-key
  span and 20.5 mm row spacing.
- The battery holder has its own two nearly closed spring clips. Slide it
  independently on the rod; put it at either key end and turn it around the rod
  to try the keycap side or reverse side. This adds a separately adjustable
  part, rather than another integrated carrier variant.
- The viewer defaults to three keys toward the tip and the cell beyond that
  row. Its end labels follow the key layout, rather than screen up/down.
  The green +Y axis identifies the tip direction. The extra-space control
  shows 0–40 mm beyond an 8 mm minimum frame gap; it is an illustration of
  adjustment, not a required stop or a limit on a bare rod.
- Load the modules from a bare tube end. The small C-clip slit provides
  compliance, not sideways snap-on access. Swapping their order can require
  removing an end component and disconnecting wiring. Do not pull a connected
  cell by its leads or twist wires around the rod; allow slack and reroute.

## Finger contact and battery retention

The key holder retains rounded load rails and omits the old outer finger
pokes. Exposed floor corners away from the socket now have a 3 mm radius,
and rounded ribs replace square rear support posts. The switch-plate outline
and actual socket recess remain unchanged. No extra underside shell or projecting
corner bridge is added before a grip trial. The rounded thumb brace stays with
the key holder when the battery moves. The LiPo pouch is never a thumb stop.
Both orientations retain the same load paths; turning the holder does not turn
the keycaps inward. Clean support marks on all finger-contact surfaces.

R7's four rectangular side openings were **tape/strap eyes**, not wire outlets.
R8 removes those projecting loops. Wrap two tape bands around the cell and
both side rails through the open ladder floor, between its cross ribs. Keep
tape off the rod so the module can slide. The cell has two leads; strain-relieve
them to an end rail without pulling its terminals. Real tape routing and
retention still need a physical trial.

## Preserved interfaces and evidence limits

R8 composes the frozen R7 socket interface, board holder, clip profiles and
bought-part references. Its parameters store only changed assembly choices.
See [R7's part identities, drawings and caveats](../carbon-rod-holders-r7-spring-clips/README.md#bought-part-identity-and-reference-accuracy).
The 8 mm tube is nominal, the default relaxed clip bore is 7.9 mm, and the rigid
frame corridor is 8.4 mm. The cell reserve is 30 × 22 × 6 mm plus 0.8 mm side
allowance; actual wrapping is unmeasured. The cell floor is 5.85 mm from
the rod axis, 0.25 mm above R7 to leave 0.3 mm over the clip crown. Physical spring force and the ideal amount of friction are
unknown. Use the preserved R7 7.9/8.0/8.1 mm coupons before the complete print.

The XIAO print STL is byte-identical to R7. Gyro placement, electronics,
firmware and the existing alternative whole-wand studies are unchanged.

## Files and printing

- `exports/Key_Carrier.stl`: keys only, faces down for printing.
- `exports/Battery_Holder.stl`: independently sliding battery cradle.
- `exports/XIAO_Rod_Holder.stl`: retained separate sensor holder.
- `exports/Holder-modular-sliced.3mf`: all three parts, one plate, PETG,
  P1S 0.4 mm nozzle, 0.2 mm layers, 3 walls and 20% infill. Reslice for a
  different printer. Labelled socket-floor support helpers are print-only.

Model, support and brim material are reported separately in
`exports/mass-modular.json`. The first layout attempt overlapped plate objects;
the checked layout separates them. An initial slice's removable battery brim
crossed the open cell reserve, so the final battery object uses no brim. The
final bead audit checks every normal model and support-backed layer start;
supports still need physical removal from open seats and clip bores.

`geometry-checks.json` checks five nominal and maximum-size-sensitive socket
loading routes, unchanged key spacing, cap envelopes, connected load joints,
free spring arms, battery reserve and thirty-two reversible poses at four battery angles. CAD and sliced
clearance are not measured key travel, comfort, printed fit or strength.

## Rebuild

Keep the supplied dependency tree intact. In this folder, install
`requirements.txt` in a virtual environment, then run:

```sh
python cad.py
python verify_geometry.py
python print_project.py --slice --scratch /your/scratch/r8
python verify_slice.py
python measure_mass.py
python build_preview.py
```

Serve the repository root and visit
`magic-wand/hardware/carbon-rod-holders-r8-modular/preview/`. The preview reads
the actual exported meshes and CAD-generated placement values. It retains the
existing endless free orbit, scroll zoom and explicit wand scroll override.
`package_release.py --out /your/delivery/folder` creates the checked portable
source/print/viewer archive. Earlier model sources inside it are dependencies,
not newer fit approvals.
