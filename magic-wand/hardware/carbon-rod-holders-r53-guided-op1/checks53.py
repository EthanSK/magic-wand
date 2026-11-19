"""Check the exported R53 bodies against the bought-part references, along every assembly
route and along the hinge arc. CAD clearances only: nothing here measures a printed part.

Run in a fresh process (the inherited OP1 configurator applies its offset once).
"""
import json
import math
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

import build53 as b

sys.path.insert(0, str(b.R52))
sys.path.insert(0, str(b.R51))
import build52 as d  # noqa: E402

old, q, h, r = d.old, d.q, d.h, d.r
TOL = 1e-3


def vol(a, c):
    return float((a ^ c).volume())


def onset(test, low, high, steps=40):
    """Smallest value in [low, high] where test becomes true (test(low) is false)."""
    if test(low):
        return low
    if not test(high):
        return None
    for _ in range(steps):
        mid = (low + high) / 2
        if test(mid):
            high = mid
        else:
            low = mid
    return high


def first_true(test, values):
    """Scan, then refine: for tests that are true only over part of the range."""
    previous = values[0]
    if test(previous):
        return previous
    for value in values[1:]:
        if test(value):
            return onset(test, previous, value, 24)
        previous = value
    return None


def file_hash(path):
    from hashlib import sha256
    return sha256(Path(path).read_bytes()).hexdigest()


def moved(shape, offset):
    return shape.translate(tuple(float(v) for v in offset))


def drop_at(angle, y=b.STATION[1], z=b.FREE_TOP):
    """Vertical travel of a paddle point that starts at (y, z)."""
    m = np.asarray(b.hinge_matrix(angle))
    return z - float(m[2] @ (0.0, y, z, 1.0))


