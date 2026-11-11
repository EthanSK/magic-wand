#!/usr/bin/env python3
"""R31: a small hinged bracket holds the DFR0030 V2 through its two holes.

Two fixed supports and their matching flexible arms sit farther towards
the two-key end. The R26 pusher and stop feet are kept. The OP1 board
uses removable nonconductive tape at the rear of its slot. The R28/R29 perimeter tray, walls, lips, end
stop and filament board keeper are gone. The board sits on two seat rails
and two posts go up through its mounting holes. A small printed clip snaps
onto each post's neck above the board.

DFR0030 V2 dimensions (see README): the 22 mm width and 3 mm nominal holes
are published. The 35 mm length follows a distributor sheet. The 15-16 mm
hole pitch, hole position and 1.6 mm thickness are photo-derived or assumed.
The posts are narrow across the pitch, so a board with a 15.0-16.0 mm pitch
still fits. The bracket is modelled in the R26 cap frame.
"""

from functools import lru_cache
import math
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "exports"
R29 = HERE.parent / "carbon-rod-holders-r29-dfrobot-snap-arms"
sys.dont_write_bytecode = True
sys.path.insert(0, str(R29))
import holder29 as h29  # noqa: E402

h28, k27, d, H = h29.h28, h29.k27, h29.d, h29.H
box, union, mirrored = h29.box, h29.union, h29.mirrored
REVISION = HERE.name
CLICK_SHIFT = h29.CLICK_SHIFT
HINGE_SHIFT = k27.REAR - CLICK_SHIFT - h29.SUPPORT_HALF_Y - h29.AXIS_Y  # Ethan's "further up" is towards the two-key end.
AXIS_Y, AXIS_Z = h29.AXIS_Y + HINGE_SHIFT, h29.AXIS_Z
REST = math.degrees(math.asin(d.DEPRESSION / (AXIS_Y - d.PUSH_Y)))
ARM_ROOT_Y = AXIS_Y - (h29.ARM_ROOT_Y - h29.AXIS_Y)
ARM_OFFSET = np.array([0., HINGE_SHIFT, 0.])
ARM_MIRROR_Y = AXIS_Y + h29.AXIS_Y
PINCH_Y = (ARM_MIRROR_Y - h29.PINCH[1], ARM_MIRROR_Y - h29.PINCH[0])


def placement(angle=None, local=(0., 0., 0.), lift=0.):
    angle = -REST if angle is None else angle
    transform = d.pose(angle)
    basis = transform[:, :3]
    transform[:, 3] += ARM_OFFSET - basis @ ARM_OFFSET + basis @ np.asarray(local)
    transform[:, 3] += [0., CLICK_SHIFT, lift]
    return transform


def world(shape, angle=None):
    return shape.transform(placement(angle).tolist())


def supports():
    return h29.supports().translate(tuple(ARM_OFFSET))


def arms():
    return h29.arms().mirror((0., 1., 0.)).translate((0., ARM_MIRROR_Y, 0.))


def arm_bend(points, amount=1.):
    points = np.asarray(points)
    original = points.copy()
    original[:, 1] = ARM_MIRROR_Y - original[:, 1]
    return h29.arm_bend(original, amount)


def bent(shape, amount=1.):
    return shape.warp_batch(lambda points: points + arm_bend(points, amount))


# DFR0030 V2 (assumed or photo-derived unless stated).
BOARD_HALF = 11.0                 # published 22 mm width
BOARD_LENGTH = 35.0               # distributor sheet; the maker's page says 30
BOARD_Z = h28.BOARD_Z             # 20.25-21.85 at the hard stop, 1.6 mm assumed
HOLE_D = 3.0                      # published nominal; photos suggest 3.2-3.4
HOLE_PITCH = 15.5                 # photos 15.0-16.0
PITCH_RANGE = (15.0, 16.0)
HOLE_FROM_PAD = 24.1              # hole centres from the gold-pad end (photos)
POST_X = HOLE_PITCH / 2

