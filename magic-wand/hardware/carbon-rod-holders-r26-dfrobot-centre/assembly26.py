#!/usr/bin/env python3
"""Animate the actual DFR0030 first-fit parts in the shared assembly viewer."""

import argparse
from copy import deepcopy
import json
import sys

import numpy as np
import trimesh

import holder26 as d
from assembly23 import relative_actor, translation
from audit26 import keeper_pin, lead

SHARED = d.HERE.parent / "carbon-rod-holders" / "assembly"
COLORS = {"paddle": "#e19753", "keeper": "#ea825f", "sensor": "#303e39",
          "electrode": "#ddba59", "connector": "#e9e1d2", "sensor_lead": "#a7777a", "pin": "#ffdd68",
          "op1_latch": "#a493d9"}
OP1 = ("board", "sockets", "switch", "plunger", "plug", "wire")
MOVING = ("paddle", "keeper", "sensor", "electrode", "connector", "sensor_lead", "pin")


def step(title, caption, frames, seconds=3):
    return {"title": title, "caption": caption, "duration": seconds, "samples": list(frames)}


def translate_steps(state, movers, before, after):
    return [{**state, **{name: translation(*xyz) for name in movers}}
            for xyz in np.linspace(before, after, 25)]


def assembly_matrix(*, angle=-d.REST, x=0., y=0., z=0.):
    motion = d.pose(angle)
    motion[:, 3] += [x, y, z]
    return motion.ravel().tolist()


def mesh_file(name, solid):
    file = f"guide/{name}.stl"
    d.mesh(solid).export(d.OUT / file)
    return file


def flex_file(part, deformation, file):
    path = d.OUT / f"{part}-assembly.stl"
    model = trimesh.load_mesh(path, process=False)
    target = trimesh.Trimesh(model.vertices + deformation(model.vertices), model.faces, process=False)
    target.export(d.OUT / file)
    written = trimesh.load_mesh(d.OUT / file, process=False)
    assert np.array_equal(written.faces, model.faces)
    return file


