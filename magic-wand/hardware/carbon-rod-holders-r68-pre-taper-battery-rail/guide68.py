"""R68 assembly guide: the published R67 guide with the R68 carrier.

Every motion, step and sample is R67's (and so R66's): R68 changes no assembly path. The
battery still slides in from the open end against the keypad base; only the outer rail is
back to its full pre-taper length. Lead meshes are regenerated here from design66, so the
guide refers only to files in this folder or upstream exports.
"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

import trimesh

import design68 as d
import kit68

r66, r67 = d.r66, d.r67
OUT = d.OUT
GUIDE_DIR = OUT / 'guide'
SOURCE = r67.OUT / 'assembly-guide.json'
BATTERY_NOTE = ('The broad face of the battery rests against the keypad base. Both rails run the full length, '
                'as they did before R66. Pull the exposed end of the pack to remove it.')


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def save_lead_meshes():
    GUIDE_DIR.mkdir(parents=True, exist_ok=True)
    for shape, name in r66.LEAD_FILES.items():
        v, f = r66.preview_lead_vertices(shape)
        trimesh.Trimesh(v, f, process=False).export(GUIDE_DIR / name)


def write(register=False, current=False):
    save_lead_meshes()
    guide = json.loads(SOURCE.read_text())
    hashes = {}
    for name, module in guide['modules'].items():
        if name == 'battery':
            module['note'] = BATTERY_NOTE
        for actor, spec in module['actors'].items():
            for field in ('file', 'morphFile'):
                if field not in spec:
                    continue
                if spec[field].startswith('guide/'):
                    src = OUT / spec[field]
                elif actor == 'carrier' and field == 'file':
                    src = OUT / d.HOLDER
                else:
                    src = (r67.OUT / spec[field]).resolve(strict=True)
                key = os.path.relpath(src, OUT)
                spec[field] = key
                hashes.setdefault(key, digest(src))
        if 'status' in module:
            module['status'] = 'R68 design · physical fit untested'
    guide['print_components']['keys'] = sorted(row['name'] for row in kit68.parts())
    guide['revision'] = 'R68'
    guide['physical_fit_verified'] = False
    route = OUT / 'op1-route.json'
    guide['sources'] = dict(generator_sha256=digest(__file__), upstream_guide_sha256=digest(SOURCE),
                            route_report_sha256=digest(route) if route.exists() else None,
                            meshes_sha256=hashes)
    dest = OUT / 'assembly-guide.json'
    dest.write_text(json.dumps(guide, separators=(',', ':'), allow_nan=False) + '\n')
    if register or current:
        sys.path.insert(0, str(d.HARDWARE / 'carbon-rod-holders/assembly'))
        from register_assembly import register_assembly
        register_assembly(dest, 'r68', 'R68 · Full battery rail restored', group_keys=True, make_current=current)
    return dest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--register', action='store_true')
    parser.add_argument('--current', action='store_true', help='also make R68 the default revision')
    args = parser.parse_args()
    print(write(args.register, args.current))
