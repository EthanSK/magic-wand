"""Assembly guide for R58. It reuses the R57 guide builder and swaps in the changed parts.

Changes from the R57 guide:
- the R58 key holder, paddle and plain OP1 retainer replace the R57 ones;
- every key part is shown 1.42 mm lower, on the lowered seats;
- the battery view shows the pouch sliding into the tray under the upper-left key. The separate
  rod-mounted battery holder is no longer part of this assembly;
- labels name the bought board, the bought switch and the printed features that hold them.

Run after build58.py, checks58.py and carrier58.py. The finished meshes and check results are
copied into exports/ beside the guide, because the guide stores paths relative to that folder.
Nothing is registered in the catalog unless --register is given.
"""
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import sys

import build58 as n
import carrier58 as c

m, b = n.m, n.b
import guide57 as base  # noqa: E402

g = base.g
OUT = n.HERE / 'exports'
R57_OUT = n.R57 / 'exports'
STATUS = 'Design candidate · not printed or fitted'
BACKERS = ('Socket_Backer_Left', 'Socket_Backer_Right')
PRINTED = ['Key_Carrier', 'Touch_Paddle', 'OP1_Lid_Stop', 'Hinge_Pin_Snug', *BACKERS]
REUSED = ['Hinge_Pin', 'Pin_Clip', 'DFR_Post_Bar', 'DFR_Clip_Left', 'DFR_Clip_Right']
MESHES = (*PRINTED, 'OP1_Lid_Plain', 'Battery_Pack')
RECEIPTS = ('dimensions.json', 'mechanical-fit.json', 'carrier.json')
RETAINER_STEP = 'Fit the OP1 retainer'
RETAINER_CAPTION = ('Hold the paddle down. Slide the retainer in from the front, along both rails and '
                    'over the OP1 board, until the latch seats.')
BATTERY_TRAVEL = 34.0


def collect(source=n.EXPORT):
    """Copy the built meshes and check results beside the guide."""
    OUT.mkdir(parents=True, exist_ok=True)
    if Path(source).resolve() == OUT.resolve():
        return
    for name in (*(f'{mesh}-assembly.stl' for mesh in MESHES), *RECEIPTS):
        shutil.copy2(Path(source) / name, OUT / name)


def reused(name):
    return os.path.relpath(R57_OUT / name, OUT)


def labels():
    """Annotations in each actor's own mesh coordinates. Board and switch meshes are stored 3.3 mm
    forward and 0.2 mm below their R53 position; the holder, lead and retainer are stored in place."""
    barrel = b.board_point(0, 1.95)       # middle of the three socket barrels
    finger = b.board_point(0, -6.25)
    eyelet = b.board_point(0, 11.65)
    cover = b.board_point(4.3, 4.0)
    body = b.board_point(0, 1.95)
    seat, fit = 'Seat the OP1 board', 'Fit the mouse switch'
    return [
        dict(side='left', actor='carrier', point=[barrel[0], barrel[1], b.PCB_Z - 0.4], step=seat,
             title='Three floor openings, one under each socket barrel of the bought board. Their pointed shape is intended.'),
        dict(side='left', actor='carrier', point=[finger[0], finger[1], b.PCB_Z + 0.3], step=seat,
             title='Printed finger under each board eyelet. It locates the board. No screws.'),
        dict(side='right', actor='board', point=[eyelet[0], eyelet[1] - 3.3, b.PCB_TOP - 0.2], step=seat,
             title='Bought OP1 board. Its two large eyelets sit over the two printed fingers.'),
        dict(side='right', actor='op1_wire', point=[8.1, 16.9, 4.0], step=seat,
             title='The lead leaves through this open channel beside the rod.'),
        dict(side='right', actor='switch', point=[body[0], body[1] - 3.3, b.BODY_TOP - 0.2], step=fit,
             title='Bought switch. Its three pins plug into the board sockets. It fits either way round.'),
        dict(side='left', actor='lid', point=[cover[0], cover[1], b.LID_Z[1]], step=RETAINER_STEP,
             title='The retainer covers the board and latches in the left rail. The raised ends limit paddle lift.'),
    ]


def is_pose(value):
    return isinstance(value, (list, tuple)) and len(value) == 12


def move_key_poses(module, measurements):
    """Use the installed switch and socket offsets from the carrier fit check."""
    offsets = {name.removeprefix('key_'): g.translation(pose['moved_mm'])
               for name, pose in measurements['key_poses'].items()}
    moved = set()
    for step in module['steps']:
        for sample in step['samples']:
            for actor, value in sample.items():
                index = actor.rsplit('_', 1)[-1]
                if index in offsets and is_pose(value):
                    sample[actor] = g.pack(offsets[index] @ g.unpack(value))
                    moved.add(actor)
    return sorted(moved)


