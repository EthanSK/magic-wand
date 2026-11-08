#!/usr/bin/env python3
"""Build and slice the R16 Bambu A1 mini / Generic PETG project from the exact final STLs.

Reuses the shared Shard layout builder for the 3MF skeleton, then embeds the resolved A1 mini
machine/process/filament profile from the installed Bambu Studio (the same resolution used for
the actual R15 A1 mini print), with this revision's overrides. No automatic supports, no brim,
no CAD print helpers. The CLI slice runs from an explicit scratch directory so its result.json
never lands in the repository.
"""
from pathlib import Path
import argparse, json, os, shutil, subprocess, zipfile, xml.etree.ElementTree as E
import numpy as np, trimesh
import holder16 as h
E.register_namespace('', 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02')

BUILDER = h.HERE.parent / 'printed-loop-wand/shard-tube-r2'
BAMBU = Path('/Applications/BambuStudio.app/Contents/MacOS/BambuStudio')
PROFILES = Path('/Applications/BambuStudio.app/Contents/Resources/profiles/BBL')
OVERRIDES = dict(wall_loops='3', sparse_infill_density='20%', layer_height='0.2', initial_layer_print_height='0.2',
                 enable_support='0', brim_type='no_brim', enable_prime_tower='0', print_sequence='by layer',
                 bridge_no_support='1', max_bridge_length='12', initial_layer_speed=['20'], initial_layer_infill_speed=['30'])
META = {'name', 'inherits', 'type', 'from', 'version', 'setting_id', 'instantiation', 'description', 'compatible_printers', 'compatible_printers_condition'}


def resolve(kind, name):
    data = json.loads((PROFILES / kind / (name + '.json')).read_text())
    parent = data.get('inherits', '')
    result = resolve(kind, parent) if parent else {}
    result.update(data)
    return result


def a1_mini_settings():
    p = h.P['print']
    machine = resolve('machine', p['printer']); process = resolve('process', p['process']); filament = resolve('filament', p['filament'])
    cfg = {}
    for d in (machine, process, filament):
        cfg.update({k: v for k, v in d.items() if k not in META})
    cfg.update(printer_settings_id=machine['name'], print_settings_id=process['name'], filament_settings_id=[filament['name']],
               filament_ids=['GFG99'], filament_colour=['#057748'], curr_bed_type='Textured PEI Plate')
    cfg.update(OVERRIDES)
    diff = cfg.get('different_settings_to_system', ['', '', ''])
    diff[0] = ';'.join(sorted(set(filter(None, diff[0].split(';'))) | set(OVERRIDES)))
    cfg['different_settings_to_system'] = diff
    for key in ['nozzle_temperature', 'nozzle_temperature_initial_layer', 'textured_plate_temp', 'textured_plate_temp_initial_layer']:
        cfg.setdefault(key, None)
    return cfg


def layout(names, centres, dest, manifest, settings):
    builder = h.r15.load('print_projects', BUILDER)
    builder.settings = lambda: settings
    parts = []
    for name in names:
        record = manifest['parts'][name]
        mesh = trimesh.load_mesh(h.HERE / 'exports' / (name + '-SOURCE-REQUIRES-PREPARATION.stl'))
        mesh.apply_transform(np.array(record['print_to_assembly']))
        parts.append(dict(name=name, **record, assembly_vertices=mesh.vertices.tolist(), assembly_faces=mesh.faces.tolist()))
    dest.unlink(missing_ok=True)
    builder.make(names, centres, dest, {'parts': parts})
    with zipfile.ZipFile(dest) as z:
        files = {n: z.read(n) for n in z.namelist()}
    config = E.fromstring(files['Metadata/model_settings.config']); model = E.fromstring(files['3D/3dmodel.model'])
    modifiers = add_band_modifiers(model, config, names, centres, manifest)
    files['3D/3dmodel.model'] = E.tostring(model, encoding='utf-8', xml_declaration=True)
    for obj in config.findall('object'):
        meta = {m.get('key'): m for m in obj.findall('metadata')}
        meta['enable_support'].set('value', '0')
        for k, v in OVERRIDES.items():
            if k not in ('enable_support', 'print_sequence', 'enable_prime_tower') and not isinstance(v, list):
                E.SubElement(obj, 'metadata', key=k, value=v)
    for plate in config.findall('plate'):
        for item in plate.findall('metadata'):
            if item.get('key') == 'plater_name': item.set('value', 'Magic Wand R16 repair - A1 mini PETG')
    files['Metadata/model_settings.config'] = E.tostring(config, encoding='utf-8', xml_declaration=True)
    files['Metadata/project_settings.config'] = json.dumps(settings, indent=2).encode()
    with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, d in files.items(): z.writestr(n, d)
    # Bed check: the A1 mini plate is 180 x 180 mm.
    with zipfile.ZipFile(dest) as z:
        model = E.fromstring(z.read('3D/3dmodel.model'))
    ns = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
    bounds = {}
    for item in model.findall('m:build/m:item', ns):
        t = np.array([float(v) for v in item.get('transform').split()]).reshape(4, 3)
        obj = next(o for o in model.findall('m:resources/m:object', ns) if o.get('id') == item.get('objectid'))
        child = obj.find('m:components/m:component', ns).get('objectid')
        mesh_obj = next(o for o in model.findall('m:resources/m:object', ns) if o.get('id') == child)
        vv = np.array([[float(v.get(k)) for k in 'xyz'] for v in mesh_obj.findall('m:mesh/m:vertices/m:vertex', ns)]) @ t[:3] + t[3]
        name = mesh_obj.get('name'); bounds[name] = [vv.min(0).tolist(), vv.max(0).tolist()]
        assert vv.min(0)[0] >= 8 and vv.min(0)[1] >= 8 and vv.max(0)[0] <= 172 and vv.max(0)[1] <= 172 and vv.min(0)[2] > -.001, (name, vv.min(0), vv.max(0))
    return bounds, modifiers


def add_band_modifiers(model, config, names, centres, manifest):
    """Bambu modifier parts over the bay-roof and gate-cap bands carrying the local recipe speeds.

    A modifier volume is the slicer's own mechanism for region settings and travels inside the
    3MF model (the installed CLI hangs on a separate layer_config_ranges.xml). Each modifier is
    a box in the part's print frame spanning its XY bounds over one print-height band; only the
    recipe speeds are set, everything else stays at the profile. slice16.py reads the actual
    G-code speeds back.
    """
    ns = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'; tag = lambda s: '{' + ns + '}' + s
    resources = model.find(tag('resources')); recipe = h.P['print']['local_recipe']
    ident = max(int(o.get('id')) for o in resources.findall(tag('object'))) + 100
    added = {}
    for obj in config.findall('object'):
        name = next(m.get('value') for m in obj.findall('metadata') if m.get('key') == 'name')
        bands = recipe.get(name + '_bands_mm', [])
        if not bands: continue
        mesh = trimesh.load_mesh(h.HERE / 'exports' / (name + '-SOURCE-REQUIRES-PREPARATION.stl')); lo, hi = mesh.bounds
        parent = next(o for o in resources.findall(tag('object')) if o.get('id') == obj.get('id'))
        for z0, z1 in bands:
            ident += 1
            # The slicer assigns a layer to a modifier by the layer's middle; extend the box 0.3 mm past
            # the requested band so every layer whose middle lies in the band is fully inside it.
            b0, b1 = max(0., z0 - .3), z1 + .3
            box = trimesh.creation.box(extents=(hi[0] - lo[0] + 2, hi[1] - lo[1] + 2, b1 - b0))
            box.apply_translation(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (b0 + b1) / 2))
            title = f'SLOW BAND {z0:g}-{z1:g} mm - modifier, not printed'
            child = E.SubElement(resources, tag('object'), id=str(ident), type='model', name=title)
            m = E.SubElement(child, tag('mesh')); vs = E.SubElement(m, tag('vertices')); ts = E.SubElement(m, tag('triangles'))
            for v in box.vertices: E.SubElement(vs, tag('vertex'), **{k: format(float(t), '.9g') for k, t in zip('xyz', v)})
            for f in box.faces: E.SubElement(ts, tag('triangle'), v1=str(f[0]), v2=str(f[1]), v3=str(f[2]))
            E.SubElement(parent.find(tag('components')), tag('component'), objectid=str(ident))
            part = E.SubElement(obj, 'part', id=str(ident), subtype='modifier_part')
            E.SubElement(part, 'metadata', key='name', value=title)
            for key, value in recipe['speeds_mm_s'].items():
                E.SubElement(part, 'metadata', key=key, value=str(value))
            if recipe.get('band_wall_loops'):
                E.SubElement(part, 'metadata', key='wall_loops', value=str(recipe['band_wall_loops']))
            added.setdefault(name, []).append({'band_mm': [z0, z1], 'modifier_id': ident, 'speeds_mm_s': recipe['speeds_mm_s'], 'wall_loops': recipe.get('band_wall_loops')})
    return added


