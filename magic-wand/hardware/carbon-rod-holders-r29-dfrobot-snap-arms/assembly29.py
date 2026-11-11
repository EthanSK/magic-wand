#!/usr/bin/env python3
"""Export R29, run its snap-arm checks and write the shared-viewer guide."""

import argparse
from copy import deepcopy
import json
import sys

import numpy as np
import trimesh

import holder29 as h
sys.path.insert(0, str(h.R28))
import assembly28 as a28  # noqa: E402
from assembly23 import relative_actor, translation  # noqa: E402

d, H, k27, h28 = h.d, h.H, h.k27, h.h28
OUT = h.OUT
R28_OUT = h.R28 / "exports"
SOURCE = R28_OUT / "assembly-guide.json"
register_assembly, write_json = a28.register_assembly, a28.write_json
cap_pose, move = a28.cap_pose, a28.move
CARRIER, TRAY, KEEPER = a28.CARRIER, a28.TRAY, a28.KEEPER
TOUCH, SLIDE, PIN_OUT, LEAD_OFF = a28.TOUCH, a28.SLIDE, a28.PIN_OUT, a28.LEAD_OFF


def guide_mesh(name, solid):
    file = f"guide/{name}.stl"
    model = H.mesh(solid)
    assert model.is_watertight and model.is_winding_consistent, name
    model.export(OUT / file)
    return file


def export_parts(carrier):
    H.OUT = OUT
    H.PRINT_ROT[TRAY] = H.PRINT_ROT[CARRIER]
    H.PRINT_ROT[KEEPER] = H.PRINT_ROT[CARRIER]
    shapes = {CARRIER: carrier, TRAY: h.cap(), KEEPER: k27.keeper()}
    return {name: H.export_part(name, shape, name) for name, shape in shapes.items()}


def pinched_tray(source, file):
    """Bend the exported tray's own arm vertices. Same faces, same order."""
    model = trimesh.load_mesh(OUT / source, process=False)
    target = trimesh.Trimesh(model.vertices + h.arm_bend(model.vertices), model.faces, process=False)
    target.export(OUT / file)
    written = trimesh.load_mesh(OUT / file, process=False)
    assert np.array_equal(written.faces, model.faces)
    moved = np.linalg.norm(written.vertices - model.vertices, axis=1)
    assert moved.max() > .8 and np.count_nonzero(moved) < len(moved), "only the arms bend"
    return file, int(np.count_nonzero(moved > 1e-6))


