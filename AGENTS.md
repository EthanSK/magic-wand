# Magic Wand: instructions for agents

This repository owns the public Magic Wand website, the wand’s published device code and receiver
source, and their tests. Read README.md, SOURCES.md and LEARNINGS.md before changing anything.

## One source of truth

- `wand.json` describes the wand: controls, pins, keys, lights, tuning, versions, status and
  dependencies. Change it with every device, bridge or receiver change.
- Never hand-edit generated output: `device/generated/`, `docs/device/`, `docs/data/`, anything
  between `<!-- wand:NAME -->` markers in `docs/index.html` and `README.md`, the `/* wand:lights */`
  block in `docs/styles.css`, or `?v=` cache keys. Run `python3 scripts/build.py`.
- `scripts/site_build.py` holds the wording that turns tuning numbers into sentences; keep it
  factual and update it when a tuning field changes meaning.

## When the wand changes

1. Finish and verify the change on the wand first. This repository publishes; it never installs.
2. Import the canonical sources: `python3 scripts/import_private.py --from <private outputs directory>`.
   Don’t copy files by hand and never record the private path. If an anchor changed, update the
   sanitiser rather than weakening it.
3. Update `wand.json`: versions, any changed control or light, tuning, `status` and `updated`.
4. `python3 scripts/build.py`, then `npm run check` (generated files, vendored files, privacy
   scan, every test). The manifest tests fail until `wand.json` matches the code.
5. If Agentic Mouse’s Default mode changed, run `python3 scripts/sync_hud.py`.
6. Check every changed visible string with the `write-user-facing-messages` skill. Never use the
   word “whether”. Keep the AI wording disclaimer once, in the footer.
7. Test the finished site in Codex’s built-in browser (below) before publishing.
8. Publish through `docs/` on `main`, wait for Pages to deploy, and compare the live cache-keyed
   assets with the committed files.
9. If the name, URL or description changes, update the Magic Wand entry in EthanSK/ethan-setup
   (`docs/projects.json` and its README count) in an isolated checkout.

## Browser check

Use Codex’s built-in browser; don’t open or focus Ethan’s personal Chrome. After the last edit, run
a local server (`npm run serve`) or use the live site and check:

- Hovering turns the wand; left button is Bottom, right button is Middle.
- Bottom: tap to follow, hold-turn-release clicks once, tap-then-hold drags a light stroke,
  double tap recenters on the main display. The pointer holds still while a click is decided.
- Middle: tap opens the HUD on Switch App, turning moves the outline and stops at the edges,
  a tap uses a card after about 0.8 s, double tap closes, Bottom returns to the pointer.
- Starting with the HUD closed: hold Middle, turn to a card, then release to use it once.
- Control V3 on the installed receiver: a Bottom-held straight stroke sets scrolling direction and speed; holding still continues it. Another stroke can reverse in the same hold. Release stops; the pointer remains anchored. Circular page scrolling stays disabled. The browser simulation and illustrated videos retain their labelled earlier control scope until ported.
- Hold Middle on Horizontal Scroll + Wheel and tilt: wheel steps appear.
- Bottom + Middle (both mouse buttons, B+M keys, or the chord key while dragging) scrolls both axes.
- Top toggles the Agent Flow indicator; the light is red only when nothing else is active.
- Keys T, M, B and the arrows, Space/Enter on a focused grip key, touch dragging with a held key,
  Reset, a narrow phone width, reduced motion, and browser console errors.
- The fallback wand when WebGL is unavailable.

Report any check the browser tool can’t do, such as real multitouch, rather than calling it passed.

## Boundaries

- If we are going to add a delay in the future, warn Ethan and double-check his explicit confirmation first.
- Before adding or increasing an intentional delay to pointer movement, including buffering,
  look-ahead, or smoothing/interpolation that adds latency, explain what will be delayed and the
  expected amount, then wait for his confirmation before implementing it.
- An earlier latency experiment or approval does not authorize a new delay. Do not describe
  smoothing or interpolation as delay-free unless that has been established.

