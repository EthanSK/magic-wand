#!/usr/bin/env python3
"""Export R31, run its hole-mount checks and write the shared-viewer guide."""

import argparse
from copy import deepcopy
import json
import sys

import numpy as np
import trimesh

import holder31 as h
sys.path.insert(0, str(h.R29))
sys.path.insert(0, str(h.h29.R28))
import assembly28 as a28  # noqa: E402
from assembly23 import relative_actor  # noqa: E402

d, H, k27, h29 = h.d, h.H, h.k27, h.h29
OUT = h.OUT
R29_OUT = h.R29 / "exports"
SOURCE = R29_OUT / "assembly-guide.json"
register_assembly, write_json = a28.register_assembly, a28.write_json
move = a28.move


def cap_pose(angle=None, local=(0., 0., 0.), lift=0.):
    return h.placement(angle, local, lift).ravel().tolist()
CARRIER = a28.CARRIER
BRACKET, CLIP = "DFRobot_Hole_Bracket", "DFR0030_Post_Clip"
TOUCH = ("sensor", "electrode", "connector")
CLIPS = ("clip_left", "clip_right")
LEAD_OFF = a28.LEAD_OFF
BOARD_UP = (0., 0., 16.)           # board parked above the posts
CLIP_FRONT = (0., -4., 0.)         # clip on the board face, mouth towards its post
CLIP_UP = (0., -4., 8.)
FULL_LABEL, HINGE_LABEL = "Keys · full assembly", "Keys · snap hinge detail"


def guide_mesh(name, solid):
    file = f"guide/{name}.stl"
    model = H.mesh(solid)
    assert model.is_watertight and model.is_winding_consistent, name
    model.export(OUT / file)
    return file


def export_parts(carrier):
    H.OUT = OUT
    H.PRINT_ROT[BRACKET] = trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])     # front face down: grow the arms from their roots
    H.PRINT_ROT[CLIP] = H.PRINT_ROT[CLIP + "_2"] = np.eye(4)                    # flat, as modelled
    shapes = {CARRIER: carrier, BRACKET: h.cap(),
              CLIP: h.clip_local(), CLIP + "_2": h.clip_local()}
    return {name: H.export_part(name, shape, name) for name, shape in shapes.items()}


def pinched(source, file):
    """Bend the exported bracket's own arm vertices. Same faces, same order."""
    model = trimesh.load_mesh(OUT / source, process=False)
    target = trimesh.Trimesh(model.vertices + h.arm_bend(model.vertices), model.faces, process=False)
    target.export(OUT / file)
    written = trimesh.load_mesh(OUT / file, process=False)
    assert np.array_equal(written.faces, model.faces)
    moved = np.linalg.norm(written.vertices - model.vertices, axis=1)
    assert moved.max() > .8 and np.count_nonzero(moved) < len(moved), "only the arms bend"
    return file, int(np.count_nonzero(moved > 1e-6))


