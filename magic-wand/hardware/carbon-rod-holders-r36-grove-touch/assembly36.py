"""Export the Grove revision's editable meshes and matching assembly animation.

Run with --register after the plate has passed its printability checks.
"""

import argparse
from copy import deepcopy
from pathlib import Path
import shutil

import numpy as np

import holder36 as design
import assembly35 as old_assembly

HERE = Path(__file__).resolve().parent
OUT = HERE / "exports"
SOURCE = design.R35 / "exports"
BRACKET = design.BRACKET
CARRIER = old_assembly.CARRIER
REVISION = "r36"
LABEL = "R36 Seeed Grove touch"
a31 = old_assembly.prior.a31
r = design.r

PCB = ("sensor", "electrode", "connector", "sensor_parts")
PLUG = "sensor_plug"
PLUGGED = (*PCB, PLUG)
SCREWS = ("grove_screw_front", "grove_screw_rear")
GROVE = (*PLUGGED, *SCREWS, "sensor_lead")
DISPLACED = (*GROVE, "clip_left", "clip_right")
PARKED = [0.] * 12


def placement(lift=0., angle=None):
    return r.placement(angle, local=(0., 0., lift)).reshape(-1).tolist()


def assemble_touch(previous, assets, morph, travel, stop_angle=0.):
    full = deepcopy(previous)
    for name in DISPLACED:
        full["actors"].pop(name, None)
    full["actors"].update(assets)
    full["actors"]["cap"].update(
        label="Orange Grove bracket and flexible hinge arms",
        file=f"{BRACKET}-assembly.stl", morphFile=morph,
    )
    first = full["steps"][:9]
    for step in first:
        step["samples"] = [{**{k: v for k, v in row.items() if k not in DISPLACED},
                            **{part: PARKED for part in GROVE}} for row in step["samples"]]
    state = first[-1]["samples"][-1]
    initial = {**{part: placement(design.SERVICE_LIFT) for part in PLUGGED},
               **{part: placement(design.SERVICE_LIFT + 4.) for part in SCREWS}}
    steps = first

    def slide(title, caption, parts, start, finish, duration=3, feed_lead=False):
        nonlocal state
        frames = []
        for z in np.linspace(start, finish, 21):
            frame = {**state, **{part: placement(float(z)) for part in parts}}
            if feed_lead:
                frame["sensor_lead"] = placement()
                frame["morphs"] = {**state.get("morphs", {}), "sensor_lead": float(z / design.SERVICE_LIFT)}
            frames.append(frame)
        steps.append({"title": title, "caption": caption, "duration": duration, "samples": frames, "reveal": True})
        state = frames[-1]

    # The connector is already attached when the board is lowered. The flexible
    # tail is fed into the channel before the board reaches its screw seats.
    state = {**state, **initial}
    slide("Seat the Grove Board",
          "Two-key end at the top. Plug in the Grove cable first, feed the free wire ends through the left opening, then lower the gold face up onto the two centred seats.",
          PLUGGED, design.SERVICE_LIFT, 0., feed_lead=True)
    slide("Fit the Two M2 Screws",
          "Fasten the upper and lower tabs with two M2 × 4 mm pan-head screws. Tighten gently against the printed seats.",
          SCREWS, design.SERVICE_LIFT + 4., 0.)
    state = {**state, "sensor_lead": placement()}
    angles = [*np.linspace(-r.REST, stop_angle, 25), *np.linspace(stop_angle, -r.REST, 25)]
    frames = [
        {**state, **{part: placement(angle=float(angle)) for part in ("cap", *GROVE)},
         "plunger": a31.move(state["plunger"], (0., 0., -max(0., travel + r.d.DEPRESSION * (angle - stop_angle) / r.REST)))}
        for angle in angles
    ]
    steps.append({
        "title": "Touch, Click and Release",
        "caption": "Light contact on the gold pad sends touch to the XIAO. Press farther to click the separate OP1 switch, then release. The orange bracket pivots until its two feet meet the stops.",
        "duration": 5, "samples": frames, "reveal": True,
    })
    state = frames[-1]
    slide("Undo the Two Screws",
          "Switch off first and leave slack in the cable. Remove both centred screws before lifting the module.",
          SCREWS, 0., design.SERVICE_LIFT + 4.)
    slide("Lift the Grove Board",
          "Lift the Grove board with its cable still attached. Guide the loose wires back through the opening.",
          PLUGGED, 0., design.SERVICE_LIFT, feed_lead=True)
    unplugged = design.SERVICE_LIFT - 3.2
    slide("Unplug the Grove Lead",
          "Hold the board above the bracket. Release the latch and pull the plug down from its socket.",
          (PLUG,), design.SERVICE_LIFT, unplugged, feed_lead=True)
    slide("Reconnect the Grove Lead",
          "Line up the keyed plug and reconnect it above the bracket.",
          (PLUG,), unplugged, design.SERVICE_LIFT, feed_lead=True)
    slide("Put the Grove Board Back",
          "Feed the loose wire ends through the same opening before reseating the board.",
          PLUGGED, design.SERVICE_LIFT, 0., feed_lead=True)
    slide("Fasten the Grove Board",
          "Refit both screws and leave slack at the cable bend.", SCREWS, design.SERVICE_LIFT + 4., 0.)
    full["steps"] = steps
    full["annotations"] = [
        {"side": "right", "actor": "sensor", "point": [0., design.HOLES[1], design.BOARD_Z + 1.6],
         "step": "Fit the Two M2 Screws", "title": "Centred screw at the two-key end"},
        {"side": "right", "actor": "sensor", "point": [0., design.HOLES[0], design.BOARD_Z + 1.6],
         "step": "Fit the Two M2 Screws", "title": "Centred screw at the three-key end"},
        {"side": "left", "actor": "connector", "point": [-6.1, design.BOARD_Y, design.BOARD_Z - 7.7],
         "step": "Seat the Grove Board", "title": "Underboard plug on the left of the rod"},
        {"side": "right", "actor": "electrode", "point": [1.6, design.BOARD_Y, design.BOARD_Z + 1.68],
         "step": "Touch, Click and Release", "title": "Touch pad, offset by the board layout"},
        *[a for a in previous["annotations"] if a["actor"] == "board" or
          a["step"] == "Let the Tabs Snap Into the Holes"],
    ]
    full.update(label="Seeed Grove touch with OP1 click", openSeated=False,
                status="CAD assembly candidate · hardware fit and touch response pending",
                note="The two screw holes run along the rod. The connector faces down and exits to the left, opposite the OP1 switch.")
    return full


