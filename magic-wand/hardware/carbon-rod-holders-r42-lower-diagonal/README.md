# R42 · Lower DFRobot touch with diagonal OP1 click

**Print hold after the R41 physical trial:** one part toppled late in the combined print.
The combined R42 package remains a digital audit artifact; do not restart it unchanged.
Image/layout comparison points to the battery holder, with the key carrier still standing;
peeling, fracture and collision remain unconfirmed initiating causes. The next trial isolates the main key carrier. Separate grouped keys, battery
and XIAO/cable jobs also remain prepared, with a changed battery attachment.

R42 seats the DFRobot DFR0030 touch board **0.95 mm lower** inside the R41
bracket. Its released touch surface is about **1.72 mm above the Choc caps**.
The key carrier, diagonal OP1 board, rod position, hinge axis, pusher and
adjustable stops retain R41's positions. This is the next trial candidate;
the R41 physical trial has now been stopped after toppling.

## What limits the height

The three OP1 terminals are not the closest obstruction. Its fitted harness
plug has only about **0.31 mm** nominal clearance beside the round rod.
Lowering that OP1 stack by 0.15 mm reduces this to about 0.198 mm, below the
existing 0.2 mm clearance gate. Lowering it by 0.30 mm leaves about 0.09 mm.
A limited 21–32° yaw study retaining the adjacent Choc wall did not create
more useful clearance. These measurements concern the preserved layout;
they do not prove every possible layout is optimal.

R41 left space between the bracket floor and the DFRobot board. R42 uses
that space instead: its board underside is at Z 19.30 mm, the fixed floor
at 19.20 mm and the unchanged arm/root tops at 19.00 mm. The board sits on
its side rails, hole pads and front web. It is lower, but not fully flush.

The local Gravity-pin pocket clears the modelled 1.5–2.0 mm factory tails
and solder flares. A 45° local relief opens the pocket through the inner
fan tips without changing the loaded arm roots or pusher. The raised rear
pinch pads start 0.33 mm farther back so the lower board can slide past.
The hinge still uses the two flexible side arms and their integral pins;
there is no separate hinge axle.

## Complete print (9 parts)

| Component | Printed parts |
| --- | --- |
| Keys | Key_Carrier, DFRobot_Hole_Bracket, DFR0030_Post_Clip, DFR0030_Post_Clip_2 |
| XIAO | XIAO_Rod_Holder, XIAO_Near_Keeper (R25) |
| Battery | Battery_Holder, Battery_End_Door (R39 lower catch) |
| Cable | Cable_Clip_12_Wire (R22) |

The DFRobot board and lead, OP1 kit and screws, M2 × 4 stop screw, Choc
switches and carbon rod are bought parts. There is no Grove board and no
loose flat battery spacer in this print. The assembly guide retains all
five component selections, including the whole assembly.

## Single key-holder diagnostic

Ethan selected the main key holder alone for the next trial, after he gets
home and clears the failed plate/nozzle. `single42.py` prepares only
`Key_Carrier`, keeping its removable adhesion pads, required native supports
and Smooth-timelapse wipe tower. The DFRobot bracket and both post clips are
excluded by this explicit diagnostic selection. The complete assembly and
three grouped jobs below remain available; this is not a complete keys kit.
The selected file is
`exports/key-holder-only/R42-Key-Holder-Only-print-only.3mf`: about **1 h 41 min**,
**14.62 g**, at **245°C / 60°C**. Its initial and reopened own-path audits both
passed without slicer warnings. Nothing has been sent to the printer.

`carrier_checks42.py` checks the single job's own deposited paths for working
openings, load-path sections, pad joins, support backing and cleanup access.
The single-object comments produced by Studio are adapted in memory for the
existing readers; executable commands and delivered G-code are unchanged.
A path comparison with the group job is diagnostic only, never a substitute
for checking the changed single-job paths. Preparation does not authorize
sending or starting the print. Physical fit, strength and success still need
the real trial.

## Separate retry jobs

The complete assembly is the component source; the next trials use three
separate jobs in `exports/print-jobs/`, prepared by `split42.py` and retained
by `retain_split42.py`. All nine parts appear exactly once across the jobs.

| Job | Contents | Estimate | Material |
| --- | --- | --- | --- |
| Keys assembly | Carrier, DFRobot bracket, both post clips | 1 h 49 min | 15.50 g |
| Battery | Holder and matching door | 45 min | 4.88 g |
| XIAO and cable | XIAO holder, keeper and cable clip | 39 min | 4.12 g |

The keys assembly is separate from the battery and XIAO, **not a one-object
carrier plate**: the touch bracket and its two clips remain with it. That
limits cross-part loss from the other holders but does not isolate a bracket
failure from the carrier. The bracket has not completed its full height in
the R41 physical trial; its attachment and cleanup remain trial checks.

The battery's permanent mesh and upright orientation are unchanged. Its six
outward pad necks widen from 1 to 2 mm, still only 0.4 mm/two layers thick.
Pad extension increases from 6 to 8 mm. Actual reopened first-layer model
and helper contact is 1205.642 mm² versus R41's 1017.289 mm², about 18.5%
more. Each nominal neck/body contact doubles to about 0.74–0.80 mm², and
both sliced pad layers remain joined. Cut the ties before lifting the body;
easy removal and physical strength have not been established.

