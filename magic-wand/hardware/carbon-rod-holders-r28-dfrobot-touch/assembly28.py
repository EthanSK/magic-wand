#!/usr/bin/env python3
"""Export R28, run its fit checks and write the shared-viewer guide."""

import argparse
from copy import deepcopy
import json
import sys

import numpy as np
import trimesh

import holder28 as h
from assembly23 import relative_actor, translation

d, H, k27 = h.d, h.H, h.k27
OUT = h.OUT
SHARED = h.HERE.parent / "carbon-rod-holders" / "assembly"
R27_OUT = h.R27 / "exports"
SOURCE = R27_OUT / "assembly-guide.json"
sys.path.insert(0, str(SHARED))
from register_assembly import register_assembly, write_json  # noqa: E402

CARRIER, TRAY, KEEPER = "Key_Carrier", "DFRobot_Touch_Tray", "OP1_Rear_Keeper"
R27_X = {0: -18.7, 2: 18.7, 3: -13.05, 4: 13.05}
NEW_X = {0: -h.KEY_X, 2: h.KEY_X, 3: -h.KEY_X, 4: h.KEY_X}
TOUCH = ("sensor", "electrode", "connector")
SLIDE, PIN_OUT, LEAD_OFF = 42., 26., (0., 10., 5.)


def guide_mesh(name, solid):
    file = f"guide/{name}.stl"
    model = H.mesh(solid)
    assert model.is_watertight and model.is_winding_consistent, name
    model.export(OUT / file)
    return file


def export_parts(carrier):
    """Printable solids: assembly frame plus a rear-down print orientation."""
    H.OUT = OUT
    H.PRINT_ROT[TRAY] = H.PRINT_ROT[CARRIER]
    H.PRINT_ROT[KEEPER] = H.PRINT_ROT[CARRIER]
    shapes = {CARRIER: carrier, TRAY: h.cap(), KEEPER: k27.keeper()}
    return {name: H.export_part(name, shape, name) for name, shape in shapes.items()}


def squeezed_carrier():
    model = trimesh.load_mesh(OUT / f"{CARRIER}-assembly.stl", process=False)
    local = model.vertices - [0., h.CLICK_SHIFT, 0.]
    target = trimesh.Trimesh(model.vertices + d.flex(local), model.faces, process=False)
    file = "guide/carrier-squeezed.stl"
    target.export(OUT / file)
    assert np.array_equal(trimesh.load_mesh(OUT / file, process=False).faces, model.faces)
    return file


def cap_pose(angle=None, local=(0., 0., 0.), lift=0.):
    angle = -d.REST if angle is None else angle
    m = d.pose(angle)
    m[:, 3] += m[:, :3] @ np.asarray(local, float)
    m[1, 3] += h.CLICK_SHIFT
    m[2, 3] += lift
    return m.ravel().tolist()


def move(matrix, xyz):
    copy = list(matrix)
    for index, offset in zip((3, 7, 11), xyz):
        copy[index] += float(offset)
    return copy


def shift_keys(key, carrier_file):
    key["actors"]["carrier"]["file"] = carrier_file
    for step in key["steps"]:
        step.pop("checks", None)
        for frame in step["samples"]:
            for actor in key["actors"]:
                if actor.startswith(("switch_", "socket_")):
                    i = int(actor.split("_")[-1])
                    frame[actor] = move(frame[actor], (NEW_X[i] - R27_X[i], 0., 0.))
    return key


