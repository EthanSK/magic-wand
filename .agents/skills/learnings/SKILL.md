---
name: learnings
description: Use before Magic Wand bug fixes, regressions or fragile hardware and receiver changes, and after work yields a durable verified lesson.
---

# Magic Wand repository learnings

## Continuous improvement

Preserve Ethan's explicit project rules as requested in `AGENTS.md`. Improve this skill when
verified experience reveals a reusable decision or safeguard, keeping it concise and retaining
unrelated guidance. Put detailed evidence in `LEARNINGS.md`, not a growing task recap here.
Distinguish user-requested changes from agent-discovered lessons; mark the latter with a date
and evidence. Do not preserve guesses, private paths, logs or credentials in public files.

## Skill usage announcement

Tell Ethan which skill is being used and briefly why before taking skill-directed action.
Reuse an announcement for the same ongoing task; do not repeat it at every command.

## Workflow

- Read relevant sections of [LEARNINGS.md](../../../magic-wand/LEARNINGS.md) before changing fragile
  behaviour. Follow [AGENTS.md](../../../magic-wand/AGENTS.md) and inspect current code and live evidence;
  an old incident description does not establish the current installed state.
- Save reusable, verified technical lessons in `LEARNINGS.md` in the same task. Include the
  symptom, established cause, decision that prevents recurrence, and verification boundary.
- Merge with the existing relevant section instead of repeating the same lesson. Keep source
  test results, live telemetry and user physical acceptance distinct.
- Durable user rules belong in `AGENTS.md` or the relevant skill, not in incident notes.
  Current controls and values belong in `wand.json`; prototype recovery policy belongs in
  `prototypes/README.md`. Preserve the no-unapproved-movement-delay rule.
- Keep transient PIDs, device addresses, local paths, raw logs and private conversations out
  of public lessons. Save necessary diagnostic artifacts privately.

## Completion

Verify the edited guidance agrees with current source and evidence, check relative links,
run the applicable repository checks, and include the intended guidance in the next commit.