# Posts: narrow across the pitch so they float, close fit along the board.
# Section: round towards +Y, pointed towards -Y. The bracket prints front (-Y)
# face down, so each post is a horizontal boss with its point underneath,
# like a teardrop hole.
POST_W, POST_L = 2.25, 2.52         # X, Y
NECK_R = .85
SEAT_TOP = BOARD_Z[0]
NECK = (BOARD_Z[1], BOARD_Z[1] + 1.0)   # room for up to a 1.8 mm board under the clip
HEAD_TOP = NECK[1] + .8

# Snap clip, printed flat. The open mouth faces +Y (connector end):
# push it on towards +Y, pull it off towards the pads.
CLIP_T = .8
CLIP_HALF_X = 1.8
CLIP_BACK, CLIP_TIP = 1.8, 2.2   # closed end / mouth, from the neck centre along Y
CLIP_BORE_R = .9
CLIP_SLOT = 1.5                  # 0.1 mm snap per jaw over the 1.7 mm neck

# Seats and frame (cap frame).
RAIL_X = (8.6, 10.6)
RAIL_Z = (18.5, SEAT_TOP)
PAD_X = (6.4, 10.6)
ROOT = (ARM_ROOT_Y - .6, ARM_ROOT_Y, h29.ARM_Z[0], h29.ARM_Z[1])
FIRST_FRONT = -12.3


def _point(y):
    return mf.CrossSection.square((.06, .06)).translate((-.03, y - .06))


def _section(w, l):
    """Plan section centred on the origin: round end at +Y, point at -Y."""
    return mf.CrossSection.batch_hull([mf.CrossSection.circle(w / 2, 48).translate((0., -l / 2 + w / 2)), _point(l / 2)]).mirror((0., 1.))


def _prism(section, z0, z1):
    return mf.Manifold.extrude(section, z1 - z0).translate((0., 0., z0))


def post():
    """One post at the origin in plan: shaft, neck and head."""
    shaft = _prism(_section(POST_W, POST_L), SEAT_TOP - .05, NECK[0])
    neck = _prism(mf.CrossSection.batch_hull([mf.CrossSection.circle(NECK_R, 48), _point(POST_L / 2)]),
                  NECK[0] - .01, NECK[1] + .01)
    head = _prism(_section(POST_W, POST_L), NECK[1], HEAD_TOP - .3)
    crown = _prism(_section(POST_W - .6, POST_L - .6), HEAD_TOP - .01, HEAD_TOP)
    solid = union((shaft, neck, mf.Manifold.batch_hull([head, crown])))
    # Front-down printing grows this head from the circular neck. Remove the
    # leading underside overhang with a 45-degree ramp, keeping its side lips.
    leading_undercut = d.wedge(-2., 2., [
        (-3., NECK[1]), (-NECK_R, NECK[1]),
        (-NECK_R + 1.8, NECK[1] + 1.8), (-3., NECK[1] + 1.8),
    ])
    return solid - leading_undercut


