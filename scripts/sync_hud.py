#!/usr/bin/env python3
"""Refresh the demo HUD's card labels from Agentic Mouse's published website.

The wand borrows the right-handed Corsair layout of Agentic Mouse's HUD. This copies only the
Default mode's grid, titles, colours and wheel labels into data/agentic-mouse-hud.json, with the
upstream revision and a hash of the downloaded file. It never reads a local Agentic Mouse checkout.

    python3 scripts/sync_hud.py           # download and write
    python3 scripts/sync_hud.py --check   # fail if the published labels changed
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://ethansk.github.io/agentic-mouse/simulator-data.json"
TARGET = ROOT / "data" / "agentic-mouse-hud.json"


def extract(raw: bytes) -> dict:
    data = json.loads(raw)
    corsair = data["sources"]["corsair"]
    default = corsair["modes"]["default"]
    cards = []
    for control in sorted(default["controls"], key=lambda item: item["cell"]):
        wheel = control.get("wheel")
        cards.append({
            "cell": control["cell"],
            "title": control["title"],
            "fill": control["hud"]["fill"],
            "border": control["hud"]["border"],
            "foreground": control["hud"]["foreground"],
            "opens": control.get("next"),
            "wheel": None if not wheel else {key: wheel.get(key) for key in ("id", "up", "down") if wheel.get(key) is not None},
        })
    return {
        "source": SOURCE,
        "sourceSha256": hashlib.sha256(raw).hexdigest(),
        "revision": data["revision"],
        "version": data["version"],
        "title": default["title"],
        "rows": corsair["rows"],
        "cards": cards,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    with urllib.request.urlopen(SOURCE, timeout=30) as response:
        raw = response.read()
    content = json.dumps(extract(raw), indent=2, ensure_ascii=False) + "\n"
    current = TARGET.read_text() if TARGET.exists() else ""
    if args.check:
        same = json.loads(current or "{}").get("cards") == json.loads(content)["cards"] if current else False
        print("HUD labels match the published Agentic Mouse site" if same else "Published HUD labels changed; run scripts/sync_hud.py")
        return 0 if same else 1
    TARGET.write_text(content)
    print("Wrote", TARGET.relative_to(ROOT), "from revision", json.loads(content)["revision"][:10])
    return 0


if __name__ == "__main__":
    sys.exit(main())
