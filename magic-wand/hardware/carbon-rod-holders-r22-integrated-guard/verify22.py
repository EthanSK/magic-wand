#!/usr/bin/env python3
"""R22 geometry checks: runner roots and necks, every socket loading route with its stated solder allowance,
fingertip probes, row-spacing table, battery slot lead-in and door routes, XIAO under-board clearance, keeper
route, 12-wire clip packing and slit, and the exported meshes against the manifest.

Run through the repository geometry runner. Reads the exported meshes when they exist; every CAD-side number
is recomputed from holder22 so the two can be compared. Nothing here is a physical fit or strength result.
Usage: verify22.py [output.json]   (default exports/geometry-checks.json)
"""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import json, math
import numpy as np, trimesh, manifold3d as mf
import holder22 as h

OUT = h.HERE / 'exports'; base = h.base; G = h.G; C = h.C; THRESH = .005


def vol(a, b): return float((a ^ b).volume())


def thickness(section):
    """Twice the largest inward offset that leaves material: the narrowest real dimension, not a bounding box."""
    lo, hi = 0., 2.
    if section.area() <= 0: return 0.
    for _ in range(14):
        mid = (lo + hi) / 2
        if section.offset(-mid, h.ROUND, 2., 16).area() > 1e-6: lo = mid
        else: hi = mid
    return round(2 * lo, 3)


def runner_report():
    """Per runner: free (outside the holder) section area and thickness on every print layer, and its bond into the holder at both ends."""
    layers, stats = h.guard_layers(); cb = h.to_layer(h.carrier_base()); out = {}
    for b in G['beams']:
        rows = []
        for y0, y1, s in layers:
            yc = (y0 + y1) / 2; p = h.beam_path(b, yc)
            if p is None: continue
            x = p[0]; window = h.rect(x - 2.5, x + 2.5, -1, 12); piece = s ^ window; here = cb.slice(-yc) ^ window
            bond = (piece.offset(.12, h.ROUND, 2., 16) ^ here).area()
            rows.append({'y': round(yc, 2), 'area': round(piece.area(), 3), 'thick': thickness(piece), 'bond': round(bond, 3), 'z_bottom': round(p[2], 3)})
        # Leading/trailing layers where the runner is still wholly inside the holder have no separate section; drop them.
        nz = [j for j, r in enumerate(rows) if r['area'] > .05]; rows = rows[nz[0]:nz[-1] + 1] if nz else rows
        free = [r for r in rows if r['bond'] < 1e-3]; rear = [r for r in rows if r['bond'] > 1e-3 and r['y'] > 5]; front = [r for r in rows if r['bond'] > 1e-3 and r['y'] < 5]
        gaps = [r['y'] for r in rows if r['area'] < .05]
        out[b['name']] = {'layers': len(rows), 'free_layers': len(free), 'min_free_area_mm2': min(r['area'] for r in free) if free else None, 'min_free_thickness_mm': min(r['thick'] for r in free) if free else None,
                          'rear_root_bond_layers': len(rear), 'rear_root_bond_y_mm': [rear[-1]['y'], rear[0]['y']] if rear else None, 'front_root_bond_layers': len(front), 'front_root_bond_y_mm': [front[-1]['y'], front[0]['y']] if front else None,
                          'layers_with_no_runner_section_y_mm': gaps, 'lowest_z_mm': min(r['z_bottom'] for r in rows)}
    return out, stats


