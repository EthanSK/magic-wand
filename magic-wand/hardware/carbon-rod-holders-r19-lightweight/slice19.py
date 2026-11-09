#!/usr/bin/env python3
"""Audit the actual sliced R19 project, part by part, from its G-code.

Every bead type in every working space, layer starts on real beads, fused anchor necks and the
designed flange gap, ring and channel sections with surviving tracks. Numerical guards are not
manufacturing tolerances. Nothing here is a physical print result.
"""
import argparse, json, math, zipfile, xml.etree.ElementTree as E
from pathlib import Path
import numpy as np, trimesh
import manifold3d as mf
import holder19 as h
import anchors19
import slice16 as s16
import travel19

q = s16.q; start_audit = s16.start_audit; OUT = h.HERE / 'exports'; N = s16.N
STEP = s16.STEP


def anchor_in_project(project, name, place):
    """Read the labelled anchor part back out of the delivered project."""
    with zipfile.ZipFile(project) as z:
        cfg = E.fromstring(z.read('Metadata/model_settings.config')); model = E.fromstring(z.read('3D/3dmodel.model')); cache = {'3D/3dmodel.model': model}
        roots = {o.get('id'): o for o in model.findall('m:resources/m:object', N)}; builds = {i.get('objectid'): q.transform(i.get('transform')) for i in model.findall('m:build/m:item', N)}
        for obj in cfg.findall('object'):
            if q.metadata(obj)['name'] != name: continue
            for part in obj.findall('part'):
                title = q.metadata(part).get('name', '')
                if not (title.startswith('REMOVE AFTER PRINT') and part.get('subtype') == 'normal_part'): continue
                comp = next(c for c in roots[obj.get('id')].findall('m:components/m:component', N) if c.get('objectid') == part.get('id'))
                path = next((v.lstrip('/') for k, v in comp.attrib.items() if k.endswith('}path')), '3D/3dmodel.model')
                if path not in cache: cache[path] = E.fromstring(z.read(path))
                child = next(o for o in cache[path].findall('m:resources/m:object', N) if o.get('id') == part.get('id'))
                vv = np.array([[float(v.get(k)) for k in 'xyz'] for v in child.findall('m:mesh/m:vertices/m:vertex', N)]); tt = np.array([[int(v.get(k)) for k in ['v1', 'v2', 'v3']] for v in child.findall('m:mesh/m:triangles/m:triangle', N)])
                vv = q.points(q.points(vv, q.transform(comp.get('transform'))), builds[obj.get('id')])
                return q.solid(vv - place, tt), title
    raise AssertionError((name, 'anchor part missing from project'))