def touch_view(r29_dfr, files):
    actors = {name: deepcopy(actor) for name, actor in r29_dfr["actors"].items() if name not in {"touch_pin", "op1_latch", "keeper_pin"}}
    actors["carrier"] = {**actors["carrier"], "file": files["carrier"], "label": "Key holder with two fixed hinge supports"}
    actors["carrier"].pop("morphFile", None)
    actors["cap"] = {"label": "Orange hinged bracket: two posts through the board holes, two flexible arms",
                     "file": files["bracket"], "morphFile": files["pinched"], "color": "#e19753"}
    actors["sensor"] = {**actors["sensor"], "file": files["sensor"], "label": "DFR0030 V2 board (22 × 35 mm, two holes)"}
    actors["electrode"] = {**actors["electrode"], "file": files["electrode"]}
    actors["connector"] = {**actors["connector"], "file": files["connector"]}
    actors["sensor_lead"] = {**actors["sensor_lead"], "file": files["lead"]}
    for name, side in zip(CLIPS, ("Left", "Right")):
        actors[name] = {"label": f"{side} post clip (printed)", "file": files[name], "color": "#ffdd68"}
    last = r29_dfr["steps"][-1]["samples"][-1]
    seated = {name: last[name] for name in actors if name in last}
    for name in (*TOUCH, *CLIPS, "cap", "sensor_lead"):
        seated[name] = cap_pose()
    state = dict(seated)
    state["morphs"] = {"cap": 0.}
    group = ("cap", *TOUCH, *CLIPS, "sensor_lead")
    op1 = seated["board"]
    for name in ("board", "sockets", "plug", "op1_wire"):
        state[name] = move(seated[name], (0., 42., 0.))
    for name in ("switch", "plunger"):
        state[name] = move(seated[name], (0., 0., 8.))
    state["cap"] = cap_pose(lift=8.)
    for name in TOUCH:
        state[name] = cap_pose(local=BOARD_UP)
    for name in CLIPS:
        state[name] = cap_pose(local=CLIP_UP)
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

    def path(names, points, n=13):
        frames = []
        for a, b in zip(points, points[1:]):
            frames += cap_slide(names, a, b, n)[(1 if frames else 0):]
        return frames

    def pinch(lift, a, b, n=10):
        return [{**state, "cap": cap_pose(lift=lift), "morphs": {"cap": float(t)}} for t in np.linspace(a, b, n)]

    def lower(a, b, n=25):
        return [{**state, "cap": cap_pose(lift=float(z)), "morphs": {"cap": 1.}} for z in np.linspace(a, b, n)]

    zero = (0., 0., 0.)
    add("Slide In the OP1 Board", "Feed the stock OP1 board in from the two-key end, connector towards you.",
        slide(("board", "sockets", "plug", "op1_wire")), 4)
    add("Plug in the Switch", "Press the microswitch into its three sockets. Hold the rear of the OP1 board in its slot with removable nonconductive tape. Keep the tape clear of the switch.", slide(("switch", "plunger")))
    add("Pinch the Bracket Arms", "Hold the orange bracket above the holder. Pinch the two raised pads under the connector end so both tabs pull inwards.",
        pinch(8., 0., 1.), 2, True)
    add("Lower Between the Supports", "Keep pinching and lower the bracket. The two tabs pass between the two fixed supports.",
        lower(8., 0.), 3, True)
    add("Let the Tabs Snap Into the Holes", "Let go. Each arm springs back and its tab enters the hole in the support beside it.",
        pinch(0., 1., 0.), 2, True)
    add("Fit the Board Over the Posts", "Gold face up, pads at the three-key end. Lower the DFR0030 so its two holes go over the two posts and it sits on the rails.",
        cap_slide(TOUCH, BOARD_UP, zero, 25), 3, True)
    add("Clip the Posts", "Put each clip on the board in front of its post, open end towards the post. Push it towards the connector until it snaps round the neck.",
        path(CLIPS, (CLIP_UP, CLIP_FRONT, zero)), 3, True)
    add("Plug In the Gravity Lead", "Plug the lead in at the top end and leave a loose loop behind the board.",
        cap_slide(("sensor_lead",), LEAD_OFF, zero, 18))
    press = [{**state, **{name: cap_pose(float(a)) for name in group},
              "plunger": move(op1, (0., 0., -d.DEPRESSION * (1 + a / h.REST)))}
             for a in [*np.linspace(-h.REST, 0., 25), *np.linspace(0., -h.REST, 25)]]
    add("Touch, Click and Release", "Press the gold face. The bracket turns on the two tabs until its feet meet the stops at 0.48 mm of plunger travel.",
        press, 5, True)
    service = len(steps)
    add("Unplug the Gravity Lead", "Unplug the lead before removing the board.",
        cap_slide(("sensor_lead",), zero, LEAD_OFF, 18))
    add("Pull Off the Clips", "Push each clip towards the gold pads with a fingernail. Its jaws open round the neck and it comes off.",
        path(CLIPS, (zero, CLIP_FRONT, CLIP_UP)), 3, True)
    add("Lift the Board Off the Posts", "Lift the board straight up off the two posts. This uncovers the two pinch pads.",
        cap_slide(TOUCH, zero, BOARD_UP, 25), 3, True)
    add("Pinch to Release the Tabs", "Pinch both pads. The tabs pull out of the support holes.", pinch(0., 0., 1.), 2, True)
    add("Lift Off the Empty Bracket", "Keep pinching and lift the bracket straight up.", lower(0., 8.), 3, True)
    add("Pinch and Lower It Back", "To refit, pinch again and lower the bracket between the supports.", lower(8., 0.), 3, True)
    add("Let the Tabs Snap Back In", "Let go so both tabs return into their holes.", pinch(0., 1., 0.), 2, True)
    refit = {"Lift the Board Off the Posts": ("Fit the Board Back on the Posts", "Lower the board back over the two posts."),
             "Pull Off the Clips": ("Refit the Clips", "Push both clips back on until they snap round the necks."),
             "Unplug the Gravity Lead": ("Reconnect the Lead", "Plug the lead back in with a loose loop.")}
    for item in reversed(steps[service:service + 3]):
        title, caption = refit[item["title"]]
        add(title, caption, [{**state, **{k: v for k, v in frame.items() if k in group}} for frame in reversed(item["samples"])],
            item["duration"], item.get("reveal", False))
    for name in actors:
        assert np.allclose(state[name], seated[name]), name
    hy, top = h.hole_y(), h.NECK[0] + h.CLIP_T
    return {**r29_dfr, "label": "DFRobot board on the hole-mount bracket", "keysLabel": FULL_LABEL,
            "actors": actors, "steps": steps,
            "annotations": [
                {"side": "left", "actor": "cap", "point": [-h.POST_X, hy, h.HEAD_TOP],
                 "step": "Fit the Board Over the Posts", "title": "Post through the left board hole"},
                {"side": "right", "actor": "clip_right", "point": [h.POST_X + h.CLIP_HALF_X, hy, top],
                 "step": "Clip the Posts", "title": "Clip on the post neck holds the board down"},
                {"side": "left", "actor": "cap", "point": [-h29.TAB_TIP, h.AXIS_Y, h.AXIS_Z],
                 "step": "Let the Tabs Snap Into the Holes", "title": "Tab in the fixed support hole"},
            ],
            "status": "CAD-checked candidate. Board hole pitch, print, arm flex, clip snap and touch response are untested.",
            "note": "A small orange bracket holds the DFR0030 V2 through its two holes: two posts, two printed clips, and reversed flexible arms snapping into the fixed supports. The orange bracket is the only hinge. The OP1 board stays in its slot with removable tape."}


