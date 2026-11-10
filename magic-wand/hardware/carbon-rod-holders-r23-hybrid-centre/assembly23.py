#!/usr/bin/env python3
"""Generate the shared Wand viewer's R23 recipe from its CAD meshes and motion.

The centre click uses the exported hinge geometry. The four Choc positions and
unchanged holders reuse the R22 guide. The CAD exporter calls this automatically.
"""

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import sys

import numpy as np


IDENTITY = [1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0.]
CHOC_KEYS = (0, 2, 3, 4)
PADDLES = {
    "centre": ("Centre_Paddle", "Centre Click · OP1"),
    "centre_shallow": ("Centre_Paddle_Shallow_Trial", "Centre Click · Shallow Paddle"),
    "centre_deep": ("Centre_Paddle_Deep_Trial", "Centre Click · Deep Paddle"),
}
XIAO_COMPONENTS = {
    "usb_c": ("USB-C shell", "#aeb8c1"),
    "shield": ("Radio shield", "#c7ccd2"),
    "antenna": ("Antenna", "#5260a0"),
    "pdm_microphone": ("Microphone", "#62666b"),
    "reset_button": ("Reset button", "#9a9390"),
    "user_led": ("User LED", "#f0ddb8"),
    "charge_led": ("Charge LED", "#e8c092"),
}


def translation(x: float = 0., y: float = 0., z: float = 0.) -> list[float]:
    pose = IDENTITY.copy()
    pose[3], pose[7], pose[11] = float(x), float(y), float(z)
    return pose


def relative_actor(record: dict, source: Path, target: Path) -> dict:
    return {**record, **{key: os.path.relpath((source / record[key]).resolve(strict=True), target)
                        for key in ("file", "morphFile") if key in record}}


def show_xiao_components(module: dict, current: Path, holder) -> None:
    """Draw the stock board's measured protrusions in its existing assembly frame."""
    # R17 records the measurements from Seeed's STEP and Sense outline. The
    # guide uses those same bounds without changing either printed mesh.
    board = holder.h22.h18.h17
    module["actors"]["board"].update(label="XIAO nRF52840 Sense board", color="#333b3d")
    for name, (label, color) in XIAO_COMPONENTS.items():
        file = f"guide/xiao_{name}.stl"
        holder.mesh(board.component_box(name)).export(current / file)
        module["actors"][f"board_{name}"] = {"label": label, "file": file, "color": color}
    module["note"] = "The board and its raised parts use Seeed's measured dimensions. Solder and fitted wires vary."
    for step in module["steps"]:
        if step["title"] == "Slide Onto the Rod":
            step["caption"] = "Slide the holder onto the rod end-first. The USB-C port, antenna and reset button stay accessible."
        for pose in step["samples"]:
            pose.update({f"board_{name}": pose["board"] for name in XIAO_COMPONENTS})


