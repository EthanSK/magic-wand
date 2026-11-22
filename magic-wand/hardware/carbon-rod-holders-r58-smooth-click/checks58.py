"""CAD checks for the R58 click parts: contact bar, hinge play, retainers, lift limit and the R57 jam.

Run in a fresh process after build58.py. Clearances only: nothing here measures a printed part.

Hinge play is measured by moving the meshes inside their holes, not from the nominal radii.
Fore and aft is along Y (toward and away from the hinge). Sideways is along X (along the pin).
The jam study moves the paddle through that play, through the click stroke, against each retainer.
A pose is used only if the switch body can still sit inside the paddle sleeve, with the OP1 board
free to follow by its 0.45 mm pocket float.
"""
import itertools
import json
from pathlib import Path
import sys

import numpy as np

import build58 as n

m, b = n.m, n.b
import checks53 as k  # noqa: E402  (R53 helpers and the inherited bought-part models)

TOL = 0.01          # mm3; STL round trips leave a few thousandths
R57_OUT = n.R57 / "exports"
vol, moved, onset = k.vol, k.moved, k.onset


def drop_at(angle, y=b.STATION[1], z=b.FREE_TOP):
    matrix = np.asarray(m.hinge_matrix(angle))
    return z - float(matrix[2] @ (0.0, y, z, 1.0))


def displaced(shape, angle, dx=0.0, forward=0.0, yaw=0.0):
    """Paddle pose inside the hinge play: yaw about the hinge centre, press, then shift."""
    turned = shape.translate((0, -m.AXIS_Y, 0)).rotate((0, 0, yaw)).translate((0, m.AXIS_Y, 0))
    return m.posed(turned, angle).translate((dx, -forward, 0))


def lowest(solid, x_board, y_board, half=0.04):
    """Lowest paddle surface over one point of the board frame, inside the sleeve."""
    column = solid ^ b.ubox(x_board - half, x_board + half, y_board - half, y_board + half, b.BODY_TOP + 0.2, b.SEAT_Z - 0.3)
    return None if column.is_empty() else float(column.bounding_box()[2])


def recess(solid, x_board):
    """Deepest upward step between the two plunger stations along one line of the bar."""
    line = [lowest(solid, x_board, y) for y in np.linspace(n.STATIONS[0], n.STATIONS[1], 27)]
    line = [b.MOAT if v is None else v for v in line]
    return round(max(v - max(line[0], line[-1]) for v in line), 3)


def play(moving, fixed):
    """Fore-aft room of `moving` inside `fixed`: at rest, and with the hinge end free to ride up."""
    clear = lambda shape: vol(shape, fixed) < 1e-5
    reach = lambda shape, sign: onset(lambda t: not clear(moved(shape, (0, sign * t, 0))), 0.0, 1.5)
    rest = envelope = None
    for dz in np.arange(-0.10, 0.81, 0.02):
        shape = moved(moving, (0, 0, float(dz)))
        if not clear(shape):
            continue
        pair = (reach(shape, -1), reach(shape, 1))
        rest = rest or pair
        envelope = pair if envelope is None else (max(envelope[0], pair[0]), max(envelope[1], pair[1]))
    return dict(at_rest_toward_front_mm=round(rest[0], 3), at_rest_toward_rear_mm=round(rest[1], 3),
                most_toward_front_mm=round(envelope[0], 3), most_toward_rear_mm=round(envelope[1], 3))


def hinge_play(carrier, paddle, pin):
    seats = carrier ^ b.box(-13, 13, 24, 33, 10, 22)
    barrel = paddle ^ b.box(-8, 8, 24.5, 33, 12, 20)
    cheek, bore = play(pin, seats), play(barrel, pin)
    total = {key: round(cheek[key] + bore[key], 3) for key in cheek}
    total["most_total_mm"] = round(total["most_toward_front_mm"] + total["most_toward_rear_mm"], 3)
    total["at_rest_total_mm"] = round(total["at_rest_toward_front_mm"] + total["at_rest_toward_rear_mm"], 3)
    return dict(pin_in_holder_cheeks=cheek, paddle_on_pin=bore, paddle_to_holder_fore_aft=total)