def neck_audit(name, samples, widths, tops):
    """Prove from actual beads that each neck is continuous plastic joining part and flange."""
    solid_, flange, plan, section, record = anchors19.anchor(name); t = record['thickness_mm']; rows = []; A_ = h.LOCAL['anchors']
    layers = sorted({round(float(v), 3) for v in tops if v <= t + 1e-3 and v > 0}); necks = plan['necks']; joined = mf.CrossSection.batch_boolean(necks, mf.OpType.Add)
    worst_gap = 9.; pad_counts = []
    for top in layers:
        sel = abs(tops - top) < 1e-3; beads = start_audit.bead_footprints(q, samples[sel, :2], widths[sel]); components = beads.decompose()
        for index, neck in enumerate(necks):
            b = neck.bounds()
            # The centre line runs the joining direction: from inside the part, through the gap, into the flange.
            # A 1 mm tie prints as two touching beads, so probe along each bead rather than the seam between them.
            best = None
            for off in (-.22, .22):
                if plan['axes'][index] == 'x': pts_ = np.c_[np.linspace(b[0], b[2], 41), np.full(41, (b[1] + b[3]) / 2 + off)]
                else: pts_ = np.c_[np.full(41, (b[0] + b[2]) / 2 + off), np.linspace(b[1], b[3], 41)]
                cov = float(q._inside(beads, pts_).mean())
                if best is None or cov > best[0]: best = (cov, pts_)
            covered, pts = best; fraction = (beads ^ neck).area() / neck.area()
            ids = [i for i, c in enumerate(components) if q._inside(c, pts).sum() >= 30]
            assert covered >= .8 and len(ids) == 1, (name, top, index, covered, fraction, ids)
            comp = components[ids[0]]
            # The same printed island must reach into both the part and the flange at this neck.
            assert (comp ^ section).area() > .5 and (comp ^ flange).area() > .5, (name, top, index, 'neck does not join part and flange')
            rows.append({'layer_top_mm': top, 'neck': index, 'centre_line_bead_coverage': round(covered, 4), 'neck_area_bead_fraction': round(fraction, 4)})
        # Everywhere away from the necks, the flange beads must stay clear of the part beads.
        away = beads - joined.offset(.35, q.JoinType.Round); flange_beads = away ^ flange.offset(.3, q.JoinType.Round); part_beads = away ^ section.offset(.3, q.JoinType.Round)
        lo, hi = 0., 1.2
        if not (part_beads.offset(lo + .01, q.JoinType.Round) ^ flange_beads).is_empty(): raise AssertionError((name, top, 'flange bead touches part bead away from the necks'))
        for _ in range(9):
            mid = (lo + hi) / 2
            if (part_beads.offset(mid, q.JoinType.Round) ^ flange_beads).is_empty(): lo = mid
            else: hi = mid
        worst_gap = min(worst_gap, lo)
        pads_printed = [c for c in flange_beads.decompose() if c.area() > 1.]; assert len(pads_printed) == record['separate_pads'], (name, top, len(pads_printed), record['separate_pads'])
        pad_counts.append(len(pads_printed))
        for i, c in enumerate(pads_printed):
            for other in pads_printed[i + 1:]: assert (c.offset(.35, q.JoinType.Round) ^ other).is_empty(), (name, top, 'pads closer than 0.35 mm')
    assert worst_gap >= .35, (name, 'flange to part bead gap', worst_gap)
    return {'neck_count': len(necks), 'layers': layers, 'minimum_centre_line_bead_coverage': min(r['centre_line_bead_coverage'] for r in rows), 'minimum_neck_bead_fraction': min(r['neck_area_bead_fraction'] for r in rows),
            'minimum_flange_to_part_bead_gap_away_from_necks_mm': round(worst_gap, 3), 'designed_gap_mm': A_['gap_mm'], 'separate_pads_printed_in_each_layer': pad_counts, 'minimum_gap_between_pads_screen_mm': .35, 'rows': rows,
            'method': 'Actual 12-gon bead footprints in each anchor layer: coverage along each neck in its joining direction, a single printed island reaching the part and the flange, and the bead gap everywhere else.'}


def classify(name, part_rows, to_assembly, actual):
    out = []; cg = h.CAGE; s = h.S; r = h.RET; bz = h.BZ
    for row in part_rows:
        b = row['print_xy_bounds_mm']; top = row['layer_top_mm']
        x, y, z = [float(v) for v in q.points(np.array([[(b[0] + b[2]) / 2, (b[1] + b[3]) / 2, top - .1]]), to_assembly)[0]]; rad = math.hypot(x, z)
        section = actual.slice(top - .1); patch = q.CrossSection([[[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]]])
        cls = None
        if (patch - section.offset(-.5, q.JoinType.Round)).area() < .05: cls = 'internal shell transition inside a solid region (slicer behaviour, enclosed by walls)'
        elif name == 'Battery_Holder':
            if rad < 6.2 and z < 4.3 and y > cg['near_band_y_mm'][1] - .3: cls = 'ring lead-in skirt: 45-degree arc rule, each layer rests on the previous arm layer'
            elif abs(x) > cg['side_rail_x_mm'][0] - .3 and y < cg['gate_slot_y_mm'][0] + .4: cls = 'gate slot closing ramp: grown inward from the outer wall at 45 degrees, not over air; local slow band applied'
            elif abs(x) > cg['side_rail_x_mm'][0] - .3 and y < cg['guide_y_mm'][1] + 2.8: cls = 'gate guide led in at 45 degrees from the side wall, same as R16'
            elif z > 10.5 and -14 < y < h.B19['arrow_root_y_mm'] - .3 and abs(x) < h.CAGE['side_rail_x_mm'][0] and abs(y - (abs(x) - 13.)) < 1.2: cls = 'arrow roof V edge: grows 45 degrees toward the near-end bar'
            elif abs(y - cg['end_plate_y_mm'][0]) < 1.5 and abs(x) < 11: cls = 'cell end stop or plate window roof at the closed end'
        elif name == 'XIAO_Rod_Holder':
            if rad < 6.2 and z < 4.3 and y > s['near_band_y_mm'][1] - .3: cls = 'ring lead-in skirt: 45-degree arc rule'
            elif abs(x) <= h.S['keel_x_mm'] + .3 and -5.3 < y < 3.3 and z > 5.8: cls = 'keeper ridge: both faces 45 degrees, width equal to the keel'
            elif z > 13.4 and y > 20.3: cls = 'far hoop arrow over USB: narrows going up'
            elif r['post']['full_y_mm'][0] - .3 < y < r['post']['lead_end_y_mm'] + .3 and abs(x) > s['rail_x_mm'][0] - .3 and z > s['rail_z_mm'][0]: cls = 'near post: grown from the rail at 45 degrees; the groove is a plain notch in each layer'
            elif abs(x) > s['cradle_inner_x_mm'] - .3 and y < s['near_contact_limit_y_mm'] + s['ramp_length_mm'] + (s['rail_x_mm'][0] - s['cradle_inner_x_mm']) + .4 and z < bz + s['stop_height_mm'] + .3: cls = 'near board cradle: ledge and lead grown from the rail at 45 degrees, clear of the first solder pad'
            elif y < s['near_band_y_mm'][1] + (s['bar_rail_mm'][0] - s['bar_crown_mm'][0]) + .6 and abs(x) > 1.0: cls = 'near end gusset bar growing at 45 degrees from the rail toward the saddle, as R16 with the rail moved outward'
            elif rad < 6.2: cls = 'saddle flank over the rod at 45 degrees'
        elif name in ('Battery_End_Door', 'XIAO_Near_Keeper') or name.startswith('Battery_Spacer'):
            cls = 'flat part on its broad face'
        out.append({**row, 'assembly_centre_mm': [round(x, 3), round(y, 3), round(z, 3)], 'decision_class': cls or 'UNCLASSIFIED - review'})
    return out


