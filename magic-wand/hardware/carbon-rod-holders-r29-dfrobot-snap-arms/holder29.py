#!/usr/bin/env python3
"""R29: R28's DFRobot touch tray with the hinge ownership reversed.

The key holder carries two rigid supports with coaxial bores on R27's hinge
axis (world Y 10.1, Z 18.5). The touch tray carries two flexible arms. Each
arm ends in a rounded tab pointing outwards. Pinch the arms inwards, lower
the empty tray between the supports and let go: the tabs spring into the
bores. No loose hinge pin, and the key holder does not bend.

Everything else is R28: board rails, end stop, filament board keeper, the
rear-loaded OP1 board and its keeper, click stops, alignment and the six
finger guards. The tray is modelled in the R26 cap frame (hinge Y 6.55).
"""

from functools import lru_cache
import math
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "exports"
R28 = HERE.parent / "carbon-rod-holders-r28-dfrobot-touch"
sys.dont_write_bytecode = True
sys.path.insert(0, str(R28))
import holder28 as h28  # noqa: E402

k27, d, H, r = h28.k27, h28.d, h28.H, h28.r
box, union, mirrored = h28.box, h28.union, h28.mirrored
REVISION = HERE.name
world = h28.world
CLICK_SHIFT = h28.CLICK_SHIFT
AXIS_Y, AXIS_Z = d.HINGE_Y, d.HINGE_Z            # cap frame; world Y = AXIS_Y + CLICK_SHIFT

# Fixed supports on the key holder (world frame).
SUPPORT_X = (3.4, 5.5)        # inner face carries the bore mouth; stops 0.32 mm short of the stop feet
SUPPORT_HALF_Y = 1.5
SUPPORT_FRONT_EXTENSION = .45   # keeps material over the teardrop apex in the print direction
SUPPORT_TOP = 20.0
SUPPORT_ROOT = (3.4, 7.0, 11.05, 12.9)   # wide foot on the solid deck beside the OP1 slot
BORE_R = .9

# Flexible tray arms (cap frame). Cantilevers along Y, bending in X.
ARM_X = (1.85, 3.05)          # 1.2 mm thick
ARM_Z = (17.6, 19.0)          # 1.4 mm tall
ARM_FRONT = 5.75
ARM_ROOT_Y = 17.36            # joins the floor behind its window
TAB_R = .7
TAB_TIP = 4.1                 # 0.7 mm into the bore
TAB_CHAMFER = .25
PINCH = (9.0, 11.5, 20.0)     # raised pinch pads behind the supports, Y range and top
SQUEEZE = .98                 # tab movement inwards when pinched
E_PETG, YIELD_STRAIN = 2000., .04   # nominal PETG values for the estimate only


def tray_frame_support_y():
    return AXIS_Y - SUPPORT_HALF_Y - SUPPORT_FRONT_EXTENSION, AXIS_Y + SUPPORT_HALF_Y


def supports():
    """Two rigid supports with through bores, fixed to the key holder."""
    y0, y1 = (y + CLICK_SHIFT for y in tray_frame_support_y())
    x0, x1, z0, z1 = SUPPORT_ROOT
    column = box(*SUPPORT_X, y0, y1, z0, SUPPORT_TOP)
    foot = box(x0, x1, y0, y1, z0, z1)
    solid = mirrored(column + foot)
    # Rear-down printing puts -Y up, so each bore roof peaks towards -Y.
    bore = H.teardrop_x(BORE_R, SUPPORT_X[0] - .5, SUPPORT_X[1] + .5, AXIS_Y + CLICK_SHIFT, AXIS_Z, (-1., 0.))
    return solid - mirrored(bore)


def bores():
    """The bore openings only, for engagement measurements."""
    return mirrored(d.axis_oval(AXIS_Y + CLICK_SHIFT, AXIS_Z, BORE_R, *SUPPORT_X))


