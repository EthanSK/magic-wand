"""Verify the exported R52 solids and reference hardware in assembly coordinates."""
import json
import math
import numpy as np
import build52 as d
import mechanical_checks51 as m


def main():
    old, q, h = d.old, d.q, d.h
    old.configure_new_op1()
    C, P = (
        old.baseline.b.load(d.EXPORT / (n + "-assembly.stl"))
        for n in ["Key_Carrier", "DFRobot_Hole_Bracket"]
    )
    M = q.hardware()
    permanent = d.union(
        M[k] for k in ["board", "sockets", "housing", "plug", "switch", "terminals", "op1_wire"]
    )
    bearing = old.pivot_hardware()
    axle = d.union(bearing.values())
    ref = old.baseline.b.load(d.PREV / "exports/Key_Carrier-assembly.stl")
    feet,heels=d.stop_parts(C,P)
    button = M["plunger"]
    crown = P ^ d.dome()

    def placed(s, a, roll=0, dx=0, dz=0):
        return m.roll_at_hinge(old.world(s, a), roll, dx, dz)

    rest = m.onset(lambda a: m.vol(button, placed(crown, a)) > 1e-8, (-1.6, -0.5))
    reviews = {}
    roll = math.degrees(
        math.atan(
            2
            * (d.RUNNING_RADIUS + 0.105 * math.cos(math.radians(67)) ** 4 - old.SLEEVE_RADIUS)
            / (2 * d.HALF)
        )
    )
    # The cheeks close 0.10 mm per side at assembly onto the 12 mm sleeve.
    # Test the actual final thrust plates, with any axial slide permitted:
    # if the x extents no longer fit between both cheek planes, roll stops.
    faces = d.thrust_faces()
    clamped_gap = old.SLEEVE_LENGTH

    def width_at_roll(angle):
        s = faces.rotate((0, angle, 0))
        lo, _, _, hi, _, _ = s.bounding_box()
        return hi - lo

    stopped_roll = m.onset(lambda a: width_at_roll(a) > clamped_gap, (0.0, 2.0))
    # Confirm both limiting rounded ends meet real printed cheek material at
    # either side of the travel, including the small offset to centre them.
    guides_world = placed(faces, 0)
    guide_contact = {}
    clamped = []
    for side in (-1, 1):
        lo, hi = sorted([side * old.FORK_INNER, side * old.FORK_OUTER])
        cheek = C ^ d.box(
            lo - 0.002, hi + 0.002, old.AXIS_WORLD_Y - 3, old.AXIS_WORLD_Y + 3, 11.1, 24.0
        )
        clamped.append(cheek.translate((-side * (old.FORK_INNER - old.SLEEVE_LENGTH / 2), 0, 0)))
    for direction in (-1, 1):
        tilted = m.roll_at_hinge(guides_world, direction * (stopped_roll + 0.20))
        lo, _, _, hi, _, _ = tilted.bounding_box()
        centred = tilted.translate((-(lo + hi) / 2, 0, 0))
        guide_contact[str(direction)] = [m.vol(centred, v) for v in clamped]
    bearing_only = roll
    roll = min(roll, stopped_roll)
    for label, tilt, dx, dz in [
        ("centre", 0, 0, 0),
        ("left", roll, -0.18, 0),
        ("right", -roll, 0.18, 0),
        ("high", 0, 0, 0.128),
        ("low", 0, 0, -0.128),
    ]:
        stop = m.onset(lambda a: m.vol(feet, placed(heels, a, tilt, dx, dz)) > 1e-8, (-0.5, 0.9))
        pad = placed(crown, stop, tilt, dx, dz)
        drop = m.onset(
            lambda delta: m.vol(button.translate((0, 0, -delta)), pad) < 1e-8, (0.0, 1.2)
        )
        reviews[label] = dict(
            stop_deg=stop,
            plunger_drop_mm=drop,
            paddle_case_interference_mm3=m.vol(placed(P, stop, tilt, dx, dz), permanent),
        )
    fixed = reviews["centre"]["stop_deg"]
    ns = h.d.geometry()[1]
    keys = d.union(
        ns[f"key_{i}_{item}"]
        for i in (0, 2, 3, 4)
        for item in ("switch", "maximum_socket", "cap_travel")
    )
    static = {k: m.vol(C, v) for k, v in M.items() if k != "fasteners"}
    static["four_keys"] = m.vol(keys, C)
    static["axle"] = m.vol(axle, C)
    static["paddle_and_sleeve_fitting"] = max(
        m.vol((placed(P, rest) + bearing["pivot-sleeve"]).translate((0, 0, z)), C + permanent)
        for z in np.linspace(0, 14, 29)
    )
    for name, sign in [("pivot-screw", -1), ("pivot-locknut", 1)]:
        static[name + "_insertion"] = max(
            m.vol(bearing[name].translate((sign * x, 0, 0)), C + placed(P, rest) + permanent)
            for x in np.linspace(0, 32, 33)
        )
    static["dfr_board_insertion"] = max(
        m.vol((d.r.sensor() + q.gravity_pins()).translate((0, 0, z)), P)
        for z in np.linspace(0, 12, 25)
    )
    sweep = {}
    for k, obstacle in [("carrier", C), ("axle", axle), ("OP1", permanent), ("outer_keys", keys)]:
        sweep[k] = max(
            m.vol(placed(P, a), obstacle) for a in np.linspace(rest - 0.02, fixed - 0.008, 13)
        )
    changed_entry = ref ^ d.board_entry_relief()
    key_land_loss = {}
    for i in (0, 2, 3, 4):
        key = ns[f"key_{i}_switch"]
        local_band = d.union(
            key.translate(v)
            for v in ((0.75, 0, 0), (-0.75, 0, 0), (0, 0.75, 0), (0, -0.75, 0), (0, 0, 0.75))
        )
        key_land_loss[str(i)] = m.vol(changed_entry, local_band)
    shifted = M["board"].translate((0, 0, -0.10))
    seat_support = m.vol(C, shifted) / 0.10
    mouse = d.union(M[k] for k in ("switch", "plunger", "terminals"))
    mouse_sweep = max(m.vol(mouse.translate((0, 0, z)), C + keys) for z in np.linspace(0, 9, 19))
    springs = []
    # Nonmoving carrier is checked separately to avoid counting the integral
    # arms' intentional connection to their own roots as a collision.
    stationary = C
    for y, side in zip(h.h32.EYELETS, (1, -1)):
        root, leaf, tip = d.arm_features(y, side)
        stationary -= q.board_frame(leaf + tip)
    board = d.union(M[k] for k in ("board", "sockets", "plug", "housing"))
    approach = [board.transform(d.entry_transform(t)) for t in np.linspace(0, 1, 33)] + [
        board.transform(d.entry_transform(1)).translate((0, 0, z)) for z in np.linspace(0, 16, 17)
    ]
    rod = h.base.rod()
    lead_to_rod = min(b.min_gap(rod, 4.0) for b in approach)
    rod_insertion = max(m.vol(b, rod) for b in approach)
    pitch_tolerance = max(m.vol(C, q.op1_board(pitch, 3.6)) for pitch in (17.3, 17.9, 18.5))
    for y, side in zip(h.h32.EYELETS, (1, -1)):
        root, leaf, tip = d.arm_features(y, side)
        rootw = q.board_frame(root)
        _, park_leaf, park_tip = d.arm_features(y, side, lift=d.RELEASE)
        parked = q.board_frame(park_leaf + park_tip)
        # Ignore the fixed first 1.35 mm embedded in the filleted anchor.
        root_y = y + side * d.SPRING_LENGTH
        lo, hi = sorted((root_y - side * 1.36, y - side * 2.7))
        free_window = q.board_frame(d.box(-25, 25, lo, hi, 6, 22))
        poses = np.linspace(0, d.RELEASE, 8)
        swept_interference = 0.0
        board_interference = 0.0
        for lift in poses:
            _, lv, tp = d.arm_features(y, side, lift)
            at = q.board_frame(lv + tp)
            swept_interference = max(swept_interference, m.vol(at ^ free_window, stationary))
            board_interference = max(board_interference, m.vol(at, board))
        springs.append(
            dict(
                peg_on_pcb_mm3=m.vol(M["board"], q.board_frame(tip)),
                upward_capture_mm3=m.vol(
                    M["board"].translate((0, 0, 1.35)), q.board_frame(tip + leaf)
                ),
                open_board_sweep_mm3=max(m.vol(b, parked + stationary) for b in approach),
                root_at_seat_mm3=m.vol(rootw, ref),
                working_leaf_to_carrier_during_release_mm3=swept_interference,
                working_leaf_to_board_during_release_mm3=board_interference,
                eyelet_world_xy=q.board_point(0, y),
            )
        )
    outlet = old.baseline.cable48.check(h, C)
    result = dict(
        physical_acceptance=False,
        first_contact_deg=rest,
        presses=reviews,
        max_nominal_bearing_roll_deg=roll,
        thrust_face_further_roll_overlap_against_both_actual_cheeks_mm3=guide_contact,
        checked_mesh_sha256={
            n: m.file_hash(d.EXPORT / (n + "-assembly.stl"))
            for n in ["Key_Carrier", "DFRobot_Hole_Bracket"]
        },
        unconstrained_bearing_roll_deg=bearing_only,
        thrust_face_limit_deg=stopped_roll,
        clamped_axial_end_play_mm=old.SLEEVE_LENGTH - 2 * d.THRUST_HALF,
        static_interferences_mm3=static,
        moving_interferences_mm3=sweep,
        snaps=springs,
        wire_outlet=outlet,
        carrier_material_removed_within_0_75mm_of_each_switch_mm3=key_land_loss,
        switch_insertion_interference_mm3=mouse_sweep,
        nominal_seat_support_area_mm2=seat_support,
        lift_mm=d.RELEASE,
        printed_flexure_life_measured=False,
        tapered_beam_peak_outer_fibre_strain=d.nominal_bending_strain(),
        board_feed_to_rod_mm3=rod_insertion,
        board_feed_to_rod_gap_mm=lead_to_rod,
        pitch_17_3_to_18_5_at_3_6_mm_eyelet_interference_mm3=pitch_tolerance,
        estimated_outer_fibre_strain_uniform_cantilever=1.5
        * 1.14
        * d.RELEASE
        / (d.SPRING_LENGTH - 1.25) ** 2,
        bore_minimum_in_slice_checked_separately=True,
    )
    print(json.dumps(result, indent=2), flush=True)
    result["passes"] = (
        max(static.values()) < 0.001
        and max(sweep.values()) < 0.001
        and mouse_sweep < 0.001
        and seat_support > 25
        and max(key_land_loss.values()) < 0.001
        and outlet["passes"]
        and all(
            0.48 < v["plunger_drop_mm"] < 0.86 and v["paddle_case_interference_mm3"] < 0.001
            for v in reviews.values()
        )
        and all(
            v["upward_capture_mm3"] > 0.01
            and v["open_board_sweep_mm3"] < 0.001
            and v["root_at_seat_mm3"] > 0.3
            and v["working_leaf_to_carrier_during_release_mm3"] < 0.01
            and v["working_leaf_to_board_during_release_mm3"] < 0.001
            for v in springs
        )
    )
    result["passes"] = bool(
        result["passes"]
        and rod_insertion < 0.001
        and pitch_tolerance < 0.001
        and min(v for pair in guide_contact.values() for v in pair) > 1e-6
    )
    if not result["passes"]:
        raise ValueError("Check mechanical results")
    (d.EXPORT / "mechanical-fit.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
