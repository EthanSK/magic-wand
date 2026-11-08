#!/usr/bin/env python3
"""Check the exact exported R16 meshes against the bought interfaces, routes, springs and stack.

Geometric screening only: no claim of physical fit, friction, strength, comfort or fatigue.
"""
import json
import math
from itertools import product
import numpy as np
import trimesh
import manifold3d as mf
import holder16 as h
import spaces16

OUT = h.HERE / 'exports'


def overlap(a, b):
    return max(0., float((a ^ b).volume()))


def read(name):
    m = trimesh.load_mesh(OUT / (name + '-assembly.stl'))
    return mf.Manifold(mf.Mesh(np.asarray(m.vertices, dtype=np.float32), np.asarray(m.faces, dtype=np.uint32)))


def section_thickness(solid, centre, direction):
    """Material interval through `centre` along `direction` (both endpoints outside)."""
    c = np.array(centre, dtype=float); d = np.array(direction, dtype=float); d /= np.linalg.norm(d)
    hits = sorted(solid.ray_cast(c - d * 60, c + d * 60), key=lambda q: q.distance)
    for a, b in zip(hits[::2], hits[1::2]):
        if a.distance < .5 < b.distance:  # ray_cast distance is the segment parameter 0..1
            return float(np.linalg.norm(np.array(b.position) - np.array(a.position)))
    raise AssertionError(('Probe is not in material', centre, direction))


def polygon_distance(a, b):
    """Minimum distance between two closed polygons (every vertex of one to every edge of the other)."""
    a = np.asarray(a, float); b = np.asarray(b, float)

    def points_to_edges(p, s):
        s0 = s; s1 = np.roll(s, -1, axis=0); d = s1 - s0; length2 = np.maximum((d ** 2).sum(1), 1e-12)
        t = np.clip(((p[:, None, :] - s0[None]) * d[None]).sum(2) / length2[None], 0, 1)
        proj = s0[None] + t[..., None] * d[None]
        return float(np.sqrt(((p[:, None, :] - proj) ** 2).sum(2)).min())
    return min(points_to_edges(a, b), points_to_edges(b, a))


def contains(poly, pt):
    x, y = pt; inside = False; n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]; x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0): inside = not inside
    return inside


def window_ligaments(keys):
    """Actual plan distance from every key's lightening window to each of its backplate holes,
    measured on the final carrier section through the middle of the thinned backplate."""
    z = h.PCB_Z - .6
    polys = [np.array(p, float) for p in keys.slice(z).to_polygons()]

    def signed_area(p):
        return .5 * float(np.dot(p[:, 0], np.roll(p[:, 1], -1)) - np.dot(p[:, 1], np.roll(p[:, 0], -1)))
    holes = [p for p in polys if signed_area(p) < 0]

    def containing(pt):
        hits = [p for p in holes if contains(p, pt)]
        assert len(hits) == 1, ('Expected exactly one hole around', pt, len(hits)); return hits[0]
    result = {}
    for i, ((kx, ky), rot) in enumerate(zip(h.key_positions(), h.key_rotations())):
        outline = np.array(h.window_outline(rot), float) + (kx, ky)
        window = containing(tuple(outline.mean(0)))
        dists = {}
        for hx, hy, r in h.backplate_hole_centres(rot):
            dists[f'hole_at_{hx:+.2f}_{hy:+.2f}_r{r:.2f}'] = round(polygon_distance(window, containing((kx + hx, ky + hy))), 4)
        result[f'key_{i}'] = {'rotation_degrees': rot, 'window_to_hole_mm': dists, 'minimum_mm': min(dists.values()),
                              'window_area_mm2': round(abs(signed_area(window)), 3)}
    return result


