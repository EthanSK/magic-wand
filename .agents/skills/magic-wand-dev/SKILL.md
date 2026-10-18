---
name: magic-wand-dev
description: Use for Magic Wand firmware, native receiver, HUD or speech integration, installation, publication, and hardware-prototype changes. Keeps the installed device and published sources distinct.
---

# Magic Wand development

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

1. Read [AGENTS.md](../../../AGENTS.md), the relevant [LEARNINGS.md](../../../LEARNINGS.md)
   sections and [SOURCES.md](../../../SOURCES.md). Inspect the actual source and Git state;
   preserve unrelated changes and identify the installed version before diagnosing hardware.
2. Use [BUILDING.md](../../../BUILDING.md) for the real build and connection architecture.
   This public checkout publishes sources; do not connect to, flash or restart hardware here.
   Authorized hardware changes run from the established private installation workflow.
3. Keep one Bluetooth owner: the installed receiver. Prefer diagnostics through its existing
   connection; opening a second connection can make a working device appear disconnected.
   Prepare and check updates before the short swap, preserving calibration and rollback.
   Before any private installation, follow the Agent Flow recording/processing gate in the
   shared development-workflow local-installation reference. Do not restart while Ethan is
   using Agent Flow; recording=false alone does not prove transcription/delivery is idle.
   Table-rest detection must not stop dictation or dismiss an explicitly open HUD.
4. Do not add intentional movement latency without Ethan's fresh explicit confirmation.
   Sensor sampling, delivered update rate and end-to-end latency are different measurements.
5. For prototype changes, read [the prototype policy](../../../prototypes/README.md).
   Preserve the V1 baseline and feature flags. New hardware needs its own profile; do not
   silently redefine the original button positions, gestures, gains or colours.
6. Verify relevant source tests and the installed version, then distinguish hardware evidence
   from synthetic checks and Ethan's physical acceptance. Update `wand.json` with control,
   version or status changes. Import through `scripts/import_private.py`; do not publish
   private receipts, settings or logs. Regenerate with `python3 scripts/build.py`.
7. Run `npm run check`; perform the applicable browser and real-device checks from AGENTS.
   Commit completed changes regularly. For an authorized publication, verify the remote
   commit, CI and deployed assets rather than stopping at a local commit.

## Completion

Report what is installed, what is committed/published, what was tested, and any real remaining
physical check. Keep prototype snapshots reproducible and the working tree free of scratch.
