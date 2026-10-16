#!/usr/bin/env python3
"""Website and privacy checks that complement the generated-file and vendor checks.

    python3 scripts/check.py

- No private values in any repository file: home-directory paths, device identifiers, Bluetooth
  UUIDs other than the public Nordic UART Service, task or session paths, emails or tokens.
- The footer links Ethan's setup at its canonical URL, and the wording disclaimer appears once.
- Every cache-keyed asset URL carries a key, and the import map and worker URLs point at files.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SKIP_DIRS = {".git", "build", ".cache", "work", "node_modules", "__pycache__"}
BINARY = {".png", ".jpg", ".webp", ".woff2", ".icns"}
PUBLIC_UUIDS = {"6E400001-B5A3-F393-E0A9-E50E24DCCA9E", "6E400002-B5A3-F393-E0A9-E50E24DCCA9E", "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"}
PATTERNS = {
    "home directory path": re.compile(r"/Users/[A-Za-z0-9._-]+"),
    "private temporary path": re.compile(r"/private/(?:tmp|var)/"),
    "task workspace path": re.compile(r"Documents/Codex/|\.codex/(?:sessions|memories)"),
    "Puck device name": re.compile(r"puck\.js [0-9a-f]{4}\b", re.IGNORECASE),
    "email address": re.compile(r"[A-Za-z0-9._%+-]+@(?:gmail|icloud|outlook|hotmail|me)\.com", re.IGNORECASE),
    "token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16})\b"),
    "private key": re.compile(r"BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY"),
}
UUID = re.compile(r"\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\b")
CANONICAL_SETUP = "https://ethansk.github.io/ethan-setup/"
DISCLAIMER = "All the wording on this website is AI generated, so sorry if it’s cringe."


def repository_files():
    for path in ROOT.rglob("*"):
        if path.is_file() and not (set(path.relative_to(ROOT).parts) & SKIP_DIRS) and path.suffix not in BINARY:
            yield path


def main() -> int:
    problems: list[str] = []
    for path in repository_files():
        if path.relative_to(ROOT).as_posix() == "scripts/check.py":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        name = path.relative_to(ROOT).as_posix()
        for label, pattern in PATTERNS.items():
            if name.startswith("docs/lib/") and label in {"email address"}:
                continue
            match = pattern.search(text)
            if match:
                problems.append(f"{name}: {label} at line {text.count(chr(10), 0, match.start()) + 1}")
        for value in UUID.findall(text):
            if value.upper() not in PUBLIC_UUIDS and not name.startswith("docs/lib/"):
                problems.append(f"{name}: unexpected UUID {value[:8]}…")

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
    print("Privacy scan, backlink, disclaimer, cache keys and asset URLs passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
