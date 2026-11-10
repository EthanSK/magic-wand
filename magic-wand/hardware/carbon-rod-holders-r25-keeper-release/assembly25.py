#!/usr/bin/env python3
"""Show the R25 holder, PCB, keeper and rod moving through the checked fit trial."""

import argparse
from copy import deepcopy
import json
import sys

import numpy as np
import trimesh

import catch25 as catch
from assembly23 import relative_actor, translation


OUT = catch.OUT
GUIDE = OUT / "guide"
SHARED = catch.HERE.parent / "carbon-rod-holders" / "assembly"
R24_EXPORTS = catch.HERE.parent / "carbon-rod-holders-r24-patterned-spacer" / "exports"


def step(title, caption, samples, duration=3):
    return {"title": title, "caption": caption, "duration": duration, "samples": samples}


def motion_samples(state, path):
    frames = []
    for dy, blend in path:
        state["keeper"] = translation(y=dy)
        frames.append({**state, "morphs": {"keeper": float(blend)}})
    return frames


def shape_file(name, solid):
    file = f"guide/{name}.stl"
    catch.h.mesh(solid).export(OUT / file)
    return file


def morph_file(name, source):
    base = trimesh.load_mesh(OUT / source, process=False)
    target = trimesh.Trimesh(base.vertices + catch.lift(base.vertices), base.faces, process=False)
    file = f"guide/{name}-lifted.stl"
    target.export(OUT / file)
    written = trimesh.load_mesh(OUT / file, process=False)
    assert np.array_equal(base.faces, written.faces)
    assert np.allclose(written.vertices, target.vertices, atol=.000002, rtol=0)
    return file


def release_steps(state, paths):
    return [
        step("Pull Gently to Check the Stop",
             "A small straight pull brings the tooth against the steep face. The board prongs stay flat.",
             motion_samples(state, paths["pull_to_stop"])),
        step("Lift the Rounded Tab",
             "Lift the rounded edge a little with a fingernail. The tooth rises above the ridge.",
             motion_samples(state, paths["lift"])),
        step("Slide the Keeper Out",
             "Keep the tab raised while you slide the keeper back along its two grooves.",
             motion_samples(state, paths["remove"]), 4),
        step("Let the Tab Settle",
             "Let go once the tooth is clear. The spring tab returns to its flat shape.",
             motion_samples(state, paths["relax"]), 2),
    ]


def full_view(module, paths):
    holder_file = f"{catch.HOLDER}-assembly.stl"
    keeper_file = f"{catch.KEEPER}-assembly.stl"
    module["label"] = "XIAO holder · R25 lift-release trial"
    module["note"] = "Fit the R25 holder and keeper together to try the stronger catch. The board sits in its original position."
    module["actors"]["holder"].update(file=holder_file, label="R25 holder and steep stop")
    module["actors"]["keeper"].update(file=keeper_file, label="R25 keeper and rounded lift tab",
                                       morphFile=morph_file("keeper25", keeper_file))
    prep, lay_board = module["steps"][:2]
    module["steps"] = [prep, lay_board]
    state = deepcopy(lay_board["samples"][-1])
    module["steps"].append(step("Point the Tooth Toward the Holder",
                                "Line up the two side ears with the grooves. The small tooth faces down and the rounded edge faces the board.",
                                [state.copy()]))
    module["steps"].append(step("Slide On the Keeper",
                                "Push along the grooves until the tab drops behind the ridge. The prongs rest over the two corners of the board.",
                                motion_samples(state, paths["insert"]), 4))
    rod_frames = []
    for dy in np.linspace(80., 0., 33):
        state["rod"] = translation(y=dy)
        rod_frames.append(state.copy())
    module["steps"].append(step("Slide the Rod Through the Rings",
                                "Feed the rod through both rings, end-first.",
                                rod_frames, 4))
    module["steps"].extend(release_steps(state, paths))
    board_actors = [name for name in module["actors"] if name == "board" or name.startswith("board_")]
    board_frames = []
    for previous in reversed(lay_board["samples"]):
        state.update({name: previous[name] for name in board_actors})
        board_frames.append(state.copy())
    module["steps"].append(step("Lift the Board Out",
                                "Lift the keeper end of the board and slide the USB end out from under the far fingers.",
                                board_frames, 4))
    unmount = [{**state, "rod": pose["rod"]} for pose in reversed(rod_frames)]
    module["steps"].append(step("Slide the Holder Off the Rod",
                                "Draw the rod out through the rings to separate the holder.",
                                unmount, 4))


def cutaway(paths):
    box = catch.h.box(-.45, .45, -7.5, 3.8, 8., 13.5)
    holder = catch.h.h22.read(OUT / f"{catch.HOLDER}-assembly.stl")
    keeper = catch.h.h22.read(OUT / f"{catch.KEEPER}-assembly.stl")
    keeper_file = shape_file("keeper25_section", keeper ^ box)
    actors = {
        "holder": {"label": "Blue holder ridge and steep face",
                   "file": shape_file("holder25_section", holder ^ box), "color": "#29a5b7"},
        "keeper": {"label": "Orange keeper tooth and spring tab",
                   "file": keeper_file, "morphFile": morph_file("keeper25_section", keeper_file),
                   "color": "#f19a49"},
    }
    close = {name: [pose for pose in route if pose[0] >= -3.5] for name, route in paths.items()}
    close["relax"] = [(close["remove"][-1][0], blend) for _, blend in paths["relax"]]
    state = {name: translation() for name in actors}
    steps = [
        step("Find the Ramp and Tooth",
             "The orange spring is joined to the keeper outside this side section. The blue ridge has a slope on the way in and a steep face on the way out.",
             motion_samples(state, close["insert"][:1])),
        step("Push Until It Clicks",
             "The tooth climbs the blue slope. The tab drops flat once the tooth passes the steep face.",
             motion_samples(state, close["insert"]), 4),
        *release_steps(state, close),
    ]
    return {"label": "XIAO keeper latch · R25 cutaway",
            "note": "Side section of the matching R25 parts. The bend is drawn from the checked CAD route.",
            "rotation": [np.pi / 2, np.pi / 2, 0.], "actors": actors, "steps": steps}


def build(make_current):
    GUIDE.mkdir(exist_ok=True)
    sys.path.insert(0, str(SHARED))
    from register_assembly import register_assembly, write_json

    previous = R24_EXPORTS / "assembly-guide.json"
    modules = json.loads(previous.read_text())["modules"]
    for module in modules.values():
        module["actors"] = {name: relative_actor(actor, R24_EXPORTS, OUT)
                            for name, actor in module["actors"].items()}
    paths = catch.motions()
    full_view(modules["xiao"], paths)
    modules["xiao_latch"] = cutaway(paths)
    assets = {actor[key] for module in modules.values() for actor in module["actors"].values()
              for key in ("file", "morphFile") if key in actor}
    guide = {"schema_version": 2, "units": "mm", "revision": catch.REVISION,
             "physical_fit_verified": False,
             "sources": {"r24_guide_sha256": catch.h.sha(previous),
                         "manifest_sha256": catch.h.sha(OUT / "manifest.json"),
                         "generator_sha256": catch.h.sha(__file__),
                         "meshes_sha256": {file: catch.h.sha(OUT / file) for file in sorted(assets)}},
             "modules": modules}
    path = OUT / "assembly-guide.json"
    write_json(path, guide)
    register_assembly(path, "r25", "R25 XIAO keeper trial", make_current=make_current,
                      helper=OUT / "timelapse-tower.json" if make_current else None)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--make-current", action="store_true")
    build(parser.parse_args().make_current)