def touch_view(r28_dfr, files):
    actors = {name: deepcopy(actor) for name, actor in r28_dfr["actors"].items()}
    actors["carrier"] = {**actors["carrier"], "file": files["carrier"], "label": "Key holder with two fixed hinge supports"}
    actors["carrier"].pop("morphFile", None)
    actors["cap"] = {"label": "DFRobot touch tray with two flexible arms", "file": files["tray"],
                     "morphFile": files["pinched"], "color": "#e19753", "cutaway": True}
    actors["op1_latch"]["file"] = files["keeper"]
    actors["op1_latch"]["label"] = "OP1 board rear keeper (holds the OP1 board only)"
    actors["touch_pin"]["label"] = "1.75 mm filament board keeper (holds the DFR0030 only)"
    seated = r28_dfr["steps"][-1]["samples"][-1]
    state = {name: seated[name] for name in actors}
    state["morphs"] = {"cap": 0.}
    group = ("cap", *TOUCH, "touch_pin", "sensor_lead")
    op1 = seated["board"]
    # Start with the OP1 hardware out and the tray, board, pin and lead parked.
    for name in ("board", "sockets", "plug", "op1_wire"):
        state[name] = move(seated[name], (0., 42., 0.))
    for name in ("switch", "plunger", "op1_latch"):
        state[name] = move(seated[name], (0., 0., 8.))
    state["keeper_pin"] = move(seated["keeper_pin"], (17., 0., 0.))
    state["cap"] = cap_pose(lift=8.)
    for name in TOUCH:
        state[name] = cap_pose(local=(0., SLIDE, 0.))
    state["touch_pin"] = cap_pose(local=(PIN_OUT, 0., 0.))
    state["sensor_lead"] = cap_pose(local=LEAD_OFF)
    steps = []

    def add(title, caption, frames, seconds=3, reveal=False):
        nonlocal state
        frames = list(frames)
        steps.append({"title": title, "caption": caption, "duration": seconds, "samples": frames,
                      **({"reveal": True} if reveal else {})})
        state = frames[-1]

    def slide(names, n=25):
        start = {name: state[name] for name in names}
        frames = [{**state, **{name: [float(a + t * (b - a)) for a, b in zip(start[name], seated[name])] for name in names}}
                  for t in np.linspace(0., 1., n)]
        frames[-1] = {**state, **{name: list(seated[name]) for name in names}}
        return frames

    def cap_slide(names, start, end, n=25):
        return [{**state, **{name: cap_pose(local=tuple(np.add(start, t * np.subtract(end, start)))) for name in names}}
                for t in np.linspace(0., 1., n)]

    add("Slide In the OP1 Board", "Feed the stock OP1 board in from the two-key end, connector towards you, as on R27.",
        slide(("board", "sockets", "plug", "op1_wire")), 4)
    add("Fit the OP1 Rear Keeper", "Lower the purple keeper behind the OP1 board. It only holds the OP1 board.", slide(("op1_latch",)))
    add("Pin the OP1 Keeper", "Push a short piece of 1.75 mm filament across to trap the keeper.", slide(("keeper_pin",)))
    add("Plug in the Switch", "Press the microswitch down into its three sockets.", slide(("switch", "plunger")))

    def pinch(lift, a, b, n=10):
        return [{**state, "cap": cap_pose(lift=lift), "morphs": {"cap": float(t)}} for t in np.linspace(a, b, n)]

    def lower(a, b, n=25):
        return [{**state, "cap": cap_pose(lift=float(z)), "morphs": {"cap": 1.}} for z in np.linspace(a, b, n)]

    add("Pinch the Tray Arms", "Hold the empty tray above the holder. Pinch the two raised pads so both tabs pull inwards.",
        pinch(8., 0., 1.), 2, True)
    add("Lower Between the Supports", "Keep pinching and lower the tray. The two tabs pass between the two fixed supports.",
        lower(8., 0.), 3, True)
    add("Let the Tabs Snap Into the Holes", "Let go. Each arm springs back and its tab enters the hole in the support beside it.",
        pinch(0., 1., 0.), 2, True)
    add("Slide In the Touch Board", "Gold face up, pad end first. Slide the DFR0030 in from the top under both rails until it meets the end stop.",
        cap_slide(TOUCH, (0., SLIDE, 0.), (0., 0., 0.), 33), 4)
    add("Pin the Touch Board", "Push a 24 mm piece of 1.75 mm filament through both rear ears. It only holds the DFR0030.",
        cap_slide(("touch_pin",), (PIN_OUT, 0., 0.), (0., 0., 0.)))
    add("Plug In the Gravity Lead", "Plug the lead in at the top end and leave a loose loop behind the tray.",
        cap_slide(("sensor_lead",), LEAD_OFF, (0., 0., 0.), 18))
    press = [{**state, **{name: cap_pose(float(a)) for name in group},
              "plunger": move(op1, (0., 0., -d.DEPRESSION * (1 + a / d.REST)))}
             for a in [*np.linspace(-d.REST, 0., 25), *np.linspace(0., -d.REST, 25)]]
    add("Touch, Click and Release", "Press the gold face. The tray turns on the two tabs until its feet meet the stops at 0.48 mm of plunger travel.",
        press, 5, True)
    service = len(steps)
    add("Unplug the Gravity Lead", "Unplug the lead before removing the board.",
        cap_slide(("sensor_lead",), (0., 0., 0.), LEAD_OFF, 18))
    add("Push Out the Board Keeper", "Push the filament out sideways. It passes above the upper keycap.",
        cap_slide(("touch_pin",), (0., 0., 0.), (PIN_OUT, 0., 0.)))
    add("Slide Out the Touch Board", "Slide the board out towards the top. This uncovers the two pinch pads.",
        cap_slide(TOUCH, (0., 0., 0.), (0., SLIDE, 0.), 33), 4)
    add("Pinch to Release the Tabs", "Pinch both pads. The tabs pull out of the support holes.", pinch(0., 0., 1.), 2, True)
    add("Lift Off the Empty Tray", "Keep pinching and lift the tray straight up.", lower(0., 8.), 3, True)
    add("Pinch and Lower It Back", "To refit, pinch again and lower the tray between the supports.", lower(8., 0.), 3, True)
    add("Let the Tabs Snap Back In", "Let go so both tabs return into their holes.", pinch(0., 1., 0.), 2, True)
    refit = {"Slide Out the Touch Board": ("Slide the Board Back In", "Slide the board back down to the end stop."),
             "Push Out the Board Keeper": ("Refit the Board Keeper", "Push the filament back through both ears."),
             "Unplug the Gravity Lead": ("Reconnect the Lead", "Plug the lead back in with a loose loop.")}
    for item in reversed(steps[service:service + 3]):
        title, caption = refit[item["title"]]
        add(title, caption, [{**state, **{k: v for k, v in frame.items() if k in group}} for frame in reversed(item["samples"])],
            item["duration"])
    for name in actors:
        assert np.allclose(state[name], seated[name]), name
    return {**r28_dfr, "label": "DFRobot touch board · snap arms", "actors": actors, "steps": steps,
            "annotations": [
                {"side": "left", "actor": "cap", "point": [-h.TAB_TIP, h.AXIS_Y, h.AXIS_Z],
                 "title": "Left tab enters the left support hole"},
                {"side": "right", "actor": "cap", "point": [h.TAB_TIP, h.AXIS_Y, h.AXIS_Z],
                 "title": "Right tab enters the right support hole"},
                {"side": "right", "actor": "carrier", "point": [h.SUPPORT_X[1], h.AXIS_Y + h.CLICK_SHIFT, h.SUPPORT_TOP],
                 "title": "Fixed support on the key holder"},
            ],
            "status": "CAD-checked candidate. Arm flex, print and touch response are untested.",
            "note": "Two flexible tray arms with outward tabs snap into two fixed supports on R27's hinge axis. The OP1 keeper and the board keeper are separate."}