def main(source=None):
    source = Path(source) if source else b.EXPORT
    old.configure_new_op1()
    assert abs(q.OP1_YAW - b.YAW) < 1e-9 and np.allclose(q.PLUNGER_XY, b.STATION, atol=1e-5)
    assert abs(q.PCB_TOP - b.PCB_TOP) < 1e-6 and abs(q.FREE_TOP - b.FREE_TOP) < 1e-6
    C, P, CAP, LID, BAR = (b.load(source / f"{n}-assembly.stl") for n in
                           ("Key_Carrier", "Touch_Paddle", "Hinge_Cap", "OP1_Lid", "DFR_Post_Bar"))
    C52 = b.load(b.R52 / "exports/Key_Carrier-assembly.stl")
    M = q.hardware()
    plunger, case = M["plunger"], M["switch"]
    op1_fixed = d.union(M[k] for k in ("board", "sockets", "housing", "plug", "terminals", "op1_wire"))
    loaded = d.union(M[k] for k in ("board", "sockets", "housing", "plug"))
    mouse = d.union(M[k] for k in ("switch", "plunger", "terminals"))
    spaces = h.d.geometry()[1]
    keys = d.union(spaces[f"key_{i}_{item}"] for i in (0, 2, 3, 4) for item in ("switch", "maximum_socket", "cap_travel"))
    rod = h.base.rod()
    shift = (0.0, r.CLICK_SHIFT, 0.0)
    touch = moved(r.sensor() + q.gravity_pins() + r.connector(), shift)
    clips = moved(r.clips(), shift)
    group = P + BAR
    riding = group + touch + clips
    axis = b.board_axis()
    result = dict(physical_acceptance=False, checked_mesh_sha256={
        n: file_hash(source / f"{n}-assembly.stl") for n in ("Key_Carrier", "Touch_Paddle", "Hinge_Cap", "OP1_Lid", "DFR_Post_Bar")})

    # --- 1. the four outer keys are the R52 carrier outside the centre zone
    zone = b.box(b.ZONE[0] - 0.02, b.ZONE[1] + 0.02, -30, 40, -20, 40)
    result["key_zone_difference_from_r52_mm3"] = dict(added=float(((C - C52) - zone).volume()), removed=float(((C52 - C) - zone).volume()))
    # The print-facing bevels are confined to these portions of the underside
    # plus the leading corner of one key flange. Check the complete bearing
    # on each physical Choc flange against the previously printed carrier.
    lower = b.box(-33,33,-22,33,-8,6.04)
    left_underside = b.box(-34.1,-23.45,-22,33,-8,13.50)
    outer_corner = b.box(14.12,16.63,-14.1,-6.84,10.46,12.83)
    # Isolated sub-bead ramp tips under the right rear key are eased into the previous wall.
    ramp_tips = b.box(20.7,24.0,17.9,25.6,7.1,9.0)
    from carrier53 import finger_rest_brace_envelope
    permitted = zone + lower + left_underside + outer_corner + ramp_tips + finger_rest_brace_envelope()
    result["unplanned_outer_shape_change_mm3"] = dict(added=float(((C-C52)-permitted).volume()),
                                                       removed=float(((C52-C)-permitted).volume()))
    bearing_path=source/'key-bearing.json'
    if not bearing_path.exists() or json.loads(bearing_path.read_text())['new_carrier_sha256'] != result['checked_mesh_sha256']['Key_Carrier']:
        # The earlier generator configures its global key layout once per process.
        import subprocess
        subprocess.run([sys.executable,str(b.R52/'key_lands52.py'),str(source)],check=True)
    lands=json.loads(bearing_path.read_text())['key_lands']
    prior=json.loads((b.R52/'exports/key-bearing.json').read_text())['key_lands']
    retained={key:lands[key]['new_flange_bearing_mm2']/prior[key]['new_flange_bearing_mm2'] for key in lands}
    result["key_flange_bearing_fraction_of_r52"] = retained
    # Every inherited switch, socket, cap and socket-loading space, pose by pose.
    # Only material that R52 did not have can count against R53.
    extra = C - C52
    worse, pose_count = {}, 0
    for n in sorted(n for n in spaces if n.startswith("key_")):
        poses = list(spaces[n].poses()) if hasattr(spaces[n], "poses") else [spaces[n]]
        pose_count += len(poses)
        amount = max(vol(extra, pose) for pose in poses)
        if amount > TOL:
            worse[n] = round(amount, 4)
    result["key_spaces_checked"] = dict(names=len([n for n in spaces if n.startswith("key_")]), poses=pose_count)
    result["key_spaces_entered_by_new_material_mm3"] = worse

    # --- 2. static fit of the fixed parts
    static = {k: vol(C, v) for k, v in M.items() if k != "fasteners"}
    # Each switch is fitted independently. Apply the same intersection tolerance
    # to each bought assembly as to the board, lid, and other individual parts.
    for key in (0, 2, 3, 4):
        seated = d.union(spaces[f"key_{key}_{part}"] for part in ("switch", "maximum_socket", "cap_travel"))
        static[f"seated_key_{key}"] = vol(C, seated)
    static["rod"] = vol(C - h.base.clip_bands(), rod) if hasattr(h.base, "clip_bands") else vol(C, rod)
    static["lid_to_carrier"] = vol(LID, C)
    static["lid_to_op1"] = vol(LID, op1_fixed + mouse)
    static["cap_to_carrier"] = vol(CAP, C)
    static["lid_and_cap_to_keys"] = vol(LID + CAP, keys)
    static["cap_to_paddle"] = vol(CAP, riding)
    static["paddle_to_carrier"] = vol(group, C)
    static["paddle_to_lid"] = vol(riding, LID)
    static["paddle_to_op1_board_and_wire"] = vol(riding, op1_fixed)
    static["paddle_to_switch_case"] = vol(riding, case)
    static["paddle_to_keys"] = vol(riding, keys)
    static["touch_board_to_paddle"] = vol(touch, group)
    static["clips_to_paddle_and_board"] = vol(clips, P + touch)
    static["touch_parts_to_carrier_lid_cap"] = vol(touch + clips, C + LID + CAP)
    result["static_interference_mm3"] = static
    result["clip_on_post_neck_mm3"] = vol(clips, BAR)

    # --- 3. loading routes
    routes = {}
    routes["op1_board_straight_down"] = max(vol(moved(loaded, (0, 0, z)), C) for z in np.linspace(0, 16, 33))
    float_cases = []
    for across, along in ((0.40, 0), (-0.40, 0), (0, 0.42), (0, -0.42), (0.28, 0.28), (-0.28, -0.28), (0.28, -0.28), (-0.28, 0.28)):
        off = np.array(b.board_point(across, along)) - np.array(b.board_point(0, 0))
        float_cases.append(max(vol(moved(loaded, (off[0], off[1], z)), C) for z in (0.0, 0.4, 1.2, 3.0)))
    routes["op1_board_at_pocket_float_extremes"] = max(float_cases)
    routes["switch_straight_down"] = max(vol(moved(mouse, (0, 0, z)), C) for z in np.linspace(0, 10, 21))
    routes["paddle_straight_down"] = max(vol(moved(riding, (0, 0, z)), C + mouse + op1_fixed + keys) for z in np.linspace(0, 14, 57))
    ridge = b.box(-4, 4, 31.4, 32.7, b.WALL_TOP - 0.005, 21)
    routes["cap_from_rear"] = max(vol(moved(CAP, (0, y, 0)), (C - ridge) + riding) for y in np.linspace(0, 9, 37))
    routes["cap_over_latch_ridge_peak_mm3"] = max(vol(moved(CAP, (0, y, 0)), C ^ ridge) for y in np.linspace(0, 2.4, 49))
    notch = b.ubox(-b.RAIL_WALL[1], -b.LID_HALF + 0.9, -40, 20, b.LID_Z[0] - 0.1, b.LID_Z[1] + 0.2)
    bump = LID ^ notch ^ b.ubox(-9, -b.LID_HALF + 0.001, b.DETENT[0] - 1.2, b.DETENT[0] + 1.2, 0, 30)
    lid_body = LID - bump
    stations = np.linspace(0, 34, 137)
    routes["lid_from_front"] = max(vol(moved(lid_body, -axis * s), C + op1_fixed + mouse + riding) for s in stations)
    routes["lid_latch_bump_peak_mm3"] = max(vol(moved(bump, -axis * s), C) for s in stations)
    routes["lid_latch_bump_seated_mm3"] = vol(bump, C)
    routes["post_bar_from_below"] = max(vol(moved(BAR, (0, 0, -z)), P) for z in np.linspace(0, 8, 33))
    routes["touch_board_onto_posts"] = max(vol(moved(touch, (0, 0, z)), group) for z in np.linspace(0, 12, 49))
    result["route_interference_mm3"] = routes

    # --- 4. the click along the hinge arc
    dome = P ^ b.to_world(b.box(-3, 3, -3, 7, b.BODY_TOP + 0.3, b.MOAT))
    first = onset(lambda a: vol(b.posed(dome, a), plunger) > 1e-7, -0.6, 0.6)
    fixed = C + LID + CAP + op1_fixed + keys
    travel_per_degree = drop_at(1.0)
    stop = onset(lambda a: vol(b.posed(riding, a), case) > 1e-6, 0.0, 4.0)
    other = onset(lambda a: vol(b.posed(riding, a), fixed) > 1e-6, 0.0, 6.0)
    lift = first_true(lambda a: vol(b.posed(riding, -a), LID) > 1e-6, [float(v) for v in np.linspace(0, 4, 81)])
    sweep = [float(a) for a in np.linspace(-0.97 * (lift or 0.0), stop, 41)]
    sweep_fixed = max(vol(b.posed(riding, a), fixed) for a in sweep)
    needed = b.FREE_TOP - (b.OPERATE[0] - 0.1)
    result["click"] = dict(
        crown_meets_free_plunger_deg=first, lever_mm=b.AXIS_Y - b.STATION[1], travel_mm_per_degree=travel_per_degree,
        paddle_meets_switch_case_deg=stop, plunger_travel_at_case_mm=drop_at(stop),
        first_contact_with_anything_else_deg=other,
        plunger_travel_at_that_contact_mm=None if other is None else drop_at(other),
        travel_needed_for_lowest_operating_point_mm=needed,
        fixed_part_interference_over_sweep_mm3=sweep_fixed)
    # A lower free position, as allowed by the drawing: the paddle rests lower and still reaches the case.
    low = onset(lambda a: vol(b.posed(dome, a), moved(plunger, (0, 0, -0.55))) > 1e-7, -0.2, 3.0)
    result["click"]["rest_angle_for_free_position_6_80_deg"] = low
    # Switch plugged in the other way round: the second crown is over the plunger.
    other_way = np.array(b.board_point(0, b.MIRROR_STATION)) - np.array(b.STATION)
    swapped = moved(plunger, (other_way[0], other_way[1], 0))
    result["click"]["reversed_switch_crown_meets_plunger_deg"] = onset(lambda a: vol(b.posed(dome, a), swapped) > 1e-7, -0.6, 0.6)
    rest2 = result["click"]["reversed_switch_crown_meets_plunger_deg"]
    y2 = b.board_point(0, b.MIRROR_STATION)[1]
    result["click"]["reversed_switch_travel_at_case_mm"] = drop_at(stop, y=y2) - drop_at(rest2, y=y2)

    # --- 5. lift limits
    free_lift = onset(lambda a: vol(b.posed(riding, -a), C + CAP + op1_fixed + keys) > 1e-6, 0.0, 30.0)
    result["lift"] = dict(lid_stops_paddle_deg=lift, front_rise_at_plunger_mm=None if lift is None else -drop_at(-lift),
                          without_lid_next_stop_deg=free_lift,
                          without_lid_front_rise_mm=None if free_lift is None else -drop_at(-free_lift),
                          sleeve_overlap_on_case_at_rest_mm=b.BODY_TOP - b.SLEEVE_RIM)

    # --- 6. play in the hinge: shift, yaw and roll the paddle within its clearances
    def displaced(shape, angle, dx=0.0, yaw=0.0, roll=0.0):
        pivot = (0.0, b.AXIS_Y, b.AXIS_Z)
        s = shape.translate(tuple(-v for v in pivot)).rotate((0, roll, yaw)).translate(pivot).translate((dx, 0, 0))
        return b.posed(s, angle)

    thrust = b.JOURNAL_X[0] - b.THRUST_X
    # The journals bear on their V seats and the keel on the cheek faces. Those contacts are the
    # hinge itself, so the seats are left out and everything else must stay clear.
    seats = d.r.mirrored(b.box(b.THRUST_X - 0.3, b.WALL_X[0] + 0.05, 26.8, b.REAR_WALL_Y + 0.05, 13.8, b.CAP_Z[0]))
    around = (C - seats) + keys + op1_fixed
    play = {}
    for dx in (-thrust, 0.0, thrust):
        for yaw in (-0.35, 0.0, 0.35):
            for roll in (-0.5, 0.0, 0.5):
                for angle in (-lift * 0.9, 0.0, stop * 0.98):
                    key = f"dx{dx:+.2f}_yaw{yaw:+.2f}_roll{roll:+.2f}_a{angle:+.2f}"
                    play[key] = vol(displaced(group, angle, dx, yaw, roll), around)
    worst = max(play, key=play.get)
    side = first_true(lambda dx: vol(group.translate((dx, 0, 0)), LID) > 1e-6, [float(v) for v in np.linspace(0, 1.0, 41)])
    result["hinge_play"] = dict(end_float_each_way_mm=thrust, cases=len(play), worst_case=worst,
                                worst_interference_mm3=play[worst], sideways_gap_to_lid_towers_mm=side,
                                note="Shift, yaw and roll are test inputs at or beyond the nominal hinge clearances.")
    print(json.dumps(result, indent=2), flush=True)

    ok = (max(result["unplanned_outer_shape_change_mm3"].values()) < 0.1 and retained["0"] >= .865 and min(v for k,v in retained.items() if k!="0") >= .93 and not worse
          and all(v < TOL for v in static.values())
          and result["clip_on_post_neck_mm3"] < TOL
          and all(v < TOL for k, v in routes.items() if not k.startswith(("cap_over", "lid_latch")))
          and abs(first) < 0.02 and stop is not None and drop_at(stop) > needed
          and (other is None or other > stop - 1e-6) and sweep_fixed < TOL
          and lift is not None and 0.1 < -drop_at(-lift) < 1.2
          and play[worst] < TOL)
    result["passes"] = bool(ok)
    (source / "mechanical-fit.json").write_text(json.dumps(result, indent=2) + "\n")
    if not ok:
        raise SystemExit("Mechanical checks need attention")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
