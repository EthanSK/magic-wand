"""Measure the R71 post/clip stack in deposited beads, not just its CAD.

R70's enclosing-circle method is reused over the complete measured rigid lift.
The spring feet, three head ledges and complete stepped roots are measured
independently in matching assembly coordinates. These nominal bead envelopes do not predict force, sag or creep.
— GPT-6.1 Sol
"""
import argparse
import json
from pathlib import Path

import numpy as np
from shapely import set_precision
from shapely.geometry import box, LineString

import audit71 as a
import sections70 as previous


def local_beads(points, frame, x, y):
    """Keep a small complete neighbourhood before transforming, avoiding a copy
    of the entire plate for each fitting. Each row is X,Y,Zlow,Zhigh,radius."""
    assert abs(frame[2, 2]) > .999, 'These fittings must print with their post axis vertical'
    corners = np.array([[x + dx, y + dy, a.b.BOARD_TOP, 1]
                        for dx in (-3., 3.) for dy in (-6., 4.)]) @ frame.T
    lo, hi = corners[:, :2].min(axis=0) - .5, corners[:, :2].max(axis=0) + .5
    chosen = points[np.all(points[:, :2] >= lo, axis=1) & np.all(points[:, :2] <= hi, axis=1)]
    inv = np.linalg.inv(frame)
    local = chosen[:, :3] @ inv[:3, :3].T + inv[:3, 3]
    other = local[:, 2] - inv[2, 2] * chosen[:, 4]
    return np.column_stack((local[:, :2], np.minimum(local[:, 2], other),
                            np.maximum(local[:, 2], other), chosen[:, 3] / 2))


def at_xy(beads, x, y, floor):
    inside = ((beads[:, 0] - x) ** 2 + (beads[:, 1] - y) ** 2 < beads[:, 4] ** 2)
    chosen = beads[inside & (beads[:, 3] > floor)]
    if not len(chosen):
        return None
    return float(chosen[:, 2].min()), float(chosen[:, 3].max())


