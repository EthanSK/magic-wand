#!/usr/bin/env python3
"""Small physical acceptance pieces; use the full carrier's printing axes."""
import json
import math
import numpy as np
import manifold3d as mf
import trimesh
import cad

def build():
    out = cad.HERE / 'exports/fit-coupons'; out.mkdir(exist_ok=True)
    shapes = {}
    for diameter in [7.9,8.0,8.1]:
        for name,width,root in [('Carrier',cad.P['rod']['ring_width'],cad.P['rod']['clip_root_wall']),
                                ('Sensor',cad.P['rod']['sensor_clip_width'],cad.P['rod']['sensor_clip_root_wall'])]:
            # Retain the real print orientation; a flat C on the bed would
            # test a different layer direction from the integrated holder.
            shapes[f'{name}-spring-{diameter:.1f}mm'] = cad.ring(0,diameter,width,root) + cad.box(-4,4,-width/2,width/2,5.2,6.4)
    for d in [14.0, 14.1, 14.2]:
        shapes[f'Key-opening-{d:.1f}mm'] = cad.key_seat(d) ^ cad.box(-20,20,-20,20,-15,2.25)
    shapes['Centre-key-with-clips'] = cad.carrier('front') ^ cad.box(-11.2,11.2,-14.5,14,-15,30)
    record = {}
    for name, shape in shapes.items():
        m = cad.mesh(shape); assert m.is_watertight and len(m.split()) == 1
        m.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1,0,0])); m.apply_translation(-m.bounds[0])
        normal = mf.Manifold(mf.Mesh(np.asarray(np.round(m.vertices,6),dtype=np.float32),np.asarray(m.faces,dtype=np.uint32))).simplify(.000001)
        assert normal.status() == mf.Error.NoError and abs(normal.volume()-m.volume)<.01
        path = out / (name + '.stl'); cad.mesh(normal).export(path)
        final = trimesh.load_mesh(path)
        assert final.is_watertight and len(final.split()) == 1, name
        record[name] = {'sha256':cad.sha(path), 'physical_fit_verified':False}
    (out / 'manifest.json').write_text(json.dumps({'generator_sha256':cad.sha(cad.HERE/'fit_coupons.py'), 'cad_sha256':cad.sha(cad.HERE/'cad.py'), 'parts':record},indent=2)+'\n')
    print('Ten fit coupons exported; physical spring/creep test pending.')

if __name__ == '__main__': build()
