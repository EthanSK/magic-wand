"""Check R37's complete deposited paths, including the adjustable stop."""

import argparse
import json
from pathlib import Path

import numpy as np

import holder37 as design
import audit36 as grove

grove.design = design


class Travel(grove.Travel):
    def poses(self):
        for angle in np.linspace(design.EARLY_ANGLE, design.BACKUP_ANGLE, 19):
            yield design.r.world(self.part, angle)


grove.Travel = Travel


def routes():
    clear, material = grove.routes()
    clear[design.BRACKET]["adjustment pilot"] = design.stop_pilot(.61) ^ design.box(
        -1., 1., design.STOP_Y - 1., design.STOP_Y + 1.,
        design.STOP_BOSS_BOTTOM + .12, design.STOP_BOSS_BOTTOM + 4.05)
    material[design.BRACKET]["adjustment screw boss"] = design.stop_stock() ^ design.box(
        -1.85, 1.85, design.STOP_Y - 1.8, design.STOP_Y + 1.8,
        design.STOP_BOSS_BOTTOM + .15, design.STOP_BOSS_BOTTOM + 2.5)
    material[grove.plate.KEY]["hard-stop screw landing"] = design.box(
        -1.75, 1.75, design.STOP_Y + 3.55 - 1.4, design.STOP_Y + 3.55 + 1.4, 10.65, design.DECK_TOP)
    return clear, material


def audit(archive, scratch):
    result = grove.audit(archive, scratch, route_builder=routes)
    checker = grove.load_checker().audit
    data, features, _, _, offset, objects, *_ = checker.read_project(archive)
    data = data[np.asarray(features)[data[:, 5].astype(int)] != "Prime tower"]
    part = design.BRACKET
    manifest = grove.plate.read_json(scratch / "build-source/exports/manifest.json")
    inverse = np.linalg.inv(np.asarray(manifest["parts"][part]["print_to_assembly"]))[:3, :]
    local = data[:, :3] + offset - objects[part]["vertices"].min(0)
    pilot = routes()[0][part]["adjustment pilot"]
    result["adjustable_pilot_section"] = grove.clearance_sections(data, local, [pilot], inverse, checker)
    if not result["adjustable_pilot_section"]["passed"]:
        result["failures"].append([part, "adjustment pilot", result["adjustable_pilot_section"]])
    result["passed"] = not result["failures"]
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("scratch", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = audit(args.archive, args.scratch)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    if not report["passed"]:
        raise SystemExit("See the R37 audit for remaining printability issues.")