def bracket(front):
    """Hinged bracket in the cap frame, for a board whose pad end is at `front`."""
    hy = front + HOLE_FROM_PAD
    rails = mirrored(box(*RAIL_X, front + .5, ROOT[1], *RAIL_Z))
    pads = mirrored(box(*PAD_X, hy - 2.0, hy + 2.0, *RAIL_Z))
    roots = mirrored(box(h29.ARM_X[0], RAIL_X[1], *ROOT))
    floor = box(-RAIL_X[0] - .1, RAIL_X[0] + .1, -4.1, 4.72, 18.5, 19.2)
    # Grow the crossbars from the two seat rails in the front-down print.
    # The narrow diagonal ribs back the inner ends before the crossbars begin.
    floor_ribs = mirrored(mf.Manifold.batch_hull([
        box(*RAIL_X, front + .5, front + 1.9, 18.5, 19.2),
        box(-.1, 1.1, -2.1, -.7, 18.5, 19.2),
    ]))
    root_ribs = mirrored(mf.Manifold.batch_hull([
        box(*RAIL_X, ARM_ROOT_Y - 9., ARM_ROOT_Y - 7.6, *h29.ARM_Z),
        box(*h29.ARM_X, ARM_ROOT_Y - .6, ARM_ROOT_Y, *h29.ARM_Z),
    ]))
    shape = union((rails, pads, roots, floor, floor_ribs, root_ribs))
    s0, s1 = (y + HINGE_SHIFT for y in h29.tray_frame_support_y())
    z0, z1 = 17.0, 21.0
    shape -= union((box(-3.35, 3.35, ARM_ROOT_Y, AXIS_Y + .85, z0, z1),       # free space round both arms
                    box(-5.85, 5.85, s0 - .45, s1 + .45, z0, z1)))      # the fixed supports
    # R26 pusher and stop feet, cut round the supports exactly as on R29.
    old = d.paddle() ^ box(-7.95, 7.95, -4.1, 4.72, 12.95, 19.20)
    old -= mirrored(box(1.6, 6.0, 3.9, 9.0, 12., 21.))
    posts = union(post().translate((s * POST_X, hy, 0.)) for s in (-1, 1))
    return H.base.clean(union((shape, old, arms(), posts)), "DFRobot_Hole_Bracket")


def _plate(f, pitch=HOLE_PITCH, hole_d=HOLE_D, holes=True):
    plate = box(-BOARD_HALF, BOARD_HALF, f, f + BOARD_LENGTH, *BOARD_Z)
    if not holes:
        return plate
    return plate - union(mf.Manifold.cylinder(4., hole_d / 2, hole_d / 2, 64)
                         .translate((s * pitch / 2, f + HOLE_FROM_PAD, BOARD_Z[0] - 1.)) for s in (-1, 1))


@lru_cache(maxsize=1)
def board_front_y():
    """Put the released board's pad edge on the Choc cap fronts."""
    f = FIRST_FRONT
    for _ in range(4):
        f += (h28.OUTER_CAP_BOTTOM - world(_plate(f, holes=False)).bounding_box()[1]) / placement()[1, 1]
    return round(f, 5)


def hole_y():
    return board_front_y() + HOLE_FROM_PAD


def sensor(pitch=HOLE_PITCH, hole_d=HOLE_D):
    return _plate(board_front_y(), pitch, hole_d)


@lru_cache(maxsize=1)
def cap():
    return bracket(board_front_y())


def electrode():
    f = board_front_y()
    return box(-9.75, 9.75, f + .58, f + 13.70, BOARD_Z[1] - .01, BOARD_Z[1] + .07)


def connector():
    """R26 Gravity envelope, 1 mm from the connector end."""
    rear = board_front_y() + BOARD_LENGTH
    x0, x1, _, _, _, z1 = d.CONNECTOR
    return box(x0, x1, rear - 8.65, rear - 1.0, BOARD_Z[1], z1 - d.BOARD_BOTTOM + BOARD_Z[0])


def gravity_lead():
    """R28's slack lead path, moved 5 mm with the longer board."""
    f = board_front_y() + BOARD_LENGTH - 30.
    points = [(0., f + 26., 24.3), (0., f + 33.5, 24.3), (2.5, f + 36.5, 23.),
              (6.5, f + 38.5, 19.5), (9., f + 40., 16.)]
    balls = [mf.Manifold.sphere(1.25, 20).translate(p) for p in points]
    return union(mf.Manifold.batch_hull([a, b]) for a, b in zip(balls, balls[1:]))


