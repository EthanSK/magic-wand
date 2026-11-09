#!/usr/bin/env python3
"""Build and slice the R19 Bambu A1 mini / Generic PETG project from the exact final STLs.

One plate: battery holder and door, XIAO holder and keeper, and three cell spacers.
The two holders include separate 'REMOVE AFTER PRINT' anchor parts. No automatic
support or slicer brim. CLI slicing uses explicit private scratch. Keep this
source slice intact; audit any separate Studio re-slice before sending it.
"""
from pathlib import Path
import argparse, json, os, re, subprocess, zipfile, xml.etree.ElementTree as E
import numpy as np, trimesh
import holder19 as h
E.register_namespace('', 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02')

BUILDER = h.HERE.parent / 'printed-loop-wand/shard-tube-r2'
BAMBU = Path('/Applications/BambuStudio.app/Contents/MacOS/BambuStudio')
PROFILES = Path('/Applications/BambuStudio.app/Contents/Resources/profiles/BBL')
NS = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
tag = lambda s: '{' + NS + '}' + s
PROCESS_OVERRIDES = dict(wall_loops='3', sparse_infill_density='20%', layer_height='0.2', initial_layer_print_height='0.2',
                         enable_support='0', brim_type='no_brim', enable_prime_tower='0', print_sequence='by layer',
                         bridge_no_support='1', max_bridge_length='12', initial_layer_speed=['20'], initial_layer_infill_speed=['30'], reduce_crossing_wall='1')
PRINTER_OVERRIDES = dict(z_hop=[str(h.LOCAL['print']['z_hop_mm'])], z_hop_types=['Normal Lift'])
ORIGINS = {'Battery_Holder': (30, 115), 'XIAO_Rod_Holder': (110, 115), 'Battery_End_Door': (20, 82), 'XIAO_Near_Keeper': (95, 82), 'Battery_Spacer_0p4mm': (14, 20), 'Battery_Spacer_0p6mm': (62, 20), 'Battery_Spacer_0p8mm': (110, 20)}
META = {'name', 'inherits', 'type', 'from', 'version', 'setting_id', 'instantiation', 'description', 'compatible_printers', 'compatible_printers_condition'}


def resolve(kind, name):
    data = json.loads((PROFILES / kind / (name + '.json')).read_text()); parent = data.get('inherits', '')
    result = resolve(kind, parent) if parent else {}
    result.update(data)
    return result


def settings():
    p = h.P['print']; machine = resolve('machine', p['printer']); process = resolve('process', p['process']); filament = resolve('filament', p['filament']); cfg = {}
    for d in (machine, process, filament):
        cfg.update({k: v for k, v in d.items() if k not in META})
    cfg.update(printer_settings_id=machine['name'], print_settings_id=process['name'], filament_settings_id=[filament['name']], filament_ids=['GFG99'], filament_colour=['#057748'], curr_bed_type='Textured PEI Plate')
    cfg.update(PROCESS_OVERRIDES); cfg.update(PRINTER_OVERRIDES)
    diff = cfg.get('different_settings_to_system', ['', '', ''])
    diff[0] = ';'.join(sorted(set(filter(None, diff[0].split(';'))) | set(PROCESS_OVERRIDES)))
    diff[-1] = ';'.join(sorted(set(filter(None, diff[-1].split(';'))) | set(PRINTER_OVERRIDES)))
    cfg['different_settings_to_system'] = diff
    return cfg


def add_mesh_part(model, config_obj, mesh, ident, subtype, title, metadata=()):
    resources = model.find(tag('resources'))
    child = E.SubElement(resources, tag('object'), id=str(ident), type='model', name=title)
    m = E.SubElement(child, tag('mesh')); vs = E.SubElement(m, tag('vertices')); ts = E.SubElement(m, tag('triangles'))
    for v in mesh.vertices: E.SubElement(vs, tag('vertex'), **{k: format(float(t), '.9g') for k, t in zip('xyz', v)})
    for f in mesh.faces: E.SubElement(ts, tag('triangle'), v1=str(f[0]), v2=str(f[1]), v3=str(f[2]))
    parent = next(o for o in resources.findall(tag('object')) if o.get('id') == config_obj.get('id'))
    E.SubElement(parent.find(tag('components')), tag('component'), objectid=str(ident))
    part = E.SubElement(config_obj, 'part', id=str(ident), subtype=subtype)
    E.SubElement(part, 'metadata', key='name', value=title)
    for k, v in metadata: E.SubElement(part, 'metadata', key=k, value=str(v))


def layout(dest, manifest, cfg):
    builder = h.base.r15.load('print_projects', BUILDER); builder.settings = lambda: cfg
    parts = []
    for name in h.PLATE:
        record = manifest['parts'][name]; mesh = trimesh.load_mesh(h.HERE / 'exports' / (name + '-SOURCE-REQUIRES-PREPARATION.stl'))
        mesh.apply_transform(np.array(record['print_to_assembly']))
        parts.append(dict(name=name, **record, assembly_vertices=mesh.vertices.tolist(), assembly_faces=mesh.faces.tolist()))
    dest.unlink(missing_ok=True)
    builder.make(h.PLATE, [ORIGINS[n] for n in h.PLATE], dest, {'parts': parts})
    with zipfile.ZipFile(dest) as z: files = {n: z.read(n) for n in z.namelist()}
    config = E.fromstring(files['Metadata/model_settings.config']); model = E.fromstring(files['3D/3dmodel.model'])
    resources = model.find(tag('resources')); ident = max(int(o.get('id')) for o in resources.findall(tag('object'))) + 100; recipe = h.P['print']['local_recipe']; bands = {}
    for obj in config.findall('object'):
        meta = {m.get('key'): m for m in obj.findall('metadata')}; name = meta['name'].get('value'); meta['enable_support'].set('value', '0')
        for k, v in PROCESS_OVERRIDES.items():
            if k not in ('enable_support', 'print_sequence', 'enable_prime_tower', 'reduce_crossing_wall') and not isinstance(v, list): E.SubElement(obj, 'metadata', key=k, value=v)
        if name in h.ANCHORED:
            ident += 1; anchor = trimesh.load_mesh(h.HERE / 'exports' / (name + '-ANCHOR-REMOVE-AFTER-PRINT.stl'))
            add_mesh_part(model, obj, anchor, ident, 'normal_part', f'REMOVE AFTER PRINT - {name} tear-off pads')
        for z0, z1 in recipe.get(name + '_bands_mm', []):
            mesh = trimesh.load_mesh(h.HERE / 'exports' / (name + '-SOURCE-REQUIRES-PREPARATION.stl')); lo, hi = mesh.bounds
            b0, b1 = max(0., z0 - .3), z1 + .3; box = trimesh.creation.box(extents=(hi[0] - lo[0] + 2, hi[1] - lo[1] + 2, b1 - b0)); box.apply_translation(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (b0 + b1) / 2))
            ident += 1; title = f'SLOW BAND {z0:g}-{z1:g} mm - modifier, not printed'
            add_mesh_part(model, obj, box, ident, 'modifier_part', title, recipe['speeds_mm_s'].items())
            bands.setdefault(name, []).append([z0, z1])
    for plate in config.findall('plate'):
        for item in plate.findall('metadata'):
            if item.get('key') == 'plater_name': item.set('value', 'Magic Wand R19 lightweight - A1 mini PETG')
    files['3D/3dmodel.model'] = E.tostring(model, encoding='utf-8', xml_declaration=True)
    files['Metadata/model_settings.config'] = E.tostring(config, encoding='utf-8', xml_declaration=True)
    files['Metadata/project_settings.config'] = json.dumps(cfg, indent=2).encode()
    with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, d in files.items(): z.writestr(n, d)
    extents = {}
    for name in h.PLATE:
        lows, highs = [], []
        for suffix in ('-SOURCE-REQUIRES-PREPARATION.stl', '-ANCHOR-REMOVE-AFTER-PRINT.stl') if name in h.ANCHORED else ('-SOURCE-REQUIRES-PREPARATION.stl',):
            m = trimesh.load_mesh(h.HERE / 'exports' / (name + suffix)); lows.append(m.bounds[0]); highs.append(m.bounds[1])
        lo = np.min(lows, axis=0) + [*ORIGINS[name], 0]; hi = np.max(highs, axis=0) + [*ORIGINS[name], 0]
        assert lo[0] >= 8 and lo[1] >= 8 and hi[0] <= 172 and hi[1] <= 172, (name, lo, hi); extents[name] = [lo.tolist(), hi.tolist()]
    names = list(extents)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            assert any(extents[a][1][k] + 3 <= extents[b][0][k] or extents[b][1][k] + 3 <= extents[a][0][k] for k in range(2)), (a, b, 'closer than 3 mm')
    return extents, bands


