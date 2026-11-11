"""R32 keeps R31's rear hinge and seats the stock OP1 PCB on its eyelets.

The OP1 board yaw leaves the switch actuator in the middle of the paddle
and moves the underside plug outside the carbon rod. No lift of the PCB
or switch is required. Vendor renders give the PCB envelope and eyelet
locations. The Omron 60M is the dimensioned reference from the bought kit.
"""
from functools import lru_cache
import json
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "exports"
R31 = HERE.parent / "carbon-rod-holders-r31-rear-hinge"
sys.dont_write_bytecode = True
sys.path.insert(0, str(R31))
import holder31 as r31

d, H, k27, h29 = r31.d, r31.H, r31.k27, r31.h29
box, union = r31.box, r31.union
CLICK_SHIFT = r31.CLICK_SHIFT
REVISION = HERE.name

# Ethan's "white bits" are the plug/housing under the PCB. The three
# contacts and their socket barrels need separate, shallower clearance.
PCB_Z = H.ZB
PCB_TOP = H.ZT
ACTUATOR_Y = d.PUSH_Y + CLICK_SHIFT
PCB_YAW = -25.
PIN_PITCH = 5.08
ACTUATOR_TO_MIDDLE = 1.95
EYELETS = (-8.2 + ACTUATOR_TO_MIDDLE, 9.7 + ACTUATOR_TO_MIDDLE)
# Offset the first screw towards the end of its eyelet so its stock head
# clears the mouse switch body. The locating shoulder stays centred.
SCREW_CENTRES = (EYELETS[0] - .85, EYELETS[1])
PCB_Y = (-11. + ACTUATOR_TO_MIDDLE, 19. + ACTUATOR_TO_MIDDLE)
PCB_HALF_X = 5.0
PLUG_Y = (13. + ACTUATOR_TO_MIDDLE, 19.2 + ACTUATOR_TO_MIDDLE)
PLUG_HALF_X, PLUG_DEPTH = 3.6, 5.9
MATE_Y = (17.0, 20.65)
MATE_HALF_X = 3.10
MATE_TOP = PCB_Z - 2.80
PLUNGER_H = 7.35
TERMINAL_DEPTH = 3.5
SOCKET_DEPTH = 4.3
MOUNT_PILOT_R = .68
BOARD_RISE = 16.


def board_frame(shape):
    """Transform from PCB coordinates, with the actuator at the origin."""
    return shape.rotate((0., 0., PCB_YAW)).translate((0., ACTUATOR_Y, 0.))


def cylinder_at(x, y, low, high, radius, top_radius=None):
    return mf.Manifold.cylinder(high - low, radius, radius if top_radius is None else top_radius, 48).translate((x, y, low))


def terminals():
    return board_frame(union(
        box(-.22, .22, y - .45, y + .45, PCB_TOP - TERMINAL_DEPTH, PCB_TOP + .01)
        for y in (ACTUATOR_TO_MIDDLE - PIN_PITCH, ACTUATOR_TO_MIDDLE, ACTUATOR_TO_MIDDLE + PIN_PITCH)
    ))


def socket_local(clearance=0., sweep=False):
    top = 17. if sweep else PCB_Z + .01
    return union(cylinder_at(0., y, PCB_Z - SOCKET_DEPTH - clearance, top, 1.30 + clearance)
                 for y in (ACTUATOR_TO_MIDDLE - PIN_PITCH, ACTUATOR_TO_MIDDLE, ACTUATOR_TO_MIDDLE + PIN_PITCH))


def sockets():
    outer = socket_local()
    bores = union(cylinder_at(0., y, PCB_Z - SOCKET_DEPTH - .1, PCB_Z + .1, .62)
                  for y in (ACTUATOR_TO_MIDDLE - PIN_PITCH, ACTUATOR_TO_MIDDLE, ACTUATOR_TO_MIDDLE + PIN_PITCH))
    return board_frame(outer - bores)


