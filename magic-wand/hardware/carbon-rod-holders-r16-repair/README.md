# R16: repair of the failed R15 prints

R means revision. R16 follows the physical failure of the R15 A1 mini batch: the XIAO holder's
upper end printed as loose bits and fell apart, the key carrier's lower-right backplate snapped
off, the lower lip was uncomfortable under the index finger, and the battery rattled in a cage
sized for a provisional 22 x 30 x 6 mm envelope. R15 and every earlier revision are preserved
unchanged. This folder owns three redesigned parts and the end gate, their checks and one
prepared Bambu A1 mini / Generic PETG project. Nothing here is physically verified.

## What changed and why

**No removable print helpers anywhere.** Every clip ring that does not sit on the print bed grows
from a 45-degree arc lead-in skirt: the spring arm is extended toward the bed so that each layer
of the arm rests on the previous arm layer, and the crown is embedded in a saddle that reaches the
slab, keel or floor. The R15 far clip face started 26 mm up with 0.9 percent of its area over real
plastic; here `slice16.py` requires at least 90 percent of every skirted band's first true layer
(chosen by its layer middle) to sit directly on the previous layer's actual bead footprints, with
no lateral credit (95.5 / 93.9 / 94.5 % measured, see `AUDIT.md`). The saddle bonds the crown
down to 46-47 degrees above the equator on the skirted rings (measured by radial sections; the
plain far rings are bonded to 56 degrees by their end bars or plate), so each free arm runs from
that angle to its tip at -75 degrees: 121-122 degrees of arc on the skirted rings, 131 on the
plain ones. The skirt widens the arm root, so the skirted arms are stiffer than R15's:
`arm_stiffness16.py`, a stated-assumption curved-beam screen, puts them at about 2.3x (3.6 mm
bands) and 3.0x (2.4 mm XIAO band) a plain arm of the same root. The bore (7.9 mm relaxed),
30-degree gap and R7 wall profile are unchanged. The real slide force, friction and fatigue are
unmeasured; `arrow_ring.lead_angle_degrees` and the R15 bore-bracket coupon approach are the
levers if the slide feel needs tuning.

**Key carrier (`Key_Carrier`).** One flat slab, 3 lower keys with 2 centred above at the R15 pitch
(18.7 mm) and row spacing (17.8 mm), built from the standard Choc V1 interface rather than the
R7-R15 posts-and-floor seat:

- 1.2 mm switch plate with a 14.1 mm opening (13.8 mm standard plus 0.3 mm), a clip relief below
  it (15.6 x 14.3 mm) so the switch's side hooks can spring out under the plate, and a 1.6 mm
  backplate 2.25 mm below the plate top carrying the standard PCB hole pattern: 3.6 mm centre
  post hole, 2.0 mm side post holes at +/-5.51 mm, 3.1 mm holes for the hot-swap socket bosses
  at the two pin positions, each hole with a 45-degree peak toward the finger side so its roof
  is printed as 45-degree overhangs instead of a flat bridge (whether it sags is a physical
  result). The housing rests on the backplate; the socket sits under it like a PCB-mounted
  socket, located by its bosses. The switch pins locate the socket but are not its retainer:
  **one strip of polyimide (Kapton) tape across each socket's underside and its wires, pressed
  onto the backplate, is a required prototype assembly step** (Ethan: "not too snug", "you can
  always glue it in or tape it in"). The tape holds the socket on its bosses while the switch is
  pushed in, insulates the solder from the carbon rod (the lower-middle socket's underside sits
  1.6 mm above the 8 mm rod surface, 1.4 mm above the 8.4 mm rigid corridor; recorded in
  `geometry-checks.json`), and relieves wire strain. Printed snap hooks were rejected: in this
  orientation they would be thin walls loaded across layers. Away from the socket zone the
  backplate is thinned to 1.2 mm; one arrow window per bay. `verify16.py` measures every key's
  window-to-hole ligament on the final section: 1.20 mm on the four unturned keys (window point
  to the side-post hole) and 1.24 mm on the turned key, whose mirrored window edge faces that
  hole's teardrop peak and is therefore set back 0.45 mm.
- The upper-left key is turned half a turn so its socket sits outboard, clear of the ring
  saddle and of its own straight insertion from below. Every socket's 6 mm straight insertion
  from below is carved from the final solid pose by pose, so no neighbour can refill it.
- **Assembly order (required):** fit, wire and Kapton-tape every socket while the carrier is off
  the rod and upside down on the bench; then press each switch in from above while supporting
  its socket from below with a finger or flat tool (the pins are not structural and the rod would
  otherwise be the only backing under the lower-middle socket); slide the carrier onto the rod
  only after all five switches are seated.
- The index-finger edge below the three lower keys is genuinely rounded: a 2.4 mm round where
  the finger meets the underside and a 0.6 mm round at the cap side, with no lip, chamfer, chin
  or notch. The front face sits at Y -8.3, level with the inferred cap fronts.
- Two rings as on the battery holder: one between the rows (Y 9.0-12.6) and one at the tip end
  (Y 23.3-26.9), joined to the slab by one saddle. The front under the finger stays clear of
  rings so the finger wraps only the rod and the middle socket inserts straight up.
- Printed tip-edge down: the rear edge of the upper row and the tip ring sit on the bed, the
  rounded nose is the top of the print. The lower row's outer bays therefore grow from the
  upper slab through solid 45-degree shoulders. Each bay's finger-side opening edge is a
  14.1 mm (opening) and 15.6 mm (clip relief) span printed across air: the upper bays at print
  height 16.2-16.6 mm, the lower bays at 34.0-34.4 mm. The project carries Bambu modifier parts
  over those bands (16.0-16.8 and 33.8-35.2 mm) that slow every wall, gap-fill, bridge and
  overhang feature to 8-20 mm/s; `slice16.py` reads the actual F, fan and per-feature path
  length by fan level back from the G-code (walls 8-15, gap fill 12, bridges 12, overhang walls
  10-12 mm/s). Cooling is a filament-profile matter, not part of the local recipe: these slow
  layers run longer than the profile's 30 s `fan_cooling_layer_time`, so the base fan falls to
  the 40 % minimum and only the paths the slicer classifies as overhang wall or bridge get the
  90 % overhang/bridge fan (carrier bands: 307 mm of such paths at 90 %, 353 mm of gap fill at
  40 %). A local "more walls in the bands" variant was sliced and rejected: it turned the
  bridges into walls and raised the 40 % gap fill to 512 mm (see `AUDIT.md`). No global fan
  change was made unasked; `fan_min_speed` in the filament profile is the lever if the roofs
  droop. Digital evidence does not predict PETG droop: the switch housing has only 0.15-0.2 mm
  of clearance at those edges, so inspect all five edges for sag and trim before fitting switches.

**Battery cage (`Battery_Holder`) and gate (`Battery_End_Gate`).** Sized for the identified
PKCell LP402025 150 mAh protected pack at its manufacturer maximum of 20.5 x 27.5 x 4.3 mm:
reserve 21.2 x 28.0 x 4.9 mm, so the nominal play is 0.7 mm across, 0.5 mm along and 0.6 mm in
thickness instead of about 2.4, 3.3 and 2.1 mm in R15. The retailer's 26 x 21 x 4 mm text differs
from the drawing and is recorded, not used. Nothing presses the pouch. Floor and roof are
chevron lattices pointing toward the tip; the side rails are 45-degree zigzag trusses; the closed
end plate has a pointed window and sits on the bed. The cell is stopped at the closed end by two
corner blocks and at the gate end by two stubs on the gate, both outside the lead end. The cell
goes in non-lead end first from the gate end; the leads trail and leave through the open 13 mm
centre of the gate. The gate keeps the R15 sliding wedges and the 1.6 mm outer guide wall (the slot
is open toward the cage so the bar can pass, as in R15), with a 1.9 mm grab bar above the cell. The
guide end cap closes over each slot as a short cantilever; its inner top corner is chamfered 1 mm
and the band 33.6-34.4 mm is slowed by the same modifier recipe. The roof lattice stops before
the gate so the gate lifts straight out.

**XIAO Sense holder (`XIAO_Rod_Holder`).** Target: Seeed XIAO nRF52840 Sense on the official
plain-board outline, 20.955 x 17.78 mm with R1.905 corners (parent's measurement of the plain
STEP; nothing about the fitted header configuration is derived from it), board underside at
Z 8.8 mm (R2 stack assumption). Same rail interface (X +/-9.2-11.2 mm), rebuilt so that nothing
starts in air: full-length rails, a 3 mm keel over the rod joining both crowns, flat end bars in
the far ring plane on the bed, 45-degree gusset bars at the near end that grow from the rails
toward the saddle, and one diagonal strut per side from mid-rail down to the keel below the board
(about 47 degrees in print) so the rails are no longer 21 mm free columns. Board seat: because
the corners are rounded, the straight ends of the board lie inside |X| 6.985 and the earlier
ledges at X 8.0-8.2 could lose contact entirely. Each corner now rests on an L-shaped end cradle
joined to its rail: a 1.0 mm thick ledge from the rail in to |X| 7.3 under the first 1.0 mm (near)
or 1.3 mm (far) of the board, and a stop above the board plane. The near ledge is led in at
45 degrees from the rail; the near stop is a 45-degree face in plan tangent to the corner arc
offset by 0.3 mm (a flat face at |X| 7.3 cannot be printed at 45 degrees or less in this
orientation), so the two near stops form a self-centring V for the USB-plug push. The far ledge
and far stop stand on the bed, outside the USB footprint, and take the unplug pull. `verify16.py`
sweeps the rounded outline through its whole play (0.31 mm to each rail, 0.43 mm to the near V
when centred and 0.12 mm when hard against a rail, 0.35-0.38 mm to the far stops; the bisected
mesh values agree with the analytic model within 0.006 mm). The independently checked printed
V is stepped on the 0.2 mm layer grid: near travel is about 0.35 mm centred, 0.20 mm at a
0.15 mm sideways offset and 0.04 mm against a rail; real board tolerance and printed fit remain
unverified. The CAD check finds at least 0.91 mm² (near) and
0.72 mm² (far) of ledge directly under every corner at all 25 poses, stops engaged at every
lateral pose, USB plug body and top-side pad access clear, and the 1.5 mm keepout under the board
centre (|X| <= 4) untouched by any contact geometry. `slice16.py` scans the surviving printed
beads of all four ledges, both V tabs and both far blocks layer by layer. The near ledge lead
runs under the board edge to Y 4.2. On the stated pad assumption, only its tip reaches the
first pad: 0.027 mm² per side averaged through the 0.05 mm directly below the board plane
(CAD), about 0.03 mm² in the printed beads. The independent DXF-land check gives at most
0.17 mm² per side. Other material beneath assumed pads 1, 3 and 4 is 0.54-0.76 mm below the
board, not contact. Solder the external wires on the top pads and keep the contact undersides
flat, as the rails already demand flush castellations. **Tape across the
board and rails is a required prototype step** because nothing printed holds the board down. The
USB end prints on the bed. The near ring (Y -5.0 to -2.6) is the one at the top of the print and
carries the lead-in skirt under the antenna end of the board. Between the end cradles, the
minimum underside clearance is 0.536 mm at the edge struts and 1.84 mm under |X| <= 4; the
cradles themselves intentionally touch the board. The rails, end bars, near gussets, diagonal struts and
cradles all assume no header plastic below the board edges: a board with pre-soldered underside
headers is not fitted by this or any earlier holder, and the fitted header configuration is still
unknown.

## Reference photo and measurements used

The working reference photograph (five bays, flat backplates with the Choc post and pin holes,
connected frame) set the interface philosophy: standard plate cutout plus a PCB-pattern
backplate. It was not used to restore the rejected side-key layout, copy its mass or infer a rod
attachment. Dimensions come from the Kailh CPG135001D01 switch drawing, the CPG135001S30 socket
drawing and the sourced KiSwitch meshes frozen under R7 (`references/provenance.json`), measured
again here by exact sections: housing 13.44 mm in the mesh (13.8 mm drawn), flange 15 mm at
Z 2.25-3.05, centre post 3.2 mm, side posts 1.65 mm at +/-5.51 mm, pins at (0, 5.87) and
(5.0, 3.86), socket body 9.55 x 6.85 mm with 2.82 mm bosses. The inferred 17.5 x 16.6 mm cap and
the 0.4 mm play allowance are unchanged and still unmeasured: measure a mounted cap before
relying on the 0.4 mm residual gap.

## Files

- `parameters.json`, `holder16.py`, `spaces16.py`: editable model and the single definition of
  every working space. Composes only the frozen bought interfaces from the R15 chain.
- `exports/*-assembly.stl` (assembly frame) and `exports/*-SOURCE-REQUIRES-PREPARATION.stl`
  (print frame, bare). `exports/manifest.json` binds sources and meshes.
- `verify16.py` -> `exports/geometry-checks.json`: working spaces, bought parts, cap envelopes,
  window ligaments of every key, socket-to-rod clearance, cell play, gate, the rounded board
  outline through its full play (travel, cradle contact, stops, access), rings, stack and
  section screens.
- `project16.py` -> `exports/R16-A1-mini-PETG.gcode.3mf` and `-print-checks.json`: the sliced
  project (Bambu Lab A1 mini 0.4 nozzle, Generic PETG @BBL A1M, 0.20 mm Standard, 3 walls, 20 %
  infill, 255/70 C, no support, no brim, 20 mm/s first layer), built from the installed Bambu
  Studio profiles exactly as the actual R15 A1 mini print was prepared.
- `slice16.py` -> `exports/slice-clearances.json` and `*-layer-views.png`: every bead type in
  every working space, actual previous-bead backing of every layer, band-start regression for
  each skirted ring, skirt and ring sections with surviving tracks, fixed load-path sections,
  complete layer scans of the load paths and board cradles, band speeds and per-feature path
  length by fan level, bridge/overhang locations.
- `roundtrip16.py` -> `exports/roundtrip-checks.json`: reloads the exact delivered gcode.3mf in
  the offline Bambu Studio CLI (process-private HOME/CFFIXED_USER_HOME, --datadir and TMPDIR in
  task scratch), re-slices it into scratch and checks that the re-sliced archive carries the same
  meshes, plate settings and modifier parts and that its G-code passes the same `slice16` audit
  with the same functional results. GUI reopening is not available in this offline environment.
- `arm_stiffness16.py` -> `exports/arm-stiffness-screen.json` (stated-assumption screen).
- `views16.py` -> overview, layout and assembled images; `check16.py` -> `delivery-checks.json`.

## Reproduce

Run each unit serially through the repository runner, for example
`python3 .agents/skills/printability-audit/scripts/geometry_budget.py --timeout-seconds 900 -- <cad-python> magic-wand/hardware/carbon-rod-holders-r16-repair/holder16.py`,
then `verify16.py`, `views16.py`, `project16.py --slice --scratch <external scratch>`,
`slice16.py`, `roundtrip16.py --scratch <external scratch>`, `arm_stiffness16.py`, and finally
`python3 check16.py`. Keep Bambu CLI scratch outside the repository. `project16.py --out-dir
<scratch> --band-wall-loops N` slices a recipe experiment outside `exports/` without touching
the delivered project.

## Physical trial

After measuring the mounted caps and cell, and confirming the XIAO underside and top-side
wiring, print the complete four-part test project. Watch: the first layers (upper-row edge, ring ends, end
plate); the skirt leads (carrier 13-22 mm, battery 20-30 mm, XIAO 18-26 mm print height); the
carrier's bay opening edges at 16.2-16.6 mm and 34.0-34.4 mm (slowed bands); the battery guide
caps at 33.8-34.2 mm; the XIAO rails from 2.6 to 23.8 mm and the near cradles at the very top
(21-24 mm). Deburr bed edges lightly; the A1 mini profile has no elephant-foot compensation.
Check every switch opening edge against a bare housing and trim sag before fitting. With the
carrier off the rod: fit each socket from below with its Kapton strip, then press each switch in
from above while supporting its socket from below; press every key through full travel with
sideways bias and tug each wire; only then slide the carrier onto the rod. Slide every ring from
a bare rod end; stop on cracking or excessive force (the skirted arms are stiffer than R15's).
Load the cell non-lead end first from the gate end, fit the gate by its bar with the leads
trailing through the centre opening, and cycle the gate without a cell first. Seat the board on
its four cradles between the V stops and the far blocks, tape it down, plug and unplug USB.
Comfort, slide force, retention, strength and fatigue remain physical results; the cradle
contact areas, stop engagement and bead survival are geometric and toolpath facts only.