def check():
    manifest = json.loads((OUT / 'manifest.json').read_text())
    for path, digest in manifest['source_sha256'].items():
        assert h.sha(h.HERE / path) == digest, ('Stale source', path)
    solids = {name: read(name) for name in manifest['parts']}
    for name, record in manifest['parts'].items():
        assert record['stl_sha256'] == h.sha(OUT / (name + '-SOURCE-REQUIRES-PREPARATION.stl')), name
    report = {'manifest_sha256': h.sha(OUT / 'manifest.json'), 'checker_sha256': h.sha(h.HERE / 'verify16.py'),
              'parts': {}, 'physical_fit_verified': False, 'physical_strength_verified': False, 'physical_comfort_verified': False}

    # 1. Every working space is empty of final material, for every part.
    spaces = {}
    for name, solid in solids.items():
        rows = {}
        for label, region in spaces16.regions(name).items():
            if isinstance(region, spaces16.Swept):
                worst = 0.
                for pose in region.poses():
                    worst = max(worst, overlap(solid, pose))
                rows[label] = {'poses': len(region), 'worst_pose_intersection_mm3': worst}
                assert worst < .002, (name, label, worst)
            else:
                v = overlap(solid, region); rows[label] = {'intersection_mm3': v}
                assert v < .002, (name, label, v)
        spaces[name] = rows
    report['working_spaces'] = spaces

    # 2. Key carrier: bought parts, caps, nose, rings.
    keys = solids['Key_Carrier']; refs = h.references(); c = h.P['cap_clearance_screen']; k = h.P['keys']
    envelopes = []; gaps = {}
    for i in range(5):
        bb = refs[f'key_{i}_cap'].bounding_box(); m = c['lateral_allowance_per_cap_side_mm']
        assert abs(bb[3] - bb[0] - c['reference_width_mm']) < 1e-5 and abs(bb[4] - bb[1] - c['reference_length_mm']) < 1e-5
        envelopes.append((bb[0] - m, bb[1] - m, bb[2] - c['stroke_mm'], bb[3] + m, bb[4] + m, bb[5]))
    for i in range(5):
        for j in range(i + 1, 5):
            a, b = envelopes[i], envelopes[j]
            gaps[f'{i}_{j}'] = float(np.linalg.norm([max(a[d] - b[d + 3], b[d] - a[d + 3], 0) for d in range(3)]))
    assert min(gaps.values()) >= c['minimum_residual_gap_mm'] - 1e-5, gaps
    assert c['reference_width_mm'] > c['reference_length_mm'] and c['purchased_cap_dimensions_verified'] is False
    # Flange lands: the plate top must exist under all four flange corners of every key.
    lands = {}
    top = h.plate_top()
    for i, (cx, cy) in enumerate(h.key_positions()):
        for x, y in product([-7.15, 7.15], repeat=2):
            probe = h.box(cx + x - .08, cx + x + .08, cy + y - .08, cy + y + .08, top - .2, top)
            lands[f'{i}:{x},{y}'] = float((probe - keys).volume())
    assert max(lands.values()) < 1e-4, lands
    # Backplate under every switch housing edge midpoint (the housing rests on it).
    seats = {}
    for i, ((cx, cy), rot) in enumerate(zip(h.key_positions(), h.key_rotations())):
        for x, y in [(-6.3, -6.3), (6.3, -6.3), (6.3, 6.3), (-2.5, 6.3), (0, -6.4)]:
            # Housing-footprint probes between the standard holes and the lightening window.
            probe = h.box(x - .1, x + .1, y - .1, y + .1, h.PCB_Z - .3, h.PCB_Z - .005).rotate((0, 0, rot)).translate((cx, cy, 0))
            seats[f'{i}:{x},{y}'] = float((probe - keys).volume())
    assert max(seats.values()) < 1e-4, seats
    # Nose: nothing ahead of the front plane; rounded corners absent; flat plate top reaches the flange edge.
    s = h.P['slab']; front = s['front_y_mm']
    ahead = overlap(keys, h.box(-60, 60, -60, front - .001, -60, 60)); assert ahead < .002, ahead
    r_f = s['nose_finger_radius_mm']; under = h.slab_bottom() + h.P['bay']['backplate_thickness_mm'] - h.P['bay']['backplate_thin_mm']
    # The corner square of side r(1-cos45) lies wholly outside the tangent round.
    corner_probe = h.box(-20, 20, front, front + r_f * .28, under, under + r_f * .28)
    assert overlap(keys, corner_probe) < .002, 'Finger corner not rounded'
    top_probe = h.box(-20, 20, front, front + s['nose_top_radius_mm'] * .28, top - s['nose_top_radius_mm'] * .28, top)
    assert overlap(keys, top_probe) < .002, 'Top front corner not rounded'
    cap_front = min(refs[f'key_{i}_cap'].bounding_box()[1] for i, (x, y) in enumerate(h.key_positions()) if not y)
    # Rings: spring arms free, gaps open, bore lips present, saddle coverage.
    rings = {}
    cr = h.P['carrier_rings']; width = cr['ring_width_mm']
    for label, (y0, y1), skirted in [('mid', cr['mid_band_y_mm'], True), ('rear', cr['rear_band_y_mm'], False)]:
        yc = (y0 + y1) / 2
        band = h.ring(yc, None, width)
        lower = h.box(-8, 8, y0 - .01, y1 + .01, -8, -.05)
        extra = overlap((keys - band) ^ lower, h.tube_y(3.94, 7.0, y0, y1))
        missing = max(0., ((band ^ h.tube_y(4.25, 5.35, yc - .4, yc + .4)) - keys).volume())
        gap = overlap(keys, h.gap_cut(y0, y1))
        assert extra < .002 and missing < .005 and gap < .002, (label, extra, missing, gap)
        rings[label] = {'lower_arm_extra_material_mm3': extra, 'missing_band_mm3': missing, 'gap_intersection_mm3': gap, 'skirted': skirted}
    # Window-to-hole ligaments of every key, measured on the final section (the turned key included).
    ligaments = window_ligaments(keys)
    assert min(v['minimum_mm'] for v in ligaments.values()) >= 1.2, ligaments
    # Clearance from the lower-middle socket (nominal and maximum envelope) down to the rod surface.
    rod_top = h.ROD['diameter'] / 2; socket_bottom = float(refs['key_1_socket'].bounding_box()[2])
    socket_rod = {'nominal_socket_above_rod_surface_mm': round(socket_bottom - rod_top, 3),
                  'nominal_socket_above_rigid_corridor_mm': round(socket_bottom - h.CORRIDOR, 3),
                  'maximum_socket_above_rod_surface_mm': round(float(spaces16.regions('Key_Carrier')['key_1_maximum_socket'].bounding_box()[2]) - rod_top, 3),
                  'rod_diameter_mm': h.ROD['diameter'], 'rigid_corridor_diameter_mm': 2 * h.CORRIDOR,
                  'note': 'Lower-middle key socket underside above the rod; the switch pins are not structural, support the socket from below while pressing the switch in.'}
    report['parts']['Key_Carrier'] = {'cap_envelope_gaps_mm': gaps, 'minimum_cap_gap_mm': min(gaps.values()), 'flange_land_missing_mm3': lands,
                                      'housing_seat_missing_mm3': seats, 'material_ahead_of_front_mm3': ahead, 'front_y_mm': front,
                                      'lower_reference_cap_front_y_mm': cap_front, 'rings': rings,
                                      'key_rotations_degrees': h.key_rotations(), 'socket_insertion_route_mm': h.P['bay']['socket_insertion_route_mm'],
                                      'window_ligaments': ligaments, 'minimum_window_ligament_mm': min(v['minimum_mm'] for v in ligaments.values()),
                                      'socket_to_rod_clearance': socket_rod}

    # 3. Battery: cell envelope, reserve, loading, gate.
    battery = solids['Battery_Holder']; gate_relaxed = solids['Battery_End_Gate']; gate_fitted = h.battery_gate(True)
    cell = h.cell_shape(); reserve = h.cell_shape(True); lv = h.cage_levels()
    cell_in_reserve = max(0., (cell - reserve).volume()); assert cell_in_reserve < 1e-6
    loading = max(overlap(battery, cell.translate((0, dy, 0))) for dy in np.linspace(-50, 0, 101)); assert loading < .002, loading
    relaxed = overlap(battery, gate_relaxed); assert .005 < relaxed < 2, relaxed
    fitted_route = max(overlap(battery, gate_fitted.translate((0, 0, dz))) for dz in np.linspace(0, 15, 61)); assert fitted_route < .002
    far_stop = overlap(battery, cell.translate((0, 3, 0))); assert far_stop > 1, far_stop
    gate_stop = overlap(gate_fitted, cell.translate((0, -3, 0))); assert gate_stop > 1, gate_stop
    gate_touch = overlap(gate_fitted, cell); assert gate_touch < 1e-6, gate_touch
    play = {'width_total_mm': lv['half_w'] * 2 - h.P['cell']['manufacturer_max_mm']['width'],
            'length_total_mm': lv['half_l'] * 2 - h.P['cell']['manufacturer_max_mm']['length'],
            'thickness_total_mm': (lv['roof_bottom'] - lv['floor_top']) - h.P['cell']['manufacturer_max_mm']['thickness']}
    # Floor support under the cell: at least 25% of the cell footprint has floor plastic directly below.
    floor_section = battery.slice(lv['floor_top'] - .2) ^ mf.CrossSection.square((cell.bounding_box()[3] - cell.bounding_box()[0], cell.bounding_box()[4] - cell.bounding_box()[1])).translate((cell.bounding_box()[0], cell.bounding_box()[1]))
    footprint = (cell.bounding_box()[3] - cell.bounding_box()[0]) * (cell.bounding_box()[4] - cell.bounding_box()[1])
    floor_fraction = floor_section.area() / footprint; assert floor_fraction > .25, floor_fraction
    roof_section = battery.slice(lv['roof_bottom'] + .2) ^ mf.CrossSection.square((21.2, 26)).translate((-10.6, -13))
    roof_fraction = roof_section.area() / (21.2 * 26)
    lead_exit = overlap(battery, spaces16.regions('Battery_Holder')['lead_exit'])
    cage_rings = {}
    for label, (y0, y1) in [('near', h.P['cage']['near_band_y_mm']), ('far', h.P['cage']['far_band_y_mm'])]:
        yc = (y0 + y1) / 2; band = h.ring(yc, None, h.ROD['ring_width'])
        extra = overlap((battery - band) ^ h.box(-8, 8, y0 - .01, y1 + .01, -8, -.05), h.tube_y(3.94, 7.0, y0, y1))
        missing = max(0., ((band ^ h.tube_y(4.25, 5.35, yc - .4, yc + .4)) - battery).volume())
        assert extra < .002 and missing < .005, (label, extra, missing)
        cage_rings[label] = {'lower_arm_extra_material_mm3': extra, 'missing_band_mm3': missing}
    report['parts']['Battery_Holder'] = {'cell_outside_reserve_mm3': cell_in_reserve, 'cell_loading_route_intersection_mm3': loading,
                                         'gate_relaxed_wedge_interference_mm3': relaxed, 'gate_fitted_removal_route_mm3': fitted_route,
                                         'cell_stopped_at_closed_end_mm3': far_stop, 'cell_stopped_by_gate_stubs_mm3': gate_stop,
                                         'gate_touching_seated_cell_mm3': gate_touch, 'nominal_play_mm': play,
                                         'floor_plastic_fraction_under_cell': floor_fraction, 'roof_plastic_fraction_over_cell': roof_fraction,
                                         'lead_exit_intersection_mm3': lead_exit, 'rings': cage_rings,
                                         'note': 'Play is against the manufacturer maximum envelope; the real cell, printed shrinkage and lead bumps are unmeasured.'}

    # 4. XIAO holder: the official rounded board outline through its whole lateral and axial play
    #    against the final mesh: free travel, cradle contact at every corner, stop engagement,
    #    pad/solder and USB access, struts, rings.
    sensor = solids['XIAO_Rod_Holder']; sn = h.P['sensor']; bz = h.SENSOR['board_z']; bt = h.SENSOR['board_thickness']
    clear = {n: overlap(sensor, refs[n]) for n in ['pcb', 'usb', 'wire', 'usb_plug_body', 'pad_access_top']}; assert max(clear.values()) < .002, clear
    analytic = h.board_travel()

    # Poses 5 um inside the rail faces: the float32 mesh faces would otherwise register a coplanar sliver.
    EPS = .005

    def free_travel(dx, sign):
        lo, hi = 0., 2.0
        for _ in range(16):
            mid = (lo + hi) / 2
            if overlap(sensor, h.board_outline(dx, sign * mid)) > 1e-4: hi = mid
            else: lo = mid
        return lo
    travel = {}
    for dx in np.linspace(-analytic['lateral'] + EPS, analytic['lateral'] - EPS, 5):
        near = free_travel(float(dx), -1); far = free_travel(float(dx), +1); a = h.board_travel(float(dx))
        assert abs(near - a['near']) < .03 and abs(far - a['far']) < .03, (dx, near, far, a)
        travel[f'dx_{dx:+.3f}'] = {'near_mm': round(near, 4), 'far_mm': round(far, 4), 'analytic_near_mm': round(a['near'], 4), 'analytic_far_mm': round(a['far'], 4)}
    assert overlap(sensor, h.board_outline(analytic['lateral'] + .05, 0)) > 1e-3 and overlap(sensor, h.board_outline(analytic['lateral'] - .02, 0)) < 1e-4
    # Cradle contact: holder material in the 0.05 mm directly under the board, per corner, at 25 poses
    # spanning the full reachable play (rails and stops touched at the extremes).
    mid_y = sn['board_near_end_y_mm'] + sn['board_outline_mm']['length'] / 2
    corners = {}
    for sx in (1, -1):
        for end in ('near', 'far'):
            y_lo, y_hi = (-3., mid_y) if end == 'near' else (mid_y, 30.)
            corners[f'{"+" if sx > 0 else "-"}x_{end}'] = h.box(min(sx * 5.5, sx * 12.5), max(sx * 5.5, sx * 12.5), y_lo, y_hi, bz - .06, bz + .01)
    contact = {k: {'minimum_area_mm2': 99., 'minimum_y_extent_mm': 99., 'worst_pose_dx_dy_mm': None, 'nominal_area_mm2': None} for k in corners}
    for dx, dy in [(0., 0.)] + h.board_travel_poses(margin=EPS, n_lateral=5, n_axial=5):
        touch = h.board_outline(dx, dy, thickness=.05, z0=bz - .05) ^ sensor
        for k, cb in corners.items():
            part = touch ^ cb; area = float(part.volume()) / .05
            extent = float(part.bounding_box()[4] - part.bounding_box()[1]) if area > 1e-6 else 0.
            if abs(dx) < 1e-9 and abs(dy) < 1e-9: contact[k]['nominal_area_mm2'] = round(area, 4)
            if area < contact[k]['minimum_area_mm2']:
                contact[k].update(minimum_area_mm2=round(area, 4), minimum_y_extent_mm=round(extent, 4), worst_pose_dx_dy_mm=[round(dx, 3), round(dy, 3)])
    assert all(c['minimum_area_mm2'] >= .3 and c['minimum_y_extent_mm'] >= .4 for c in contact.values()), contact
    # Stops: pushed 0.2 mm past its free travel the board must meet printed material above the board
    # plane (a stop face), at both ends, for the centred board and the board hard against either rail.
    above = sensor ^ h.box(-12, 12, -6, 24, bz - .001, bz + 3)
    stops = {}
    for dx in (-analytic['lateral'] + EPS, 0., analytic['lateral'] - EPS):
        t = h.board_travel(dx); row = {}
        pushed = h.board_outline(dx, -(t['near'] + .2)); pulled = h.board_outline(dx, t['far'] + .2)
        for sx in (1, -1):
            side = h.box(min(sx * 5, sx * 12), max(sx * 5, sx * 12), -6, 30, bz - .01, bz + 3)
            row[f'near_{"+" if sx > 0 else "-"}x_mm3'] = round(overlap(above ^ side, pushed), 4)
            row[f'far_{"+" if sx > 0 else "-"}x_mm3'] = round(overlap(above ^ side, pulled), 4)
        # A laterally offset board meets one face of each pair first (the faces are 45-degree or
        # corner-arc contacts); the centred board must engage both faces of both pairs.
        assert row['near_+x_mm3'] + row['near_-x_mm3'] > .05 and row['far_+x_mm3'] + row['far_-x_mm3'] > .05, row
        if abs(dx) < 1e-9: assert min(row.values()) > .05, row
        stops[f'dx_{dx:+.3f}'] = row
    # Report every assumed pad separately. Material a millimetre below a pad is not board contact.
    bo = sn['board_outline_mm']; first = mid_y - 3 * 2.54; pad_material = {}
    for sx in (1, -1):
        for k in range(7):
            yc = first + k * 2.54
            x0, x1 = sorted((sx * (bo['width'] / 2 - 1.8), sx * bo['width'] / 2))
            below = sensor ^ h.box(x0, x1, yc - .5, yc + .5, bz - 1., bz)
            near_plane = overlap(sensor, h.box(x0, x1, yc - .5, yc + .5, bz - .05, bz))
            volume = float(below.volume())
            pad_material[f'{sx:+d}_pad_{k}'] = {
                'material_within_1mm_below_board_mm3': round(volume, 5),
                'material_within_0p05mm_below_board_mm3': round(near_plane, 6),
                'mean_contact_region_area_over_top_0p05mm_mm2': round(near_plane / .05, 4),
                'highest_material_gap_below_board_mm': round(bz - float(below.bounding_box()[5]), 4) if volume > 1e-6 else None}
    # Intentional cradle contact is excluded from these underside-clearance regions.
    between = (sn['board_near_end_y_mm'] + sn['ledge_under_board_mm'][0] + sn['rail_x_mm'][0] - sn['cradle_inner_x_mm'] + .1,
               sn['board_near_end_y_mm'] + bo['length'] - sn['ledge_under_board_mm'][1] - .05)
    underside_clearance = {'assembly_y_range_mm': list(between)}
    for label, half_width in [('whole_board_width', bo['width'] / 2), ('centre_abs_x_le_4', 4.)]:
        material = sensor ^ h.box(-half_width, half_width, *between, bz - 6., bz)
        underside_clearance[label] = round(bz - float(material.bounding_box()[5]), 4)
    struts = {f'{sign:+d}': float((h.box(sign * 5.5 - .1, sign * 5.5 + .1, 10.0 - .1, 10.0 + .1, 6.4, 6.6) - sensor).volume()) for sign in (1, -1)}
    assert max(struts.values()) < 1e-4, struts
    sensor_rings = {}
    for label, (y0, y1) in [('near', h.P['sensor']['near_band_y_mm']), ('far', h.P['sensor']['far_band_y_mm'])]:
        yc = (y0 + y1) / 2; band = h.ring(yc, None, h.P['sensor']['clip_width_mm'], h.ROD['sensor_clip_root_wall'])
        extra = overlap((sensor - band) ^ h.box(-8, 8, y0 - .01, y1 + .01, -8, -.05), h.tube_y(3.94, 7.0, y0, y1))
        missing = max(0., ((band ^ h.tube_y(4.25, 5.3, yc - .4, yc + .4)) - sensor).volume())
        assert extra < .002 and missing < .005, (label, extra, missing)
        sensor_rings[label] = {'lower_arm_extra_material_mm3': extra, 'missing_band_mm3': missing}
    report['parts']['XIAO_Rod_Holder'] = {'board_outline_mm': sn['board_outline_mm'], 'board_nominal_y_mm': [sn['board_near_end_y_mm'], round(sn['board_near_end_y_mm'] + bo['length'], 3)],
                                          'board_usb_wire_intersection_mm3': clear, 'free_travel_mm': travel, 'lateral_play_to_rails_mm': round(analytic['lateral'], 4),
                                          'cradle_contact_under_board': contact, 'stop_engagement_0p2_past_travel_mm3': stops,
                                          'assumed_pad_material': pad_material,
                                          'material_within_1mm_below_all_assumed_pads_mm3': round(sum(p['material_within_1mm_below_board_mm3'] for p in pad_material.values()), 4),
                                          'pad_record_note': 'Per-pad material in two depth bands; the top 0.05 mm mean area describes near-plane CAD material, not printed contact or a measured solder footprint.',
                                          'underside_clearance_between_cradles_mm': underside_clearance,
                                          'castellation_assumption': sn['castellation_assumption'],
                                          'mid_strut_missing_mm3': struts, 'rings': sensor_rings, 'usb_direction': 'positive Y toward tip',
                                          'header_caveat': sn['header_caveat'],
                                          'note': 'Exact booleans of the official rounded outline against the final assembly mesh at 25 poses covering the full lateral and axial play. Contact areas are geometric, not a measured seat; printed-bead survival is in slice-clearances.json.'}

    # 5. Fitted-rod check: every ring's relaxed 7.9 bore exists and the rigid corridor is clear elsewhere.
    for name, solid in solids.items():
        if name == 'Battery_End_Gate': continue
        assert overlap(solid, h.cyl(h.ROD['clip_diameter'] / 2 - .001, -85, 85).rotate((-90, 0, 0))) < .002, name

    # 6. Assembled stack along one rod: carrier, battery (gate to tip), XIAO holder, 8 mm gaps.
    battery_y = h.battery_position(); xiao_y = h.xiao_position()
    bat_pose = battery.rotate((0, 0, 180)).translate((0, battery_y, 0)); xiao_pose = sensor.translate((0, xiao_y, 0))
    assert overlap(keys, bat_pose) < .002 and overlap(bat_pose, xiao_pose) < .002
    stack = {'carrier_y_mm': [float(keys.bounding_box()[1]), float(keys.bounding_box()[4])],
             'battery_module_y_mm': [float(bat_pose.bounding_box()[1]), float(bat_pose.bounding_box()[4])],
             'xiao_holder_y_mm': [float(xiao_pose.bounding_box()[1]), float(xiao_pose.bounding_box()[4])],
             'end_gaps_mm': h.P['assembly']['battery_end_clearance']}
    report['assembled_stack'] = stack

    # 7. Minimum sections of the fixed load paths (screening values only).
    sections = {}
    sections['carrier_saddle_neck_at_slab'] = section_thickness(keys, (0.013, 15.013, h.slab_bottom() + .23), (1, 0, 0))
    sections['carrier_inter_row_strip'] = section_thickness(keys, (-12.013, 8.913, h.PCB_Z + .5), (0, 1, 0))
    sections['carrier_outer_wall_lower_left'] = section_thickness(keys, (-27.0, 0.0, h.PCB_Z + .5), (1, 0, 0))
    sections['carrier_plate_lip'] = section_thickness(keys, (0, 7.4, h.PCB_Z + 1.6), (0, 0, 1))
    sections['carrier_backplate_thin'] = section_thickness(keys, (-18.7 - 6.0, -5.0, h.PCB_Z - .5), (0, 0, 1))
    sections['carrier_backplate_socket_pad'] = section_thickness(keys, (2.0, 5.0, h.PCB_Z - .5), (0, 0, 1))
    sections['xiao_rail'] = section_thickness(sensor, (10.2, 10.0, 8.6), (1, 0, 0))
    sections['xiao_keel'] = section_thickness(sensor, (0, 12.0, 5.2), (1, 0, 0))
    sections['xiao_far_bar'] = section_thickness(sensor, (6.0, 22.2, 6.65), (-.37, 0, 1.0))
    sections['battery_side_chord_bottom'] = section_thickness(battery, (11.4, 5.0, 5.0), (1, 0, 0))
    sections['battery_floor_spine'] = section_thickness(battery, (0, 5.0, 5.0), (1, 0, 0))
    sections['gate_wedge_neck'] = section_thickness(gate_relaxed, (12.2, -14.9, 9.5), (1, 0, 0))
    sections['gate_bar'] = section_thickness(gate_relaxed, (0, -14.9, 11.1), (0, 0, 1))
    report['minimum_sections_mm'] = {k: (round(v, 3) if v is not None else None) for k, v in sections.items()}
    assert sections['carrier_saddle_neck_at_slab'] >= 3.6 and sections['carrier_inter_row_strip'] >= 3.3 and sections['carrier_plate_lip'] >= 1.15
    assert sections['xiao_rail'] >= 1.95 and sections['xiao_keel'] >= 2.9 and sections['gate_wedge_neck'] >= 1.15
    report['passed'] = True
    (OUT / 'geometry-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS: working spaces, bought interfaces, cap envelopes, cell play, gate, board, rings and stack.')
    print(json.dumps({'cap_gap': min(gaps.values()), 'cell_play': play, 'floor_fraction': round(floor_fraction, 3), 'sections': report['minimum_sections_mm']}, indent=1))


if __name__ == '__main__':
    check()
