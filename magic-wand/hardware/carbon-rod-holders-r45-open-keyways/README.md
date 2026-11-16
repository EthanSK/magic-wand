# R45 — key-holder printability repair

Status: file checks passed for a first physical trial. On-screen verification
and Studio loading await an unlocked Mac. No R45 print has been started.
See the [parent trial assessment](exports/key-holder-only/trial-review.json)
and [independent reopen comparison](exports/key-holder-only/reopen-checks.json).

R44 completed its machine cycle, but its automatic support filled the working
switch openings. See [the rejected physical trial](../carbon-rod-holders-r44-middle-finger-rest/PHYSICAL-TRIAL.md).
R45 preserves the R44 bought-part positions, outer key collars, rod clips and
rounded joined finger rests. Flat and tilted experiments were rejected. The
selected standing preparation adds backing under a free lip, relieves unused
lower ledges, and replaces the abrupt leading corner of the left guard web
with a buttress growing from the frame. The original rod skirt is retained.
The selected native paths, rather than a CAD-only result, determine the trial.

All 33 original structural reference volumes remain visible in the audit,
including the six deliberately replaced web/joint targets and their exact
losses. The replacement has separate, pre-union frame and individual rib
references. Its actual printed overlap and connected sections at specified
physical stations must exceed the originals. Whole-member and joint coverage,
including any small joint end slabs below 90%, are retained rather than hidden
or cropped into a pass. Other structural targets retain the original checks.

Only the key carrier is a functional part on this trial plate. Its matching
DFRobot bracket and the existing battery, XIAO and cable components remain
available in the versioned assembly guide; they are not on this one-part trial.
The project retains Smooth timelapse's separate wipe tower. A real future
send still needs Timelapse checked in Studio's send dialog.

## Print helpers and cleanup

The conventional `External_cradle` supports bed-visible undersides and is
withdrawn in the negative print-Z direction after cooling and lifting from the
plate. `Front_pull_shelf` reaches beneath concealed roofs above the finger rests
and pulls forward in negative print-Y. The selected `Rear_pull_shelf` supports
the switch aperture and pulls in positive print-Y. `Release_tabs` are thin bed tabs.
These are explicitly owned, disposable normal meshes, not installed wand parts.
Native automatic support is disabled on every object.

Working spaces containing a helper are reported as **obstructed until cleanup**.
No carrier or tab intrusion is accepted. A helper in an opening is accepted only
when its complete ordered solid and actual-bead withdrawal passes; cutting it
into imaginary fragments is never credited. Removal geometry does not measure
PETG bonding or hand force. Stop rather than lever against a thin finger rest.
The selected cleanup animation must match the final helper inventory and order.

## Verification and sources

- `holder45.py`, `roof45.py`: compose R44's carrier and construct the conventional
  cradle and bed tabs. The saddle-tip trim is retained only for flat diagnostics.
- `standing45.py`, `standing_relief45.py`: make the local standing-print lip
  repair, preserving its original structural targets and seated hardware surfaces.
- `standing_web45.py`, `web_qualification45.py`: generate and measure the
  replacement guard buttress against the independent original attachments and
  matching physical section stations, using actual native bead footprints.
- `standing_board45.py`: relieve the unused lower OP1 ledge without cutting
  raised seats, mating surfaces or structural reference volumes.
- `standing_comb45.py`: generate the removable finger-side comb without
  altering the permanent rounded finger-contact surfaces.
- `shelf45.py`: construct side-extracting roof supports and prove complete solid
  withdrawal. Their exported hashes and generation source bind the proof.
- `plate45.py`, `owner45.py`, `process45.py`, `saddle_bridge45.py`: generate the
  native layout, distinct ownership IDs and local process selectors.
- `geometry45.py`, `starts45.py`: early geometry/start diagnostics only.
- `audit45.py`, `route_audit45.py`, `release45.py`, `lateral45.py`: check all actual
  bead types, complete loading poses, original load-path witnesses and ordered
  whole-helper removal. The existing 0.90 minimum structural coverage is retained
  outside the six explicitly qualified replacement targets.
- `helper_starts45.py`: follow actual helper islands to grounded lower plastic.
- `roof_strokes45.py`: measure direct interior backing and native-order anchors,
  including leftover unsupported paths across successive moves. A long extrusion
  is not automatically a long unsupported flight. Legacy one-gap carrier backing
  is restricted to the existing outer-key floor seam and reported separately.
- `contact45.py`: measure actual roof contacts and accessible support feet.
- `bridge45.py`, `saddle_strokes45.py`, `bridge_moves45.py`: optional older
  diagnostics. The fixed flat-frame saddle coordinates do not establish
  coverage in the standing frame; `roof_strokes45.py` owns the complete
  selected-frame backing measurements.
- `slice45.py`: run one isolated headless native slice. Never send or start.
- `delivery45.py`: verify effective object recipes, real executable PETG startup,
  bed bounds, timelapse tower clearance and native file identity.
- `package45.py`: reuse the established R37/R44 print-only wrapper so Studio opens
  the checked G-code without moving its wipe tower or generating another slice.
  The same command regenerates the matching cleanup/assembly guide and evidence
  inventory from that audited file, keeping delivery and viewer together.
- `guide45.py`, `evidence45.py`: compose the versioned guide from the exact parts
  and retain source, mesh, native-archive and report hashes.

Use the repository geometry lease and verified SD scratch workflow. The native
slice expects macOS Bambu Studio and the project's Python CAD dependencies.
The default is the selected 270-degree standing orientation, finger-side comb
and switch-aperture prop. Other orientation flags are diagnostic recipes.
Run the commands serially against the same generated directory:

```sh
python plate45.py OUTPUT
python slice45.py OUTPUT/R45-Key-Carrier-layout.3mf OUTPUT/R45-candidate.gcode.3mf
python audit45.py OUTPUT/R45-candidate.gcode.3mf
python helper_starts45.py OUTPUT/R45-candidate.gcode.3mf
python roof_strokes45.py OUTPUT/R45-candidate.gcode.3mf
python contact45.py OUTPUT/R45-candidate.gcode.3mf
python delivery45.py OUTPUT/R45-candidate.gcode.3mf
python evidence45.py OUTPUT
```

Run `contact45.inspect` for every selected side-helper owner as well as the
external cradle before assembling the evidence inventory.

A successful core screen does not establish that every roof is backed or every
helper strand is grounded. Review those separate reports before selecting a
trial file. Reopen and re-slice the selected sliced 3MF once in fresh scratch,
then rerun the complete checks against its own newly emitted G-code. Retain the
actual native warnings. Seal only after the parent trial review passes, and
compare the packaged G-code bytes with the checked native archive.

Digital checks are distinct from physical fit, support removal force, bridge
sag, printed strength, fatigue and comfort. Bought board/connector envelopes
include estimates, and all those physical checks remain unverified until a
successful real trial. No diagnostic archive is a ready-file designation.

The selected file retains nine straight bridges up to 13.564 mm and five tiny
unbacked strokes measuring 0.407–0.620 mm. The latter can leave wisps or local
roughness; later plastic does not back them when they are first deposited.
These limitations are explicit in the trial assessment. Neither the native
warning nor the raw roof-screen flags have been hidden.
