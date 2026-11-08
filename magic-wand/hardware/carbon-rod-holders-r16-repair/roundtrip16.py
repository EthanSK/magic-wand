#!/usr/bin/env python3
"""Reload and re-slice the exact delivered R16 project offline; compare with the registered receipts.

Input: the delivered `exports/R16-A1-mini-PETG.gcode.3mf` itself, never the layout archive. The
Bambu Studio CLI re-reads that archive with a process-private HOME/CFFIXED_USER_HOME and a
--datadir/TMPDIR inside task scratch, slices it again and exports a new gcode.3mf into scratch.
The re-sliced archive must still carry the registered normal meshes, the same effective plate
settings and modifier-part settings, and its actual G-code must pass the same slice16 audit
with the same functional results (working spaces, layer starts, band speeds and fan, ring
sections and tracks, path scans). GUI reopening is not available in this offline, headless
environment; this CLI reload of the delivered archive is the roundtrip that was performed.
"""
import argparse, json, os, re, subprocess, zipfile, xml.etree.ElementTree as E
from pathlib import Path
import numpy as np
import holder16 as h
import project16, slice16

OUT = h.HERE / 'exports'


def modifier_settings(model_settings_text):
    """{object name: {modifier part name: {key: value}}} for every modifier part."""
    root = E.fromstring(model_settings_text); out = {}
    for obj in root.findall('object'):
        name = next(m.get('value') for m in obj.findall('metadata') if m.get('key') == 'name')
        parts = {}
        for part in obj.findall('part'):
            if part.get('subtype') != 'modifier_part': continue
            meta = {m.get('key'): m.get('value') for m in part.findall('metadata')}
            parts[meta.pop('name')] = meta
        out[name] = parts
    return out


def effective_modifier_placement(project):
    """World-frame bounds of every modifier part in a 3MF, from its mesh vertices, its component
    transform and the build item transform (what the slicer actually uses), keyed by object name."""
    q = slice16.q; N = slice16.N
    with zipfile.ZipFile(project) as z:
        cfg = E.fromstring(z.read('Metadata/model_settings.config'))
        model = E.fromstring(z.read('3D/3dmodel.model')); cache = {'3D/3dmodel.model': model}
        roots = {o.get('id'): o for o in model.findall('m:resources/m:object', N)}
        builds = {i.get('objectid'): q.transform(i.get('transform')) for i in model.findall('m:build/m:item', N)}
        out = {}
        for obj in cfg.findall('object'):
            name = q.metadata(obj)['name']; rows = {}
            for part in obj.findall('part'):
                if part.get('subtype') != 'modifier_part': continue
                title = q.metadata(part)['name']
                comp = next(c for c in roots[obj.get('id')].findall('m:components/m:component', N) if c.get('objectid') == part.get('id'))
                path = next((v.lstrip('/') for k, v in comp.attrib.items() if k.endswith('}path')), '3D/3dmodel.model')
                if path not in cache: cache[path] = E.fromstring(z.read(path))
                child = next(o for o in cache[path].findall('m:resources/m:object', N) if o.get('id') == part.get('id'))
                vv = np.array([[float(v.get(k)) for k in 'xyz'] for v in child.findall('m:mesh/m:vertices/m:vertex', N)])
                vv = q.points(q.points(vv, q.transform(comp.get('transform'))), builds[obj.get('id')])
                rows[title] = {'world_bounds_mm': [np.round(vv.min(0), 4).tolist(), np.round(vv.max(0), 4).tolist()], 'component_transform': comp.get('transform'), 'matrix_metadata': q.metadata(part).get('matrix')}
            out[name] = rows
    return out


def archive_settings(project):
    with zipfile.ZipFile(project) as z:
        return json.loads(z.read('Metadata/project_settings.config')), z.read('Metadata/model_settings.config').decode(), z.read('Metadata/plate_1.gcode').decode()


def normalized_gcode(text):
    """Drop header/footer comment lines that carry times, dates or tool versions; keep every move and marker."""
    volatile = re.compile(r'^;\s*(generated|.*time|.*date|.*estimated|HEADER_BLOCK|EXECUTABLE_BLOCK|CONFIG_BLOCK|.*_version)', re.I)
    return '\n'.join(line for line in text.splitlines() if not (line.startswith(';') and volatile.match(line)))