def hinge_view(carrier, full):
    """The same bracket mesh and poses as the full assembly, with the key holder cut away."""
    world_y = h.AXIS_Y + h.CLICK_SHIFT
    holder = guide_mesh("hinge-detail-key-holder",
                        carrier ^ h.box(-7.6, 7.6, world_y - 3.1, world_y + 9., 10.9, 20.1))
    actors = {
        "carrier": {**full["actors"]["carrier"], "file": holder},
        "cap": {**full["actors"]["cap"], "cutaway": False},
    }
    steps = []
    for step in full["steps"]:
        if not all("cap" in sample.get("morphs", {}) for sample in step["samples"]):
            continue
        if not any(sample["morphs"]["cap"] > 0 for sample in step["samples"]):
            continue
        samples = [{name: sample[name] for name in (*actors, "morphs")} for sample in step["samples"]]
        steps.append({**step, "samples": samples})
    return {
        "label": HINGE_LABEL,
        "rotation": [.7, 0., -.46],
        "actors": actors,
        "steps": steps,
        "annotations": [
            {"side": "left", "actor": "cap", "point": [-h29.TAB_TIP, h.AXIS_Y, h.AXIS_Z],
             "step": "Pinch the Bracket Arms", "title": "Tab on the bracket arm"},
            {"side": "right", "actor": "carrier", "point": [h29.SUPPORT_X[1], world_y, h.AXIS_Z],
             "step": "Let the Tabs Snap Into the Holes", "title": "Hole in the fixed support"},
            {"side": "right", "actor": "cap", "point": [h.POST_X, h.hole_y(), h.HEAD_TOP],
             "title": "Post for the board hole"},
        ],
        "note": "The whole orange bracket from the full assembly, with the key holder cut away round the supports. Pinch the arms to fit or remove it.",
    }