def write_guide(key, travel, stop_angle=0.):
    guide = old_assembly.prior.read(SOURCE / "assembly-guide.json")
    modules = guide["modules"]
    for module in modules.values():
        module["actors"] = {name: a31.relative_actor(actor, SOURCE, OUT)
                            for name, actor in module["actors"].items()}
    for name in ("key", "dfr"):
        modules[name]["actors"]["carrier"]["file"] = f"{CARRIER}-assembly.stl"
    morph, _ = a31.pinched(f"{BRACKET}-assembly.stl", "guide/grove-bracket-pinched.stl")
    assets = {}
    for name, label, colour, mesh in (
        ("sensor", "Seeed Grove Touch V1.1", "#287497", design.board()),
        ("electrode", "Exposed touch electrode", "#cfaa67", design.electrode()),
        ("connector", "Straight Grove socket", "#eeeadd", design.housing()),
        ("sensor_parts", "Underside component clearance", "#2e3f48", design.components()),
        ("sensor_plug", "Mated Grove plug envelope", "#fff6dc", design.plug()),
        ("sensor_lead", "Forward Grove wire route", "#eeb04f", design.lead()),
        ("grove_screw_front", "Three-key-end M2 screw", "#aaaeb5", design.fastener(design.HOLES[0])),
        ("grove_screw_rear", "Two-key-end M2 screw", "#aaaeb5", design.fastener(design.HOLES[1])),
    ):
        assets[name] = {"file": a31.guide_mesh(name, mesh), "label": label, "color": colour}
    # Stretch the straight part above the first bend while the loose tail
    # remains through the opening. Keep mesh faces and vertex order fixed.
    lead = a31.trimesh.load_mesh(OUT / assets["sensor_lead"]["file"], process=False)
    lower = design.BOARD_Z - 12.15
    stretch = np.clip((lead.vertices[:, 2] - lower) / (12.15 - 9.8), 0., 1.)
    lead.vertices[:, 2] += design.SERVICE_LIFT * stretch
    cable_morph = "guide/sensor-lead-fed.stl"
    lead.export(OUT / cable_morph)
    assets["sensor_lead"]["morphFile"] = cable_morph
    modules["dfr"] = assemble_touch(modules["dfr"], assets, morph, travel, stop_angle)
    hinge = modules["snap_hinge"]
    hinge["actors"]["cap"].update(file=f"{BRACKET}-assembly.stl", morphFile=morph,
                                  label="Grove bracket snap hinge")
    hinge["annotations"] = hinge["annotations"][:2]
    pivot = r.AXIS_Y + r.CLICK_SHIFT
    detail = key ^ design.box(-7.6, 7.6, pivot - 3.1, pivot + 9., 10.9, 20.1)
    hinge["actors"]["carrier"]["file"] = a31.guide_mesh("grove-hinge-detail", detail)
    guide["print_components"] = {name: group["parts"] for name, group in
                                 old_assembly.prior.read(HERE / "complete-assembly.json")["groups"].items()}
    files = {actor[k] for module in modules.values() for actor in module["actors"].values()
             for k in ("file", "morphFile") if k in actor}
    guide.update(revision=HERE.name, sources={
        "r35_guide_sha256": design.h.H.sha(SOURCE / "assembly-guide.json"),
        "generator_sha256": design.h.H.sha(__file__),
        "manifest_sha256": design.h.H.sha(OUT / "manifest.json"),
        "meshes_sha256": {name: design.h.H.sha(OUT / name) for name in sorted(files)},
    })
    a31.write_json(OUT / "assembly-guide.json", guide)


