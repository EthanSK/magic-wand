"""R69 assembly guide: the published R68 guide carried onto the R69 parts.

What changes, and how each sampled motion is carried over:

* Meshes: the holder, paddle, retainer and touch leads are the R69 exports.
* Hinge: the pin line moved 1.3 mm toward the touch board. Parts that sit on the pin (pin,
  centre clip) are shifted with it. Parts that ride on the paddle keep their rest places and
  have every sampled pose re-expressed about the new pin line.
* White plug: it rises on the line checks69 found (op1.json), not on R66's. The plug and its
  lead are moved onto that line while threading and eased back to their unchanged mated
  pose during the turn above the holder. The moved poses are checked against the holder.
* Rod grip: the two steps that fitted the loose collet are removed, with the collet.
* Notes for the retainer, the plug window, the lead route over the hinge and the rod grip.
 — Claude Fable 5.2"""
import argparse
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys

import numpy as np

import design69 as d
import hinge69
import kit69

b, r68, h64 = d.b, d.r68, hinge69.h64
OUT = d.OUT
SOURCE = r68.OUT / 'assembly-guide.json'
SHIFT = np.array([0., hinge69.AXIS - h64.AXIS, hinge69.KEEPER_Z - h64.KEEPER_Z])
NEW_FILES = {'Key_Carrier-assembly.stl': d.HOLDER, 'Touch_Paddle-assembly.stl': hinge69.PADDLE,
             'OP1_Lid_Stop-assembly.stl': hinge69.LID, 'Gravity_Wires-assembly.stl': hinge69.WIRES}
ON_PIN = {'hinge_pin', 'pin_clip'}                        # shifted with the pin line
ON_PADDLE = {'cap', 'sensor', 'sensor_lead', 'gravity_plug', 'clip_left', 'clip_right', 'post_bar'}
PLUG_ACTORS = {'plug', 'op1_lead'}
THREAD_STEPS = {'Thread the white plug up from below': (1., 1.), 'Lower the plug back through the opening': (1., 1.),
                'Turn the plug upright above the holder': (1., 0.), 'Tip the plug so its lead hangs down': (0., 1.)}
COLLET_STEPS = {'Clip the grip onto the carbon rod', 'Seat the rod grip'}
NOTES = {
    'The retainer covers the board': ('The retainer covers the board and latches in the left rail. Its two low posts sit over the feet of the '
                                      "paddle's two legs and limit paddle lift."),
    'Opening for the white plug': ('One window for the white plug and its lead. Bring the plug up beside the rod sleeve, on the guard side; '
                                   'the guard arm now runs clear of this path.'),
}
MODULE_NOTES = {
    'dfr': ' Lay the three touch leads over the hinge barrel between its two posts, then to the right behind the right post.',
    'pin_hinge': ' Lay the three touch leads over the hinge barrel between its two posts, then to the right behind the right post.',
    'key': ' The holder grips the rod with its own two rings; push it on with a twist. There is no separate rod grip.',
}


