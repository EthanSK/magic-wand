#!/usr/bin/env python3
"""Measure both axial approaches using the delivered meshes, never moved CAD.

The animation consumes this same sampled path. Contacts are rigid CAD overlaps;
wire allowances, printed tolerances and other modules remain separate limits.
"""
from pathlib import Path
import json
import numpy as np
import holder20 as h

OUT = h.HERE / 'exports'


def build() -> None:
    guard = h.read(OUT / 'Finger_Guard-assembly.stl')
    key = h.read(OUT / 'Key_Carrier-assembly.stl')
    references = {'key_holder': key, **h.bought_parts(), **h.contact_envelopes()}
    paths = {}
    for name, start in [('hand', -60.), ('rings', 60.)]:
        rows = []
        for distance in np.linspace(start, 0., 241):
            moved = guard.translate((0., float(distance), 0.))
            overlaps = {label: float((moved ^ solid).volume()) for label, solid in references.items()}
            hits = {label: v for label, v in overlaps.items() if v > .01}
            rows.append({'offset_mm': float(distance), 'overlaps_mm3': hits})
        first = next((i for i, row in enumerate(rows) if row['overlaps_mm3']), None)
        paths[name] = {'samples': rows, 'first_collision_index': first,
                       'stop_index': len(rows) - 1 if first is None else max(0, first - 1)}
    assert paths['hand']['first_collision_index'] is None
    assert paths['rings']['first_collision_index'] is not None
    assert not paths['hand']['samples'][-1]['overlaps_mm3']
    hardware = {}
    for label, shape in h.bought_parts().items():
        mesh = h.mesh(shape)
        hardware[label] = {'vertices': np.round(mesh.vertices, 5).tolist(), 'faces': mesh.faces.tolist()}
    data = {'revision': 'R20', 'units': 'mm', 'generator_sha256': h.sha(Path(__file__)),
            'meshes_sha256': {n: h.sha(OUT / (n + '-assembly.stl')) for n in ('Finger_Guard', 'Key_Carrier')},
            'paths': paths, 'hardware': hardware, 'rod_diameter_mm': 8.,
            'guard_length_mm': h.G['y_rear_mm'] - h.G['y_front_mm'],
            'guard_rear_y_mm': h.G['y_rear_mm'], 'key_ring_start_y_mm': h.P['carrier_rings']['mid_band_y_mm'][0],
            'nominal_stop_gap_mm': h.P['carrier_rings']['mid_band_y_mm'][0] - h.G['y_rear_mm'],
            'step_mm': .25, 'overlap_threshold_mm3': .01, 'physical_fit_verified': False,
            'scope': 'Rigid axial movement of the exported guard relative to R20 key holder, bought parts and stated wire/solder envelopes. Other modules along the rod and real wire routing are not measured.'}
    (OUT / 'assembly-guide.json').write_text(json.dumps(data, separators=(',', ':')) + '\n')
    print(json.dumps({name: {'first_collision': path['first_collision_index'], 'stop_offset_mm': path['samples'][path['stop_index']]['offset_mm']} for name, path in paths.items()}), flush=True)


if __name__ == '__main__':
    build()
