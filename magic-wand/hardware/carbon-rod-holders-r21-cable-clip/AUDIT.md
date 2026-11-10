# R21 cable clip — digital audit

## Verdict and physical boundary

The frozen clip is digitally checked for a controlled prototype print. No
confirmed geometric print defect remains in the delivered archive. It has not
been printed, sent, or reopened in the GUI. Real wire fit, insertion force,
rod grip, fatigue, adhesion and pad release remain unverified. The 4 mm cable
bore is a provisional loose guide, not a bought-wire measurement.

R20 is unchanged. This standalone clip belongs to a later print after the
previous plate has cooled and been cleared. Slide the rod loop on from a free
rod end only; do not force its narrow opening over the full rod.

## Exact delivery

- Prepared slice SHA-256: `813a0678712992297505ba08d5cc3ccca064f3ac55915b2789d300a5baeb93b4`.
- Clip STL SHA-256: `cee64ade58125cfeac4e2656f975eac9e7f61036540e70d7fe6a84b9cf90a0ec`.
- Pad STL SHA-256: `541d585b0a96d2785fe083a5bd11f2af03d9e01f57366de9006284a6cc7cb409`.
- Reloaded slice SHA-256: `e23a3a29f986687e05c757b37569f75c8242c5b7dace806840bdbdff330385ea`.
- CAD solid mass: 0.130 g at 1.27 g/cm3.
- Slicer estimate: 8 minutes 47 seconds / 0.333 g including removable pads and
  the separate Smooth-timelapse tower; installed clip mass excludes both.

The editable CAD, normal STLs, prepared layout, sliced archive and hash-bound
reports are all retained here. Reproduce through `clip21.py`, `project21.py`,
`check21.py` and `roundtrip21.py` with verified external scratch as documented.

## Actual toolpaths

- A1 mini / 0.4 mm, Generic PETG, textured PEI, 0.2 mm layers, three walls and
  0.6 mm Normal lift. Official included startup/end/layer/timelapse templates.
- Executable commands wait unconditionally for 255°C nozzle and 70°C bed before
  the first non-custom extrusion feature, including the earlier tower. Final
  heater targets are zero. Metadata alone is not credited.
- All 12 real layers contain one connected bead footprint. Minimum coverage of
  the intended section is 95.7%; the shared waist prints every layer.
- Both loops retain at least two sampled radial track clusters at both side
  quadrants on every layer. These samples and connected whole-layer footprints
  are print-continuity screens, not measured spring force or fatigue.
- Every real layer clears the 7.7 mm rod-core, 3.7 mm cable-core, 0.7 mm rod-entry
  and 0.6 mm cable-entry witnesses inside the nominal bores/slits. No automatic
  support, brim or skirt enters these spaces. No floating/missing starts or
  partly backed regions were found.
- The two pads print through both bed layers, with complete tie-centre coverage.
  Minimum actual pad-to-arm gap away from the ties is
  0.586 mm, exceeding the existing 0.35 mm screen.
- The cutter corridor at source Y ±3.7 mm intersects under 0.001 mm3 of permanent
  plastic. Snip rather than peel. A short bed-layer stub remains near the arm
  root; trim it without cutting into the arm. Physical cleanup is not proven.
- All extrusion belongs to the clip, its pads or the tower. The tower is inside
  the bed and 68.03 mm clear of clip/pad bounds.
- Exact exported triangles, current source geometry and the archived pad mesh
  match. Reopening/re-slicing preserves checked settings and normalised G-code;
  the complete new bead audit passes again. This is CLI reload evidence.

Canonical details: [manifest](exports/manifest.json),
[recipe/commands](exports/print-checks.json),
[actual beads](exports/slice-checks.json),
[reload](exports/roundtrip-checks.json) and
[reloaded beads](exports/roundtrip-slice-checks.json).

## Independent review and dispositions

Claude Opus 5.5 inspected the source, reports and actual path image read-only;
its verdict accepted controlled prototype printing. Codex independently checked
source, exact archive identity, path image and the affected tests. No Fable call
was used for this clip.

1. **Fixed — missing pad-to-arm bead-gap coverage [Claude Opus 5.5].** Added the
   established R19/R20 gap screen; both pad layers pass. Geometry and sliced
   commands were unchanged. Codex ran the expanded audit on the delivered and
   reloaded archive; this follow-up was not another Opus invocation.
2. **Fixed — ambiguous rod installation [Claude Opus 5.5].** Instructions now
   require a rod-end slide and explain access past adjacent holders. Cleanup
   wording also identifies the short outside tie stub and protects the arm.

Review split for this clip: Codex 0; Opus 2; shared 0 confirmed coverage/document
findings. Physical unknowns are not counted as demonstrated geometry failures.
Five command regressions reject wrong/conditional temperature waits and later
cold targets; two delivery regressions bind mesh, slice, image and reload
receipts. Earlier R20 delivery tests still pass.