def battery_module(modules):
    """The pouch slides into the tray from the left, past the sprung hook, and out again."""
    like = modules['dfr']
    seated = like['steps'][-1]['samples'][-1]
    actors = {name: dict(actor) for name, actor in like['actors'].items() if name == 'carrier' or name.startswith('rod')}
    actors['battery'] = dict(file='Battery_Pack-assembly.stl', label='Bought Micron 72217 pouch, 27 × 11.8 × 3.9 mm', color='#5b7fd6')
    state = {name: seated.get(name, g.pack(g.I)) for name in actors}
    state['battery'] = g.pack(g.translation([-BATTERY_TRAVEL, 0, 0]))
    steps = []
    g.add(steps, 'Slide in the battery', 'Hold the holder with its underside up. Slide the pouch in from the left, flat on the shelf, '
          'until the sprung hook closes behind its end. Leave the plug outside the tray.', state, ('battery',), [BATTERY_TRAVEL, 0, 0])
    steps.append(g.reverse(steps[0], 'Remove the battery', 'Press the sprung finger back with a fingernail and slide the pouch out by its body. Do not pull the leads.'))
    x, y, z = c.MOUTH_X + 0.6, c.REAR_Y - 0.5, sum(c.LEAF[1:]) / 2
    notes = [
        dict(side='left', actor='carrier', point=[x, y, z], step='Slide in the battery',
             title='Sprung finger with a hook. It holds the end of the pouch and does not squeeze it.'),
        dict(side='right', actor='carrier', point=[c.END_X + 0.4, c.ROOM_Y[0] + 3.0, c.FLOOR_Z + 2.0], step='Slide in the battery',
             title='Open in front of the short end wall, so leads at this end lie in from the front.'),
        dict(side='left', actor='carrier', point=[-24.0, c.SOCKET_PATH[2], c.FLOOR_Z - 0.6], step='Slide in the battery',
             title='The shelf stops here. With the battery out, the upper-left key socket still loads from below.'),
    ]
    return dict(label='Battery in the key holder', rotation=like['rotation'], actors=actors, steps=steps, annotations=notes, status=STATUS,
                note='The pouch end and tray stand out past the left edge of the holder. Lead exit end and slack are not confirmed on the bought pack.')


def socket_backers_module(keys, rotation):
    """The two loose strips support the lower sockets while their switches seat."""
    frames = keys['steps'][-1]['samples'][-1]
    visible = ('carrier', 'rod', 'socket_0', 'socket_2', 'switch_0', 'switch_2')
    actors = {name: keys['actors'][name] for name in visible}
    state = {name: frames[name] for name in visible}
    for actor, part, offset in (('left_backer', BACKERS[0], -30), ('right_backer', BACKERS[1], 30)):
        actors[actor] = dict(file=f'{part}-assembly.stl', label='Socket backing strip', color='#69b8c2')
        state[actor] = g.pack(g.translation([offset, 0, 0]))
    for name in ('switch_0', 'switch_2'):
        state[name] = g.pack(g.translation([0, 0, 10]) @ g.unpack(state[name]))
    steps = []
    g.add(steps, 'Support the lower-left socket', 'Slide the backing strip in from the left so it sits beneath the black socket.',
          state, ('left_backer',), [30, 0, 0])
    g.add(steps, 'Support the lower-right socket', 'Slide the second strip in from the right.',
          state, ('right_backer',), [-30, 0, 0])
    g.add(steps, 'Seat both lower switches', 'Brace each strip close to its socket while pressing the switch in from above.',
          state, ('switch_0', 'switch_2'), [0, 0, -10])
    g.add(steps, 'Remove the left strip', 'Slide the left strip out once the switch is seated.',
          state, ('left_backer',), [-30, 0, 0])
    g.add(steps, 'Remove the right strip', 'Slide the right strip out once the switch is seated.',
          state, ('right_backer',), [30, 0, 0])
    return dict(label='Support the lower sockets', rotation=rotation, status=STATUS,
                actors=actors, steps=steps, note='The backing strips are removable tools for pressing in the lower switches.')