- Never connect to, flash, reconfigure or restart the real Puck, Wand Receiver, Agentic Mouse or
  Agent Flow from work in this repository.
- Don’t build the receiver app next to Ethan’s installed copy with the same bundle identifier; it
  can register with Launch Services and share permissions. Compile checks use
  `swiftc -typecheck` or a bare executable in a temporary directory.
- Never commit `device.json`, logs, receipts, readback dumps, Bluetooth identifiers, local paths,
  order details or tokens. `scripts/check.py` scans for the patterns it can recognise; it can’t
  recognise everything.
- Don’t state latency, accuracy, battery life or other performance the wand hasn’t been measured
  for. Don’t describe parts that aren’t fitted, such as researched replacement switches.
- Keep the demo boundary sentence: the simulation never connects to a wand, Bluetooth or a Mac.
- Agentic Mouse owns the HUD and its labels; Agent Flow owns dictation. Describe their wand support
  as unpublished until it is on their public `main` branches.
- Keep the footer’s “Ethan’s setup” link to https://ethansk.github.io/ethan-setup/.
- Preserve third-party licences in `docs/lib/` and `docs/fonts/`; update `data/vendor.lock.json`
  only through `scripts/vendor.py`.

## Working rules and project skills

- Commit code regularly, including after each completed, verified feature or fix. Do not leave
  all the work uncommitted until the end of a long chat. Commit only the intended change;
  preserve unrelated staged and unstaged work. A commit is not a claim of physical acceptance.
- Keep track of the rules Ethan adds automatically in this project's `AGENTS.md` or the relevant
  project skill, using his original wording as closely as possible. He has explicitly chosen
  these project files for that ongoing rule capture. Preserve explicit corrections to older
  rules; ask only when the intended rule is unclear. Do not turn every idea, experiment or
  dictated aside into a permanent rule.
- Keep historical findings and verified technical lessons in `LEARNINGS.md`; current controls,
  colours and tuning belong in `wand.json`. Do not use `AGENTS.md` as a transcript or task log.
- Use [magic-wand-dev](.agents/skills/magic-wand-dev/SKILL.md) for device, receiver, integration,
  release and prototype work. Use [learnings](.agents/skills/learnings/SKILL.md) before bug fixes
  and fragile changes, and preserve useful verified lessons afterward.
- Skills live in `.agents/skills/<name>/SKILL.md`, with `references/`, `scripts/` or `assets/`
  only when needed. `CLAUDE.md` and `.claude/skills` point at the same canonical instructions;
  never maintain diverging copies. Reuse the structure, not AIMVS-specific rules or tooling.
- Preserve `prototype-v1.0.0` as the immutable original-hardware baseline. Read
  `prototypes/README.md` before changing prototype profiles; later hardware gets a separate
  profile so returning to V1 does not lose its tuned behaviour.

## Control versions

- Before moving on to the next control version, keep the current state and snapshot it.
  Preserve the matching device code, receiver, settings and controls together so we can
  go back without losing the behavior. Control versions are separate from hardware prototypes.
- When a new control version changes only Bottom, keep every other control unchanged.
  Use one runtime version selector; never silently redefine an older version or move its tag.

- Before restarting Wand Receiver or Agentic Mouse, check Agent Flow automatically using its current authoritative idle probe, then recheck immediately after the restart warning and before replacement. Do not ask me whether I am finished when the app can report that itself. Busy or unknown capture state blocks the swap; do not stop recording to manufacture idle. Leave Agent Flow itself running. Table-rest detection must never stop dictation or dismiss an explicitly open wand HUD. User-requested — 2026-10-18.

- Notify me in this chat and with the native heads-up before installing a new wand version. Prepare and check it first so disconnection is as short as possible. Red is only for voice recording; updates, unavailable connections and calibration use orange. User-requested — 2026-10-18.

