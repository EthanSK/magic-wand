"""Generate the matched R34 plate sources and assembly preview."""

import argparse
from pathlib import Path
import shutil

import numpy as np

import holder34 as h
import assembly31 as a31
import assembly32 as a32
from assembly33 import BRACKET, CARRIER, CLIPS, read
import spacer34

SOURCE = h.R33 / 'exports'
OUT = h.OUT
LABEL = 'R34 Straight OP1 board'


def build(current):
    checks = h.checks()
    if not checks['passed']:
        raise ValueError('The straight OP1 assembly has unresolved CAD fit checks.')
    (OUT / 'guide').mkdir(parents=True, exist_ok=True)
    carrier, _, _, _ = h.geometry()
    h.H.OUT = a31.OUT = a32.OUT = OUT
    h.H.PRINT_ROT[BRACKET] = a31.trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])
    source_manifest = read(SOURCE / 'manifest.json')
    parts = {**source_manifest['parts'], CARRIER: h.H.export_part(CARRIER, carrier, CARRIER),
             BRACKET: h.H.export_part(BRACKET, h.bracket(), BRACKET), spacer34.NAME: spacer34.export(OUT)}
    for name in CLIPS:
        for suffix in ('assembly', 'SOURCE-REQUIRES-PREPARATION'):
            filename = f'{name}-{suffix}.stl'
            shutil.copyfile(SOURCE / filename, OUT / filename)
    morph = a31.pinched(f'{BRACKET}-assembly.stl', 'guide/touch-bracket-pinched.stl')[0]
    guide = read(SOURCE / 'assembly-guide.json')
    for module in guide['modules'].values():
        module['actors'] = {name: a31.relative_actor(actor, SOURCE, OUT) for name, actor in module['actors'].items()}
    modules = guide['modules']
    for name in ('key', 'dfr'):
        modules[name]['actors']['carrier']['file'] = f'{CARRIER}-assembly.stl'
    for name in ('dfr', 'snap_hinge'):
        modules[name]['actors']['cap'].update(file=f'{BRACKET}-assembly.stl', morphFile=morph)
    pivot = h.r.AXIS_Y + h.r.CLICK_SHIFT
    hinge = carrier ^ h.box(-7.6, 7.6, pivot - 3.1, pivot + 9., 10.9, 20.1)
    modules['snap_hinge']['actors']['carrier']['file'] = a31.guide_mesh('hinge-detail-key-holder', hinge)

    full = modules['dfr']
    for name, solid in h.hardware().items():
        full['actors'][name]['file'] = a32.guide_mesh(f'op1-{name}', solid)
    for annotation in full['annotations']:
        if annotation['actor'] == 'board':
            annotation['point'] = [h.PCB_X, h.h32.ACTUATOR_Y + h.h32.EYELETS[0], h.h32.PCB_TOP]
    full['status'] = 'Straight OP1 board · CAD clearances checked'
    full['note'] = ('The OP1 board sits parallel to the rod, offset to leave room for the underside plug. '
                    'The centred touch board uses the rear snap hinge and two post clips.')
    modules['battery_spacer']['actors']['spacer'].update(file=f'{spacer34.NAME}-assembly.stl',
                                                       label='Angled vent spacer (0.4 mm)')

    bom = {**read(h.R33 / 'complete-assembly.json'), 'revision': 'r34'}
    bom['groups']['spacer'] = {'directory': '.', 'parts': [spacer34.NAME]}
    a31.write_json(h.HERE / 'complete-assembly.json', bom)
    manifest = {**source_manifest, 'revision': h.HERE.name, 'based_on': h.R33.name, 'parts': parts,
                'change': 'Straight OP1 board, two front travel stops and angled battery spacer vents.',
                'source_sha256': {p.name: h.H.sha(p) for p in (h.HERE / 'holder34.py', Path(__file__),
                                   h.HERE / 'complete-assembly.json', h.HERE / 'spacer34.py')}}
    a31.write_json(OUT / 'manifest.json', manifest)
    a31.write_json(OUT / 'geometry-checks.json', {'revision': h.HERE.name, 'physical_fit_verified': False, 'checks': checks})
    assets = {actor[field] for module in modules.values() for actor in module['actors'].values()
              for field in ('file', 'morphFile') if field in actor}
    guide.update(revision=h.HERE.name, sources={
        'r33_guide_sha256': h.H.sha(SOURCE / 'assembly-guide.json'),
        'generator_sha256': h.H.sha(__file__), 'manifest_sha256': h.H.sha(OUT / 'manifest.json'),
        'meshes_sha256': {name: h.H.sha(OUT / name) for name in sorted(assets)},
    })
    a31.write_json(OUT / 'assembly-guide.json', guide)
    a31.register_assembly(OUT / 'assembly-guide.json', 'r34', LABEL, make_current=current, group_keys=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--make-current', action='store_true')
    build(parser.parse_args().make_current)
