#!/usr/bin/env python3
"""Audit the actual sliced R20 project, part by part, from its G-code.

Uses the R16 project reader and bead parser and the R15 layer-start auditor unchanged. For each of the four
objects: the sliced meshes are the exported ones; no support, brim or skirt exists; every working space is clear
of every part bead; tear-off pad beads stay out of rod bores, ring openings and guard windows; no layer starts
in air; each tie is one continuous printed island joining pad and part; pads stay clear of the part elsewhere.
First-pass evidence for the independent review. Nothing here is a physical print result.
"""
import sys
sys.dont_write_bytecode = True
import argparse, json
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf
import holder20 as h
import anchors20
sys.path[:0] = [str(h.R19), str(h.R16)]
import slice16 as s16  # noqa: E402
import slice19  # noqa: E402  (only anchor_in_project, which reads a labelled pad part back out of a project)
import project20  # noqa: E402  points project19 at the R20 plate and recipe
project19 = project20.p19

q = s16.q; start_audit = s16.start_audit; OUT = h.HERE / 'exports'; A = h.LOCAL['anchors']
KEEP_CLEAR_OF_PADS = ('unloaded_clip_bore', 'clip_gap', 'wire_crossing_sector', 'six_windows', 'rigid_rod_corridor', 'gate_slot', 'retainer_groove')


def neck_audit(name, samples, widths, tops):
    """slice19.neck_audit with the R20 pads: each tie continuous and joining pad to part, pads clear of the part elsewhere."""
    _, flange, plan, section, record = anchors20.anchor(name); t = record['thickness_mm']; rows = []; necks = plan['necks']; joined = mf.CrossSection.batch_boolean(necks, mf.OpType.Add)
    layers = sorted({round(float(v), 3) for v in tops if 0 < v <= t + 1e-3}); worst_gap = 9.; counts = []
    for top in layers:
        sel = abs(tops - top) < 1e-3; beads = start_audit.bead_footprints(q, samples[sel, :2], widths[sel]); components = beads.decompose()
        for index, neck in enumerate(necks):
            b = neck.bounds(); best = None
            for off in (-.22, .22):
                pts = np.c_[np.linspace(b[0], b[2], 41), np.full(41, (b[1] + b[3]) / 2 + off)] if plan['axes'][index] == 'x' else np.c_[np.full(41, (b[0] + b[2]) / 2 + off), np.linspace(b[1], b[3], 41)]
                cov = float(q._inside(beads, pts).mean())
                if best is None or cov > best[0]: best = (cov, pts)
            covered, pts = best; ids = [i for i, c in enumerate(components) if q._inside(c, pts).sum() >= 30]
            assert covered >= .8 and len(ids) == 1, (name, top, index, covered, ids)
            comp = components[ids[0]]; assert (comp ^ section).area() > .5 and (comp ^ flange).area() > .5, (name, top, index, 'tie does not join pad and part')
            rows.append({'layer_top_mm': top, 'tie': index, 'centre_line_bead_coverage': round(covered, 4), 'tie_area_bead_fraction': round((beads ^ neck).area() / neck.area(), 4)})
        away = beads - joined.offset(.35, q.JoinType.Round); pad_beads = away ^ flange.offset(.3, q.JoinType.Round); part_beads = away ^ section.offset(.3, q.JoinType.Round); lo, hi = 0., 1.2
        assert (part_beads.offset(.01, q.JoinType.Round) ^ pad_beads).is_empty(), (name, top, 'pad bead touches part bead away from the ties')
        for _ in range(9):
            mid = (lo + hi) / 2; lo, hi = (mid, hi) if (part_beads.offset(mid, q.JoinType.Round) ^ pad_beads).is_empty() else (lo, mid)
        worst_gap = min(worst_gap, lo); printed = [c for c in pad_beads.decompose() if c.area() > 1.]; assert len(printed) == record['separate_pads'], (name, top, len(printed)); counts.append(len(printed))
    assert worst_gap >= .35, (name, worst_gap)
    return {'tie_count': len(necks), 'layers': layers, 'smallest_centre_line_bead_coverage': min(r['centre_line_bead_coverage'] for r in rows), 'smallest_pad_to_part_bead_gap_away_from_ties_mm': round(worst_gap, 3), 'designed_gap_mm': A['gap_mm'], 'separate_pads_printed_in_each_layer': counts, 'rows': rows}