def restore_registration(path, expected):
    """CLI export drops registration metadata. Restore it; never invent values."""
    with zipfile.ZipFile(path) as z:
        files = {i.filename: (i, z.read(i)) for i in z.infolist()}
    key = 'Metadata/project_settings.config'; config = json.loads(files[key][1])
    required = set(filter(None, expected['different_settings_to_system'][0].split(';')))
    for name in required:
        assert json.dumps(config.get(name)) == json.dumps(expected.get(name)), (name, config.get(name), expected.get(name), 'Sliced value differs from prepared recipe')
    before = set(filter(None, config.get('different_settings_to_system', [''])[0].split(';')))
    slots = config.get('different_settings_to_system', ['', '', '']); slots[0] = ';'.join(sorted(before | required))
    config['different_settings_to_system'] = slots
    files[key] = (files[key][0], json.dumps(config, indent=2).encode())
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for info, data in files.values(): z.writestr(info, data)
    return {'required_keys': sorted(required), 'registered_keys': sorted(before | required), 'cli_dropped_keys': sorted(required - before), 'values_unchanged': True}


def build(scratch, do_slice, only=None, out_dir=None, band_wall_loops=None):
    out = Path(out_dir).resolve() if out_dir else h.HERE / 'exports'; out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((h.HERE / 'exports' / 'manifest.json').read_text())
    if band_wall_loops is not None:
        # Experiment only (writes outside exports): more walls inside the slow bands.
        assert out != h.HERE / 'exports', 'Experiments must not overwrite the delivered project'
        h.P['print']['local_recipe']['band_wall_loops'] = band_wall_loops
    names = only or list(manifest['parts'])
    label = 'R16-A1-mini-PETG' + ('' if not only else '-' + '-'.join(only))
    centres = {'Key_Carrier': (60, 40), 'Battery_Holder': (135, 45), 'Battery_End_Gate': (60, 120), 'XIAO_Rod_Holder': (135, 110)}
    settings = a1_mini_settings()
    layout_path = out / (label + '-layout.3mf')
    bounds, modifiers = layout(names, [centres[n] for n in names], layout_path, manifest, settings)
    report = {'layout_sha256': h.sha(layout_path), 'generator_sha256': h.sha(Path(__file__)), 'builder_sha256': h.sha(BUILDER / 'print_projects.py'),
              'parts': names, 'plate_bounds_mm': bounds, 'printer': settings['printer_settings_id'], 'process': settings['print_settings_id'],
              'filament': settings['filament_settings_id'], 'nozzle_c': settings.get('nozzle_temperature'), 'bed_c': settings.get('textured_plate_temp'),
              'overrides': OVERRIDES, 'local_recipe': h.P['print']['local_recipe'], 'band_modifiers': modifiers, 'support_policy': 'No automatic support, no brim, no CAD print helpers; rings not on the bed use arc lead-in skirts.',
              'physical_print_verified': False}
    if do_slice:
        scratch = scratch.resolve(); scratch.mkdir(parents=True, exist_ok=True); (scratch / 'tmp').mkdir(exist_ok=True)
        target = label + '.gcode.3mf'
        cmd = [str(BAMBU), '--datadir', str(scratch / 'bambu-data'), '--debug', '2', '--orient', '0', '--arrange', '0',
               '--slice', '0', '--export-3mf', target, '--outputdir', str(scratch), str(layout_path)]
        # Process-private home: macOS window-state restoration for the app bundle otherwise blocks
        # the offline CLI behind a modal after any earlier crash. Only this child process sees it;
        # the user's preferences and saved state are untouched. --datadir still isolates Bambu's data.
        home = scratch / 'home'; (home / 'Library' / 'Preferences').mkdir(parents=True, exist_ok=True)
        env = {**os.environ, 'TMPDIR': str(scratch / 'tmp'), 'HOME': str(home), 'CFFIXED_USER_HOME': str(home)}
        with (scratch / 'slice.log').open('w') as log:
            subprocess.run(cmd, cwd=scratch, stdout=log, stderr=subprocess.STDOUT, check=True, env=env, timeout=240)
        result = json.loads((scratch / 'result.json').read_text()); assert result['return_code'] == 0, result
        report['slice'] = result; report['warnings'] = [p['warning_message'] for p in result['sliced_plates'] if p.get('warning_message')]
        (out / target).write_bytes((scratch / target).read_bytes())
        report['delivered_settings_registration'] = restore_registration(out / target, settings)
        report['sliced_project_filename'] = target; report['sliced_project_sha256'] = h.sha(out / target)
        import re
        match = re.search(r'BambuStudio Version (\S+)', (scratch / 'slice.log').read_text())
        report['bambu_studio_version'] = match.group(1) if match else None
        report['cli_launch'] = 'offline CLI with --datadir in task scratch and a process-private HOME/CFFIXED_USER_HOME (no window-state restoration); 240 s subprocess timeout'
    (out / (label + '-print-checks.json')).write_text(json.dumps(report, indent=2) + '\n')
    print(report.get('warnings', []), report.get('sliced_project_filename'), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--scratch', type=Path, required=True); p.add_argument('--slice', action='store_true')
    p.add_argument('--only', nargs='+', choices=h.PARTS)
    p.add_argument('--out-dir', type=Path, help='experiment output directory outside exports')
    p.add_argument('--band-wall-loops', type=int, help='experiment: wall loops inside the slow-band modifiers (requires --out-dir)')
    a = p.parse_args(); build(a.scratch, a.slice, a.only, a.out_dir, a.band_wall_loops)
