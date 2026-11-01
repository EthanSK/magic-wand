#!/usr/bin/env python3
"""Audit prepared meshes and all five hardware spaces in the actual G-code."""
import json
import zipfile
from pathlib import Path
import numpy as np
import cad

if __name__ == '__main__':
    out = cad.HERE / 'exports'
    m = cad.load_previous('verify_slice', cad.HERE.parent / 'carbon-rod-holders')
    m.HERE, m.OUT = cad.HERE, out
    m.inspect()
    q = m.q
    manifest = json.loads((out / 'manifest.json').read_text())
    entries = [dict(name=n, file=n + '.stl', sha256=r['stl_sha256'], **r) for n, r in manifest['parts'].items()]
    with zipfile.ZipFile(out / 'Holder-pair-sliced.3mf') as archive:
        objects, offset, _ = q.objects(archive, {'parts': entries}, out / 'manifest.json')
        data, features, _ = q.extrusion_points(archive.read('Metadata/plate_1.gcode').decode(), .3)
    extra = {}
    for obj in objects:
        xyz = data[:, :3] + offset - obj['build'][:3, 3]
        bb = obj['print_bbox']
        mask = np.all(xyz >= bb[0] - [8, 8, .4], axis=1) & np.all(xyz <= bb[1] + [8, 8, .4], axis=1)
        pa = obj['print_to_assembly']
        inverse = np.linalg.inv(pa)
        regions = {}
        if obj['name'] == 'Key_Battery_Carrier':
            for i, (x, y) in enumerate(cad.key_positions()):
                for label, part in cad.ds.local_hardware(cad.C).items():
                    if label in ['switch_housing', 'socket', 'switch_pins']:
                        regions[f'key_{i}_{label}'] = part.translate((x, y, cad.P['keys']['plate_z']))
        else:
            s = cad.P['sensor']
            regions = {'wire_route': cad.wire_route(), 'usb_approach': cad.box(-5.2, 5.2, -22.7, -.7, s['board_z'] + .9, s['board_z'] + 4.4)}
        extra[obj['name']] = {name: q.inspect_region(region.transform(inverse[:3, :]), xyz[mask], data[mask, 3], data[mask, 4], data[mask, 5].astype(int), features, pa)
                              for name, region in regions.items()}
    report = json.loads((out / 'slice-clearances.json').read_text())
    report['r3_extra_regions'] = extra
    report['r3_checker_sha256'] = cad.sha(Path(__file__))
    report['passed'] = report['passed'] and all(not c['violations'] for regions in extra.values() for c in regions.values())
    (out / 'slice-clearances.json').write_text(json.dumps(report, indent=2) + '\n')
    assert report['passed'], 'Inspect the saved slice-clearances.json'
    print('All five key interfaces, sensor wire and reversed USB approach passed.')
