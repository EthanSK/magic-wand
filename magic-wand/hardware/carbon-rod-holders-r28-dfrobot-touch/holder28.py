#!/usr/bin/env python3
"""R28: the bought DFR0030 board is the centre touch face on R27's OP1 click.

Assembly frame: X across, +Y towards the two-key top, +Z up from the rod
centre. Ethan's "bottom" is the three-key row. The tray is modelled in the
R26 cap frame, like R27's cap, and placed with towards_top(pose(angle)).
The R27 OP1 board slot, rear keeper, snap hinge, stops and heights are reused.
DFR0030 thickness, connector, underside parts and OP1 parts are estimates.
"""

from functools import lru_cache
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "exports"
R27 = HERE.parent / "carbon-rod-holders-r27-compact-copper"
sys.dont_write_bytecode = True
sys.path.insert(0, str(R27))
import holder27 as k27  # noqa: E402

d, H = k27.d, k27.d.h
r = H.h22
box, union, mirrored = d.box, d.union, d.mirrored
REVISION = HERE.name

CLICK_SHIFT = k27.CLICK_SHIFT
BOTTOM_EDGE = k27.BOTTOM_EDGE          # flat lower plane of the carrier
REAR = k27.REAR
OUTER_CAP_BOTTOM = k27.OUTER_CAP_BOTTOM  # Choc cap fronts, Y -8.75
CHOC_HALF_X = 16.6 / 2
CHOC_TOP = 19.92

# DFRobot DFR0030 V2: published 22 x 30 mm. 1.6 mm thickness is assumed.
BOARD_HALF, BOARD_LENGTH, BOARD_THICKNESS = 11.0, 30.0, 1.6
SIDE_PLAY = .24
INNER = BOARD_HALF + SIDE_PLAY          # 11.24
WALL = .86
CAP_HALF = round(INNER + WALL, 3)       # 12.1
KEY_CLEARANCE = .7                       # R26's centre-to-Choc side clearance
KEY_X = round(CAP_HALF + KEY_CLEARANCE + CHOC_HALF_X, 3)   # 21.1, all four Chocs
UPPER_Y = 17.8 + CLICK_SHIFT             # R27 row spacing, unchanged

# Heights at the hard stop (pose angle 0), matching R26's board and floor.
FLOOR = (18.5, 19.4)
BOARD_Z = (20.25, 20.25 + BOARD_THICKNESS)
LIP = (22.05, 22.55)
LEDGE_X, LIP_X = 10.26, 10.27
NOSE_WALL = .7
END_PLAY = .1
PIN_R, BORE_R = .875, 1.0
PIN_Z = 22.05
EAR_TOP = 23.45
EAR_HALF_Y = 1.4
FIRST_NOSE = -12.3


def world(shape, angle=None, local=(0., 0., 0.)):
    """Cap-frame shape placed at a click angle. Default is released."""
    angle = -d.REST if angle is None else angle
    return k27.towards_top(shape.translate(local).transform(d.pose(angle).tolist()))


def layout(nose):
    front = nose + NOSE_WALL
    back = front + BOARD_LENGTH
    pin_y = back + END_PLAY + PIN_R
    return {"nose": nose, "board_front": front, "board_rear": back, "pin_y": pin_y, "rear": pin_y + EAR_HALF_Y}


def _plate(nose, rear, top):
    return H.rounded_plate(CAP_HALF, nose, rear, FLOOR[0], top, r_plan=1.2, r_top=.3)


