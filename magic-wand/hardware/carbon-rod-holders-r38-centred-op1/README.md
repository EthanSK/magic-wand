# R38 centred OP1 click — first-fit trial

R38 follows [R37](../carbon-rod-holders-r37-adjustable-op1/README.md). It has
been sliced and audited for a first physical fit trial. R38 has not been
printed. R37 and its print files are unchanged.

## What changed

- The OP1 mouse-switch board sits straight on the rod centre line, X = 0.
  In R37 it sat 7.45 mm to the right. The centre click stays bottom-aligned
  with the three-key row, and the rear snap hinge keeps its position.
- The OP1 seat alone is 0.9 mm higher. The board underside is 10.1 mm
  above the rod centre. The modelled plug then clears the 8 mm rod by 0.2 mm.
- The Grove board, its two screw seats and its plug pocket sit 2.0 mm to
  the left and 0.9 mm higher. The Grove socket under that board then passes
  0.6 mm beside the OP1 board. The touch pad centre moves from X 1.6 to −0.4.
- The adjustable stop screw moves from the centre to X 8.3, beside the
  board. Its old landing is now under the OP1 front screw and switch body.
- A new left rail outside the Grove socket carries the left hinge arm
  load to the front of the bracket. The shifted socket pocket removed the
  old rail.
- The carrier centre is rebuilt from the R22 base. The old R26 stop recess
  that R34 left in the deck, the rear-loading board channels and the side
  OP1 mount are gone.

## Measured against R37

| | R37 | R38 |
| --- | ---: | ---: |
| Key carrier width | 60.2 mm | 60.05 mm |
| Key carrier depth and height | 41.85 × 24.78 mm | unchanged |
| Key carrier solid mass | 9.75 g | 9.61 g |
| Grove bracket width | 21.2 mm | 22.6 mm |
| Grove bracket solid mass | 0.78 g | 1.06 g |
| Touch face at the stop | 21.03 mm | 21.93 mm |
| Choc seat, rod clip and hinge axis heights | | unchanged |

The exact-centre layout is not substantially thinner or lighter. Both parts
together are about 0.13 g heavier, and the touch face is 0.9 mm higher. The left-shifted Grove
board limits each Choc seat to a 0.1 mm inward move while keeping 0.7 mm to
the caps. An earlier trial with the OP1 board 2 mm off centre and the Grove
board unmoved allowed 1.5 mm per side and a 0.96 g lighter carrier. Masses
are solid mesh volume at 1.27 g/cm³, without pads or slicing.

## Checks

`assembly38.py` writes [geometry-checks.json](exports/geometry-checks.json).
All CAD checks pass:

- OP1 three pins, socket barrels, white housing, plug and wire against the
  rod, the carrier and the four Choc envelopes
- wired OP1 board and its complete lead lowering, switch insertion, Grove board lowering with its
  plug, and Grove lead feed
- bracket pinch, drop and release, the full click stroke to the backup
  stops, and every stop-screw setting
- hinge tab engagement, lift retention, rib joins and fingertip probes
- a rod reference guard, which fails when the rod is deliberately misplaced

The stop screw sets the switch stop from 6.55 to 7.29 mm above its base and
always lands before any printed contact.

## Before printing

- Use the checked [editable plate](exports/standard-retry/R38-Complete-A1-mini-PETG-layout.3mf)
  or [print-only file](exports/standard-retry/R38-Centred-OP1-print-only.3mf).
  They include seven parts: key carrier, Grove bracket, XIAO holder and
  keeper, battery holder and end door, and the 12-wire cable clip. The
  unused battery spacer is excluded from both the plate and current viewer.
- Print from the **print-only file**. The final Studio re-slice of the editable
  plate moved the wipe tower and omitted the approved gentle layer commands.
  That GUI output was rejected; the unchanged checked print-only file was
  reopened in Studio with slicing disabled. Treat the editable plate as
  authoring input and repeat the command and toolpath audit after any re-slice.
- The plate retains R37's Standard PETG recipe: 245°C nozzle, 60°C bed,
  gentle first three layers, 6 mm brims, broad 0.4 mm pads and narrow
  accessible ties. Smooth timelapse uses its wipe tower. Estimated material
  is 18.85 g; elapsed print time is about two hours, plus printer preparation.
- Four selected carrier roofs have normal removable support with a
  realised 0.2 mm separation. Board-screw seats use local solid infill;
  the remaining carrier keeps its sparse infill. Guard beams are 1.9 mm
  across. A short local rod-transition relief clears the deposited beads
  without changing either 7.8 mm gripping band.
- The [actual-slice audit](exports/standard-retry/slice-audit.json) passes
  all seven parts, first-layer attachment, connected starts, working
  openings, insertion routes, critical joints and support interfaces.
  All four selected roofs have interface coverage at the intended gap.
  The audit also reports support occupying the rod and connector paths;
  those spaces are not usable until cleaned.
- Once cool, cut the pad ties. Remove the central support through the
  empty board opening and the open rear end of the rod bore. Remove the
  small outer guard support outwards. Check the entire rod, plug and cable
  paths before fitting electronics. The removal grid is only a coarse
  small-fragment access check, not proof of easy hand removal.
- Watch the small outer guard support during its first trial: it is a
  slender free-standing support for a small non-structural roof. A failed
  support may leave a rough edge or loose strand. Physical support removal,
  printed strength, hinge force, click feel and fatigue remain untested.
- OP1 board, connector depth (5.9 mm) and wire sizes are scaled from
  photos. The manufacturer kit photo shows a two-wire mating lead.
  The candidate routes it out of the plug's longitudinal end face, then
  beside the rod. The entire prewired insertion/removal path has a
  clearance channel, rather than moving the cable origin to a side corner
  to avoid the rod. Outlet height and bend stiffness remain unmeasured.
  This is a conditional fit-trial route, not a physically verified harness.
- The Grove board overhangs the bracket by 1.4 mm on the left.

The independent Opus review accepted the repaired geometry for a first-fit
trial with those cleanup and support caveats. A passing slice does not
guarantee a successful print or hardware fit. The exact-centre request is
implemented; substantial weight and thickness reduction remains unfinished.

## Regenerate

Run from the repository root with the CAD runtime on `PYTHONPATH`:

```sh
python3 .agents/skills/printability-audit/scripts/geometry_budget.py \
  --timeout-seconds 1500 --receipt <scratch>/r38-export.json \
  -- python3.14 magic-wand/hardware/carbon-rod-holders-r38-centred-op1/assembly38.py
```

`assembly38.py --register` adds the guide to the shared viewer. `plate38.py`
builds a fresh editable plate from the current meshes and the exact R37
recipe. Slice with the installed Bambu Studio, then run `audit38.py` on
that archive. Package a print-only file only after the audit passes.
The manifest, plate receipt and slice audit bind their results to source
and artifact hashes; changing geometry or settings requires another slice.

## Bounded packing check

[The static packing probe](evidence/packing-probe.json) tests both 90-degree
crosswise PCB orientations against the bought-part and R37 Choc envelopes.
Both clash with the lower keys and the original Grove assembly. Clearing
only the key clashes would add at least 14.2 mm to the overall key spacing,
so that change is not adopted. The same probe checks the longitudinal lead
and its full insertion path against the final carrier.

The evidence scripts use the same CAD runtime as the model. They are
checks, not alternative geometry sources. The source hash in each report
identifies the exact candidate tested.