def reuse_modules(guide: dict, previous: Path, current: Path, carrier: Path, holder) -> dict:
    modules = guide["modules"]
    for module in modules.values():
        module["actors"] = {key: relative_actor(actor, previous, current)
                            for key, actor in module["actors"].items()}
    show_xiao_components(modules["xiao"], current, holder)
    key = modules["key"]
    key.update(label="Four Choc Keys · R23",
               note="Fit the four Choc switches here. Choose Centre Click to fit the OP1 board and paddle.")
    key["actors"]["carrier"].update(file=carrier.name, label="Key holder")
    removed = {"socket_1", "switch_1"}
    for actor in removed:
        del key["actors"][actor]
    key["steps"] = [step for step in key["steps"] if step["title"] != "Push Up the Middle Socket"]
    for step in key["steps"]:
        for sample in step["samples"]:
            for actor in removed:
                del sample[actor]
        if "seated_switch_overlap_mm3" in step.get("checks", {}):
            overlaps = step["checks"]["seated_switch_overlap_mm3"]
            step["checks"]["seated_switch_overlap_mm3"] = [overlaps[i] for i in CHOC_KEYS]

    battery = modules["battery"]
    del battery["actors"]["spacer"]
    battery["steps"] = [step for step in battery["steps"] if step["title"] != "Optional Spacer"]
    body = holder.h22.read(previous / "Battery_Holder-assembly.stl")
    cell = holder.h22.read(previous / "guide/lp402025_max_envelope.stl")
    for step in battery["steps"]:
        for sample in step["samples"]:
            del sample["spacer"]
            sample["cell"][11] = 0.
        if step["title"] == "Insert the Cell":
            step["caption"] = "Slide the cell in, leads last. Bring the leads through the centre opening."
            overlaps = [(body ^ cell.translate((0., pose["cell"][7], 0.))).volume()
                        for pose in step["samples"]]
            step["checks"] = {"max_overlap_mm3_rigid_max_envelope": round(max(overlaps), 4)}
            if max(overlaps) > .01:
                raise ValueError("Battery insertion without a spacer needs checking")
    trial = deepcopy(battery)
    trial["label"] = "Battery Holder · Easier Door"
    trial["actors"]["door"] = relative_actor({
        "label": "End door (easier trial)", "file": "Battery_End_Door_Easy_Trial-assembly.stl",
        "color": "#d9822b",
    }, previous, current)
    for step in trial["steps"]:
        if step["title"] == "Drop In the Door":
            step["caption"] = (
                "Push the easier door straight down into the same slots. "
                "Its shallower centre tooth takes less force to fit and holds less firmly."
            )
            door = holder.h22.read(previous / "Battery_End_Door_Easy_Trial-assembly.stl")
            overlaps = [(body ^ door.translate((0., 0., pose["door"][11]))).volume()
                        for pose in step["samples"]]
            if overlaps[-1] > .01:
                raise ValueError("Easier battery door does not seat")
            step["checks"] = {"max_overlap_mm3": round(max(overlaps), 4),
                              "seated_overlap_mm3": round(overlaps[-1], 4)}
    modules["battery_easy"] = trial
    return modules


def centre_module(motion: dict, key_module: dict, holder, variant: str, label: str) -> dict:
    """Show the front-slide path, pin, and click using the real carrier frame."""
    refs = motion["references"]
    parts = {
        "board": ("Stock OP1 board", "op1_board_envelope", "#208465"),
        "sockets": ("Socket pins", "op1_socket_barrels", "#c6a956"),
        "switch": ("Microswitch", "op1_switch_body", "#302a42"),
        "plunger": ("Switch plunger", "op1_switch_plunger_free", "#d85497"),
        "plug": ("White plug", "op1_white_plug_envelope", "#eae8df"),
        "wire": ("Cable route", "op1_pigtail_route", "#a3b8c5"),
        "pin": ("1.75 mm filament pin", "hinge_pin_1p75_filament", "#ffdd68"),
    }
    actors = {name: {"label": label, "file": refs[ref], "color": color}
              for name, (label, ref, color) in parts.items()}
    actors.update(carrier=key_module["actors"]["carrier"],
                  paddle={"label": "Click paddle", "file": f"{variant}-assembly.stl", "color": "#e19753"},
                  rod=key_module["actors"]["rod"])
    for index in CHOC_KEYS:
        name = f"switch_{index}"
        actors[name] = {**key_module["actors"][name], "frame": False}

    poses = motion["variants"][variant]["poses_deg"]
    tip_at_stop = holder.STOP_PLUNGER - holder.PD["variants"][variant]
    rest = poses["rest_on_plunger"]
    lifted = poses["released"]
    board_actors = ("board", "sockets", "switch", "plunger", "plug", "wire")
    state = {actor: IDENTITY for actor in actors}
    key_seated = key_module["steps"][-1]["samples"][-1]
    for index in CHOC_KEYS:
        state[f"switch_{index}"] = key_seated[f"switch_{index}"]
    for actor in board_actors:
        state[actor] = translation(y=-30.)
    state["pin"] = translation(x=-25.)

    def paddle_pose(angle: float, height: float = 0.) -> list[float]:
        pose = holder.pose_matrix(angle).reshape(-1).tolist()
        pose[11] += height
        return pose

    state["paddle"] = paddle_pose(lifted, 16.)
    steps = []

    def add(title: str, caption: str, duration: float, samples: list[dict]) -> None:
        steps.append({"title": title, "caption": caption, "duration": duration, "samples": samples})

    samples = []
    for y in np.linspace(-30., 0., 61):
        for actor in board_actors:
            state[actor] = translation(y=y)
        samples.append(state.copy())
    add("Slide In the Stock Board",
        "Plug the switch and white cable into the OP1 board. Slide the board in from the front with the paddle lifted away.",
        4., samples)

    samples = []
    for height in np.linspace(16., 0., 33):
        state["paddle"] = paddle_pose(lifted, height)
        samples.append(state.copy())
    add("Fit the Paddle", "Lower the paddle between the two hinge sides and line up the holes.", 3., samples)

    samples = []
    for x in np.linspace(-25., 0., 51):
        state["pin"] = translation(x=x)
        samples.append(state.copy())
    add("Slide In the Hinge Pin", "Use a short piece of 1.75 mm filament through both sides of the hinge.", 3., samples)

    samples = []
    for start, end in ((lifted, rest), (rest, 0.), (0., rest)):
        for angle in np.linspace(start, end, 25):
            state["paddle"] = paddle_pose(angle)
            tip = tip_at_stop + holder.lift_at(holder.YC, tip_at_stop, angle)
            state["plunger"] = translation(z=min(0., tip - holder.PLUNGER_FREE))
            samples.append(state.copy())
    add("Press and Release",
        "The small ridge presses the switch. The side stops take the load at the end of the press.",
        4., samples)
    add("Connect the Click",
        "Find COM and NO with a meter on the unplugged harness. Connect COM to GND and NO to D8 on the XIAO.",
        3., [state.copy()])
    return {"label": label,
            "note": "The printed parts use the R23 meshes. The OP1 board, plug and switch use estimated dimensions.",
            "actors": actors, "steps": steps}