def tray(nose):
    L = layout(nose)
    n, rear, front, pin_y = L["nose"], L["rear"], L["board_front"], L["pin_y"]
    # The side walls start at the floor top. When released, the rear dips
    # beside the upper Choc caps, whose travel envelope is 18.3 mm wide.
    floor = box(-INNER - .01, INNER + .01, n, rear, *FLOOR)
    walls = mirrored(box(INNER, CAP_HALF, n, rear, FLOOR[1] - .01, LIP[1]))
    ledges = mirrored(box(LEDGE_X, INNER + .01, n, rear, FLOOR[1] - .01, BOARD_Z[0]))
    lips = mirrored(box(LIP_X, CAP_HALF, n, rear, *LIP))
    # Fixed end stop at the flat bottom. The board slides in from the top.
    end_stop = box(-CAP_HALF, CAP_HALF, n, front, FLOOR[0], LIP[1])
    shape = union((floor, walls, ledges, lips, end_stop)) ^ _plate(n, rear, LIP[1])
    # Pin ears stand above the lips so the released pin clears the upper caps.
    ears = mirrored(box(INNER, CAP_HALF, pin_y - EAR_HALF_Y, rear, LIP[0], EAR_TOP)) ^ _plate(n, rear, EAR_TOP)
    shape += ears
    # Floor opening over the integral hinge tongues, joined to a window under
    # the Gravity connector's estimated solder pins.
    hinge = mf.Manifold.extrude(r.poly([(-2.0, 9.4), (-2.0, 5.0), (0., 3.0), (2.0, 5.0), (2.0, 9.4)]), 1.3)
    plug_relief = box(-4.0, 4.0, 9.39, front + 29.0, FLOOR[0] - .2, FLOOR[1] + .1)
    shape -= hinge.translate((0., 0., FLOOR[0] - .2)) + plug_relief
    # R26 pusher, stop feet and hinge ears, exactly as R27's copper cap uses them.
    old = d.paddle()
    click = old ^ box(-7.95, 7.95, -4.1, 4.72, 12.95, 19.20)
    hinge_ears = old ^ mirrored(box(1.95, 4.02, 4.6, 8.22, 16.98, 19.45))
    shape = union((shape, click, hinge_ears))
    bores = mirrored(H.teardrop_x(d.BORE_R, d.ARM_INNER - .05, d.ARM_OUTER + .6, d.HINGE_Y, d.HINGE_Z, (-1., 0.)))
    shape -= bores + d.axis_oval(pin_y, PIN_Z, BORE_R, -13., 13.)
    return H.base.clean(shape, "DFRobot_Touch_Tray")


@lru_cache(maxsize=1)
def nose_y():
    """Put the released tray's foremost point on the Choc cap fronts."""
    nose = FIRST_NOSE
    for _ in range(3):
        released = world(tray(nose)).bounding_box()[1]
        nose += (OUTER_CAP_BOTTOM - released) / d.pose(-d.REST)[1, 1]
    return round(nose, 5)


@lru_cache(maxsize=1)
def cap():
    return tray(nose_y())


def sensor():
    L = layout(nose_y())
    return box(-BOARD_HALF, BOARD_HALF, L["board_front"], L["board_rear"], *BOARD_Z)


def _from_r26(y):
    """R26 board-local Y, turned 180 degrees so the pad is at the bottom."""
    return layout(nose_y())["board_front"] + (d.BOARD_REAR - y)


def electrode():
    return box(-9.75, 9.75, _from_r26(4.77), _from_r26(-8.35), BOARD_Z[1] - .01, BOARD_Z[1] + .07)


def connector():
    x0, x1, y0, y1, _, z1 = d.CONNECTOR
    return box(x0, x1, _from_r26(y1), _from_r26(y0), BOARD_Z[1], z1 - d.BOARD_BOTTOM + BOARD_Z[0])


def gravity_lead():
    """Slack Gravity lead leaving the plug towards the top, then down behind it."""
    f = layout(nose_y())["board_front"]
    points = [(0., f + 26., 24.3), (0., f + 33.5, 24.3), (2.5, f + 36.5, 23.),
              (6.5, f + 38.5, 19.5), (9., f + 40., 16.)]
    balls = [mf.Manifold.sphere(1.25, 20).translate(p) for p in points]
    return union(mf.Manifold.batch_hull([a, b]) for a, b in zip(balls, balls[1:]))


def touch_pin():
    L = layout(nose_y())
    return d.axis_oval(L["pin_y"], PIN_Z, PIN_R, -CAP_HALF, CAP_HALF)


RUNNERS = {}


def runners():
    """R23's reinforced runner paths adjusted for the wider R28 key layout."""
    # The wider upper-left socket blocks the old roots. Mirror the right
    # paths, stopping the middle runner before the socket and taking the
    # outer runner around its far side.
    right = [beam for beam in r.G["beams"] if beam["name"].startswith("R")]
    left = [{**beam, "name": "L" + beam["name"][1:],
             "plan_y_x_mm": [[y, -x] for y, x in beam["plan_y_x_mm"]]} for beam in right]
    inner, middle, outer = left
    middle = {**middle, "root_y_mm": 12.0,
              "plan_y_x_mm": [[12.0, middle["plan_y_x_mm"][0][1]], *middle["plan_y_x_mm"][1:]]}
    outer = {**outer, "root_y_mm": 16.0, "plan_y_x_mm": [[16.0, -28.3], [-9.0, -28.3]]}
    grown = []
    for beam in (*right, inner, middle, outer):
        solid, stats, _ = d.guard23._grow([beam])
        assert not solid.is_empty(), f'Empty finger guard runner: {beam["name"]}'
        RUNNERS[beam["name"]] = {"volume_mm3": round(solid.volume(), 3),
                                 "root_y_mm": beam["root_y_mm"], **stats}
        grown.append(solid)
    return union(grown)