def arms():
    """Both flexible arms with their outward tabs and pinch pads (cap frame)."""
    arm = box(*ARM_X, ARM_FRONT, ARM_ROOT_Y + .6, *ARM_Z)
    pad = box(*ARM_X, PINCH[0], PINCH[1], ARM_Z[1] - .01, PINCH[2])
    straight = d.axis_oval(AXIS_Y, AXIS_Z, TAB_R, ARM_X[1] - .05, TAB_TIP - TAB_CHAMFER)
    tip = mf.Manifold.cylinder(TAB_CHAMFER, TAB_R, TAB_R - TAB_CHAMFER, 48).rotate((0, 90, 0))
    tip = tip.translate((TAB_TIP - TAB_CHAMFER, AXIS_Y, AXIS_Z))
    return mirrored(arm + pad + straight + tip)


def tray(nose):
    L = h28.layout(nose)
    n, rear, front, pin_y = L["nose"], L["rear"], L["board_front"], L["pin_y"]
    floor = box(-h28.INNER - .01, h28.INNER + .01, n, rear, *h28.FLOOR)
    walls = mirrored(box(h28.INNER, h28.CAP_HALF, n, rear, h28.FLOOR[1] - .01, h28.LIP[1]))
    ledges = mirrored(box(h28.LEDGE_X, h28.INNER + .01, n, rear, h28.FLOOR[1] - .01, h28.BOARD_Z[0]))
    lips = mirrored(box(h28.LIP_X, h28.CAP_HALF, n, rear, *h28.LIP))
    end_stop = box(-h28.CAP_HALF, h28.CAP_HALF, n, front, h28.FLOOR[0], h28.LIP[1])
    shape = union((floor, walls, ledges, lips, end_stop)) ^ h28._plate(n, rear, h28.LIP[1])
    ears = mirrored(box(h28.INNER, h28.CAP_HALF, pin_y - h28.EAR_HALF_Y, rear, h28.LIP[0], h28.EAR_TOP))
    shape += ears ^ h28._plate(n, rear, h28.EAR_TOP)
    s0, s1 = tray_frame_support_y()
    z0, z1 = h28.FLOOR[0] - .3, h28.FLOOR[1] + .3
    openings = union((
        box(-3.35, 3.35, 4.0, ARM_ROOT_Y, z0, z1),             # free space round both arms
        box(-5.85, 5.85, s0 - .45, s1 + .45, z0, z1),          # supports pass up through the floor
        box(-5.5, 5.5, PINCH[0] - .6, PINCH[1] + .5, z0, z1),  # finger/tweezer room at the pinch pads
        box(-4.0, 4.0, 9.39, front + 29.0, z0, z1),            # R28 Gravity solder relief
    ))
    shape -= openings
    # R26 pusher and stop feet. The old R26 hinge ears and their bores are gone.
    old = d.paddle() ^ box(-7.95, 7.95, -4.1, 4.72, 12.95, 19.20)
    old -= mirrored(box(1.6, 6.0, 3.9, 9.0, 12., 21.))
    shape = union((shape, old, arms()))
    shape -= d.axis_oval(pin_y, h28.PIN_Z, h28.BORE_R, -13., 13.)
    return H.base.clean(shape, "DFRobot_Touch_Tray")


def arm_bend(points, amount=1.):
    """Inward bend of both arms, as a cantilever from the root (cap frame).

    Selects only arm, pad and tab vertices. The tab moves SQUEEZE * amount.
    """
    p = np.asarray(points, float)
    x, y, z = p.T
    in_arm = (abs(x) >= ARM_X[0] - .01) & (abs(x) <= ARM_X[1] + .01)
    in_tab = (abs(x) > ARM_X[1]) & (abs(x) <= TAB_TIP + .01) & (abs(y - AXIS_Y) <= TAB_R + .01) & (abs(z - AXIS_Z) <= TAB_R + .01)
    chosen = (in_arm | in_tab) & (y >= ARM_FRONT - .01) & (y <= ARM_ROOT_Y + .61) & (z >= ARM_Z[0] - .01) & (z <= PINCH[2] + .01)
    length = ARM_ROOT_Y - AXIS_Y
    s = np.clip((ARM_ROOT_Y - y) / length, 0., None)
    shape = np.where(s <= 1., s * s * (3. - s) / 2., 1. + 1.5 * (s - 1.))
    shift = -np.sign(x) * SQUEEZE * amount * shape * chosen
    return np.column_stack((shift, 0. * y, 0. * z))


