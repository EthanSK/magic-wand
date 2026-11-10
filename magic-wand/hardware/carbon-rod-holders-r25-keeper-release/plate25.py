#!/usr/bin/env python3
"""Slice the matched R25 holder and keeper using the checked A1 mini recipe."""

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import catch25 as catch
import project22
import project23
import roundtrip23
import slice23


LABEL = "R25-XIAO-Catch-A1-mini-PETG"
OUT = catch.OUT


def build(scratch):
    old = project22.holder
    project22.holder = SimpleNamespace(
        PLATE=(catch.HOLDER, catch.KEEPER), ANCHORED=(catch.HOLDER,),
        HERE=catch.HERE, R19=old.R19, R20=old.R20, P=old.P, LOCAL=old.LOCAL,
        base=old.base, sha=old.sha, key_carrier_bands=old.key_carrier_bands,
    )
    project22.LABEL = LABEL
    project22.PLATE_NAME = "Magic Wand R25 lift-release holder and keeper trial"
    project22.ORIGINS = {catch.HOLDER: (34, 106), catch.KEEPER: (73, 66)}
    project22.OBJECT_WALL_GENERATORS = {}
    project22.FILL_BOUNDS = []
    configure = project22.configure_layout
    project22.configure_layout = lambda path: project23.configure_fit_trial(
        path, configure, False, catch.h, project22.studio.p19, None)
    project22.build(scratch, True)
    receipt = OUT / f"{LABEL}-print-checks.json"
    report = json.loads(receipt.read_text())
    report["trial_generator_sha256"] = catch.h.sha(__file__)
    report["adhesion_policy"] = ("The holder uses the checked removable pads. "
                                 "The keeper uses a 3 mm outer-only brim. No automatic support.")
    receipt.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        slice23.inspect(catch.R23, OUT, OUT / "slice-clearances.json", label=LABEL)
        roundtrip23.run(args.scratch / "reopen", OUT, label=LABEL, exports=OUT)
    else:
        build(args.scratch / "studio")
