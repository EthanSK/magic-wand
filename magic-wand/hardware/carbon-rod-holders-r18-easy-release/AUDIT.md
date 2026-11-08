# R18 printability and physical acceptance

Independent CAD/slice review passed for a physical trial after the door-catch
correction. The actual Studio job was sent and entered preparation. This does
not establish physical adhesion, strength, fit, comfort or easy cleanup.

## Exact artifacts

- CLI source slice: `exports/R18-A1-mini-PETG.gcode.3mf`, SHA-256
  `6e796431d061d52c2164ca99cf1ad007eab9a8cd6f654408325405938af5e4f3`.
- Actual audited/sent Studio archive SHA-256:
  `2bd9956845f9e74f2f3f3ad2462a82a71b3ddc50b337594d4c83d7d7967d8486`.
- Public Studio copy: `exports/R18-SENT-A1-mini-PETG.gcode.3mf`, SHA-256
  `bae339866b785f455a58f063f1a7902eaca403f3bf703a6fe70c4802149683d6`.
  Only account metadata was removed; all other archive entries are identical.
  `exports/sent-export-binding.json` records both archive and G-code hashes.

| Part | Working spaces checked | Print and weak points |
|---|---|---|
| Battery holder | Cell reserve, loading, door route/slots, wire exit, rod bore/slits, wire buses | One-section channel, arrow roof, ring roots, 6 ties on end plate |
| Battery door | Seats, full slot float, release route and catalogue cell clear | 1.8 mm plate; tooth beads on three layers above it; catch/release force unmeasured |
| Battery spacers | Clear of holder inside reserve | Broad thin flat parts, no anchors; inspect first layers |
| XIAO holder | Board poses, tilt loading, USB/plug, components, all 14 pad exits, wire routes, rod bore/slits | Connected tray, hoop, grooves, posts, ring roots, 6 ties in 4 pads |
| XIAO keeper | Removal clear of holder, wires, board and components | 1.2 mm tongue, tooth over six layers; ideal beam strain about 2.4% |

## Verified digital checks

Evidence in `exports/`: `manifest.json`, `geometry-checks.json`, `anchors.json`,
`R18-A1-mini-PETG-print-checks.json`, `slice-clearances.json`,
`short-features.json`, `roundtrip-checks.json`, `view-checks.json`, plus
`slice-clearances-gui-final.json` and its layer images for the final Studio slice.

Both final slices passed the working-space, actual-bead, floating/missing-layer,
classified-overhang and continuous-anchor checks. The GUI audit verifies each
label's complete extrusion XY footprint against the reviewed meshes/placements
before supplying mesh expectations absent from Studio's sliced-only export.
The GUI audit also passed for the public copy with identical print paths.

Each upright holder has six 1.0 x 0.4 mm ties, continuous along their joining
direction on both layers. The bead gap away from ties is at least 0.987 mm.
The broad-face door, keeper and spacers were accepted without additional helpers;
this is a deliberate exception to the usual brim default, not proof of adhesion.

Independent review found the original door could lose almost all catch overlap
at one end of slot movement. The corrected 1.8 mm plate limits float to +/-0.15 mm;
catch overlap is 0.25 / 0.40 / 0.55 mm at outward / centre / inward positions.
Release and catalogue-cell clearance pass at all three positions. Only the door
mesh changed during this targeted correction. The tooth prints at layer tops
2.0, 2.2 and 2.4 mm. The old beam estimate used too long a loaded span; estimates
now use the actual tooth load point. Door in-plane bending does not by itself
prove layer separation, but interlayer shear and fatigue remain physical risks.

One CLI reopen/re-slice passed the same audit; normalized G-code differs. The
actual final GUI slice was checked separately after confirming 0.6 mm Normal
travel lift. Studio estimated 3863 seconds and 7.99 g; the CLI slice estimated
3383 seconds and 8.01 g. Timelapse, bed levelling and flow-dynamics calibration
were enabled in the actual send dialog, independently of archive defaults.

The slices retain `not_support_traditional_timelapse` warnings at levels 2 and 3.
Studio's pre-print notice says instant timelapse may mark the surface; it was
acknowledged to keep the explicitly requested timelapse. A saved playable R18
recording is not yet verified. The earlier source archive was restored by exact
hash after a GUI save left it without G-code; future editing uses a separate layout.

## Physical limits and cleanup

- Tie adhesion and removal forces are unmeasured. Stop if a holder/pad comes loose.
  Support solid faces; snip the two XIAO hoop ties rather than pulling on the hoop.
  Peel other pads gently and snip any resisting side tie. Do not lever against
  rings, ledges, keeper lips or the hoop.
- Bought cell thickness and pouch behaviour are unmeasured. The 4.9 mm bay is
  unchanged; choose the thickest 0.4/0.6/0.8 mm spacer that slides in without force.
  Slide cell and spacer in together, fully seat the spacer before fitting the door,
  and never compress the pouch. Tape may take up residual play.
- Beam estimates assume a 2000 MPa modulus and are not force measurements: door
  worst fixed-position case about 6.2 N and 2.4% strain; moving it outward first
  reduces the estimated thumb release load. Keeper about 4.6 N and 2.4% strain.
  Fatigue and comfortable release still need the printed trial.
- Real solder, wire gauge/bends and populated Sense underside are unmeasured.
  The provisional wire corridors and STEP-based USB gap need physical checking.
- Acceptance still required: clean removal without cracks; door/keeper insertion
  and removal; battery held without rattle or squeeze; board/wire/USB/reset access;
  and rod grip. The key carrier was already accepted and is excluded from this plate.
