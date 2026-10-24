#!/usr/bin/env python3
"""Check Magic Wand's published site assets. Privacy is checked repository-wide."""
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import DOCS

CANONICAL_SETUP = "https://ethansk.github.io/ethan-setup/"
DISCLAIMER = "All the wording on this website is AI generated, so sorry if it’s cringe."

def main() -> int:
    problems: list[str] = []
    index = (DOCS / "index.html").read_text()
    footer = index[index.index('<footer class="footer">'):]
    if f'<a href="{CANONICAL_SETUP}">Ethan’s setup' not in footer:
        problems.append("index.html footer must link “Ethan’s setup” to " + CANONICAL_SETUP)
    if index.count(DISCLAIMER) != 1:
        problems.append("index.html must contain the wording disclaimer exactly once")
    for page in ("index.html", "404.html", "styles.css"):
        text = (DOCS / page).read_text()
        empty = re.findall(r"[\w./-]+\?v=(?![0-9a-f]{10})", text)
        if empty:
            problems.append(f"{page}: asset URLs without a content key: {', '.join(sorted(set(empty)))}")
    imports = json.loads(re.search(r'<script type="importmap">(.*?)</script>', index, re.S).group(1))["imports"]
    assets = json.loads(re.search(r'<script type="application/json" id="asset-urls">(.*?)</script>', index, re.S).group(1))
    for url in list(imports.values()) + list(assets.values()):
        if not (DOCS / url.split("?")[0].removeprefix("./")).is_file():
            problems.append(f"index.html points at a missing file: {url}")
    for key in imports:
        if key.startswith("./") and not (DOCS / key[2:]).is_file():
            problems.append(f"import map key has no module: {key}")

    if problems:
        print("Checks failed:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    print("Backlink, disclaimer, cache keys and asset URLs passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
