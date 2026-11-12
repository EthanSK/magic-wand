"""Check the exact Grove PETG slice for clearance, starts and load paths.

Run with a sliced archive, plate36.py output directory, and report path.
"""

import argparse
import json
from pathlib import Path

import manifold3d as mf
import numpy as np

import holder36 as design
from plate36 import plate
from audit35 import audit_roots, connector_support, early_connections, pad_holes, rectangle
from audit34 import print_routes as previous_routes, verify_bonds, verify_stops
from audit_plate32 import inspect, load_checker


class Travel:
    """Yield every sampled operating pose to the existing deposited-path checker."""

    def __init__(self, part):
        self.part = part

    def poses(self):
        for angle in np.linspace(-design.r.REST, 0., 13):
            yield design.r.world(self.part, angle)


def routes():
    gaps, material = previous_routes()
    previous = gaps.pop("DFRobot_Hole_Bracket")
    for name in ("DFR0030_Post_Clip", "DFR0030_Post_Clip_2"):
        gaps.pop(name, None)
        material.pop(name, None)
    gaps[plate.KEY].update({
        "Grove mated plug stroke": Travel(design.plug()),
        "Grove wire bend stroke": Travel(design.lead()),
    })
    gaps[design.BRACKET] = {
        name: part for name, part in previous.items()
        if not any(word in name.lower() for word in ("post", "clip", "dfrobot", "pcb", "lead"))
    }
    gaps[design.BRACKET].update({
        "Grove board seat": design.board(),
        "Grove socket and mated plug": design.housing() + design.plug(),
        "Grove underside solder components": design.components(),
        **{f"Grove screw pilot {index}": design.cylinder(0., y, design.BOARD_Z - design.PILOT_DEPTH + .25,
                                                       design.BOARD_Z - .07, .61)
           for index, y in enumerate(design.HOLES, 1)},
    })
    old_material = material.pop("DFRobot_Hole_Bracket")
    paddle = design.bracket()
    material[design.BRACKET] = {
        **{name: part for name, part in old_material.items()
           if not any(word in name.lower() for word in ("post", "clip", "dfrobot", "pcb", "lead"))},
        **{f"Grove screw boss {index}": paddle ^ design.cylinder(0., y, design.BOARD_Z - design.BOSS_DEPTH + .15,
                                                               design.BOARD_Z - .20, 1.78)
           for index, y in enumerate(design.HOLES, 1)},
    }
    return gaps, material


def audit_grove_roots(archive, exports):
    # The connected part of the web ends at the connector window. Check
    # the whole width from the bed to that opening, and the pad perforations.
    checker = load_checker().audit
    data, features, _, _, offset, objects, *_ = checker.read_project(archive)
    labels = np.asarray(features)[data[:, 5].astype(int)]
    model = (labels != "Prime tower") & ~np.char.startswith(labels, "Skirt") & ~np.char.startswith(labels, "Support")
    data = data[model]
    local = data[:, :3] + offset - objects[design.BRACKET]["vertices"].min(0)
    record = plate.read_json(exports / "manifest.json")["parts"][design.BRACKET]
    inverse = np.linalg.inv(np.asarray(record["print_to_assembly"]))[:3, :]
    front = design.box(-9.7, 9.7, design.old.TOUCH_WEB_FRONT, -4.76, 15.88, design.BOARD_Z)
    x0, y0, x1, y1 = front.transform(inverse).slice(.1).bounds()
    region = rectangle(x0, y0, x1, y1)
    ends = rectangle(x0, y0, x0 + 1.2, y1), rectangle(x1 - 1.2, y0, x1, y1)
    footprints = checker.start_audit.bead_footprints
    web = early_connections(data, local, {"front web up to the plug opening":
                           (region, *ends, -4.76 - design.old.TOUCH_WEB_FRONT)}, footprints, checker.q)
    anchors = plate.read_json(exports / "anchors.json")["parts"][design.BRACKET]
    holes = pad_holes(data, local, anchors, footprints, checker.q)
    return {"early_connections": web, "pad_holes": holes, "passed": web["passed"] and holes["passed"]}


