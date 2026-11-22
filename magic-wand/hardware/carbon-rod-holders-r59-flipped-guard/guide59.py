"""Assembly guide for R59. It reuses the R58 guide builder and swaps in what R59 changes.

- the R59 key holder (guard rails, battery sleeve) replaces the R58 holder in every view;
- a finger-guard view shows both guards sliding onto their rails from the front edge, and off again;
- the battery view shows the pouch going in from the rear beside the rod, then its cap;
- the R58 backing-strip view is dropped: with a guard off, the lower sockets are open.
The guide uses the revised R59 retainers and clips and the unchanged R58 paddle.

Run after carrier59.py. Nothing is registered in the catalog unless --register is given.
"""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

import numpy as np

import carrier59 as f

c, R58 = f.c, f.R58
import guide58 as base  # noqa: E402  (R58 builder; R58 files are not changed)

g = base.g
OUT = f.HERE / 'exports'
STATUS = 'Design candidate · not printed or fitted'
R58_PARTS = ('Touch_Paddle', 'Hinge_Pin_Snug', 'Socket_Backer_Left', 'Socket_Backer_Right')
OPTIONAL = ['Hinge_Pin_Snug', 'Socket_Backer_Left', 'Socket_Backer_Right']
R58_RECEIPTS = ('mechanical-fit.json', 'dimensions.json')
NEW = ('Key_Carrier', 'Finger_Guard_Left', 'Finger_Guard_Right', 'Battery_Cap', 'OP1_Lid_Stop', 'Pin_Clip', 'DFR_Clip_Left', 'DFR_Clip_Right')
PRINTED = [*NEW, 'Pin_Clip_Spare', 'Touch_Paddle', 'Hinge_Pin', 'DFR_Post_Bar', *OPTIONAL]
HOLDER_LABEL = 'Key holder with guard rails and battery sleeve'
GUARD_TRAVEL, BATTERY_TRAVEL, CAP_TRAVEL = 16.0, 30.0, 12.0


def collect():
    """Copy the unchanged R58 click meshes and their check results beside the R59 guide."""
    OUT.mkdir(parents=True, exist_ok=True)
    for name in (*(f'{part}-assembly.stl' for part in R58_PARTS), *R58_RECEIPTS):
        shutil.copy2(R58 / 'exports' / name, OUT / name)


def guard_module(keys, rotation):
    """Both guards slide onto the rails under the front rim, then off again."""
    actors = {name: dict(actor) for name, actor in keys['actors'].items()}
    seated = keys['steps'][-1]['samples'][-1]
    state = {name: seated.get(name, g.pack(g.I)) for name in actors}
    for side, color in (('left', '#4f9d69'), ('right', '#3f8f8a')):
        actors[f'guard_{side}'] = dict(file=f'Finger_Guard_{side.capitalize()}-assembly.stl', label=f'Slide-on finger guard, {side}', color=color)
        state[f'guard_{side}'] = g.pack(g.translation([0, -GUARD_TRAVEL, 0]))
    steps = []
    for side in ('left', 'right'):
        g.add(steps, f'Slide on the {side} guard', 'Fit and wire the lower socket first, with the guard off. Then hold the holder underside up, '
              'line the two guard arms up with the two rails under the front rim and push the guard back until it wedges and its noses meet the rim.',
              state, (f'guard_{side}',), [0, GUARD_TRAVEL, 0])
    steps.append(g.reverse(steps[1], 'Pull off the right guard', 'Pull the guard straight forward off its rails. The lower socket is then open from every side.'))
    steps.append(g.reverse(steps[0], 'Pull off the left guard', 'Pull the guard straight forward off its rails.'))
    x, y = f.RAIL_X[0], f.RAIL_Y[0] + 2.0
    notes = [
        dict(side='right', actor='carrier', point=[x, y, f.RAIL_Z[0]], step='Slide on the right guard',
             title='Rail under the front rim. It widens toward the rear, so the guard wedges on by hand.'),
        dict(side='left', actor='carrier', point=[-x, y, f.RAIL_Z[0]], step='Slide on the left guard',
             title='The left side has the same two rails and the same outer arm as the right.'),
        dict(side='right', actor='guard_right', point=[21.0, f.GUARD_Y[1] - 0.5, f.SHELF_Z[1]], step='Slide on the right guard',
             title='Open toward the upper row: the socket can still be reached and pushed up from here.'),
    ]
    return dict(label='Finger guards', rotation=rotation, actors=actors, steps=steps, annotations=notes, status=STATUS,
                note='Each guard is a separate printed part held at the front edge. Fit the lower sockets with the guards off.')