def ring_entry(solid, pts, wd, y0, y1, width, root_wall, skirted):
    yc = (y0 + y1) / 2; a = h.P['arrow_ring']
    sections = {str(ang): round(s16.radial_section(solid, yc, ang), 4) for ang in [-70, -55, 0, 90, 180, 235, 250]}
    assert min(sections.values()) > .95, sections
    layer, tracks = s16.polar_tracks(pts, wd, yc); assert all(len(v) >= 2 for v in tracks.values()), tracks
    entry = {'band_y_mm': [y0, y1], 'radial_STL_sections_mm': sections, 'sampled_layer_assembly_y_mm': layer, 'radial_track_centres_mm': tracks, 'arm_bonding': s16.arm_bonding(solid, yc, width, root_wall)}
    if skirted:
        entry['lead_in_skirt'] = s16.skirt_scan(solid, pts, wd, y0, y1, width, root_wall, a['skin_thickness_mm']); entry['band_start_backing'] = s16.band_start_backing(pts, wd, y0, y1, +1, f'band y {y0:g}')
    return entry


def inspect(project_name, out_dir=None, tag=''):
    out_dir = Path(out_dir) if out_dir else OUT; project = Path(project_name) if Path(project_name).is_absolute() else OUT / project_name
    manifest = json.loads((OUT / 'manifest.json').read_text()); data, features, stats, settings, offset, parts, gcode_text, config_text = s16.read_project(project)
    assert not any(f.startswith(('Support', 'Brim', 'Skirt')) for f in features), features
    import project19
    slice_info = project19.slice_info_warnings(project)
    allowed = {'not_support_traditional_timelapse'}; assert all(w['msg'] in allowed for w in slice_info), slice_info
    report = {'project_sha256': h.sha(project), 'manifest_sha256': h.sha(OUT / 'manifest.json'), 'checker_sha256': h.sha(Path(__file__)), 'travel_parser_sha256': h.sha(h.HERE / 'travel19.py'), 'r16_slice_helpers_sha256': h.sha(h.R16 / 'slice16.py'), 'parser_sha256': h.sha(Path(q.__file__)), 'start_auditor_sha256': h.sha(h.base.R15 / 'start_audit.py'),
              'features': features, 'parser_stats': stats, 'settings': {k: settings.get(k) for k in ['printer_settings_id', 'print_settings_id', 'filament_settings_id', 'layer_height', 'wall_loops', 'sparse_infill_density', 'enable_support', 'brim_type', 'nozzle_temperature', 'textured_plate_temp', 'initial_layer_speed', 'z_hop', 'elefant_foot_compensation']},
              'parts': {}, 'physical_print_verified': False,
              'slice_info_warnings': slice_info, 'slice_info_warning_note': 'not_support_traditional_timelapse appears at levels 2 and 3 on this project, the committed R16 project and the offline re-slice of the retry, whose printer timelapse still recorded. What Bambu Studio means by it was not established.'}
    images = {}; assembly = {}
    for name in h.PLATE:
        record = manifest['parts'][name]; info = parts[name]; expected = trimesh.load_mesh(OUT / (name + '-SOURCE-REQUIRES-PREPARATION.stl')); has_anchor = name in h.ANCHORED; anchor_file = trimesh.load_mesh(OUT / (name + ('-ANCHOR-REMOVE-AFTER-PRINT.stl' if has_anchor else '-SOURCE-REQUIRES-PREPARATION.stl')))
        place = (info['vertices'].min(0) + info['vertices'].max(0) - expected.bounds.sum(0)) / 2
        actual = q.solid(expected.vertices, expected.faces); project_solid = q.solid(info['vertices'] - place, info['faces'])
        difference = abs((actual - project_solid).volume()) + abs((project_solid - actual).volume()); assert difference < .05, (name, difference)
        anchor_difference = 0.; title = None; combined = actual
        if has_anchor:
            anchor_solid = q.solid(anchor_file.vertices, anchor_file.faces); read_anchor, title = anchor_in_project(project, name, place)
            anchor_difference = abs((anchor_solid - read_anchor).volume()) + abs((read_anchor - anchor_solid).volume()); assert anchor_difference < .05, (name, anchor_difference)
            combined = actual + anchor_solid
        lo = np.minimum(expected.bounds[0], anchor_file.bounds[0]); hi = np.maximum(expected.bounds[1], anchor_file.bounds[1])
        local = data[:, :3] + offset - place; mask = np.all(local >= lo - .4, 1) & np.all(local <= hi + .4, 1)
        samples = local[mask]; w = data[mask, 3]; hh = data[mask, 4]; f = data[mask, 5].astype(int); tops = data[mask, 7]; assert len(samples) > 500, name
        pa = np.array(record['print_to_assembly']); to_print = np.linalg.inv(pa); assembly[name] = (q.points(samples, pa), w)
        # Anchor beads are cut off before assembly, so they answer only to the print-time keep-clear list.
        if has_anchor:
            _, flange, plan_, _, record_ = anchors19.anchor(name); anchor_plan = flange + mf.CrossSection.batch_boolean(plan_['necks'], mf.OpType.Add); is_anchor = (tops <= record_['thickness_mm'] + 1e-3) & q._inside(anchor_plan.offset(.3, q.JoinType.Round), samples[:, :2])
        else: is_anchor = np.zeros(len(samples), bool)
        keep = ~is_anchor
        checks = {}; swept = {}
        for label, region in h.regions(name).items():
            if isinstance(region, h.spaces16.Swept):
                worst = None
                for pose in region.poses():
                    res = q.inspect_region(pose.transform(to_print[:3, :]), samples[keep], w[keep], hh[keep], f[keep], features, pa, limit=4)
                    if worst is None or sum(res['violations'].values()) > sum(worst['violations'].values()): worst = res
                checks[label] = {**worst, 'poses': len(region)}; swept[label] = len(region)
            else:
                checks[label] = q.inspect_region(region.transform(to_print[:3, :]), samples[keep], w[keep], hh[keep], f[keep], features, pa, limit=4)
        keep_clear = {}
        for label, region in h.regions(name).items():
            if label == 'unloaded_clip_bore' or label.startswith(('clip_gap', 'gate_slot', 'retainer_groove', 'tongue_slit')):
                res = q.inspect_region(region.transform(to_print[:3, :]), samples[is_anchor], w[is_anchor], hh[is_anchor], f[is_anchor], features, pa, limit=4)
                keep_clear[label] = {'checked_samples': res['checked_samples'], 'violations': res['violations']}; assert not res['violations'], (name, label, res['violations'])
        starts = start_audit.inspect(q, combined, samples, hh, f, features, tops, pa, w)
        rows = classify(name, starts['partial_overhangs'], pa, combined)
        unclassified = [r for r in rows if r['decision_class'].startswith('UNCLASSIFIED')]
        necks = neck_audit(name, samples, w, tops) if has_anchor else {'neck_count': 0, 'minimum_centre_line_bead_coverage': None, 'minimum_flange_to_part_bead_gap_away_from_necks_mm': None}; s16.views(name, combined, samples, w, tops, starts['partial_overhangs'], pa, images, out_dir, tag)
        report['parts'][name] = {'normal_mesh_difference_mm3': difference, 'anchor_mesh_difference_mm3': anchor_difference, 'anchor_part_label': title, 'path_samples': int(mask.sum()), 'checks': checks, 'swept_space_poses': swept,
                                 'layer_starts': {k: v for k, v in starts.items() if k != 'partial_overhangs'}, 'partial_overhangs': rows, 'unclassified_overhangs': unclassified, 'anchor_necks': necks, 'anchor_bead_samples': int(is_anchor.sum()), 'anchor_beads_against_print_time_keep_clear': keep_clear}
        print(name, 'violations:', {k: v['violations'] for k, v in checks.items() if v['violations']}, 'floating:', len(starts['floating_components']), 'missing:', len(starts['missing_printed_components']), 'partial rows:', len(rows), 'unclassified:', len(unclassified), 'neck min coverage', necks['minimum_centre_line_bead_coverage'], 'gap', necks['minimum_flange_to_part_bead_gap_away_from_necks_mm'], flush=True)
        for r in unclassified: print('   UNCLASSIFIED', json.dumps({k: r[k] for k in ['layer_top_mm', 'unbacked_mesh_area_mm2', 'print_xy_bounds_mm', 'direct_backed_fraction', 'assembly_centre_mm']}), flush=True)
    # Local recipe speeds read back from the G-code.
    recipe = h.P['print']['local_recipe']; bands = {n: recipe.get(n + '_bands_mm', []) for n in ['Battery_Holder']}
    actual_bands = s16.band_speeds(gcode_text, config_text, bands)
    limits = {'Outer wall': 'outer_wall_speed', 'Inner wall': 'inner_wall_speed', 'Gap infill': 'gap_infill_speed', 'Overhang wall': 'overhang_1_4_speed', 'Bridge': 'bridge_speed', 'Internal solid infill': 'internal_solid_infill_speed', 'Sparse infill': 'sparse_infill_speed', 'Top surface': 'top_surface_speed'}
    too_fast = [(p, z, feat, sp) for p, layers in actual_bands.items() for z, row in layers.items() for feat, sp in row['features_mm_s'].items() if limits.get(feat) and max(sp) > recipe['speeds_mm_s'][limits[feat]] + .5]
    assert actual_bands and not too_fast, too_fast[:4]
    report['band_recipe_actual'] = {'bands_mm': bands, 'requested_speeds_mm_s': recipe['speeds_mm_s'], 'actual_in_bands': actual_bands, 'features_faster_than_requested': too_fast}
    # Rings, channel, rails and cradles against actual beads.
    solids = {n: q.solid(*(lambda m: (m.vertices, m.faces))(trimesh.load_mesh(OUT / (n + '-assembly.stl')))) for n in h.ANCHORED}
    B, X = solids['Battery_Holder'], solids['XIAO_Rod_Holder']; bs, bw = assembly['Battery_Holder']; xs, xw = assembly['XIAO_Rod_Holder']; c = h.CAGE; s = h.S; rw = h.P['rod']['ring_width']; rr_ = h.P['rod']['clip_root_wall']; sw = s['clip_width_mm']; sr = h.P['rod']['sensor_clip_root_wall']
    report['strength'] = {'rings': {'Battery_Holder': {'near': ring_entry(B, bs, bw, *c['near_band_y_mm'], rw, rr_, True), 'far': ring_entry(B, bs, bw, *c['far_band_y_mm'], rw, rr_, False)},
                                    'XIAO_Rod_Holder': {'near': ring_entry(X, xs, xw, *s['near_band_y_mm'], sw, sr, True), 'far': ring_entry(X, xs, xw, *s['far_band_y_mm'], sw, sr, False)}}}
    bz = h.BZ; inner = s['cradle_inner_x_mm']; rail = s['rail_x_mm'][0]; yn = s['board_near_end_y_mm']; yf = yn + s['board_outline_mm']['length']; un, uf = s['ledge_under_board_mm']; limit = s['near_contact_limit_y_mm']; r = h.RET; scans = {
        'Battery_Holder': [s16.path_scan(B, bs, bw, (-12.6, 16.4), (-15, 15, 3.0, 12.5), 'Whole open section, every layer between the near bar and the end frame', 16., .55, 'Cell, rod and print-time loads pass through walls, keel and cross bars in series.', 'Open ladder; see load_paths for the member-by-member check.'),
                           s16.path_scan(B, bs, bw, (-12.6, 16.4), (-h.B19['keel_half_x_mm'], h.B19['keel_half_x_mm'], 4.2, 5.85), 'Keel, every layer', 4., .6, 'Spine joining both rod rings.', 'Continuous 3 x 1.65 mm section.'),
                           s16.path_scan(B, bs, bw, (-5., 14.), (c['side_rail_x_mm'][0], h.B19['wall_outer_x_mm'], 4.35, 12.35), 'Right wall, every layer', 5.5, .6, 'Side retention and longitudinal chord.', 'Continuous 1.3 mm wall.'),
                           s16.path_scan(B, bs, bw, (-5., 14.), (-h.B19['wall_outer_x_mm'], -c['side_rail_x_mm'][0], 4.35, 12.35), 'Left wall, every layer', 5.5, .6, 'Side retention and longitudinal chord.', 'Continuous 1.3 mm wall.')],
        'XIAO_Rod_Holder': [s16.path_scan(X, xs, xw, (-2.6, 21.0), (-14.5, 14.5, -1, 15), 'Whole open section, every layer', 13., .55, 'Board, USB and rod loads pass along rails and keel.', 'Open ladder; see load_paths for the member-by-member check.'),
                            s16.path_scan(X, xs, xw, (-2.6, 21.0), (-s['keel_x_mm'], s['keel_x_mm'], s['keel_z_mm'][0], s['keel_z_mm'][1]), 'Keel, every layer', 5., .6, 'Spine joining both rod rings.', 'Continuous 3 x 2 mm section.')]}
    # The strip of each cross bar: the only in-layer tie between wall and keel, so it must really print.
    for sign, side in ((1, '+X'), (-1, '-X')):
        wn = sorted([sign * 3.3, sign * 8.9]); (zb, zt) = h.B19['rib_z_mm']
        scans['Battery_Holder'] += [s16.path_scan(B, bs, bw, (cap + .1, cap + h.LOCAL['ribs']['strip_y_mm'] - .1), (wn[0], wn[1], zb, zt), f'Cross bar strip {side} at Y {cap:g}', 7.0, .7, 'Ties wall to keel inside the layer plane.', '1.5 mm thick strip, 1.2 mm deep, carried by 45-degree wedges.') for cap in h.B19['bar_cap_y_mm']]
        wn = sorted([sign * 3.3, sign * 8.3])
        scans['XIAO_Rod_Holder'] += [s16.path_scan(X, xs, xw, (cap + .1, cap + h.LOCAL['ribs']['strip_y_mm'] - .1), (wn[0], wn[1], 4.5, 8.6), f'Cross bar strip {side} at Y {cap:g}', 5.5, .7, 'Ties rail to keel inside the layer plane.', '1.3 mm thick sloped strip, 1.2 mm deep, carried by 45-degree wedges.') for cap in h.X19['bar_cap_y_mm']]
    # Bar roots: in every strip layer, one printed island must run from the bar into the rail or wall, and into the keel.
    def root(solid_pts, widths, cap, x_bar, z_bar, x_chord, z_chord, keel_z, label):
        rows = []; ys = np.unique(np.round(solid_pts[:, 1], 4)); ys = ys[(ys + .1 > cap) & (ys + .1 < cap + h.LOCAL['ribs']['strip_y_mm'])]; assert len(ys) >= 4, (label, ys)
        for y in ys:
            sel = abs(solid_pts[:, 1] - y) < .01; beads = start_audit.bead_footprints(q, solid_pts[sel][:, [0, 2]] * np.array([1, -1]), widths[sel]); pieces = beads.decompose()
            # A bead seam can leave a tiny void at any single point, so each probe is a 0.6 mm square of printed plastic.
            square = lambda x, z: q.CrossSection([[[x - .3, -z - .3], [x + .3, -z - .3], [x + .3, -z + .3], [x - .3, -z + .3]]])
            bar, chord, keel = square(x_bar, z_bar), square(x_chord, z_chord), square(0., keel_z); hit = max(pieces, key=lambda c: (c ^ bar).area())
            assert (hit ^ bar).area() > .08 and (hit ^ chord).area() > .08 and (hit ^ keel).area() > .08, (label, float(y), (hit ^ bar).area(), (hit ^ chord).area(), (hit ^ keel).area())
            rows.append(round(float(y), 2))
        return {'bar': label, 'layers_checked': rows, 'one_printed_island_bar_to_chord_and_keel': True}
    plane = lambda x: tuple(np.interp(x, [h.X19['rib_inner_x_z_z'][0], h.X19['rib_outer_x_z_z'][0]], [h.X19['rib_inner_x_z_z'][i], h.X19['rib_outer_x_z_z'][i]]) for i in (1, 2))
    roots = []
    for sign, side in ((1, '+X'), (-1, '-X')):
        z_mid = sum(plane(8.5)) / 2
        roots += [root(xs, xw, cap, sign * 8.5, z_mid, sign * 11.2, 8.4, sum(s['keel_z_mm']) / 2, f'XIAO {side} cap Y {cap:g}') for cap in h.X19['bar_cap_y_mm']]
        roots += [root(bs, bw, cap, sign * 8.5, 5.1, sign * 11.25, 5.1, 5.1, f'Battery {side} cap Y {cap:g}') for cap in h.B19['bar_cap_y_mm']]
    report['strength']['cross_bar_roots_actual_beads'] = roots
    # Highest actual bead under each XIAO pad row, on both sides. Row 0 is left out because it holds R18's unchanged near-ledge lead.
    hv = h.XO['pad_land_half_v']; under = {}
    for row_i, v in enumerate(h.XO['castellation_v_centres']):
        if row_i == 0: continue
        y0, y1 = h.board_y(v - hv), h.board_y(v + hv)
        if row_i == 1: y0 = max(y0, s['near_contact_limit_y_mm'] + s['ramp_length_mm'] + s['rail_x_mm'][0] - s['cradle_inner_x_mm'] + .05)
        for sign in (1, -1):
            x0, x1 = sorted([sign * 7., sign * 9.95]); sel = (xs[:, 0] >= x0) & (xs[:, 0] <= x1) & (xs[:, 1] >= y0) & (xs[:, 1] <= y1) & (xs[:, 2] < h.BZ)
            if not sel.any(): under[f'row{row_i}_{sign:+d}'] = {'beads_sampled': 0}; continue
            top = float((xs[sel, 2] + xw[sel] / 2).max()); gap = h.BZ - top; assert gap >= 1.0, (row_i, sign, gap); under[f'row{row_i}_{sign:+d}'] = {'highest_bead_top_z_mm': round(top, 3), 'gap_to_board_underside_mm': round(gap, 3), 'beads_sampled': int(sel.sum())}
    report['strength']['xiao_pad_rows_actual_bead_clearance'] = under
    # Named thin sections: mesh thickness along the probe and the actual bead centres that fill it.
    def thin(solid, pts, wd, label, origin, axis, length, load):
        d = np.array(axis, float); o = np.array(origin, float); size, a, b = s16.ray_section(solid, o, d); layer, tracks = s16.tracks_on_ray(pts, wd, o, d, a, b)
        return {'section': label, 'mesh_thickness_mm': round(size, 3), 'bead_centres_across_it': len(tracks), 'probe_layer_y_mm': round(float(layer), 2), 'carries': load}
    thin_rows = []
    for sign, side in ((1, '+X'), (-1, '-X')):
        thin_rows += [thin(X, xs, xw, f'XIAO hoop outer leg {side}', (sign * 11.4, 22.7, 12.2), (1, 0, 0), 2., 'Hoop bar and lip'),
                      thin(X, xs, xw, f'XIAO hoop inner leg {side}', (sign * 8.3, 22.7, 12.2), (1, 0, 0), 2., 'Hoop bar and lip'),
                      thin(B, bs, bw, f'Battery door-slot outer wall {side}', (sign * 13.6, -15., 9.), (1, 0, 0), 2., 'Door side load')]
    thin_rows += [thin(B, bs, bw, f'Battery catch-bar ligament above pocket, Y {yy:g}', (0., yy, 11.9), (0, 0, 1), 2., 'Door tooth catch; unchanged from R18') for yy in (-13.7, -13.3)]
    report['strength']['named_thin_sections'] = thin_rows
    for row in thin_rows: assert row['bead_centres_across_it'] >= (1 if 'ligament' in row['section'] else 2), row
    r18_rings = json.loads((h.h18.HERE / 'exports' / 'slice-clearances.json').read_text())['strength']['rings']
    report['strength']['ring_free_arc_vs_r18_degrees'] = {n: {b: {'r18': r18_rings[n][b]['arm_bonding']['free_arm_arc_degrees'], 'r19': report['strength']['rings'][n][b]['arm_bonding']['free_arm_arc_degrees']} for b in ('near', 'far')} for n in h.ANCHORED}
    p = r['post']; g = r['groove']; hp = h.H['hoop']
    for sign, label in ((1, '+X'), (-1, '-X')):
        xr = sorted([sign * inner, sign * rail]); pr = sorted([sign * rail, sign * p['outer_x_mm']]); lip = sorted([sign * g['lip_inner_x_mm'], sign * g['back_x_mm']]); sh = sorted([sign * hp['shoulder_inner_x_mm'], sign * s['rail_x_mm'][1]])
        scans['XIAO_Rod_Holder'] += [
            s16.path_scan(X, xs, xw, (yn + .3, limit), (xr[0], xr[1], bz - .45, bz), f'Near {label} contact ledge', .4, .5, 'A board corner rests here.', 'Contact only ahead of the first solder pad.'),
            s16.path_scan(X, xs, xw, (yf - uf, yf), (xr[0], xr[1], bz - .45, bz), f'Far {label} ledge', .5, .5, 'A board corner rests here.', 'As R16.'),
            s16.path_scan(X, xs, xw, (p['full_y_mm'][0] + .1, p['full_y_mm'][1] - .2), (pr[0], pr[1], s['rail_z_mm'][0], p['top_z_mm']), f'Near post {label}', 12., .5, 'Keeper bears here.', 'C-section carried into the rail.'),
            s16.path_scan(X, xs, xw, (p['full_y_mm'][0] + .1, g['closed_end_y_mm'] - .2), (lip[0], lip[1], g['ceiling_z_mm'], p['top_z_mm']), f'Groove lip {label}', 1.5, .5, 'Holds the keeper down.', 'Tied to the outer wall in every layer.'),
            s16.path_scan(X, xs, xw, (hp['y_mm'][0] + .1, h.X19['hoop']['column_y_mm'][0] - .1), (sh[0], sh[1], hp['shoulder_under_z_mm'], h.X19['hoop']['top_z_mm']), f'Far hoop lip {label}', 4.5, .5, 'Holds the USB end down over the bare board corner.', 'Lip over the board corner, carried by the column behind it.'),
            s16.path_scan(X, xs, xw, (h.X19['hoop']['column_y_mm'][0] + .1, hp['y_mm'][1] - .1), (sh[0], sh[1], hp['shoulder_under_z_mm'], h.X19['hoop']['top_z_mm']), f'Far hoop pierced column {label}', 12., .5, 'Carries the lip and the USB bar.', 'Column with a window, standing on the rail, printed from the bed.')]
    report['strength']['path_scans'] = scans
    import loadpath19
    report['strength']['actual_beads_in_every_island'] = {n: loadpath19.bead_islands(solids[n], assembly[n][0], assembly[n][1], start_audit.bead_footprints, q) for n in h.ANCHORED}
    for n, v in report['strength']['actual_beads_in_every_island'].items(): assert v['smallest_printed_fraction_of_an_island'] >= .55 and v['smallest_printed_area_of_an_island_mm2'] >= 2.0, (n, v)
    # Comparison evidence: toolhead traffic over the battery in the upper layers.
    origin = np.array(json.loads((OUT / 'R19-A1-mini-PETG-print-checks.json').read_text())['plate_origins_mm']['Battery_Holder'], dtype=float)
    report['battery_travel_exposure_from_layer_top_20_mm'] = travel19.exposure(gcode_text, origin - 1, origin + [30.2, 18.2], 20.0)
    report['images_sha256'] = images
    report['passed'] = all(not c_['violations'] for p in report['parts'].values() for c_ in p['checks'].values()) and all(not p['layer_starts']['floating_components'] and not p['layer_starts']['missing_printed_components'] and not p['unclassified_overhangs'] for p in report['parts'].values())
    target = out_dir / f'slice-clearances{tag}.json'; target.write_text(json.dumps(report, indent=2) + '\n')
    assert report['passed'], f'See {target.name}'
    print('Actual beads clear every working space; every layer start is backed; anchor necks are continuous; every overhang row classified.', flush=True)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--project', default='R19-A1-mini-PETG.gcode.3mf'); a = p.parse_args(); inspect(a.project)
