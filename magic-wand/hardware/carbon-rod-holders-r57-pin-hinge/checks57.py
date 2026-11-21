"""CAD checks for the R57 pin hinge and longer posts, against the R53 bought-part references.

Run in a fresh process after build57.py. Clearances only: nothing here measures a printed part.
"""
import json
from pathlib import Path
import sys

import numpy as np

import build57 as m

b = m.b
import checks53 as k  # noqa: E402  (shares the R53 helpers and the inherited hardware chain)

TOL = 1e-3
PARTS = ("Key_Carrier", "Touch_Paddle", "Hinge_Pin", "Pin_Clip", "DFR_Post_Bar", "DFR_Tall_Clip")


def drop_at(angle, y=b.STATION[1], z=b.FREE_TOP):
    """Vertical travel of a paddle point that starts at (y, z)."""
    matrix = np.asarray(m.hinge_matrix(angle))
    return z - float(matrix[2] @ (0.0, y, z, 1.0))


def hinge_bracket():
    """Nominal and pessimistic openings for the pin. Pessimistic: each printed hole 0.25 mm
    under size, 0.30 mm of sag on its closing flat, and the pin 0.15 mm over size."""
    rows = {}
    for name, radius in (("cheek", m.CHEEK_HOLE_R), ("barrel", m.BARREL_HOLE_R)):
        across = 2 * radius
        tall = 2 * radius + m.ROOF
        rows[name] = dict(
            nominal_across_mm=across, nominal_along_print_height_mm=tall, nominal_radial_gap_mm=radius - m.PIN_R,
            pessimistic_across_mm=across - 0.25, pessimistic_along_print_height_mm=tall - 0.25 - 0.30,
            pessimistic_pin_mm=2 * m.PIN_R + 0.15,
            pessimistic_spare_mm=min(across - 0.25, tall - 0.55) - (2 * m.PIN_R + 0.15))
    waist = 2 * m.WAIST[0]
    rows["pin_end_float_each_way_mm"] = (m.WELL[0] - m.CLIP_T / 2) + (waist - m.CLIP_T) / 2
    rows["pin_end_stays_inside_cheek_mm"] = m.CHEEK_X[1] - (m.PIN_HALF + rows["pin_end_float_each_way_mm"])
    rows["shortest_pin_bearing_in_a_cheek_mm"] = (m.PIN_HALF - 0.5) - rows["pin_end_float_each_way_mm"] - m.CHEEK_X[0]
    rows["paddle_side_float_each_way_mm"] = m.CHEEK_X[0] - m.BARREL_X
    return rows