def route_report(carrier):
    """Every socket's loading route, carrying the maximum socket plus the stated terminal solder and wire allowance."""
    out = {}
    for i in range(5):
        solid = h.soldered_socket(i)
        poses = h.slide_poses(i) if i in G['slide_keys'] else h.dogleg_poses(i) if i in G['dogleg_keys'] else [tuple(p) for p in h.spaces16.socket_route_below()]
        straight = [vol(carrier, solid.translate(tuple(float(v) for v in p))) for p in h.spaces16.socket_route_below()]
        hits = [vol(carrier, solid.translate(tuple(float(v) for v in p))) for p in poses]
        row = {'route': 'sideways slide then lift' if i in G['slide_keys'] else 'up 1 mm away from the rod, in 2 mm below the seat, then up' if i in G['dogleg_keys'] else 'straight up from 6 mm below', 'poses': len(poses), 'max_overlap_mm3': round(max(hits), 4), 'poses_over_threshold': sum(v > THRESH for v in hits),
               'straight_up_with_solder_allowance_max_overlap_mm3': round(max(straight), 4)}
        if i in G['slide_keys']:
            # Vertical margin: how much lower the slide could run before the soldered socket meets the runners.
            lowered = [d for d in np.arange(0., 1.01, .05) if all(vol(carrier, solid.translate((float(p[0]), 0., float(p[2]) - d))) < THRESH for p in poses[::4])]
            row['extra_drop_allowed_mm'] = round(max(lowered), 2) if lowered else 0.
            row['lift_mm'] = G['slide_lift_mm']; row['entry_side'] = '+X (right edge)' if base.key_positions()[i][0] > 0 else '-X (left edge)'
        out[f'key_{i}'] = row
    log = h.spaces16.CARVE_LOG.get('carrier22:final', {})
    out['carve_log_final'] = {k: v for k, v in log.items()}
    out['carve_log_final_poses_meeting_material'] = sum(v['poses_meeting_material'] for v in log.values())
    return out


def interference_report(carrier):
    guard = h.guard(); refs = {**h.h20.bought_parts(), **h.h20.contact_envelopes(), 'rod_corridor_r4.2': h.cyl(4.2, -40, 100).rotate((-90, 0, 0))}
    refs.update({k: v for k, v in base.references().items() if k.endswith('_switch')})
    return {'runners_vs_' + k: round(vol(guard, v), 4) for k, v in refs.items()}, {'carrier_vs_' + k: round(vol(carrier, v), 4) for k, v in refs.items() if 'switch' in k or 'maximum_socket' in k or 'terminal' in k}


def probe_report(carrier, with_guard=True):
    """Rigid fingertip spheres pressed straight up under each terminal's stated solder allowance. 'blocked' means the
    sphere meets the holder, runners or rod before it reaches the bottom of that allowance. Stated probe sizes only."""
    obstacles = (carrier ^ h.box(-40, 40, -20, 40, -10, 7.6)) + h.cyl(4.0, -40, 100).rotate((-90, 0, 0)); out = {}
    for name, env in h.h20.contact_envelopes().items():
        b = env.bounding_box(); pts = [(x, y) for x in np.linspace(b[0] + .2, b[3] - .2, 3) for y in np.linspace(b[1] + .2, b[4] - .2, 3)]; row = {}
        for R in G['assumed_allowances']['fingertip_probe_radii_mm']:
            free = 0
            for x, y in pts:
                ball = mf.Manifold.sphere(R, 48).translate((float(x), float(y), float(b[2] - R - .01)))
                if (ball ^ obstacles).volume() < THRESH: free += 1
            row[f'R{R:g}'] = f'{len(pts) - free}/{len(pts)} blocked'
        out[name] = row
    return out


def row_table():
    c = base.P['cap_clearance_screen']; L = c['reference_length_mm']; m = c['lateral_allowance_per_cap_side_mm']; rows = []
    for d in (0., .4, .8, 1.0):
        spacing = h.K['r16_row_spacing_mm'] - d; gap = spacing - L
        rows.append({'shift_mm': d, 'row_spacing_mm': round(spacing, 2), 'reference_cap_gap_mm': round(gap, 2), 'after_0.4mm_play_each_cap_mm': round(gap - 2 * m, 2),
                     'meets_r16_screen_min_0.4mm': gap - 2 * m >= c['minimum_residual_gap_mm'] - 1e-9, 'max_socket_gap_key0_key3_mm': round(1.2 - d, 2)})
    return {'rows': rows, 'used_shift_mm': h.SHIFT, 'basis': 'Reference caps 17.5 x 16.6 mm with 0.4 mm lateral play each (R16 cap screen); purchased caps not measured. Socket gap from the bounding boxes of the maximum socket (key0 rear 8.3, key3 front 9.5 - shift).'}