def build(holder, make_current: bool = False) -> None:
    sys.path.insert(0, str(holder.HERE.parent / "carbon-rod-holders" / "assembly"))
    from register_assembly import register_assembly, write_json

    exports = holder.OUT
    previous = holder.R22 / "exports"
    source = previous / "assembly-guide.json"
    motion_path = exports / "centre-motion.json"
    motion = json.loads(motion_path.read_text())
    modules = reuse_modules(json.loads(source.read_text()), previous, exports,
                           exports / "Key_Carrier-assembly.stl", holder)
    centre = {key: centre_module(motion, modules["key"], holder, variant, label)
              for key, (variant, label) in PADDLES.items()}
    modules = {**centre, **modules}
    manifest_path = exports / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    mesh_hashes = {}
    for module in modules.values():
        for actor in module["actors"].values():
            for filename in (actor[key] for key in ("file", "morphFile") if key in actor):
                if filename not in mesh_hashes:
                    mesh_hashes[filename] = holder.sha(exports / filename)
    for name, record in manifest["parts"].items():
        if mesh_hashes.get(f"{name}-assembly.stl") != record["assembly_stl_sha256"]:
            raise ValueError(f"Assembly guide does not use the exported {name} mesh")
    guide = {"schema_version": 2, "units": "mm", "revision": holder.L["revision"],
             "physical_fit_verified": False,
             "sources": {"r22_assembly_guide_sha256": holder.sha(source),
                         "centre_motion_sha256": holder.sha(motion_path),
                         "manifest_sha256": holder.sha(manifest_path),
                         "generator_sha256": holder.sha(Path(__file__)), "meshes_sha256": mesh_hashes},
             "modules": modules}
    guide_path = exports / "assembly-guide.json"
    write_json(guide_path, guide)
    tower = exports / "timelapse-tower.json"
    register_assembly(guide_path, "r23", "R23 fit trial", make_current=make_current,
                      helper=tower if make_current else None)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--make-current", action="store_true")
    import holder23
    build(holder23, make_current=parser.parse_args().make_current)
