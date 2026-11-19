"""Combined horizontal board play and corner press against an illustrative rounded button."""
import json
import numpy as np
import build52 as d
import mechanical_checks51 as m


def main():
    old, q = d.old, d.q
    old.configure_new_op1()
    result = json.loads((d.EXPORT / "mechanical-fit.json").read_text())
    tilt = result["max_nominal_bearing_roll_deg"]
    P = old.baseline.b.load(d.EXPORT / "DFRobot_Hole_Bracket-assembly.stl")
    nub = P ^ d.dome()
    z = d.local_z(q.FREE_TOP)
    profile = [(-0.60, z - 0.85), (0.60, z - 0.85)]
    for a in np.linspace(0, np.pi, 33):
        profile.append((0.60 * np.cos(a), z - 0.60 + 0.60 * np.sin(a)))
    button = q.board_frame(
        d.mf.Manifold.hull_points(
            np.asarray([[x, y, h] for x in (-1.45, 1.45) for y, h in profile])
        )
    )
    case = q.hardware()["switch"]
    # The widest retained 4.5 mm photo estimate versus the 2.08 mm peg.
    # The still-present slot walls restrict some of these directions further.
    radius = (4.5 - 2.08) / 2
    C = old.baseline.b.load(d.EXPORT / "Key_Carrier-assembly.stl")
    hardware = q.hardware()
    board = q.op1_board(17.9, 4.5) + d.union(hardware[n] for n in ("sockets", "housing", "plug"))
    xmin, ymin, zmin, xmax, ymax, zmax = board.bounding_box()
    seats = C
    C ^= d.box(xmin - 1.3, xmax + 1.3, ymin - 1.3, ymax + 1.3, zmin - 0.1, zmax + 0.1)
    offsets = []
    limits = []
    for direction in np.linspace(0, 2 * np.pi, 16, endpoint=False):
        vx, vy = np.cos(direction), np.sin(direction)

        def hits(distance):
            return m.vol(C, board.translate((distance * vx, distance * vy, 0))) > 0.0001

        limit = m.onset(hits, (0.0, radius)) if hits(radius) else radius
        limits.append(limit)
        offsets.append((limit * vx, limit * vy, 0))
    samples = []
    feet,heels=d.stop_parts(seats,P)
    poses = []
    # Roll uses some axial clearance. At each roll angle sweep only the two
    # end positions still obtainable between the cheeks clamped on the sleeve.
    for roll in np.linspace(-tilt, tilt, 5):
        tilted = m.roll_at_hinge(old.world(d.thrust_faces(), 0), roll)
        xmin, _, _, xmax, _, _ = tilted.bounding_box()
        for dx in set(
            [round(-old.SLEEVE_LENGTH / 2 - xmin, 6), round(old.SLEEVE_LENGTH / 2 - xmax, 6)]
        ):
            poses.append((roll, dx))
    for roll, dx in poses:
        corner = "left" if roll > 0 else "right" if roll < 0 else "centre"
        ang = m.onset(
            lambda v: m.vol(feet, m.roll_at_hinge(old.world(heels, v), roll, dx)) > 1e-8,
            (-0.5, 0.90),
        )
        pad = m.roll_at_hinge(old.world(nub, ang), roll, dx)
        paddle = m.roll_at_hinge(old.world(P, ang), roll, dx)
        for off in offsets:
            target = button.translate(off)
            if m.vol(target, pad) < 1e-8:
                raise ValueError("Lost contact with offset rounded plunger")
            travel = m.onset(
                lambda dz: m.vol(target.translate((0, 0, -dz)), pad) < 1e-8, (0.0, 1.15)
            )
            samples.append(
                dict(
                    corner=corner,
                    roll_deg=roll,
                    axial_offset_mm=dx,
                    offset_world_xy_mm=list(off[:2]),
                    travel_mm=travel,
                    switch_case_intersection_mm3=m.vol(case.translate(off), paddle),
                )
            )
    worst = min(samples, key=lambda row: row["travel_mm"])
    high = max(samples, key=lambda row: row["travel_mm"])
    collision = max(row["switch_case_intersection_mm3"] for row in samples)
    receipt = dict(
        rounded_profile="Illustrative 0.6 mm radius, 2.9 × 1.2 mm envelope; exact bought crown unknown.",
        theoretical_eyelet_only_slack_radius_mm=radius,
        actual_slot_and_barrel_limits_mm=limits,
        largest_achievable_board_translation_in_test_mm=max(limits),
        angle_count=16,
        case_count=len(samples),
        least_travel=worst,
        most_travel=high,
        max_case_collision_mm3=collision,
        carrier_hash=m.file_hash(d.EXPORT / "Key_Carrier-assembly.stl"),
        paddle_hash=m.file_hash(d.EXPORT / "DFRobot_Hole_Bracket-assembly.stl"),
        passes=bool(0.48 < worst["travel_mm"] and high["travel_mm"] < 0.86 and collision < 0.001),
    )
    print(json.dumps(receipt, indent=2), flush=True)
    if not receipt["passes"]:
        raise ValueError("Combined misalignment check failed")
    (d.EXPORT / "contact-misalignment.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
