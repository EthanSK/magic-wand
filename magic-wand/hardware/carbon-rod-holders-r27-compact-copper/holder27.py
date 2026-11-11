#!/usr/bin/env python3
"""Compact copper carrier, with the OP1 board loaded from the two-key end."""

from functools import lru_cache
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
R26 = HERE.parent / "carbon-rod-holders-r26-dfrobot-centre"
sys.dont_write_bytecode = True
sys.path.insert(0, str(R26))
import copper26 as c
import holder26 as d

r = d.h.h22
box, union, mesh = d.box, d.union, d.mesh
# Ethan's "bottom" is the three-key row at Y=0. The two-key row is +Y.
BOTTOM_EDGE = -9.2
BOARD_STOP = -8.67
CLICK_SHIFT = 3.55
TOP_SPREAD = 3.7
REAR = 32.65
PIN_Y, PIN_Z = 31.28, 13.1
PIN_RADIUS = 1.0
BACK_STOP = 21.8
CLIP_Z = 9.36
BOARD_Y_OFFSET = CLICK_SHIFT + 2 * d.h.YC


def towards_top(shape):
    return shape.translate((0., CLICK_SHIFT, 0.))


def op1(shape):
    return shape.rotate((0, 0, 180)).translate((0., BOARD_Y_OFFSET, 0.))


def key_shift(index):
    side = -1 if index in (0, 3) else 1
    if index in d.LOWER_INDICES:
        return -side * d.LOWER_SHIFT, 0.
    return side * TOP_SPREAD, CLICK_SHIFT


def lead():
    points = [(0., 27.35, 6.9), (0., 30.5, 6.9), (0., 33.1, 6.5),
              (-2.3, 35.2, 5.7), (-5.9, 36.65, 3.1), (-7., 37.6, 2.1)]
    balls = [mf.Manifold.sphere(1.30, 20).translate(p) for p in points]
    return union(mf.Manifold.batch_hull([a, b]) for a, b in zip(balls, balls[1:]))


def keeper_bore():
    return d.axis_oval(PIN_Y, PIN_Z, PIN_RADIUS, -8.0, 8.0)


def pin():
    return d.axis_oval(PIN_Y, PIN_Z, .875, -6.8, 6.8)


def keeper():
    tongue = box(-1.48, 1.48, BACK_STOP, 32.12, CLIP_Z, 11.20)
    eye = box(-2.55, 2.55, 30.02, 32.46, 10.9, 14.45)
    return d.h.base.clean((tongue + eye) - keeper_bore(), "OP1_Rear_Keeper")


@lru_cache(maxsize=1)
def geometry():
    # Move the real pockets and all loaded/soldered Choc paths together.
    p = r.P
    p["keys"]["row_spacing"] += CLICK_SHIFT
    p["keys"]["upper_half_spacing"] += TOP_SPREAD
    slab = p["slab"]
    slab["upper_half_x_mm"] += TOP_SPREAD
    slab["front_y_mm"], slab["rear_y_mm"] = BOTTOM_EDGE, REAR
    rear_band = p["carrier_rings"]["rear_band_y_mm"]
    p["carrier_rings"]["rear_band_y_mm"] = [value + REAR - r.REAR for value in rear_band]
    p["carrier_rings"]["saddle_y_mm"][-1] = REAR
    r.REAR = REAR
    r.K["shoulder_curve"]["length_mm"] = 17.5

    working = {name: shape for name, shape in r.carrier_regions().items()
               if not name.startswith("key_1_")}
    base = r.carrier_base() + d.guard23.runners()
    # Long rear-loading slot below the fixed hinge. Push the separate switch
    # in vertically after loading the board, so the hinge can stay integral.
    deck = box(-7.1, 7.1, BOTTOM_EDGE, REAR, r.base.slab_bottom() - .01, 11.35)
    # Fill the old centre Choc clip recess before cutting the OP1 bay.
    old_relief = box(-7.94, 7.94, -7.28, 7.28, 8.85, 10.02)
    floor = d.wedge(-3.4, 3.4, [
        (-8.8, 4.38), (28.1, 4.38), (REAR, 8.2), (REAR, 9.25), (-8.8, 9.25),
    ])
    ears = d.mirrored(box(2.78, 6.7, 29.96, 32.57, 9.1, 14.50))
    middle = box(-5.46, 5.46, BOARD_STOP, 35., 9.18, 10.94)
    switch_slot = box(-3.22, 3.22, -4.17, 9.24, 10.88, 15.)
    pin_channel = box(-1.58, 1.58, -4.15, 35., 4.98, 9.24)
    plug_channel = box(-4.76, 4.76, 18.31, 35., 4.38, 9.24)
    keeper_space = box(-2.71, 2.71, BACK_STOP - .10, 34., 9.24, 14.8)
    shape = union((base, deck, old_relief, floor, ears, towards_top(d.spring_root()),
                   towards_top(d.spring_tongues()), towards_top(d.stop_posts())))
    shape -= union((middle, switch_slot, pin_channel, plug_channel,
                    keeper_space, keeper_bore(), working["unloaded_clip_bore"]))
    # All components stop at the same bottom plane, including the guards.
    shape ^= box(-40., 40., BOTTOM_EDGE, REAR, -12., 30.)
    return d.h.base.clean(r.spaces16.carve(shape, working, "carrier27"), "Compact_Key_Carrier"), working