def board(pitch=17.9, hole_d=4.05):
    y0, y1 = PCB_Y
    eyes = (EYELETS[0], EYELETS[0] + pitch)
    blank = box(-PCB_HALF_X, PCB_HALF_X, y0, y1, PCB_Z, PCB_TOP)
    holes = union(cylinder_at(0., y, PCB_Z - .1, PCB_TOP + .1, hole_d / 2) for y in eyes)
    contacts = union(cylinder_at(0., y, PCB_Z - .1, PCB_TOP + .1, .67)
                     for y in (ACTUATOR_TO_MIDDLE - PIN_PITCH, ACTUATOR_TO_MIDDLE, ACTUATOR_TO_MIDDLE + PIN_PITCH))
    return board_frame(blank - holes - contacts)


def white_housing():
    return board_frame(box(-PLUG_HALF_X, PLUG_HALF_X, *PLUG_Y, MATE_TOP, PCB_Z))


def plug():
    return board_frame(box(-MATE_HALF_X, MATE_HALF_X, *MATE_Y, PCB_Z - PLUG_DEPTH, MATE_TOP))


def cable(radius=1.3):
    centre = sum(PLUG_Y) / 2
    points = [(0., centre, 4.25), (0., centre, 2.65), (1.9, centre + .4, 2.1),
              (4.5, centre + 1.35, 2.15), (7.3, centre + 2.7, 3.25)]
    balls = [mf.Manifold.sphere(radius, 24).translate(p) for p in points]
    return board_frame(union(mf.Manifold.batch_hull([a, b]) for a, b in zip(balls, balls[1:])))


def switch():
    y = ACTUATOR_TO_MIDDLE
    body = box(-2.90, 2.90, y - 6.4, y + 6.4, PCB_TOP, PCB_TOP + 6.5)
    stalk = box(-1.45, 1.45, -.60, .60, PCB_TOP + 6.49, PCB_TOP + PLUNGER_H)
    return board_frame(body), board_frame(stalk)


def screw_pilots(bottom):
    return board_frame(union(cylinder_at(0., y, bottom, PCB_TOP + .2, MOUNT_PILOT_R)
                             for y in SCREW_CENTRES))


def mount_saddles():
    """Low locating shoulders allow the two eyelets to drop on from above."""
    a, b = EYELETS
    # The rear locator is shorter along the board to accommodate photo-scale
    # uncertainty in the pitch. The screw head spans the eyelet on either.
    seats = union(cylinder_at(0., y, PCB_Z - 3.4, PCB_Z, 2.80) for y in EYELETS)
    front = cylinder_at(0., a, PCB_Z - .03, PCB_Z + .54, 1.42, 1.15)
    rear = cylinder_at(0., b, PCB_Z - .03, PCB_Z + .54, 1.28, 1.08)
    rear = rear ^ box(-2., 2., b - .85, b + .85, PCB_Z - .05, PCB_Z + .6)
    return board_frame(seats + front + rear)


def screws():
    """Kit M1.6×4 fasteners, modeled with the specified 5 mm head."""
    return board_frame(union(
        cylinder_at(0., y, PCB_TOP - 4., PCB_TOP + .02, .80)
        + cylinder_at(0., y, PCB_TOP, PCB_TOP + .85, 2.50, 2.05)
        for y in SCREW_CENTRES
    ))


def reliefs():
    """Open the path from the deck down to the outboard wire exit."""
    board_slot = box(-5.65, 5.65, PCB_Y[0] - .65, PCB_Y[1] + .65, PCB_Z - .02, 16.5)
    housing = box(-PLUG_HALF_X - .52, PLUG_HALF_X + .52, PLUG_Y[0] - .5, PLUG_Y[1] + .55,
                  MATE_TOP - .35, 16.5)
    plug_entry = box(-MATE_HALF_X - .45, MATE_HALF_X + .45, MATE_Y[0] - .4, MATE_Y[1] + .4,
                     -12., MATE_TOP + .15)
    # Leave the cable open on the outer side and underneath. The top
    # stays closed beside the PCB mount and the neighbouring key.
    wire_entry = box(-1.85, 8.8, MATE_Y[0] - .3, PLUG_Y[1] + 2.4, -12., 5.9)
    return board_frame(board_slot), board_frame(socket_local(.35, sweep=True)), board_frame(housing + plug_entry + wire_entry)


