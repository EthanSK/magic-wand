"""Checks specific to the edge click; all dimensions are in millimetres."""

import math

import manifold3d as mf


def clip_shoulder_checks(h, carrier, previous):
    """Measure the original spring's actual arc, separate from nearby braces."""
    from shoulder48 import shoulder

    clip = h.d.r22
    start, end = clip.P['carrier_rings']['mid_band_y_mm']
    rod = clip.h20.ROD
    spring = clip.h20.clip_ring(start, end, rod['clip_gap_degrees'],
                                rod['clip_root_wall'], clip.K['ring_bore_mm'] / 2.)
    original = spring ^ previous
    retained = carrier ^ (spring + shoulder(h))
    missing = original - carrier
    clearance_window = h.box(2.65, 4.6, start, end, 3., 4.8)
    sectors = []
    for angle in range(0, 85, 5):
        left, right = map(math.radians, (angle, angle + 5))

        def sector_volume(shape):
            return shape.trim_by_plane((math.cos(left), 0., -math.sin(left)), 0.).trim_by_plane(
                (-math.cos(right), 0., math.sin(right)), 0.).volume()

        sectors.append({'arc_start_deg': angle, 'original_mm3': round(sector_volume(original), 4),
                        'reinforced_mm3': round(sector_volume(retained), 4)})
    return {
        'missing_original_material_mm3': round(missing.volume(), 4),
        'missing_outside_connector_window_mm3': round((missing - clearance_window).volume(), 5),
        'connected_arc_pieces_above_0.001mm3': sum(s.volume() > .001 for s in retained.decompose()),
        'upper_right_arc_sectors': sectors,
    }


def check(h, cap, result, carrier, previous):
    q, r = h.q, h.r
    # Test each actual horizontal web section for a connected path between
    # the contact and both side rails. Eroding it first excludes a paper-thin
    # or point contact that would otherwise count as continuity.
    paths = []
    probe_y = q.PUSH_Y + .45
    for z in (18.70, 18.85, 19.00):
        section = cap.slice(z).offset(-.25, mf.JoinType.Round)
        hits = []
        for piece in section.decompose():
            hit = []
            for x in (q.PLUNGER_XY[0], -9.05, 9.05):
                witness = mf.CrossSection.circle(.18, 24).translate((x, probe_y))
                hit.append((piece ^ witness).area() > .06)
            hits.append(hit)
        paths.append({'z_mm': z, 'contact_connected_to_both_rails': any(all(row) for row in hits)})
    # A component may overlap the nominal rod outside a snap ring only if the
    # original design intentionally used interference. Electronics need air.
    rod = h.base.rod()
    clear = {name: round(float(q.hardware()[name].min_gap(rod, 10.)), 4)
             for name in ('plug', 'sockets', 'terminals', 'op1_wire')}
    edge = r.AXIS_Y - h.BOARD_FRONT
    lever = r.AXIS_Y - q.PUSH_Y
    old = edge - 6.5
    plunger = q.hardware()['plunger']
    actual_plunger = plunger.bounding_box()
    centre_y = .5 * (actual_plunger[1] + actual_plunger[4])
    inset = centre_y - (h.BOARD_FRONT + r.CLICK_SHIFT)
    # Check bottom face centre as well as the centre of the actual switch.
    face = q.pusher().slice(q.PUSH_Z + .001)
    contact_faces = face.decompose()
    travel = result['r47']['checks']['press_contacts_through_stroke']
    shoulder = clip_shoulder_checks(h, carrier, previous)
    return {
        'plunger_inset_from_free_edge_mm': round(inset, 4),
        'hinge_to_plunger_mm': round(lever, 4),
        'hinge_to_free_edge_mm': round(edge, 4),
        'op1_board_yaw_deg': q.OP1_YAW,
        'board_screw_hole_centres_world_xy_mm': [list(q.board_point(0., y)) for y in h.h32.EYELETS],
        'web_path_after_0.25mm_edge_erosion': paths,
        'electronics_to_rod_mm': clear,
        'forward_clip_shoulder': shoulder,
        'nominal_finger_force_ratio_to_r47_at_free_edge': round(lever / old, 4),
        'nominal_finger_travel_ratio_to_r47_at_free_edge': round(old / lever, 4),
        'gates': {
            'switch_centred_at_requested_free_edge': abs(inset - h.PUSH_FROM_FRONT) < .01,
            'free_edge_within_two_mm': 0 < inset <= 2.,
            'contact_face_is_single_patch': len(contact_faces) == 1 and face.area() >= .56,
            'contact_load_path_to_both_fitted_rails': all(row['contact_connected_to_both_rails'] for row in paths),
            'electronics_clear_the_rod': min(clear.values()) > .20,
            'rod_clip_shoulders_and_tips_continuous': shoulder['connected_arc_pieces_above_0.001mm3'] == 1
                and shoulder['missing_outside_connector_window_mm3'] < .02,
            'connector_shoulder_supported_across_arc': all(
                s['reinforced_mm3'] + .02 >= s['original_mm3'] for s in shoulder['upper_right_arc_sectors']),
            'bracket_contacts_no_other_switch_parts_through_motion': len(travel) >= 29 and all(
                row['bracket_to_other_op1_parts_mm3'] < .0002 for row in travel),
        },
        'physical_fit_verified': False,
    }
