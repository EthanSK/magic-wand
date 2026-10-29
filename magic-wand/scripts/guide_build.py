"""Generate the receiver's always-available instruction panel from wand.json.

Ethan asked for "a HUD that's always showing that gives away all the instructions for how to
do everything". The instructions themselves stay in the canonical manifest (button gestures,
lights and power tuning); this only selects and orders them, so the panel, website and README
cannot disagree. The receiver chooses the Puck or Sense button labels at run time.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import ROOT  # noqa: E402

GENERATED = ROOT / "device" / "generated"
# Panel order: HUD, mouse, then speech, matching the Sense grip from left to right.
ORDER = ["middle", "bottom", "top"]
# Light modes worth a line in the panel; the rest are covered by Power.
LIGHTS = ["mouse", "scroll", "hud", "app", "recording", "update", "disconnected", "sleep"]


def _minutes(seconds: float) -> str:
    minutes = round(seconds / 60)
    return "a minute" if minutes == 1 else f"{minutes} minutes"


def guide(manifest: dict) -> dict:
    buttons = {button["id"]: button for button in manifest["buttons"]}
    missing = [button_id for button_id in ORDER if button_id not in buttons or "senseButton" not in buttons[button_id]]
    if missing:
        raise ValueError("wand.json buttons need senseButton labels: " + ", ".join(missing))
    sections = []
    for button_id in ORDER:
        button = buttons[button_id]
        sense = button["senseButton"]
        sections.append({
            "button": button_id,
            "role": button["role"],
            "puckLabel": button["name"],
            "senseLabel": f"Button {sense['number']} · {sense['position']}",
            "rows": [list(row) for row in button["gestures"]],
        })
    tuning = manifest["tuning"]
    warning = tuning["sleepWarning"]
    flashes = {1: "once", 2: "twice"}.get(warning["flashes"], f"{warning['flashes']} times")
    power = [
        ["All three buttons", tuning["manualPowerChord"]],
        ["Resting on the desk", f"The light turns off after {_minutes(tuning['deskSleepSeconds'])}; pick the wand up to wake it"],
        ["Left resting longer", f"After {_minutes(tuning['deepSleepSeconds'])}, every light flashes {flashes} and the wand sleeps; press any button to wake it"],
    ]
    lights = {light["mode"]: light for light in manifest["lights"]}
    return {
        "schemaVersion": 1,
        "title": "Wand guide",
        "sections": sections,
        "power": power,
        "lights": [{"mode": mode, "name": lights[mode]["name"], "detail": lights[mode]["detail"],
                    "display": lights[mode]["display"]} for mode in LIGHTS if mode in lights],
    }


def artifacts() -> dict[Path, str]:
    manifest = json.loads((ROOT / "wand.json").read_text())
    return {GENERATED / "wand-guide.json": json.dumps(guide(manifest), indent=2, ensure_ascii=False) + "\n"}
