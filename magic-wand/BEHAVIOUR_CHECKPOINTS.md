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


## 2026-11-01 — Liked quick initial and nearby-target clicks

**User feedback:** “Okay, the click things seems to work. Record that, this commit. The current head fixes it. Or maybe it's the sensor being really fast”.

| Component | Installed version | Source checkpoint |
| --- | --- | --- |
| Wand Receiver | 1.2.187 (192) | [c83491891022ffed0931cb23b33eee02f91f4c8a](https://github.com/EthanSK/magic-wand/commit/c83491891022ffed0931cb23b33eee02f91f4c8a)|
| Agentic Mouse / wand HUD | 1.0.327 (333) | [11b50dc64dea90ea9b51f3bfee40aa35e3e8453e](https://github.com/EthanSK/agentic-mouse/commit/11b50dc64dea90ea9b51f3bfee40aa35e3e8453e)|
| XIAO Sense firmware | 13 | Same Magic Wand source checkpoint; saved compiled firmware retained privately|
| Active reversible rate experiment | 6660 Hz configured sensor ODR | Firmware 13 runtime rate control; received throughput is lower and measured separately|

**Acceptance boundary:** Ethan likes the improved initial/nearby-target click behavior with this installed combination. He explicitly noted the improvement might also come from the higher sensor rate. No controlled comparison separated those causes, so preserve the complete combination as this checkpoint; do not claim the receiver or rate alone caused it.

**Known exception at acceptance:** stationary repeats at 300 ms are too fast. Ethan wants about one second between clicks when the pointer has not moved, while a small intentional move to another target should still click quickly. That slower repeat adjustment is a follow-up to this checkpoint, not part of the accepted 192 source.

**Preserve during the repeat adjustment:** first-click and tiny-retarget responsiveness, stillness thresholds, pointer output and smoothing, sensor rate, HUD/scroll/recenter cancellation, and the physical mouse profiles. Only the no-movement repeat interval should change.

**Verification:** installed 192 binary matched its reviewed signed receipt; the receiver reported ready over Bluetooth with firmware13 and the6660Hz experiment active. The previous batch passed 279 Wand, 17 Control Stones and 4 shared checks. This records physical click feedback, not acceptance of every gesture or prolonged sensor-rate stability.