def touch_view(copper, key, files):
    actors = {name: deepcopy(copper["actors"][name]) for name in
              ("board", "sockets", "switch", "plunger", "plug", "op1_wire", "rod", "carrier",
               "op1_latch", "keeper_pin", "switch_0", "switch_2", "switch_3", "switch_4")}
    actors["carrier"].update(file=files["carrier"], morphFile=files["squeezed"])
    actors["op1_latch"].update(file=files["keeper"])
    actors["keeper_pin"].update(file=files["op1_pin"])
    actors["op1_wire"].update(file=files["op1_lead"])
    actors.update({
        "cap": {"label": "DFRobot touch tray", "file": files["tray"], "color": "#e19753", "cutaway": True},
        "sensor": {"label": "DFR0030 board (22 × 30 mm)", "file": files["sensor"], "color": "#303e39"},
        "electrode": {"label": "Gold touch pad", "file": files["electrode"], "color": "#ddba59"},
        "connector": {"label": "Gravity socket and plug (estimate)", "file": files["connector"], "color": "#e9e1d2"},
        "touch_pin": {"label": "1.75 mm filament board keeper", "file": files["touch_pin"], "color": "#ffdd68"},
        "sensor_lead": {"label": "Gravity lead slack", "file": files["lead"], "color": "#a7777a", "frame": False},
    })
    seated_keys = key["steps"][-1]["samples"][-1]
    op1 = np.array([[-1., 0., 0., 0.], [0., -1., 0., k27.BOARD_Y_OFFSET], [0., 0., 1., 0.]]).ravel().tolist()
    state = {name: translation() for name in actors}
    state.update({name: seated_keys[name] for name in actors if name.startswith("switch_")})
    for name in ("board", "sockets", "plug", "switch", "plunger"):
        state[name] = op1
    state["morphs"] = {"carrier": 0.}
    seated = deepcopy(state)
    state["cap"] = cap_pose(lift=8.)
    for name in TOUCH:
        state[name] = cap_pose(local=(0., SLIDE, 0.))
    state["touch_pin"] = cap_pose(local=(PIN_OUT, 0., 0.))
    state["sensor_lead"] = cap_pose(local=LEAD_OFF)
    for name in ("board", "sockets", "plug", "op1_wire"):
        state[name] = move(state[name], (0., 42., 0.))
    for name in ("switch", "plunger", "op1_latch"):
        state[name] = move(state[name], (0., 0., 8.))
    state["keeper_pin"] = translation(17.)
    steps = []

    def add(title, caption, frames, seconds=3, reveal=False):
        nonlocal state
        frames = list(frames)
        steps.append({"title": title, "caption": caption, "duration": seconds, "samples": frames,
                      **({"reveal": True} if reveal else {})})
        state = frames[-1]

    def slide(names, targets, n=25):
        start = {name: state[name] for name in names}
        frames = [{**state, **{name: [float(a + t * (b - a)) for a, b in zip(start[name], targets[name])]
                               for name in names}} for t in np.linspace(0., 1., n)]
        frames[-1] = {**state, **{name: list(targets[name]) for name in names}}
        return frames

    def cap_slide(names, start, end, n=25, angle=None):
        return [{**state, **{name: cap_pose(angle, local=tuple(np.add(start, t * np.subtract(end, start))))
                             for name in names}} for t in np.linspace(0., 1., n)]

    add("Slide In the OP1 Board", "Feed the stock OP1 board in from the two-key end, connector towards you, as on R27.",
        slide(("board", "sockets", "plug", "op1_wire"), seated), 4)
    add("Fit the Rear Keeper", "Lower the purple keeper behind the OP1 board.", slide(("op1_latch",), seated))
    add("Pin the Keeper", "Push a short piece of 1.75 mm filament across to trap the keeper.", slide(("keeper_pin",), seated))
    add("Plug in the Switch", "Press the microswitch down into its three sockets.", slide(("switch", "plunger"), seated))
    mounting = ([{**state, "morphs": {"carrier": float(t)}} for t in np.linspace(0., 1., 9)]
                + [{**state, "cap": cap_pose(lift=float(z)), "morphs": {"carrier": 1.}} for z in np.linspace(8., 0., 25)]
                + [{**state, "cap": cap_pose(), "morphs": {"carrier": float(t)}} for t in np.linspace(1., 0., 9)])
    add("Snap On the Empty Tray", "Pinch the two hinge arms, lower the empty orange tray onto the pins and let go.",
        mounting, 4, True)
    add("Slide In the Touch Board", "Gold face up, pad end first. Slide the DFR0030 in from the top under both rails until it meets the end stop at the bottom edge.",
        cap_slide(TOUCH, (0., SLIDE, 0.), (0., 0., 0.), 33), 4)
    add("Pin the Touch Board", "Push a 24 mm piece of 1.75 mm filament through both rear ears, behind the board.",
        cap_slide(("touch_pin",), (PIN_OUT, 0., 0.), (0., 0., 0.)))
    add("Plug In the Gravity Lead", "Plug the lead in at the top end and leave a loose loop behind the tray.",
        cap_slide(("sensor_lead",), LEAD_OFF, (0., 0., 0.), 18))
    group = ("cap", *TOUCH, "touch_pin", "sensor_lead")
    press = [{**state, **{name: cap_pose(float(a)) for name in group},
              "plunger": move(op1, (0., 0., -d.DEPRESSION * (1 + a / d.REST)))}
             for a in [*np.linspace(-d.REST, 0., 25), *np.linspace(0., -d.REST, 25)]]
    add("Touch, Click and Release", "Touch the gold face, then press. The two feet meet the stops at 0.48 mm of plunger travel. The switch spring lifts the tray back.",
        press, 5, True)
    service = len(steps)
    add("Unplug the Gravity Lead", "Unplug the lead before removing the board.",
        cap_slide(("sensor_lead",), (0., 0., 0.), LEAD_OFF, 18))
    add("Push Out the Keeper Pin", "Push the filament out sideways. It passes above the upper keycap.",
        cap_slide(("touch_pin",), (0., 0., 0.), (PIN_OUT, 0., 0.)))
    add("Slide Out the Touch Board", "Slide the board out towards the top. The tray stays on the wand.",
        cap_slide(TOUCH, (0., 0., 0.), (0., SLIDE, 0.), 33), 4)
    for item in reversed(steps[service:]):
        title = {"Unplug the Gravity Lead": "Reconnect the Lead", "Push Out the Keeper Pin": "Refit the Keeper Pin",
                 "Slide Out the Touch Board": "Slide the Board Back In"}[item["title"]]
        add(title, {"Reconnect the Lead": "Plug the lead back in with a loose loop.",
                    "Refit the Keeper Pin": "Push the filament back through both ears.",
                    "Slide the Board Back In": "Slide the board back down to the end stop."}[title],
            [{**state, **{k: v for k, v in frame.items() if k in group}} for frame in reversed(item["samples"])],
            item["duration"])
    for name in seated:
        if name not in group and name != "morphs":
            assert state[name] == seated[name] or name in ("plunger",), name
    return {"label": "DFRobot touch board", "openSeated": True, "rotation": [0., 0., 0.], "actors": actors, "steps": steps,
            "annotations": [
                {"side": "left", "actor": "cap", "point": [0., h.nose_y() + .35, 21.], "title": "Fixed end stop at the flat bottom"},
                {"side": "right", "actor": "touch_pin", "point": [h.CAP_HALF, h.layout(h.nose_y())["pin_y"], h.PIN_Z],
                 "title": "Filament pin keeps the board in"},
            ],
            "status": "CAD-checked candidate. Physical fit, print and touch response are untested.",
            "note": "DFR0030 V2 on R27's OP1 click. The tray's released front lines up with the Choc caps. Board thickness, plug and underside parts are estimates."}


