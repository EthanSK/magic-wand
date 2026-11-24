"""R66 assembly guide: the R64 guide with the R66 carrier and the threaded OP1 plug route.

The OP1 steps follow the checked rigid motions in design66/checks66 exactly:
thread the tipped plug up from below, turn it upright above the holder, push the
board's housing onto it, lower the board onto its three holes and lay the lead in
its channel. Removal plays the same motions in reverse.
"""
import argparse
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys

import numpy as np

import design66 as d
import kit66
from checks66 import turn_poses

OUT = d.OUT
SOURCE = d.R64_OUT / 'assembly-guide.json'
SEATED = d.r64.SEATED
GROUP = ('board', 'sockets', 'housing')
OP1 = ('board', 'sockets', 'housing', 'plug', 'op1_wire', 'op1_lead')
FRAME = [[-24, -22, -27], [32, 40, 34]]
MODULES = ('dfr', 'pin_hinge', 'op1_clips')

INSERT = [
    ('Thread the white plug up from below',
     'Leave the black switch and the retainer off and unplug the white plug from the board. '
     'Tip the plug so its lead hangs straight down. Raise it beside the rod, inside the right finger guard, '
     'and up through the small opening at the end of the board seat.'),
    ('Turn the plug upright above the holder',
     'Hold the plug above the holder with its socket face up. The lead runs back down through the opening.'),
    ('Push the board onto the plug',
     'Hold the bare board level, white housing down, and push the housing onto the plug.'),
    ('Lower the board into its three holes',
     'Lower the board straight down. Its three metal sockets drop into the three holes in the holder '
     'while the housing and plug sink into the opening and the lead slides down through it.'),
    ('Press the lead into its channel',
     'From underneath, press the lead up into the open channel beside the rod so it runs towards the hinge end.'),
]
REMOVE = [
    ('Free the lead from its channel', 'With the retainer and switch off, pull the lead down out of its channel.'),
    ('Lift the board straight up', 'Lift the board straight off its three holes. The plug and lead come up through the opening.'),
    ('Pull the board off the plug', 'Above the holder, pull the board off the white plug.'),
    ('Tip the plug so its lead hangs down', 'Turn the plug so its lead hangs straight down through the opening.'),
    ('Lower the plug back through the opening', 'Lower the plug through the opening and out beside the rod.'),
]


def matrix(values):
    return np.vstack([np.reshape(values, (3, 4)), [0, 0, 0, 1]])


def flat(m):
    return [round(float(v), 6) for v in np.asarray(m)[:3].ravel()]


def seated(actor):
    return np.eye(4) if actor in ('op1_wire', 'op1_lead') else matrix(SEATED[actor])


def frame(base, plug=None, group=None, lead=None, lead_morph=None, wire_morph=None):
    """One sample: the fixed carrier and rod plus whichever OP1 actors are present."""
    sample = dict(base)
    if plug is not None:
        sample['plug'] = flat(plug @ seated('plug'))
    if group is not None:
        for actor in GROUP:
            sample[actor] = flat(group @ seated(actor))
    morphs = {}
    if lead is not None:
        sample['op1_lead'] = flat(lead)
        morphs['op1_lead'] = round(float(lead_morph), 4)
    if wire_morph is not None:
        sample['op1_wire'] = flat(group if group is not None else np.eye(4))
        morphs['op1_wire'] = round(float(wire_morph), 4)
    if morphs:
        sample['morphs'] = morphs
    return sample


def insertion(base):
    """Five steps of samples, each a list. Every transition between steps is continuous."""
    lift = d.translation
    heights = np.linspace(*d.THREAD_Z, int(d.THREAD_Z[1] - d.THREAD_Z[0]) + 1)
    turning = turn_poses(19)
    above = d.mate_pose(d.LIFT)
    push = [lift((0, 0, d.LIFT + h)) for h in np.linspace(10, 0, 11)]
    lower = [lift((0, 0, h)) for h in np.linspace(d.LIFT, 0, int(d.LIFT) + 1)]
    steps = [
        [frame(base, plug=d.tip_pose(z), lead=lift((0, 0, z-d.THREAD_Z[1])), lead_morph=0) for z in heights],
        [frame(base, plug=m, lead=np.eye(4), lead_morph=t) for m, t in zip(turning, np.linspace(0, 1, len(turning)))],
        [frame(base, plug=above, lead=np.eye(4), lead_morph=1, group=g) for g in push],
        [frame(base, plug=g, group=g, wire_morph=0) for g in lower],
        [frame(base, plug=np.eye(4), group=np.eye(4), wire_morph=t) for t in np.linspace(0, 1, 11)],
    ]
    return steps


def op1_steps(module, base):
    samples = insertion(base)
    durations = (3.2, 2.2, 1.6, 2.6, 1.6)
    inserted = [dict(title=t, caption=c, duration=dur, samples=s, frameBounds=FRAME)
                for (t, c), dur, s in zip(INSERT, durations, samples)]
    removed = [dict(title=t, caption=c, duration=dur, samples=list(reversed(s)), frameBounds=FRAME)
               for (t, c), dur, s in zip(REMOVE, reversed(durations), reversed(samples))]
    return inserted, removed


