"""Assembly guide for R57: the loose hinge pin and its clip, the longer posts and the full rod.

Run after build57.py and checks57.py. Writes exports/assembly-guide.json. It does not register
the guide in the catalog unless --register is given.
"""
from copy import deepcopy
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys

import numpy as np

import build57 as m

b = m.b
import guide53 as g  # noqa: E402  (shared step helpers; also puts the assembly tools on the path)
from register_assembly import full_length_rods, register_assembly  # noqa: E402

OUT = m.EXPORT
OLD = b.R52 / 'exports'
R53_OUT = m.R53 / 'exports'
BOARD, SWITCH, SENSOR, CLIPS = g.BOARD, g.SWITCH, g.SENSOR, g.CLIPS
TOUCH = ('cap', 'post_bar', *SENSOR, *CLIPS)
LID_FILE = os.path.relpath(R53_OUT / 'OP1_Lid-assembly.stl', OUT)
NAMES = dict(carrier=('Key_Carrier-assembly.stl', 'Key holder with two hinge holes', '#9d4139'),
             cap=('Touch_Paddle-assembly.stl', 'Paddle with switch guide and hinge barrel', '#d78845'),
             post_bar=('DFR_Post_Bar-assembly.stl', 'Two-post bar with longer necks', '#ba75ae'),
             hinge_pin=('Hinge_Pin-assembly.stl', 'Hinge pin', '#f1c35d'),
             pin_clip=('Pin_Clip-assembly.stl', 'Pin clip', '#6fcf7f'),
             lid=(LID_FILE, 'OP1 board retainer (unchanged)', '#47b3aa'))
PRINTED = ['Key_Carrier', 'Touch_Paddle', 'Hinge_Pin', 'Pin_Clip', 'DFR_Post_Bar', 'DFR_Tall_Clip']