def write(register=False, current=False):
    guide = json.loads(SOURCE.read_text())
    to_new, to_old = translation(SHIFT), translation(-SHIFT)
    plug_spec = guide['modules']['op1_clips']['actors']['plug']['file']
    plug_move, plug_turn, tried = choose_turn(guide, (r68.OUT / plug_spec).resolve(strict=True))
    hashes = {}
    for name, module in guide['modules'].items():
        module['actors'].pop('rod_collet', None)
        module['steps'] = [s for s in module['steps'] if s['title'] not in COLLET_STEPS]
        for note in module.get('annotations', []):
            for start, text in NOTES.items():
                if note.get('title', '').startswith(start):
                    note['title'] = text
        if name in MODULE_NOTES and MODULE_NOTES[name].strip() not in module.get('note', ''):
            module['note'] = module.get('note', '') + MODULE_NOTES[name]
        for step in module['steps']:
            ease = THREAD_STEPS.get(step['title'])
            count = max(len(step['samples']) - 1, 1)
            for i, sample in enumerate(step['samples']):
                sample.pop('rod_collet', None)
                for actor in list(sample):
                    if actor == 'morphs':                 # morph weights, not a pose
                        sample[actor].pop('rod_collet', None)
                        continue
                    m = mat(sample[actor])
                    if actor in ON_PIN:
                        m = to_new @ m
                    elif actor in ON_PADDLE:
                        m = to_new @ m @ to_old
                    elif actor in PLUG_ACTORS and ease:
                        m = blend(plug_move, ease[0] + (ease[1] - ease[0]) * i / count) @ m
                    else:
                        continue
                    sample[actor] = flat(m)
        for actor, spec in module['actors'].items():
            for field in ('file', 'morphFile'):
                if field not in spec:
                    continue
                src = (r68.OUT / spec[field]).resolve(strict=True)
                if src.name in NEW_FILES and src.parent in (r68.OUT, h64.OUT, hinge69.R59_LID.parent, d.r67.OUT, d.r66.OUT):
                    src = OUT / NEW_FILES[src.name]
                key = os.path.relpath(src, OUT)
                spec[field] = key
                hashes.setdefault(key, digest(src))
        if 'status' in module:
            module['status'] = 'R69 design · physical fit untested'
    guide['print_components']['keys'] = sorted(row['name'] for row in kit69.parts())
    guide['revision'] = 'R69'
    guide['physical_fit_verified'] = False
    guide['sources'] = dict(generator_sha256=digest(__file__), upstream_guide_sha256=digest(SOURCE),
                            route_report_sha256=digest(OUT / 'op1.json'), meshes_sha256=hashes,
                            hinge_shift_mm=[round(float(v), 3) for v in SHIFT],
                            plug_line=dict(turn_about_new_line_deg=plug_turn, holder_overlap_tried_mm3={str(k): v for k, v in tried.items()}))
    dest = OUT / 'assembly-guide.json'
    dest.write_text(json.dumps(guide, separators=(',', ':'), allow_nan=False) + '\n')
    if register or current:
        sys.path.insert(0, str(d.HARDWARE / 'carbon-rod-holders/assembly'))
        from register_assembly import register_assembly
        register_assembly(dest, 'r69', 'R69 · Snug rod, short hinge, clean OP1 seat', group_keys=True, make_current=current)
    return dest


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def mat(values):
    m = np.eye(4)
    m[:3] = np.asarray(values, float).reshape(3, 4)
    return m


def flat(m):
    return [round(float(v), 6) for v in m[:3].ravel()]


def translation(v):
    m = np.eye(4)
    m[:3, 3] = v
    return m


def plug_line():
    """R66's threading line and the R69 one from the checked report. — Claude Fable 5.2"""
    route = json.loads((OUT / 'op1.json').read_text())['largest_plug_margin_per_side']['r69']
    return np.array([*d.r66.THREAD_XY, 0.]), np.array([*route['centre_world_xy_mm'], 0.]), route


def about(point, degrees):
    a = math.radians(degrees)
    m = np.eye(4)
    m[:2, :2] = [[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]]
    m[:3, 3] = point - m[:3, :3] @ point
    return m


def choose_turn(guide, plug_file):
    """Turn about the new line that leaves the threading plug clear of the R69 holder. — Claude Fable 5.2"""
    old_line, new_line, _ = plug_line()
    holder = b.load(OUT / d.HOLDER)
    plug = b.load(plug_file)
    samples = next(s for s in guide['modules']['op1_clips']['steps'] if s['title'].startswith('Thread the white plug'))['samples']
    result = {}
    for degrees in (0., -10., 10., -20., 20.):
        move = about(new_line, degrees) @ translation(new_line - old_line)
        worst = max(float((holder ^ plug.transform((move @ mat(s['plug']))[:3].tolist())).volume()) for s in samples[::3])
        result[degrees] = round(worst, 4)
        if worst < 1e-3:
            return move, degrees, result
    raise ValueError(f'no clear threading pose for the guide: {result}')


def blend(move, weight):
    """Part of a small rigid move (rotation about Z and translation), for easing in and out. — Claude Fable 5.2"""
    angle = math.atan2(move[1, 0], move[0, 0]) * weight
    out = np.eye(4)
    out[:2, :2] = [[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]]
    out[:3, 3] = move[:3, 3] * weight
    return out

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--register', action='store_true')
    parser.add_argument('--current', action='store_true', help='also make R69 the default revision')
    args = parser.parse_args()
    print(write(args.register, args.current))
