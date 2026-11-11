#!/usr/bin/env python3
"""Printable DFR0030 V2 cradle on the stock OP1 switch board.

X is across the keys, +Y points towards the upper row, and +Z is up.
The paddle and sensor are modelled at the click stop. The bought electronics
are fit envelopes. The carrier reuses the R22 switch seats and R23 guard paths.
"""

from functools import lru_cache
import json
import math
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
OUT = HERE / "exports"
R23 = HERE.parent / "carbon-rod-holders-r23-hybrid-centre"
R25 = HERE.parent / "carbon-rod-holders-r25-keeper-release"
sys.dont_write_bytecode = True
sys.path.insert(0, str(R23))
import holder23 as h
import guard23

REVISION = HERE.name
CARRIER = "Key_Carrier"
PADDLE = "DFRobot_Paddle"
KEEPER = "DFRobot_Front_Keeper"
OP1_LATCH = "OP1_Board_Latch"
PARTS = (CARRIER, PADDLE, KEEPER, OP1_LATCH)
box, union, mesh = h.box, h.union, h.mesh
LEFT_RIGHT = (-1, 1)
LOWER_SHIFT = 2.8
LOWER_INDICES = (0, 2)
BOARD_X = 11.
BOARD_FRONT, BOARD_REAR = -24.65, 5.35
BOARD_BOTTOM, BOARD_THICKNESS = 20.25, 1.6
EDGE_X = BOARD_X + .24
PADDLE_X = EDGE_X + 1.25
HINGE_Y, HINGE_Z = 6.55, 18.5
PIN_ROOT, PIN_TIP, PIN_R = 1.75, 2.52, .79
ARM_INNER, ARM_OUTER, BORE_R = 2.04, 3.80, .99
SQUEEZE = .65
STOP_X = 6.55
STOP_Y0, STOP_Y1 = -2.75, -.9
STOP_Z = 13.05
DEPRESSION = .48
PUSH_Y = h.YC
PUSH_Z = h.PLUNGER_FREE - DEPRESSION
# The switch's spring sets the released height when the nominal OP1 is fitted.
REST = math.degrees(math.asin(DEPRESSION / (HINGE_Y - PUSH_Y)))
KEEPER_PIN = (-26.67, 18.6)
LATCH_Y = (-21.73, -20.19)
LATCH_SPREAD = .56
LATCH_FLEX_ROOT = 13.76
LATCH_ROOT_ROUND = .6
LATCH_BLADE_BOTTOM = 9.58
# There is room for the estimated Gravity housing and a lead directed forward.
CONNECTOR = (-4.6, 4.6, -23.65, -16., BOARD_BOTTOM + BOARD_THICKNESS, 28.0)


def mirrored(shape):
    return shape + shape.mirror((1., 0., 0.))


def axis_oval(y, z, r, x0, x1):
    return h.bar_x(r, x0, x1, y, z, 48)


def wedge(x0, x1, points):
    return h.prism_yz(points, x0, x1)


def pose(angle):
    """Rigid transform about the snap pins, positive angle is a press."""
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)
    basis = np.array([[1., 0., 0.], [0., c, -s], [0., s, c]])
    pivot = np.array([0., HINGE_Y, HINGE_Z])
    return np.column_stack((basis, pivot - basis @ pivot))


@lru_cache(maxsize=1)
def spring_tongues():
    # Sloped rear edge grows from the unchanged saddle when printing rear-down.
    # The split runs all the way below the live flex length.
    tongue = wedge(.75, PIN_ROOT, [
        (5.73, 11.0), (14.72, 11.0), (8.93, 16.79),
        (8.0, 18.0), (6.22, 19.78), (5.58, 19.78),
    ])
    # Blend the pin into the arm. Chamfered outer end leads into the bore.
    pin = axis_oval(HINGE_Y, HINGE_Z, PIN_R, 1.60, PIN_TIP - .23)
    tip = mf.Manifold.cylinder(.23, PIN_R, .58, 48).rotate((0, 90, 0))
    tip = tip.translate((PIN_TIP - .23, HINGE_Y, HINGE_Z))
    # Start each pin next to its tongue and grow outwards on succeeding
    # layers. The front and bottom keep the circular bearing surface.
    ramp = mf.CrossSection([[(1.58, 5.4), (2.7, 5.4), (2.7, 6.29), (1.58, 7.41)]])
    ramp = mf.Manifold.extrude(ramp, 4.).translate((0., 0., 16.5))
    return mirrored(tongue + ((pin + tip) ^ ramp))