def inspect(project_name='R20-A1-mini-PETG.gcode.3mf', out_dir=None, tag=''):
    out_dir = Path(out_dir) if out_dir else OUT; project = Path(project_name) if Path(project_name).is_absolute() else OUT / project_name
    manifest = json.loads((OUT / 'manifest.json').read_text()); data, features, stats, settings, offset, parts, gcode_text, config_text = s16.read_project(project)
    assert not any(f.startswith(('Support', 'Brim', 'Skirt')) for f in features), features
    slice_info = project19.slice_info_warnings(project); assert not slice_info, slice_info
    assert settings['timelapse_type'] == '1' and settings['enable_prime_tower'] == '1'
    tower = data[:, 5].astype(int) == features.index('Prime tower')
    assert int(tower.sum()) > 500, 'Smooth timelapse needs actual tower extrusion'
    tower_points = data[tower, :3] + offset
    tower_widths = data[tower, 3, None] / 2
    tower_lo = (tower_points[:, :2] - tower_widths).min(0)
    tower_hi = (tower_points[:, :2] + tower_widths).max(0)
    assert (tower_lo >= 0).all() and (tower_hi <= 180).all(), (tower_lo, tower_hi)
    # A rectangle around every actual tower bead also includes its native brim.
    # It must be separate from every functional object and its adhesion pads.
    extents = json.loads((OUT / 'R20-A1-mini-PETG-print-checks.json').read_text())['plate_extents_mm']
    tower_gaps = {}
    for name, (lo, hi) in extents.items():
        gap = np.maximum(np.maximum(np.array(lo[:2]) - tower_hi, tower_lo - np.array(hi[:2])), 0)
        tower_gaps[name] = round(float(np.linalg.norm(gap)), 3)
        assert tower_gaps[name] > 5, (name, 'tower too close to part or pads', gap)
    report = {'project_sha256': h.sha(project), 'manifest_sha256': h.sha(OUT / 'manifest.json'), 'anchors_sha256': h.sha(OUT / 'anchors.json'), 'checker_sha256': h.sha(Path(__file__)), 'r16_slice_helpers_sha256': h.sha(h.R16 / 'slice16.py'), 'parser_sha256': h.sha(Path(q.__file__)), 'start_auditor_sha256': h.sha(h.base.R15 / 'start_audit.py'),
              'features': features, 'parser_stats': stats, 'settings': {k: settings.get(k) for k in ['printer_settings_id', 'print_settings_id', 'filament_settings_id', 'layer_height', 'wall_loops', 'sparse_infill_density', 'enable_support', 'brim_type', 'nozzle_temperature', 'textured_plate_temp', 'initial_layer_speed', 'z_hop', 'elefant_foot_compensation']},
              'executable_commands': project19.command_audit(project, project19.settings()), 'slice_info_warnings': slice_info, 'parts': {}, 'physical_print_verified': False}
    report['timelapse_tower'] = {'mode': 'Smooth', 'path_samples': int(tower.sum()),
                               'actual_bead_bounds_xy_mm': [tower_lo.tolist(), tower_hi.tolist()],
                               'gap_to_part_and_pad_bounds_mm': tower_gaps,
                               'bed_size_mm': [180, 180]}
    images = {}; assembly = {}
    for name in h.PARTS:
        record = manifest['parts'][name]; info = parts[name]; expected = trimesh.load_mesh(OUT / (name + '-SOURCE-REQUIRES-PREPARATION.stl')); pad_file = trimesh.load_mesh(OUT / (name + '-ANCHOR-REMOVE-AFTER-PRINT.stl'))
        place = (info['vertices'].min(0) + info['vertices'].max(0) - expected.bounds.sum(0)) / 2; actual = q.solid(expected.vertices, expected.faces); in_project = q.solid(info['vertices'] - place, info['faces'])
        # Same triangles in the same order: compare vertices directly. A Boolean difference of two almost-coincident meshes is numerical noise.
        same_topology = info['faces'].shape == expected.faces.shape and bool((np.asarray(info['faces']) == np.asarray(expected.faces)).all())
        difference = float(np.abs(info['vertices'] - place - expected.vertices).max()) if same_topology else abs((actual - in_project).volume()) + abs((in_project - actual).volume())
        assert difference < (1e-4 if same_topology else .05) and abs(actual.volume() - in_project.volume()) < .01, (name, same_topology, difference)
        pad_solid = q.solid(pad_file.vertices, pad_file.faces); read_pad, title = slice19.anchor_in_project(project, name, place); pad_difference = abs((pad_solid - read_pad).volume()) + abs((read_pad - pad_solid).volume()); assert pad_difference < .05, (name, pad_difference)
        combined = actual + pad_solid; lo = np.minimum(expected.bounds[0], pad_file.bounds[0]); hi = np.maximum(expected.bounds[1], pad_file.bounds[1])
        local = data[:, :3] + offset - place; mask = np.all(local >= lo - .4, 1) & np.all(local <= hi + .4, 1)
        samples = local[mask]; w = data[mask, 3]; hh = data[mask, 4]; f = data[mask, 5].astype(int); tops = data[mask, 7]; assert len(samples) > 500, name
        pa = np.array(record['print_to_assembly']); to_print = np.linalg.inv(pa)
        _, flange, plan_, _, pad_record = anchors20.anchor(name); pad_plan = flange + mf.CrossSection.batch_boolean(plan_['necks'], mf.OpType.Add)
        is_pad = (tops <= pad_record['thickness_mm'] + 1e-3) & q._inside(pad_plan.offset(.3, q.JoinType.Round), samples[:, :2]); keep = ~is_pad
        assembly[name] = (q.points(samples[keep, :3], pa), w[keep])
        checks = {}; pad_checks = {}; regions = h.part_regions(name)
        for label, region in regions.items():
            if isinstance(region, h.spaces16.Swept):
                worst = None
                for pose in region.poses():
                    res = q.inspect_region(pose.transform(to_print[:3, :]), samples[keep], w[keep], hh[keep], f[keep], features, pa, limit=4)
                    if worst is None or sum(res['violations'].values()) > sum(worst['violations'].values()): worst = res
                checks[label] = {'checked_samples': worst['checked_samples'], 'violations': worst['violations'], 'poses': len(region)}
            else:
                res = q.inspect_region(region.transform(to_print[:3, :]), samples[keep], w[keep], hh[keep], f[keep], features, pa, limit=4); checks[label] = {'checked_samples': res['checked_samples'], 'violations': res['violations'], **({'examples': res['examples']} if res['violations'] else {})}
                if label.startswith(KEEP_CLEAR_OF_PADS):
                    res = q.inspect_region(region.transform(to_print[:3, :]), samples[is_pad], w[is_pad], hh[is_pad], f[is_pad], features, pa, limit=4); pad_checks[label] = {'checked_samples': res['checked_samples'], 'violations': res['violations']}
        bad = {k: (v['violations'], v.get('examples')) for k, v in {**checks, **{'pads:' + k: v for k, v in pad_checks.items()}}.items() if v['violations']}; assert not bad, (name, bad)
        starts = start_audit.inspect(q, combined, samples, hh, f, features, tops, pa, w); rows = starts['partial_overhangs']
        assert not starts['floating_components'] and not starts['missing_printed_components'], (name, starts['floating_components'][:3], starts['missing_printed_components'][:3])
        necks = neck_audit(name, samples, w, tops); s16.views(name, combined, samples, w, tops, rows, pa, images, out_dir, tag)
        report['parts'][name] = {'sliced_mesh_has_the_exported_triangles': same_topology, 'largest_vertex_difference_mm_or_volume_difference_mm3': difference, 'pad_mesh_difference_mm3': pad_difference, 'pad_part_label': title, 'path_samples': int(mask.sum()), 'pad_bead_samples': int(is_pad.sum()), 'working_spaces_checked': len(checks), 'working_space_checks': checks, 'pad_beads_against_keep_clear': pad_checks,
                                 'layer_starts': {k: v for k, v in starts.items() if k != 'partial_overhangs'}, 'partly_backed_layers': len(rows), 'largest_partly_backed_rows': sorted(rows, key=lambda r: -r.get('unbacked_mesh_area_mm2', 0))[:6], 'ties': necks}
        print(name, 'spaces', len(checks), 'violations', bad, 'floating', len(starts['floating_components']), 'missing', len(starts['missing_printed_components']), 'partly backed rows', len(rows), 'tie coverage', necks['smallest_centre_line_bead_coverage'], 'pad gap', necks['smallest_pad_to_part_bead_gap_away_from_ties_mm'], flush=True)
    solids = {n: h.read(OUT / (n + '-assembly.stl')) for n in h.PARTS}
    c = h.P['carrier_rings']; rod = h.ROD; cage = h.h19.CAGE; sensor = h.S
    rings = {
        'Key_Carrier': [('middle', c['mid_band_y_mm'], c['ring_width_mm'], rod['clip_root_wall'], True), ('rear', c['rear_band_y_mm'], c['ring_width_mm'], rod['clip_root_wall'], False)],
        'Battery_Holder': [('near', cage['near_band_y_mm'], rod['ring_width'], rod['clip_root_wall'], True), ('far', h.B20['far_band_y_mm'], rod['ring_width'], rod['clip_root_wall'], False)],
        'XIAO_Rod_Holder': [('near', sensor['near_band_y_mm'], sensor['clip_width_mm'], rod['sensor_clip_root_wall'], True), ('far', h.X20['far_ring_band_y_mm'], 3.6, rod['sensor_clip_root_wall'], False)]}
    report['strength'] = {'rings': {}, 'physical_strength_verified': False}
    for name, bands_ in rings.items():
        pts, widths = assembly[name]
        report['strength']['rings'][name] = {label: slice19.ring_entry(solids[name], pts, widths, *band, width, wall, skirted)
                                           for label, band, width, wall, skirted in bands_}
    # Guard rings face the opposite way. Mirror the solid and actual samples,
    # and choose rays within their wider 90-degree opening's remaining arc.
    pts, widths = assembly['Finger_Guard']; pts = pts * np.array([1, 1, -1]); solid = solids['Finger_Guard'].mirror((0, 0, 1))
    guard_rings = {}
    for label in ('front', 'rear'):
        band = h.G['ring'][label + '_band_y_mm']; yc = sum(band) / 2
        angles = (-35, 0, 90, 180, 215)
        sections = {str(a): round(s16.radial_section(solid, yc, a), 4) for a in angles}
        layer, tracks = s16.polar_tracks(pts, widths, yc, angles=angles)
        assert min(sections.values()) >= .95 and min(map(len, tracks.values())) >= 2, (label, sections, tracks)
        guard_rings[label] = {'band_y_mm': band, 'radial_STL_sections_mm': sections,
                              'sampled_layer_assembly_y_mm': layer, 'radial_track_centres_mm': tracks}
        if label == 'front': guard_rings[label]['band_start_backing'] = s16.band_start_backing(pts, widths, *band, +1, 'Guard front band')
    report['strength']['rings']['Finger_Guard'] = guard_rings
    # Whole-layer load paths, including the newly open wings, are checked in
    # every layer rather than inferring strength from a thick joint elsewhere.
    report['strength']['whole_sections'] = {}
    for name, yrange, window, area in (
            ('Battery_Holder', (-12.6, 14.), (-15, 15, 3., 12.5), 16.),
            ('XIAO_Rod_Holder', (-2.6, 21.), (-14.5, 14.5, -1., 15.), 13.),
            ('Finger_Guard', (-8., 8.4), (-31., 31., -9., 8.), 15.)):
        points, widths = assembly[name]
        report['strength']['whole_sections'][name] = s16.path_scan(solids[name], points, widths, yrange, window, name + ' complete section', area, .55,
                                                                 'Loads pass through the complete intervening printed section.', 'Digital material screen only; printed strength is unmeasured.')
    # Member by member, on actual beads: guard rims and rails, and every key-holder layer against R16 (see members20.py).
    import members20
    report['member_checker_sha256'] = h.sha(h.HERE / 'members20.py')
    report['strength']['members_actual_beads'] = members20.beads(assembly, q, start_audit.bead_footprints)
    recipe = project19.h.P['print']['local_recipe']; bands = {n: recipe.get(n + '_bands_mm', []) for n in ('Key_Carrier', 'Battery_Holder')}; actual_bands = s16.band_speeds(gcode_text, config_text, bands)
    limits = {'Outer wall': 'outer_wall_speed', 'Inner wall': 'inner_wall_speed', 'Gap infill': 'gap_infill_speed', 'Overhang wall': 'overhang_1_4_speed', 'Bridge': 'bridge_speed', 'Internal solid infill': 'internal_solid_infill_speed', 'Sparse infill': 'sparse_infill_speed', 'Top surface': 'top_surface_speed'}
    too_fast = [(p, z, feat, sp) for p, layers in actual_bands.items() for z, row in layers.items() for feat, sp in row['features_mm_s'].items() if limits.get(feat) and max(sp) > recipe['speeds_mm_s'][limits[feat]] + .5]
    assert actual_bands and not too_fast, too_fast[:4]
    report['slow_bands'] = {'bands_mm': bands, 'requested_speeds_mm_s': recipe['speeds_mm_s'], 'actual_in_bands': actual_bands}; report['images_sha256'] = images; report['passed'] = True
    (out_dir / f'slice-clearances{tag}.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Sliced meshes match; no support or brim; every working space clear; no floating start; every tie continuous.', flush=True)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--project', default='R20-A1-mini-PETG.gcode.3mf'); a = p.parse_args()
    inspect(a.project)