def stack(points, frames, side):
    h, b = a.h, a.b
    x, y = (-1 if side == 'Left' else 1) * b.HOLE_X, b.HOLE_Y
    bar_frame = np.asarray(frames['DFR_Post_Bar']['assembly_to_machine'])
    clip_frame = np.asarray(frames['DFR_Clip_' + side]['assembly_to_machine'])
    bar = local_beads(points, bar_frame, x, y)
    clip = local_beads(points, clip_frame, x, y)

    # The free exported frame is raised against the head, with the spring feet
    # below the board. Establish its actual deposited stop from all three ledges.
    contacts = {}
    windows = {'left_wing': (np.arange(-1.14, -.99, .025), np.arange(-.15, .151, .05)),
               'right_wing': (np.arange(1.01, 1.15, .025), np.arange(-.15, .151, .05)),
               'rear_ledge': (np.arange(-.50, .501, .05), np.arange(-1.08, -.959, .02))}
    rail_bottoms = []
    for name, (xs, ys) in windows.items():
        gaps = []
        for dx in xs:
            for dy in ys:
                head = at_xy(bar, x + dx, y + dy, b.BOARD_TOP + h.NECK - .25)
                rail = at_xy(clip, x + dx, y + dy, b.BOARD_TOP - .10)
                if head and rail:
                    gaps.append(head[0] - rail[1])
                    rail_bottoms.append(rail[0])
        assert len(gaps) >= 12, (side, 'No useful native head/rail witness', name, len(gaps))
        contacts[name] = dict(witnesses=len(gaps), least_gap_mm=round(min(gaps), 4), largest_gap_mm=round(max(gaps), 4))
    shift = min(row['least_gap_mm'] for row in contacts.values())
    assert -.20 < shift < .25, (side, 'Head/frame seating exceeds one layer allowance', contacts)
    stop = min(rail_bottoms) + shift - b.BOARD_TOP
    assert .03 < stop < .45, (side, 'Rigid frame jams or permits excessive board lift', stop)

    # Each foot stands below the frame. Its realised underside, after the frame
    # seats against the head, must interfere with the board so its arm bends.
    feet, roots = {}, {}
    for sign in (-1, 1):
        witnesses = []
        mid_x = sign * sum(h.ARM_X) / 2
        mid_y = sum(h.FOOT_Y) / 2
        for dx in np.arange(mid_x - .15, mid_x + .151, .05):
            for dy in np.arange(mid_y - .10, mid_y + .101, .05):
                foot = at_xy(clip, x + dx, y + dy, b.BOARD_TOP - h.FOOT - .30)
                if foot:
                    witnesses.append(b.BOARD_TOP - (foot[0] + shift))
        assert len(witnesses) >= 12, (side, 'No useful native spring foot witness', sign, len(witnesses))
        required = max(witnesses)
        assert .03 < min(witnesses) <= required < h.FOOT + .11, (side, 'Native foot preload absent or excessive', witnesses)
        feet[str(sign)] = dict(witnesses=len(witnesses), least_free_intrusion_mm=round(min(witnesses), 4),
                               required_arm_tip_deflection_mm=round(required, 4))

        # A foot contact alone cannot prove an attached arm. Follow the full
        # flared plan and local root thickness, including each added root layer;
        # the old fixed 0.8 mm-wide box covered only the centre of this new root.
        top = b.BOARD_TOP + h.LIFT + h.CLIP_T
        arm_plan = h.clip_plans(side)[1]
        rows = []
        for offset in (.08, .25, .40):
            local_y = -h.ARM_ROOT + offset
            thickness = h.arm_thickness(local_y)
            bottom = top - thickness
            strip = h.mf.CrossSection.square((10., .002)).translate((0. if sign > 0 else -10., local_y - .001))
            planned = arm_plan ^ strip
            assert planned.area() > .0001, (side, sign, 'No source root at station', local_y)
            low_x, _, high_x, _ = planned.bounds()
            nominal_width = planned.area() / .002
            bounds = (x + low_x - .06, bottom, x + high_x + .06, top)
            station = y + local_y
            section = previous.section_y(points, clip_frame, station, bounds).intersection(box(*bounds))
            # Native float32 layer slabs can meet 1.5e-8 mm apart after the
            # inverse transform. Snap only at one millionth of a millimetre;
            # never inflate bead widths to turn a real gap into a joint.
            raw_area = section.area
            section = set_precision(section, .000001)
            assert abs(section.area - raw_area) < .00001, (side, sign, 'Unexpected precision change')
            widths = [section.intersection(LineString([(bounds[0], z), (bounds[2], z)])).length
                      for z in np.arange(bottom + .10, top, .20)]
            assert len(widths) == round(thickness / .20), (side, sign, widths)
            assert section.area > .75 * nominal_width * thickness and min(widths) > .75 * nominal_width, (side, sign, station, section.area, widths)
            pieces = list(getattr(section, 'geoms', [section]))
            assert len(pieces) == 1, (side, sign, 'Disconnected spring root', len(pieces))
            rows.append(dict(y_mm=round(station, 4), source_width_mm=round(nominal_width, 4), source_thickness_mm=round(thickness, 4), area_mm2=round(section.area, 4), layer_widths_mm=[round(w, 4) for w in widths]))
        roots[str(sign)] = rows

    # Check the complete possible board rise, not only the seated post layer.
    lift = stop + .05
    ends = np.unique(bar[:, 2:4])
    candidates = [b.SEAT_Z + .001, b.SEAT_Z + lift]
    for boundary in ends[(ends > b.SEAT_Z) & (ends < b.SEAT_Z + lift)]:
        candidates.extend((float(boundary) - .001, float(boundary) + .001))
    planes = sorted(set(z for z in candidates if b.SEAT_Z < z <= b.SEAT_Z + lift))
    profile = previous.post_sections(points, bar_frame, x, planes=planes)
    minimum = min(row['smallest_enclosing_diameter_mm'] for row in profile)
    # This tests positive interference against the documented nominal 3 mm
    # hole, not equality with R70's first bead. Native variable-width paths made
    # the next R71 layer 3.0274 mm rather than the CAD prediction of 3.049 mm.
    # Neither value establishes friction against an unmeasured real hole.
    assert 3.0 < minimum < 3.30, (side, 'Nominal 3 mm interference lost within allowed lift', profile)
    rib_profile = previous.post_sections(points, bar_frame, x,
                                         planes=tuple(b.SEAT_Z + v for v in (.10, .30, .50)))
    assert all(row['smallest_enclosing_diameter_mm'] > 3.0 for row in rib_profile), rib_profile
    return dict(native_head_contacts=contacts, native_frame_seating_translation_mm=round(shift, 4),
                rigid_board_lift_to_frame_mm=round(stop, 4), checked_board_lift_mm=round(lift, 4),
                spring_feet=feet, spring_root_sections=roots, post_sections=profile,
                full_rib_layer_sections=rib_profile,
                minimum_enclosing_diameter_through_checked_lift_mm=minimum,
                nominal_hole_mm=3.0, actual_hole_tolerance_and_friction_unmeasured=True)


def run(folder):
    points, _ = a.v.read_native(folder / a.v.ARCHIVE)
    frame = a.v.read(folder / 'layout.frame.json')
    rows = {side: stack(points, frame['parts'], side) for side in ('Left', 'Right')}
    report = dict(revision='R71', archive_sha256=a.v.digest(folder / a.v.ARCHIVE),
                  frame_sha256=a.v.digest(folder / 'layout.frame.json'), checker_sha256=a.v.digest(__file__),
                  parts=rows, passes=True, physical_fit_force_and_creep_verified=False,
                  method='Complete native layer slabs and nominal circular bead footprints in matching assembly coordinates; sampled head/frame and foot/board contacts, then complete post-layer intervals through the conservative rigid-lift range.')
    a.v.write(folder / 'native-retention.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    report = run(args.folder)
    print(json.dumps({side: {key: row[key] for key in (
        'rigid_board_lift_to_frame_mm', 'spring_feet',
        'minimum_enclosing_diameter_through_checked_lift_mm')} for side, row in report['parts'].items()}))