- Bottom (mouse), Middle (HUD/review), and Top (Agent Flow speech) are independent. Bottom must not clear review selection or the Middle HUD. In Review changes (Ethan's “eyes mode”) or Stage files (his “bang” / “!” whole-file mode), hide the large HUD on entry; use unheld clockwise circles for next and anticlockwise for previous only while VS Code is frontmost; one Middle press cancels and exits; hold Middle for about half a second to stage the accumulated set and stay in the same review mode, ready for the next set. Freeze review navigation for the entire press, including after staging. The floating indicator includes `(hold to commit set)`. Every rough clockwise quarter-turn is one next step; every anticlockwise quarter-turn is one previous step. A full loop is four steps, regardless of radius. North-to-east is next; east-to-north and north-to-west are previous. Accept rough diamond corners too. Straight down/up flick navigation is disabled; keep the nod/shake experiment behind its disabled option unless Ethan asks to enable it. Updated at Ethan’s request — 2026-10-19. Reuse Better Git's existing selection and staging lifecycle. User-requested — 2026-10-18.

## Action-by-action tutorials

Ethan wants “individual actions that the user can ask, how do I do this? And then we just show
the video for that action.” Read [tutorials/README.md](tutorials/README.md). Use the shared
index or `node tutorials/find.mjs "user question"` and return the matching direct guide link.
Check the selected control version and options first: default review-circle videos do not
describe the optional nod/shake mode. Keep the manifest, rendered videos and gallery in sync
through their build/check commands; never claim an illustration is physical verification.

- Control V3 page scrolling follows Ethan’s “drag up or down or left or right”: a straight stroke chooses velocity, holding still continues at that speed, another deliberate stroke changes direction or speed without release, and release stops. Do not re-enable circular page scrolling in V3. Preserve V2 and the independent Middle review gestures. User-requested — 2026-10-19.

## Opus for UX

- Ethan: “Do any UX related stuff with Opus actually and bug fixing and stuff you do yourself and like testing and installing.” Use Opus for Magic Wand UX implementation; Codex owns bug fixes, verification and installation. Announce each use with “Opus for UX” and say why it is being used. User-requested — 2026-10-19.

## Current contextual hold and sleep behaviour

- Bottom hold scrolls over a scroll area and drags a confirmed draggable target.
  Unknown or late target detection must never turn scrolling into a surprise
  drag; release and lost telemetry cancel pending target results. Preserve the
  explicit tap-then-hold drag. User-requested — 2026-10-19.
- On waking, return to the mouse-follow state from before rest instead of always
  entering mouse mode. A newer manual choice or recording-start pause wins.
  Keep HUD and dictation independent of sleep. User-requested — 2026-10-19.

## Hold-to-show wand HUD

- Hold Middle to show the wand HUD and move its outline; releasing uses the outlined card. An ordinary completed action closes the HUD. A submenu or selected continuous wheel control stays open for the next hold, and that next hold supplies its adjustment motion. Keep double-click dismissal. This replaces the earlier tap-to-latch/free-navigation HUD flow; Bottom mouse controls, Top dictation, and the separate persistent VS Code review lane remain independent. User-requested — 2026-10-20.
- The wand home Enter card sends ordinary Enter, just like the normal Agentic Mouse. Do not restore the retired wand-only Command-Enter / Steer override. User-requested — 2026-10-20.

- Keep the visible wand HUD anchored while Agent Flow starts or changes its panel. Capture recorder clearance when the HUD opens, and refresh on the next open or display reconfiguration; never move an active target under the wand because another app publishes temporary window bounds. User-requested — 2026-10-20.

## Control Stones

- Control Stones belongs in top-level `control-stones/` in this repository, not in a separate repository or under `prototypes/`. Previously `prototypes/control-stones`.
- Keep every existing sensor supported; isolate Sense and future sensor code from the Puck JavaScript and existing receiver. Reuse shared behavior through explicit adapters instead of mixing device implementations.
- Commit and push completed, checked Control Stones changes after each natural step. Preserve unrelated work; never force-push. User-requested — 2026-10-24.
