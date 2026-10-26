---
name: magic-wand-print-design
description: Revise the Magic Wand printable hardware, CAD, assembly preview or Bambu projects while preserving its helix, tapered silhouette, both handed grips and tested mechanical interfaces.
---

# Magic Wand print design

Read this skill before any wand CAD, print-layout or mechanical preview change. Follow the repository's magic-wand-dev skill and hardware lessons. Mechanical print versions are separate from firmware control versions.

## User design rules

- Preserve the original counter-wound helix / criss-cross pattern and recognisable wand silhouette. Reducing mass means thinner walls and hollow interiors; it does not authorize removing decoration or replacing the shape.
- The shaft body must taper continuously towards the head. No pinched waist that widens again, and no external bulb/collar added solely for a joint. Reinforce joints internally. The diamond naturally widens above its matching narrow neck.
- A complete Bambu project always contains **both left- and right-hand handles**. One shared set of shaft/head parts is acceptable, as in Print V2; state the contents clearly. A left-only file may be an explicitly labelled optional subset, never the complete delivery.
- Preserve purchased switch/socket holes and their alignment when reducing the surrounding insert. Recess compact mounts into the grip; use the purchased caps rather than adding visible printed squares or cap covers.
- Preserve board retention, upward USB access, battery solder/wire clearance, cable routes and handed button positions unless the user changes them.
- Keep prior models and delivered files unchanged. New revisions and supporting files go to Downloads; editable sources and regenerated exports are committed together under the repository rules.

## Before calling it final

Map each requested change to a source parameter or feature and a check. Compare old/new assembled views, not just the print plate. Check the core-radius profile for monotonic taper; explicitly check the helix is generated. Inspect both handed handles and count both in the actual 3MF build. Check new joints inside the chosen silhouette instead of making the silhouette fit arbitrary collars.

Run manifold, wire/board/USB, joint motion and lid capture checks as applicable. Slice in the actual PETG setup and compare like-for-like material estimates, including supports. Support contact blockers do not alone stop tree branches entering hollow passages; inspect sliced paths. Separate CAD clearance, slicer evidence and physical print acceptance. If the battery product is still unknown, retain its provisional status rather than inventing a fit.

## Maintain verified learnings

Before work, read the applicable stored lessons here and in magic-wand/LEARNINGS.md. During meaningful discoveries and before completion, update this user-maintained skill when a verified lesson changes future design decisions, without another reminder. Keep user preferences distinct from measured behaviour and hypotheses. Consolidate corrections, preserve unrelated guidance and avoid private transcripts, paths, receipts or credentials. Scope maintenance to this skill and its resources; no background learning process is created.

- 2026-10-26 — Explicit user correction: the V3 candidate lost the helix and used narrow spans between wider joint collars. Preserve the helix and a monotonic shaft silhouette while hollowing/thinning the interior. Source geometry and assembled preview establish the regression; neither the old nor replacement design is physically strength-verified.
- 2026-10-26 — Explicit project requirement: complete means both handed handles. Exporting a right-hand STL separately does not meet that requirement if the opened complete 3MF has only the left handle.