def hinge_view(carrier, full):
    """Show the integral tabs and their matching holes from the same CAD and poses."""
    world_y = h.AXIS_Y + h.CLICK_SHIFT
    bracket = guide_mesh("hinge-detail-key-holder",
                         carrier ^ h.box(-7.6, 7.6, world_y - 3.1, world_y + 9., 10.9, 20.1))
    arms = guide_mesh("hinge-detail-tray", h.cap() ^ h.box(-7.6, 7.6, 3.5, 18.8, 16.8, 20.25))
    bent, _ = pinched_tray(arms, "guide/hinge-detail-tray-pinched.stl")
    actors = {
        "carrier": {**full["actors"]["carrier"], "file": bracket},
        "cap": {**full["actors"]["cap"], "file": arms, "morphFile": bent, "cutaway": False},
    }
    # Replay the checked full-assembly poses with the board hardware out of view.
    steps = []
    for step in full["steps"]:
        if not all("cap" in sample.get("morphs", {}) for sample in step["samples"]):
            continue
        if not any(sample["morphs"]["cap"] > 0 for sample in step["samples"]):
            continue
        samples = [{name: sample[name] for name in (*actors, "morphs")} for sample in step["samples"]]
        steps.append({**step, "samples": samples})
    return {
        "label": "Snap hinge",
        "rotation": [.7, 0., -.46],
        "actors": actors,
        "steps": steps,
        "annotations": [
            {"side": "left", "actor": "cap", "point": [-h.TAB_TIP, h.AXIS_Y, h.AXIS_Z],
             "title": "Tab on the tray arm"},
            {"side": "right", "actor": "carrier", "point": [h.SUPPORT_X[1], world_y, h.AXIS_Z],
             "title": "Hole in the fixed support"},
        ],
        "note": "Cutaway of the key holder and empty touch tray. Pinch the arms to fit or remove the tray.",
    }


