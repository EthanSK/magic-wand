"""Export R37 with a visible, adjustable centre-click stop.

Run this before plate37.py. Pass --register after checking the print files.
"""

import argparse
from pathlib import Path

import numpy as np

import holder37 as design
import assembly36 as grove

HERE = Path(__file__).resolve().parent
OUT = HERE / "exports"
LABEL = "R37 Grove touch with adjustable OP1 stop"


def export():
    (OUT / "guide").mkdir(parents=True, exist_ok=True)
    grove.OUT = grove.a31.OUT = design.h.H.OUT = OUT
    grove.HERE = HERE
    grove.design = design
    design.h.H.PRINT_ROT[design.BRACKET] = grove.a31.trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])
    checks = design.checks()
    grove.a31.write_json(OUT / "geometry-checks.json", {
        "revision": HERE.name, "physical_fit_verified": False, "checks": checks,
    })
    if not checks["passed"]:
        raise ValueError("Adjustable stop failed a clearance, stroke or load-path check")
    carrier = design.carrier()
    manifest = {
        "revision": HERE.name, "based_on": design.R36.name,
        "parts": {name: design.h.H.export_part(name, solid, name) for name, solid in
                  ((grove.CARRIER, carrier), (design.BRACKET, design.bracket()))},
        "source_sha256": {p.name: design.h.H.sha(p) for p in
                          (Path(__file__), HERE / "holder37.py", HERE / "complete-assembly.json")},
    }
    grove.a31.write_json(OUT / "manifest.json", manifest)
    midpoint = checks["stop_settings"][len(checks["stop_settings"]) // 2]
    grove.write_guide(carrier, midpoint["nominal_plunger_travel_mm"], midpoint["angle_deg"])
    guide_path = OUT / "assembly-guide.json"
    guide = grove.old_assembly.prior.read(guide_path)
    full = guide["modules"]["dfr"]
    screw_file = grove.a31.guide_mesh("op1-adjustment-screw", design.stop_screw())
    full["actors"]["adjustment_screw"] = {"file": screw_file, "label": "M2×4 stop screw", "color": "#aeb4c1"}
    first_snap = next(i for i, step in enumerate(full["steps"])
                      if step["title"] == "Pinch the Bracket Arms")
    for index, step in enumerate(full["steps"]):
        for pose in step["samples"]:
            pose["adjustment_screw"] = pose["cap"] if index >= first_snap else grove.PARKED
    staged = full["steps"][first_snap]["samples"][0]
    samples = [{**staged, "adjustment_screw": grove.a31.move(staged["cap"], (0., 0., float(z)))}
               for z in np.linspace(-5., 0., 21)]
    full["steps"].insert(first_snap, {
        "title": "Set the OP1 Stop Screw",
        "caption": "Install the M2×4 socket-head screw from below before snapping the bracket in. Start 2¼ turns out from seated, then turn it in ⅛ turn at a time until the switch clicks and releases.",
        "duration": 3, "samples": samples, "reveal": True,
    })
    full["annotations"].append({
        "side": "right", "actor": "adjustment_screw", "point": [0., design.STOP_Y, design.STOP_BOSS_BOTTOM - 2.4],
        "step": "Set the OP1 Stop Screw", "title": "Adjustable hard stop",
    })
    full.update(label="Seeed Grove touch and adjustable OP1 click",
                status="CAD-checked travel range · set the screw for your switch",
                note="The centred screws hold the Grove board. The separate underside screw sets OP1 travel. The outer feet are backup stops.")
    guide["sources"]["meshes_sha256"][screw_file] = design.h.H.sha(OUT / screw_file)
    guide["sources"]["adjustable_stop_generator_sha256"] = design.h.H.sha(__file__)
    grove.a31.write_json(guide_path, guide)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register", action="store_true")
    if parser.parse_args().register:
        grove.a31.register_assembly(OUT / "assembly-guide.json", "r37", LABEL, make_current=True, group_keys=True)
    else:
        export()