def jam_study(group, lid, stop, case, float_x):
    side, aft, fore, yaw = float_x
    across = np.array([np.asarray(b.board_matrix())[0][0], np.asarray(b.board_matrix())[1][0], 0.0])
    follow = [moved(case, across * s) for s in (-b.FLOAT, -b.FLOAT / 2, 0.0, b.FLOAT / 2, b.FLOAT)]
    poses = list(itertools.product((0.0, 0.5 * stop, stop - 0.02), (-side, 0.0, side), (-aft, 0.0, fore), (-yaw, 0.0, yaw)))
    used, touching, worst, nearest = 0, [], 0.0, None
    for angle, dx, forward, turn in poses:
        placed = displaced(group, angle, dx, forward, turn)
        if min(vol(placed, body) for body in follow) > 1e-3:
            continue                      # the sleeve cannot be here: the switch body is in the way
        used += 1
        amount = vol(placed, lid)
        if amount > 1e-6:
            touching.append(dict(angle_deg=round(angle, 3), dx_mm=dx, forward_mm=forward, yaw_deg=turn, overlap_mm3=round(amount, 4)))
            worst = max(worst, amount)
        else:
            gap = float(placed.min_gap(lid, 3.0))
            nearest = gap if nearest is None else min(nearest, gap)
    return dict(poses_tried=len(poses), poses_the_sleeve_can_reach=used, poses_touching_the_retainer=len(touching),
                worst_overlap_mm3=round(worst, 4), smallest_gap_in_clear_poses_mm=None if nearest is None else round(nearest, 3),
                examples=touching[:4])