def battery_module(modules):
    """The pouch slides into the sleeve from the rear, beside the rod, then the cap goes on."""
    like = modules['dfr']
    seated = like['steps'][-1]['samples'][-1]
    actors = {name: dict(actor) for name, actor in like['actors'].items() if name == 'carrier' or name.startswith('rod')}
    actors['battery'] = dict(file='Battery_Pack-assembly.stl', label='Bought Micron 72217 pouch, 27 × 11.8 × 3.9 mm', color='#5b7fd6')
    actors['battery_cap'] = dict(file='Battery_Cap-assembly.stl', label='Slip-on cap for the battery end', color='#c9a227')
    state = {name: seated.get(name, g.pack(g.I)) for name in actors}
    state['battery'] = g.pack(g.translation([0, BATTERY_TRAVEL, 0]))
    state['battery_cap'] = g.pack(g.translation([0, BATTERY_TRAVEL + CAP_TRAVEL, 0]))
    steps = []
    g.add(steps, 'Slide in the battery', 'Slide the pouch into the sleeve from the rear, beside the rod, until it meets the stop. '
          'The rod can stay in. Trim the print-base tab under the rear of the sleeve flush before fitting the battery. The plug stays outside.', state, ('battery',), [0, -BATTERY_TRAVEL, 0])
    g.add(steps, 'Push on the cap', 'Lay the leads out through the open side of the cap, then push the cap over the pouch end until it clicks under the sleeve.',
          state, ('battery_cap',), [0, -BATTERY_TRAVEL - CAP_TRAVEL, 0])
    steps.append(g.reverse(steps[1], 'Pull off the cap', 'Pull the cap straight back.'))
    steps.append(g.reverse(steps[0], 'Remove the battery', 'Slide the pouch out by its body. Do not pull the leads.'))
    x = sum(f.SLEEVE_X) / 2
    notes = [
        dict(side='left', actor='carrier', point=[f.SLEEVE_X[0] - 0.4, f.BED_Y - 1.0, 3.0], step='Slide in the battery',
             title='Sleeve walls run fore and aft and carry the load. Nothing squeezes the pouch.'),
        dict(side='left', actor='carrier', point=[f.SOCKET_WINDOW[0] - 2.0, f.SOCKET_WINDOW[1] - 3.0, 0.2], step='Slide in the battery',
             title='Open here so the upper-left key socket still loads from below with the battery out.'),
        dict(side='right', actor='battery_cap', point=[f.SLEEVE_X[1], f.BED_Y + 4.0, 3.0], step='Push on the cap',
             title='Open side for the leads. The bought two-pin plug stays outside.'),
    ]
    return dict(label='Battery in the key holder', rotation=like['rotation'], actors=actors, steps=steps, annotations=notes, status=STATUS,
                note=f'The pouch lies along the rod inside the holder\'s own width. Its end and the cap stand {f.CAP_DEPTH:g} mm past the rear face. '
                     'Lead exit end and slack are not confirmed on the bought pack.')


def swap_click_parts(modules):
    """Show the R59 pin clip and the two thicker post clips. Inherited clip actors carry a stored
    offset, so each R59 clip mesh is saved once more in that actor's own coordinates."""
    seated = modules['dfr']['steps'][-1]['samples'][-1]
    for name in base.base.CLIPS:
        actor = modules['dfr']['actors'][name]
        pose = np.vstack([np.asarray(g.unpack(seated[name]), float)[:3], [0, 0, 0, 1]])
        old = f.b.load((OUT / actor['file']).resolve())
        box = old.transform(pose[:3].tolist()).bounding_box()
        side = 'Left' if box[0] + box[3] < 0 else 'Right'
        mesh = f.b.load(OUT / f'DFR_Clip_{side}-assembly.stl').transform(np.linalg.inv(pose)[:3].tolist())
        f.b.save_closed(OUT / f'DFR_Clip_{side}-guide.stl', mesh)
        for module in modules.values():
            if name in module['actors']:
                module['actors'][name].update(file=f'DFR_Clip_{side}-guide.stl', label=f'Touch-board post clip 1.4 mm, {side.lower()}')
                module['actors'][name].pop('morphFile', None)
    for module in modules.values():
        if 'pin_clip' in module['actors']:
            module['actors']['pin_clip'].update(file='Pin_Clip-assembly.stl', label='Pin clip with lowered grip')
        if 'lid' in module['actors']:
            module['actors']['lid']['label'] = 'OP1 board retainer with lift stop (longer tower stems)'


