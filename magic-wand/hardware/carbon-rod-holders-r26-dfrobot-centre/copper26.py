#!/usr/bin/env python3
"""Compact copper insert preview for the R26 OP1 click mechanism.

The copper is adhesive foil on an insulating carrier. The carrier slides
in from the hinge end while the cap is off. With the cap snapped on, its
downward tab meets the fixed hinge before the carrier can leave its rails.
"""

from copy import deepcopy
from functools import lru_cache

import manifold3d as mf
import numpy as np

import holder26 as d
from assembly23 import translation

HALF_WIDTH = 9.0
NOSE, REAR = -9.5, 7.8
ROOF_BOTTOM, ROOF_TOP = 21.40, 22.40
INSERT_HALF = 7.25
INSERT_FRONT, INSERT_REAR = -8.22, 5.03
INSERT_BOTTOM, INSERT_TOP = 20.39, 21.23
FOIL_THICKNESS = .07
FOIL_X, FOIL_Y = 6.6, (-7.45, 4.05)
SLIDE = 17.5
TAB_FRONT, TAB_REAR = 4.74, 5.06
WIRE_RADIUS = .24
JOINT = np.array([0., 5.11, 21.01])
FIXED_END = np.array([0., 13.75, 21.10])
CAP_PARTS = ("cap", "insert", "foil", "wire")


@lru_cache(maxsize=1)
def cap():
    """Carry over the actual snap ears, OP1 pusher and down-stop feet."""
    old = d.paddle()
    click = old ^ d.box(-7.95, 7.95, -4.1, 4.72, 12.95, 19.20)
    ears = old ^ d.mirrored(d.box(1.95, 4.02, 4.6, 8.22, 16.98, 19.45))
    # Side cheeks tie the cover to the lower click bridge. The two shelves
    # support the insert edges and leave the hinge end open for loading.
    sides = d.mirrored(d.box(7.45, 8.65, -8.5, 5.65, 18.95, 21.52))
    shelves = d.mirrored(d.box(6.64, 7.58, -8.40, 5.65, 19.90, 20.39))
    nose_stop = d.box(-7.52, 7.52, -8.75, -8.43, 20.28, 21.55)
    bridge = d.mirrored(d.box(3.45, 7.7, 4.40, 4.63, 18.94, 19.40))
    roof = d.h.rounded_plate(HALF_WIDTH, NOSE, REAR, ROOF_BOTTOM, ROOF_TOP,
                             r_plan=1.55, r_top=.29)
    return d.h.base.clean(d.union((click, ears, sides, shelves, nose_stop, bridge, roof)),
                          "Copper_touch_cap")


def tab():
    return d.box(-1.43, 1.43, TAB_FRONT, TAB_REAR, 19.24, INSERT_BOTTOM + .12)


def insert():
    return d.h.base.clean(d.box(-INSERT_HALF, INSERT_HALF, INSERT_FRONT, INSERT_REAR,
                                INSERT_BOTTOM, INSERT_TOP) + tab(), "Copper_foil_insert")


def foil():
    # The tiny rear tongue folds around the insert edge to expose a joint
    # face for the wire. Keep that joint below the sensing surface.
    top = INSERT_TOP + FOIL_THICKNESS
    patch = d.box(-FOIL_X, FOIL_X, *FOIL_Y, INSERT_TOP, top)
    tongue = d.box(-.54, .54, FOIL_Y[1] - .01, INSERT_REAR + FOIL_THICKNESS,
                   INSERT_TOP, top)
    fold = d.box(-.54, .54, INSERT_REAR, INSERT_REAR + FOIL_THICKNESS, 20.79, top)
    return d.h.base.clean(patch + tongue + fold, "Copper_foil")


def local_terminal(angle):
    pose = d.pose(angle)
    return pose[:, :3].T @ (FIXED_END - pose[:, 3])