def clip_local():
    """One clip round a neck at the origin, resting on the board's top face."""
    body = mf.CrossSection.square((2 * CLIP_HALF_X, CLIP_BACK + CLIP_TIP)).translate((-CLIP_HALF_X, -CLIP_BACK))
    body = body.offset(-.5, mf.JoinType.Round, 2., 32).offset(.5, mf.JoinType.Round, 2., 32)
    bore = mf.CrossSection.circle(CLIP_BORE_R, 48)
    slot = mf.CrossSection.square((CLIP_SLOT, CLIP_TIP + 1.)).translate((-CLIP_SLOT / 2, 0.))
    mouth = mf.CrossSection([[(-CLIP_SLOT / 2, CLIP_TIP - .6), (CLIP_SLOT / 2, CLIP_TIP - .6),
                              (CLIP_SLOT / 2 + .4, CLIP_TIP + .01), (-CLIP_SLOT / 2 - .4, CLIP_TIP + .01)]])
    return _prism(body - bore - slot - mouth, NECK[0], NECK[0] + CLIP_T)


def clip(side):
    return clip_local().translate((side * POST_X, hole_y(), 0.))


def clips():
    return clip(-1) + clip(1)


def snap_per_jaw_mm():
    return round((2 * NECK_R - CLIP_SLOT) / 2, 4)


def clip_estimate():
    jaw = CLIP_HALF_X - CLIP_SLOT / 2
    length = CLIP_TIP + CLIP_BORE_R
    delta = snap_per_jaw_mm()
    return {"jaw_width_mm": round(jaw, 3), "jaw_length_mm": round(length, 3), "snap_per_jaw_mm": delta,
            "jaw_strain_percent_estimate": round(100 * 3 * jaw * delta / (2 * length ** 2), 2),
            "assumed_PETG_yield_strain_percent": 100 * h29.YIELD_STRAIN}


def _vol(shape):
    return round(float(shape.volume()), 6)


def _max(pairs):
    return round(max(float((a ^ b).volume()) for a, b in pairs), 6)