def shoulder_report():
    s = base.P['slab']; ys = np.linspace(s['lower_rear_y_mm'], s['lower_rear_y_mm'] + h.K['shoulder_curve']['length_mm'], 301); xs = h.shoulder_x(ys)
    slope = float(np.max(np.abs(np.diff(xs) / np.diff(ys)))); out = h.slab_outline()
    return {'max_plan_slope': round(slope, 4), 'max_angle_degrees': round(math.degrees(math.atan(slope)), 2), 'prints_at_45_or_less': slope < 1, 'outline_area_mm2': round(out.area(), 2),
            'ends_y_mm': [s['lower_rear_y_mm'], s['lower_rear_y_mm'] + h.K['shoulder_curve']['length_mm']]}


def battery_report():
    body22, body20 = h.battery_module(), h.h20.battery_module(); out = {'leadin_removed_mm3': round(body20.volume() - body22.volume(), 4)}
    regions = h.h20.part_regions('Battery_Holder')
    out['working_spaces_overlap_mm3'] = {k: round(vol(body22, v), 4) for k, v in regions.items() if not isinstance(v, h.spaces16.Swept)}
    doors = {'Battery_End_Door': h.read(h.R19 / 'exports/Battery_End_Door-assembly.stl'), 'Battery_End_Door_Easy_Trial': h.easy_door()}
    for dn, door in doors.items():
        for bn, body in (('R20', body20), ('R22', body22)):
            hits = [vol(body, door.translate((0, 0, float(dz)))) for dz in np.linspace(15, 0, 61)]
            out[f'{dn}_into_{bn}'] = {'max_overlap_mm3': round(max(hits), 4), 'seated_overlap_mm3': round(hits[-1], 4), 'first_contact_height_mm': next((round(float(dz), 2) for dz, v in zip(np.linspace(15, 0, 61), hits) if v > THRESH), None)}
    out['note'] = 'Rigid CAD overlaps of the door dropped straight into its slots. Overlap near the seat is the designed catch/press fit inherited from R19/R20, not a new interference; compare R20 and R22 rows.'
    return out


def xiao_report():
    body = h.read(h.R20 / 'exports/XIAO_Rod_Holder-assembly.stl'); m = trimesh.load_mesh(h.R20 / 'exports/XIAO_Rod_Holder-assembly.stl'); bz = h.h19.BZ; board = h.h19.board_outline()
    sec = board.slice(bz + .5) if board.bounding_box()[5] > bz + .5 else board.slice((board.bounding_box()[2] + board.bounding_box()[5]) / 2)
    b = sec.bounds(); xs = np.arange(b[0] + .25, b[2], .5); ys = np.arange(b[1] + .25, b[3], .5); pts = [(x, y) for x in xs for y in ys if sec.offset(-.01).area() and (sec ^ h.rect(x - .01, x + .01, y - .01, y + .01)).area() > 0]
    origins = np.array([(x, y, bz - .005) for x, y in pts]); dirs = np.tile([0, 0, -1.], (len(origins), 1))
    loc, ray, _ = m.ray.intersects_location(origins, dirs, multiple_hits=False); clear = np.full(len(origins), 9.)
    for p, r in zip(loc, ray): clear[r] = min(clear[r], bz - p[2])
    clear = np.minimum(clear, 9.); pads = np.abs(origins[:, 0]) > h.h19.S['board_outline_mm']['width'] / 2 - 2.0
    hist = {f'>={t:g}mm': round(float(np.mean(clear >= t)) * 100, 1) for t in (1., 1.5, 2., 3.)}
    keeper = h.read(h.R19 / 'exports/XIAO_Near_Keeper-assembly.stl'); route = [vol(body, keeper.translate((0, -float(d), 0))) for d in np.linspace(12, 0, 33)]
    return {'board_underside_z_mm': bz, 'grid_points': len(pts), 'percent_of_board_area_with_clearance': hist, 'min_clearance_under_pad_band_mm': round(float(np.min(clear[pads])), 3),
            'percent_pad_band_with_2mm_or_more': round(float(np.mean(clear[pads] >= 2.)) * 100, 1), 'min_clearance_under_centre_mm': round(float(np.min(clear[~pads])), 3),
            'keeper_route_max_overlap_mm3': round(max(route), 4), 'keeper_seated_overlap_mm3': round(route[-1], 4),
            'decision': 'R20 body kept: Ethan reports the board sits almost flush and the R19 keeper was never printed for R20. Clearance under the board is listed here so a relief body can be made if the keeper cannot slide over a board lifted by underside solder.'}