def export():
    (OUT / "guide").mkdir(parents=True, exist_ok=True)
    a31.OUT = design.h.H.OUT = OUT
    design.h.H.PRINT_ROT[BRACKET] = a31.trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])
    checks = design.checks()
    a31.write_json(OUT / "geometry-checks.json", {"revision": HERE.name, "physical_fit_verified": False, "checks": checks})
    if not checks["passed"]:
        raise ValueError("Grove board working-space check failed")
    key = design.carrier()
    parts = {
        CARRIER: design.h.H.export_part(CARRIER, key, CARRIER),
        BRACKET: design.h.H.export_part(BRACKET, design.bracket(), BRACKET),
    }
    spacer = old_assembly.prior.spacer34.NAME
    parts[spacer] = old_assembly.prior.read(SOURCE / "manifest.json")["parts"][spacer]
    for suffix in old_assembly.EXPORT_SUFFIXES:
        name = f"{spacer}-{suffix}.stl"
        shutil.copyfile(SOURCE / name, OUT / name)
    manifest = {
        "revision": HERE.name, "based_on": design.R35.name, "parts": parts,
        "change": "Centred Grove sensor screws, forward plug route and lower touch seat.",
        "source_sha256": {p.name: design.h.H.sha(p) for p in
                          (Path(__file__), HERE / "holder36.py", HERE / "complete-assembly.json")},
    }
    a31.write_json(OUT / "manifest.json", manifest)
    write_guide(key, checks["measured_nominal_plunger_travel_to_stop_mm"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register", action="store_true")
    args = parser.parse_args()
    if args.register:
        a31.register_assembly(OUT / "assembly-guide.json", REVISION, LABEL, group_keys=True)
    else:
        export()