def checks(carrier, working):
    op1_board, sockets, plug = (k27.op1(part) for part in (H.board(), H.barrels(), H.plug()))
    switch, _ = (k27.op1(part) for part in H.switch())
    installed = union(working[f"key_{i}_{part}"] for i in (0, 2, 3, 4) for part in ("switch", "maximum_socket"))
    travel = union(working[f"key_{i}_cap_travel"] for i in (0, 2, 3, 4))
    fixed = union((carrier, installed, travel, op1_board, sockets, plug, switch, k27.lead()))
    lifted = union((carrier, installed, travel, op1_board, switch))
    part = cap()
    board, plug_box, lead, keepers = sensor(), connector(), gravity_lead(), clips()
    group = union((part, board, plug_box, keepers))
    angles = np.linspace(-REST, 0., 25)
    hy = hole_y()
    necks = union(mf.Manifold.cylinder(NECK[1] - NECK[0] + .2, NECK_R + .02, NECK_R + .02, 48)
                  .translate((s * POST_X, hy, NECK[0] - .1)) for s in (-1, 1))
    squeezed = bent(part)
    tab_box = box(2.4, h29.TAB_TIP + .5, AXIS_Y - .8, AXIS_Y + .8, h29.AXIS_Z - .8, h29.AXIS_Z + .8)
    released_tip = (part ^ tab_box).bounding_box()[3]
    squeezed_tip = (squeezed ^ tab_box).bounding_box()[3]
    lift = {f"{z:.2f}": _vol(world(part).translate((0., 0., z)) ^ lifted) for z in (.1, .3, .5)}
    stop_posts = k27.towards_top(d.stop_posts()).decompose()
    front = board_front_y()
    op1_feed = union((op1_board, sockets, plug, k27.lead()))
    result = {
        "hinge_axis_world_y_mm": AXIS_Y + CLICK_SHIFT,
        "hinge_moved_towards_two_key_end_mm": HINGE_SHIFT,
        "op1_board_insertion_overlap_mm3": _max((carrier, op1_feed.translate((0., y, 0.))) for y in np.linspace(42., 0., 57)),
        "board_outline_mm": [2 * BOARD_HALF, BOARD_LENGTH], "board_thickness_assumed_mm": round(BOARD_Z[1] - BOARD_Z[0], 3),
        "hole_nominal_diameter_mm": HOLE_D, "hole_pitch_nominal_mm": HOLE_PITCH, "pitch_range_checked_mm": list(PITCH_RANGE),
        "hole_centre_from_pad_end_mm": HOLE_FROM_PAD, "post_section_mm": [POST_W, POST_L],
        "board_float_across_pitch_each_way_at_nominal_mm": round((HOLE_D - POST_W) / 2, 3),
        "board_float_along_board_each_way_mm": round((HOLE_D - POST_L) / 2, 3),
        "board_axial_float_under_clip_mm": round(NECK[1] - NECK[0] - CLIP_T, 3),
        "post_top_above_touch_face_mm": round(HEAD_TOP - BOARD_Z[1], 3),
        "board_y_cap_frame_mm": [front, round(front + BOARD_LENGTH, 5)],
        "hole_centres_world_at_hard_stop_mm": [[-POST_X, round(hy + CLICK_SHIFT, 4)], [POST_X, round(hy + CLICK_SHIFT, 4)]],
        "released_front_mm": round(world(board).bounding_box()[1], 6),
        "released_front_alignment_error_mm": round(abs(world(board).bounding_box()[1] - h28.OUTER_CAP_BOTTOM), 6),
        "bracket_behind_board_front_mm": round(min(world(part, a).bounding_box()[1] - world(board, a).bounding_box()[1] for a in angles), 4),
        "min_front_clear_of_bottom_over_stroke_mm": round(min(world(group, a).bounding_box()[1] for a in angles) - h28.BOTTOM_EDGE, 6),
        "top_released_max_mm": round(world(part + board + keepers).bounding_box()[5], 4),
        "released_tab_axial_engagement_mm": round(released_tip - h29.SUPPORT_X[0], 4),
        "squeezed_tab_clear_of_support_mm": round(h29.SUPPORT_X[0] - squeezed_tip, 4),
        "arm": h29.arm_estimate(),
        "pivot_distance_from_board_connector_end_mm": round(board_front_y() + BOARD_LENGTH - AXIS_Y, 4),
        "switch_lever_arm_mm": round(AXIS_Y - d.PUSH_Y, 4),
        "touch_centre_lever_arm_mm": round(AXIS_Y - (board_front_y() + (.58 + 13.70) / 2), 4),
        "clip": clip_estimate(),
        "click_stroke_overlap_mm3": _max((world(group, a), fixed) for a in angles),
        "lead_stroke_overlap_mm3": _max((world(lead, a), fixed + world(part, a)) for a in angles),
        "squeezed_lowering_overlap_mm3": _max((world(squeezed).translate((0., 0., z)), lifted) for z in np.linspace(8., 0., 33)),
        "arm_release_overlap_mm3": _max((world(bent(part, t)), lifted) for t in np.linspace(1., 0., 11)),
        "board_lift_off_overlap_mm3": _max((sensor().translate((0., 0., z)), part) for z in np.linspace(0., 6., 25)),
        "clip_seated_overlap_mm3": _vol(keepers ^ (part + board + plug_box)),
        # Removal pulls each clip towards the pads; the neck leaves through the jaws.
        "clip_slide_overlap_excluding_snap_mm3": _max((keepers.translate((0., -y, 0.)), (part - necks) + board + plug_box)
                                                     for y in np.linspace(0., 5., 21)),
        "board_on_posts_overlap_by_pitch_mm3": {f"{p:.2f}": _vol(sensor(pitch=p) ^ part) for p in np.linspace(*PITCH_RANGE, 5)},
        "straight_lift_contact_by_height_mm3": lift,
        "straight_lift_retention_contact_mm3": lift["0.30"],
        "board_seat_contact_mm3": _vol(part ^ board.translate((0., 0., -.1))),
        "board_lateral_capture_contact_mm3": _vol(part ^ board.translate((.55, 0., 0.))),
        "board_along_capture_contact_mm3": _vol(part ^ board.translate((0., .4, 0.))),
        "clip_head_capture_contact_mm3": _vol(keepers.translate((0., 0., NECK[1] - NECK[0] - CLIP_T + .1)) ^ part),
        "board_to_clip_lift_contact_mm3": _vol(board.translate((0., 0., .1)) ^ keepers),
        "overpress_stop_contacts_mm3": [_vol(world(part, .25) ^ p) for p in stop_posts],
        "guard_runners": dict(h28.RUNNERS),
        "nominal_click_stop_depression_mm": d.DEPRESSION,
    }
    overlaps = [v for k, v in result.items() if k.endswith("overlap_mm3")]
    overlaps += list(result["board_on_posts_overlap_by_pitch_mm3"].values())
    contacts = [v for k, v in result.items() if k.endswith("contact_mm3")]
    result["passed"] = bool(
        max(overlaps) < .035 and min(contacts) > .04
        and len(result["overpress_stop_contacts_mm3"]) == 2 and min(result["overpress_stop_contacts_mm3"]) > .01
        and result["released_front_alignment_error_mm"] < .001
        and result["bracket_behind_board_front_mm"] > .2
        and result["min_front_clear_of_bottom_over_stroke_mm"] > .15
        and result["released_tab_axial_engagement_mm"] >= .6
        and result["squeezed_tab_clear_of_support_mm"] > .2
        and lift["0.10"] < .035
        and result["arm"]["root_strain_percent_estimate"] < 2.
        and result["clip"]["jaw_strain_percent_estimate"] < 2.
        and len(result["guard_runners"]) == 6)
    return result


