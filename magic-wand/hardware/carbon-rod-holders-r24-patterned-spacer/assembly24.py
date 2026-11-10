#!/usr/bin/env python3
"""Compose R24's changed assembly parts with the checked R23 recipes."""

import argparse
import json
import os
import sys

import manifold3d as mf
import numpy as np

import spacer24 as spacer_model
from assembly23 import relative_actor

h = spacer_model.h
OUT = spacer_model.HERE / "exports"


def battery_leads():
    cell = h.base.cell_shape()
    near = cell.bounding_box()[1]
    paths = {}
    for name, x, color in (("positive", -1., "#b9453d"), ("negative", 1., "#303239")):
        points = [(x, near + .1, 7.9), (x, -16.6, 7.9), (x, -18.6, 8.8), (x, -20., 11.4)]
        balls = [mf.Manifold.sphere(.65, 24).translate(point) for point in points]
        wire = h.union(mf.Manifold.batch_hull([a, b]) for a, b in zip(balls, balls[1:]))
        file = f"guide/battery_{name}_lead.stl"
        h.mesh(wire).export(OUT / file)
        paths[name] = (file, color, wire)
    return paths


def show_leads(module, leads):
    body = h.h22.read((OUT / module["actors"]["holder"]["file"]).resolve(strict=True))
    door = h.h22.read((OUT / module["actors"]["door"]["file"]).resolve(strict=True))
    for name, (file, color, wire) in leads.items():
        module["actors"][name] = {"label": f"Battery {name} lead (illustrative)", "file": file, "color": color}
        for step in module["steps"]:
            for sample in step["samples"]:
                sample[name] = sample["cell"]
                moving = wire.transform(np.asarray(sample["cell"]).reshape(3, 4))
                moving_door = door.transform(np.asarray(sample["door"]).reshape(3, 4))
                assert h.vol(moving ^ body) < .005 and h.vol(moving ^ moving_door) < .005, step["title"]


def add_spacer(modules, manifest, name):
    previous = h.R22 / "exports"
    prior = json.loads((previous / "assembly-guide.json").read_text())
    module = prior["modules"]["battery"]
    module["actors"] = {key: relative_actor(actor, previous, OUT)
                        for key, actor in module["actors"].items()}
    file = f"spacer/{name}-assembly.stl"
    shape = h.h22.read(OUT / file)
    bounds = shape.bounding_box()
    thickness = float(bounds[5] - bounds[2])
    assert h.sha(OUT / file) == manifest["parts"][name]["assembly_stl_sha256"]
    module["label"] = "Battery Holder · Patterned Spacer"
    module["note"] = "Use the patterned layer only if the battery still slides in easily."
    module["actors"]["spacer"].update(file=file, label=f"Patterned spacer ({thickness:.2g} mm)")
    for step in module["steps"]:
        for sample in step["samples"]:
            sample["cell"][11] = thickness
        if step["title"] == "Optional Spacer":
            step["title"] = "Slide In the Patterned Spacer"
            step["caption"] = "Slide the patterned layer along the floor before inserting the battery."
        if step["title"] == "Insert the Cell":
            step["caption"] = "Slide the battery in end-first. Feed the two leads through the open arch."
    modules["battery_spacer"] = module


def build(make_current):
    source = spacer_model.R23 / "exports" / "assembly-guide.json"
    prior = json.loads(source.read_text())
    modules = prior["modules"]
    del modules["cable"]
    for module in modules.values():
        module["actors"] = {key: relative_actor(actor, source.parent, OUT)
                            for key, actor in module["actors"].items()}
    spacer_path = spacer_model.OUT / "manifest.json"
    spacer = json.loads(spacer_path.read_text())
    name, = spacer["parts"]
    add_spacer(modules, spacer, name)
    (OUT / "guide").mkdir(exist_ok=True)
    leads = battery_leads()
    for key in ("battery", "battery_easy", "battery_spacer"):
        show_leads(modules[key], leads)
    assets = {actor[key] for module in modules.values() for actor in module["actors"].values()
              for key in ("file", "morphFile") if key in actor}
    hashes = {file: h.sha(OUT / file) for file in sorted(assets)}
    guide = {"schema_version": 2, "units": "mm", "revision": spacer["revision"],
             "physical_fit_verified": False,
             "sources": {"r23_guide_sha256": h.sha(source),
                         "spacer_manifest_sha256": h.sha(spacer_path),
                         "generator_sha256": h.sha(__file__),
                         "meshes_sha256": hashes},
             "modules": modules}
    sys.path.insert(0, os.fspath(spacer_model.HERE.parent / "carbon-rod-holders" / "assembly"))
    from register_assembly import register_assembly, write_json
    path = OUT / "assembly-guide.json"
    write_json(path, guide)
    tower = OUT / "timelapse-tower.json"
    register_assembly(path, "r24", "R24 patterned spacer trial", make_current=make_current,
                      helper=tower if make_current else None)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--make-current", action="store_true")
    build(parser.parse_args().make_current)