def install(module):
    steps = module['steps']
    first = next(i for i, s in enumerate(steps) if s['title'] == 'Seat the OP1 board')
    base = {k: v for k, v in steps[first]['samples'][0].items() if k in ('carrier', 'rod')}
    inserted, removed = op1_steps(module, base)
    rebuilt = []
    for step in steps:
        if step['title'] == 'Seat the OP1 board':
            rebuilt.extend(inserted)
        elif step['title'] == 'Lift the OP1 board':
            rebuilt.extend(removed)
        else:
            for sample in step['samples']:
                if 'op1_wire' in sample:
                    sample.setdefault('morphs', {})['op1_wire'] = 1.0
            rebuilt.append(step)
    module['steps'] = rebuilt
    actors = module['actors']
    actors['op1_wire'] = dict(file='guide/' + d.LEAD_FILES['drop'], morphFile='guide/' + d.LEAD_FILES['route'],
                              label='OP1 lead from the white plug', color='#a3b8c5')
    actors['op1_lead'] = dict(file='guide/' + d.LEAD_FILES['thread'], morphFile='guide/' + d.LEAD_FILES['turn_end'],
                              label='OP1 lead while the plug is threaded', color='#a3b8c5')
    actors['plug'] = dict(actors['plug'], label='White plug on the wand harness')
    actors['housing'] = dict(actors['housing'], label='Fixed white housing under the OP1 board')
    actors['board'] = dict(actors['board'], label='OP1 board, switch removed')
    notes = [n for n in module.get('annotations', []) if n.get('step') != 'Seat the OP1 board']
    opening = [*d.THREAD_XY, 9.6]
    plug_local = np.linalg.solve(seated('plug'), [*np.mean(np.reshape(d.hardware()['plug'].bounding_box(), (2, 3)), axis=0), 1])[:3]
    board_local = np.linalg.solve(seated('board'), [*b_point(3.2), 11.0, 1])[:3]
    notes += [
        dict(side='right', actor='carrier', point=opening, step=INSERT[0][0],
             title='Opening for the white plug and its lead. Only this end was enlarged; the three socket holes are unchanged.'),
        dict(side='left', actor='plug', point=plug_local.tolist(), step=INSERT[0][0],
             title='Tip the plug so the lead trails straight down behind it.'),
        dict(side='left', actor='board', point=board_local.tolist(), step=INSERT[3][0],
             title='Three metal sockets, three fixed holes. The board rests on the deck around them.'),
        dict(side='right', actor='carrier', point=[8.4, 26.0, 6.0], step=INSERT[4][0],
             title='The lead runs in this open channel under the deck, clear of the rod.'),
    ]
    module['annotations'] = notes
    module['annotationsByStep'] = True


def b_point(y):
    return d.b.board_point(0, y)


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write(register=False, current=False):
    d.save_lead_meshes()
    guide = json.loads(SOURCE.read_text())
    hashes = {}
    for name, module in guide['modules'].items():
        if name in MODULES:
            install(module)
            if name == 'op1_clips':
                module['note'] = ('The white plug threads up through a small opening beside the three socket holes. '
                                  'Plug the board onto it above the holder, then lower the board into its holes.')
            else:
                module['note'] = ('Fit the OP1 board first: thread its white plug up through the small opening, plug the '
                                  'board onto it and lower it into its three holes. Then fit the mouse switch and the paddle.')
        if name == 'battery':
            module['note'] = ('The broad face of the battery rests against the keypad base. The rod-side rail runs the full '
                              'length; the outer rail tapers away towards the open end. Pull the exposed end to remove the pack.')
        for actor, spec in module['actors'].items():
            for field in ('file', 'morphFile'):
                if field not in spec:
                    continue
                if spec[field].startswith('guide/'):
                    src = OUT / spec[field]
                elif actor == 'carrier' and field == 'file':
                    src = OUT / d.HOLDER
                else:
                    src = (SOURCE.parent / spec[field]).resolve(strict=True)
                key = os.path.relpath(src, OUT)
                spec[field] = key
                hashes.setdefault(key, digest(src))
        if 'status' in module:
            module['status'] = 'R66 design · physical fit untested'
    guide['print_components']['keys'] = sorted(row['name'] for row in kit66.parts())
    guide['revision'] = 'R66'
    guide['physical_fit_verified'] = False
    guide['sources'] = dict(generator_sha256=digest(__file__), upstream_guide_sha256=digest(SOURCE),
                            route_report_sha256=digest(OUT / 'op1-route.json') if (OUT / 'op1-route.json').exists() else None,
                            meshes_sha256=hashes)
    dest = OUT / 'assembly-guide.json'
    dest.write_text(json.dumps(guide, separators=(',', ':'), allow_nan=False) + '\n')
    if register or current:
        sys.path.insert(0, str(d.HARDWARE / 'carbon-rod-holders/assembly'))
        from register_assembly import register_assembly
        register_assembly(dest, 'r66', 'R66 · Three-hole OP1 seat with a plug opening', group_keys=True, make_current=current)
    return dest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--register', action='store_true')
    parser.add_argument('--current', action='store_true', help='also make R66 the default revision')
    args = parser.parse_args()
    print(write(args.register, args.current))