def add_dfr(module, keys):
    actors = {name: deepcopy(module["actors"][name]) for name in (*OP1, "rod", "carrier")}
    actors.update({name: deepcopy(actor) for name, actor in keys["actors"].items()
                   if name.startswith(("switch_", "socket_"))})
    for name in actors:
        if name.startswith("switch_"):
            actors[name]["frame"] = True
    actors["carrier"].update(file=f"{d.CARRIER}-assembly.stl",
                             morphFile=flex_file(d.CARRIER, d.flex, "guide/carrier-squeezed.stl"))
    refs = {
        "paddle": ("DFRobot paddle", f"{d.PADDLE}-assembly.stl"),
        "keeper": ("Removable DFRobot keeper", f"{d.KEEPER}-assembly.stl"),
        "sensor": ("DFR0030 board", mesh_file("dfr0030-pcb", d.sensor())),
        "electrode": ("Capacitive touch surface", mesh_file("dfr0030-electrode",
            d.box(-9.75, 9.75, -8.35, 4.77, 21.84, 21.92))),
        "connector": ("Gravity socket and plug clearance", mesh_file("dfr0030-connector", d.box(*d.CONNECTOR))),
        "sensor_lead": ("Gravity cable service loop", mesh_file("gravity-lead", lead())),
        "pin": ("1.75 mm filament keeper pin", mesh_file("keeper-pin", keeper_pin())),
        "op1_latch": ("Removable OP1 board latch", f"{d.OP1_LATCH}-assembly.stl"),
    }
    actors.update({name: {"label": label, "file": file, "color": COLORS[name],
                          "frame": name not in ("wire", "sensor_lead")}
                   for name, (label, file) in refs.items()})
    actors["op1_latch"]["morphFile"] = flex_file(d.OP1_LATCH, d.spread_latch, "guide/op1-latch-spread.stl")
    state = {name: translation() for name in actors}
    seated_keys = keys["steps"][-1]["samples"][-1]
    state.update({name: seated_keys[name] for name in actors if name.startswith(("switch_", "socket_"))})
    # The tray is assembled off the carrier. The moving hardware is drawn
    # at the printed alignment as it slides, then carried through the hinge.
    off = np.array([0., -39., 14.])
    state.update({name: translation(*off) for name in MOVING})
    sensor_group = ("sensor", "electrode", "connector")
    for name in (*sensor_group, "sensor_lead"):
        state[name] = translation(*(off + [0, -33, 0]))
    state["keeper"] = translation(*(off + [0, -7, 0]))
    state["pin"] = translation(*(off + [18, 0, 0]))
    state["op1_latch"] = translation(z=10.)
    steps = []

    def add(title, caption, frames, duration=3):
        nonlocal state
        frames = list(frames)
        steps.append(step(title, caption, frames, duration))
        state = frames[-1]

    add("Slide In the OP1 Board",
        "Plug the microswitch into its stock board. Slide it in with the white plug facing the tip.",
        translate_steps(state, OP1, (0, -33, 0), (0, 0, 0)))

    def latch_frames(start, height=7.):
        return ([{**start, "op1_latch": translation(z=height), "morphs": {"op1_latch": float(t)}}
                 for t in np.linspace(0, 1, 10)]
                + [{**start, "op1_latch": translation(z=float(z)), "morphs": {"op1_latch": 1.}}
                   for z in np.linspace(height, 0, 24)]
                + [{**start, "op1_latch": translation(), "morphs": {"op1_latch": float(t)}}
                   for t in np.linspace(1, 0, 10)])

    add("Clip In the OP1 Latch",
        "Spread the purple latch arms, lower them into the slots and let go. The blade sits in front of the board and above the plug.",
        latch_frames(state, height=10.), 4)
    add("Slide In the Touch Board",
        "Face the gold surface up. Slide the bare board in under the two rails, gold end first.",
        translate_steps(state, (*sensor_group, "sensor_lead"), off + [0, -33, 0], off))
    add("Lock the Front Keeper",
        "Put the keeper across the open end. Feed a roughly 16 mm piece of 1.75 mm filament through the three aligned holes.",
        [*translate_steps(state, ("keeper",), off + [0, -7, 0], off),
         *translate_steps({**state, "keeper": translation(*off)}, ("pin",), off + [18, 0, 0], off)], 4)
    add("Line Up the Snap Hinge",
        "Bring the tray above the switch. Leave the Gravity lead slack while you line up the two round pins.",
        [{**state, **{name: translation(*xyz) for name in MOVING}}
         for xyz in np.linspace(off, (0, 0, 6), 25)])
    add("Squeeze and Seat the Paddle",
        "Pinch both blue arms inward. Lower the orange hinge ears until their holes line up with the pins, then let go.",
        [{**state, "morphs": {"carrier": float(t)}} for t in np.linspace(0, 1, 10)]
        + [{**state, **{name: assembly_matrix(z=float(z), angle=0) for name in MOVING},
            "plunger": translation(z=-max(d.DEPRESSION - z, 0.)),
            "morphs": {"carrier": 1.}} for z in np.linspace(6, 0, 25)]
        + [{**state, **{name: assembly_matrix(angle=0) for name in MOVING},
            "plunger": translation(z=-d.DEPRESSION),
            "morphs": {"carrier": float(t)}} for t in np.linspace(1, 0, 10)], 5)
    add("Let the Switch Lift the Paddle",
        "The switch spring brings the paddle up. Leave enough slack that the cable can move with it.",
        [{**state, **{name: assembly_matrix(angle=float(angle)) for name in MOVING},
          "plunger": translation(z=-d.DEPRESSION * (1 + angle / d.REST))}
         for angle in np.linspace(0, -d.REST, 18)])
    add("Touch, Click and Release",
        "Touch the gold face. Press gently until the two feet meet the holder. The feet limit travel at the OP1 switch.",
        [{**state, **{name: assembly_matrix(angle=float(angle)) for name in MOVING},
          "plunger": translation(z=-d.DEPRESSION * (1 + angle / d.REST))}
         for angle in [*np.linspace(-d.REST, 0, 25), *np.linspace(0, -d.REST, 25)]], 5)
    add("Unclip the Paddle",
        "Unplug the Gravity lead. Pinch both arms inward again and lift the paddle off.",
        [{**state, "morphs": {"carrier": float(t)}} for t in np.linspace(0, 1, 10)]
        + [{**state, **{name: assembly_matrix(z=float(z)) for name in MOVING},
            "morphs": {"carrier": 1.}} for z in np.linspace(0, 8, 25)]
        + [{**state, **{name: assembly_matrix(z=8.) for name in MOVING},
            "morphs": {"carrier": float(t)}} for t in np.linspace(1, 0, 10)], 4)
    paddle_refit = steps[-1]["samples"]
    add("Release the OP1 Latch",
        "With the paddle lifted, spread the two purple arms and lift the latch.",
        reversed(latch_frames(state)), 4)
    latch_aside = translation(x=31., z=7.)
    board_service = [*translate_steps(state, ("op1_latch",), (0, 0, 7), (31, 0, 7)),
                     *translate_steps({**state, "op1_latch": latch_aside}, OP1, (0, 0, 0), (0, -33, 0))]
    add("Slide Out the OP1 Board",
        "Move the latch aside. Slide the OP1 board out towards the tip with its plug attached.", board_service, 4)
    add("Slide the OP1 Board Back In", "Guide the board all the way back into its two rails.",
        reversed(board_service), 3)
    add("Refit the OP1 Latch",
        "Clip the latch back over the two blue ears.",
        latch_frames(state), 3)
    # The viewer opens on the final frame. Leave the complete assembly seated.
    add("Assembled",
        "Both boards are held in place. The purple latch holds the OP1 board and the front keeper holds the touch board.",
        reversed(paddle_refit), 3)
    return {"label": "DFRobot centre click", "note": "DFR0030 V2, stock OP1 switch and four Choc V1 keys. Board height and plug shape are fit envelopes.",
            "rotation": [.92, 0, .34], "openSeated": True, "actors": actors, "steps": steps}


