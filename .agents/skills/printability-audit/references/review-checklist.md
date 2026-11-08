# Final printability and strength review

Use the relevant sections when a changed feature, uncertainty or physical failure needs deeper checking. The core delivery checks and evidence-reuse rules live in [SKILL.md](../SKILL.md); do not repeat an unchanged historical investigation just because it appears here. The aim is a model that can actually be printed, cleaned and assembled with minimal design changes. A valid mesh and a slicer success message do not establish that result.

## Establish the actual delivery

- Identify the latest intended revision and exact project, source, normal STLs, transforms and settings. Preserve delivered archives. Inspect the final exported meshes and full build list, not a similar source solid or an older screenshot.
- List every printed part and every working opening: switch/keycap/socket seats, pins and solder, sliding rod bores and clip gaps, USB/wires, battery entry/reserve, gates, grooves, locks and small holes. Record what must fit, its complete insertion/removal path and the evidence for its size. Keep unknown bought-part dimensions explicit.
- Self-improved — 2026-11-06: rectangular cap dimensions must be mapped to the mounted switch's stem axis before using them for spacing. The R15 independent review found that a plausible 90-degree reference rotation changed the nominal sideways gap from 1.2 to 0.3 mm. Use bought-part drawings or a mounted measurement; while orientation is unknown, screen both orientations and retain a pre-print measurement gate. Do not lower a clearance threshold merely to match the chosen layout.
- Use the real printer/nozzle/material/layer/wall/infill/support/brim recipe. Read effective per-object overrides as well as global settings. Regenerate and re-slice after relevant changes; check that reopening the portable project retains them.

## Examine the real slice

- Scan every working opening through its full depth against actual model, support, support-interface, brim and raft bead footprints. Do not silently exclude support or brim and then report an opening clear. Include access paths and clip relief, not only a seated hardware volume. Check neighbouring extrusion exists so empty or mis-transformed samples cannot produce a false pass.
- Inspect layer cross-sections and relevant toolpath views visually. Check first-layer contact, isolated starts, overhangs, bridge direction/span/anchors, thin walls, gaps between rails and missing small features. Review broad partly unsupported areas even when no isolated island is reported.
- For each support touching a functional region, establish an exterior removal route and realistic tool access without loading a thin clip or prying on a key seat. “Removable” is a finding to justify, not a default. Prefer keeping support out of fit surfaces and narrow/curved bores. If clearance depends on removal, label it as support-obstructed until cleanup, describe the route and keep physical removal unverified. Never count that as an unobstructed print.
- A support blocker defines a generation rule, not an empty toolpath. Descending columns and branches can still pass through a hole from a contact source above it. Inspect the resulting paths and adjust source regions/orientation or add local printable geometry where needed.
- Compare practical orientations and targeted support settings before altering the design. Prefer local fillets, gussets, short supported bridges, ribs or clearly labelled accessible breakaway helpers when needed. Do not solve printability by changing key positions, rod size, slide fits, purchased interfaces, silhouette or agreed ergonomics without the user's decision.

## Examine likely snap points

- Inspect every thin rail, clip arm, gate wedge, socket floor, connector root, long lever and joint. Measure actual minimum sections and joint overlap in the final STL and count the extrusion lines that survive slicing. A single connected body is not evidence of an adequate load path.
- Consider ordinary assembly, support removal, sliding on the rod, button pressing, battery loading, accidental snags and repeated flexing. Check unsupported levers, sharp inside corners, notches and small bonded areas. Trace loads into neighbouring material rather than checking a part alone.
- Compare layer direction with those loads. A change that clears a hole may weaken a spring across layers or leave a tall narrow print unstable. Preserve intended flexible arms and interference while reinforcing fixed roots and adding smooth transitions outside functional keepouts.
- Scan the complete per-layer section between each loaded body and its anchors after an orientation change. Identify the actual narrowest connection and compare printed material there, including each intended reinforcing rail. A thick joint elsewhere or a collection of convenient point probes does not clear a thin interlayer bottleneck.
- Use calculations only with stated loads and sourced material/print assumptions; do not invent a breaking force or call a geometry check a strength simulation. Include small representative fit/flex/bridge coupons where the uncertainty matters. Printed force, retention, fatigue, toughness and comfort require real tests.

Self-improved — 2026-11-06: a track count or a median-width bead envelope does not measure filled material. For a questionable loaded neck, inspect each track's feature and actual width and the union of its footprints across the section; report internal unfilled intervals explicitly. R15's targeted four-ray check distinguished two separated walls from variable-width gap fill without claiming breaking force.

## Independent review, repair and handoff

Use the current `invoke-claude` workflow to give Opus the authored requirements, exact current artifacts, settings, visual slice evidence and measured checks. Ask for its own assessment of holes, support removal and weakness with minimal design changes; keep Codex's initial conclusion separate. Require actual file inspection and distinguish source-only review from review of a final slice. If stuck, use Gemini through the council when available under the user's requested boundary. Report unavailable coverage honestly.

Account for each finding, fix in-scope failures and repeat the affected final slice/visual/strength checks. Have Opus review the final affected artifacts when later changes invalidate its earlier view. No obsolete review or successful re-slice closes an unresolved opening or snap risk.