def functional_summary(audit):
    """Functional and critical numbers of a slice16 audit, free of hashes and image digests."""
    parts = {name: {'violations': {k: v['violations'] for k, v in p['checks'].items()},
                    'floating': len(p['layer_starts']['floating_components']), 'missing': len(p['layer_starts']['missing_printed_components']),
                    'unclassified': len(p['unclassified_overhangs']), 'partial_rows': len(p['partial_overhangs']), 'path_samples': p['path_samples'],
                    'special_features': {k: v['samples'] for k, v in p['special_features'].items()}}
             for name, p in audit['parts'].items()}
    rings = {f'{part}:{label}': {'bonded': r['arm_bonding']['crown_bonded_down_to_degrees_above_equator'],
                                 'backing': r.get('band_start_backing', {}).get('directly_backed_fraction'),
                                 'skirt_tracks': r.get('lead_in_skirt', {}).get('minimum_track_count'),
                                 'radial_sections': r['radial_STL_sections_mm'], 'tracks': {k: len(v) for k, v in r['radial_track_centres_mm'].items()}}
             for part, rr in audit['strength']['rings'].items() for label, r in rr.items()}
    scans = {f'{part}:{s["feature"]}': {'mesh_min_mm2': s['minimum_mesh_section_mm2'], 'printed_min_mm2': s['minimum_printed_area_mm2'],
                                        'printed_fraction': s['minimum_printed_fraction'], 'layers': s['layers_scanned']}
             for part, ss in audit['strength']['path_scans'].items() for s in ss}
    fixed = {f'{part}:{f["feature"]}': {k: f.get(k) for k in ['minimum_sampled_section_mm', 'minimum_sampled_track_count', 'printed_fraction', 'mesh_section_area_mm2']}
             for part, ff in audit['strength']['fixed_features'].items() for f in ff}
    recipe = audit['band_recipe_actual']
    return {'parts': parts, 'rings': rings, 'path_scans': scans, 'fixed_features': fixed, 'features': audit['features'],
            'band_actual': recipe['actual_in_bands'], 'band_fan_lengths': recipe['band_feature_length_mm_by_fan'],
            'too_fast': recipe['features_faster_than_requested'], 'settings': audit['settings']}