An initial native 8 mm outer brim entered the open rod bore and clip mouth.
It was rejected by the actual path check. The selected battery holder uses
the larger outward CAD pads instead, with zero working-space violations;
the matching door keeps its removable brim. The battery is shifted to
X 30, Y 63, keeping its larger pads inside the verified edge margin.

Each job passed its own initial and reopened path audit. The exact selected
G-code is copied into its print-only file; source revalidation checks all
embedded meshes, placements, settings and height ranges after report-only
corrections. Temperatures remain 245°C/60°C, with Smooth timelapse and its
wipe tower. Sending still requires checking Timelapse in the actual dialog.

**No retry has been started.** Before clearing the cooled failed plate,
inspect where the battery separated: pads left on the plate indicate the
ties; pads lifting with the holder indicate adhesion; a break above the
base or curled upper strands needs a different correction. The camera
does not establish that cause. The higher bridge/overhang features remain
physical checks, and stronger base helpers do not fix an upper break.

## Sources and preparation

- `holder42.py`: source solids and clearance/motion checks, composed from R41.
- `assembly42.py`: normal and print meshes, geometry manifest and assembly guide.
- `complete-assembly.json`: the complete nine-part build list.
- `plate42.py`: native Studio settings, orientations, supports, blockers and pads.
- `audit42.py`: actual deposited-path checks, including working openings and joints.
- `trial42.py`: retains the selected archive and its hash-bound review record.
- `test_audit42.py`: adversarial support-removal and connected-material fixtures.
- `split42.py`: three scoped native projects, changed battery ties/brim, and actual
  per-job initial/reopened path audits. Preparation is not print authorization.
- `retain_split42.py`: complete/disjoint selection, exact artifact bindings and
  retained per-job evidence. The combined package below remains historical.

Run heavy geometry and slicing through the repository's serial
`geometry_budget.py` runner. Generate with `assembly42.py`, prepare a fresh
staging directory with `plate42.py`, slice, then audit the actual archive.
Reopen and re-slice once and audit the reopened archive's own toolpaths.
Retain both evidence directories with `trial42.py`; raw STLs are not the
checked print package. Register a checked guide with `assembly42.py --register`.

## Selected PETG trial

The retained `exports/print-trial/R42-DFRobot-Diagonal-print-only.3mf` copies
the selected reopened G-code without another slice. The editable layout and
reopened sliced archive are retained separately with the reports. The
composite `print-manifest.json` describes all nine staged parts; the root
`exports/manifest.json` describes this revision's generated sources/meshes.

- A1 mini, 0.4 mm nozzle, textured PEI, external Flashforge HS PETG Metallic Red.
- 245°C nozzle, 60°C bed, 0.2 mm layers, slow first three layers, 8 mm³/s max flow.
- Selected reopened estimate: **2 h 24 min 5 s**, **21.40 g**.
- Carrier rear face down; bracket front face down; small clips flat.
- Native snug supports under the required carrier roofs and early bracket feet.
- Actual support paths must stay out of the rod grip, clip mouths and hinge bores.
- Smooth timelapse requires its separate wipe tower. Enable timelapse, bed
  leveling and flow calibration when sending; the file is not evidence that
  those send-dialog options were selected.

Wide removable pads use narrow cut ties. R42 moves the bracket ties 0.4 mm
away from the lowered board's loading route and extends their overlap with
the fixed face by 0.1 mm. Both initial and reopened slices check the entire
deposited bead footprint; their board-loading core intrusion is zero.
The nominal tie/body overlap is 0.102 mm² per side, against R41's 0.140 mm².
The same 1 mm external neck and broad pads remain; equal strength or adhesion
has not been established. Watch the narrow ties and bracket base in the trial.

The final report accounts for all partial overhangs, actual support backing,
support removal routes, every working opening and the complete pusher load
path. The unchanged carrier has small remaining reaches under 0.84 mm.
The bracket's remaining short ledges reach about 1.55 mm; its existing
two-ended bridge has a measured maximum distance of about 1.98 mm to its
actual backing. Physical underside quality and bridge sag still need a trial.
The short hole-pad fronts and local pocket/pinch-pad starts are below the
2 mm² reporting filter. Their absence from the rows does not prove support
backing; the source review accepts them as short trial features, about
1.2 mm or less, with their undersides still needing physical inspection.

## Assembly and physical checks

Remove all pads, ties, brims and listed native supports before fitting
electronics. Fit the OP1 plug, wire and Choc sockets before clipping the
carrier onto the rod. Follow the guide for the DFRobot board, its two
post clips, squeeze/lift hinge release and remaining components.

Set the stop screw against the **real** fitted switch: the click must close
before either stop touches, and release without binding. Never force the
plunger. Check the lowered board's factory pin tails and any solder bumps
against the local relief, and check clips and arm roots while assembling.
Gravity tails longer than the checked 2.0 mm are outside this fit envelope.
Push the board forward on its posts and check that it rests on its rails,
not on the raised rear pinch pads. Hole play can exceed the nominal 0.3 mm
rear gap; do not force a board that will not seat.

CAD and deposited-path checks do not establish physical fit, easy cleanup,
strength, fatigue or comfort. Several DFRobot and OP1 dimensions are
photo-derived or assumed. The 0.1 mm floor clearance is nominal, not a claim
of printer accuracy. Inspect the complete part before putting force on it.
