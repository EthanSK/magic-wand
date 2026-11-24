---
name: model-user-requirements
description: Look up the user's requirements before changing any Magic Wand 3D model, coupon, printable kit, plate or mechanical assembly preview. Capture each new requirement, correction and fitted result when received, including during discussion and replacement prints.
---

# Model user requirements

Announce this skill and its purpose. The [catalog](catalog/) owns the mechanical requirements. Existing CAD, drawings and frozen dimensional contracts still own their dimensions. The [print-design skill](../magic-wand-print-design/SKILL.md) owns design and assembly procedures. Use the [printability audit](../printability-audit/SKILL.md) for the actual slice.

## Before changing a model

1. Identify the model family, revision, component and intended assembly. From the repository root run the lookup for the whole family. Read active requirements, fitted evidence, candidates and replaced directions in their labelled scopes. Select the affected interfaces, including assembly routes, the plate and the viewer. Repeat when resuming with missing context.
2. Compare the request with the last relevant user feedback, the actual revision sources and the last physically working reference. Follow the [private source map](user-preferences.md) for a disputed detail. A CAD clearance, a finished print and a successful fitted trial answer different questions.
3. Capture new direction immediately, before editing geometry, by updating the narrowest applicable catalog file and its private source pointer. Do this even when the request arrives in a voice chat or a planning-only discussion. The model owner receives the stable ID in any already-authorized handoff. A repeated requirement reuses its existing ID. A missing measurement stays uncertain.
4. In the work or delivery notes map each affected ID to its change, check or outstanding physical trial. Preserve the other applicable requirements. An agent proposal becomes active only after the user adopts it.

From the repository root:

```sh
req=.agents/skills/model-user-requirements/scripts/requirements.py
python3 "$req" show carbon-rod --history
python3 "$req" show carbon-rod/key-holder/guard
python3 "$req" show printed-loop/shard --history
```

The family lookup includes every component under that family. Each line gives its scope. A component lookup includes its ancestors, descendants and common Wand rules. Read sibling interfaces using the family view. The separate battery tray, integrated tray, Grove alternative, Shard, lattice study and frozen V20 are distinct assemblies. For a historical revision use its dated source and fitted evidence to establish what applied at that time. Today's catalog governs new changes.

## Capture and supersession

A JSON array at `catalog/<family>/<component>.json` owns that scope. Use `all.json` for genuine cross-family requirements. Each entry has a stable unique `id`, one `text` statement and a `status`. Use **active** for adopted direction, **candidate** for a suggestion, **evidence** for observed behaviour, and **superseded** for replaced instructions. Name the revision and the observation method in evidence. Mark a superseded entry in place and put its ID in the replacement's `supersedes` list. A narrower exception must preserve the parent rule wherever it still applies. Split the affected scope before retiring a shared rule. Keep the reason, original wording and dated source privately. Git preserves previous editions.

For example, the large-base request originally included tiny pins. The subsequent correction retained a broad base for the heavy carrier and specified smaller pads for tiny fittings. In [base.json](catalog/carbon-rod/base.json), `proportionate-bases` supersedes `large-bases-all`. Run the same lookup with and without `--history` to see the change. In [guard.json](catalog/carbon-rod/key-holder/guard.json), `guard-lower-blend` adds the earlier blend into the body. The existing contact protection still applies.

## Before a model commit

Stage the intended model changes and any catalog edits. Review the applicable IDs against the actual request, plate and physical feedback. Run the staged reconciliation and copy its final line into the commit message.

```sh
python3 "$req" validate
python3 "$req" reconcile guard-lower-blend,complete-key-kit
# For a change that introduces no new user direction:
python3 "$req" reconcile no-new
```

The local Git commit-msg hook checks the staged model paths, content, validated catalog and decision. Reconcile again if any of these changes. For a new checkout run `sh .agents/skills/model-user-requirements/scripts/install-hook.sh` once. With a pre-existing custom hook, chain the supplied check in the repository's existing hook. For a publication path that uses Git plumbing, run both `reconcile <decision> --base <parent-commit>` and `check-message <message-file> --base <parent-commit>` with the prepared publication index before publishing. Hooks cover ordinary Git commits on installations where they are enabled. Interpretation and timely capture of spoken requirements remain the handling agent's responsibility.

When introducing a model family, add its scoped records and path mapping to the checker, and exercise an actual commit in the fixture tests. Run the repository-wide privacy check. Publish only neutral requirements, revision-qualified observations and public-source references.

## Continuous improvement

Capture user corrections during the same task. When a verified repeat failure changes how requirements should be found or checked, refine the lookup or check and exercise the failing case. Keep original private evidence in the companion and technical lessons in the owning component.
