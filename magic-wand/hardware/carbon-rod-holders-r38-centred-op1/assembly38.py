"""Check and export R38, then write its revision-local assembly guide.

Run through the geometry budget runner. Registration in the shared viewer
catalogue is a separate step: pass --register once the plate is cleared.
"""

import argparse
from copy import deepcopy
from pathlib import Path

import numpy as np

import holder38 as design
import assembly37 as before

HERE = Path(__file__).resolve().parent
OUT = HERE / "exports"
SOURCE = design.R37 / "exports"
LABEL = "R38 Centred OP1 click"
CARRIER, BRACKET = design.CARRIER, design.BRACKET
grove = before.grove          # assembly36 helpers
a31 = grove.a31
r = design.r
read = grove.old_assembly.prior.read
OP1_BOARD = ("board", "sockets", "housing")
OP1_PLUG = ("plug", "op1_wire")
MOVING = ("cap", "sensor", "electrode", "connector", "sensor_parts", "sensor_plug",
          "grove_screw_front", "grove_screw_rear", "sensor_lead", "adjustment_screw")
IDENTITY = [1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0.]


def lerp(a, b, t):
    return [float(p + t * (q - p)) for p, q in zip(a, b)]


def op1_steps(full):
    """Plug the harness in first, then lower the wired board from above."""
    steps = full["steps"]
    titles = [step["title"] for step in steps]
    first, second, third = (titles.index(name) for name in
                            ("Seat the OP1 Board", "Secure the Board", "Connect the Cable Underneath"))
    assert (first, second, third) == (0, 1, 2)
    start = deepcopy(steps[0]["samples"][0])
    done = steps[2]["samples"][-1]
    high = a31.move(IDENTITY, (0., 0., design.h32.BOARD_RISE))
    apart = a31.move(high, (0., 0., -9.))
    start.update({name: high for name in OP1_BOARD}, **{name: apart for name in OP1_PLUG})

    def stage(title, caption, changes, state):
        frames = [{**state, **{name: lerp(a, b, t) for name, (a, b) in changes.items()}}
                  for t in np.linspace(0., 1., 25)]
        return {"title": title, "caption": caption, "duration": 3, "reveal": True, "samples": frames}, frames[-1]

    # Cleanup is an instruction at the initial pose, not an invented removal animation.
    cleanup, _ = stage(
        "Remove Print Supports",
        "Cut the narrow pad ties. Break the central support into small pieces and remove them through the empty PCB opening. Clear support inside the rod bore through its open rear end. Remove the outer finger-guard support outwards. Check the full rod bore, plug passage and cable passage are clear before fitting electronics or sliding the holder onto the rod.",
        {}, start)
    plug_in, state = stage(
        "Plug In the OP1 Harness",
        "Off the holder, connect the two-wire lead to the socket under the OP1 board. Keep the lead coming out from the end of the plug.",
        {name: (apart, high) for name in OP1_PLUG}, start)
    lower, state = stage(
        "Lower the Wired OP1 Board",
        "Leave the upper keycaps off. Feed the lead through the opening, turn it beside the rod, then lower the board onto its two seats. Check the real lead can bend this way without being pinched or forced.",
        {name: (high, IDENTITY) for name in (*OP1_BOARD, *OP1_PLUG)}, state)
    secure, state = stage(
        "Secure the Board",
        "Fit the two kit screws through the eyelets. Tighten gently until the board stops moving.",
        {"fasteners": (state["fasteners"], done["fasteners"])}, state)
    for name in (*OP1_BOARD, *OP1_PLUG, "fasteners"):
        assert np.allclose(state[name], done[name]), name
    full["steps"] = [cleanup, plug_in, lower, secure, *steps[3:]]


def click_step(full, travel, stop_angle):
    step = next(item for item in full["steps"] if item["title"] == "Touch, Click and Release")
    state = step["samples"][0]
    still = a31.move(state["plunger"], (0., 0., -state["plunger"][11]))
    angles = [*np.linspace(-r.REST, stop_angle, 25), *np.linspace(stop_angle, -r.REST, 25)]
    step["samples"] = [
        {**state, **{name: grove.placement(angle=float(angle)) for name in MOVING},
         "plunger": a31.move(still, (0., 0., -max(0., travel + r.d.DEPRESSION * (angle - stop_angle) / r.REST)))}
        for angle in angles]


