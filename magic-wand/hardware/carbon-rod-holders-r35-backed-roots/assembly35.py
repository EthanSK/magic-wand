"""Export the R35 assembly, preserving the checked bought-part geometry.

Run with --make-current once the matching print plate has passed review.
"""

import argparse
from pathlib import Path
import shutil

import numpy as np

import holder35 as design
import assembly34 as prior

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
SOURCE = design.R34 / 'exports'
REVISION = 'r35'
CARRIER, BRACKET = prior.CARRIER, prior.BRACKET
EXPORT_SUFFIXES = ('assembly', 'SOURCE-REQUIRES-PREPARATION')


def export():
    checks = design.checks()
    if not checks['passed']:
        print(checks, flush=True)
        raise ValueError('R35 structural changes failed a working-space check.')

    a31 = prior.a31
    h = design.prior
    (OUT / 'guide').mkdir(parents=True, exist_ok=True)
    h.H.OUT = a31.OUT = OUT
    h.H.PRINT_ROT[BRACKET] = a31.trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])
    carrier = design.geometry()[0]
    manifest = prior.read(SOURCE / 'manifest.json')
    manifest['parts'].update({
        CARRIER: h.H.export_part(CARRIER, carrier, CARRIER),
        BRACKET: h.H.export_part(BRACKET, design.bracket(), BRACKET),
    })
    local_unchanged = (*prior.CLIPS, prior.spacer34.NAME)
    for name in local_unchanged:
        for suffix in EXPORT_SUFFIXES:
            filename = f'{name}-{suffix}.stl'
            shutil.copyfile(SOURCE / filename, OUT / filename)

    manifest.update(revision=HERE.name, based_on=design.R34.name,
                    change='First-layer connections at the rod clip and touch-bracket feet.',
                    source_sha256={path.name: h.H.sha(path) for path in
                                   (Path(__file__), HERE / 'holder35.py', HERE / 'complete-assembly.json')})
    a31.write_json(OUT / 'manifest.json', manifest)
    a31.write_json(OUT / 'geometry-checks.json', {'revision': HERE.name, 'checks': checks})
    write_guide(a31, h, carrier)


def write_guide(a31, h, carrier):
    guide = prior.read(SOURCE / 'assembly-guide.json')
    modules = guide['modules']
    for module in modules.values():
        module['actors'] = {name: a31.relative_actor(actor, SOURCE, OUT)
                            for name, actor in module['actors'].items()}

    for name in ('key', 'dfr'):
        modules[name]['actors']['carrier']['file'] = f'{CARRIER}-assembly.stl'
    pivot = h.r.AXIS_Y + h.r.CLICK_SHIFT
    detail = carrier ^ h.box(-7.6, 7.6, pivot - 3.1, pivot + 9., 10.9, 20.1)
    modules['snap_hinge']['actors']['carrier']['file'] = a31.guide_mesh('hinge-detail-key-holder', detail)
    morph, _ = a31.pinched(f'{BRACKET}-assembly.stl', 'guide/touch-bracket-pinched.stl')
    for name in ('dfr', 'snap_hinge'):
        modules[name]['actors']['cap'].update(file=f'{BRACKET}-assembly.stl', morphFile=morph)
    modules['dfr']['status'] = 'Reinforced key carrier and touch bracket'
    modules['dfr']['note'] = ('Three braces join the rod clip to the key carrier. '
                              'The touch bracket has a crossbar between its front feet.')
    assets = {actor[field] for module in modules.values() for actor in module['actors'].values()
              for field in ('file', 'morphFile') if field in actor}
    guide.update(revision=HERE.name, sources={
        'r34_guide_sha256': h.H.sha(SOURCE / 'assembly-guide.json'),
        'generator_sha256': h.H.sha(__file__),
        'manifest_sha256': h.H.sha(OUT / 'manifest.json'),
        'meshes_sha256': {name: h.H.sha(OUT / name) for name in sorted(assets)},
    })
    a31.write_json(OUT / 'assembly-guide.json', guide)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--make-current', action='store_true')
    args = parser.parse_args()
    export()
    if args.make_current:
        prior.a31.register_assembly(OUT / 'assembly-guide.json', REVISION, 'R35 Reinforced mounts',
                                    make_current=True, group_keys=True)
