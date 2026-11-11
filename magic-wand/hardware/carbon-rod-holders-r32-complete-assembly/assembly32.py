"""Build R32's top-loading OP1 carrier and its complete assembly guide."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil

import numpy as np

import holder32 as h
import assembly31 as a31

OUT = h.OUT
R31_OUT = h.R31 / "exports"
CARRIER = "Key_Carrier"
BOARD = ("board", "sockets", "housing")
PLUG = ("plug", "op1_wire")
SWITCH = ("switch", "terminals", "plunger")
OP1 = (*BOARD, *PLUG, *SWITCH, "fasteners")
DFR = ("cap", *a31.TOUCH, *a31.CLIPS, "sensor_lead")
IDENTITY = [1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0.]
move = a31.move


def guide_mesh(name, solid):
    name = f"guide/{name}.stl"
    mesh = h.H.mesh(solid)
    assert mesh.is_watertight and mesh.is_winding_consistent, name
    mesh.export(OUT / name)
    return name


def op1_actors():
    body, plunger = h.switch()
    shapes = {
        "board": (h.board(), "OP1 PCB with two mounting eyelets", "#208465"),
        "sockets": (h.sockets(), "Three underside socket barrels", "#c6a956"),
        "housing": (h.white_housing(), "Fixed white socket beneath the board", "#eae8df"),
        "plug": (h.plug(), "Removable underside plug", "#fff5de"),
        "op1_wire": (h.cable(), "Cable exit beside the rod", "#a3b8c5"),
        "switch": (body, "Omron 60M switch reference", "#302a42"),
        "terminals": (h.terminals(), "Three switch terminals", "#d5b68c"),
        "plunger": (plunger, "Offset switch plunger", "#eeae6d"),
        "fasteners": (h.screws(), "Two OP1 PCB screws", "#8294a3"),
    }
    return {name: {"file": guide_mesh(f"op1-{name}", mesh), "label": label, "color": color}
            for name, (mesh, label, color) in shapes.items()}


def op1_steps(view):
    original = deepcopy(view["steps"][2:])
    hinge_ready = original[0]["samples"][0]
    caps = {f"keycap_{i}": hinge_ready[f"switch_{i}"] for i in (3, 4)}
    final = {**hinge_ready, **{name: IDENTITY for name in OP1}, **caps}
    state = dict(final)
    for names, delta in ((BOARD, (0., 0., h.BOARD_RISE)), (PLUG, (0., 0., -9.)),
                         (SWITCH, (0., 0., 27.)), (("fasteners",), (0., 0., 20.)),
                         (DFR, (-48., 0., 0.)), (caps, (0., 0., 28.))):
        state.update({name: move(final[name], delta) for name in names})
    steps = []

    def seat(names, title, caption, seconds=3):
        nonlocal state
        frames = [{**state, **{name: [float(a + t * (b - a)) for a, b in zip(state[name], final[name])]
                              for name in names}} for t in np.linspace(0., 1., 25)]
        frames[-1] = {**state, **{name: list(final[name]) for name in names}}
        steps.append({"title": title, "caption": caption, "duration": seconds, "reveal": True, "samples": frames})
        state = frames[-1]

    seat(BOARD, "Seat the OP1 Board", "Leave the upper keycaps off. Lower the PCB onto the two small shoulders, with the white socket towards the side opening.", 4)
    seat(("fasteners",), "Secure the Board", "Use the two kit screws through the eyelets. Tighten gently until the board stops moving.")
    seat(PLUG, "Connect the Cable Underneath", "Push the plug up into the white socket. Guide the wire out through the opening beside the rod.")
    seat(SWITCH, "Seat the Mouse Switch", "Line up the three terminals and press the switch flush into the sockets. Face the small plunger towards the three-key row.")
    seat(caps, "Refit the Upper Keycaps", "Press the two upper keycaps onto their Choc stems.")
    seat(DFR, "Bring the Bracket Over the Supports", "Hold the touch-board bracket above the two fixed supports.")
    for step in original:
        for sample in step["samples"]:
            press_depth = sample["plunger"][11]
            sample.update({name: list(IDENTITY) for name in OP1})
            sample["plunger"] = move(IDENTITY, (0., 0., press_depth))
            sample.update(caps)
    return steps + original


def build(current):
    carrier, working = h.geometry()
    result = h.checks(carrier, working)
    print(json.dumps(result), flush=True)
    if not result["passed"]:
        raise ValueError("The new OP1 fit checks failed.")

    (OUT / "guide").mkdir(parents=True, exist_ok=True)
    old_manifest = json.loads((R31_OUT / "manifest.json").read_text())
    h.H.OUT = OUT
    carrier_part = h.H.export_part(CARRIER, carrier, CARRIER)
    parts = {**old_manifest["parts"], CARRIER: carrier_part}
    for name in parts:
        if name != CARRIER:
            for suffix in ("assembly", "SOURCE-REQUIRES-PREPARATION"):
                file = f"{name}-{suffix}.stl"
                shutil.copy2(R31_OUT / file, OUT / file)

    old = json.loads((R31_OUT / "assembly-guide.json").read_text())
    modules = old["modules"]
    for module in modules.values():
        module["actors"] = {name: a31.relative_actor(actor, R31_OUT, OUT) for name, actor in module["actors"].items()}
    for name in ("key", "dfr"):
        modules[name]["actors"]["carrier"]["file"] = f"{CARRIER}-assembly.stl"
    view = modules["dfr"]
    view["actors"].update(op1_actors())
    view["steps"] = op1_steps(view)
    view["status"] = "CAD fit checked with photo-derived PCB dimensions and the Omron 60M switch reference."
    view["note"] = "The OP1 board drops onto two mounting shoulders. The cable connects underneath beside the rod. The touch board uses the rear snap hinge and two post clips."
    view["annotations"] += [
        {"side": "left", "actor": "board", "point": [h.EYELETS[0] * np.sin(np.radians(-h.PCB_YAW)), h.ACTUATOR_Y + h.EYELETS[0] * np.cos(np.radians(-h.PCB_YAW)), h.PCB_TOP],
         "step": "Seat the OP1 Board", "title": "OP1 board mounting eyelet"},
    ]
    world_y = h.r31.AXIS_Y + h.CLICK_SHIFT
    modules["snap_hinge"]["actors"]["carrier"]["file"] = guide_mesh(
        "hinge-detail-key-holder", carrier ^ h.box(-7.6, 7.6, world_y - 3.1, world_y + 9., 10.9, 20.1))
    bom = json.loads((h.HERE / "complete-assembly.json").read_text())
    manifest = {**old_manifest, "revision": h.REVISION, "based_on": h.R31.name, "parts": parts,
                "change": "Top-loading OP1 PCB with two screw seats, an offset actuator reference and an open underside cable exit.",
                "loose_hardware": ["Two stock OP1 PCB screws"],
                "source_sha256": {p.name: h.H.sha(p) for p in (h.HERE / "holder32.py", Path(__file__), h.HERE / "complete-assembly.json")}}
    a31.write_json(OUT / "manifest.json", manifest)
    a31.write_json(OUT / "geometry-checks.json", {
        "revision": h.REVISION, "physical_fit_verified": False, "print_validated": False,
        "carrier_sha256": h.H.sha(OUT / f"{CARRIER}-assembly.stl"),
        "source_sha256": h.H.sha(h.HERE / "holder32.py"), "checks": result,
    })
    assets = {actor[field] for module in modules.values() for actor in module["actors"].values()
              for field in ("file", "morphFile") if field in actor}
    guide = OUT / "assembly-guide.json"
    a31.write_json(guide, {
        **old, "revision": h.REVISION, "modules": modules,
        "defaultViews": {"battery": "battery_spacer"} if "spacer" in bom["groups"] else {},
        "print_components": {key: item["parts"] for key, item in bom["groups"].items()},
        "sources": {"r31_guide_sha256": h.H.sha(R31_OUT / "assembly-guide.json"),
                    "generator_sha256": h.H.sha(__file__), "manifest_sha256": h.H.sha(OUT / "manifest.json"),
                    "meshes_sha256": {file: h.H.sha(OUT / file) for file in sorted(assets)}},
    })
    a31.register_assembly(guide, "r32", "R32 Complete assembly", make_current=current, group_keys=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--make-current", action="store_true")
    build(parser.parse_args().make_current)