def shift_keys(modules):
    """Move every Choc socket, switch and keycap pose with its seat."""
    for module in (modules["key"], modules["dfr"]):
        for step in module["steps"]:
            for sample in step["samples"]:
                for name, pose in sample.items():
                    if name.rsplit("_", 1)[0] in ("socket", "switch", "keycap") and name[-1] in "0234":
                        side = -1. if name[-1] in "03" else 1.
                        sample[name] = a31.move(pose, (-side * design.KEY_SHIFT, 0., 0.))


def write_guide(key, checks):
    guide = read(SOURCE / "assembly-guide.json")
    modules = guide["modules"]
    modules.pop("battery_spacer", None)
    guide.setdefault("defaultViews", {})["battery"] = "battery"
    for module in modules.values():
        module["actors"] = {name: a31.relative_actor(actor, SOURCE, OUT) for name, actor in module["actors"].items()}
    for name in ("key", "dfr"):
        modules[name]["actors"]["carrier"]["file"] = f"{CARRIER}-assembly.stl"
    morph, _ = a31.pinched(f"{BRACKET}-assembly.stl", "guide/grove-bracket-pinched.stl")
    full = modules["dfr"]
    for name in ("dfr", "snap_hinge"):
        modules[name]["actors"]["cap"].update(file=f"{BRACKET}-assembly.stl", morphFile=morph)
    for name, solid in design.hardware().items():
        full["actors"][name]["file"] = a31.guide_mesh(f"op1-{name}", solid)
    full["actors"]["op1_wire"]["label"] = "Harness folded round the rod"
    for name, solid in (
        ("sensor", design.board()), ("electrode", design.electrode()), ("connector", design.housing()),
        ("sensor_parts", design.components()), ("sensor_plug", design.plug()), ("sensor_lead", design.lead()),
        ("grove_screw_front", design.fastener(design.HOLES[0])),
        ("grove_screw_rear", design.fastener(design.HOLES[1])),
    ):
        full["actors"][name]["file"] = a31.guide_mesh(name, solid)
    # Same stretch as R36: the lead above its first bend follows the lifted board.
    lead = a31.trimesh.load_mesh(OUT / full["actors"]["sensor_lead"]["file"], process=False)
    lower = design.BOARD_Z - 12.15
    stretch = np.clip((lead.vertices[:, 2] - lower) / (12.15 - 9.8), 0., 1.)
    lead.vertices[:, 2] += design.SERVICE_LIFT * stretch
    lead.export(OUT / "guide/sensor-lead-fed.stl")
    full["actors"]["sensor_lead"]["morphFile"] = "guide/sensor-lead-fed.stl"
    full["actors"]["adjustment_screw"]["file"] = a31.guide_mesh("op1-adjustment-screw", design.stop_screw())
    pivot = r.AXIS_Y + r.CLICK_SHIFT
    detail = key ^ design.box(-7.6, 7.6, pivot - 3.1, pivot + 9., 10.9, 20.1)
    modules["snap_hinge"]["actors"]["carrier"]["file"] = a31.guide_mesh("grove-hinge-detail", detail)

    op1_steps(full)
    middle = checks["stop_settings"][len(checks["stop_settings"]) // 2]
    click_step(full, middle["nominal_plunger_travel_mm"], middle["angle_deg"])
    shift_keys(modules)
    h32 = design.h32
    gx, gz = design.GROVE_X, design.BOARD_Z
    points = {
        "OP1 board mounting eyelet": [design.PCB_X, h32.ACTUATOR_Y + h32.EYELETS[0], h32.PCB_TOP + design.OP1_LIFT],
        "Adjustable hard stop": [design.STOP_X, design.STOP_Y, design.STOP_BOSS_BOTTOM - 2.4],
        "Centred screw at the two-key end": [gx, design.HOLES[1], gz + 1.6],
        "Centred screw at the three-key end": [gx, design.HOLES[0], gz + 1.6],
        "Underboard plug on the left of the rod": [gx - 6.1, design.BOARD_Y, gz - 7.7],
        "Touch pad, offset by the board layout": [gx + 1.6, design.BOARD_Y, gz + 1.68],
    }
    retitle = {"Centred screw at the two-key end": "Grove screw at the two-key end",
               "Centred screw at the three-key end": "Grove screw at the three-key end",
               "Underboard plug on the left of the rod": "Grove plug beside the OP1 board",
               "Touch pad, offset by the board layout": "Touch pad over the rod"}
    for note in full["annotations"]:
        if note["title"] in points:
            note["point"] = points[note["title"]]
            if note["title"] == "OP1 board mounting eyelet":
                note["step"] = "Lower the Wired OP1 Board"
            note["title"] = retitle.get(note["title"], note["title"])
    full.update(label="Centred OP1 click under the Grove touch board",
                status="CAD-checked assembly · physical fit unverified",
                note="The OP1 board sits over the rod on a seat 0.9 mm higher than R37. The Grove board sits "
                     "2 mm to the left and 0.9 mm higher so its plug passes beside the OP1 board. "
                     "The stop screw moves to the right of the board.")
    guide["print_components"] = {name: group["parts"] for name, group in
                                 read(HERE / "complete-assembly.json")["groups"].items()}
    files = {actor[k] for module in modules.values() for actor in module["actors"].values()
             for k in ("file", "morphFile") if k in actor}
    guide.update(revision=HERE.name, physical_fit_verified=False, sources={
        "r37_guide_sha256": design.H.sha(SOURCE / "assembly-guide.json"),
        "generator_sha256": design.H.sha(__file__),
        "manifest_sha256": design.H.sha(OUT / "manifest.json"),
        "meshes_sha256": {name: design.H.sha(OUT / name) for name in sorted(files)},
    })
    a31.write_json(OUT / "assembly-guide.json", guide)


def comparison(parts):
    old = read(SOURCE / "manifest.json")["parts"]
    rows = {}
    for name, new in parts.items():
        was = old[name]
        size = lambda part: (np.asarray(part["assembly_bounds_mm"][1]) - np.asarray(part["assembly_bounds_mm"][0]))
        a, b = size(was), size(new)
        rows[name] = {
            "r37_size_xyz_mm": np.round(a, 3).tolist(), "r38_size_xyz_mm": np.round(b, 3).tolist(),
            "size_change_xyz_mm": np.round(b - a, 3).tolist(),
            "r37_volume_mm3": was["volume_mm3"], "r38_volume_mm3": new["volume_mm3"],
            "r37_solid_PETG_g": was["solid_PETG_g"], "r38_solid_PETG_g": new["solid_PETG_g"],
            "solid_PETG_change_g": round(new["solid_PETG_g"] - was["solid_PETG_g"], 3),
        }
    rows["both_parts_solid_PETG_change_g"] = round(sum(
        row["solid_PETG_change_g"] for row in rows.values()), 3)
    rows["basis"] = "Solid mesh volume at 1.27 g/cm3 from both manifests. Sliced mass with pads is not measured."
    return rows


def export():
    (OUT / "guide").mkdir(parents=True, exist_ok=True)
    grove.OUT = a31.OUT = design.H.OUT = OUT
    design.H.PRINT_ROT[BRACKET] = a31.trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])
    checks = design.checks()
    key = design.carrier()
    parts = {name: design.H.export_part(name, solid, name)
             for name, solid in ((CARRIER, key), (BRACKET, design.bracket()))}
    report = {"revision": HERE.name, "units": "mm", "physical_fit_verified": False,
              "sliced": False, "print_cleared": False,
              "compared_with_r37": comparison(parts), "checks": checks}
    a31.write_json(OUT / "geometry-checks.json", report)
    if not checks["passed"]:
        raise ValueError("R38 failed a clearance, stroke, reference or load-path check")
    a31.write_json(OUT / "manifest.json", {
        "revision": HERE.name, "based_on": design.R37.name, "units": "mm", "parts": parts,
        "frames": {CARRIER: "assembly", BRACKET: "bracket frame at the hard stop; place with holder31.world(angle)"},
        "change": "OP1 board on the rod centre line on a 0.9 mm higher seat. Grove board 2 mm left and 0.9 mm higher. "
                  "Stop screw beside the board. Choc seats 0.1 mm closer on each side.",
        "physical_fit_verified": False, "print_cleared": False,
        "source_sha256": {p.name: design.H.sha(p) for p in
                          (Path(__file__), HERE / "holder38.py", HERE / "complete-assembly.json")},
    })
    write_guide(key, checks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register", action="store_true")
    if parser.parse_args().register:
        a31.register_assembly(OUT / "assembly-guide.json", "r38", LABEL, make_current=True, group_keys=True)
    else:
        export()