@lru_cache(maxsize=1)
def geometry():
    original, working = r31.geometry()
    restored_deck = box(-7.1, 7.1, r31.h28.BOTTOM_EDGE, k27.REAR, 7.24, 11.35)
    slot, socket_cut, underside = reliefs()
    saddles = mount_saddles()
    # Extend the printed bore past the working depth so an end bead cannot
    # block the screw pilot where the head seats and the threads engage.
    pilots = screw_pilots(PCB_Z - 3.75)
    # A narrow outer land carries the second saddle where the yawed board
    # reaches the old connector opening. Preserve the R31 rod and Choc spaces.
    support = board_frame(d.wedge(-3.1, 3.1, [
        (EYELETS[1] - 3.35, 6.05), (EYELETS[1] + 4.2, 6.05),
        (EYELETS[1] + 3.05, PCB_Z), (EYELETS[1] - 3.35, PCB_Z),
    ]))
    # The outboard corner of the connector opening has a thin strip at
    # the Choc socket's inner edge. Remove it through its first connection
    # to the deck so each remaining perimeter grows from the previous layer.
    # Leave an extra bead-width of room below the clip relief at the corner.
    detached_lip = box(12.83, 14.42, 16.64, 20.40, 8.85, 11.35)
    carrier = (original + restored_deck + support - slot + saddles) - socket_cut - underside - pilots - detached_lip
    carrier = h29.r.spaces16.carve(carrier, working, "r32 two-eyelet OP1 mount")
    carrier = H.base.clean(carrier, "Key_Carrier")
    return carrier, working


def checks(carrier, working):
    metrics = {}
    max_overlap = r31._max
    installed = union(working[f"key_{i}_{part}"] for i in (0, 2, 3, 4)
                      for part in ("switch", "maximum_socket", "cap_travel"))
    installed_without_caps = union(working[f"key_{i}_{part}"] for i in (0, 2, 3, 4)
                                   for part in ("switch", "maximum_socket"))
    rod = working["unloaded_clip_bore"]
    body, plunger = switch()
    pcb_group = union((board(), sockets(), white_housing()))
    plug_group = plug() + cable()
    switch_group = union((body, terminals(), plunger))
    group = union((r31.cap(), r31.sensor(), r31.connector(), r31.clips()))
    open_top = union((carrier, installed_without_caps, rod))
    occupied = union((carrier, installed, rod))
    seated_pcb = open_top + pcb_group
    switch_seat = union((occupied, board(), sockets(), screws()))
    fixed = union((occupied, pcb_group, plug_group, body, terminals(), screws()))
    metrics["pcb_drop_overlap_mm3"] = max_overlap(
        (pcb_group.translate((0., 0., z)), open_top) for z in np.linspace(BOARD_RISE, 0., 57))
    metrics["underside_plug_insertion_overlap_mm3"] = max_overlap(
        (plug_group.translate((0., 0., z)), seated_pcb) for z in np.linspace(-9., 0., 25))
    metrics["switch_seat_overlap_mm3"] = max_overlap(
        (switch_group.translate((0., 0., z)), switch_seat) for z in np.linspace(8., 0., 33))
    metrics["board_eyelet_pitch_overlap_mm3"] = {
        f"{pitch:.2f}": max_overlap([(board(pitch, 3.6), carrier)]) for pitch in np.linspace(17.3, 18.5, 7)
    }
    metrics["screw_shank_and_board_overlap_mm3"] = max_overlap(
        (board(pitch, 3.6), screws()) for pitch in np.linspace(17.3, 18.5, 7))
    metrics["screw_heads_and_switch_overlap_mm3"] = max_overlap([(screws(), body)])
    metrics["pin_socket_fit_overlap_mm3"] = max_overlap([(terminals(), sockets())])
    metrics["white_housing_and_wire_to_rod_overlap_mm3"] = max_overlap([(white_housing() + plug_group, rod)])
    metrics["click_stroke_overlap_mm3"] = max_overlap(
        (r31.world(group, angle), fixed) for angle in np.linspace(-r31.REST, 0., 33))
    # The lead and bracket rotate together. Their mutual clearance is
    # invariant, so only the lead's relation to fixed parts varies.
    metrics["lead_stroke_overlap_mm3"] = max(
        max_overlap((r31.world(r31.gravity_lead(), angle), fixed)
                    for angle in np.linspace(-r31.REST, 0., 25)),
        max_overlap([(r31.gravity_lead(), r31.cap())]))
    metrics["bracket_drop_overlap_mm3"] = max_overlap(
        (r31.world(r31.bent(r31.cap())).translate((0., 0., z)), fixed)
        for z in np.linspace(8., 0., 33))
    metrics["bracket_unpinch_overlap_mm3"] = max_overlap(
        (r31.world(r31.bent(r31.cap(), bend)), fixed) for bend in np.linspace(1., 0., 15))
    metrics["switch_contact_under_overpress_mm3"] = r31._vol(
        r31.world(r31.cap(), .20) ^ plunger.translate((0., 0., -d.DEPRESSION)))
    metrics["seating_contact_under_board_mm3"] = r31._vol(board().translate((0., 0., -.2)) ^ carrier)
    metrics["seat_and_stock_profile_mm"] = {
        "board_bottom_z": PCB_Z, "board_top_z": PCB_TOP, "yaw_degrees": PCB_YAW,
        "socket_depth": SOCKET_DEPTH, "white_plug_depth": PLUG_DEPTH,
        "actuator_offset_from_middle_pin": ACTUATOR_TO_MIDDLE, "stop_travel": d.DEPRESSION,
    }
    metrics["passed"] = bool(max(metrics[key] for key in metrics if key.endswith("overlap_mm3") and isinstance(metrics[key], float)) < .035
        and max(metrics["board_eyelet_pitch_overlap_mm3"].values()) < .035
        and metrics["seating_contact_under_board_mm3"] > .1
        and metrics["switch_contact_under_overpress_mm3"] > .005)
    return metrics