def integrate_battery_in_whole_rod(modules):
    """The pouch loads into the keys after the sockets. It has no rod mount."""
    keys, whole = modules["key"], modules["whole"]
    battery = modules["battery"]
    install = battery["steps"][0]
    parked = install["samples"][0]["battery"]
    keys["actors"]["battery"] = battery["actors"]["battery"]
    for step in keys["steps"]:
        for sample in step["samples"]:
            sample["battery"] = parked
    fitted_keys = keys["steps"][-1]["samples"][-1]
    keys["steps"].append({
        **install, "samples": [{**fitted_keys, "battery": pose["battery"]} for pose in install["samples"]],
    })
    whole["rodMounts"] = [mount for mount in whole["rodMounts"] if mount["id"] != "battery"]
    cable = next(mount for mount in whole["rodMounts"] if mount["id"] == "cable")
    cable["caption"] = "Fit the empty cable clip between the key holder and the XIAO before feeding the wires."
    whole["note"] = "The battery slides into the key holder. The keys, cable clip and XIAO holder slide onto the rod."
    whole["finalCaption"] = "Check the battery latch, the pad click, the XIAO keeper and the wire route."


def build(fit, carrier_fit):
    base.OUT = OUT
    base.NAMES = dict(
        carrier=('Key_Carrier-assembly.stl', 'Key holder with flush key seats and battery tray', '#9d4139'),
        cap=('Touch_Paddle-assembly.stl', 'Paddle with one long contact bar', '#d78845'),
        post_bar=(reused('DFR_Post_Bar-assembly.stl'), 'Two-post bar (R57, reused)', '#ba75ae'),
        hinge_pin=(reused('Hinge_Pin-assembly.stl'), 'Hinge pin (R57, reused)', '#f1c35d'),
        pin_clip=(reused('Pin_Clip-assembly.stl'), 'Pin clip (R57, reused)', '#6fcf7f'),
        lid=('OP1_Lid_Stop-assembly.stl', 'OP1 board retainer with lift stop', '#47b3aa'))
    base.PRINTED = PRINTED
    guide = base.build(fit)
    modules = guide['modules']
    notes = labels()
    for name in ('dfr', 'pin_hinge', 'op1_clips'):
        module = modules[name]
        module['status'] = STATUS
        present = {step['title'] for step in module['steps']}
        module['annotations'] = [dict(note) for note in notes if note['actor'] in module['actors'] and note['step'] in present]
        for step in module['steps']:
            if step['title'] == RETAINER_STEP:
                step['caption'] = RETAINER_CAPTION
    modules['dfr']['note'] = ('The switch body locates the paddle sleeve. One long rounded bar under the paddle presses the button. '
                              'The retainer holds the OP1 board and limits paddle lift.')
    modules['pin_hinge']['label'] = 'Pin hinge, OP1 board and retainer'
    modules['pin_hinge']['note'] = ('Complete build of the click: bought OP1 board and lead, bought switch, touch board, paddle, '
                                    'loose pin and its clip, then the board retainer with its lift stop.')
    modules['op1_clips']['note'] = 'Hold the paddle down while sliding the retainer over the OP1 board.'
    lowered = move_key_poses(modules['key'], carrier_fit)
    modules['socket_backers'] = socket_backers_module(modules['key'], modules['finger_rest']['rotation'])
    modules['key']['status'] = STATUS
    removed = [name for name in modules if 'battery' in name.lower()]
    for name in removed:
        del modules[name]
    modules['battery'] = battery_module(modules)
    integrate_battery_in_whole_rod(modules)
    guide.update(revision='R58', physical_fit_verified=False)
    components = guide['print_components']
    for group, parts in list(components.items()):
        if isinstance(parts, list):
            components[group] = [part for part in parts if 'battery' not in str(part).lower()]
    components['keys'] = PRINTED
    guide['reuse_components'] = dict(keys=REUSED, baseline_retainer='OP1_Lid (R53, with towers) fits the R57 paddle only')
    guide['r58_changes'] = dict(key_parts_shown_lower_mm=carrier_fit['change']['moved_down_mm'],
                               row_pitch_mm=carrier_fit['key_layout']['row_pitch_mm'],
                               key_actors_lowered=lowered, battery_views_removed=removed)
    digest = lambda p: sha256(Path(p).read_bytes()).hexdigest()
    guide['sources']['generator_sha256'] = digest(__file__)
    guide['sources']['base_generator_sha256'] = digest(base.__file__)
    for name in ('Battery_Pack', *BACKERS):
        file = f'{name}-assembly.stl'
        guide['sources']['meshes_sha256'][file] = digest(OUT / file)
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
    print(json.dumps(dict(modules=summary, print_components=guide['print_components'], r58_changes=guide['r58_changes']), indent=1))
    if '--register' in sys.argv:
        from register_assembly import register_assembly
        register_assembly(path, 'r58', 'R58 trial · Flush key seats, battery tray and smooth click', group_keys=True)
