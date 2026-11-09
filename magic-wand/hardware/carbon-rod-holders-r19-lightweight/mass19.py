#!/usr/bin/env python3
"""R18 against R19 under one recipe: solid CAD and actual sliced extrusion, per object.

Sliced figures are extrusion moves in the shipped G-code, assigned to each object's plan area. Tear-off pads
and purge are kept apart from installed holder mass, and each total is reconciled against the slicer's own weight.
Sparse infill and wall overlap are as sliced, so this is plastic laid down, not a weighed part.
"""
import json, math, re, sys, zipfile, xml.etree.ElementTree as E
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf
import holder19 as h
import anchors19
import slice16 as s16
import anchors18

q = s16.q; OUT = h.HERE / 'exports'; R18 = h.h18.HERE / 'exports'; DIAMETER = 1.75
SAME_RECIPE = ['layer_height', 'initial_layer_print_height', 'wall_loops', 'sparse_infill_density', 'sparse_infill_pattern', 'nozzle_temperature', 'textured_plate_temp', 'filament_density', 'filament_flow_ratio', 'filament_settings_id', 'print_settings_id', 'printer_settings_id', 'z_hop', 'z_hop_types', 'enable_support', 'brim_type']


def extrusions(text):
    """Every printing move: (x, y, z, filament mm). Retractions, primes and wipes with no forward extrusion over XY are excluded."""
    x = y = z = 0.; rows = []; retract_unprime = 0.
    for line in text.splitlines():
        if not line or line[0] != 'G' or line[:3] not in ('G0 ', 'G1 ', 'G2 ', 'G3 '): continue
        code = line.split(';')[0]; args = dict((m[0], float(m[1])) for m in re.findall(r'([XYZEIJ])(-?\d*\.?\d+)', code)); nx, ny = args.get('X', x), args.get('Y', y); z = args.get('Z', z); e = args.get('E', 0.)
        moved = abs(nx - x) + abs(ny - y) > 1e-6 or 'I' in args or 'J' in args
        if e > 0 and moved: rows.append(((x + nx) / 2, (y + ny) / 2, z, e))
        elif e: retract_unprime += e
        x, y = nx, ny
    return np.array(rows), retract_unprime


def audit(label, project, exports, plate, anchor_module):
    data, features, stats, settings, offset, parts, gcode_text, config_text = s16.read_project(project); moves, retract = extrusions(gcode_text)
    with zipfile.ZipFile(project) as z:
        cfg = json.loads(z.read('Metadata/project_settings.config')); info = E.fromstring(z.read('Metadata/slice_info.config'))
    density = float(cfg['filament_density'][0]); area = math.pi * (DIAMETER / 2) ** 2; to_g = area * density / 1000
    slicer_g = sum(float(m.get('value')) for p in info.iter('plate') for m in p.findall('metadata') if m.get('key') == 'weight'); time_s = sum(float(m.get('value')) for p in info.iter('plate') for m in p.findall('metadata') if m.get('key') == 'prediction')
    used = np.zeros(len(moves), bool); rows = {}; manifest = json.loads((exports / 'manifest.json').read_text())
    for name in plate:
        expected = trimesh.load_mesh(exports / (name + '-SOURCE-REQUIRES-PREPARATION.stl')); place = (parts[name]['vertices'].min(0) + parts[name]['vertices'].max(0) - expected.bounds.sum(0)) / 2; lows = [expected.bounds[0]]; highs = [expected.bounds[1]]
        anchored = name in anchor_module.h.ANCHORED
        if anchored:
            a = trimesh.load_mesh(exports / (name + '-ANCHOR-REMOVE-AFTER-PRINT.stl')); lows.append(a.bounds[0]); highs.append(a.bounds[1])
        lo = np.min(lows, axis=0); hi = np.max(highs, axis=0); local = moves[:, :2] + offset[:2] - place[:2]
        inside = (local[:, 0] >= lo[0] - .5) & (local[:, 0] <= hi[0] + .5) & (local[:, 1] >= lo[1] - .5) & (local[:, 1] <= hi[1] + .5) & (moves[:, 2] <= hi[2] + .3); assert not (inside & used).any(), (label, name, 'plan boxes overlap')
        used |= inside; helper = np.zeros(len(moves), bool)
        if anchored:
            _, flange, plan_, _, record = anchor_module.anchor(name); shape = (flange + mf.CrossSection.batch_boolean(plan_['necks'], mf.OpType.Add)).offset(.3, q.JoinType.Round); idx = np.where(inside & (moves[:, 2] <= record['thickness_mm'] + .01))[0]
            if len(idx): helper[idx[q._inside(shape, local[idx])]] = True
        part_mm = float(moves[inside & ~helper, 3].sum()); helper_mm = float(moves[helper, 3].sum())
        rows[name] = {'cad_solid_volume_mm3': round(manifest['parts'][name]['volume_mm3'], 1), 'cad_solid_g': round(manifest['parts'][name]['solid_PETG_g'], 3), 'sliced_object_g': round(part_mm * to_g, 3), 'sliced_tear_off_pads_and_ties_g': round(helper_mm * to_g, 3), 'extrusion_moves': int((inside & ~helper).sum())}
    purge = float(moves[~used, 3].sum()) * to_g; total = float(moves[:, 3].sum()) * to_g
    return {'project_sha256': h.sha(project), 'objects': rows, 'purge_and_unassigned_extrusion_g': round(purge, 3), 'all_extrusion_moves_g': round(total, 3), 'slicer_reported_weight_g': round(slicer_g, 3), 'difference_extrusion_minus_slicer_g': round(total - slicer_g, 3), 'slicer_prediction_s': round(time_s, 1), 'density_g_cm3': density, 'retract_and_unprime_excluded_mm': round(retract, 2)}, cfg