def integrate_in_keys_and_whole_rod(modules):
    """Guards, battery and cap join the key assembly after the sockets. None of them mounts on the rod."""
    keys, whole = modules['key'], modules['whole']
    extra = []
    for source, step_ids in ((modules['finger_guards'], (0, 1)), (modules['battery'], (0, 1))):
        for index in step_ids:
            extra.append(source['steps'][index])
        for name, actor in source['actors'].items():
            keys['actors'].setdefault(name, actor)
    added = ('guard_left', 'guard_right', 'battery', 'battery_cap')
    parked = {name: next(step['samples'][0][name] for step in extra if name in step['samples'][0]) for name in added}
    for step in keys['steps']:
        for sample in step['samples']:
            sample.update(parked)
    state = dict(keys['steps'][-1]['samples'][-1])
    for step in extra:
        moving = [name for name in added if name in step['samples'][0] and step['samples'][0][name] != step['samples'][-1][name]]
        samples = [{**state, **{name: pose[name] for name in moving}} for pose in step['samples']]
        keys['steps'].append({**step, 'samples': samples})
        state = dict(samples[-1])
    whole['rodMounts'] = [mount for mount in whole.get('rodMounts', []) if mount['id'] != 'battery']
    whole['note'] = ('The battery slides into the key holder from the rear and both finger guards slide onto its front edge. '
                     'The keys, cable clip and XIAO holder slide onto the 500 mm rod.')
    whole['finalCaption'] = 'Check both guards are wedged on, the battery cap, the pad click, the XIAO keeper and the wire route.'


def build(fit, carrier_fit):
    base.OUT = OUT
    base.PRINTED = PRINTED
    base.BACKERS = ()
    base.battery_module = battery_module
    base.socket_backers_module = guard_module
    base.integrate_battery_in_whole_rod = lambda modules: None
    guide = base.build(fit, carrier_fit)
    modules = guide['modules']
    modules['finger_guards'] = modules.pop('socket_backers')
    swap_click_parts(modules)
    integrate_in_keys_and_whole_rod(modules)
    for name in ('dfr', 'pin_hinge'):
        for step in modules[name]['steps']:
            if step['title'] == 'Seat the touch board':
                step['caption'] = ('Plug the included 3-pin Gravity lead into the white socket before seating the touch board. '
                                   'Lower the board over both posts and leave wire slack past the lowered pin-clip grip.')
        modules[name]['annotations'].append(dict(side='right', actor='pin_clip', point=[0.0, f.m.AXIS_Y - 1.5, f.b.SEAT_Z + 0.65], step='Press in the pin clip',
            title='The front of the grip is lower here, under the bought Gravity plug and its three wires. The plug comes with the touch board; it is not printed.'))
    for name in ('pin_hinge', 'op1_clips'):
        modules[name]['annotations'].append(dict(side='left', actor='carrier', point=[*f.b.board_point(-6.4, -8.0), f.b.LID_Z[0]], step=base.RETAINER_STEP,
            title='The retainer rides on this upper ledge, under the two rail lips. The step below it is the OP1 board\'s own slot, not a track.'))
    for module in modules.values():
        if 'carrier' in module['actors']:
            module['actors']['carrier']['label'] = HOLDER_LABEL
    if 'finger_rest' in modules:
        modules['finger_rest']['note'] = 'R59 has no built-in finger rest. See the Finger guards view for the two slide-on guards.'
        modules['finger_rest']['status'] = STATUS
        modules['finger_rest']['annotations'] = []
    guide.update(revision='R59', physical_fit_verified=False)
    guide['print_components']['keys'] = PRINTED
    guide['reuse_components'] = dict(keys=[], note='R59 is a complete kit. Nothing is taken from an earlier print.')
    guide['optional_components'] = dict(keys=OPTIONAL, note='Hold a lower socket up with a fingertip when its guard is off. A backing strip is only for backing a socket with the guard left on.')
    guide['r59_changes'] = dict(finger_guards='separate, slide on from the front edge', battery='lengthwise sleeve, rear loading, slip-on cap',
                                backing_strips='optional', whole_rod_view='guards, battery and cap join the key assembly steps',
                                click_parts='R59 retainer, pin clip and post clips; R58 paddle; R57 pin and post bar')
    digest = lambda p: sha256(Path(p).read_bytes()).hexdigest()
    guide['sources']['generator_sha256'] = digest(__file__)
    guide['sources']['r58_generator_sha256'] = digest(base.__file__)
    mesh_paths = {actor[field] for module in modules.values() for actor in module['actors'].values()
                  for field in ('file', 'morphFile', 'compareFile') if actor.get(field)}
    guide['sources']['meshes_sha256'] = {path: digest(OUT / path) for path in sorted(mesh_paths)}
    return guide


if __name__ == '__main__':
    collect()
    fit = json.loads((OUT / 'mechanical-fit.json').read_text())
    carrier_fit = json.loads((OUT / 'carrier.json').read_text())
    guide = build(fit, carrier_fit)
    path = OUT / 'assembly-guide.json'
    path.write_text(json.dumps(guide, separators=(',', ':'), allow_nan=False) + '\n')
    summary = {name: dict(actors=len(module['actors']), steps=len(module['steps']), annotations=len(module.get('annotations', [])))
               for name, module in guide['modules'].items()}
    print(json.dumps(dict(modules=summary, print_components=guide['print_components']), indent=None))
    if '--register' in sys.argv:
        from register_assembly import register_assembly
        register_assembly(path, 'r59', 'R59 trial · Slide-on finger guards and lengthwise battery sleeve', group_keys=True)