def build(current):
    carrier, working = h.geometry()
    result = h.checks(carrier, working)
    print(json.dumps(result), flush=True)
    if not result["passed"]:
        raise ValueError(result)
    (OUT / "guide").mkdir(parents=True, exist_ok=True)
    parts = export_parts(carrier)
    files = {
        "carrier": f"{CARRIER}-assembly.stl", "tray": f"{TRAY}-assembly.stl", "keeper": f"{KEEPER}-assembly.stl",
        "squeezed": squeezed_carrier(),
        "op1_pin": guide_mesh("op1-keeper-pin", k27.pin()), "op1_lead": guide_mesh("op1-lead", k27.lead()),
        "sensor": guide_mesh("dfr0030-board", h.sensor()), "electrode": guide_mesh("dfr0030-pad", h.electrode()),
        "connector": guide_mesh("gravity-connector", h.connector()), "touch_pin": guide_mesh("board-keeper-pin", h.touch_pin()),
        "lead": guide_mesh("gravity-lead", h.gravity_lead()),
    }
    modules = json.loads(SOURCE.read_text())["modules"]
    copper = modules.pop("copper")
    for module in (*modules.values(), copper):
        module["actors"] = {name: relative_actor(actor, R27_OUT, OUT) for name, actor in module["actors"].items()}
    shift_keys(modules["key"], files["carrier"])
    modules["dfr"] = touch_view(copper, modules["key"], files)
    sha = H.sha
    write_json(OUT / "manifest.json", {
        "revision": h.REVISION, "physical_fit_verified": False, "print_validated": False,
        "purchased_board": "DFRobot DFR0030 Gravity Digital Capacitive Touch Sensor V2 (22 x 30 mm published)",
        "estimates": ["DFR0030 1.6 mm thickness", "Gravity socket/plug envelope (R26)", "DFR0030 underside parts",
                      "stock OP1 board, switch and plug (R23)", "Choc cap 16.6 x 17.5 mm reference"],
        "frames": {TRAY: "R26 cap frame; place with holder28.world(angle)", CARRIER: "assembly", KEEPER: "assembly"},
        "loose_hardware": ["1.75 mm filament, about 24 mm, DFR0030 keeper", "1.75 mm filament, about 14 mm, OP1 keeper (R27)"],
        "print_orientation_note": "SOURCE files are rear face down, like R26. Slicing and supports are not checked.",
        "source_sha256": {p.name: sha(p) for p in (h.HERE / "holder28.py", h.HERE / "assembly28.py")},
        "parts": parts,
    })
    write_json(OUT / "geometry-checks.json", {
        "revision": h.REVISION, "physical_fit_verified": False, "print_validated": False,
        "source_sha256": sha(h.HERE / "holder28.py"), "carrier_sha256": sha(OUT / files["carrier"]),
        "tray_sha256": sha(OUT / files["tray"]), "checks": result,
    })
    assets = {actor[field] for module in modules.values() for actor in module["actors"].values()
              for field in ("file", "morphFile") if field in actor}
    guide = OUT / "assembly-guide.json"
    write_json(guide, {"schema_version": 2, "units": "mm", "revision": h.REVISION, "physical_fit_verified": False,
                       "sources": {"r27_guide_sha256": sha(SOURCE), "generator_sha256": sha(__file__),
                                   "manifest_sha256": sha(OUT / "manifest.json"),
                                   "meshes_sha256": {file: sha(OUT / file) for file in sorted(assets)}},
                       "modules": modules})
    register_assembly(guide, "r28", "R28 DFRobot touch board", make_current=current, group_keys=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--make-current", action="store_true")
    build(parser.parse_args().make_current)