def clearance_sections(data, xyz, poses, to_print, checker, witness_width=1.15):
    """Check the cavity and nearby deposited material even if its core is empty."""
    print_poses = [pose.transform(to_print) for pose in poses]
    bounds = np.asarray([pose.bounding_box() for pose in print_poses])
    low, high = bounds[:, :3].min(0), bounds[:, 3:].max(0)
    tops, heights, widths = data[:, 7], data[:, 4], data[:, 3]
    radius = widths[:, None] / 2
    margin = witness_width + radius
    close = ((xyz[:, :2] >= low[:2] - margin) & (xyz[:, :2] <= high[:2] + margin)).all(1)
    rows = []
    for top in np.unique(tops[(tops > low[2]) & (tops < high[2] + .3)]):
        same_layer = abs(tops - top) < .001
        middle = float(top) - float(heights[same_layer][0]) / 2
        sections = [pose.slice(middle) for pose, bound in zip(print_poses, bounds)
                    if bound[2] < middle < bound[5]]
        if not sections:
            continue
        section = mf.CrossSection.batch_boolean(sections, mf.OpType.Add)
        if section.is_empty() or section.area() < .03:
            continue
        core = section.offset(-.05)
        band = section.offset(witness_width, mf.JoinType.Round) - section
        x0, y0, x1, y1 = band.bounds()
        ids = close & same_layer & ((xyz[:, :2] >= [x0, y0] - radius)
                                    & (xyz[:, :2] <= [x1, y1] + radius)).all(1)
        # The footprint helper uses 12-sided discs. Inflate them to enclose
        # the bead's full radius for intrusion testing.
        plastic = checker.start_audit.bead_footprints(checker.q, xyz[ids, :2],
                                                       widths[ids] / np.cos(np.pi / 12))
        rows.append((int(ids.sum()), (plastic ^ band).area(), (plastic ^ core).area()))
    checked = len(rows)
    surrounding = sum(area > .02 for _, area, _ in rows)
    intrusion = max((area for _, _, area in rows), default=0.)
    return {"layers_checked": checked, "layers_with_nearby_deposition": surrounding,
            "nearby_bead_samples": sum(n for n, _, _ in rows),
            "maximum_core_intrusion_mm2": round(intrusion, 5),
            "passed": bool(checked and surrounding and intrusion < .015)}


def verify_grove_clearances(archive, exports):
    checker = load_checker().audit
    data, features, _, _, offset, objects, *_ = checker.read_project(archive)
    data = data[np.asarray(features)[data[:, 5].astype(int)] != "Prime tower"]
    manifest = plate.read_json(exports / "manifest.json")["parts"]
    feed = [design.r.world(design.lead(1.45, lift=float(z))) for z in np.linspace(0., design.SERVICE_LIFT, 17)]
    clearance = {
        plate.KEY: {"plug stroke": list(Travel(design.plug()).poses()),
                    "pre-fed lead during board insertion": feed},
        design.BRACKET: {
            "underside connector": [design.housing() + design.plug()],
            "underside components": [design.components()],
            "pre-fed lead through the bracket": [design.lead(1.45, lift=float(z)) for z in np.linspace(0., design.SERVICE_LIFT, 5)],
            **{f"pilot {index}": [design.cylinder(0., y, design.BOARD_Z - design.PILOT_DEPTH + .25,
                                                  design.BOARD_Z - .07, .61)]
               for index, y in enumerate(design.HOLES, 1)},
        },
    }
    result = {}
    for part, checks in clearance.items():
        points = data[:, :3] + offset - objects[part]["vertices"].min(0)
        to_print = np.linalg.inv(np.asarray(manifest[part]["print_to_assembly"]))[:3, :]
        result[part] = {name: clearance_sections(
            data, points, shapes, to_print, checker,
            witness_width=3.2 if name == "pre-fed lead through the bracket" else 1.15)
                        for name, shapes in checks.items()}
    return result


def audit(archive, scratch, route_builder=routes):
    exports = scratch / "build-source" / "exports"
    plate.BRACKET = design.BRACKET
    result = inspect(archive, exports, route_builder, plate.read_json(scratch / "print-checks.json"),
                     removable_support=connector_support)
    for name, verify in (("travel_stop_bonds", verify_stops), ("rod_mount_bonds", verify_bonds)):
        result[name] = verify(archive, exports)
        if not result[name]["passed"]:
            result["failures"].append([name, "Deposited connection failed"])
    result["early_roots"] = audit_roots(archive, exports)
    result["early_roots"][design.BRACKET] = audit_grove_roots(archive, exports)
    for name, root in result["early_roots"].items():
        if not root["passed"]:
            result["failures"].append([name, "Early reinforcement or perforated pad check failed"])
    result["grove_clearance_sections"] = verify_grove_clearances(archive, exports)
    for part, checks in result["grove_clearance_sections"].items():
        for name, check in checks.items():
            if not check["passed"]:
                result["failures"].append([part, name, check])
    result["passed"] = not result["failures"]
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("scratch", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    result = audit(args.archive, args.scratch)
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    if not result["passed"]:
        raise SystemExit("See the R36 report for remaining printability issues.")
