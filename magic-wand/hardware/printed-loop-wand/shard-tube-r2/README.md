# Shard Tube R2 — repaired lower assembly

This revision repairs the latest main-branch Shard Tube lower assembly in editable CAD. The 192 mm shaft and open sensor cradle remain geometrically unchanged. A light-cap wand remains 410 mm overall. Both handed grips are included in the complete print project. Previous models and the V20 snapshot remain unchanged.

## What changed

| Request | R2 feature | Verification |
| --- | --- | --- |
| Handle must actually enter and stay captured | Two broad curved hook ends enter recessed openings and slide up 4 mm into solid stops. A separate stout radial quarter-turn key prevents sliding back down. 0.4 mm nominal clearance per mating surface. | Complete loop insertion/removal, key insertion/turn, radial/up/down capture checked against both final grips, bought controls and caps. Physical fit sample still required. |
| No projecting mounting furniture when handle is removed | All hooks and the key leave with the loop. Receivers sit inside the original stem envelope. | Final receiver/envelope comparison and bare-wand preview. |
| No fragile square switch carriers or claws | Bought Choc V1 switch clips directly into a rounded integral 1.3 mm lip. Purchased keycap covers the 16.4 × 17.2 mm seat. No separate printed switch plate, guide track or PETG claw. | Bought body/socket/post/pin reference and installation route checked at all six seats. |
| Switch holes must remain real holes | Body, five post/pin holes, socket floor relief and wire corridors are subtracted after all grip unions. | Reloaded STL checks and sliced-path probes. Each grip is one closed printable mesh. |
| Battery must load from the bottom | Remove the old 6.7 mm solid diaphragm and the residual 0.6 mm annular print ledge. Join the cap mouth continuously into the hollow chamber, then continue a cell/sled loading passage from the 24.4 mm clear threaded mouth to the chamber. | Full insertion sweep of exported sled and rectangular cell through both final grips, with cap removed. |
| No heavy battery-shaped block | Retain an open ladder sled, thin side guides and sparse feet supported above the cap floor. | Seated and travelling cell/sled clearance; rectangular cell margin checked. |
| Extra weight below the hand | Optional cap extends 18 mm below the butt and uses 45% gyroid, 3 walls, 5 top/bottom layers. Standard and heavy caps share the same real 3.4 mm pitch helical screw. | Both full screw routes checked. Like-for-like sliced mass is in `exports/mass.json`. |
| Preserve the design and ergonomic layout | Main Shard upper parts, full raised helix, slim solid loop, butt anchors Z14/Z104, button heights Z111/Z107/Z81 and mirrored angles remain. | Exported upper geometry comparison; both hands included in the prepared complete project. |

## Assembly order

1. **Print the fit-test project first.** Test the light cap in its complete thread gauge; check the upper handle socket/hook/key and the bought switch/socket in the small integral-seat coupon. Do not force a binding PETG interface.
2. **Remove the battery cap before attaching or removing the handle.** Its flange intersects the handle's unlocked travel even though the locked assembly is clear. Insert both handle hooks inward with the loop 4 mm below its final position; slide it upward into the closed stops.
3. Insert the keeper radially through the upper loop ear with its paddle aligned to the entry opening. Push it fully in, turn it 90°, then pull it outward 0.65 mm into its index notches. These notches resist unintended turning. Its paddle captures behind the internal land and blocks downward loop movement. To remove: push the keeper inward 0.65 mm, turn back, pull it out, lower the loop 4 mm and withdraw. Keep the keeper; it is a separate small part.
4. Feed the soldered socket wires through each switch opening into the main bore. Centre the socket above the opening at a small offset (1.5 mm tangentially, 2.5 mm down the wand), lower it to 2 mm above the final seat, slide under the lip into alignment, then press its locating posts into the floor holes. Snap the purchased Choc switch in last. Its factory clips hold the integral face and its installed body captures the socket outward. Removing the switch makes the socket serviceable; it has no independent printed latch. Wires do not retain the switch.
5. Insert the cell on its open sled from the bottom. The nominal **20 × 6 × 40 mm cell remains provisional**, with 0.2 mm side clearance in the rectangular-cell checks. This is not confirmation of a particular purchased pouch cell. Do not compress or force a pouch cell; the envelope must also accommodate the actual lead exit and insulation.
6. Screw in either cap. Looking directly at the bottom cap from below, tighten clockwise and remove anticlockwise. There are no bayonet lugs on these caps. Check that leads stay inside the routed chamber rather than the thread or handle receiver.
7. Use the matching existing Shard shaft and cradle. The grip-to-shaft connector is retained. This lower repair is **not** compatible with the old printed grip's failed cap or loop fittings.

## Print projects

All prepared projects use PETG, P1S 0.4 mm profile, 0.2 mm layers and 3 walls. Global infill is 20%; the solid loop and keeper use 100%, the weighted cap uses the recipe above. Every exported object is an ordinary positive mesh with its holes already cut. There are no slicer negative volumes defining physical holes. The unchanged sensor cradle retains main’s back-flat orientation and two explicitly labelled print helpers: a low-back manual support enforcer and a support blocker protecting its board/USB/wire/lock spaces. They are printing aids, not physical holes or printable model parts. All repaired lower parts and the shaft have supports disabled. Keep the checked orientations: loop broad side flat, keeper paddle face flat, short switch-test grip upright, sled back flat, caps closed underside down, stems/shaft upright and cradle back flat. The switch fit test is a short section of the actual grip, preserving its backed seat and upright print orientation rather than isolating an unsupported lip. Brims are disabled on the two cropped grip coupons so first-layer brim cannot cross their exposed service/receiver openings; the full-size grips retain their outer brims.

- **complete-both-hands**: both handed grips, one shared shaft/cradle/sled/loop/key, and both alternative caps. Assemble one chosen grip and one cap. This is not two complete wands.
- **replacement-lower-both-hands**: both repaired grips, sled, loop, key and both caps; reuse the matching main Shard upper parts.
- **fit-tests**: integral switch seat, upper handle receiver/hook, keeper, full thread gauge and light cap.
- **weighted-cap-only**: optional heavier cap.
- **one-left-light / one-left-weighted**: exactly one complete left wand each, for mass comparison.

Printed fit, keeper retention force, switch clip force, printed surface quality and impact/fatigue strength require physical testing. A successful mesh/route/slice check does not certify them. Cell/electronics, bought switches/keycaps, sockets, wiring and solder add weight to the printed-parts estimates.

## Editable source and repeatable checks

`wand_cad.py` is the CAD entry point, with `direct_switches.py`, `handle_design.py` and `cap_design.py`. It uses the retained V20 source helpers and checksummed Shard upper STLs. Dimensions are millimetres in assembled coordinates, butt Z0 and tip +Z. Use Python with numpy, manifold3d and trimesh. Generate into a fresh output directory; preserve every earlier export.

`verify_models.py` reloads exported STLs and checks body count, bed contact, all controls, keycap travel, handle movement and unchanged upper geometry. `verify_battery_caps.py` reloads those same meshes for full cell/sled insertion and both screw-cap routes. `check_sliced_paths.py` checks actual sliced extrusion in protected working passages. `verify_release.py` verifies sources, files, project contents, receipts and hashes without regenerating CAD. Run the repository checks before committing. No firmware, electronics or live controller connection is changed by this print revision.