def spring_root():
    # The board ends at Y 10.3. The tail of this root anchors behind its slot.
    return wedge(-1.5, 1.5, [(5.73, 10.96), (15., 10.96),
                            (14.35, 11.61), (5.73, 11.61)])


def stop_posts():
    # Short ramps taper to the underside of the paddle and land on the slab.
    return mirrored(wedge(STOP_X - .8, STOP_X + .8, [
        (-3.2, 10.87), (1.37, 10.87), (-.82, STOP_Z), (-3.2, STOP_Z),
    ]))


def op1_latch_seats():
    """Fork at the front of the carrier, with side-open guide and catch slots."""
    outline = h.h22.poly([(6.85, -23.04), (10.85, -23.04),
                          (10.85, -15.1), (8.68, -15.1), (6.85, -17.05)])
    ear = mf.Manifold.extrude(outline, 3.45).translate((0., 0., 7.79))
    # A flat front shoulder takes axial load without camming the clip open.
    # Its short outer edge tapers in the rear-down print direction.
    slot_outline = h.h22.poly([(10.04, -21.98), (10.62, -21.98), (11.05, -22.41),
                               (11.05, -19.95), (10.04, -19.95)])
    slot = mf.Manifold.extrude(slot_outline, 3.63).translate((0., 0., 7.7))
    return mirrored(ear - slot)


def op1_latch():
    """Vertical clip. Its stop blade clears the plug and catches the PCB edge."""
    y0, y1 = LATCH_Y
    crossbar = box(-11.53, 11.53, y0, y1, LATCH_FLEX_ROOT, 15.33)
    blade = box(-5.53, 5.53, y0, y1, LATCH_BLADE_BOTTOM, 13.94)
    seats = mirrored(box(7.12, 8.7, y0, y1, 11.38, 13.94))
    # Longer arms move the root up towards the crossbar. The feet set the
    # seated depth independently so the stop blade stays above the plug.
    arm = h.h22.xz(h.h22.poly([
        (10.32, 14.1), (10.35, 7.57), (9.60, 7.57),
        (10.36, 6.29), (11.31, 6.29), (11.41, 14.1),
    ]), y0, y1)
    # Round the inside corner where the spring meets the crossbar. The
    # radius is above the guide and does not change the release clearance.
    x, z = 10.324, LATCH_FLEX_ROOT
    r = LATCH_ROOT_ROUND
    arc = [(x - r + r * math.cos(angle), z - r + r * math.sin(angle))
           for angle in np.linspace(np.pi / 2, 0, 13)]
    root = h.h22.xz(h.h22.poly([*arc, (x + .12, z - r), (x + .12, z + .12), (x - r, z + .12)]), y0, y1)
    return h.base.clean(crossbar + blade + seats + mirrored(arm + root), OP1_LATCH)


def spread_latch(points, fraction=1.):
    """Bend the free prongs out for fitting, with the crossbar fixed."""
    points = np.asarray(points)
    x, y, z = points.T
    movement = LATCH_SPREAD * fraction * np.clip((LATCH_FLEX_ROOT - z) / (LATCH_FLEX_ROOT - 7.57), 0., 1.) ** 1.6
    return np.column_stack((np.sign(x) * movement * (abs(x) > 9.), y * 0., z * 0.))