def wire_centres(angle=0., attached=False):
    # The last section flexes to reach the fixed terminal. Keep the joint
    # and hinge crossing on the cap, clear of the pinching spring arms.
    path = np.array([JOINT, [0., 5.73, 21.02], [0., 6.55, 21.04],
                     [0., 7.7, 20.99], [0., 8.9, 20.78],
                     [0., 10.1, 20.74], [0., 11.05, 20.85], [0., 11.83, 21.07]])
    if attached:
        path[4:] += np.linspace(0., 1., 4)[:, None] * (local_terminal(angle) - path[-1])
    return path


def wire_mesh(points):
    """Same vertex order in all three shapes, for the viewer's flex blend."""
    vertices, faces = [], []
    width = 10
    for point, tangent in zip(points, np.gradient(points, axis=0)):
        tangent = tangent / np.linalg.norm(tangent)
        up = np.cross(tangent, [1., 0., 0.])
        vertices.extend((point + WIRE_RADIUS * (np.cos(a) * np.array([1., 0., 0.]) + np.sin(a) * up)).tolist()
                        for a in np.linspace(0., 2 * np.pi, width, endpoint=False))
    for ring in range(len(points) - 1):
        for i in range(width):
            a, b = ring * width + i, ring * width + (i + 1) % width
            faces.extend(([a, b, b + width], [a, b + width, a + width]))
    return {"vertices": vertices, "faces": faces}


def wire_solid(points):
    balls = [mf.Manifold.sphere(WIRE_RADIUS, 16).translate(p) for p in points]
    body = d.union(mf.Manifold.batch_hull([a, b]) for a, b in zip(balls, balls[1:]))
    # The wire starts at the folded foil face. Trim the rounded CAD
    # envelope there so a spherical end doesn't intrude into the insert.
    return body ^ d.box(-1., 1., JOINT[1] - .015, 18., 19.8, 22.8)


def terminal():
    x, y, z = FIXED_END
    return d.box(x - .48, x + .48, y, y + 1.25, z - .45, z + .45)


def verify():
    d.set_lower_seats()
    carrier = d.h.h22.read(d.OUT / f"{d.CARRIER}-assembly.stl")
    regions = d.h.h22.carrier_regions()
    key_travel = d.union(regions[f"key_{index}_cap_travel"] for index in (0, 2, 3, 4))
    fixed = carrier + d.op1_latch() + d.h.switch()[0] + d.h.board() + key_travel
    squeezed = (carrier - d.spring_tongues()) + d.spring_tongues().warp_batch(lambda p: p + d.flex(p)) + key_travel
    shell, sled, copper = cap(), insert(), foil()
    released_wire = wire_solid(wire_centres())
    moving_insert = d.union((sled, copper, released_wire))
    moving_cap = shell + moving_insert
    slide = max((shell ^ moving_insert.translate((0., y, 0.))).volume() for y in np.linspace(0., SLIDE, 41))
    mounted_shape = moving_cap.transform(d.pose(-d.REST).tolist())
    install = max((squeezed ^ mounted_shape.translate((0., 0., z))).volume()
                  for z in np.linspace(0., 8., 25))
    max_click = max_wire = max_terminal_drift = 0.
    min_lock = float("inf")
    for t in np.linspace(0., 1., 25):
        angle = -d.REST * (1 - t)
        pose = d.pose(angle)
        shape = (shell + sled + copper).transform(pose.tolist())
        # Interpolate exactly as the browser does; the far end should stay fixed.
        points = (1 - t) * wire_centres(-d.REST, True) + t * wire_centres(0., True)
        max_terminal_drift = max(max_terminal_drift, np.linalg.norm(pose[:, :3] @ points[-1] + pose[:, 3] - FIXED_END))
        wire = wire_solid(points)
        max_click = max(max_click, (shape ^ fixed).volume())
        max_wire = max(max_wire, (wire ^ (shell + sled)).volume(),
                       (wire.transform(pose.tolist()) ^ fixed).volume())
        min_lock = min(min_lock, (tab().translate((0., 1.1, 0.)).transform(pose.tolist()) ^ carrier).volume())
    values = {"slide_overlap_mm3": round(slide, 5), "pinched_install_overlap_mm3": round(install, 5),
              "max_click_overlap_mm3": round(max_click, 5), "max_wire_overlap_mm3": round(max_wire, 5),
              "max_fixed_end_drift_mm": round(float(max_terminal_drift), 5),
              "hinge_tab_overlap_on_1p1mm_pull_mm3": round(min_lock, 5),
              "foil_to_cover_nominal_gap_mm": round(ROOF_BOTTOM - INSERT_TOP - FOIL_THICKNESS, 3),
              "front_stop_contact_mm3": round((sled.translate((0., -.4, 0.)) ^ shell).volume(), 5),
              "nominal_OP1_stroke_mm": d.DEPRESSION}
    passed = (max(slide, install, max_click, max_wire) < .03 and min_lock > .04
              and max_terminal_drift < .02 and values["front_stop_contact_mm3"] > .1)
    d.save_json("copper-insert-checks.json", {
        "passed": bool(passed), "print_validated": False, "physical_fit_verified": False,
        "touch_sensitivity_verified": False, "source_sha256": d.h.sha(__file__),
        "carrier_assembly_sha256": d.h.sha(d.OUT / f"{d.CARRIER}-assembly.stl"), "checks": values,
    })
    print(values, flush=True)
    if not passed:
        raise ValueError("Copper insert fit checks did not pass")


