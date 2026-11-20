"""Write independent, support-free parts using the native A1 mini PETG settings."""
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np

HERE = Path(__file__).resolve().parent
HARDWARE = HERE.parent
sys.path.insert(0, str(HARDWARE / 'carbon-rod-holders-r52-snap-seat'))
from plate52 import add_modifiers, decode, MODEL, SETTINGS, PROJECT, resource, tag, value, load_solid, digest
from tower52 import add_tower_base
from panels53 import backed_panel

TEMPLATE = HARDWARE/'carbon-rod-holders-r52-snap-seat/exports/print-recovery/layout.3mf'


def mesh_path(reference, mesh_dir):
    """Resolve a revision mesh or the shared, original DFRobot post clip."""
    path = Path(reference)
    return (mesh_dir if path.parent == Path('.') else HERE / 'exports') / path


def carrier_wall_settings():
    # Preserve the native wall recipe which kept Ethan's four R52 keys open.
    source = TEMPLATE.parent.parent / 'print-mechanisms/layout.3mf'
    with ZipFile(source) as z:
        owners = ET.fromstring(z.read(SETTINGS)).findall('object')
    for owner in owners:
        options = {m.get('key'):m.get('value') for m in owner.findall('metadata')}
        if options.get('name') == 'Key_Carrier':
            keys = ('wall_loops','sparse_infill_density','wall_generator','outer_wall_acceleration',
                    'inner_wall_acceleration','top_surface_speed','bridge_angle','is_infill_first',
                    'min_bead_width','wall_distribution_count','inner_wall_line_width',
                    'outer_wall_line_width','internal_solid_infill_line_width')
            return {k:options[k] for k in keys}
    raise ValueError('Missing the R52 key carrier wall recipe')


def preserve_key_corner(resources, compound, owner, pose):
    """Reuse the proven narrow wall at the left Choc socket in its assembly coordinates."""
    source = TEMPLATE.parent.parent / 'print-mechanisms/layout.3mf'
    with ZipFile(source) as archive:
        settings = ET.fromstring(archive.read(SETTINGS))
        model = ET.fromstring(archive.read(MODEL))
    prior = next(o for o in settings.findall('object')
                 if o.find("metadata[@key='name']").get('value') == 'Key_Carrier')
    modifier = next(p for p in prior.findall("part[@subtype='modifier_part']")
                    if p.find("metadata[@key='name']").get('value') == 'Upper left socket corner line width')
    item = model.find(tag('build') + '/' + tag('item') + f"[@objectid='{prior.get('id')}']")
    origin = np.array([float(n) for n in item.get('transform').split()[-3:]])
    old = model.find(tag('resources') + '/' + tag('object') + f"[@id='{modifier.get('id')}']")
    previous_frame = json.loads(source.with_suffix('.frame.json').read_text())['parts']['Key_Carrier']['assembly_to_machine']
    location = pose @ np.linalg.inv(previous_frame)
    corner = decode(old).translate(origin).transform(location[:3])
    add_modifiers(resources, compound, owner, {'Upper left socket corner line width':corner}, 599, 'modifier_part')
    target = owner.find("part[@id='599']")
    for meta in modifier.findall('metadata'):
        value(target, meta.get('key'), meta.get('value'))


def write_layout(parts, out, tower, title, *, panel_builder=backed_panel):
    """Parts supply one STL, its rigid print pose and the outer brim for that object."""
    with ZipFile(TEMPLATE) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    model = ET.fromstring(files[MODEL])
    ET.register_namespace('', model.tag[1:].split('}')[0])
    resources = model.find(tag('resources'))
    build = model.find(tag('build'))
    resources.clear()
    build.clear()
    cfg = ET.fromstring(files[SETTINGS])
    for owner in cfg.findall('object'):
        cfg.remove(owner)
    plate = cfg.find('plate')
    for obj in plate.findall('model_instance'):
        plate.remove(obj)
    value(plate, 'plater_name', title)
    frames = {}
    for index, entry in enumerate(parts, 1):
        part_id, object_id = index * 2 - 1, index * 2
        name = entry['name']
        source = entry['source']
        pose = np.asarray(entry['assembly_to_print'], dtype=float)
        assert pose.shape == (4, 4)
        assert np.allclose(pose[3], [0, 0, 0, 1])
        assert np.allclose(pose[:3,:3].T @ pose[:3,:3], np.eye(3))
        assert np.isclose(np.linalg.det(pose[:3,:3]), 1)
        body = load_solid(source).transform(pose[:3])
        lo, hi = np.asarray(body.bounding_box()).reshape(2, 3)
        assert abs(lo[2]) < .015, (name, lo)
        shells = sorted(body.decompose(),key=lambda shell: -abs(shell.volume()))
        # Reloading the inherited key mesh can expose a zero-volume folded edge.
        # A second printable solid is a release failure.
        fragments = [abs(s.volume()) for s in shells[1:]]
        if any(v >= .008 for v in fragments) or sum(fragments) >= .016:
            raise ValueError(f'{name} has a second printable solid: {fragments}')
        body = shells[0]
        xy = np.asarray(entry['bed_center'], dtype=float)
        shift = xy - (lo[:2] + hi[:2]) / 2
        panel = entry.get('panel')
        print_body = panel_builder(body, panel) if panel else body
        resource(resources, tag, part_id, name, print_body)
        owner = ET.Element('object', id=str(object_id))
        cfg.insert(index - 1, owner)
        options = dict(name=name, extruder=1, enable_support=0, wall_loops=4,
                       brim_type='no_brim' if panel else 'outer_only', brim_width=entry.get('brim_mm',0),
                       brim_object_gap=0, outer_wall_speed=35, inner_wall_speed=55,
                       outer_wall_acceleration=500, bridge_speed=16)
        if name == 'Key_Carrier':
            options.update(carrier_wall_settings())
        options.update(entry.get('wall_settings',{}))
        for key, val in options.items():
            value(owner, key, val)
        value(ET.SubElement(owner, 'part', id=str(part_id), subtype='normal_part'), 'name', name)
        node = ET.SubElement(resources, tag('object'), id=str(object_id), type='model')
        ET.SubElement(ET.SubElement(node, tag('components')), tag('component'), objectid=str(part_id))
        if name == 'Key_Carrier':
            preserve_key_corner(resources, node, owner, pose)
        tr = '1 0 0 0 1 0 0 0 1 ' + ' '.join(map(str, [*shift, 0]))
        ET.SubElement(build, tag('item'), objectid=str(object_id), transform=tr, printable='1')
        instance = ET.SubElement(plate, 'model_instance')
        for key, val in dict(object_id=object_id, instance_id=0, identify_id=object_id).items():
            value(instance, key, val)
        world = pose.copy()
        world[:2,3] += shift
        frames[name] = dict(source=entry.get('mesh_reference', source.name), source_sha256=digest(source),
                            assembly_to_machine=world.tolist(), adhesion_panel=panel)
    settings = json.loads(files[PROJECT])
    settings.update(enable_support='0', brim_type='no_brim')
    files[PROJECT] = json.dumps(settings, indent=2).encode()
    add_tower_base(files, **tower)
    for name, tree in [(MODEL, model), (SETTINGS, cfg), ('Metadata/layer_config_ranges.xml', ET.Element('objects'))]:
        files[name] = ET.tostring(tree, encoding='utf-8', xml_declaration=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(out, 'w', ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    out.with_suffix('.frame.json').write_text(json.dumps(dict(parts=frames, layout_sha256=digest(out)),
                                                        indent=2)+'\n')
