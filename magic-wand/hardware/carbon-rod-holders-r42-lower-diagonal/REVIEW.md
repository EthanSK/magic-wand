# R42 final review

**Later physical evidence:** the combined R41 trial was stopped after a part toppled
around layer 143. That overrides treating the same complete-plate preparation as ready.
The verdict below records the earlier digital review; the next print needs separate
plates and renewed stability checks. No causal link to diagonal OP1 yaw is established.

The independent Claude Opus 5.5 review accepted the selected assembly for a
first physical trial, with no blocking printability finding. Its run also
included a Fable 5.1 check. The parent separately reviewed the sources,
inspected the actual slice plots and tested the viewer.

This review concerns the reopened archive with SHA-256
`22799be1a7d606da2fe6f2a8b1fce38c696c5a67abe0ea5cecfcd71c3360ba4e`.
The parent corrected the two checks/reporting findings below. The final
source, geometry and evidence bindings are in `exports/print-trial/trial-review.json`.
Printed shapes and settings are intended to remain identical across those
corrections; the retained revalidation record establishes that separately.

## Findings

### 1. Fixed — Let the floor-height probe detect raised material [Claude Opus 5.5]

**Severity / priority:** Low — P3; a checking defect, not a discovered collision.

**Change required / fix effort:** Small, about 10–15 lines — holder42.py, test_audit42.py.

**What happened:** The old floor probe stopped at the expected floor height
plus 0.001 mm. It clipped away an unwanted taller face before the height
gate could inspect it. The physical board-space cut remained a separate
geometry constraint, so the defect overstated this measurement's coverage.

**Example:** A negative fixture added a 19.26 mm top surface inside the floor
region. The old probe reported only 19.201 mm and the regression fixture
failed, demonstrating that it could hide the extra height.

**Fix:** Extended the measurement region above the expected floor and kept
the existing height acceptance threshold. Added the raised-floor fixture.
This follows the established pattern of measuring actual remaining geometry,
as `seat_metrics` does for arm roots and `audit42.py` does for deposited
material. It changes the check, not the bracket solid.

### 2. Fixed — Describe the real overhangs and reporting limits [Claude Opus 5.5]

**Severity / priority:** Low — P3; evidence/reporting, with physical trial limits.

**Change required / fix effort:** Small, about 15–25 lines — trial42.py, README.md, plate42.py.

**What happened:** The decision text called two bracket starts
"nonfunctional", although they are leading ends of load-bearing root ribs
and fans. Smaller starts also fell below the inherited 2 mm² reporting
filter; absence from its rows did not establish support backing.

**Example:** The actual 19.8 and 25.8 mm rows reach about 1.55 mm beyond
their backing. Opus checked them against R41's matching rows and source;
they are short starts away from the loaded root, not cosmetic material.
The lowered hole-pad fronts no longer exceed the reporting filter.

**Fix:** Named the rib/fan ends, retained the same measured reaches and
acceptance limits, and recorded the below-filter hole-pad, pin-pocket and
pinch-pad starts as source-reviewed trial features with unmeasured backing.
Clarified the tie contact separately: 0.102 mm² per side versus 0.140 mm² in
R41, with the same 1 mm external neck. Equal physical strength or adhesion
was not measured. This follows the established pattern of explicit
per-overhang decisions in `trial41.py` and actual support-removal reporting
in `audit42.py`; no unsupported region was waived by lowering a threshold.

## Per-part disposition

| Part | Digital evidence and physical limit |
| --- | --- |
| DFRobot_Hole_Bracket | Full pusher/load path remains connected; critical material fractions at least 0.913. Board/pin loading routes and working spaces pass. Foot interfaces back the early feet at a 0.2 mm gap. The existing 3.4 mm two-ended bridge and short root starts still need underside/strength inspection. |
| Key_Carrier | Same mesh as R41. Actual support is absent from the rod grip, clip mouths and hinge bores. Remove support from the listed key/OP1/pilot spaces before fitting parts; reachable removal is not proof of easy cleanup. |
| DFR0030_Post_Clip and _2 | Same dimensions; their assembly height follows the lowered posts. Four flat layers and checked pads/ties. First-layer squashing can stiffen the 0.1 mm snap engagement; inspect the jaw edges after cleanup. |
| XIAO_Rod_Holder and XIAO_Near_Keeper | Reused R25 parts; no floating starts or reported overhang rows in the selected complete slice. Physical keeper fit still needs inspection. |
| Battery_Holder and Battery_End_Door | Same meshes as R41, lower R39 catch. No floating starts or reported overhang rows; clean door slots and catch before fitting. |
| Cable_Clip_12_Wire | Reused R22 part, checked complete plate and pad attachment. External wire runs remain illustrative. |