def differences(a, b, path=''):
    """Leaf-level differences between two JSON-like structures."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b: out.append((path + '/' + str(k), a.get(k, '<missing>'), b.get(k, '<missing>')))
            else: out += differences(a[k], b[k], path + '/' + str(k))
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)): out += differences(x, y, f'{path}[{i}]')
    elif a != b:
        out.append((path, a, b))
    return out


def run(scratch, timeout):
    printed = json.loads((OUT / 'R16-A1-mini-PETG-print-checks.json').read_text())
    project = OUT / printed['sliced_project_filename']; project_sha = h.sha(project)
    assert project_sha == printed['sliced_project_sha256'], 'The delivered project is not the registered one'
    registered = json.loads((OUT / 'slice-clearances.json').read_text())
    assert registered['project_sha256'] == project_sha, 'slice-clearances.json does not audit the delivered project'
    work = scratch.resolve() / 'roundtrip'
    for sub in ['tmp', 'data', 'home/Library/Preferences', 'out']: (work / sub).mkdir(parents=True, exist_ok=True)
    for stale in (work / 'out').glob('*'): stale.unlink()
    source = work / 'delivered-input.gcode.3mf'; source.write_bytes(project.read_bytes())  # the delivered file is only read
    target = 'resliced.gcode.3mf'
    cmd = [str(project16.BAMBU), '--datadir', str(work / 'data'), '--debug', '2', '--orient', '0', '--arrange', '0',
           '--slice', '0', '--export-3mf', target, '--outputdir', str(work / 'out'), str(source)]
    env = {**os.environ, 'TMPDIR': str(work / 'tmp'), 'HOME': str(work / 'home'), 'CFFIXED_USER_HOME': str(work / 'home')}
    with (work / 'reslice.log').open('w') as log:
        proc = subprocess.run(cmd, cwd=work, stdout=log, stderr=subprocess.STDOUT, env=env, timeout=timeout)
    log_text = (work / 'reslice.log').read_text()
    # The CLI writes result.json beside its exports (--outputdir), not in the working directory.
    result_path = next((p for p in [work / 'out' / 'result.json', work / 'result.json'] if p.exists()), None)
    result = json.loads(result_path.read_text()) if result_path else {}
    assert proc.returncode == 0 and result.get('return_code') == 0, ('Re-slice failed', proc.returncode, result)
    resliced = work / 'out' / target; assert resliced.exists(), 'No re-sliced archive'
    version = re.search(r'BambuStudio Version (\S+)', log_text)
    # 1. Settings and modifiers survive the reload.
    in_cfg, in_model, in_gcode = archive_settings(project); out_cfg, out_model, out_gcode = archive_settings(resliced)
    keys = sorted(set(project16.OVERRIDES) | {'printer_settings_id', 'print_settings_id', 'filament_settings_id', 'nozzle_temperature', 'textured_plate_temp',
                                              'enable_support', 'brim_type', 'initial_layer_speed', 'overhang_fan_speed', 'fan_min_speed', 'fan_max_speed',
                                              'fan_cooling_layer_time', 'slow_down_layer_time', 'slow_down_min_speed', 'bridge_speed', 'enable_overhang_speed'})
    settings_same = {k: json.dumps(in_cfg.get(k)) == json.dumps(out_cfg.get(k)) for k in keys}
    mods_in, mods_out = modifier_settings(in_model), modifier_settings(out_model)

    def same_modifier_settings(a, b):
        """Same modifier parts with the same settings. The CLI rewrites the `matrix` metadata on
        export (it stores the composite placement), so placement is checked from the meshes below."""
        if set(a) != set(b): return False
        for obj in a:
            if set(a[obj]) != set(b[obj]): return False
            for part in a[obj]:
                x, y = dict(a[obj][part]), dict(b[obj][part]); x.pop('matrix', None); y.pop('matrix', None)
                if x != y: return False
        return True
    place_in, place_out = effective_modifier_placement(project), effective_modifier_placement(resliced)
    recipe = h.P['print']['local_recipe']
    placement_rows = {}
    for name, rows in place_in.items():
        bands = recipe.get(name + '_bands_mm', [])
        for title, row in rows.items():
            z0, z1 = row['world_bounds_mm'][0][2], row['world_bounds_mm'][1][2]
            band = next((b for b in bands if abs(z0 - max(0., b[0] - .3)) < .05 and abs(z1 - (b[1] + .3)) < .05), None)
            other = place_out.get(name, {}).get(title)
            same = other is not None and np.allclose(np.array(row['world_bounds_mm']), np.array(other['world_bounds_mm']), atol=.05)
            placement_rows[f'{name}: {title}'] = {'delivered_world_z_mm': [round(z0, 3), round(z1, 3)], 'matches_recipe_band_mm': band, 'resliced_world_bounds_equal': bool(same),
                                                 'delivered_matrix_metadata': row['matrix_metadata'], 'resliced_matrix_metadata': other['matrix_metadata'] if other else None}
    placement_ok = bool(placement_rows) and all(r['matches_recipe_band_mm'] is not None and r['resliced_world_bounds_equal'] for r in placement_rows.values()) \
        and sum(len(v) for v in place_out.values()) == sum(len(v) for v in place_in.values())
    modifiers_identical = same_modifier_settings(mods_in, mods_out) and placement_ok
    # 2. Meshes: the re-sliced archive's part meshes against the delivered ones (slice16 checks them against the registered normal STLs).
    _, _, _, _, _, parts_in, _, _ = slice16.read_project(project)
    _, _, _, _, _, parts_out, _, _ = slice16.read_project(resliced)
    meshes_same = {name: bool(parts_in[name]['vertices'].shape == parts_out[name]['vertices'].shape and np.allclose(parts_in[name]['vertices'], parts_out[name]['vertices'], atol=1e-5)
                              and np.array_equal(parts_in[name]['faces'], parts_out[name]['faces'])) for name in parts_in}
    # 3. The same audit on the re-sliced G-code, against the same registered normal STLs, written to scratch.
    audit = slice16.inspect(resliced, out_dir=work / 'out', tag='-roundtrip')
    summary_registered, summary_resliced = functional_summary(registered), functional_summary(audit)
    diffs = differences(summary_registered, summary_resliced)
    gcode_identical = normalized_gcode(in_gcode) == normalized_gcode(out_gcode)

    def speeds_and_fans(band_actual):
        return {part: {z: {'features_mm_s': row['features_mm_s'], 'fan_M106_0_255': row['fan_M106_0_255']} for z, row in layers.items()} for part, layers in band_actual.items()}

    def lengths_close(a, b, rel=.02, abs_mm=.5):
        for part in set(a) | set(b):
            for feat in set(a.get(part, {})) | set(b.get(part, {})):
                for fan in set(a.get(part, {}).get(feat, {})) | set(b.get(part, {}).get(feat, {})):
                    x = a.get(part, {}).get(feat, {}).get(fan, 0.); y = b.get(part, {}).get(feat, {}).get(fan, 0.)
                    if abs(x - y) > max(abs_mm, rel * max(x, y)): return False
        return True
    # Functional equivalence: identical working-space results, layer-start results, features, band
    # speeds and fan levels, ring bonding and backing; path-scan minima and band path lengths within 2 %.
    equivalent = (audit['passed'] and not summary_resliced['too_fast'] and summary_resliced['features'] == summary_registered['features']
                  and speeds_and_fans(summary_resliced['band_actual']) == speeds_and_fans(summary_registered['band_actual'])
                  and lengths_close(summary_registered['band_fan_lengths'], summary_resliced['band_fan_lengths'])
                  and all(summary_resliced['parts'][n]['violations'] == summary_registered['parts'][n]['violations'] and summary_resliced['parts'][n]['floating'] == 0
                          and summary_resliced['parts'][n]['missing'] == 0 and summary_resliced['parts'][n]['unclassified'] == 0
                          and summary_resliced['parts'][n]['partial_rows'] == summary_registered['parts'][n]['partial_rows'] for n in summary_registered['parts'])
                  and all(abs(summary_resliced['path_scans'][k]['printed_min_mm2'] - v['printed_min_mm2']) <= .02 * max(v['printed_min_mm2'], 1e-9)
                          and abs(summary_resliced['path_scans'][k]['mesh_min_mm2'] - v['mesh_min_mm2']) <= 1e-6 for k, v in summary_registered['path_scans'].items())
                  and all(summary_resliced['rings'][k]['bonded'] == v['bonded'] and summary_resliced['rings'][k]['tracks'] == v['tracks']
                          and (v['backing'] is None or abs(summary_resliced['rings'][k]['backing'] - v['backing']) <= .01) for k, v in summary_registered['rings'].items())
                  and summary_resliced['settings'] == summary_registered['settings'])
    report = {'generator_sha256': h.sha(Path(__file__)), 'slice_checker_sha256': h.sha(h.HERE / 'slice16.py'),
              'input_project': project.name, 'input_project_sha256': project_sha, 'registered_slice_audit_sha256': h.sha(OUT / 'slice-clearances.json'),
              'input_is_layout_archive': False, 'resliced_project_sha256': h.sha(resliced), 'resliced_audit_sha256': h.sha(work / 'out' / 'slice-clearances-roundtrip.json'),
              'resliced_artifacts_kept_in_task_scratch_only': True, 'bambu_studio_version': version.group(1) if version else None,
              'cli_launch': 'offline CLI reload of the delivered gcode.3mf with --datadir and TMPDIR in task scratch and a process-private HOME/CFFIXED_USER_HOME; cwd in scratch; bounded subprocess timeout',
              'timeout_seconds': timeout, 'slicer_result': {k: result.get(k) for k in ['return_code', 'error_string']}, 'slicer_warnings': [p.get('warning_message') for p in result.get('sliced_plates', []) if p.get('warning_message')],
              'effective_settings_identical': settings_same, 'modifier_parts_input': mods_in, 'modifier_parts_resliced': mods_out, 'modifier_parts_identical': modifiers_identical,
              'modifier_effective_placement': placement_rows,
              'modifier_placement_note': 'Placement is taken from each archive\'s modifier mesh vertices through the component and build transforms (what the slicer uses); the CLI\'s matrix metadata is rewritten as a composite on export and is recorded, not compared.',
              'part_meshes_identical': meshes_same, 'normalized_gcode_identical': gcode_identical,
              'equivalence_rule': 'identical working-space, layer-start, feature-list, band speed/fan, ring bonding/track and settings results; path-scan printed minima and band path lengths within 2 % (the CLI rewrites mesh floats on export, so toolpaths may differ by a few samples)',
              'functional_summary_identical': not diffs, 'functional_differences': [{'path': p, 'registered': a, 'resliced': b} for p, a, b in diffs[:200]],
              'functional_summary_equivalent': bool(equivalent), 'resliced_audit_passed': bool(audit['passed']),
              'gui_reopen': 'not available: offline headless environment; the roundtrip performed is the CLI reload and re-slice of the delivered archive',
              'physical_print_verified': False}
    report['passed'] = bool(all(settings_same.values()) and report['modifier_parts_identical'] and all(meshes_same.values()) and equivalent and not report['slicer_warnings'])
    (OUT / 'roundtrip-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['passed', 'normalized_gcode_identical', 'functional_summary_identical', 'functional_summary_equivalent', 'modifier_parts_identical', 'part_meshes_identical']}), flush=True)
    if diffs: print('DIFFS', json.dumps(report['functional_differences'][:12]), flush=True)
    assert report['passed'], 'See roundtrip-checks.json'


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--scratch', type=Path, required=True); p.add_argument('--timeout', type=int, default=300)
    a = p.parse_args(); run(a.scratch, a.timeout)
