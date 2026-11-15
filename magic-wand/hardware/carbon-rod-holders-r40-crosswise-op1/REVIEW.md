# R40 frozen candidate review

This record covers the R40 crosswise OP1 candidate and the selected reopened archive. It is an assessment of the linked frozen files, not a physical acceptance record. `exports/readiness.json` binds the final sources, meshes, archive and reports by hash. Later edits require new affected checks.

Codex reviewed the source and regressions. Claude Opus 5.5 independently reviewed the actual source, sliced paths, support-removal evidence and animation data. Its verdict was: an experimental physical fit trial may proceed using the reopened archive; no CAD or toolpath blocker was identified. It did not perform browser checks. Codex verified the live Chrome and Codex views separately.

## Confirmed findings and dispositions

### 1. Fixed — Measure the real reinforcement attachments [Codex] [↗](</The web was present in both groups being intersected, so its entire volume could be counted as its own attachment. The corrected checks measure the original frame and guard against the added web separately.>)

**Severity / priority:** Medium — P2.

**Change required / fix effort:** Small, about 25–40 lines — holder40.py, audit40.py.

**What happened:** The former intersection was taken after the web had been added to both the fixed frame and the guards. That could conceal a weak attachment even while showing good deposition in the web itself.

**Example:** Static intersection reasoning showed that the common web would survive the intersection even without crediting the original guard-to-web interface. The corrected reopened audit measured the web-to-frame interface at a minimum nominal layer fraction of 0.9797 and the common outer guard-tail-to-web interface at 0.9564, above the unchanged 0.9 acceptance threshold. The three guards share that outer tail; these are not three independent outer load paths. Their separate rod-side joints were retained too.

**Fix:** Added new, separate attachment witnesses before unioning the web into the final solid; retained the existing deposited-bead measurement machinery. This is a new interface decomposition, not a claim of established pattern. Mechanical part records and STL hashes were unchanged by this audit fix. Physical bonding strength remains untested.

### 2. Fixed — Select the archive with current audit coverage [Claude Opus 5.5] [↗](</The initial and reopened packages contain different nozzle paths. Only the reopened package was checked with the final attachment witnesses, so the initial package must not look like the current print file.>)

**Severity / priority:** Medium — P2.

**Change required / fix effort:** Small, artifact names and about 10–20 documentation lines — README.md, readiness.json, REVIEW.md.

**What happened:** The initial archive had the simplest filename, but its older checker did not include the final attachment witnesses. Reopening produced different paths despite equivalent settings, recipes and modifier placements.

**Example:** The normalized paths differ, so a pass on one archive cannot be silently applied to the other. The reopened package hash starts `737aea906096`, and its own final audit has no failures across all seven parts.

**Fix:** Explicitly selected the reopened package, labelled the initial archive and its reports `superseded`, and bound the selected package to its own audit in the readiness record. This adds new delivery labels; it does not alter the nozzle paths or waive an audit failure.

### 3. Fixed — Describe the missing layout snapshot honestly [Claude Opus 5.5] [↗](</The reopen preparation reported a layout hash for a disposable file that was not retained. The saved editable layout is a different artifact and must not be described as that exact file.>)

**Severity / priority:** Low — P3.

**Change required / fix effort:** Small, about 10–20 metadata/documentation lines — readiness.json, README.md.

**What happened:** The retained editable layout and the disposable preparation used during reopening have different archive hashes. The original raw preparation snapshot cannot be recovered from its hash.

**Example:** The readiness record preserves both the retained layout hash and the reopen report's unretained-layout hash. All seven source mesh hashes and transforms match, and the self-contained reopened print package was independently checked.

**Fix:** Added an explicit provenance limitation and selected the actual audited package as the trial file. This is new traceability metadata; it does not claim the missing snapshot was recovered. Editing or re-slicing the reference layout requires a new audit.

## Printability decisions and physical boundary

- The short unbacked surface strips remain visible in `reopened-audit.json`; they were not reclassified as directly supported. The new left-web strip is 2.16 mm² at layer 17.6, extending across the existing shared tail. A nearby 0.60 mm² island starts on generated support. The other carrier and bracket partial strips also remain recorded. Codex and Opus accept these only as experimental trial features, based on continuous final geometry, actual emitted material, no floating-component findings and the audited local joints. This is not evidence of a sound physical bond or a sag-free surface. Inspect these regions before assembly and lightly flex the left junction; stop using a fractured or poorly bonded part.
- The 0.75 mm wall between the OP1 slot and upper key-clip relief has no dedicated material-region check. The general slice checks cover the part, but no separate strength claim is made for this narrow wall. Check it while seating the Choc switches; do not force a binding switch.
- Remove the labelled bed pads and generated supports before electronics. The spatial removal check reaches all 899 central and 273 outer support cells under its 0.4 mm fragment assumption. Actual removal has not been performed.
- OP1 board, connector and lead envelopes are photo-derived. Confirm the real board seats, its M1.6 screws hold, the plug enters from underneath and the lead bends without pulling a joint.
- Hinge squeeze clearance is nominally 0.209 mm; the PETG bending estimate is not a fatigue or layer-bond test. Adjust the separate M2 stop screw against the actual switch so it clicks and releases before the stops meet. The reference plunger is depressed about 0.014 mm at rest; check real release.
- The two upper keys move out 3.2 mm each. The outer lower seats, rod clips and hinge-axis height are unchanged. The released touch surface is about 0.52 mm higher. Real fit, strength, finish, fatigue, click feel and comfort remain unverified.

The selected seven-part plate estimates 7,783 seconds and 19.85 g. Executable startup reaches 245°C nozzle / 60°C bed with a temperature wait, gentle first three layers, Smooth timelapse and its wipe tower. The initial archive is retained only as superseded evidence. No physical print, heater or calibration command was sent as part of this preparation.

Confirmed finding attribution: Codex 1; Opus 2; shared 0. All three delivery/review findings above were addressed. The physical limits and missing raw layout snapshot remain explicitly disclosed rather than treated as recovered or physically verified.