@lru_cache(maxsize=1)
def geometry():
    """R27's carrier with all four Choc centres at X +-21.1."""
    p = r.P
    assert (p["keys"]["pitch"], p["keys"]["upper_half_spacing"], p["keys"]["row_spacing"]) == (18.7, 9.35, 17.8)
    assert r.carrier_base.cache_info().currsize == 0
    slab = p["slab"]
    slab["lower_half_x_mm"] += KEY_X - p["keys"]["pitch"]
    slab["upper_half_x_mm"] += KEY_X - p["keys"]["upper_half_spacing"]
    p["keys"]["pitch"] = p["keys"]["upper_half_spacing"] = KEY_X
    p["keys"]["row_spacing"] += CLICK_SHIFT
    slab["front_y_mm"], slab["rear_y_mm"] = BOTTOM_EDGE, REAR
    rear_band = p["carrier_rings"]["rear_band_y_mm"]
    p["carrier_rings"]["rear_band_y_mm"] = [value + REAR - r.REAR for value in rear_band]
    p["carrier_rings"]["saddle_y_mm"][-1] = REAR
    r.REAR = REAR
    r.K["shoulder_curve"]["length_mm"] = 17.5

    working = {name: shape for name, shape in r.carrier_regions().items() if not name.startswith("key_1_")}
    base = r.carrier_base() + runners()
    # Below this line, R27's OP1 slot, keeper seat and hinge, unchanged.
    deck = box(-7.1, 7.1, BOTTOM_EDGE, REAR, r.base.slab_bottom() - .01, 11.35)
    old_relief = box(-7.94, 7.94, -7.28, 7.28, 8.85, 10.02)
    floor = d.wedge(-3.4, 3.4, [(-8.8, 4.38), (28.1, 4.38), (REAR, 8.2), (REAR, 9.25), (-8.8, 9.25)])
    ears = mirrored(box(2.78, 6.7, 29.96, 32.57, 9.1, 14.50))
    middle = box(-5.46, 5.46, k27.BOARD_STOP, 35., 9.18, 10.94)
    switch_slot = box(-3.22, 3.22, -4.17, 9.24, 10.88, 15.)
    pin_channel = box(-1.58, 1.58, -4.15, 35., 4.98, 9.24)
    plug_channel = box(-4.76, 4.76, 18.31, 35., 4.38, 9.24)
    keeper_space = box(-2.71, 2.71, k27.BACK_STOP - .10, 34., 9.24, 14.8)
    shape = union((base, deck, old_relief, floor, ears, k27.towards_top(d.spring_root()),
                   k27.towards_top(d.spring_tongues()), k27.towards_top(d.stop_posts())))
    shape -= union((middle, switch_slot, pin_channel, plug_channel, keeper_space,
                    k27.keeper_bore(), working["unloaded_clip_bore"]))
    shape ^= box(-40., 40., BOTTOM_EDGE, REAR, -12., 30.)
    return H.base.clean(r.spaces16.carve(shape, working, "carrier28"), "Key_Carrier"), working


def _max_overlap(pairs):
    return round(max(float((a ^ b).volume()) for a, b in pairs), 6)