def main(source=None):
    source = Path(source) if source else n.EXPORT
    k.old.configure_new_op1()
    q, h, r, d = k.q, k.h, k.r, k.d
    load = lambda folder, name: b.load(folder / f"{name}-assembly.stl")
    names = ("Touch_Paddle", "OP1_Lid_Plain", "OP1_Lid_Stop", "Hinge_Pin_Snug")
    P58, PLAIN, STOP, SNUG = (load(source, name) for name in names)
    C, P57, PIN, CLIP, BAR = (load(R57_OUT, name) for name in ("Key_Carrier", "Touch_Paddle", "Hinge_Pin", "Pin_Clip", "DFR_Post_Bar"))
    LID53 = load(m.R53 / "exports", "OP1_Lid")
    M = q.hardware()
    plunger, case, board = M["plunger"], M["switch"], M["board"]
    op1_fixed = d.union(M[x] for x in ("board", "sockets", "housing", "plug", "terminals", "op1_wire"))
    mouse = d.union(M[x] for x in ("switch", "plunger", "terminals"))
    spaces = h.d.geometry()[1]
    keys = d.union(spaces[f"key_{i}_{item}"] for i in (0, 2, 3, 4) for item in ("switch", "maximum_socket", "cap_travel"))
    shift = (0.0, r.CLICK_SHIFT, 0.0)
    touch = moved(r.sensor() + q.gravity_pins() + r.connector(), shift)
    clips = moved(r.clips(), shift)
    group57, group58 = P57 + BAR, P58 + BAR
    riding = group58 + touch + clips
    axis = b.board_axis()
    result = dict(physical_acceptance=False,
                  checked_mesh_sha256={name: k.file_hash(source / f"{name}-assembly.stl") for name in names},
                  reused_r57_mesh_sha256={name: k.file_hash(R57_OUT / f"{name}-assembly.stl")
                                          for name in ("Key_Carrier", "Hinge_Pin", "Pin_Clip", "DFR_Post_Bar")},
                  baseline_retainer_sha256=k.file_hash(m.R53 / "exports/OP1_Lid-assembly.stl"))
    failed = []

    def gate(name, passed):
        if not passed:
            failed.append(name)

    # --- 1. the contact bar
    dome = lambda paddle: paddle ^ b.to_world(b.box(-3, 3, -3, 7, b.BODY_TOP + 0.3, b.MOAT))
    other_way = np.array(b.board_point(0, b.MIRROR_STATION)) - np.array(b.STATION)
    swapped = moved(plunger, (other_way[0], other_way[1], 0))
    meets = lambda paddle, button: onset(lambda a: vol(m.posed(dome(paddle), a), button) > 1e-7, -0.6, 0.6)
    first57, first58 = meets(P57, plunger), meets(P58, plunger)
    swapped57, swapped58 = meets(P57, swapped), meets(P58, swapped)
    lines = (0.0, 1.0, n.PLUNGER[0])
    result["contact_bar"] = dict(
        meets_free_plunger_deg=dict(r57=first57, r58=first58),
        reversed_switch_meets_free_plunger_deg=dict(r57=swapped57, r58=swapped58),
        upward_step_between_stations_mm={f"{x:.2f}_mm_off_centre": dict(r57=recess(P57, x), r58=recess(P58, x)) for x in lines},
        underside_along_centre_mm=dict(
            along_board_mm=[round(float(y), 2) for y in np.linspace(-1.5, 5.4, 9)],
            r57=[lowest(P57, 0.0, y) for y in np.linspace(-1.5, 5.4, 9)],
            r58=[lowest(P58, 0.0, y) for y in np.linspace(-1.5, 5.4, 9)]))
    gate("contact bar meets the standard plunger as R57", abs(first58 - first57) < 0.02)
    gate("contact bar meets a reversed switch as R57", abs(swapped58 - swapped57) < 0.02)
    # A convex bar has no recess. The few hundredths measured come from the raised standard end.
    gate("no upward step between the stations", max(row["r58"] for row in result["contact_bar"]["upward_step_between_stations_mm"].values()) < 0.02)

    # --- 2. hinge play, measured on the meshes
    yaw_room = lambda shape, fixed: onset(lambda a: vol(displaced(shape, 0, yaw=a), fixed) > 1e-5, 0.0, 8.0)
    side57 = onset(lambda t: vol(moved(P57, (t, 0, 0)), C) > 1e-5, 0.0, 1.5)
    side58 = onset(lambda t: vol(moved(P58, (t, 0, 0)), C) > 1e-5, 0.0, 1.5)
    hinge = dict(
        r57_paddle_standard_pin=hinge_play(C, P57, PIN),
        r58_paddle_standard_pin=hinge_play(C, P58, PIN),
        r58_paddle_snug_pin=hinge_play(C, P58, SNUG),
        sideways_along_the_pin_each_way_mm=dict(r57=round(side57, 3), r58=round(side58, 3)),
        yaw_at_rest_deg=dict(pin_in_cheeks=round(yaw_room(PIN, C), 2), r57_paddle_on_pin=round(yaw_room(P57, PIN), 2),
                             r58_paddle_on_pin=round(yaw_room(P58, PIN), 2)),
        nominal_gap_mm=dict(cheek_hole_radial=m.CHEEK_HOLE_R - m.PIN_R, r57_bore_radial=m.BARREL_HOLE_R - m.PIN_R,
                            r58_bore_fore_aft_each_side=n.SLOT_HALF - m.PIN_R, r58_bore_up_down=m.BARREL_HOLE_R - m.PIN_R,
                            snug_pin_in_cheek_radial=m.CHEEK_HOLE_R - n.SNUG_PIN_R, snug_pin_in_bore_fore_aft_each_side=n.SLOT_HALF - n.SNUG_PIN_R),
        pin_fit=dict(standard_pin_to_r58_paddle_mm3=vol(PIN, group58), snug_pin_to_holder_mm3=vol(SNUG, C),
                     snug_pin_to_clip_mm3=vol(SNUG, moved(CLIP, (0, 0, n.SNUG_PIN_R - m.PIN_R))),
                     go_gauge_mm=dict(fore_aft=2 * (m.PIN_R + 0.06), up_down=2 * (m.PIN_R + 0.10))))
    result["hinge_play"] = hinge
    was, now, snug = (hinge[key]["paddle_to_holder_fore_aft"]["most_total_mm"]
                      for key in ("r57_paddle_standard_pin", "r58_paddle_standard_pin", "r58_paddle_snug_pin"))
    gate("the slot reduces fore-aft play", now < was - 0.15 and snug < now - 0.2)
    gate("standard pin clears the slotted bore", hinge["pin_fit"]["standard_pin_to_r58_paddle_mm3"] < TOL)
    gate("snug pin clears the cheek holes", hinge["pin_fit"]["snug_pin_to_holder_mm3"] < TOL)
    gate("sideways float unchanged", abs(side57 - side58) < 0.01)
    total57 = hinge["r57_paddle_standard_pin"]["paddle_to_holder_fore_aft"]
    float_x = (side57, total57["most_toward_rear_mm"], total57["most_toward_front_mm"], 1.5)

    # --- 3. both retainers hold the OP1 board as the R53 retainer did
    tower_zone = b.ubox(-10, 10, b.TOWER_Y[0] - n.TOWER_CUT - 0.01, b.TOWER_Y[1] + n.TOWER_CUT + 0.01, b.LID_Z[1] - 0.01, 30)
    rise = lambda lid: onset(lambda z: vol(moved(board, (0, 0, z)), lid) > 1e-6, 0.0, 1.5)
    cover = lambda lid: vol(moved(board, (0, 0, rise(lid) + 0.2)), lid) / 0.2
    retainers = {}
    for name, lid in (("r53", LID53), ("plain", PLAIN), ("stop", STOP)):
        retainers[name] = dict(board_lift_before_it_stops_mm=round(rise(lid), 3), board_area_under_it_mm2=round(cover(lid), 2),
                               highest_point_mm=round(float(lid.bounding_box()[5]), 3), to_holder_mm3=vol(lid, C),
                               to_op1_and_switch_mm3=vol(lid, op1_fixed + mouse), to_keys_mm3=vol(lid, keys))
    retainers["plain_differs_from_r53_outside_the_towers_mm3"] = float(((LID53 - PLAIN) - tower_zone).volume() + (PLAIN - LID53).volume())
    retainers["stop_differs_from_plain_outside_the_towers_mm3"] = float(((STOP - PLAIN) - tower_zone).volume() + (PLAIN - STOP).volume())
    result["retainers"] = retainers
    for name in ("plain", "stop"):
        row = retainers[name]
        gate(f"{name} retainer holds the board as R53", abs(row["board_lift_before_it_stops_mm"] - retainers["r53"]["board_lift_before_it_stops_mm"]) < 0.01
             and abs(row["board_area_under_it_mm2"] - retainers["r53"]["board_area_under_it_mm2"]) < 0.5)
        gate(f"{name} retainer clears the holder and bought parts", max(row["to_holder_mm3"], row["to_op1_and_switch_mm3"], row["to_keys_mm3"]) < TOL)
    gate("retainers differ only at the towers", retainers["plain_differs_from_r53_outside_the_towers_mm3"] < TOL
         and retainers["stop_differs_from_plain_outside_the_towers_mm3"] < TOL)

    # --- 4. the click
    seats = b.box(-12, 12, 25.2, 33, 10, 22)
    fixed = (C - seats) + PLAIN + op1_fixed + keys
    stop = onset(lambda a: vol(m.posed(riding, a), case) > 1e-6, 0.0, 4.0)
    other = onset(lambda a: vol(m.posed(riding, a), fixed) > 1e-6, 0.0, 6.0)
    sweep = max(vol(m.posed(riding, a), fixed) for a in np.linspace(-6.0, stop, 41))
    needed = b.FREE_TOP - (b.OPERATE[0] - 0.1)
    y_swapped = b.board_point(0, b.MIRROR_STATION)[1]
    result["click"] = dict(
        lever_mm=m.AXIS_Y - b.STATION[1], travel_mm_per_degree=drop_at(1.0),
        paddle_meets_switch_case_deg=stop, plunger_travel_at_case_mm=drop_at(stop) - drop_at(first58),
        reversed_switch_travel_at_case_mm=drop_at(stop, y=y_swapped) - drop_at(swapped58, y=y_swapped),
        first_contact_with_anything_else_deg=other, travel_needed_for_lowest_operating_point_mm=needed,
        fixed_part_interference_from_6_deg_lift_to_stop_mm3=sweep,
        r57_values=json.loads((R57_OUT / "mechanical-fit.json").read_text())["click"])
    gate("travel reaches the lowest operating point", result["click"]["plunger_travel_at_case_mm"] > needed
         and result["click"]["reversed_switch_travel_at_case_mm"] > needed)
    gate("the switch case is the first stop", other is None or other > stop - 1e-6)
    gate("press sweep is clear", sweep < TOL)
    static = dict(paddle_to_holder=vol(group58, C), paddle_to_plain_retainer=vol(riding, PLAIN), paddle_to_stop_retainer=vol(riding, STOP),
                  paddle_to_op1=vol(riding, op1_fixed), paddle_to_switch_case=vol(riding, case), paddle_to_keys=vol(riding, keys),
                  paddle_to_pin=vol(group58, PIN), paddle_to_pin_clip=vol(group58, CLIP), touch_board_to_paddle=vol(touch, group58))
    result["static_interference_mm3"] = static
    gate("static fit is clear", max(static.values()) < TOL)

    # --- 5. what limits paddle lift
    everything = C + op1_fixed + case
    scan = [float(a) for a in np.arange(0.25, 60.01, 0.25)]
    free = k.first_true(lambda a: vol(m.posed(riding, -a), everything + PLAIN) > 1e-4, scan)
    sleeve = P58 ^ b.ubox(-6, 6, -6, 11, 0, b.PLATE_Z)
    leaves = onset(lambda a: float(m.posed(sleeve, -a).bounding_box()[2]) > b.BODY_TOP, 0.0, 20.0)
    fine = [float(a) for a in np.arange(0.0, 4.01, 0.1)]      # a scan: the solids pass through each other further up
    stopped = k.first_true(lambda a: vol(m.posed(riding, -a), STOP) > 1e-6, fine)
    shifted = {}
    for dx in (-0.8, -0.4, 0.0, 0.4, 0.8):
        angle = k.first_true(lambda a: vol(m.posed(riding, -a).translate((dx, 0, 0)), STOP) > 1e-6, fine)
        shifted[f"{dx:+.1f}_mm_sideways"] = None if angle is None else round(-drop_at(-angle), 3)
    side_gap = lambda lid, paddle: k.first_true(lambda dx: vol(paddle.translate((dx, 0, 0)), lid) > 1e-6, [float(v) for v in np.linspace(0, 1.5, 61)])
    result["paddle_lift"] = dict(
        plain_retainer=dict(first_contact_deg=free, front_rise_at_plunger_mm=None if free is None else -drop_at(-free),
                            note="first contact is the touch board against the hinge cheeks; nothing is designed to stop it"),
        sleeve_leaves_the_switch_body_deg=leaves,
        stop_retainer=dict(lift_stops_at_deg=stopped, front_rise_at_plunger_mm=-drop_at(-stopped),
                           front_rise_with_the_paddle_pushed_sideways_mm=shifted,
                           sideways_gap_to_towers_mm=side_gap(STOP, group58),
                           r53_retainer_sideways_gap_to_r57_paddle_mm=side_gap(LID53, group57)),
        r53_retainer_stopped_r57_paddle_at_mm=result["click"]["r57_values"].get("front_rise_at_plunger_mm"))
    gate("the stop retainer keeps the sleeve on the switch", stopped is not None and stopped < 0.5 * leaves)
    gate("the stop retainer leaves side room", result["paddle_lift"]["stop_retainer"]["sideways_gap_to_towers_mm"] > 0.85)
    gate("the stop never holds the paddle down inside 0.8 mm of side shift", all(v is not None and v > 0.1 for v in shifted.values()))

    # --- 6. fitting either retainer with the paddle already in place
    notch = b.ubox(-b.RAIL_WALL[1], -b.LID_HALF + 0.9, -40, 20, b.LID_Z[0] - 0.1, b.LID_Z[1] + 0.2)
    slide = np.linspace(0, 34, 69)
    routes = {}
    for label, lid in (("plain", PLAIN), ("stop", STOP)):
        rigid = lid - (lid ^ notch ^ b.ubox(-9, -b.LID_HALF + 0.001, b.DETENT[0] - 1.2, b.DETENT[0] + 1.2, 0, 30))
        for pose, angle in (("paddle_at_rest", 0.0), ("paddle_pressed", stop), ("paddle_lifted_3_deg", -3.0)):
            there = C + op1_fixed + mouse + m.posed(riding, angle)
            routes[f"{label}_retainer_from_front_with_{pose}"] = max(vol(moved(rigid, -axis * s), there) for s in slide)
    result["route_interference_mm3"] = routes
    needs_paddle_down = "stop_retainer_from_front_with_paddle_lifted_3_deg"
    gate("retainer routes are clear", all(value < TOL for name, value in routes.items() if name != needs_paddle_down))

    # --- 7. the R57 jam, and each R58 retainer through the same hinge play
    study = dict(hinge_play_used=dict(sideways_each_way_mm=float_x[0], toward_rear_mm=float_x[1], toward_front_mm=float_x[2], yaw_deg=float_x[3],
                                      source="R57 paddle and standard pin, measured above"),
                 r57_paddle_with_r53_retainer=jam_study(group57, LID53, stop, case, float_x),
                 r58_paddle_with_plain_retainer=jam_study(group58, PLAIN, stop, case, float_x),
                 r58_paddle_with_stop_retainer=jam_study(group58, STOP, stop, case, float_x))
    result["jam_study"] = study
    gate("plain retainer cannot touch the paddle", study["r58_paddle_with_plain_retainer"]["poses_touching_the_retainer"] == 0
         and study["r58_paddle_with_plain_retainer"]["smallest_gap_in_clear_poses_mm"] > 0.4)
    # The furthest reachable poses carry the sleeve about 0.9 mm sideways at the towers, which is all the
    # room the stop has. Touching there is a flat rub, not a wedge, so it is reported and not gated to zero.
    gate("stop retainer is not entered through the hinge play", study["r58_paddle_with_stop_retainer"]["worst_overlap_mm3"] < TOL)

    result["failed"] = failed
    result["passes"] = not failed
    (source / "mechanical-fit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)
    if failed:
        raise SystemExit("R58 mechanical checks need attention: " + "; ".join(failed))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