def restore_registration(path, expected):
    """CLI export drops registration metadata; restore it and never invent values."""
    with zipfile.ZipFile(path) as z: files = {i.filename: (i, z.read(i)) for i in z.infolist()}
    key = 'Metadata/project_settings.config'; config = json.loads(files[key][1]); slots = config.get('different_settings_to_system', ['', '', '']); wanted = expected['different_settings_to_system']; dropped = []
    while len(slots) < len(wanted): slots.append('')
    for index, text in enumerate(wanted):
        required = set(filter(None, text.split(';'))); before = set(filter(None, slots[index].split(';')))
        for name in required:
            assert json.dumps(config.get(name)) == json.dumps(expected.get(name)), (name, config.get(name), expected.get(name), 'Sliced value differs from prepared recipe')
        dropped += sorted(required - before); slots[index] = ';'.join(sorted(before | required))
    config['different_settings_to_system'] = slots; files[key] = (files[key][0], json.dumps(config, indent=2).encode())
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for info, data in files.values(): z.writestr(info, data)
    return {'cli_dropped_keys': dropped, 'values_unchanged': True}


def slice_info_warnings(path):
    """The slicer's own warning records from Metadata/slice_info.config, which the CLI result does not repeat."""
    with zipfile.ZipFile(path) as z:
        root = E.fromstring(z.read('Metadata/slice_info.config'))
    return [{'msg': w.get('msg'), 'level': w.get('level'), 'error_code': w.get('error_code')} for w in root.iter('warning')]