def print_routes():
    carrier, working = geometry()
    pilots = screw_pilots(PCB_Z - 3.2)
    hinge = h29.mirrored(d.axis_oval(
        r31.AXIS_Y + CLICK_SHIFT, r31.AXIS_Z, h29.TAB_R + .03, *h29.SUPPORT_X))
    routes = {
        "Key_Carrier": {**working, "Snap hinge holes": hinge, "OP1 PCB": board(),
                        "OP1 three socket barrels": sockets() + terminals(), "OP1 white connector": white_housing() + plug(),
                        "OP1 underside cable": cable(1.55), "OP1 screw pilot holes": pilots},
        "DFRobot_Hole_Bracket": {"PCB underside and both mounting holes": r31.sensor(),
            "DFRobot connector": r31.connector(), "Both clip insertion paths": union(
                mf.Manifold.batch_hull([r31.clip(side), r31.clip(side).translate((0., -5., 0.))])
                - r31.post().translate((side * r31.POST_X, r31.hole_y(), 0.)) for side in (-1, 1))},
    }
    material = {"Key_Carrier": {"Fixed hinge support walls": r31.supports(),
                               "OP1 mounting shoulders": mount_saddles() ^ carrier},
                "DFRobot_Hole_Bracket": {
                    "Both flex arms and root contact": r31.arms(),
                    "Left post and neck": r31.post().translate((-r31.POST_X, r31.hole_y(), 0.)),
                    "Right post and neck": r31.post().translate((r31.POST_X, r31.hole_y(), 0.))}}
    for name in ("DFR0030_Post_Clip", "DFR0030_Post_Clip_2"):
        routes[name] = {"Clip opening": cylinder_at(0., 0., r31.NECK[0] - .05, r31.NECK[0] + r31.CLIP_T + .05, r31.NECK_R)}
        material[name] = {"Both jaws": r31.clip_local()}
    return routes, material


if __name__ == "__main__":
    print(json.dumps(checks(*geometry()), indent=2))
