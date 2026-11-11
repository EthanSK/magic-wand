#!/usr/bin/env python3
"""Compose the R27 keys from the checked layout and the R26 foil animation."""

import argparse
from copy import deepcopy
import json
import sys

import numpy as np
import trimesh

import holder27 as h
from assembly23 import relative_actor, translation

OUT = h.HERE / "exports"
SHARED = h.HERE.parent / "carbon-rod-holders" / "assembly"
SOURCE = h.R26 / "exports" / "assembly-guide.json"
sys.path.insert(0, str(SHARED))
from register_assembly import register_assembly, write_json


def asset(name, solid):
    file = f"{name}.stl"
    model = h.mesh(solid)
    assert model.is_watertight and model.is_winding_consistent, name
    model.export(OUT / file)
    return file


def flex_asset(carrier_file):
    model = trimesh.load_mesh(OUT / carrier_file, process=False)
    local = model.vertices - [0., h.CLICK_SHIFT, 0.]
    target = trimesh.Trimesh(model.vertices + h.d.flex(local), model.faces, process=False)
    file = "carrier-squeezed.stl"
    target.export(OUT / file)
    assert np.array_equal(trimesh.load_mesh(OUT / file, process=False).faces, model.faces)
    return file


def shifted_keys(key, carrier_file):
    key["actors"]["carrier"]["file"] = carrier_file
    for step in key["steps"]:
        step.pop("checks", None)
        for frame in step["samples"]:
            for actor in key["actors"]:
                if not actor.startswith(("switch_", "socket_")):
                    continue
                dx, dy = h.key_shift(int(actor.split("_")[-1]))
                frame[actor][3] += dx
                frame[actor][7] += dy
    return key


def translate_actors(state, actors, start, end):
    return [{**state, **{name: move(state[name], delta) for name in actors}}
            for delta in np.linspace(start, end, 49)]


def move(matrix, xyz):
    copy = list(matrix)
    for index, offset in zip((3, 7, 11), xyz):
        copy[index] += float(offset)
    return copy


def compact_view(module, carrier_file):
    actors = module["actors"]
    actors["carrier"].update(file=carrier_file, morphFile=flex_asset(carrier_file))
    actors["op1_latch"] = {"file": asset("OP1_Rear_Keeper", h.keeper()),
                           "label": "Removable OP1 rear keeper", "color": "#a493d9"}
    actors["keeper_pin"] = {"file": asset("OP1_Keeper_Pin", h.pin()),
                            "label": "1.75 mm filament keeper pin", "color": "#ffdd68"}
    actors["op1_wire"]["file"] = asset("OP1_Lead", h.lead())
    actors["cap"]["file"] = asset("Aligned_Copper_Cap", h.centre_cap())
    board_set = ("board", "sockets", "plug", "op1_wire")
    click = ("switch", "plunger")
    board_transform = np.array([[-1., 0., 0., 0.], [0., -1., 0., h.BOARD_Y_OFFSET], [0., 0., 1., 0.]])
    for step in module["steps"]:
        for frame in step["samples"]:
            for actor in ("board", "sockets", "plug", *click):
                # Existing seated OP1 poses are identity except for plunger Z travel.
                frame[actor] = move(board_transform.ravel().tolist(), (0., 0., frame[actor][11]))
            for actor in (*h.c.CAP_PARTS, "terminal"):
                frame[actor] = move(frame[actor], (0., h.CLICK_SHIFT, 0.))
            for actor in actors:
                if actor.startswith("switch_"):
                    dx, dy = h.key_shift(int(actor.split("_")[-1]))
                    frame[actor] = move(frame[actor], (dx, dy, 0.))
            frame["keeper_pin"] = translation()
    # The carrier's front stays closed. The bare board and lead slide in from
    # the upper end before the switch is pushed in vertically ahead of the hinge.
    state = deepcopy(module["steps"][0]["samples"][0])
    for name in ("cap", "insert", "foil", "wire"):
        state[name] = move(state[name], (0., 0., 18.))
    prefix = []

    def add(title, caption, names, start, end, seconds=3):
        nonlocal state
        samples = translate_actors(state, names, start, end)
        prefix.append(dict(title=title, caption=caption, samples=samples, duration=seconds))
        state = samples[-1]

    switch_up, keeper_up, pin_out = (0., 0., 8.), (0., 0., 8.), (17., 0., 0.)
    first = state
    state = {**state, "switch": move(state["switch"], switch_up), "plunger": move(state["plunger"], switch_up),
             "op1_latch": move(state["op1_latch"], keeper_up), "keeper_pin": move(state["keeper_pin"], pin_out)}
    add("Slide in the OP1 Board", "Feed the switch board in from the two-key end, with the connector facing you.",
        board_set, (0., 42., 0.), (0., 0., 0.), 5)
    state = {**state, "op1_latch": first["op1_latch"]}
    add("Fit the Rear Keeper", "Lower the purple keeper until it meets the rear pin holes.",
        ("op1_latch",), keeper_up, (0., 0., 0.))
    state = {**state, "keeper_pin": first["keeper_pin"]}
    add("Pin the Keeper", "Push a short piece of 1.75 mm filament across to trap the keeper.",
        ("keeper_pin",), pin_out, (0., 0., 0.))
    state = {**state, "switch": first["switch"], "plunger": first["plunger"]}
    add("Plug in the Switch", "Press the microswitch down into its three sockets before fitting the cap.",
        click, switch_up, (0., 0., 0.))
    end = module["steps"][0]["samples"][0]
    lower = [{**state, **{name: move(end[name], (0., 0., z)) for name in h.c.CAP_PARTS}}
             for z in np.linspace(18., 0., 21)]
    prefix.append(dict(title="Prepare the Cap", caption="Fit the foil while the cap is off the wand.",
                       samples=lower, duration=2, reveal=True))
    module["steps"] = prefix + module["steps"]
    module["label"] = "Compact copper insert"
    module["note"] = "The three bottom caps line up when released. The OP1 connector faces the two-key top."
    module["rotation"] = [0., 0., 0.]
    return module


def build(current):
    carrier, working = h.geometry()
    result = h.checks(carrier, working)
    if not result["passed"]:
        raise ValueError(result)
    print(result, flush=True)
    OUT.mkdir(exist_ok=True)
    carrier_file = asset("Compact_Key_Carrier", carrier)
    modules = json.loads(SOURCE.read_text())["modules"]
    del modules["dfr"]
    for module in modules.values():
        module["actors"] = {name: relative_actor(actor, SOURCE.parent, OUT)
                            for name, actor in module["actors"].items()}
    shifted_keys(modules["key"], carrier_file)
    compact_view(modules["copper"], carrier_file)
    assets = {actor[field] for module in modules.values() for actor in module["actors"].values()
              for field in ("file", "morphFile") if field in actor}
    sha = h.d.h.sha
    write_json(OUT / "geometry-checks.json", {
        "revision": h.HERE.name, "physical_fit_verified": False, "print_validated": False,
        "source_sha256": sha(h.__file__), "carrier_sha256": sha(OUT / carrier_file), "checks": result,
    })
    guide = OUT / "assembly-guide.json"
    write_json(guide, {"schema_version": 2, "units": "mm", "revision": h.HERE.name,
                       "physical_fit_verified": False, "sources": {
                           "r26_guide_sha256": sha(SOURCE), "generator_sha256": sha(__file__),
                           "meshes_sha256": {file: sha(OUT / file) for file in sorted(assets)},
                       }, "modules": modules})
    register_assembly(guide, "r27", "R27 Compact copper insert", make_current=current, group_keys=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--make-current", action="store_true")
    build(parser.parse_args().make_current)