def build(fit):
    guide = json.loads((OLD / 'assembly-guide.json').read_text())
    modules = guide['modules']
    for module in modules.values():
        for actor in module['actors'].values():
            for key in ('file', 'morphFile'):
                if key in actor:
                    actor[key] = os.path.relpath((OLD / actor[key]).resolve(), OUT)
    old = modules['dfr']
    references = json.loads((R53_OUT / 'assembly-transforms.json').read_text())['actors']
    actors = {k: deepcopy(old['actors'][k]) for k in ('rod', *BOARD, *SWITCH, *SENSOR, *CLIPS)}
    for actor, (file, label, color) in NAMES.items():
        actors[actor] = dict(file=file, label=label, color=color)
    seated = old['steps'][-1]['samples'][-1]
    state = {k: g.pack(g.I) for k in actors}
    state['rod'] = seated['rod']
    for actor in (*BOARD, *SWITCH, *SENSOR, *CLIPS):
        source = references[actor]
        state[actor] = source['base']
        actors[actor]['file'] = source['file']
        if 'morphFile' in source:
            actors[actor]['morphFile'] = source['morphFile']
    axis = b.board_axis()

    def shift(group, delta):
        for actor in group:
            state[actor] = g.pack(g.translation(delta) @ g.unpack(state[actor]))

    shift(BOARD, [0, 0, 15])
    shift(SWITCH, [0, 0, 29])
    shift(TOUCH, [52, 0, 19])
    shift(('post_bar',), [0, 0, -9])
    shift(SENSOR, [0, 0, 11])
    shift(CLIPS, [0, -8, 11])
    shift(('hinge_pin',), [28, 0, 0])
    shift(('pin_clip',), [0, 0, 11])
    shift(('lid',), -axis * 34)
    steps = []
    add = g.add
    add(steps, 'Seat the OP1 board', 'Feed the plugged-in lead through its outlet, then lower the board straight into the angled pocket until both eyelets settle over the tapered fingers.', state, BOARD, [0, 0, -15])
    add(steps, 'Fit the mouse switch', 'Line the three switch pins up with the OP1 sockets and seat the case squarely.', state, SWITCH, [0, 0, -29])
    add(steps, 'Insert the two-post bar', 'With the paddle off the holder, push both posts up through its two holes from underneath.', state, ('post_bar',), [0, 0, 9])
    add(steps, 'Seat the touch board', 'Lower the DFRobot board onto the two posts. It rests on the pad end, the two side rails and the lands round the posts.', state, (*SENSOR, *CLIPS), [0, 0, -11])
    add(steps, 'Slide on the two small clips', 'Slide the open ends round the post necks above the touch board. The necks are longer than before.', state, CLIPS, [0, 8, 0])
    add(steps, 'Move the paddle over the holder', 'Line the barrel up between the two hinge cheeks. The sleeve faces the mouse switch.', state, TOUCH, [-52, 0, 0])
    add(steps, 'Lower the paddle', 'Lower it so the sleeve surrounds the switch and the barrel sits between the cheeks.', state, TOUCH, [0, 0, -19])
    add(steps, 'Slide in the hinge pin', 'Push the pin through one cheek, the barrel and the other cheek. Do this before the upper key on that side is fitted.', state, ('hinge_pin',), [-28, 0, 0])
    add(steps, 'Press in the pin clip', 'Press the clip down into the slot in the middle of the barrel until its legs snap over the waist of the pin.', state, ('pin_clip',), [0, 0, -11])
    add(steps, 'Fit the OP1 retainer', 'Hold the paddle down. Slide the retainer in from the front, along both rails and over the OP1 board, until the latch seats.', state, ('lid',), axis * 34)
    stop = fit['click']['paddle_meets_switch_case_deg']
    angle = .90 * stop
    pressed = []
    for t in np.linspace(0, 1, 41):
        a = angle * math.sin(math.pi * t) ** 2
        tf = np.vstack([np.asarray(m.hinge_matrix(a)), [0, 0, 0, 1]])
        sample = deepcopy(state)
        for actor in TOUCH:
            sample[actor] = g.pack(tf @ g.unpack(state[actor]))
        travel = max(0., b.FREE_TOP - (tf @ [*b.STATION, b.FREE_TOP, 1])[2])
        sample['plunger'] = g.pack(g.translation([0, 0, -travel]) @ g.unpack(state['plunger']))
        pressed.append(sample)
    steps.append(dict(title='Press the lower half of the pad', caption='Press and release the centre and either lower corner. The switch should click and return freely.', duration=2, samples=pressed))
    mod = dict(label='OP1 and DFRobot paddle', rotation=old['rotation'], actors=actors, steps=steps, annotations=[],
               keysLabel='Key assembly', fitOuterKeysSeparately=True,
               note='The switch body locates the sleeve. The hinge is a loose pin through two holder cheeks and the paddle barrel. Touch-board component heights are estimates.')
    modules['dfr'] = mod
    modules['key']['actors']['carrier'] = actors['carrier']
    modules['finger_rest']['actors']['carrier'] = actors['carrier']
    reverse, subset = g.reverse, g.subset
    remove_hinge = [reverse(steps[9], 'Remove the OP1 retainer', 'Release its latch and slide the retainer out towards the front.'),
                    reverse(steps[8], 'Pull out the pin clip', 'Pinch the top of the clip and pull it straight up.'),
                    reverse(steps[7], 'Withdraw the hinge pin', 'Push the pin out sideways. An upper key on that side has to be out of the way.'),
                    reverse(steps[6], 'Lift out the paddle', 'Lift the barrel from between the cheeks and clear the sleeve from the switch.')]
    remove_keys = [reverse(steps[1], 'Lift out the mouse switch', 'Lift the switch straight up from its three sockets.'),
                   reverse(steps[0], 'Lift the OP1 board', 'Lift the board straight up and guide the lead out of the open channel.')]
    remove_touch = [reverse(steps[5], 'Move the paddle clear', 'Move the lifted paddle clear of the holder.'),
                    reverse(steps[4], 'Remove the two clips', 'Slide both clips away from the post necks. Keep both clips.'),
                    reverse(steps[3], 'Lift the touch board', 'Lift the board clear of the two posts.'),
                    reverse(steps[2], 'Withdraw the post bar', 'Pull the loose two-post bar out from the underside of the paddle.')]
    modules['pin_hinge'] = subset(mod, ('carrier', 'cap', 'hinge_pin', 'pin_clip', 'lid', 'post_bar', *BOARD, *SWITCH, *SENSOR, *CLIPS),
                                  steps + remove_hinge + remove_touch + remove_keys, 'Pin hinge and guide',
                                  'The centre clip locks the loose pin. Reuse the sliding OP1 retainer from the earlier holder kit to hold the board down.')
    modules['op1_clips'] = subset(mod, ('carrier', 'lid', *BOARD, *SWITCH), steps[:2] + [steps[9], remove_hinge[0]] + remove_keys,
                                  'OP1 board retainer', 'Install the touch paddle before sliding its retainer into place.')
    guide.update(revision='R57', physical_fit_verified=False)
    # Printed for R57. The OP1 lid and both 0.8 mm post clips are reused from the earlier print.
    guide['print_components']['keys'] = PRINTED
    guide = full_length_rods(guide, OUT)
    modules = guide['modules']
    files = {a[k] for module in modules.values() for a in module['actors'].values() for k in ('file', 'morphFile') if k in a}
    digest = lambda p: sha256(p.read_bytes()).hexdigest()
    guide['sources'] = dict(upstream_guide_sha256=digest(OLD / 'assembly-guide.json'), generator_sha256=digest(Path(__file__)),
                            meshes_sha256={f: digest(OUT / f) for f in sorted(files)})
    return guide


if __name__ == '__main__':
    fit = json.loads((OUT / 'mechanical-fit.json').read_text())
    guide = build(fit)
    path = OUT / 'assembly-guide.json'
    path.write_text(json.dumps(guide, separators=(',', ':'), allow_nan=False) + '\n')
    if '--register' in sys.argv:
        register_assembly(path, 'r57', 'R57 · Pin hinge and longer touch-board posts', make_current=True, group_keys=True)