def clip_report():
    clip = h.cable_clip(); w = C['axial_width_mm']; sec = clip.slice(w / 2); cx = C['centres_mm']; r_in = C['cable_bore_mm'] / 2
    holes = [p for p in sec.to_polygons()]; boundary = np.vstack(holes)
    def dist(x, y): return float(np.min(np.hypot(boundary[:, 0] - x, boundary[:, 1] - y)))
    wires = h.wire_centres(); rw = C['conductor_od_mm'] / 2
    clear = [round(dist(x, y) - rw, 3) for x, y in wires]; inside = all((sec ^ mf.CrossSection.circle(rw, 32).translate((x, y))).area() < 1e-4 for x, y in wires)
    pair = min(math.hypot(a[0] - b[0], a[1] - b[1]) for i, a in enumerate(wires) for b in wires[i + 1:])
    # Free opening of the slit: the two arm tips are the material nearest the slit line beyond the bore.
    tips = sec ^ h.rect(cx + r_in - .2, cx + r_in + C['cable_wall_mm'] + .5, -3, 3); pieces = [np.vstack(p.to_polygons()) for p in tips.decompose()]
    gap = min(float(np.min(np.hypot(a[:, None, 0] - b[None, :, 0], a[:, None, 1] - b[None, :, 1]))) for i, a in enumerate(pieces) for b in pieces[i + 1:]) if len(pieces) > 1 else 0.
    free_bore = dist(cx, 0.)
    rod_free = dist(0., 0.); waist = sec ^ h.rect(0, cx, -.05, .05)
    return {'section_z_mm': w / 2, 'cable_bore_free_radius_mm': round(free_bore, 3), 'wire_envelope_radius_mm': round(max(math.hypot(x - cx, y) for x, y in wires) + rw, 3), 'radial_slack_mm': round(free_bore - (max(math.hypot(x - cx, y) for x, y in wires) + rw), 3),
            'each_wire_clearance_to_plastic_mm': clear, 'all_wires_inside_bore': inside, 'min_wire_centre_spacing_mm': round(pair, 4), 'slit_free_opening_mm': round(gap, 3), 'slit_minus_wire_od_mm': round(gap - C['conductor_od_mm'], 3),
            'rod_bore_free_radius_mm': round(rod_free, 3), 'waist_material_on_axis_mm': round(waist.area() / .1, 3), 'volume_mm3': round(clip.volume(), 2), 'solid_PETG_g': round(clip.volume() * .00127, 4),
            'basis': '12 equal 1.5 mm conductors (stated envelope, not measured). One wire passes the slit at a time; real wire OD, stiffness and clip force are physical trials.'}


