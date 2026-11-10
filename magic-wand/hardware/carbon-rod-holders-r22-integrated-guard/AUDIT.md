# R22 audit

Skills used: printability-audit (layer growth, roots and necks, routes, snippable pads, slice checkpoints) and
magic-wand-print-design (rounded skin edges, arrow and 45° rules, matching keepers). All geometry jobs ran one at a
time through the guarded geometry runner. Bambu Studio ran through its command-line slicer.

## Checked digitally (exports/geometry-checks.json)

- **Exports.**
  - Every plate part's preparation STL matches its manifest hash, is watertight and is one body.
  - The R19 door, keeper and spacers, and the R20 XIAO body, are byte-identical to their source revisions.
  - Key holder export vs. source drift: 0.016 mm³.
  - The build list covers every plate part.
- **Runner growth.** Each runner is built layer by layer on the slicer grid. A layer only keeps material within 0.2 mm
  (45°) of the layer below, whether holder or runner.
  - Of 265.6 mm³ designed, 6.4 mm³ was trimmed. All of it is the first layers of each root, still inside the holder's
    underside.
- **Runner sections and roots.**
  - All six runners are continuous: no empty layer between their roots.
  - The narrowest free section is 1.4 mm (inscribed thickness, not a bounding box), 1.92 mm² in area.
  - Each runner bonds into the underside over 11 layers (2.2 mm) at both ends.
  - Runner R1 was moved behind key 4's front arrow window. At the earlier root position that window cut the runner off
    completely; the parent's joined-sections probe exposed it.
- **Seated parts.** The runners do not touch any switch (pins included), socket, maximum socket, tape-and-wire zone,
  terminal allowance, wire bus or the 4.2 mm rod corridor.
- **Routes with the stated solder allowance.** Zero rigid overlap on every pose:
  - keys 0 and 2: sideways slide 1.8 mm below the seat, then lift; 0.35 mm of extra drop is still clear;
  - key 1: straight up;
  - keys 3 and 4: dog-leg, 1 mm out, in at 2 mm below the seat. Pushed straight up they would overlap 2.9 and
    1.9 mm³, the inner solder allowance meeting the rod ring. This is inherited R16/R20 geometry.
- **Carve log.** Re-carving the finished holder with every working space removes less than 0.02 mm³ (asserted).
- **Fingertip probes.** R5 to R8 spheres straight up under every terminal, with and without runners. Table in the JSON;
  summary in the README.
- **Row-spacing table** for upper-row shifts of 0, 0.4, 0.8 and 1.0 mm. Only 0 mm passes the R16 cap-play screen.
- **Shoulder curve.** Steepest plan slope 0.979 (44.4°).
- **Battery.**
  - The R22 body leaves every R20 working space empty: cell bay, loading route, slots, wire exits and ring gaps.
  - Peak rigid overlap of each door dropped into the R20 and R22 bodies is recorded; seated overlap is zero for both
    doors. The lead-in removes 2.5 mm³.
- **XIAO.** Clearance map under the board in the R20 body (1,498 points). The keeper slides on with zero seated
  overlap; its tongue flexes past its tooth during the slide, peaking at 0.37 mm³.
- **Cable clip.**
  - The section shows a free bore radius of 3.5 mm. All 12 wire envelopes are inside it, each at least 0.45 mm from the
    plastic.
  - The slit opens 1.7 mm. The guide checks the last wire entering with the other eleven in their packed positions.
- **Assembly guide** (exports/assembly-guide.json, schema 2).
  - Modules: key, xiao, battery and cable. Every sample has a 12-number matrix for every actor.
  - The motions are the checked routes, with per-step overlaps against the exported meshes.
- **Slice.** All ten models deposit material on the single plate. The official A1 mini startup reaches 255 °C nozzle and
  70 °C bed before object paths. Smooth timelapse has a separate wipe tower.
  - Classic wall paths left the narrow guard cores partly hollow. The key holder uses Arachne to vary bead width.
    Across 126 sections of the six free spans, at least 93.9% of the section and 99.69% of the 0.30 mm inset core are
    covered. A small tapered relief clears the upper-left socket corner where the new beads first intruded.
  - Two local solid-fill regions back internal shell loops at print Z 1.4 and 17.2 mm. The original loops started over
    gaps in the infill even though the CAD was solid there. The actual paths now have backing in both regions.
    The inherited bay-roof spans still use their existing slow settings.
  - The final slice leaves all audited openings and loading routes clear after the labelled pads are snipped off. The
    checker found zero floating or missing starts. Cable pads have 0.59 mm or more printed clearance away from their ties.
  - Reopening and slicing again with isolated Studio settings preserves the wall override, print settings, slow zones
    and solid-fill regions.
    The changed toolpaths pass the same opening, start, pad and beam checks.
  - See [settings and commands](exports/R22-A1-mini-PETG-print-checks.json), [deposited paths](exports/slice-clearances.json)
    and [reopen checks](exports/roundtrip-checks.json).

## Not established (physical trial needed)

- Real solder blobs, wire gauge and insulation diameter. 1.5 mm insulation and R20's solder allowances are stated
  assumptions.
- Whether sliding a pre-soldered socket in sideways is comfortable, and whether the tape can be pressed down between
  the runners.
- Finger comfort, and whether a real fingertip reaches the inner terminals.
- Purchased keycap size and play. The row spacing stays at 17.8 mm until the caps are measured.
- Door snap force with either door, and whether the shallower trial tooth still holds in use.
- Underside solder height on the XIAO, and whether the keeper slides over the board as soldered.
- Clip grip on the rod and wire retention in the 1.7 mm slit. The assembly guide uses a free rod end for installation.
- Runner strength. Finger load bends each runner across its layer lines; the stated-assumption fixed–fixed screen
  gives roughly 4–10 N at midspan per runner (span 18–25 mm, I ≈ 0.37 mm⁴, 25–35 MPa interlayer). Not tested.
- Runner stability while printing. Each runner is a free 1.6 × 1.4 mm island for about 20 mm of print height before
  it rejoins the holder. The checked backing and bead coverage leave physical movement under the nozzle unmeasured.
- PETG sag on runner roots and bay roofs. Inspect the slow bands after printing.
