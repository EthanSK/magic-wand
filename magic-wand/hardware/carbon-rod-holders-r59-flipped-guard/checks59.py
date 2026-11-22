"""CAD checks for the R59 click-side parts on the R59 holder. Clearances only; nothing measures a printed part.

Run in a fresh process after carrier59.py and build59.py.
The Gravity plug is a nominal envelope, not a measurement: a 3-way PH 2.0 mm housing 8.0 mm wide
and 4.8 mm tall, 3.6 mm of it behind the board's side-entry socket, with three 1.3 mm wires
running 6 mm straight back. The socket position is the R41 photo estimate.
"""
import json
from pathlib import Path
import sys

import numpy as np

import carrier59 as f
import build59 as p

c, n, m, b, k = f.c, f.n, f.m, f.b, f.k
import checks58 as k58  # noqa: E402  (pose and jam-study helpers)

TOL = 0.01
vol, moved, onset = k.vol, k.moved, k.onset


def main(source=None):
    source = Path(source) if source else f.EXPORT
    k.old.configure_new_op1()
    q, h, r, d = k.q, k.h, k.r, k.d
    load = lambda folder, name: b.load(Path(folder) / f"{name}-assembly.stl")
    C, GR, GL = (load(source, x) for x in ("Key_Carrier", "Finger_Guard_Right", "Finger_Guard_Left"))
    CLIP59, DL, DR, STOP59 = (load(source, x) for x in ("Pin_Clip", "DFR_Clip_Left", "DFR_Clip_Right", "OP1_Lid_Stop"))
    P, STOP58 = (load(f.R58 / "exports", x) for x in ("Touch_Paddle", "OP1_Lid_Stop"))
    PIN, CLIP57, BAR = (load(n.R57 / "exports", x) for x in ("Hinge_Pin", "Pin_Clip", "DFR_Post_Bar"))
    M = q.hardware()
    case, board = M["switch"], M["board"]
    op1 = d.union(M[x] for x in ("board", "sockets", "housing", "plug", "terminals", "op1_wire"))
    mouse = d.union(M[x] for x in ("switch", "plunger", "terminals"))
    working = h.d.geometry()[1]
    where = {name: c.placed(space, name, 1.42, f.NEARER) for name, space in working.items() if name.startswith("key_")}
    keys = d.union(where[f"key_{i}_{item}"] for i in (0, 2, 3, 4) for item in ("switch", "maximum_socket", "cap_travel"))
    shift = (0.0, r.CLICK_SHIFT, 0.0)
    touch = moved(r.sensor() + q.gravity_pins() + r.connector(), shift)
    group = P + BAR
    riding = group + touch + DL + DR
    failed, result = [], dict(physical_acceptance=False)

    def gate(name, passed):
        if not passed:
            failed.append(name)

    # --- 1. the bought Gravity plug and its wires behind the touch board
    mouth, top = b.BOARD_REAR - 1.0, b.BOARD_TOP
    plug = b.box(-4.0, 4.0, mouth - 4.6, mouth + 3.6, top + 0.3, top + 5.1)
    wires = d.union(b.box(x - 0.65, x + 0.65, mouth + 3.6, mouth + 9.6, top + 2.05, top + 3.35) for x in (-2.0, 0.0, 2.0))
    lead = plug + wires
    # How far the plug and wires could sit lower than modelled before they meet the clip.
    under = lambda clip: round(onset(lambda z: vol(lead.translate((0, 0, -z)), clip) > 1e-6, 0.0, 3.0), 3)
    rest = C + PIN + keys
    stop = onset(lambda a: vol(m.posed(riding, a), case) > 1e-6, 0.0, 4.0)
    insert = lambda clip: max(vol(lead.translate((0, float(dy), 0)), group + touch - moved(r.connector(), shift) + clip + rest) for dy in np.arange(0.0, 9.1, 1.0))
    sweep = max(vol(m.posed(lead, a), rest) for a in np.linspace(-6.0, stop, 25))
    result["gravity_plug"] = dict(
        basis="nominal PH 2.0 mm 3-way housing and R41 photo-estimated socket position; not measured",
        gap_under_plug_and_wires_to_pin_clip_mm=dict(r57_clip=under(CLIP57), r59_clip=under(CLIP59)),
        plug_in_and_pull_out_9_mm_mm3=dict(r57_clip=insert(CLIP57), r59_clip=insert(CLIP59)),
        press_and_6_deg_lift_sweep_to_holder_pin_and_keys_mm3=sweep,
        pin_clip_still_clears=dict(to_paddle_mm3=vol(CLIP59, group), to_pin_mm3=vol(CLIP59, PIN), to_touch_board_mm3=vol(CLIP59, touch), to_holder_mm3=vol(CLIP59, C)),
        grip_left_above_paddle_top_mm=p.GRIP_LOW, rear_grip_unchanged_mm=round(top - b.SEAT_Z - 0.05, 2))
    row = result["gravity_plug"]
    gate("the plug has more room over the pin clip than in R57", row["gap_under_plug_and_wires_to_pin_clip_mm"]["r59_clip"] > row["gap_under_plug_and_wires_to_pin_clip_mm"]["r57_clip"] + 0.5)
    gate("the plug goes in and out and rides through the click", max(row["plug_in_and_pull_out_9_mm_mm3"]["r59_clip"], sweep) < TOL)
    gate("the pin clip still fits", max(row["pin_clip_still_clears"].values()) < TOL)

    # --- 2. left against right, in CAD
    mirror = lambda shape: shape.mirror((1.0, 0.0, 0.0))
    differ = lambda shape, zone: round(float(((shape - mirror(shape)) ^ zone).volume() + ((mirror(shape) - shape) ^ zone).volume()), 4)
    posts = b.mirrored(b.box(b.HOLE_X - 2.6, b.HOLE_X + 2.6, b.HOLE_Y - 2.8, b.HOLE_Y + 2.8, 12, 20))
    hinge = b.mirrored(b.box(7.0, 12.0, 26.0, 32.65, 13.0, 20.6))
    result["left_against_right"] = dict(paddle_post_holes_differ_mm3=differ(P, posts), holder_hinge_holes_differ_mm3=differ(C, hinge),
                                        post_bar_differs_mm3=differ(BAR, b.box(-12, 12, 10, 20, 12, 26)),
                                        note="zero means the CAD holes are mirror images; any difference on the print comes from slicing or printing")

    # --- 3. thicker post clips
    result["post_clips"] = dict(thickness_mm=p.CLIP_T, r31_thickness_mm=r.CLIP_T, arm_section_gain=round(p.CLIP_T / r.CLIP_T, 2),
                                free_neck_left_over_mm=round(m.NECK - p.CLIP_T, 2), snap_overlap_with_post_necks_mm3=round(vol(DL + DR, BAR), 4),
                                r31_snap_overlap_mm3=round(vol(moved(r.clips(), shift), BAR), 4), to_touch_board_mm3=vol(DL + DR, touch), to_paddle_mm3=vol(DL + DR, P),
                                left_is_mirror_of_right_mm3=round(float((DL - mirror(DR)).volume() + (mirror(DR) - DL).volume()), 5))
    row = result["post_clips"]
    gate("the thicker post clips fit the necks and the board", row["free_neck_left_over_mm"] > 0.5 and max(row["to_touch_board_mm3"], row["to_paddle_mm3"]) < TOL
         and row["snap_overlap_with_post_necks_mm3"] <= row["r31_snap_overlap_mm3"] * p.CLIP_T / r.CLIP_T + 0.02)

    # --- 4. the stop retainer
    rise = lambda lid: onset(lambda z: vol(moved(board, (0, 0, z)), lid) > 1e-6, 0.0, 1.5)
    fine = [float(a) for a in np.arange(0.0, 4.01, 0.1)]
    lifted = k.first_true(lambda a: vol(m.posed(riding, -a), STOP59) > 1e-6, fine)
    side = lambda lid: k.first_true(lambda dx: vol(group.translate((dx, 0, 0)), lid) > 1e-6, [float(v) for v in np.linspace(0, 1.5, 61)])
    axis = b.board_axis()
    notch = b.ubox(-b.RAIL_WALL[1], -b.LID_HALF + 0.9, -40, 20, b.LID_Z[0] - 0.1, b.LID_Z[1] + 0.2)
    rigid = STOP59 - (STOP59 ^ notch ^ b.ubox(-9, -b.LID_HALF + 0.001, b.DETENT[0] - 1.2, b.DETENT[0] + 1.2, 0, 30))
    slide = np.linspace(0, 34, 69)
    routes = {pose: max(vol(moved(rigid, -axis * s), C + op1 + mouse + m.posed(riding, angle)) for s in slide) for pose, angle in (("paddle_at_rest", 0.0), ("paddle_pressed", stop))}
    float_x = (0.25, 0.55, 0.644, 1.5)
    jam = k58.jam_study(group, STOP59, stop, case, float_x)
    press = max(vol(k58.displaced(group, a, dx, 0.0, 0.0), STOP59) for a in np.linspace(0.0, stop, 9) for dx in (-0.6, -0.3, 0.0, 0.3, 0.6))
    stem = (n.WALL - n.WALL_TRIM) + n.FLANGE + n.STEM_CLEAR
    thick = b.LID_HALF - stem
    result["stop_retainer"] = dict(
        board_lift_before_it_stops_mm=round(rise(STOP59), 3), to_holder_mm3=vol(STOP59, C), to_op1_and_switch_mm3=vol(STOP59, op1 + mouse), to_keys_mm3=vol(STOP59, keys),
        paddle_at_rest_mm3=vol(riding, STOP59), whole_press_stroke_with_0_6_mm_side_shift_mm3=press, lift_stops_at_plunger_mm=round(-k58.drop_at(-lifted), 3),
        sideways_gap_to_towers_mm=dict(r58=side(STOP58), r59=side(STOP59)), slide_in_from_front_mm3=routes, hinge_play_study=jam,
        stem_root_section_mm2=dict(r58=round(thick * (b.TOWER_Y[1] - b.TOWER_Y[0]), 2), r59=round(thick * (b.TOWER_Y[1] - p.STEM_FROM_Y), 2)),
        stem_root_section_modulus_mm3=dict(r58=round((b.TOWER_Y[1] - b.TOWER_Y[0]) * thick ** 2 / 6, 3), r59=round((b.TOWER_Y[1] - p.STEM_FROM_Y) * thick ** 2 / 6, 3)),
        needs_paddle_down_while_sliding_in=True,
        lower_ledge="the step under the retainer track is the OP1 board's own slot, open at the front because the board's true length is unknown; the retainer rides on the ledge above it, under the two rail lips")
    row = result["stop_retainer"]
    gate("the stop retainer holds the board and clears holder and bought parts", abs(row["board_lift_before_it_stops_mm"] - 0.15) < 0.01 and max(row["to_holder_mm3"], row["to_op1_and_switch_mm3"], row["to_keys_mm3"]) < TOL)
    gate("nothing of the retainer is in the press stroke", max(row["paddle_at_rest_mm3"], press) < 1e-6)
    gate("the retainer stops lift and keeps its side room", lifted is not None and row["sideways_gap_to_towers_mm"]["r59"] > 0.9)
    gate("the retainer slides in with the paddle down", max(routes.values()) < TOL)
    gate("hinge play does not push the paddle into the retainer", jam["poses_touching_the_retainer"] == 0)

    # --- 5. the two optional R58 backing strips on the R59 holder
    fitted = lambda skip: d.union(where[f"key_{j}_{item}"] for j in (0, 2, 3, 4) for item in ("switch", "maximum_socket") if (j, item) != skip)
    strips = {}
    for name, sign, key, guard in (("Socket_Backer_Left", -1.0, 0, GL), ("Socket_Backer_Right", 1.0, 2, GR)):
        tool = load(f.R58 / "exports", name)
        way = lambda extra: max(vol(tool.translate((sign * float(dx), 0, 0)), C + fitted((key, "maximum_socket")) + extra) for dx in np.arange(0.0, 26.1, 2.0))
        strips[name] = dict(slide_in_with_guard_off_mm3=way(b.box(0, 0.001, 0, 0.001, 0, 0.001) - b.box(-1, 1, -1, 1, -1, 1)), slide_in_with_guard_on_mm3=way(guard))
    result["optional_backing_strips"] = dict(strips, when="with a guard off, hold the socket up with a fingertip; use a strip only to back a socket with the guard left on")
    gate("the R58 backing strips still pass", all(max(row.values()) < TOL for row in strips.values()))

    result.update(failed=failed, passes=not failed)
    text = json.dumps(result, indent=2) + "\n"
    for folder in {source, f.HERE / "exports"}:
        (Path(folder) / "click-fit.json").write_text(text)
    print(text, flush=True)
    if failed:
        raise SystemExit("R59 click checks need attention: " + "; ".join(failed))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
