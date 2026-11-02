#!/usr/bin/env python3
"""Small physical acceptance pieces; use the full carrier's printing axes."""
import json
import math
import trimesh
import cad

def build():
    out = cad.HERE / 'exports/fit-coupons'; out.mkdir(exist_ok=True)
    shapes = {}
    for d in [8.2, 8.4, 8.6]:
        # A flat landing on the outside makes the horizontal ring printable;
        # its 3.6mm long bearing and lead-ins match the carrier's rings.
        shapes[f'Tube-bore-{d:.1f}mm'] = cad.ring(0, d) + cad.box(-5, 5, -1.8, 1.8, 5.2, 6.4)
    for d in [14.0, 14.1, 14.2]:
        shapes[f'Key-opening-{d:.1f}mm'] = cad.key_seat(d) ^ cad.box(-20,20,-20,20,-15,2.25)
    shapes['Centre-key-with-rings'] = cad.carrier('front') ^ cad.box(-11.2,11.2,-14.5,14,-15,30)
    record = {}
    for name, shape in shapes.items():
        m = cad.mesh(shape); assert m.is_watertight and len(m.split()) == 1
        m.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1,0,0])); m.apply_translation(-m.bounds[0])
        path = out / (name + '.stl'); m.export(path)
        record[name] = {'sha256':cad.sha(path), 'physical_fit_verified':False}
    (out / 'manifest.json').write_text(json.dumps({'generator_sha256':cad.sha(cad.HERE/'fit_coupons.py'), 'cad_sha256':cad.sha(cad.HERE/'cad.py'), 'parts':record},indent=2)+'\n')
    print('Seven fit coupons exported; physical test pending.')

if __name__ == '__main__': build()