def main(source=None):
    source = Path(source) if source else m.EXPORT
    k.old.configure_new_op1()
    q, h, r, d = k.q, k.h, k.r, k.d
    C, P, PIN, CLIP, BAR, TALL = (b.load(source / f"{n}-assembly.stl") for n in PARTS)
    C53 = b.load(m.R53 / "exports/Key_Carrier-assembly.stl")
    LID = b.load(m.R53 / "exports/OP1_Lid-assembly.stl")
    M = q.hardware()
    plunger, case = M["plunger"], M["switch"]
    op1_fixed = d.union(M[n] for n in ("board", "sockets", "housing", "plug", "terminals", "op1_wire"))
    loaded = d.union(M[n] for n in ("board", "sockets", "housing", "plug"))
    mouse = d.union(M[n] for n in ("switch", "plunger", "terminals"))
    spaces = h.d.geometry()[1]
    keys = d.union(spaces[f"key_{i}_{item}"] for i in (0, 2, 3, 4) for item in ("switch", "maximum_socket", "cap_travel"))
    shift = (0.0, r.CLICK_SHIFT, 0.0)
    touch = k.moved(r.sensor() + q.gravity_pins() + r.connector(), shift)
    clips = k.moved(r.clips(), shift)
    group = P + BAR
    riding = group + touch + clips
    axis = b.board_axis()
    vol, moved = k.vol, k.moved
    result = dict(physical_acceptance=False, checked_mesh_sha256={n: k.file_hash(source / f"{n}-assembly.stl") for n in PARTS},
                  reused_op1_lid_sha256=k.file_hash(m.R53 / "exports/OP1_Lid-assembly.stl"))

    # --- 1. only the hinge yoke of the key holder changed
    zone = b.box(-11.7, 11.7, 25.2, 33.0, 10.5, 40)
    result["carrier_difference_from_r53_outside_the_yoke_mm3"] = dict(
        added=float(((C - C53) - zone).volume()), removed=float(((C53 - C) - zone).volume()))
    extra = C - C53
    entered, poses_checked = {}, 0
    for name in sorted(n for n in spaces if n.startswith("key_")):
        poses = list(spaces[name].poses()) if hasattr(spaces[name], "poses") else [spaces[name]]
        poses_checked += len(poses)
        amount = max(vol(extra, pose) for pose in poses)
        if amount > TOL:
            entered[name] = round(amount, 4)
    result["key_spaces_checked"] = poses_checked
    result["key_spaces_entered_by_new_material_mm3"] = entered

    # --- 2. static fit at rest: the pin lies in the cheek holes and the paddle hangs on the pin
    static = {name: vol(C, shape) for name, shape in M.items() if name != "fasteners"}
    # The unchanged socket envelopes already intersect R53 by 0.0012 mm³. Keep that result visible
    # and reject any added interference from the new hinge. — GPT-6.2 Sol
    prior_key_overlap = vol(C53, keys)
    key_overlap = vol(C, keys)
    result["carrier_to_key_envelopes_mm3"] = dict(r53=prior_key_overlap, r57=key_overlap)
    static["carrier_added_overlap_to_keys"] = max(vol(extra, keys), key_overlap - prior_key_overlap, 0.0)
    static["lid_to_carrier"] = vol(LID, C)
    static["paddle_to_carrier"] = vol(group, C)
    static["paddle_to_lid"] = vol(riding, LID)
    static["paddle_to_op1_board_and_wire"] = vol(riding, op1_fixed)
    static["paddle_to_switch_case"] = vol(riding, case)
    static["paddle_to_keys"] = vol(riding, keys)
    static["pin_to_carrier"] = vol(PIN, C)
    static["pin_to_paddle"] = vol(PIN, group)
    static["pin_to_keys"] = vol(PIN, keys)
    static["clip_to_paddle_and_carrier"] = vol(CLIP, group + C)
    static["clip_to_pin"] = vol(CLIP, PIN)
    static["clip_to_touch_board"] = vol(CLIP, touch + clips)
    static["touch_board_to_paddle"] = vol(touch, group)
    static["standard_clips_to_paddle_board_and_posts"] = vol(clips, P + touch + BAR)
    static["touch_parts_to_carrier_and_lid"] = vol(touch + clips, C + LID)
    result["static_interference_mm3"] = static

    # --- 3. what the board rests on, and what hangs free under it
    seat = b.box(-12, 12, -12, 34, b.SEAT_Z - 0.05, b.SEAT_Z + 0.01)
    under = b.box(-11, 11, b.BOARD_FRONT, b.BOARD_REAR, b.SEAT_Z - 2.0, b.SEAT_Z + 0.01)
    relief = b.box(-8.5, 8.5, m.FRONT_END + 0.1, 25.6, b.SEAT_Z - 2.0, b.SEAT_Z + 0.01)
    relief -= b.mirrored(b.box(m.PAD[0] - 0.01, 9, m.PAD[1], m.PAD[2], 0, 40))
    result["board_support"] = dict(
        seat_area_under_a_35_mm_board_mm2=round(vol(P, seat ^ under) / 0.05, 1),
        paddle_material_within_2_mm_under_the_open_zone_mm3=vol(P, relief),
        open_zone_xy=[-8.5, m.FRONT_END + 0.1, 8.5, 25.6],
        pin_tail_envelope_to_paddle_mm3=vol(moved(q.gravity_pins(), shift), group),
        pin_tail_envelope_if_board_is_30_mm_long_mm3=vol(moved(q.gravity_pins(), (0, r.CLICK_SHIFT - 5.0, 0)), group))

    # --- 4. posts and clips: free neck for a board that is held up by parts underneath
    r31_neck = r.NECK[1] - r.NECK[0]
    reach = {}
    for lift in (0.0, 0.4, 0.8, 1.2, 1.4):
        reach[f"board_raised_{lift:.1f}_mm"] = dict(
            free_neck_mm=round(m.NECK - lift, 2), standard_clip_fits=bool(m.NECK - lift >= r.CLIP_T + 0.05),
            tall_clip_fits=bool(m.NECK - lift >= m.TALL_CLIP + 0.05), r53_free_neck_mm=round(r31_neck - lift, 2),
            r53_clip_fitted=bool(r31_neck - lift >= r.CLIP_T + 0.05))
    result["post_reach"] = dict(neck_mm=m.NECK, r53_neck_mm=r31_neck, standard_clip_mm=r.CLIP_T, tall_clip_mm=m.TALL_CLIP,
                                head_top_above_board_mm=m.NECK + m.HEAD, cases=reach,
                                tall_clip_on_post_mm3=vol(TALL, BAR), tall_clip_to_board_mm3=vol(TALL, touch))

    # --- 5. fitting routes
    routes = {}
    routes["op1_board_straight_down"] = max(vol(moved(loaded, (0, 0, z)), C) for z in np.linspace(0, 16, 33))
    routes["switch_straight_down"] = max(vol(moved(mouse, (0, 0, z)), C) for z in np.linspace(0, 10, 21))
    routes["paddle_straight_down"] = max(vol(moved(riding, (0, 0, z)), C + mouse + op1_fixed + keys) for z in np.linspace(0, 14, 57))
    travel = np.linspace(0, 26, 105)
    for label, sign in (("right", 1), ("left", -1)):
        routes[f"pin_from_the_{label}"] = max(vol(moved(PIN, (sign * x, 0, 0)), C + group) for x in travel)
        routes[f"pin_from_the_{label}_through_fitted_upper_key_mm3"] = max(vol(moved(PIN, (sign * x, 0, 0)), keys) for x in travel)
    legs = CLIP ^ b.box(-2, 2, 20, 40, 0, m.PIN_Z - 1.0)
    rigid = CLIP - legs
    routes["pin_clip_from_above"] = max(vol(moved(rigid, (0, 0, z)), group + C + PIN + touch + clips) for z in np.linspace(0, 9, 37))
    routes["pin_clip_legs_past_the_waist_peak_mm3"] = max(vol(moved(legs, (0, 0, z)), PIN) for z in np.linspace(0, 4, 81))
    routes["pin_clip_legs_to_paddle_and_carrier"] = max(vol(moved(legs, (0, 0, z)), group + C) for z in np.linspace(0, 9, 37))
    notch = b.ubox(-b.RAIL_WALL[1], -b.LID_HALF + 0.9, -40, 20, b.LID_Z[0] - 0.1, b.LID_Z[1] + 0.2)
    bump = LID ^ notch ^ b.ubox(-9, -b.LID_HALF + 0.001, b.DETENT[0] - 1.2, b.DETENT[0] + 1.2, 0, 30)
    routes["lid_from_front"] = max(vol(moved(LID - bump, -axis * s), C + op1_fixed + mouse + riding) for s in np.linspace(0, 34, 137))
    routes["post_bar_from_below"] = max(vol(moved(BAR, (0, 0, -z)), P) for z in np.linspace(0, 9, 37))
    routes["touch_board_onto_posts"] = max(vol(moved(touch, (0, 0, z)), group) for z in np.linspace(0, 12, 49))
    routes["standard_clip_slide_peak_on_neck_mm3"] = max(vol(moved(clips, (0, -y, 0)), BAR) for y in np.linspace(0, 5, 41))
    routes["standard_clip_slide_to_board_and_paddle"] = max(vol(moved(clips, (0, -y, 0)), touch + P) for y in np.linspace(0, 5, 41))
    result["route_interference_mm3"] = routes

    # --- 6. the click along the hinge arc (R53 sleeve, crowns and lid unchanged)
    dome = P ^ b.to_world(b.box(-3, 3, -3, 7, b.BODY_TOP + 0.3, b.MOAT))
    first = k.onset(lambda a: vol(m.posed(dome, a), plunger) > 1e-7, -0.6, 0.6)
    seats = b.box(-12, 12, 25.2, 33, 10, 22)   # pin, cheeks and barrel bear on each other by design
    fixed = (C - seats) + LID + op1_fixed + keys
    stop = k.onset(lambda a: vol(m.posed(riding, a), case) > 1e-6, 0.0, 4.0)
    other = k.onset(lambda a: vol(m.posed(riding, a), fixed) > 1e-6, 0.0, 6.0)
    yoke_first = k.onset(lambda a: vol(m.posed(group - PIN, a), (C ^ seats)) > 1e-4, 0.0, 12.0)
    lift = k.first_true(lambda a: vol(m.posed(riding, -a), LID) > 1e-6, [float(v) for v in np.linspace(0, 4, 81)])
    sweep = max(vol(m.posed(riding, a), fixed) for a in np.linspace(-0.97 * (lift or 0.0), stop, 41))
    needed = b.FREE_TOP - (b.OPERATE[0] - 0.1)
    result["click"] = dict(
        crown_meets_free_plunger_deg=first, lever_mm=m.AXIS_Y - b.STATION[1], travel_mm_per_degree=drop_at(1.0),
        paddle_meets_switch_case_deg=stop, plunger_travel_at_case_mm=drop_at(stop),
        first_contact_with_anything_else_deg=other,
        plunger_travel_at_that_contact_mm=None if other is None else drop_at(other),
        barrel_meets_cheek_or_deck_deg=yoke_first, travel_needed_for_lowest_operating_point_mm=needed,
        fixed_part_interference_over_sweep_mm3=sweep,
        lid_stops_paddle_deg=lift, front_rise_at_plunger_mm=None if lift is None else -drop_at(-lift))

    # --- 7. slack in the loose hinge: the paddle may ride up, forward and sideways on the pin
    slack = {}
    gap = (m.CHEEK_HOLE_R - m.PIN_R) + (m.BARREL_HOLE_R - m.PIN_R)
    side = m.CHEEK_X[0] - m.BARREL_X
    around = (C - seats) + op1_fixed + keys
    for dx in (-side, 0.0, side):
        for dy in (-gap, 0.0, gap + m.ROOF):
            for angle in (0.0, 0.98 * stop):
                slack[f"dx{dx:+.2f}_dy{dy:+.2f}_a{angle:.2f}"] = vol(moved(m.posed(group, angle), (dx, -dy, 0)), around)
    worst = max(slack, key=slack.get)
    tower = k.first_true(lambda dx: vol(group.translate((dx, 0, 0)), LID) > 1e-6, [float(v) for v in np.linspace(0, 1.0, 41)])
    result["hinge_slack"] = dict(bracket=hinge_bracket(), fore_aft_float_mm=[gap, gap + m.ROOF], cases=len(slack), worst_case=worst,
                                 worst_interference_mm3=slack[worst], sideways_gap_to_lid_towers_mm=tower,
                                 note="Slack cases move the paddle as far as the pin holes allow and test it against everything "
                                      "except the pin, cheeks, lid towers, sleeve and switch, which are what limit it.")
    print(json.dumps(result, indent=2), flush=True)

    bracket = result["hinge_slack"]["bracket"]
    difference = result["carrier_difference_from_r53_outside_the_yoke_mm3"]
    blocked = [n for n, v in static.items() if v > TOL]
    jammed = [n for n, v in routes.items() if v > TOL and not n.endswith("_mm3")]
    ok = (max(abs(v) for v in difference.values()) < 0.1 and not entered and not blocked and not jammed
          and result["board_support"]["paddle_material_within_2_mm_under_the_open_zone_mm3"] < TOL
          and result["board_support"]["pin_tail_envelope_to_paddle_mm3"] < TOL
          and result["board_support"]["pin_tail_envelope_if_board_is_30_mm_long_mm3"] < TOL
          and reach["board_raised_1.2_mm"]["standard_clip_fits"] and reach["board_raised_0.0_mm"]["tall_clip_fits"]
          and abs(first) < 0.02 and stop is not None and drop_at(stop) > needed
          and (other is None or other > stop - 1e-6) and (yoke_first is None or yoke_first > stop + 1.0)
          and sweep < TOL and lift is not None and 0.1 < -drop_at(-lift) < 1.2
          and bracket["cheek"]["pessimistic_spare_mm"] > 0 and bracket["barrel"]["pessimistic_spare_mm"] > 0
          and bracket["pin_end_stays_inside_cheek_mm"] > 0 and bracket["shortest_pin_bearing_in_a_cheek_mm"] > 2.0
          and slack[worst] < TOL)
    result["failed"] = dict(static=blocked, routes=jammed)
    result["passes"] = bool(ok)
    (source / "mechanical-fit.json").write_text(json.dumps(result, indent=2) + "\n")
    if not ok:
        raise SystemExit("R57 mechanical checks need attention")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
