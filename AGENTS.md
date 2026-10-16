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
  double tap stops. The pointer holds still while a click is decided.
- Middle: tap opens the HUD on Switch App, turning moves the outline and stops at the edges,
  a tap uses a card after about 0.8 s, double tap closes, Bottom returns to the pointer.
- Starting with the HUD closed: hold Middle, turn to a card, then release to use it once.
- In released-button pointer follow: a deliberate full clockwise circle starts down-scroll,
  anticlockwise starts up-scroll, cyan shows recognition, and pausing returns to pointing.
  Bottom holds, real drags and HUD navigation must never trigger circular scrolling.
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
