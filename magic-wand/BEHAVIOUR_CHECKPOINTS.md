# Behaviour checkpoints

This is the shared register of versions Ethan has explicitly liked. Append a
checkpoint when he confirms a useful baseline; keep the earlier entries and
their exceptions. A passing test or an agent's opinion is not user acceptance.

Each checkpoint pins the components separately: the Mac receiver, Agentic Mouse
(which owns the HUD), and the wand firmware. Do not assume they share a version.
Use the existing private, guarded installation workflow to restore an installed
component. Do not reset a working checkout, erase later work, or flash firmware
merely to revisit a HUD change. For a partial rollback, compare the relevant
files with the pinned commit and preserve later unrelated improvements.

## 2026-11-01 — Liked baseline before directed HUD aiming

**User feedback:** “I like the behavior overall other than that.” Ethan asked
for this checkpoint so the liked behavior can be recovered in future.

| Component | Installed version | Source checkpoint |
| --- | --- | --- |
| Agentic Mouse / wand HUD | 1.0.324 (330) | [8eedd5270ab2923e6aeaf37f1666de73930b02fb](https://github.com/EthanSK/agentic-mouse/commit/8eedd5270ab2923e6aeaf37f1666de73930b02fb) |
| Wand Receiver | 1.2.185 (190) | [87bbf5dc8a77c6f6dbe8fe56e6fb8a610bad682a](https://github.com/EthanSK/magic-wand/commit/87bbf5dc8a77c6f6dbe8fe56e6fb8a610bad682a) |
| XIAO Sense firmware | 12 | Same Magic Wand source checkpoint; saved installed firmware retained |

**Known exceptions at acceptance:** the liquid HUD outline was hard to aim
midway between selections, and slow movement could skip an intervening wedge
(Ethan's example: moving right from Utility could reach Keys instead of Chrome).
This is acceptance of the overall feel, not a claim that those defects were
fixed or that every feature was physically tested.

**Preserve while fixing those exceptions:** ordinary pointer and scroll feel,
stop-to-click, button timing, the existing hold/release and dotted-mode rules,
submenu behaviour, physical mouse controls, layout, and user-selected HUD size.
No firmware change is part of the directed-HUD-aiming fix.

**Verification recorded with this baseline:** installed versions and source
commits were read back before the next HUD edit. The previous release passed
1,259 native Agentic Mouse tests (four skipped), the receiver's 294 checks, and
its recorded installed review. Those checks are release evidence, separate
from Ethan's feedback above.
