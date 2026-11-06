---
name: printability-audit
description: Before finishing any 3D model, coupon or print project in this repository, review actual sliced holes, supports, removal access and likely snap points with Opus. Also use after physical print failures. Keep the design and bought-part interfaces intact.
---

# Printability audit

Make sure the model can be printed, cleaned and assembled, while changing the design as little as possible. This is a project skill shared by the components, not a global copy or a licence to apply Wand geometry to Control Stones.

## Continuous improvement

Preserve explicit user requirements during the same task. Keep verified reusable checks and failure prevention here or in the owning component's LEARNINGS.md; distinguish measured causes from hypotheses and physical acceptance from CAD or slicing results. Refine existing guidance instead of accumulating incident recaps, and keep conditional detail in the linked checklist. Preserve unrelated edits; exclude private prompts, paths, logs and credentials. Mark agent-discovered material additions Self-improved with date, reason and evidence; do not label user-requested rules that way. Validate changed skills and exercise affected checks before finishing.

## Skill usage announcement

Tell Ethan this skill is active and briefly why before its first use, following response-preferences. Reuse that announcement for the ongoing audit.

## User requirements

User-requested — 2026-11-05: every time you finish a 3D model, fully analyse with Opus if it will print well because of the support structure, and what you can fix or add while changing the design as little as possible. Check every time that nothing is too weak and can snap easily. Check holes in general, including keycap/socket areas and holes sliding over the rod. Ask Gemini through the council if stuck; that does not require an automatic council pass for every model.

## Final review

Before any CAD, exporter or geometry-query command, follow [allocation-efficient geometry work](references/geometry-budget.md): complete batched queries and one owned heavy job per host, with finite command cleanup. This includes reviewers' one-off probes. User-corrected — 2026-11-06: fix the actual excessive allocation or leak in our code; do not add hard RAM limits or block work based on host memory pressure. A tool timeout must not leave expensive background work running.

1. Read the owning component's instructions, design requirements and relevant lessons, then [the review checklist](references/review-checklist.md). Inspect the exact deliverable revision, final exported normal meshes, every actual build instance, orientation and effective per-object print settings. Preserve previous deliveries.
2. List every functional opening, fit/contact face and complete insertion/removal route. Scan actual model, support, interface, transition, brim and raft bead footprints through the full depth. Default to failure when any obstructs a working space. An explicitly justified cleanup exception is still support-obstructed until removal, never an unobstructed pass. Check adjacent model paths and source/export hashes to reject empty or misplaced scans. Research why holes close or shrink using the mechanism checklist, including sag, first-layer effects, seams, stringing, gap fill and dimensional compensation.
3. Examine actual layer/toolpath views: first-layer contact and stability, floating starts, broad partial overhangs, bridge span/direction/anchors, missing or single-bead features and dimensional effects. Derive backing from actual previous-layer bead footprints, never unprinted mesh geometry. Inspect source contact regions and the whole support-removal route; a support blocker or a slicer success message alone proves neither.
4. Check likely snap points in every part: minimum actual sections and printed bead counts, joint overlap and load paths, sharp corners, notches, cantilevers, flexing arms, assembly/removal forces and layer direction. After changing orientation, scan the intervening layer sections between loaded bodies and their anchors; hand-picked probes can miss the only connecting strips. Reinforce weak fixed areas locally without immobilising intended springs or filling keepouts. Geometry cannot establish printed breaking force or fatigue life.
5. Use invoke-claude for an independent Opus review of these exact artifacts and requirements. Give actual read access to source, slice evidence and visual views. Keep Codex's view separate, resolve disagreements by measurement, and re-review affected final artifacts after changes. State unavailable coverage accurately. Use Gemini through the council if stuck and available.
6. Fix in order of least design disturbance: orientation and targeted print settings, then local fillets/ribs/gussets or accessible labelled print helpers. Re-slice and repeat affected hole, support, bridge, strength and assembly checks. A requested support repair does not authorize changing agreed ergonomics, rod dimensions or bought interfaces.
7. Save a reproducible per-part report with hashes, check coverage, review findings/disposition, minimal changes, support-removal notes and a representative coupon-first plan. Bind every project's images and receipts to its exact final files. Check settings protection in the actual delivered export, not only the layout; follow known GUI round-trip requirements and state unavailable GUI coverage. Require consistent source/project/checker/helper receipts, directly-beneath backing, actual layer-grid gaps, measured sideways clearance, helper exits and explicit decisions for every broad overhang and weak point before a ready-file claim. Follow the repository's privacy, source-generation, root check, commit and push rules before delivering the checked replacement. Do not message a third party or restart monitoring without authorization.

## Completion boundary

A finished audit accounts for every printed part, functional space, support/bridge issue and plausible snap point; unresolved print risks block a ready-file claim. Keep physical fit, support removal, strength, fatigue and comfort explicitly unverified until real trials. Physical failure overrides a previous CAD or slicer pass.

Read [user-preferences.md](user-preferences.md) only when an unsettled choice needs the original private preference evidence.
