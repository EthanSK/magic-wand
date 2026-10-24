#!/usr/bin/env python3
"""Scan every component and published asset for private values."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
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


def repository_files():
    for path in ROOT.rglob("*"):
        if path.is_file() and not (set(path.relative_to(ROOT).parts) & SKIP_DIRS) and path.suffix not in BINARY:
            yield path


def main() -> int:
    problems: list[str] = []
    for path in repository_files():
        if path.relative_to(ROOT).as_posix() == "shared/checks/privacy.py":
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

    if problems:
        print("Privacy checks failed:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    print("Repository-wide privacy scan passed")
    return 0

if __name__ == "__main__":
    sys.exit(main())
