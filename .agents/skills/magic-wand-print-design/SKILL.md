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

Run manifold, wire/board/USB, joint motion and lid capture checks as applicable. Slice in the actual PETG setup and compare like-for-like material estimates, including supports. Support contact blockers do not alone stop tree branches or descending normal-support columns entering hollow passages; block their landing-source regions where needed and inspect sliced paths. Separate CAD clearance, slicer evidence and physical print acceptance. If the battery product is still unknown, retain its provisional status rather than inventing a fit.

## Maintain verified learnings

Before work, read the applicable stored lessons here and in magic-wand/LEARNINGS.md. During meaningful discoveries and before completion, update this user-maintained skill when a verified lesson changes future design decisions, without another reminder. Keep user preferences distinct from measured behaviour and hypotheses. Consolidate corrections, preserve unrelated guidance and avoid private transcripts, paths, receipts or credentials. Scope maintenance to this skill and its resources; no background learning process is created.

- 2026-10-26 — Explicit user correction: the V3 candidate lost the helix and used narrow spans between wider joint collars. Preserve the helix and a monotonic shaft silhouette while hollowing/thinning the interior. Source geometry and assembled preview establish the regression; neither the old nor replacement design is physically strength-verified.
- 2026-10-26 — Explicit project requirement: complete means both handed handles. Exporting a right-hand STL separately does not meet that requirement if the opened complete 3MF has only the left handle.

- 2026-10-26 — Explicit button-mount correction: use a small rounded thin plate that slides down from above directly into integral wand guides. No bulky cassette, separate printed cap/keeper or glue. Keep the bought keycap distinct from printed parts. Back the socket recess and use a small cable outlet rather than a generic large opening into the hollow grip. Check the full insertion path in both hands and past neighbouring buttons; an assembled pose alone is insufficient.
- 2026-10-26 — Mass comparisons must contain exactly one complete wand per row (one handed grip plus matching shared parts). Report printed-parts mass separately from support/brim and keep original print settings distinct from a matched-settings comparison.

- 2026-10-26 — Explicit handle correction: keep the mug loop at the butt with removable-cap clearance, controls above and clear of it, and greater outward projection in the upper/thumb region than in the lower return. The user corrected the earlier sloping-arm interpretation: keep loop orientation and button angles unchanged. Vent holes must reach the inner hand-contact face, not only the broad side faces. Check both hands and the whole assembled relationship; isolated button coordinates are insufficient. CAD passage probes and sampled sliced paths establish clearance, not physical comfort or cooling.

- 2026-10-26 — Current loop requirement: detachable without unplugging wiring, using the same mounts on both handed stems. Check the entire released slide past caps, positive radial/lift capture and a small print coupon. A geometric spring-deflection envelope does not establish PETG force or fatigue life. The user rejected the open-braid interpretation: keep the supporting tube and entire raised helix strips continuous. Cut independent elongated slots between those strips, preserving longitudinal lands and local solid collars/hardware protection. Do not turn the helix itself into holes. Use elongated loop slots instead of little bores. Inspect sliced paths and actual single-wand extrusion mass.
