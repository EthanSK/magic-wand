#!/usr/bin/env python3
"""Download the website's third-party files at pinned versions and record their hashes.

    python3 scripts/vendor.py          # fetch Three.js and the fonts, write data/vendor.lock.json
    python3 scripts/vendor.py --check  # verify the committed files against the lock (offline)

Three.js comes from the npm registry tarball, verified against the registry's sha512 integrity.
Fonts are the Latin variable WOFF2 files Google Fonts serves, with their SIL Open Font License
from google/fonts. Downloads are treated as data: files are read by name, never extracted wholesale.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import re
import sys
import tarfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import ROOT, REPOSITORY, DOCS
LOCK = ROOT / "data" / "vendor.lock.json"
THREE_VERSION = "0.185.1"  # Last npm release with minified builds; matches Agentic Mouse.
THREE_DIR = f"lib/three-{THREE_VERSION}"
THREE_FILES = {
    "package/build/three.module.min.js": f"{THREE_DIR}/three.module.min.js",
    "package/build/three.core.min.js": f"{THREE_DIR}/three.core.min.js",
    "package/LICENSE": f"{THREE_DIR}/LICENSE.txt",
}
FONTS = [
    # family, Google Fonts axis query, google/fonts directory, local file stem
    ("Big Shoulders Display", "wght@100..900", "bigshouldersdisplay", "big-shoulders-display"),
    ("Atkinson Hyperlegible Next", "wght@200..800", "atkinsonhyperlegiblenext", "atkinson-hyperlegible-next"),
    ("Atkinson Hyperlegible Mono", "wght@200..800", "atkinsonhyperlegiblemono", "atkinson-hyperlegible-mono"),
]
BROWSER = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def fetch(url: str, accept_user_agent: bool = False) -> bytes:
    headers = {"User-Agent": BROWSER} if accept_user_agent else {"User-Agent": "magic-wand-vendor"}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
        return response.read()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def vendor() -> dict:
    files: dict[str, dict] = {}
    meta = json.loads(fetch(f"https://registry.npmjs.org/three/{THREE_VERSION}"))
    tarball = fetch(meta["dist"]["tarball"])
    algorithm, expected = meta["dist"]["integrity"].split("-", 1)
    if algorithm != "sha512" or base64.b64encode(hashlib.sha512(tarball).digest()).decode() != expected:
        raise SystemExit("Three.js tarball failed its registry integrity check")
    with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as archive:
        for member, target in THREE_FILES.items():
            handle = archive.extractfile(archive.getmember(member))
            data = handle.read()
            (DOCS / target).parent.mkdir(parents=True, exist_ok=True)
            (DOCS / target).write_bytes(data)
            files[target] = {"sha256": sha256(data), "source": f"{meta['dist']['tarball']}#{member}", "license": "MIT"}
    for family, axes, directory, stem in FONTS:
        css = fetch(f"https://fonts.googleapis.com/css2?family={family.replace(' ', '+')}:{axes}&display=swap", True).decode()
        block = css.split("/* latin */", 1)[1]
        url = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+\.woff2)\)", block).group(1)
        data = fetch(url)
        target = f"fonts/{stem}.woff2"
        (DOCS / target).parent.mkdir(parents=True, exist_ok=True)
        (DOCS / target).write_bytes(data)
        files[target] = {"sha256": sha256(data), "source": url, "family": family, "license": "OFL-1.1"}
        license_text = fetch(f"https://raw.githubusercontent.com/google/fonts/main/ofl/{directory}/OFL.txt")
        license_target = f"fonts/{stem}-OFL.txt"
        (DOCS / license_target).write_bytes(license_text)
        files[license_target] = {"sha256": sha256(license_text), "source": f"https://github.com/google/fonts/blob/main/ofl/{directory}/OFL.txt"}
    return {"schemaVersion": 1, "three": THREE_VERSION, "files": files}


def check() -> int:
    lock = json.loads(LOCK.read_text())
    problems = [name for name, entry in lock["files"].items()
                if not (DOCS / name).is_file() or sha256((DOCS / name).read_bytes()) != entry["sha256"]]
    if problems:
        print("Vendored files differ from data/vendor.lock.json:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    print(f"{len(lock['files'])} vendored files match the lock")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        return check()
    LOCK.write_text(json.dumps(vendor(), indent=2) + "\n")
    return check()


if __name__ == "__main__":
    sys.exit(main())
