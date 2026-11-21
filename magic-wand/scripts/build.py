#!/usr/bin/env python3
"""Regenerate every derived file from the device sources, wand.json and the HUD snapshot.

    python3 scripts/build.py          # write generated files
    python3 scripts/build.py --check  # fail if any generated file is stale

Generated files include device/generated/*, docs/device/*, docs/data/*, docs/assembly/*,
the marked sections of docs/index.html and README.md, and the website's asset cache keys.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import assembly_publish  # noqa: E402
import device_build  # noqa: E402
import guide_build  # noqa: E402
import site_build  # noqa: E402
import tutorials_build  # noqa: E402

from paths import ROOT, REPOSITORY, DOCS


def outputs() -> dict[Path, str | bytes]:
    files = device_build.artifacts()
    files.update(guide_build.artifacts())
    files.update(site_build.artifacts(device_build.identifiers()))
    files.update(tutorials_build.artifacts(files))
    return {**files, **assembly_publish.artifacts()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="Report stale generated files without writing")
    args = parser.parse_args()
    stale = []
    for path, content in outputs().items():
        data = content.encode() if isinstance(content, str) else content
        if path.exists() and path.read_bytes() == data:
            continue
        stale.append(path.relative_to(REPOSITORY).as_posix())
        if not args.check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    if args.check:
        if stale:
            print("Stale generated files; from the repository root run npm run build --workspace magic-wand:\n  " + "\n  ".join(stale), file=sys.stderr)
            return 1
        print("Generated files are current")
        return 0
    print("Updated:\n  " + "\n  ".join(stale) if stale else "Generated files were already current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
