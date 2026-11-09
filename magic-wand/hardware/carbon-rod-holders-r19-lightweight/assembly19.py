#!/usr/bin/env python3
"""Derive assembly-view references and motion dimensions from the frozen R19 CAD.

Run with the existing CAD Python environment. Printable meshes and Gcode are
read-only here; this emits only the small reference/recipe input for the viewer.
"""
import hashlib
import json
from pathlib import Path

import holder19 as h


def geometry(shape):
    m = h.mesh(shape)
    return {'vertices': m.vertices.round(6).tolist(), 'faces': m.faces.tolist()}


def generate():
    out = h.HERE / 'exports'
    manifest = json.loads((out / 'manifest.json').read_text())
    # Keep the animation's tilt pivot and insertion travel on the same source as
    # the checked loading route, rather than inventing a second assembly path.
    refs = {'board': geometry(h.board_outline()), 'cell': geometry(h.base.cell_shape())}
    refs.update({name: geometry(h.component_box(name)) for name in h.XO['components']})
    return {
        'revision': h.LOCAL['revision'],
        'sources': {'generator_sha256': h.sha(Path(__file__)), 'manifest_sha256': h.sha(out / 'manifest.json'),
                    'assembly_mesh_sha256': {name: h.sha(out / (name + '-assembly.stl')) for name in manifest['plate_parts']}},
        'geometry': refs,
        'board': {'pivot': [0, h.S['board_near_end_y_mm'] + h.S['board_outline_mm']['length'], h.BZ],
                  'tilt_degrees': h.INSERTION['tilt_degrees'], 'slide_mm': h.INSERTION['slide_mm'],
                  'keeper_travel_mm': h.RET['route_travel_mm'], 'components': list(h.XO['components'])},
        'battery': {'entry_travel_mm': h.P['cell']['manufacturer_max_mm']['length'] + 10,
                    'door_travel_mm': 15, 'spacer_thickness_mm': h.SP['thickness_mm'][0]},
        'rod': {'diameter_mm': h.P['rod']['diameter'], 'length_mm': 65, 'entry_travel_mm': 70},
    }


if __name__ == '__main__':
    target = h.HERE / 'exports/assembly-guide.json'
    target.write_text(json.dumps(generate(), separators=(',', ':')) + '\n')
    print(target.name, hashlib.sha256(target.read_bytes()).hexdigest())