def build(current):
    sys.path.insert(0, str(SHARED))
    from register_assembly import register_assembly, write_json

    (d.OUT / "guide").mkdir(exist_ok=True)
    source = d.R25 / "exports" / "assembly-guide.json"
    modules = json.loads(source.read_text())["modules"]
    for module in modules.values():
        module["actors"] = {key: relative_actor(actor, source.parent, d.OUT)
                            for key, actor in module["actors"].items()}
    keys = modules["key"]
    keys["actors"]["carrier"]["file"] = f"{d.CARRIER}-assembly.stl"
    for key in d.LOWER_INDICES:
        for item in keys["steps"]:
            item.pop("checks", None)
            for frame in item["samples"]:
                for actor in (f"switch_{key}", f"socket_{key}"):
                    frame[actor][3] += (-1 if key == 0 else 1) * d.LOWER_SHIFT
    modules["dfr"] = add_dfr(modules["centre"], keys)
    # The earlier OP1 paddles and Cirque comparison remain available under R25.
    for key in ("centre", "centre_shallow", "centre_deep"):
        del modules[key]
    assets = {actor[field] for module in modules.values() for actor in module["actors"].values()
              for field in ("file", "morphFile") if field in actor}
    guide = {"schema_version": 2, "units": "mm", "revision": d.REVISION, "physical_fit_verified": False,
             "sources": {"r25_guide_sha256": d.h.sha(source), "manifest_sha256": d.h.sha(d.OUT / "manifest.json"),
                         "generator_sha256": d.h.sha(__file__),
                         "meshes_sha256": {file: d.h.sha(d.OUT / file) for file in sorted(assets)}},
             "modules": modules}
    path = d.OUT / "assembly-guide.json"
    write_json(path, guide)
    helper = d.OUT / "timelapse-tower.json"
    register_assembly(path, "r26", "R26 DFRobot and OP1 latch", make_current=current,
                      helper=helper if helper.is_file() else None, group_keys=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--make-current", action="store_true")
    build(parser.parse_args().make_current)