def build(scratch, do_slice):
    out = h.HERE / 'exports'; manifest = json.loads((out / 'manifest.json').read_text()); cfg = settings(); label = 'R19-A1-mini-PETG'
    layout_path = out / (label + '-layout.3mf'); extents, bands = layout(layout_path, manifest, cfg)
    report = {'layout_sha256': h.sha(layout_path), 'generator_sha256': h.sha(Path(__file__)), 'builder_sha256': h.sha(BUILDER / 'print_projects.py'), 'parts': h.PLATE, 'plate_origins_mm': ORIGINS, 'plate_extents_mm': extents,
              'printer': cfg['printer_settings_id'], 'process': cfg['print_settings_id'], 'filament': cfg['filament_settings_id'], 'nozzle_c': cfg.get('nozzle_temperature'), 'bed_c': cfg.get('textured_plate_temp'),
              'process_overrides': PROCESS_OVERRIDES, 'printer_overrides': PRINTER_OVERRIDES, 'slow_bands_mm': bands, 'local_recipe': h.P['print']['local_recipe'],
              'support_policy': 'No automatic support and no slicer brim. The two holders have labelled tear-off pads; flat parts need none.', 'physical_print_verified': False}
    if do_slice:
        scratch = scratch.resolve(); scratch.mkdir(parents=True, exist_ok=True); (scratch / 'tmp').mkdir(exist_ok=True); target = label + '.gcode.3mf'
        cmd = [str(BAMBU), '--datadir', str(scratch / 'bambu-data'), '--debug', '2', '--orient', '0', '--arrange', '0', '--slice', '0', '--export-3mf', target, '--outputdir', str(scratch), str(layout_path)]
        home = scratch / 'home'; (home / 'Library' / 'Preferences').mkdir(parents=True, exist_ok=True)
        env = {**os.environ, 'TMPDIR': str(scratch / 'tmp'), 'HOME': str(home), 'CFFIXED_USER_HOME': str(home)}
        with (scratch / 'slice.log').open('w') as log:
            subprocess.run(cmd, cwd=scratch, stdout=log, stderr=subprocess.STDOUT, check=True, env=env, timeout=280)
        result = json.loads((scratch / 'result.json').read_text()); assert result['return_code'] == 0, result
        report['slice'] = {k: v for k, v in result.items() if k in ('return_code', 'error_string', 'sliced_plates')}; report['warnings'] = [p['warning_message'] for p in result['sliced_plates'] if p.get('warning_message')]
        (out / target).write_bytes((scratch / target).read_bytes())
        report['delivered_settings_registration'] = restore_registration(out / target, cfg); report['sliced_project_filename'] = target; report['sliced_project_sha256'] = h.sha(out / target)
        report['slice_info_warnings'] = slice_info_warnings(out / target)
        match = re.search(r'BambuStudio Version (\S+)', (scratch / 'slice.log').read_text()); report['bambu_studio_version'] = match.group(1) if match else None
    (out / (label + '-print-checks.json')).write_text(json.dumps(report, indent=2) + '\n')
    print(report.get('warnings', []), report.get('sliced_project_filename'), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--scratch', type=Path, required=True); p.add_argument('--slice', action='store_true'); a = p.parse_args(); build(a.scratch, a.slice)