## Physical first-fit checks

- The touch face is 0.95 mm lower, still about 1.72 mm above the Choc caps.
  The unchanged OP1 plug has about 0.31 mm clearance beside the rod.
- The board-to-floor gap is nominally 0.1 mm. Both are rigid features of the
  same bracket; seam contact does not establish a moving-part collision.
- The rear board edge has only 0.3 mm nominal clearance to the raised pinch
  pads. Hole play can exceed that. Push the board forward and confirm it
  rests on its rails; do not force a board that will not seat.
- Gravity tails are checked only up to 2.0 mm below the PCB. Confirm that
  envelope before clicking; longer unmeasured pins are outside this fit check.
- Inspect support cleanup, pad/tie release, clip force, hinge/root strength,
  rod grip and click/release with the real switch. Set the stop against that
  switch rather than treating CAD travel as measured actuation.

The lower seat, exact bought-part dimensions, cleanup, force, fatigue and
comfort have not been physically accepted. A machine finish does not close
those checks. Finding attribution: Codex 0, Opus 2, shared 0.

## Subsequent split-job review

An independent resumed Claude Opus 5.5 review found no file-level blocker
to a first trial of the three selected jobs. Its run included Fable 5.1
advice. All three jobs have their own initial/reopened path audits, and
their selected print-only files retain byte-identical G-code. This verdict
does not establish physical success or the cause of the R41 failure.

The parent retained the matching touch bracket/clips with the keys assembly;
it is separate from the battery and XIAO jobs, not a carrier-only plate.
The review identified the remaining risk that the tall bracket can fail
on the carrier's plate. Its final height, helper strength and cleanup
remain physical trial checks. There is no evidence establishing which
part is most likely to fail in the new jobs.

The battery base changes target detachment or tie separation, not a break
higher up or a nozzle strike. Its small bridge at print Z 28.4 mm and
overhang-wall starts at Z 29.6 mm fall within the broad image observation
window. That timing does not identify them as the cause. Inspect the
cooled failed base before clearing it; do not treat more bed contact as
a confirmed cure.

### 3. Fixed — Scope each job's extent metadata [Claude Opus 5.5]

**Severity / priority:** Low — P3; stale diagnostic metadata, not changed G-code.

**Change required / fix effort:** Small, about 5–10 lines — split42.py.

**What happened:** The job selection filtered its build list and material
bounds but left `plate_extents_mm` describing all nine full-plate objects.
A later clearance reader could consult absent parts or old positions.

**Example:** The keys report listed nine extent entries beside a four-part
build list. Static source/report inspection established the mismatch;
the selected native project itself contained only the four intended parts.

**Fix:** Filtered the extent dictionary by the selected names and refreshed
the job metadata. This follows the established pattern used for
`source_parts` and `material_bounds_xy_mm` in the same selection function.
Fresh preparation is compared against every embedded model, placement,
native setting and height range before reusing the audited print bytes.

### 4. Fixed — State and refresh widened-tie diagnostic coverage [Claude Opus 5.5]

**Severity / priority:** Low — P3; diagnostic provenance and coverage limits.

**Change required / fix effort:** Small, about 10–15 lines — split42.py.

**What happened:** The widened battery helpers copied the older tie-site
record alongside new full-width contact measurements. The report did not
explain the limited backing probes or the cutter-corridor width.

**Example:** A 2 mm tie had doubled full-width contact, but its backing
diagnostic still used line probes at −0.4, 0 and +0.4 mm. Those three
lines do not establish strength across the entire widened neck.

**Fix:** Recomputed the tie-site diagnostics from the current body and
current plan, retained the complete-neck contact measurements separately,
and labelled the three probe offsets and 3 mm cutter corridor. This follows
the established pattern in `anchors19.tie_sites_report` and the separate
contact measurements in `battery_stage`. No printed shape or threshold
changed; physical cutting effort and strength remain unverified.

The old keys job metadata field name was refreshed at the same boundary.
Source revalidation now explicitly compares embedded mesh bytes as well
as placements, settings, ranges and staged source/pad hashes. These are
metadata corrections, not new slices or extra physical trials. Split-review
finding attribution: Codex 0, Opus 2, shared 0.
