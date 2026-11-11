"""Export R33 and register its matching assembly views without rewriting R32."""

import argparse
import json
from pathlib import Path
import shutil

import numpy as np

import holder33 as h
import assembly31 as a31

OUT = h.OUT
R32_OUT = h.R32 / 'exports'
CARRIER = 'Key_Carrier'
BRACKET = 'DFRobot_Hole_Bracket'
CLIPS = ('DFR0030_Post_Clip', 'DFR0030_Post_Clip_2')


def read(path):
    return json.loads(path.read_text())


def build(current):
    result = h.screen()
    print(json.dumps(result), flush=True)
    if not result['passed']:
        raise ValueError('R33 must pass its fit and guard checks before export.')

    (OUT / 'guide').mkdir(parents=True, exist_ok=True)
    working, fixed, ribs, _ = h.rib_candidates()
    carrier = h.H.base.clean(fixed + h.union(ribs.values()), CARRIER)
    h.H.OUT = a31.OUT = OUT
    h.H.PRINT_ROT[BRACKET] = a31.trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])
    old_manifest = read(R32_OUT / 'manifest.json')
    parts = {**old_manifest['parts'], CARRIER: h.H.export_part(CARRIER, carrier, CARRIER),
             BRACKET: h.H.export_part(BRACKET, h.bracket(), BRACKET)}
    for name in CLIPS:
        for suffix in ('assembly', 'SOURCE-REQUIRES-PREPARATION'):
            filename = f'{name}-{suffix}.stl'
            shutil.copy2(R32_OUT / filename, OUT / filename)
    pinched = a31.pinched(f'{BRACKET}-assembly.stl', 'guide/touch-bracket-pinched.stl')[0]

    guide = read(R32_OUT / 'assembly-guide.json')
    for module in guide['modules'].values():
        module['actors'] = {name: a31.relative_actor(actor, R32_OUT, OUT)
                            for name, actor in module['actors'].items()}
    for name in ('key', 'dfr'):
        guide['modules'][name]['actors']['carrier']['file'] = f'{CARRIER}-assembly.stl'
    for name in ('dfr', 'snap_hinge'):
        guide['modules'][name]['actors']['cap'].update(file=f'{BRACKET}-assembly.stl', morphFile=pinched)
    pivot_y = h.r31.AXIS_Y + h.r31.CLICK_SHIFT
    detail = carrier ^ h.box(-7.6, 7.6, pivot_y - 3.1, pivot_y + 9., 10.9, 20.1)
    guide['modules']['snap_hinge']['actors']['carrier']['file'] = a31.guide_mesh('hinge-detail-key-holder', detail)

    bom = {**read(h.R32 / 'complete-assembly.json'), 'revision': 'r33'}
    a31.write_json(h.HERE / 'complete-assembly.json', bom)
    manifest = {**old_manifest, 'revision': h.REVISION, 'based_on': h.R32.name, 'parts': parts,
                'change': 'Crosswise finger guards and two touch-bracket windows.',
                'source_sha256': {p.name: h.H.sha(p) for p in (h.HERE / 'holder33.py', Path(__file__), h.HERE / 'complete-assembly.json')}}
    a31.write_json(OUT / 'manifest.json', manifest)
    a31.write_json(OUT / 'geometry-checks.json', {
        'revision': h.REVISION, 'physical_fit_verified': False,
        'carrier_sha256': h.H.sha(OUT / f'{CARRIER}-assembly.stl'),
        'bracket_sha256': h.H.sha(OUT / f'{BRACKET}-assembly.stl'), 'checks': result,
    })
    files = {actor[field] for module in guide['modules'].values() for actor in module['actors'].values()
             for field in ('file', 'morphFile') if field in actor}
    guide['revision'] = h.REVISION
    guide['sources'] = {'r32_guide_sha256': h.H.sha(R32_OUT / 'assembly-guide.json'),
                        'generator_sha256': h.H.sha(__file__), 'manifest_sha256': h.H.sha(OUT / 'manifest.json'),
                        'meshes_sha256': {name: h.H.sha(OUT / name) for name in sorted(files)}}
    a31.write_json(OUT / 'assembly-guide.json', guide)
    a31.register_assembly(OUT / 'assembly-guide.json', 'r33', 'R33 Crosswise finger guards',
                          make_current=current, group_keys=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--make-current', action='store_true')
    build(parser.parse_args().make_current)