def build(current):
    carrier, working = h.geometry()
    result = h.checks(carrier, working)
    print(json.dumps(result), flush=True)
    if not result["passed"]:
        raise ValueError(result)
    (OUT / "guide").mkdir(parents=True, exist_ok=True)
    parts = export_parts(carrier)
    pinched, bent_vertices = pinched_tray(f"{TRAY}-assembly.stl", "guide/tray-arms-pinched.stl")
    result["guide_pinched_tray_moved_vertices"] = bent_vertices
    files = {"carrier": f"{CARRIER}-assembly.stl", "tray": f"{TRAY}-assembly.stl",
             "keeper": f"{KEEPER}-assembly.stl", "pinched": pinched}
    source = json.loads(SOURCE.read_text())["modules"]
    for module in source.values():
        module["actors"] = {name: relative_actor(actor, R28_OUT, OUT) for name, actor in module["actors"].items()}
    source["key"]["actors"]["carrier"]["file"] = files["carrier"]
    source["dfr"] = touch_view(source["dfr"], files)
    source["snap_hinge"] = hinge_view(carrier, source["dfr"])
    sha = H.sha
    write_json(OUT / "manifest.json", {
        "revision": h.REVISION, "physical_fit_verified": False, "print_validated": False,
        "based_on": h28.REVISION, "change": "Hinge ownership reversed: fixed bored supports on the key holder, flexible tabbed arms on the tray.",
        "frames": {TRAY: "R26 cap frame; place with holder28.world(angle)", CARRIER: "assembly", KEEPER: "assembly"},
        "loose_hardware": ["1.75 mm filament, about 24 mm, DFR0030 keeper", "1.75 mm filament, about 14 mm, OP1 keeper (R27)"],
        "print_orientation_note": "SOURCE files are rear face down, like R26. Slicing, supports and arm flex are not checked.",
        "source_sha256": {p.name: sha(p) for p in (h.HERE / "holder29.py", h.HERE / "assembly29.py")},
        "parts": parts,
    })
    write_json(OUT / "geometry-checks.json", {
        "revision": h.REVISION, "physical_fit_verified": False, "print_validated": False,
        "source_sha256": sha(h.HERE / "holder29.py"), "carrier_sha256": sha(OUT / files["carrier"]),
        "tray_sha256": sha(OUT / files["tray"]), "pinched_tray_sha256": sha(OUT / pinched), "checks": result,
    })
    assets = {actor[field] for module in source.values() for actor in module["actors"].values()
              for field in ("file", "morphFile") if field in actor}
    guide = OUT / "assembly-guide.json"
    write_json(guide, {"schema_version": 2, "units": "mm", "revision": h.REVISION, "physical_fit_verified": False,
                       "sources": {"r28_guide_sha256": sha(SOURCE), "generator_sha256": sha(__file__),
                                   "manifest_sha256": sha(OUT / "manifest.json"),
                                   "meshes_sha256": {file: sha(OUT / file) for file in sorted(assets)}},
                       "modules": source})
    register_assembly(guide, "r29", "R29 DFRobot snap arms", make_current=current, group_keys=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--make-current", action="store_true")
    build(parser.parse_args().make_current)
