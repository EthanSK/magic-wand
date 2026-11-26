"""R70 assembly guide: the published R69 guide carried onto the R70 parts.

What changes:

* Meshes: the holder, the paddle and the two-post bar are the R70 exports; the retainer is
  R70's byte-for-byte copy of R69's. The pin line, the plug route and every paddle pose are R69's.
* Right upper key: its switch and socket follow the key 2 mm toward the lower row in every
  sampled pose. The left upper key is where it was.
* Backing strip: the two steps that slid the left strip under a socket are removed with
  the strip, which is no longer on the plate. The switch step already says to back each
  socket with a finger or a flat tool.
* Words: one hinge pin, the ribbed posts, the pouch standing further out of the shorter
  rail, the rounded lower edge.

The guide is written beside the meshes. Registering it for the viewer is the caller's
decision (--register, --current); nothing here does it by default.
 — Claude Fable 5.2"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

import numpy as np

import design70 as d
import hinge70
import kit70

r69, h69 = d.r69, hinge70.h69
OUT = d.OUT
SOURCE = r69.OUT / 'assembly-guide.json'
NEW_FILES = {d.HOLDER: d.HOLDER, hinge70.PADDLE: hinge70.PADDLE, hinge70.WIRES: hinge70.WIRES, hinge70.POST_BAR: hinge70.POST_BAR,
             hinge70.LID: hinge70.LID}
REPLACED_FROM = (r69.OUT, hinge70.R57_POST_BAR.parent)       # where the R69 guide took those five files from
MOVED = {'socket_4', 'switch_4'}                             # the right upper key
SHIFT = np.array([0., -d.KEY_SHIFT, 0.])
STRIP_ACTOR = 'left_backer'
STRIP_STEPS = {'Support the outside-facing socket', 'Pull the backing strip out'}
CAPTIONS = {
    'Slide in the hinge pin': 'Lower the paddle onto both seats. Slide the pin through the three holes.',
    'Seat the touch board': ('With the flat gold face up, press the plugged-in board down over both posts until it lies on the paddle. '
                             'The slim ribs on the posts grip its two holes. The white socket faces down and the three wires turn out '
                             'through the open right edge before the hinge.'),
    'Slide in the battery': ('Slide the wrapped battery lengthwise against the underside of the key holder until it stops. About 13 mm of it '
                             'stays behind the holder. Guide the leads out through the open end and leave the connector outside.'),
    'Inspect the Rounded Finger Rest': ('Rest a fingertip across the round beams under each lower socket. The lower edge of both key banks is '
                                        'rounded along the front, the corners and the sides.'),
}
MODULE_NOTES = {
    'battery': ('The broad face of the battery rests against the keypad base. The rails hold the front 14 mm of the pack and the rest stays '
                'behind the holder. Pull the exposed end of the pack to remove it.'),
    'finger_rest': ('Both rounded supports curve into the lower edge of the holder. That edge is rounded along the front, the outer corners '
                    'and both sides. The outside paths stay open for the lower sockets.'),
}
MODULE_ADDS = {'key': ' The upper right key sits 2 mm nearer the lower row than the upper left key.'}
OPTIONAL_NOTE = ('Not on the R70 plate. The two flat strips can support a socket while its switch is pressed in, and the second pin is '
                 'slightly snugger. Their files are unchanged and the R69 plate prints them.')


def write(register=False, current=False):
    guide = json.loads(SOURCE.read_text())
    assert guide['revision'] == 'R69', guide['revision']
    hashes, moved = {}, 0
    for name, module in guide['modules'].items():
        module['actors'].pop(STRIP_ACTOR, None)
        module['steps'] = [s for s in module['steps'] if s['title'] not in STRIP_STEPS]
        module['annotations'] = [n for n in module.get('annotations', []) if n.get('step') not in STRIP_STEPS and n.get('actor') != STRIP_ACTOR]
        if not module['annotations']:
            module.pop('annotations')
        if name in MODULE_NOTES:
            module['note'] = MODULE_NOTES[name]
        if name in MODULE_ADDS and MODULE_ADDS[name].strip() not in module.get('note', ''):
            module['note'] = module.get('note', '') + MODULE_ADDS[name]
        for step in module['steps']:
            step['caption'] = CAPTIONS.get(step['title'], step.get('caption'))
            for sample in step['samples']:
                sample.pop(STRIP_ACTOR, None)
                if isinstance(sample.get('morphs'), dict):
                    sample['morphs'].pop(STRIP_ACTOR, None)
                for actor in MOVED & set(sample):
                    pose = np.asarray(sample[actor], float).reshape(3, 4)
                    pose[:, 3] += SHIFT
                    sample[actor] = [round(float(v), 6) for v in pose.ravel()]
                    moved += 1
        for actor, spec in module['actors'].items():
            for field in ('file', 'morphFile'):
                if field not in spec:
                    continue
                src = (r69.OUT / spec[field]).resolve(strict=True)
                if src.name in NEW_FILES and src.parent in REPLACED_FROM:
                    src = OUT / NEW_FILES[src.name]
                key = os.path.relpath(src, OUT)
                spec[field] = key
                hashes.setdefault(key, digest(src))
        if 'status' in module:
            module['status'] = 'R70 design · physical fit untested'
    assert moved > 0 and all(key in hashes for key in NEW_FILES.values()), (moved, sorted(hashes))
    guide['print_components']['keys'] = sorted(row['name'] for row in kit70.parts())
    guide['optional_components'] = dict(keys=sorted(kit70.DROPPED), note=OPTIONAL_NOTE)
    guide['r70_changes'] = dict(right_upper_key_toward_lower_row_mm=d.KEY_SHIFT, key_actors_moved=sorted(MOVED), poses_moved=moved,
                                left_upper_key_moved=False, holder_rear_face_y_mm=dict(r69=d.R69_BED, r70=d.BED),
                                steps_removed=sorted(STRIP_STEPS))
    guide['revision'] = 'R70'
    # R69 restored the integral rod grip, but its whole-rod metadata still
    # requested two steps for the removed collet. This broke every grouped
    # view during composition. R70 has no collet actor to assemble.
    # Found and fixed by GPT-6.1 Sol.
    for mount in guide['modules']['whole'].get('rodMounts', []):
        if mount['id']=='keys' and mount.get('afterSlide',{}).get('actor')=='rod_collet':
            assert 'rod_collet' not in guide['modules']['pin_hinge']['actors']
            mount.pop('afterSlide')
    guide['physical_fit_verified'] = False
    guide['sources'] = dict(generator_sha256=digest(__file__), upstream_guide_sha256=digest(SOURCE), meshes_sha256=hashes,
                            key_report_sha256=digest(OUT / 'keys.json'), upstream_sources=guide.get('sources', {}).get('plug_line'))
    dest = OUT / 'assembly-guide.json'
    dest.write_text(json.dumps(guide, separators=(',', ':'), allow_nan=False) + '\n')
    if register or current:
        sys.path.insert(0, str(d.HARDWARE / 'carbon-rod-holders/assembly'))
        from register_assembly import register_assembly
        register_assembly(dest, 'r70', 'R70 · Short holder, nearer right key, round edges', group_keys=True, make_current=current)
    return dest


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--register', action='store_true')
    parser.add_argument('--current', action='store_true', help='also make R70 the default revision')
    args = parser.parse_args()
    print(write(args.register, args.current))