def checks(carrier, working):
    L = layout(nose_y())
    op1_board, sockets, plug = (k27.op1(part) for part in (H.board(), H.barrels(), H.plug()))
    switch, plunger = (k27.op1(part) for part in H.switch())
    installed = union(working[f"key_{i}_{part}"] for i in (0, 2, 3, 4) for part in ("switch", "maximum_socket"))
    travel = union(working[f"key_{i}_cap_travel"] for i in (0, 2, 3, 4))
    op1_fixed = union((op1_board, sockets, plug, switch, k27.keeper(), k27.pin(), k27.lead()))
    fixed = union((carrier, installed, travel, op1_fixed))
    cover, board, plug_box, pin, lead = cap(), sensor(), connector(), touch_pin(), gravity_lead()
    touch = board + plug_box
    group = union((cover, touch, pin))
    angles = np.linspace(-d.REST, 0., 25)
    stroke = [world(group, a) for a in angles]
    released = world(cover).bounding_box()
    tongues = k27.towards_top(d.spring_tongues())
    squeezed = (carrier - tongues) + k27.towards_top(d.spring_tongues().warp_batch(lambda q: q + d.flex(q)))
    lifted_fixed = union((squeezed, installed, travel, op1_board, switch, k27.keeper(), k27.pin()))
    overpress = world(cover, .25)
    posts = k27.towards_top(d.stop_posts()).decompose()
    rest_pin = world(pin).bounding_box()
    result = {
        "choc_centres_mm": [list(map(float, q)) for i, q in enumerate(r.base.key_positions()) if i != 1],
        "lower_shift_from_r27_each_mm": round(KEY_X - 18.7, 3),
        "upper_shift_from_r27_each_mm": round(KEY_X - 13.05, 3),
        "upper_row_y_mm": UPPER_Y,
        "tray_half_width_mm": CAP_HALF,
        "side_clearance_to_choc_caps_mm": round(KEY_X - CHOC_HALF_X - CAP_HALF, 3),
        "board_y_hard_stop_mm": [round(L["board_front"] + CLICK_SHIFT, 4), round(L["board_rear"] + CLICK_SHIFT, 4)],
        "board_z_hard_stop_mm": list(BOARD_Z),
        "lip_underside_clearance_mm": round(LIP[0] - BOARD_Z[1], 3),
        "underside_relief_to_floor_mm": round(BOARD_Z[0] - FLOOR[1], 3),
        "released_front_mm": round(released[1], 6),
        "outer_cap_front_mm": OUTER_CAP_BOTTOM,
        "released_front_alignment_error_mm": round(abs(released[1] - OUTER_CAP_BOTTOM), 6),
        "min_front_clear_of_bottom_over_stroke_mm": round(min(world(cover + board, a).bounding_box()[1] for a in angles) - BOTTOM_EDGE, 6),
        "tray_top_hard_stop_mm": round(cover.bounding_box()[5], 4),
        "touch_face_top_released_max_mm": round(world(cover + board).bounding_box()[5], 4),
        "r27_cap_top_released_mm": 23.395,
        "connector_envelope_top_max_mm": round(max(world(plug_box, a).bounding_box()[5] for a in angles), 4),
        "released_pin_clear_above_choc_tops_mm": round(rest_pin[2] - CHOC_TOP, 4),
        "click_stroke_overlap_mm3": _max_overlap((s, fixed) for s in stroke),
        "lead_stroke_overlap_mm3": _max_overlap((world(lead, a), fixed + world(cover, a)) for a in angles),
        "snap_on_empty_tray_overlap_mm3": _max_overlap((world(cover).translate((0., 0., z)), lifted_fixed)
                                                       for z in np.linspace(0., 8., 25)),
        "board_slide_tray_overlap_mm3": _max_overlap((cover, touch.translate((0., y, 0.))) for y in np.linspace(0., 42., 49)),
        "board_slide_fixed_overlap_mm3": _max_overlap((world(touch, local=(0., y, 0.)), fixed) for y in np.linspace(0., 42., 49)),
        "pin_slide_overlap_mm3": _max_overlap((world(pin, local=(x, 0., 0.)), fixed + world(cover + touch))
                                              for x in np.linspace(.0, 26., 27)),
        "seated_pin_to_tray_and_board_overlap_mm3": round(float((pin ^ (cover + touch)).volume()), 6),
        "front_stop_contact_mm3": round(float((cover ^ board.translate((0., -.5, 0.))).volume()), 5),
        "rear_pin_stop_contact_mm3": round(float((pin ^ board.translate((0., .4, 0.))).volume()), 5),
        "board_lift_lip_contact_mm3": round(float((cover ^ board.translate((0., 0., .3))).volume()), 5),
        "board_side_rail_contact_mm3": round(float((cover ^ board.translate((.4, 0., 0.))).volume()), 5),
        "pin_lift_contact_mm3": round(float((cover ^ pin.translate((0., 0., .3))).volume()), 5),
        "overpress_stop_contacts_mm3": [round(float((overpress ^ post).volume()), 5) for post in posts],
        "guard_runners": dict(RUNNERS),
        "nominal_click_stop_depression_mm": d.DEPRESSION,
        "click_rotation_released_deg": round(d.REST, 4),
    }
    overlaps = [v for k, v in result.items() if k.endswith("overlap_mm3")]
    contacts = [v for k, v in result.items() if k.endswith("contact_mm3")]
    result["passed"] = bool(
        max(overlaps) < .035 and min(contacts) > .04
        and len(result["overpress_stop_contacts_mm3"]) == 2 and min(result["overpress_stop_contacts_mm3"]) > .01
        and result["released_front_alignment_error_mm"] < .001
        and result["min_front_clear_of_bottom_over_stroke_mm"] > .15
        and result["released_pin_clear_above_choc_tops_mm"] > .2
        and result["side_clearance_to_choc_caps_mm"] >= .7
        and abs(carrier.bounding_box()[1] - BOTTOM_EDGE) < .001)
    return result
