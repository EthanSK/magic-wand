#!/usr/bin/env python3
"""Derive a shared-geometry review scene from the final STL and STEP sources."""
import json
from pathlib import Path
import trimesh
import cad

def data(shape):
    m = shape if isinstance(shape, trimesh.Trimesh) else cad.mesh(shape)
    return {'vertices': m.vertices.round(6).tolist(), 'faces': m.faces.tolist()}

def build():
    out = cad.HERE / 'exports'
    manifest = json.loads((out / 'manifest.json').read_text())
    geometry = {name: data(trimesh.load_mesh(out / (name + '-assembly.stl'))) for name in manifest['parts']}
    hardware = cad.source_hardware()
    geometry.update({name: data(shape) for name, shape in hardware.items()})
    z = cad.P['keys']['pcb_z']
    geometry['cap'] = data(cad.rr(16.6, 17.5, 1.4, 6.1, 9.1))
    options = {}
    for option, label in cad.OPTIONS.items():
        items = [{'geometry': 'Carrier_' + option, 'name': 'carrier', 'part': 'carrier', 'reference': False}]
        items.append({'geometry': 'XIAO_Rod_Holder', 'name': 'sensor', 'part': 'sensor', 'reference': False})
        for i, (x, y) in enumerate(cad.key_positions()):
            for name in ['switch', 'socket', 'cap']:
                items.append({'geometry': name, 'name': f'key_{i}_{name}', 'part': 'carrier', 'reference': True, 'position': [x, y, z]})
        refs = cad.references(option)
        for name in ['rod', 'battery', 'pcb', 'usb', 'wire']:
            key = option + '_' + name
            geometry[key] = data(refs[name])
            items.append({'geometry': key, 'name': name, 'part': 'sensor' if name in ['pcb', 'usb', 'wire'] else 'carrier', 'reference': True})
        geometry[option + '_sensor_rod'] = data(cad.tube_y(3.5, 4, -9, 23.4))
        items.append({'geometry': option + '_sensor_rod', 'name': 'rod', 'part': 'sensor', 'reference': True})
        mass_path = out / ('mass-' + option + '.json')
        options[option] = {'label': label, 'items': items, 'mass': json.loads(mass_path.read_text()) if mass_path.exists() else None,
                           'cad_mass_g': manifest['parts']['Carrier_' + option]['solid_PETG_g']}
    # Compare the immediately preceding revision without regenerating it.
    old = json.loads((cad.HERE.parent / 'carbon-rod-holders-r5/exports/review-scene.json').read_text())
    for name, shape in old['geometry'].items():
        geometry['r5_' + name] = shape
    previous = old['options']['front']
    options['r5'] = {**previous, 'label': 'Previous closed rings · R5',
                     'items': [{**item, 'geometry': 'r5_' + item['geometry']} for item in previous['items']]}
    scene = {'geometry': geometry, 'options': options, 'manifest': manifest, 'parameters': cad.P,
             'sources': {'cad_sha256': cad.sha(cad.HERE / 'cad.py'), 'generator_sha256': cad.sha(Path(__file__)), 'manifest_sha256': cad.sha(out / 'manifest.json')}}
    (out / 'review-scene.json').write_text(json.dumps(scene, separators=(',', ':')))

if __name__ == '__main__':
    build()