def bent(shape, amount=1.):
    return shape.warp_batch(lambda q: q + arm_bend(q, amount))


@lru_cache(maxsize=1)
def nose_y():
    nose = h28.FIRST_NOSE
    for _ in range(3):
        nose += (h28.OUTER_CAP_BOTTOM - world(tray(nose)).bounding_box()[1]) / d.pose(-d.REST)[1, 1]
    return round(nose, 5)


@lru_cache(maxsize=1)
def cap():
    return tray(nose_y())


def arm_estimate():
    """Cantilever estimate for the pinch, nominal PETG only."""
    t, h = ARM_X[1] - ARM_X[0], ARM_Z[1] - ARM_Z[0]
    length = ARM_ROOT_Y - AXIS_Y
    a = ARM_ROOT_Y - (PINCH[0] + PINCH[1]) / 2           # pinch point from the root
    at_pad = SQUEEZE * 2 * a / (3 * length - a)           # pad movement for SQUEEZE at the tab
    inertia = h * t ** 3 / 12
    force = 3 * E_PETG * inertia * at_pad / a ** 3
    strain = 3 * at_pad * t / (2 * a ** 2)
    return {"arm_thickness_mm": round(t, 3), "arm_height_mm": round(h, 3), "root_to_tab_mm": round(length, 3),
            "root_to_pinch_pad_mm": round(a, 3), "tab_squeeze_mm": SQUEEZE, "pad_squeeze_mm": round(at_pad, 3),
            "pinch_force_each_N_estimate": round(force, 2), "root_strain_percent_estimate": round(100 * strain, 2),
            "assumed_PETG_modulus_MPa": E_PETG, "assumed_PETG_yield_strain_percent": 100 * YIELD_STRAIN}


@lru_cache(maxsize=1)
def geometry():
    """R28's carrier with R27's spring tongues replaced by two rigid supports."""
    p = r.P
    assert (p["keys"]["pitch"], p["keys"]["upper_half_spacing"], p["keys"]["row_spacing"]) == (18.7, 9.35, 17.8)
    assert r.carrier_base.cache_info().currsize == 0
    KEY_X, REAR, BOTTOM_EDGE = h28.KEY_X, h28.REAR, h28.BOTTOM_EDGE
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
    base = r.carrier_base() + h28.runners()
    deck = box(-7.1, 7.1, BOTTOM_EDGE, REAR, r.base.slab_bottom() - .01, 11.35)
    old_relief = box(-7.94, 7.94, -7.28, 7.28, 8.85, 10.02)
    floor = d.wedge(-3.4, 3.4, [(-8.8, 4.38), (28.1, 4.38), (REAR, 8.2), (REAR, 9.25), (-8.8, 9.25)])
    ears = mirrored(box(2.78, 6.7, 29.96, 32.57, 9.1, 14.50))
    middle = box(-5.46, 5.46, k27.BOARD_STOP, 35., 9.18, 10.94)
    switch_slot = box(-3.22, 3.22, -4.17, 9.24, 10.88, 15.)
    pin_channel = box(-1.58, 1.58, -4.15, 35., 4.98, 9.24)
    plug_channel = box(-4.76, 4.76, 18.31, 35., 4.38, 9.24)
    keeper_space = box(-2.71, 2.71, k27.BACK_STOP - .10, 34., 9.24, 14.8)
    shape = union((base, deck, old_relief, floor, ears, supports(), k27.towards_top(d.stop_posts())))
    shape -= union((middle, switch_slot, pin_channel, plug_channel, keeper_space,
                    k27.keeper_bore(), working["unloaded_clip_bore"]))
    shape ^= box(-40., 40., BOTTOM_EDGE, REAR, -12., 30.)
    return H.base.clean(r.spaces16.carve(shape, working, "carrier29"), "Key_Carrier"), working


