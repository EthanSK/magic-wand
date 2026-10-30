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

1. Read [AGENTS.md](../../../magic-wand/AGENTS.md), the relevant [LEARNINGS.md](../../../magic-wand/LEARNINGS.md)
   sections and [SOURCES.md](../../../magic-wand/SOURCES.md). Inspect the actual source and Git state;
   preserve unrelated changes and identify the installed version before diagnosing hardware.
2. Use [BUILDING.md](../../../magic-wand/BUILDING.md) for the real build and connection architecture.
   This public checkout publishes sources; do not connect to, flash or restart hardware here.
   Authorized hardware changes run from the established private installation workflow.
3. Keep one Bluetooth owner: the installed receiver. Prefer diagnostics through its existing
   connection; opening a second connection can make a working device appear disconnected.
   Prepare and check updates before the short swap, preserving calibration and rollback.
   Before any private installation, follow the Agent Flow recording/processing gate in the
   shared development-workflow local-installation reference. Do not restart while Ethan is
   using Agent Flow. Check its authoritative idle probe automatically; do not ask Ethan
   to declare idle when the app can report it. Recheck after the warning and leave Agent
   Flow itself running. A recording=false file alone is not the authoritative probe.
   Table-rest detection must not stop dictation or dismiss an explicitly open HUD.
   For failed startup, missing callbacks or memory errors, first read the recovery lessons in
   `LEARNINGS.md` ("A partial live patch must not look ready" and "UART source echo is not a
   runtime response"). A matching runtime version is not proof of intact registered handlers.
   Prefer clearing interrupted console input and checking the actual callbacks before a full
   upload over a partial patch. Preserve saved code and establish a recovery path before `load()`.
   Report a receiver restart, a sent Puck reload, an observed device restart and restored cursor
   movement as separate facts; do not call the Puck restarted from a sent command alone.
   User-requested recovery guidance — 2026-10-24.
4. Do not add intentional movement latency without Ethan's fresh explicit confirmation.
   Sensor sampling, delivered update rate and end-to-end latency are different measurements.
5. For wand CAD, mechanical previews or print projects, first read [magic-wand-print-design](../magic-wand-print-design/SKILL.md). Preserve the helix, monotonic shaft taper and both handed handles in the actual complete 3MF. For prototype changes, read [the prototype policy](../../../magic-wand/prototypes/README.md).
   Preserve the V1 baseline and feature flags. New hardware needs its own profile; do not
   silently redefine the original button positions, gestures, gains or colours.
6. Verify relevant source tests and the installed version, then distinguish hardware evidence
   from synthetic checks and Ethan's physical acceptance. Update `wand.json` with control,
   version or status changes. Import through `scripts/import_private.py`; do not publish
   private receipts, settings or logs. Regenerate with `python3 scripts/build.py`.
7. Run `npm run check` from the repository root for every component and the privacy scan; perform the applicable browser and real-device checks from AGENTS.
   Commit completed changes regularly. For an authorized publication, verify the remote
   commit, CI and deployed assets rather than stopping at a local commit.

## Additive workflow profiles

Ethan: “we need different profiles for what kind of a computer user you are”; Sunny's additions must be “additive” and “slot in” without breaking existing functionality. Keep new user/workflow presets isolated to the selected profile and compose through existing controls. Preserve the coder profile, other profiles and physical mouse behaviour; verify those alongside the new profile before committing. Do not introduce a speculative profile architecture merely to satisfy this rule. User-requested — 2026-10-30.

## Completion

Ethan: “It doesn't count as working if you're doing hacks like temporary code
splits. You either have installed the full firmware properly onto the wand, or
you haven't.” Installation must persist the complete required device program
and startup path on the wand so removing and reinserting its battery does not
require reinstalling code. Temporary RAM patches are diagnostic or staging work,
not a completed installation. Verify saved bytes and a clean startup that loads
them without the receiver re-uploading missing firmware; check calibration and
the requested controls afterward. Report any unverified physical power-cycle
check explicitly. User-requested — 2026-10-24.

Ethan: “Make sure this is always checked and there's a cleanup rule and it's
properly managed and maintained.” Before a firmware install, inspect the actual
free storage and saved versions. Keep rollback copies on the Mac; remove obsolete
device images only after their bytes are backed up and the active startup path
is understood. Verify enough space for the complete replacement. Never compact
flash while running functions still reference its old locations; enter a checked
maintenance state first, then verify the saved image after compaction and restart.
The Puck's small storage is not a release archive. User-requested — 2026-10-24.

Keep all three LEDs lit throughout a firmware installation, including after an
interpreter reset while saved files are being written and verified. Restore the
ordinary mode indication only when the complete saved program is running.
User-requested — 2026-10-24.

Report what is installed, what is committed/published, what was tested, and any real remaining
physical check. Keep prototype snapshots reproducible and the working tree free of scratch.