def geometry():
    """Preserve the R29 carrier interfaces and trim the isolated guard start."""
    carrier, working = h29.geometry()
    old_y0, old_y1 = (y + CLICK_SHIFT for y in h29.tray_frame_support_y())
    old_supports = mirrored(box(3.39, 5.51, old_y0 - .01, old_y1 + .01, 11.35, 20.01))
    keeper_ears = box(-6.72, 6.72, 29.95, 32.59, 11.35, 14.52)
    carrier = (carrier - old_supports - keeper_ears) + supports()
    # The socket tape clearance separates this tiny tip for its first two
    # layers. Trim the tip instead of adding plastic to the tape clearance.
    tip = box(-29.62, -26.96, 12.58, 13.10, 4.60, 5.47)
    assert .1 < (carrier ^ tip).volume() < 1.
    # Grow the tall hinge posts from the deck on the rear-down orientation.
    # The ramp lies outside the two flex arms, the switch and the hinge bores.
    # The support rear face is on the bed with the carrier rear face.
    # Its full height therefore starts directly on the build plate.
    hinge_ramps = mf.Manifold()
    # The slicer's wide inner wall overshot this corner of the upper-left
    # socket loading path. Leave local relief below its seating surface.
    socket_relief = box(-17.15, -16.05, 14.50, 16.35, 6.85, 7.82)
    # Continue the rear OP1 lead opening into a tapered roof. The former
    # square end placed a curling outline over the whole opening in one layer.
    cable_roof = mf.Manifold.batch_hull([
        box(-.05, .05, 13.40, 13.50, 6.76, 6.86),
        box(-4.76, 4.76, 18.29, 18.43, 4.38, 9.24),
    ])
    solid = h29.r.spaces16.carve(carrier + hinge_ramps - tip - socket_relief - cable_roof,
                               working, "r30-prepared-carrier")
    return H.base.clean(solid, "Key_Carrier"), working
