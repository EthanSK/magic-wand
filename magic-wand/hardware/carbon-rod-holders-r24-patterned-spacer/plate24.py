#!/usr/bin/env python3
"""Slice the patterned spacer with the checked R23 parts and R22 keepers."""

import argparse
from pathlib import Path

import spacer24 as spacer
import project23
import roundtrip23
import slice23

LABEL = "R24-A1-mini-PETG"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        staged = args.scratch / "build-source" / "exports"
        slice23.inspect(spacer.R23, staged, spacer.HERE / "exports/slice-clearances.json", label=LABEL)
        roundtrip23.run(args.scratch / "reopen", staged, label=LABEL, exports=spacer.HERE / "exports")
    else:
        project23.build(spacer.R23, args.scratch, do_slice=True, support=True, label=LABEL,
                        without_wire_clip=True, extra_exports=(spacer.OUT,),
                        extra_origins={spacer.NAME: (127, 49)}, delivery=spacer.HERE / "exports")