def build(current):
    carrier, working = h.geometry()
    result = h.checks(carrier, working)
    print(json.dumps(result), flush=True)
    if not result["passed"]:
        raise ValueError(result)
    (OUT / "guide").mkdir(parents=True, exist_ok=True)
    parts = export_parts(carrier)
    bent, bent_vertices = pinched(f"{BRACKET}-assembly.stl", "guide/bracket-arms-pinched.stl")
    result["guide_pinched_bracket_moved_vertices"] = bent_vertices
    files = {"carrier": f"{CARRIER}-assembly.stl", "bracket": f"{BRACKET}-assembly.stl",
             "pinched": bent,
             "sensor": guide_mesh("dfr0030-v2-board", h.sensor()), "electrode": guide_mesh("dfr0030-pad", h.electrode()),
             "connector": guide_mesh("gravity-connector", h.connector()), "lead": guide_mesh("gravity-lead", h.gravity_lead()),
             "clip_left": guide_mesh("post-clip-left", h.clip(-1)), "clip_right": guide_mesh("post-clip-right", h.clip(1))}
    source = json.loads(SOURCE.read_text())["modules"]
    source.pop("snap_hinge", None)
    for module in source.values():
        module["actors"] = {name: relative_actor(actor, R29_OUT, OUT) for name, actor in module["actors"].items()}
    source["key"]["actors"]["carrier"]["file"] = files["carrier"]
    dfr = touch_view(source.pop("dfr"), files)
    key = source.pop("key")
    # Keys first, then the hinge detail beside it, then the other components.
    modules = {"key": key, "dfr": dfr, "snap_hinge": hinge_view(carrier, dfr), **source}
    sha = H.sha
    write_json(OUT / "manifest.json", {
        "revision": h.REVISION, "physical_fit_verified": False, "print_validated": False,
        "based_on": h29.REVISION,
        "change": "R29's tray, edge rails, end stop and filament board keeper replaced by a small hinged bracket with two posts through the DFR0030 V2 holes and two printed clips. The pivot sits at the key holder rear edge, 19.05 mm farther towards the two-key end than R30. Its arms point forward underneath. Removable tape holds the OP1 board.",
        "purchased_board": "DFRobot DFR0030 Gravity Digital Capacitive Touch Sensor V2",
        "estimates": ["35 mm board length (distributor sheet)", "15.5 mm hole pitch, 24.1 mm from the pad end (photos)",
                      "3.0 mm holes (published nominal)", "1.6 mm board thickness", "Gravity socket/plug envelope (R26)",
                      "DFR0030 parts near the holes and under the board", "stock OP1 board, switch and plug (R23)"],
        "frames": {BRACKET: "Cap frame; place with holder31.world(angle)", CARRIER: "assembly",
                   CLIP: "flat, as printed"},
        "print_quantities": {CARRIER: 1, BRACKET: 1, CLIP: 1, CLIP + "_2": 1},
        "loose_hardware": ["Removable nonconductive tape for the OP1 board"],
        "print_orientation_note": "Carrier rear face down. Bracket front face down, growing the arms from their roots. Clips flat. See print-checks.json for the final slice. Physical fit and flex remain untested.",
        "source_sha256": {p.name: sha(p) for p in (h.HERE / "holder31.py", h.HERE / "assembly31.py")},
        "parts": parts,
    })
    write_json(OUT / "geometry-checks.json", {
        "revision": h.REVISION, "physical_fit_verified": False, "print_validated": False,
        "source_sha256": sha(h.HERE / "holder31.py"), "carrier_sha256": sha(OUT / files["carrier"]),
        "bracket_sha256": sha(OUT / files["bracket"]), "pinched_bracket_sha256": sha(OUT / bent),
        "clip_sha256": sha(OUT / f"{CLIP}-assembly.stl"), "checks": result,
    })
    assets = {actor[field] for module in modules.values() for actor in module["actors"].values()
              for field in ("file", "morphFile") if field in actor}
    guide = OUT / "assembly-guide.json"
    write_json(guide, {"schema_version": 2, "units": "mm", "revision": h.REVISION, "physical_fit_verified": False,
                       "sources": {"r29_guide_sha256": sha(SOURCE), "generator_sha256": sha(__file__),
                                   "manifest_sha256": sha(OUT / "manifest.json"),
                                   "meshes_sha256": {file: sha(OUT / file) for file in sorted(assets)}},
                       "modules": modules})
    register_assembly(guide, "r31", "R31 DFRobot rear hinge", make_current=current, group_keys=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--make-current", action="store_true")
    build(parser.parse_args().make_current)