def clear_old_hinge(shape):
    # The OP1 board pocket and its two low side rails are still used. Replace
    # only the tall front cheeks from the pin-through R23 paddle.
    high = box(-16., 16., -25., 1., h.SLAB_TOP + .01, 25.)
    return shape - ((h.cheek(-1) + h.cheek(1)) ^ high)


def set_lower_seats():
    """Keep the stock seat, switch and socket routes on the same centres."""
    r22 = h.h22
    keys, slab = r22.P["keys"], r22.P["slab"]
    keys["pitch"] += LOWER_SHIFT
    slab["lower_half_x_mm"] += LOWER_SHIFT
    # Keep the widening within the verified rear-down growth angle.
    r22.K["shoulder_curve"]["length_mm"] = 19.25
    slab["lower_rear_y_mm"] -= 3.6


@lru_cache(maxsize=1)
def carrier():
    r22 = h.h22
    assert r22.carrier_base.cache_info().currsize == 0
    set_lower_seats()
    original = r22.carrier_base() + guard23.runners()
    spaces = r22.carrier_regions()
    restored = r22.spaces16.carve(original, spaces, "carrier26:runners")
    op1_seat = clear_old_hinge(restored + h.additions()) - h.cuts()
    final = op1_seat + spring_root() + spring_tongues() + stop_posts() + op1_latch_seats()
    # The surrounding hardware stays in its own assembly space, including
    # the bent solder/socket insertion routes under all four Choc keys.
    working_spaces = {name: shape for name, shape in spaces.items()
                      if not name.startswith("key_1_")}
    return h.base.clean(r22.spaces16.carve(final, working_spaces, "carrier26:final"), CARRIER)


def sensor():
    return box(-BOARD_X, BOARD_X, BOARD_FRONT, BOARD_REAR,
               BOARD_BOTTOM, BOARD_BOTTOM + BOARD_THICKNESS)


def rear_stops():
    # The two rear feet anchor this part on the build plate. Their taper
    # grows into the floor and rail, stopping the PCB on its outside edges.
    foot = wedge(3.1, PADDLE_X, [(5.55, 18.49), (8.2, 18.49),
                                (8.2, 19.56), (6.0, 19.56)])
    stop = wedge(8.95, PADDLE_X, [(5.58, 19.35), (8.2, 19.35),
                                 (8.2, 20.17), (5.58, 22.75)])
    return mirrored(foot + stop)


@lru_cache(maxsize=1)
def paddle():
    # The thin floor is the only span across the whole tray. Low ribs stiffen
    # it around the OP1 contact. Solder joints get .85 mm nominal floor relief
    # between the narrow edge seats. The sensing face is exposed.
    floor = h.rounded_plate(PADDLE_X, -26.42, 6.13, 18.5, 19.40, r_plan=.85, r_top=.14)
    rail = box(10.26, PADDLE_X, -24.98, 5.67, 19.21, BOARD_BOTTOM)
    wall = box(EDGE_X, PADDLE_X, -24.98, 5.67, BOARD_BOTTOM - .03, 22.65)
    lip = box(10.27, PADDLE_X, -24.98, 5.67, 22.22, 22.75)
    ramp = wedge(ARM_INNER, ARM_OUTER, [
        (4.04, 18.75), (5.56, 17.33), (6.03, 17.04),
        (6.75, 17.04), (8.2, 18.49), (8.2, 19.45), (4.10, 19.45),
    ])
    bore = h.teardrop_x(BORE_R, ARM_INNER - .05, ARM_OUTER + .6, HINGE_Y, HINGE_Z, (-1., 0.))
    pusher = wedge(-1.2, 1.2, [
        (PUSH_Y - .85, 18.72), (PUSH_Y - .48, PUSH_Z), (PUSH_Y + .48, PUSH_Z),
        (PUSH_Y + 1.55, 18.81),
    ])
    stop_feet = mirrored(wedge(STOP_X - .73, STOP_X + .73, [
        (-4.0, 18.78), (STOP_Y0, STOP_Z), (STOP_Y1, STOP_Z), (4.98, 18.78),
    ]))
    # The fixed cheeks and their pin sit wholly below the PCB loading path.
    cheek = wedge(5.10, 8.12, [(-28.67, 16.97), (-25.52, 16.97),
                              (-23.22, 19.27), (-22.9, 19.27),
                              (-23.64, 20.01), (-28.67, 20.01)])
    cheeks = mirrored(cheek)
    slot = box(-5.12, 5.12, -28.73, -24.76, 16.95, 21.3)
    cross_pin = h.teardrop_x(1.04, -9., 9., *KEEPER_PIN, (-1., 0.))
    # A tapered opening closes gradually as the tray prints from the rear.
    # A square end here would make the floor bridge across the full fork.
    opening = mf.CrossSection([[(-2.88, 6.17), (-2.88, 5.17),
                                (0., 2.05), (2.88, 5.17), (2.88, 6.17)]])
    hinge_access = mf.Manifold.extrude(opening, 1.24).translate((0., 0., 18.3))
    solid = union([floor - hinge_access, mirrored(rail + wall + lip), rear_stops(),
                   mirrored(ramp), pusher, stop_feet, cheeks])
    return h.base.clean(solid - mirrored(bore) - slot - cross_pin, PADDLE)


