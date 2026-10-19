"""Generate the website and README sections that describe the wand, all from wand.json.

Hand-written prose lives in docs/index.html and README.md. Anything that names a control, pin,
light, version, dependency or tuning value sits between <!-- wand:NAME --> markers and is
rewritten here, so the site, the demo and the README cannot disagree with the manifest.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SITE = "https://ethansk.github.io/magic-wand/"
ASSET_EXTENSIONS = "css|mjs|js|json|svg|png|jpg|webp|woff2|webmanifest"
STAMP = re.compile(
    r"(?<=[\"'(])(?P<prefix>https://ethansk\.github\.io/magic-wand/|/magic-wand/|\./)?"
    r"(?P<path>[A-Za-z0-9_\-][A-Za-z0-9_\-./]*\.(?:" + ASSET_EXTENSIONS + r"))\?v=[0-9a-f]*"
)


def load_manifest(identifiers: dict[str, str]) -> dict:
    manifest = json.loads((ROOT / "wand.json").read_text())
    for key, actual in identifiers.items():
        if manifest["versions"][key] != actual:
            raise SystemExit(f"wand.json versions.{key} is {manifest['versions'][key]}, but the device sources build {actual}")
    return manifest


def light(manifest: dict, mode: str) -> dict:
    return next(item for item in manifest["lights"] if item["mode"] == mode)


def long_date(value: str) -> str:
    parsed = date.fromisoformat(value)
    return f"{parsed.day} {parsed.strftime('%B %Y')}"


# ---------------------------------------------------------------- website fragments

def html_meta(manifest: dict) -> str:
    text = escape(manifest["tagline"])
    return "\n".join([
        f'<meta name="description" content="{text}">',
        f'<meta property="og:description" content="{text}">',
        f'<meta name="twitter:description" content="{text}">',
    ])


def html_intro(manifest: dict) -> str:
    vision = manifest["vision"]
    return (
        f'<p class="tagline">{escape(manifest["tagline"])}</p>\n'
        f'<p class="summary">{escape(manifest["summary"])}</p>\n'
        f'<p class="vision"><strong>{escape(vision["headline"])}</strong> {escape(vision["detail"])}</p>'
    )


def md_intro(manifest: dict) -> str:
    vision = manifest["vision"]
    return f"{manifest['tagline']}\n\n{manifest['summary']}\n\n**{vision['headline']}** {vision['detail']}"


def grip_angle_notes(manifest: dict) -> list[str]:
    """Wand Receiver's optional roll compensation, from its tuning entry. Keep
    the limits: it measures roll from gravity, not full 3D orientation, and
    the wrist idea is untested."""
    option = manifest["tuning"]["orientationCompensation"]
    state = "on by default" if option["default"] else "off by default"
    check = " and still needs a physical check" if option.get("experimental") else ""
    return [
        "Roll the wand to a comfortable grip: Wand Receiver’s Options → Rotation-independent controls reads gravity "
        "from the Puck’s accelerometer, so directions stay upright on screen. Sideways speed also holds as the tip rises, "
        f"with up to {option['maxHeadingGain']:g}× correction.",
        f"It’s {state}{check}. It can’t read roll with the tip pointing almost straight up or down, and it isn’t full 3D "
        "tracking. Wrist training with different grip angles is an idea to study, not a tested benefit.",
    ]


def html_grip_angle(manifest: dict) -> str:
    notes = "\n".join(f"  <p>{escape(note)}</p>" for note in grip_angle_notes(manifest))
    return f'<h3 class="needs-title" id="grip-angle">Grip Angle</h3>\n<div class="inside-notes grip-notes">\n{notes}\n</div>'


def html_grip(manifest: dict) -> str:
    keys = []
    for button in manifest["buttons"]:
        keys.append(
            f'<button type="button" class="key" data-button="{button["id"]}" data-light="{button["light"]}" '
            f'aria-label="{escape(button["name"])}: {escape(button["role"])}" aria-pressed="false" aria-keyshortcuts="{button["key"]}">'
            f'<span class="key-name">{escape(button["name"])}</span>'
            f'<span class="key-role">{escape(button["role"])}</span>'
            f'<span class="key-meta"><span class="pin">{button["pin"]}</span><kbd>{button["key"]}</kbd></span>'
            "</button>"
        )
    for chord in manifest["chords"]:
        names = {button["id"]: button for button in manifest["buttons"]}
        shortcut = "+".join(names[item]["key"] for item in chord["buttons"])
        keycaps = "+".join(f"<kbd>{names[item]['key']}</kbd>" for item in chord["buttons"])
        keys.append(
            f'<button type="button" class="key key-chord" data-chord="{chord["id"]}" data-light="{chord["light"]}" '
            f'aria-label="{escape(chord["name"])}: {escape(chord["role"])}" aria-pressed="false" aria-keyshortcuts="{shortcut}">'
            f'<span class="key-name">{escape(chord["name"])}</span>'
            f'<span class="key-role">{escape(chord["role"])}</span>'
            f'<span class="key-meta">{keycaps}</span>'
            "</button>"
        )
    return "\n".join(keys)


def html_control(item: dict, pin: str | None, keys: str) -> str:
    rows = "\n".join(
        f"    <div><dt>{escape(gesture)}</dt><dd>{escape(result)}</dd></div>" for gesture, result in item["gestures"]
    )
    notes = ""
    if item.get("notes"):
        notes = '\n  <ul class="notes">' + "".join(f"<li>{escape(note)}</li>" for note in item["notes"]) + "</ul>"
    meta = (f'<span class="pin">{pin}</span>' if pin else "") + keys
    return (
        f'<div class="control" data-light="{item["light"]}">\n'
        f'  <div class="control-head"><h3>{escape(item["name"])}</h3><p class="control-meta">{meta}</p></div>\n'
        f'  <p class="control-role"><span class="swatch" aria-hidden="true"></span>{escape(item["role"])}</p>\n'
        f'  <dl class="gestures">\n{rows}\n  </dl>{notes}\n'
        "</div>"
    )


def html_controls(manifest: dict) -> str:
    names = {button["id"]: button for button in manifest["buttons"]}
    parts = [html_control(button, button["pin"], f"<kbd>{button['key']}</kbd>") for button in manifest["buttons"]]
    for chord in manifest["chords"]:
        keys = "+".join(f"<kbd>{names[item]['key']}</kbd>" for item in chord["buttons"])
        parts.append(html_control(chord, None, keys))
    return "\n".join(parts)


def html_lights(manifest: dict) -> str:
    items = "\n".join(
        f'  <li data-light="{item["mode"]}"><span class="swatch" aria-hidden="true"></span>'
        f'<strong>{escape(item["name"])}</strong> <span>{escape(item["detail"])}</span></li>'
        for item in manifest["lights"]
    )
    return f'<p class="fine">Listed from highest priority.</p>\n<ul class="lights">\n{items}\n</ul>'


def html_dependencies(manifest: dict) -> str:
    items = "\n".join(
        f'  <li><a href="{escape(item["url"])}">{escape(item["name"])} <span aria-hidden="true">↗</span></a>'
        f' <span class="need-role">{escape(item["role"])}.</span> <span class="need-status">{escape(item["availability"])}</span></li>'
        for item in manifest["dependencies"]
    )
    return f'<ul class="needs">\n{items}\n</ul>'


def schematic(manifest: dict) -> str:
    """Side view of the wand. Proportions, spacing and the wire route are illustrative."""
    buttons = {button["id"]: button for button in manifest["buttons"]}
    order = [("bottom", 82), ("middle", 142), ("top", 202)]  # Top sits nearest the shaft.
    caps = []
    wires = []
    for index, (button_id, x) in enumerate(order):
        button = buttons[button_id]
        caps.append(
            f'<g class="cap" data-light="{button["light"]}"><rect x="{x - 13}" y="78" width="26" height="12" rx="5"/>'
            f'<text class="label" x="{x}" y="58" text-anchor="middle">{escape(button["name"])}</text>'
            f'<text class="pin-label" x="{x}" y="38" text-anchor="middle">{button["pin"]}</text></g>'
        )
        y = 104 + index * 5
        wires.append(f'<path class="wire" d="M{x} 96 V{y} H858"/>')
    return f"""<svg class="schematic" viewBox="0 0 1000 200" role="img" aria-labelledby="schematic-title schematic-desc">
  <title id="schematic-title">Wand schematic</title>
  <desc id="schematic-desc">A grip with three buttons, Bottom, Middle and Top, then a long carbon-fibre shaft ending in a Puck.js at the tip.</desc>
  <defs>
    <pattern id="twill" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
      <rect width="12" height="12" class="twill-a"/><rect width="6" height="12" class="twill-b"/>
    </pattern>
    <radialGradient id="tip-light"><stop offset="0" class="tip-stop-inner"/><stop offset="1" class="tip-stop-outer"/></radialGradient>
  </defs>
  <rect class="grip-body" x="40" y="88" width="210" height="44" rx="20"/>
  {''.join(caps)}
  <rect class="shaft-body" x="246" y="102" width="616" height="16" rx="3" fill="url(#twill)"/>
  {''.join(wires)}
  <circle class="tip-glow-svg" cx="902" cy="110" r="70" fill="url(#tip-light)"/>
  <rect class="puck" x="856" y="96" width="92" height="28" rx="14"/>
  <circle class="puck-led" cx="902" cy="104" r="4"/>
  <path class="dimension" d="M246 160 V170 M862 160 V170 M246 165 H862"/>
  <text class="label" x="554" y="190" text-anchor="middle">{escape(manifest["hardware"]["parts"][1][1])}</text>
  <text class="label" x="902" y="74" text-anchor="middle">{escape(manifest["hardware"]["board"])}</text>