def sample_overlap(fixed, moving, poses):
    return max((fixed ^ moving.translate(pose)).volume() for pose in poses)


def checks(carrier, working):
    board = op1(d.h.board())
    sockets = op1(d.h.barrels())
    plug = op1(d.h.plug())
    switch, plunger = (op1(part) for part in d.h.switch())
    installed_keys = union(working[f"key_{i}_{part}"] for i in (0, 2, 3, 4)
                           for part in ("switch", "maximum_socket"))
    cap_travel = union(working[f"key_{i}_cap_travel"] for i in (0, 2, 3, 4))
    fixed = carrier + installed_keys + cap_travel
    board_set = union((board, sockets, plug, lead()))
    rod = working["unloaded_clip_bore"]
    pinned_keeper = keeper() + pin()
    def travel(value):
        return np.linspace(0., value, 49)

    body = c.cap() + c.insert() + c.foil()
    parts = [(0., 0., z) for z in travel(8.)]
    rest_pose = d.pose(-d.REST).tolist()
    loose = towards_top((body + c.wire_solid(c.wire_centres())).transform(rest_pose))
    hinge = towards_top(d.spring_tongues())
    squeezed = (carrier - hinge) + towards_top(d.spring_tongues().warp_batch(lambda p: p + d.flex(p)))
    cap_fixed = fixed + board + switch + pinned_keeper
    result = {
        "bottom_plane_mm": BOTTOM_EDGE,
        "pcb_clear_of_bottom_mm": board.bounding_box()[1] - BOTTOM_EDGE,
        "click_hardware_clear_of_bottom_mm": min(
            part.bounding_box()[1] - BOTTOM_EDGE for part in (loose, board_set, switch, pinned_keeper)
        ),
        "choc_centres_mm": [list(p) for i, p in enumerate(r.base.key_positions()) if i != 1],
        "board_slide_overlap_mm3": sample_overlap(fixed + rod, board_set, [(0., y, 0.) for y in travel(42.)]),
        "switch_fit_overlap_mm3": sample_overlap(fixed + sockets + plug + pinned_keeper, switch + plunger, parts),
        "keeper_lift_overlap_mm3": sample_overlap(fixed + board_set, keeper(), parts),
        "keeper_pin_overlap_mm3": sample_overlap(fixed + board_set + keeper(), pin(), [(x, 0., 0.) for x in travel(17.)]),
        "snap_install_overlap_mm3": sample_overlap(squeezed + installed_keys + cap_travel + board + switch, loose, parts),
        "front_stop_contact_mm3": (carrier ^ board.translate((0., -.5, 0.))).volume(),
        "rear_stop_contact_mm3": (keeper() ^ board.translate((0., .6, 0.))).volume(),
        "board_rail_lift_contact_mm3": (carrier ^ board.translate((0., 0., .3))).volume(),
        "pin_holds_keeper_contact_mm3": (pin() ^ keeper().translate((0., 0., .4))).volume(),
        "minimum_hinge_lock_contact_mm3": float("inf"),
        "click_and_lead_overlap_mm3": 0.,
    }
    for t in np.linspace(0., 1., 25):
        pose = d.pose(-d.REST * (1. - t)).tolist()
        wire = c.wire_solid((1. - t) * c.wire_centres(-d.REST, True) + t * c.wire_centres(0., True))
        moved = towards_top((body + wire).transform(pose))
        result["click_and_lead_overlap_mm3"] = max(result["click_and_lead_overlap_mm3"], (moved ^ cap_fixed).volume())
        overlap = (towards_top(c.tab().translate((0., 1.1, 0.)).transform(pose)) ^ carrier).volume()
        result["minimum_hinge_lock_contact_mm3"] = min(result["minimum_hinge_lock_contact_mm3"], overlap)
    result["passed"] = (result["click_hardware_clear_of_bottom_mm"] > .5 and abs(carrier.bounding_box()[1] - BOTTOM_EDGE) < .001
                        and max(value for key, value in result.items() if key.endswith("overlap_mm3")) < .035
                        and min(value for key, value in result.items() if key.endswith("contact_mm3")) > .04)
    return result