def actor_file(name, part):
    file = f"guide/copper26-{name}.stl"
    d.mesh(part).export(d.OUT / file)
    return file


def animation(dfr):
    fixed = ("board", "sockets", "switch", "plunger", "plug", "wire", "rod", "carrier", "op1_latch",
             *(key for key in dfr["actors"] if key.startswith("switch_")))
    # Keep the stock OP1 lead as a separate actor from the copper lead.
    actors = {("op1_wire" if k == "wire" else k): deepcopy(dfr["actors"][k]) for k in fixed}
    actors["cap"] = {"label": "Insulating cap", "file": actor_file("cap", cap()),
                     "color": "#e7dfcc", "cutaway": True}
    actors["insert"] = {"label": "Slide-out foil carrier", "file": actor_file("insert", insert()), "color": "#8b77d6"}
    actors["foil"] = {"label": "0.07 mm copper tape", "file": actor_file("foil", foil()), "color": "#d3834d"}
    actors["wire"] = {"label": "Moving electrode lead", "color": "#efae61", "frame": False,
                      "geometry": wire_mesh(wire_centres()),
                      "morphGeometries": [wire_mesh(wire_centres(-d.REST, True)), wire_mesh(wire_centres(0., True))]}
    actors["terminal"] = {"label": "Fixed connection (reference)", "file": actor_file("terminal", terminal()),
                          "color": "#b9c2c8", "frame": False}
    settled = dfr["steps"][-1]["samples"][-1]
    state = {k: settled[k] for k in fixed if k != "wire"}
    state["op1_wire"] = settled["wire"]
    state["terminal"] = translation()
    steps = []
    off = np.array([0., -39., 14.])
    detached = [0., 0.]
    state.update({part: translation(*off) for part in CAP_PARTS})
    for part in ("insert", "foil", "wire"):
        state[part] = translation(*(off + [0., SLIDE, 0.]))
    for part in ("foil", "wire"):
        state[part] = translation(*(off + [0., SLIDE, 4.]))
    state["morphs"] = {"carrier": 0., "wire": detached}

    def add(title, caption, frames, *, reveal=True, seconds=3):
        nonlocal state
        frames = list(frames)
        steps.append(dict(title=title, caption=caption, duration=seconds, reveal=reveal, samples=frames))
        state = frames[-1]

    def moved(parts, a, b):
        return [{**state, **{part: translation(*xyz) for part in parts}} for xyz in np.linspace(a, b, 23)]

    def fit_cap(pose, spring=0., weights=None, plunger=0.):
        return {**state, **{part: pose for part in CAP_PARTS}, "plunger": translation(z=plunger),
                "morphs": {"carrier": spring, "wire": detached if weights is None else weights}}

    add("Stick the Copper Foil On", "Stick the copper tape flat on the purple carrier, copper face towards the cap. Fold the small tail over the hinge end for the lead.",
        moved(("foil", "wire"), off + [0., SLIDE, 4.], off + [0., SLIDE, 0.]))
    add("Slide the Insert In", "With the cap off the wand, slide the insert in from the hinge end. The two rails keep the foil close to the inside of the cap.",
        moved(("insert", "foil", "wire"), off + [0., SLIDE, 0.], off))
    add("Line Up the Hinge", "Bring the cap over the OP1 switch. Keep the loose lead above the hinge.",
        moved(CAP_PARTS, off, (0., 0., 8.)))
    def lift_pose(z, angle=-d.REST):
        pose = d.pose(angle)
        pose[2, 3] += z
        return pose.ravel().tolist()

    mounting = (
        [fit_cap(lift_pose(8., -d.REST * t)) for t in np.linspace(0., 1., 9)]
        + [fit_cap(lift_pose(8.), spring=float(t)) for t in np.linspace(0., 1., 9)]
        + [fit_cap(lift_pose(float(z)), spring=1.) for z in np.linspace(8., 0., 25)]
        + [fit_cap(lift_pose(0.), spring=float(t)) for t in np.linspace(1., 0., 9)])
    add("Snap the Cap In", "Pinch the hinge arms, lower the cap onto the pins and let go. The hinge now blocks the insert's purple tab from sliding out.", mounting, seconds=5)
    rest = d.pose(-d.REST).ravel().tolist()
    add("Connect the Lead", "Route the lead over the hinge and leave slack before the fixed connection. The touch circuit sits off the cap.",
        [fit_cap(rest, weights=[float(t), 0.]) for t in np.linspace(0., 1., 18)])
    click = [*np.linspace(0., 1., 25), *np.linspace(1., 0., 25)]
    add("Press and Release", "The cap presses the OP1 plunger until its two feet meet the stops. The foil, insert and lead move with the cap.",
        [fit_cap(d.pose(-d.REST * (1 - t)).ravel().tolist(), weights=[1 - t, t],
                 plunger=-d.DEPRESSION * t) for t in click], seconds=5)
    add("Disconnect the Lead", "Unplug the lead at the fixed connection before lifting the cap.",
        [fit_cap(rest, weights=[float(t), 0.]) for t in np.linspace(1., 0., 18)])
    add("Lift the Cap Off", "Pinch both hinge arms and lift the cap. Its insert is now free to slide out.",
        reversed(mounting), seconds=4)
    add("Slide the Insert Out", "Pull the purple insert out towards the hinge end. The copper foil and its lead come out together.",
        moved(("insert", "foil", "wire"), (0., 0., 8.), (0., SLIDE, 8.)), seconds=4)
    add("Refit the Insert", "Slide the insert back into the rails before snapping the cap back on.",
        moved(("insert", "foil", "wire"), (0., SLIDE, 8.), (0., 0., 8.)))
    add("Snap Back On and Reconnect", "Check the cap moves freely, then reconnect the lead with a little slack.",
        mounting + [fit_cap(rest, weights=[float(t), 0.]) for t in np.linspace(0., 1., 18)], seconds=5)
    return {"label": "Removable copper insert", "actors": actors, "steps": steps,
            "concept": True, "openSeated": True,
            "annotations": [
                {"side": "left", "actor": "insert", "point": [0., TAB_REAR, 19.7], "title": "Hinge traps this tab"},
                {"side": "right", "actor": "wire", "point": [0., 7.55, 20.99], "title": "Lead exits over the hinge"},
            ],
            "status": "Fit and touch response still need testing.",
            "note": "18 × 17.3 mm cap. The 0.07 mm copper tape sits under a 1 mm insulating cover. The fixed connection is illustrative."}