def keeper():
    # A removable U with its low bridge below the Gravity lead. A short
    # filament offcut through both cheeks locks it in place without glue.
    bridge = box(-4.91, 4.91, -28.22, -24.86, 17.09, 21.22)
    pin = axis_oval(*KEEPER_PIN, 1.04, -5.2, 5.2)
    return h.base.clean(bridge - pin, KEEPER)


def flex(points):
    """Guide-only deformation of the split arms while squeezing the pins."""
    points = np.asarray(points)
    x, y, z = points.T
    f = np.clip((z - 11.61) / (HINGE_Z - 11.61), 0, 1) ** 1.6
    in_spring = (abs(x) <= PIN_TIP + .01) & (y >= 5.1) & (y <= 13.7)
    # The fingers can move far enough to retract the pins without the inner
    # faces crossing each other. Their tops flare apart above the pins.
    shift = np.minimum(SQUEEZE * f, np.maximum(abs(x) - .06, 0.))
    return np.column_stack((-np.sign(x) * shift * in_spring, y * 0., z * 0.))


def save_json(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2) + "\n")


def export():
    OUT.mkdir(exist_ok=True)
    h.OUT = OUT
    # Rear-down makes the long sensor rails vertical. The hinge bore's
    # 45-degree roof points up in this orientation. The keeper prints bore-up.
    h.PRINT_ROT[PADDLE] = h.PRINT_ROT[CARRIER]
    h.PRINT_ROT[KEEPER] = trimesh.transformations.rotation_matrix(-np.pi / 2, [0, 1, 0])
    h.PRINT_ROT[OP1_LATCH] = h.PRINT_ROT[CARRIER]
    parts = {name: h.export_part(name, shape, name) for name, shape in
             zip(PARTS, (carrier(), paddle(), keeper(), op1_latch()))}
    save_json("manifest.json", {
        "revision": REVISION, "physical_fit_verified": False,
        "source_sha256": {p.name: h.sha(p) for p in (Path(__file__), R23 / "parameters.json")},
        "purchased_board": "DFRobot DFR0030 Gravity Digital Capacitive Touch Sensor V2",
        "outline_mm": [22, 30], "pcb_edge_thickness_estimate_mm": BOARD_THICKNESS,
        "lower_outer_key_shift_each_mm": LOWER_SHIFT, "upper_key_shift_mm": 0.,
        "parts": parts, "plate_parts": list(PARTS),
    })
    save_json("anchors.json", {"parts": {}})
    print({name: record["print_height_mm"] for name, record in parts.items()}, flush=True)


if __name__ == "__main__":
    export()