def _vol(shape):
    return round(float(shape.volume()), 6)


def _max(pairs):
    return round(max(float((a ^ b).volume()) for a, b in pairs), 6)


def checks(carrier, working):
    assert abs(nose_y() - h28.nose_y()) < 1e-6, "R29 must keep R28's front alignment"
    op1_board, sockets, plug = (k27.op1(part) for part in (H.board(), H.barrels(), H.plug()))
    switch, plunger = (k27.op1(part) for part in H.switch())
    installed = union(working[f"key_{i}_{part}"] for i in (0, 2, 3, 4) for part in ("switch", "maximum_socket"))
    travel = union(working[f"key_{i}_cap_travel"] for i in (0, 2, 3, 4))
    fixed = union((carrier, installed, travel, op1_board, sockets, plug, switch,
                   k27.keeper(), k27.pin(), k27.lead()))
    cover = cap()
    board, plug_box, pin, lead = h28.sensor(), h28.connector(), h28.touch_pin(), h28.gravity_lead()
    touch = board + plug_box
    group = union((cover, touch, pin))
    angles = np.linspace(-d.REST, 0., 25)
    released = world(cover).bounding_box()
    squeezed = bent(cover)
    tabs = mirrored(d.axis_oval(AXIS_Y, AXIS_Z, TAB_R, ARM_X[1], TAB_TIP))
    tabs_world = [world(tabs, a) for a in (-d.REST, 0.)]
    inside_bore = [_vol(t ^ bores()) for t in tabs_world]
    tab_plan = [world(tabs, a).bounding_box() for a in (-d.REST, 0.)]
    # Tab reach, measured on the released and bent CAD itself (+X side).
    tab_box = box(2.4, TAB_TIP + .5, AXIS_Y - TAB_R - .1, AXIS_Y + TAB_R + .1, AXIS_Z - TAB_R - .1, AXIS_Z + TAB_R + .1)
    squeezed_tip = (squeezed ^ tab_box).bounding_box()[3]
    released_tip = (cover ^ tab_box).bounding_box()[3]
    arm_zone = box(0., 9., ARM_FRONT, ARM_ROOT_Y - .1, ARM_Z[0], ARM_Z[1])
    squeezed_inner = (squeezed ^ arm_zone).bounding_box()[0]
    lifted = union((carrier, installed, travel, op1_board, switch, k27.keeper(), k27.pin()))
    snap = [world(squeezed).translate((0., 0., z)) for z in np.linspace(8., 0., 33)]
    release = [world(bent(cover, t)) for t in np.linspace(1., 0., 11)]
    lift = {f"{z:.2f}": _vol(world(cover).translate((0., 0., z)) ^ lifted) for z in (.1, .2, .25, .3, .5, 1.)}
    overpress = world(cover, .25)
    posts = k27.towards_top(d.stop_posts()).decompose()
    rim = {
        "bore_radius_mm": BORE_R, "tab_radius_mm": TAB_R, "radial_clearance_mm": round(BORE_R - TAB_R, 3),
        "wall_above_bore_mm": round(SUPPORT_TOP - AXIS_Z - BORE_R, 3),
        "wall_at_print_roof_apex_mm": round(SUPPORT_HALF_Y + SUPPORT_FRONT_EXTENSION - BORE_R * math.sqrt(2), 3),
        "wall_behind_bore_mm": round(SUPPORT_HALF_Y - BORE_R, 3),
        "support_through_length_mm": round(SUPPORT_X[1] - SUPPORT_X[0], 3),
        "support_column_section_mm": [round(SUPPORT_X[1] - SUPPORT_X[0], 3), 2 * SUPPORT_HALF_Y + SUPPORT_FRONT_EXTENSION],
        "support_to_stop_foot_gap_mm": round(5.82 - SUPPORT_X[1], 3),
    }
    result = {
        "hinge_axis_world_mm": [round(AXIS_Y + CLICK_SHIFT, 4), AXIS_Z],
        "nose_matches_r28": True,
        "released_front_mm": round(released[1], 6),
        "released_front_alignment_error_mm": round(abs(released[1] - h28.OUTER_CAP_BOTTOM), 6),
        "min_front_clear_of_bottom_over_stroke_mm": round(min(world(cover + board, a).bounding_box()[1] for a in angles) - h28.BOTTOM_EDGE, 6),
        "touch_face_top_released_max_mm": round(world(cover + board).bounding_box()[5], 4),
        "released_tab_axial_engagement_mm": round(released_tip - SUPPORT_X[0], 4),
        "squeezed_tab_clear_of_support_mm": round(SUPPORT_X[0] - squeezed_tip, 4),
        "squeezed_arm_gap_between_arms_mm": round(2 * squeezed_inner, 4),
        "tab_inside_bore_released_and_pressed_mm3": inside_bore,
        "tab_world_x_extent_mm": [round(b[3], 4) for b in tab_plan],
        "bore_rim": rim,
        "arm": arm_estimate(),
        "click_stroke_overlap_mm3": _max((world(group, a), fixed) for a in angles),
        "lead_stroke_overlap_mm3": _max((world(lead, a), fixed + world(cover, a)) for a in angles),
        "squeezed_lowering_overlap_mm3": _max((s, lifted) for s in snap),
        "arm_release_overlap_mm3": _max((s, lifted) for s in release),
        "board_slide_tray_overlap_mm3": _max((cover, touch.translate((0., y, 0.))) for y in np.linspace(0., 42., 49)),
        "board_slide_fixed_overlap_mm3": _max((world(touch, local=(0., y, 0.)), fixed) for y in np.linspace(0., 42., 49)),
        "pin_slide_overlap_mm3": _max((world(pin, local=(x, 0., 0.)), fixed + world(cover + touch)) for x in np.linspace(0., 26., 27)),
        "seated_pin_to_tray_and_board_overlap_mm3": _vol(pin ^ (cover + touch)),
        "straight_lift_contact_by_height_mm3": lift,
        "straight_lift_retention_contact_mm3": lift["0.30"],
        "front_stop_contact_mm3": _vol(cover ^ board.translate((0., -.5, 0.))),
        "rear_pin_stop_contact_mm3": _vol(pin ^ board.translate((0., .4, 0.))),
        "board_lift_lip_contact_mm3": _vol(cover ^ board.translate((0., 0., .3))),
        "overpress_stop_contacts_mm3": [_vol(overpress ^ post) for post in posts],
        "guard_runners": dict(h28.RUNNERS),
        "nominal_click_stop_depression_mm": d.DEPRESSION,
    }
    overlaps = [v for k, v in result.items() if k.endswith("overlap_mm3")]
    contacts = [v for k, v in result.items() if k.endswith("contact_mm3") and not isinstance(v, dict)]
    result["passed"] = bool(
        max(overlaps) < .035 and min(contacts) > .04
        and min(result["overpress_stop_contacts_mm3"]) > .01 and len(result["overpress_stop_contacts_mm3"]) == 2
        and result["released_tab_axial_engagement_mm"] >= .6
        and result["squeezed_tab_clear_of_support_mm"] > .2
        and rim["wall_at_print_roof_apex_mm"] >= .6
        and result["squeezed_arm_gap_between_arms_mm"] > 1.
        and min(inside_bore) > .5
        and lift["0.10"] < .035
        and result["released_front_alignment_error_mm"] < .001
        and result["min_front_clear_of_bottom_over_stroke_mm"] > .15
        and result["arm"]["root_strain_percent_estimate"] < 2.
        and len(result["guard_runners"]) == 6)
    return result
