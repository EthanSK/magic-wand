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

## Proportionate final review

User-requested — 2026-11-08: improve speed; “whittle it down to useful required checks”. Remove duplicate work, retaining checks that catch blocked holes, weak joints and failed prints.

**Freeze and scope.** Settle geometry/settings before final review. Gather specifications once; send the relevant authored requests, constraints, changed features, exact artifacts and evidence, not the whole chat. Reuse coverage only when its hashes/dependencies still match: geometry, transforms, settings, relevant neighbours/toolpaths and checker. Documentation edits do not invalidate geometry evidence. Review changed features and dependencies; broaden for first deliveries, unknowns or physical failures.

**Required delivery checks**, batched through established checkers:

- Exact meshes, complete build list, orientations, printer/material and effective per-object settings.
- Actual first-layer attachment, floating starts, broad overhangs/bridges and thin features.
- Every working opening and complete loading/removal route against all actual bead types, including supports, interfaces, transition, brim, raft and CAD helpers. Reject empty/misplaced scans; cleanup-dependent spaces remain obstructed until cleanup.
- Likely snap points and complete load paths: minimum sections, joint overlap, surviving bead footprints, layer direction and spring freedom. Credit actual prior-layer plastic, not unprinted mesh. Helpers also need realised vertical/sideways gaps, backing and outward removal access.

**One independent Opus review.** Use invoke-claude with actual source, slice and visual access. Request actionable failures, evidence, missing coverage and a verdict. Assess existing measurements; run targeted probes for doubts rather than rebuilding a passing audit. Keep Codex's assessment independent. After fixes, re-review only invalidated coverage. Use Gemini only if stuck under existing authority.

**Finish once.** Prefer orientation/settings, then local repairs preserving bought interfaces and ergonomics. Re-slice changed geometry/settings and check actual paths even if STLs match. Reopen/re-slice the final archive once; preserve known GUI requirements, report unavailable coverage and continue independent work instead of looping on a broken UI. Keep one hash-bound per-part report linking selected views, measurements, finding dispositions and physical trials. Extra research, calculations, views or coupons need a specific unresolved question; no speculative simulations or duplicate reports. A complete-part trial may replace an unrepresentative coupon.

Use applicable sections of the [detailed checklist](references/review-checklist.md), not every historical investigation. Heavy queries follow [geometry ownership/allocation](references/geometry-budget.md): complete batches, one owned heavy job per host, bounded cleanup; no hard RAM cap or pressure gate. Preserve privacy, source/export checks, root check, commit/push and previous deliveries. No third-party sends or monitor restart without authorization.

## Completion boundary

A finished audit accounts for every printed part, functional space, support/bridge issue and plausible snap point; unresolved print risks block a ready-file claim. Keep physical fit, support removal, strength, fatigue and comfort explicitly unverified until real trials. Physical failure overrides a previous CAD or slicer pass.

Read [user-preferences.md](user-preferences.md) only when an unsettled choice needs the original private preference evidence.