def export_report():
    path = OUT / 'manifest.json'
    if not path.exists(): return {'status': 'no exports yet'}
    man = json.loads(path.read_text()); rows = {}
    for name in man['plate_parts']:
        src = OUT / (name + '-SOURCE-REQUIRES-PREPARATION.stl')
        if not src.exists(): rows[name] = 'missing'; continue
        m = trimesh.load_mesh(src); rows[name] = {'sha_matches_manifest': h.sha(src) == man['parts'][name]['stl_sha256'], 'watertight': bool(m.is_watertight), 'bodies': len(m.split(only_watertight=False)), 'volume_mm3': round(float(m.volume), 2)}
        if name in h.COPIED_R19 + h.COPIED_R20:
            ref = json.loads(((h.R19 if name in h.COPIED_R19 else h.R20) / 'exports/manifest.json').read_text())['parts'][name]['stl_sha256']; rows[name]['byte_identical_to_source_revision'] = h.sha(src) == ref
        anchor = OUT / (name + '-ANCHOR-REMOVE-AFTER-PRINT.stl')
        if name in man.get('anchored_parts', []): rows[name]['anchor_present'] = anchor.exists()
    kc = OUT / 'Key_Carrier-assembly.stl'
    if kc.exists():
        a = h.read(kc); b = h.key_carrier(); rows['Key_Carrier']['export_vs_source_drift_mm3'] = round(float((a - b).volume() + (b - a).volume()), 5)
    rows['build_list_covers_plate'] = set(man.get('build_list', {})) >= set(man['plate_parts'])
    return rows


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT / 'geometry-checks.json'
    carrier = h.key_carrier(); runners, growth = runner_report(); seated_runners, seated_carrier = interference_report(carrier)
    report = {'revision': h.LOCAL['revision'], 'generator_sha256': h.sha(Path(__file__)), 'holder22_sha256': h.sha(h.HERE / 'holder22.py'), 'parameters_sha256': h.sha(h.HERE / 'parameters.json'),
              'key_carrier': {'volume_mm3': round(carrier.volume(), 2), 'bodies': len(carrier.decompose()), 'runner_volume_mm3': round(h.guard().volume(), 2), 'runner_PETG_g': round(h.guard().volume() * .00127, 3),
                              'layer_growth': growth, 'runners': runners, 'routes': route_report(carrier), 'seated_runner_overlaps_mm3': seated_runners, 'seated_holder_overlaps_mm3': seated_carrier,
                              'fingertip_probe_r22': probe_report(carrier), 'fingertip_probe_without_runners': probe_report(h.carrier_base()), 'row_spacing_table': row_table(), 'shoulder': shoulder_report()},
              'battery': battery_report(), 'xiao': xiao_report(), 'cable_clip': clip_report(), 'exports': export_report(),
              'physical_fit_verified': False, 'physical_strength_verified': False, 'physical_comfort_verified': False}
    target.write_text(json.dumps(report, indent=2) + '\n')
    k = report['key_carrier']; print(json.dumps({'bodies': k['bodies'], 'runner_g': k['runner_PETG_g'], 'growth': growth, 'routes': {n: (v.get('max_overlap_mm3'), v.get('extra_drop_allowed_mm')) for n, v in k['routes'].items() if n.startswith('key_')},
                                                 'carve_hits': k['routes']['carve_log_final_poses_meeting_material'], 'runners': {n: (v['min_free_thickness_mm'], v['rear_root_bond_layers'], v['front_root_bond_layers'], v['layers_with_no_runner_section_y_mm'][:4]) for n, v in runners.items()},
                                                 'seated_hits': {n: v for n, v in seated_runners.items() if v > THRESH}, 'clip': {x: report['cable_clip'][x] for x in ('radial_slack_mm', 'slit_free_opening_mm', 'all_wires_inside_bore')}, 'xiao': report['xiao']['percent_of_board_area_with_clearance'],
                                                 'battery': {n: v for n, v in report['battery'].items() if n.startswith('Battery_End')}}, default=str), flush=True)


if __name__ == '__main__':
    main()