def holders(r):
    b, x = r['objects']['Battery_Holder'], r['objects']['XIAO_Rod_Holder']
    return {'Battery_Holder_g': b['sliced_object_g'], 'XIAO_Rod_Holder_g': x['sliced_object_g'], 'both_holders_g': round(b['sliced_object_g'] + x['sliced_object_g'], 3), 'Battery_Holder_CAD_g': b['cad_solid_g'], 'XIAO_Rod_Holder_CAD_g': x['cad_solid_g'], 'both_holders_CAD_g': round(b['cad_solid_g'] + x['cad_solid_g'], 3)}


def percent(old, new): return round((new - old) / old * 100, 1)


def main():
    r18, c18 = audit('R18', R18 / 'R18-A1-mini-PETG.gcode.3mf', R18, h.PLATE, anchors18); r19, c19 = audit('R19', OUT / 'R19-A1-mini-PETG.gcode.3mf', OUT, h.PLATE, anchors19)
    differing = {k: (c18.get(k), c19.get(k)) for k in SAME_RECIPE if json.dumps(c18.get(k)) != json.dumps(c19.get(k))}; assert not differing, differing
    a, b = holders(r18), holders(r19); saved = {k: {'r18_g': a[k], 'r19_g': b[k], 'difference_g': round(b[k] - a[k], 3), 'percent': percent(a[k], b[k])} for k in a}
    others = {n: (r18['objects'][n]['sliced_object_g'], r19['objects'][n]['sliced_object_g']) for n in h.PLATE if n not in h.NEW_PARTS}
    closure = max(abs(r18['difference_extrusion_minus_slicer_g']), abs(r19['difference_extrusion_minus_slicer_g']))
    result = {'generator_sha256': h.sha(h.HERE / 'mass19.py'), 'same_recipe_keys_compared': SAME_RECIPE, 'recipe_differences': differing, 'R18': r18, 'R19': r19, 'holder_comparison_excluding_pads_and_ties': saved, 'door_keeper_spacers_sliced_g_r18_r19': others,
              'tear_off_pads_and_ties_g_not_installed': {'R18': {n: r18['objects'][n]['sliced_tear_off_pads_and_ties_g'] for n in h.ANCHORED}, 'R19': {n: r19['objects'][n]['sliced_tear_off_pads_and_ties_g'] for n in h.ANCHORED}},
              'closure_note': f'Assigned moves plus purge equal all extrusion moves by construction. Against the slicer weight the largest difference is {closure:.3f} g, which also covers filament-change and prime moves outside the extrusion parser.',
              'limit': 'Sliced grams come from filament fed, not from weighing a printed part. Tear-off pads and ties are excluded from holder mass; the stub left after snipping a tie is not counted.'}
    (OUT / 'mass-comparison.json').write_text(json.dumps(result, indent=2) + '\n'); print(json.dumps({'holders': saved, 'pads': result['tear_off_pads_and_ties_g_not_installed'], 'others': others, 'purge': (r18['purge_and_unassigned_extrusion_g'], r19['purge_and_unassigned_extrusion_g']), 'closure': (r18['difference_extrusion_minus_slicer_g'], r19['difference_extrusion_minus_slicer_g']), 'slicer_g_s': (r18['slicer_reported_weight_g'], r19['slicer_reported_weight_g'], r18['slicer_prediction_s'], r19['slicer_prediction_s'])}), flush=True)


if __name__ == '__main__':
    main()