</svg>"""


def html_hardware(manifest: dict) -> str:
    hardware = manifest["hardware"]
    parts = "\n".join(
        f"    <div><dt>{escape(name)}</dt><dd>{escape(detail)}</dd></div>" for name, detail in hardware["parts"]
    )
    return (
        '<figure class="schematic-figure">\n'
        f"{schematic(manifest)}\n"
        "<figcaption>Schematic, not to scale. Button spacing and the wire route are illustrative.</figcaption>\n"
        "</figure>\n"
        '<div class="hardware-notes">\n'
        f'  <dl class="parts">\n{parts}\n  </dl>\n'
        f'  <p>{escape(hardware["wiring"])}</p>\n'
        f'  <p><a href="{escape(hardware["boardUrl"])}">{escape(hardware["board"])} <span aria-hidden="true">↗</span></a></p>\n'
        "</div>"
    )


def tuning_rows(manifest: dict) -> list[tuple[str, str, str]]:
    t = manifest["tuning"]
    reduction = round((1 - t["pointerGain"] / t["previousPointerGain"]) * 100)
    return [
        ("Pointer gain", f"{t['pointerGain']} counts per degree", f"{reduction}% below the earlier {t['previousPointerGain']}"),
        ("Vertical", f"× {t['verticalRatio']}", "Up and down move further than sideways"),
        ("Fine aim", f"{round(t['fineGain'] * 100)}% gain below {t['fineSpeedDegreesPerSecond']}°/s",
         f"Full gain from {t['fullSpeedDegreesPerSecond']}°/s"),
        ("Noise zone", f"Up to {t['maximumNoiseZoneDegreesPerSecond']}°/s", "Measured during calibration"),
        ("Sensor", f"{t['sensorRequestHz']} Hz requested", f"About {t['processedHzMeasured']} Hz fully processed in a recent measurement"),
        ("Bluetooth interval", f"{t['bluetoothIntervalMs']} ms requested", ""),
        ("Button-jolt guard", f"{t['pressGuardMs']} ms after a press, {t['releaseGuardMs']} ms after a release", "Motion in the guard is dropped, not replayed"),
        ("Cold start", f"{t['coldSettleMs']} ms settling", "Skipped when the sensor is still warm"),
        ("Gyro sleep", f"After {t['sensorIdleGraceMs'] / 1000:g} s idle", f"Accelerometer stays at {t['idleAccelerometerHz']} Hz for pickup; off on disconnect"),
        ("Hold", f"{t['holdMs']} ms", "Longer presses count as holds"),
        ("LOW movement delay", f"{t['lowMotionDelayMs']} ms", ""),
        ("HIGH stop-to-click", f"{t['highDwellMs']} ms still", "One click after deliberate movement; no repeat while still"),
        ("Double-click window", f"{t['macDoubleClickSeconds']:g} s", "Read from the Mac’s setting"),
        ("Scrolling", f"Horizontal × {t['horizontalScrollBoost']}", f"Mac wheel gain {t['hostScrollGain']}"),
        ("Middle report", f"After {t['middleReportDelayMs']} ms", "So Bottom + Middle can become a scroll"),
        ("Reports", f"Every {t['reportIntervalMs']} ms", "While the HUD or scrolling is active"),
        ("Calibration", f"{t['calibrationSeconds']} s still, no buttons pressed", "Kept across reconnects"),
    ]


def html_tuning(manifest: dict) -> str:
    rows = "\n".join(
        f'    <tr><th scope="row">{escape(label)}</th><td>{escape(value)}</td><td>{escape(note)}</td></tr>'
        for label, value, note in tuning_rows(manifest)
    )
    return f'<table class="spec">\n  <tbody>\n{rows}\n  </tbody>\n</table>'


def html_status(manifest: dict) -> str:
    versions = manifest["versions"]
    items = "\n".join(f"  <li>{escape(line)}</li>" for line in manifest["status"])
    return (
        f'<ul class="status-list">\n{items}\n</ul>\n'
        '<p class="versions">'
        f'<span>Receiver {versions["receiver"]} ({versions["receiverBuild"]})</span> '
        f'<span>Device code {versions["deviceRuntime"]}</span> '
        f'<span>Bridge {versions["bridgeRevision"][:8]}</span></p>\n'
        f'<p class="fine">Updated {long_date(manifest["updated"])}</p>'
    )


def css_lights(manifest: dict) -> str:
    return "\n".join(f'[data-light="{item["mode"]}"] {{ --swatch: {item["display"]}; }}' for item in manifest["lights"])


# ---------------------------------------------------------------- README fragments

def md_controls(manifest: dict) -> str:
    blocks = []
    for item in manifest["buttons"] + manifest["chords"]:
        head = f"**{item['name']}**" + (f" (`{item['pin']}`)" if item.get("pin") else "") + f" · {item['role']}"
        rows = "\n".join(f"| {gesture} | {result} |" for gesture, result in item["gestures"])
        notes = "".join(f"\n- {note}" for note in item.get("notes", []))
        blocks.append(f"{head}\n\n| Gesture | Result |\n| --- | --- |\n{rows}\n{notes}".rstrip())
    lights = "\n".join(f"| {item['name']} | {item['detail']} |" for item in manifest["lights"])
    return "\n\n".join(blocks) + f"\n\n**Lights**, highest priority first\n\n| Light | Shows |\n| --- | --- |\n{lights}"


def md_status(manifest: dict) -> str:
    versions = manifest["versions"]
    lines = "\n".join(f"- {line}" for line in manifest["status"])
    return (
        f"{lines}\n\nReceiver {versions['receiver']} ({versions['receiverBuild']}) · device code `{versions['deviceRuntime']}`"
        f" · bridge `{versions['bridgeRevision'][:8]}` · updated {long_date(manifest['updated'])}."
    )


def md_dependencies(manifest: dict) -> str:
    return "\n".join(f"- [{item['name']}]({item['url']}): {item['role']}. {item['availability']}" for item in manifest["dependencies"])


def md_tuning(manifest: dict) -> str:
    rows = "\n".join(f"| {label} | {value} | {note} |" for label, value, note in tuning_rows(manifest))
    return f"| Setting | Value | Note |\n| --- | --- | --- |\n{rows}"


# ---------------------------------------------------------------- assembly

def replace_markers(text: str, fragments: dict[str, str], html_markers: bool = True) -> str:
    for name, fragment in fragments.items():
        start, end = (f"<!-- wand:{name} -->", f"<!-- /wand:{name} -->") if html_markers else (f"/* wand:{name} */", f"/* /wand:{name} */")
        pattern = re.compile(r"(?P<indent>[ \t]*)" + re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
        match = pattern.search(text)
        if not match:
            continue
        indent = match.group("indent")
        body = "\n".join((indent + line) if line else line for line in fragment.splitlines())
        text = text[:match.start()] + f"{indent}{start}\n{body}\n{indent}{end}" + text[match.end():]
    return text


def stamp(text: str, contents: dict[Path, str]) -> str:
    def version(match: re.Match) -> str:
        path = DOCS / match.group("path")
        data = contents[path].encode() if path in contents else path.read_bytes() if path.is_file() else None
        if data is None:
            raise SystemExit(f"Missing asset for cache key: {match.group('path')}")
        return f"{match.group('prefix') or ''}{match.group('path')}?v={hashlib.sha256(data).hexdigest()[:10]}"
    return STAMP.sub(version, text)


def artifacts(identifiers: dict[str, str]) -> dict[Path, str]:
    from device_build import GENERATED  # noqa: PLC0415 - shared paths

    manifest = load_manifest(identifiers)
    hud = json.loads((ROOT / "data" / "agentic-mouse-hud.json").read_text())
    # Native wand-only cards override the shared mouse snapshot, without changing upstream data.
    for card in hud["cards"]:
        card.update(manifest.get("hud", {}).get("cardOverrides", {}).get(str(card["cell"]), {}))
    public = {key: value for key, value in manifest.items() if not key.startswith("$")}
    out: dict[Path, str] = {
        DOCS / "data" / "wand.json": json.dumps(public, indent=2, ensure_ascii=False) + "\n",
        DOCS / "data" / "hud.json": json.dumps(hud, indent=2, ensure_ascii=False) + "\n",
        DOCS / "device" / "wand-mouse-prototype.js": (ROOT / "device" / "wand-mouse-prototype.js").read_text(),
    }
    from device_build import artifacts as device_artifacts  # noqa: PLC0415

    out[DOCS / "device" / "wand-mode-bridge.compact.js"] = device_artifacts()[GENERATED / "wand-mode-bridge.compact.js"]

    css_path = DOCS / "styles.css"
    css = replace_markers(css_path.read_text(), {"lights": css_lights(manifest)}, html_markers=False)
    out[css_path] = stamp(css, out)

    html_fragments = {
        "meta": html_meta(manifest), "intro": html_intro(manifest), "grip": html_grip(manifest),
        "controls": html_controls(manifest), "lights": html_lights(manifest), "dependencies": html_dependencies(manifest),
        "hardware": html_hardware(manifest), "tuning": html_tuning(manifest), "status": html_status(manifest),
        "gripAngle": html_grip_angle(manifest),
    }
    for page in ("index.html", "404.html"):
        path = DOCS / page
        if path.exists():
            out[path] = stamp(replace_markers(path.read_text(), html_fragments), out)

    sitemap = DOCS / "sitemap.xml"
    if sitemap.exists():
        out[sitemap] = re.sub(r"<lastmod>[^<]*</lastmod>", f"<lastmod>{manifest['updated']}</lastmod>", sitemap.read_text())

    readme = ROOT / "README.md"
    if readme.exists():
        out[readme] = replace_markers(readme.read_text(), {
            "intro": md_intro(manifest), "controls": md_controls(manifest), "status": md_status(manifest),
            "dependencies": md_dependencies(manifest), "tuning": md_tuning(manifest),
        })
    return out