Retain a concise reproducible report with exact hashes, per-part opening/support/bridge/section evidence, review disposition, changes versus the previous revision and remaining physical tests. Keep private prompts and model-run transcripts outside the public repository. Follow normal source/CAD generation, privacy, check, commit and push rules. Deliver the checked replacement and identify superseded files; do not send it to another person or restart a monitor without authorization.


## Why holes close or shrink

For an unresolved blocked-hole or size problem, research the applicable mechanism rather than attributing everything to support. Reuse settled, sourced explanations; this is not a fresh web-research requirement for every delivery. Check actual bead paths and physical evidence separately:

- Slicer supports, interfaces or branches, including columns descending from a different source above the opening.
- Bridge/arch sag at horizontal roofs and the top edge of an opening in an upright wall. Toolpaths cannot predict the real droop.
- First-layer squish, elephant foot and brim/raft entering a C-shaped opening.
- Small-hole perimeter effects, dimensional shrinkage and the chosen hole compensation. Bracket bore sizes in coupons printed in the final orientation.
- Aligned seams, blobs, flow errors and PETG stringing in bores, narrow slits and routes. Identify their locations and inspect the physical test.
- Supports or CAD helpers fusing across small realised gaps; narrow slits closed by gap fill.
- Mesh/topology/export errors, incorrectly typed modifiers and stale project geometry or settings.

## Explicit CAD print helpers

Self-improved — 2026-11-05: the R13 actual-layer checks exposed false backing from nearby beads, a two-layer contact gap, and helpers that resumed too close above a nominal contact. The saved layer-audit regression cases and actual helper-separation scans exercise these failure modes. Keep the following checks when explicit CAD aids are used.

Verify actual vertical gaps on the final layer grid. Credit support only from bead centres directly beneath the feature, never merely within a sideways search radius. Derive normal-layer backing from actual bead footprints, clipped to the mesh only to locate the part; unprinted mesh slivers and empty infill spaces are not supporting plastic. Measure the true gap; a nominal 0.24 mm space can become two empty 0.2 mm layers. Snap intended contact tops to the actual layer grid and verify the resulting G-code.

State partial backing explicitly. A count of lower beads and their qualifying gap does not show that the whole broad area is supported or measure the minimum separation. Inspect the residual span and anchors, and measure the covered area when needed to justify the decision; keep the adjacent-layer clearance check separate.

Self-improved — 2026-11-06: the R15 independent toolpath review identified a 5.15 mm free floor tongue behind a partly backed first layer, and contact faces exactly on slicing mid-planes. Record the longest unsupported span, distance to real plastic below, and how many layers an island remains separate before joining the frame; an area percentage alone understates nozzle-catch and detachment risks. Avoid relying on a boundary face's inclusion/exclusion for helper release. Check the final empty layers after re-slicing, and state any slicer-version or placement dependence explicitly.

Measure sideways clearance between actual helper and part beads, especially beside thin struts, floors and springs. Establish a tested or explicitly provisional contact recipe. Give every helper an outward removal route: split trapped axial shells, avoid long close runs beside delicate parts, and brace tall thin starters. Identify any deliberate cut tabs, bond them only to substantial fixed areas away from fit surfaces, and include them in every working-space scan.

Apply a close contact exception only below its named first face; a different helper passing above that face must regain full clearance. Compare an exported float32 mesh with generously containing contact regions rather than subtracting an almost-identical analytical solid: microscopic residual films can erase legitimate backing when expanded. Limit whole-helper layer growth, including partial shoulders, rather than accepting an entire new cantilever because one edge is connected.

## Decisions, coupons and release evidence

Keep a per-part decision table for every broad unbacked area/bridge above the audit's stated threshold and every likely snap point: measured size/section, surviving bead paths, load case, layer direction, backing/removal route, decision and necessary physical test. No unexplained area, unreviewed slicer warning or missing row can support a ready-file claim. Distinguish a bounded coupon experiment from full-set readiness.

Read orientation instructions in their actual context before applying them to a different assembly. Check a real conflict with the user instead of silently violating it or inventing one. A broad-face rule for a separate plate does not automatically settle every axis of a joined multi-axis carrier.

Use coupons without accidental crop slivers, resolve their own warnings, and cover the riskiest features: tall prints, upper loaded joints, guide slots, gates, thin struts and helper release. A full-size lightweight part can be the appropriate trial when cropping removes its real load path. Include bore brackets in the final orientation when fit is uncertain.

Gate release on one consistent source/export/project/checker/helper receipt set. Reopen and re-slice embedded settings and recheck actual paths. Deliver only a clearly identified test-first project and source meshes labelled as requiring preparation; do not present unsupported bare STLs as independently printable files.

Self-improved — 2026-11-05: the independent R13 review and direct file checks found a 2.76 mm² upper-key connection missed by point probes, an unprinted battery-bar sliver credited as backing, a stale coupon image receipt, and process-override registration removed by CLI export. Cover the complete load path, actual prior plastic, every delivered project's images and the exported archive's registered settings. The saved eight layer regressions and per-project integration guards exercise these boundaries; geometric improvements still require real strength and cleanup trials.
