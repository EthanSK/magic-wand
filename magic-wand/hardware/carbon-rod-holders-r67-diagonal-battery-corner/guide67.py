"""R67 assembly guide: the published R66 guide with the R67 carrier.

Every motion, step and sample is R66's: R67 changes no assembly path. The OP1 plug still
threads up through the same opening, now with a lead-in on its underside edge, and the
battery slides in as before past the new diagonal corner. Lead meshes are regenerated
here from design66, so the guide refers only to files in this folder or upstream exports.
"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

import trimesh

import design67 as d
import kit67

r66 = d.r66
OUT = d.OUT
GUIDE_DIR = OUT / 'guide'
SOURCE = r66.OUT / 'assembly-guide.json'
OPENING_NOTE = ('Opening for the white plug and its lead, with a lead-in on its underside edge so the plug '
                'finds the hole from below. The three socket holes are unchanged.')


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
        for note in module.get('annotations', []):
            if note.get('title', '').startswith('Opening for the white plug'):
                note['title'] = OPENING_NOTE
        if name == 'battery':
            module['note'] = ('The broad face of the battery rests against the keypad base. The rod-side rail runs the full '
                              'length; the outer rail tapers away towards the open end and its corner is cut diagonally. '
                              'Pull the exposed end to remove the pack.')
        for actor, spec in module['actors'].items():
            for field in ('file', 'morphFile'):
                if field not in spec:
                    continue
                if spec[field].startswith('guide/'):
                    src = OUT / spec[field]
                elif actor == 'carrier' and field == 'file':
                    src = OUT / d.HOLDER
                else:
                    src = (r66.OUT / spec[field]).resolve(strict=True)
                key = os.path.relpath(src, OUT)
                spec[field] = key
                hashes.setdefault(key, digest(src))
        if 'status' in module:
            module['status'] = 'R67 design · physical fit untested'
    guide['print_components']['keys'] = sorted(row['name'] for row in kit67.parts())
    guide['revision'] = 'R67'
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
        register_assembly(dest, 'r67', 'R67 · Diagonal battery corner and cleaned saddle', group_keys=True, make_current=current)
    return dest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--register', action='store_true')
    parser.add_argument('--current', action='store_true', help='also make R67 the default revision')
    args = parser.parse_args()
    print(write(args.register, args.current))
