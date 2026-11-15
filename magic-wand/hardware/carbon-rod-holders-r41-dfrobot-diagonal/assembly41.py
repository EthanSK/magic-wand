"""Export R41 and its complete assembly guide from holder41's solids.

Run through geometry_budget.py. Only the key holder, DFRobot bracket, post
clips, OP1 poses and touch-board poses change. R39's battery, XIAO and cable
guides are reused. This script makes no printer connection and sends no print command.

  assembly41.py               check, export meshes/manifest/checks, write guide
  assembly41.py --guide-only  rewrite the guide from the exported meshes
  assembly41.py --register    add R41 to the assembly catalog (after checking)
"""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path

import numpy as np

import holder41 as d
import assembly39 as previous

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
SOURCE = d.R39 / 'exports'
A, H, I = previous.A, d.H, previous.I
CLIP2 = d.CLIP + '_2'
LABEL = 'R41 DFRobot touch with diagonal OP1 click'
OP1_BOARD = ('board', 'sockets', 'housing')
OP1_PLUG = ('plug', 'op1_wire')
MOUSE = ('switch', 'terminals', 'plunger')
BOARD_GROUP = ('sensor', 'electrode', 'connector', 'gravity_pins', 'sensor_lead')
CLIPS = ('clip_left', 'clip_right')
MOVING = ('cap', *BOARD_GROUP, *CLIPS, 'adjustment_screw')
KEPT = ('rod', 'carrier', 'switch_0', 'switch_2', 'switch_3', 'switch_4')
BOARD_LIFT = 12.          # board parked above its posts, bracket frame
CLIP_SLIDE = 6.           # clips slide on from the three-key end (R31 check: 5 mm)
ROD_OFF = -150.           # rod parked clear of the holder's front face
CLICK_STEP = 13           # assembly39.overview() takes the seated keys frame from this step


def lifted(matrix, z):
    return A.move(matrix, (0., 0., z))


def at(local=(0., 0., 0.), angle=None, lift=0.):
    return d.r.placement(angle, local=local, lift=lift).ravel().tolist()


def dfr_actors(r39_dfr):
    """Rod, carrier and Choc switches from R39; every touch and OP1 actor is new."""
    actors = {name: deepcopy(r39_dfr['actors'][name]) for name in KEPT}
    actors['carrier'].update(file='Key_Carrier-assembly.stl', label='Key holder with two fixed hinge supports')
    labels = {
        'board': ('OP1 PCB at 25°, two mounting eyelets', '#208465'),
        'sockets': ('Three underside socket barrels', '#c6a956'),
        'switch': ('Omron 60M switch reference', '#302a42'),
        'plunger': ('Switch plunger under the three-key row', '#eeae6d'),
        'plug': ('Harness plug, pushed in from below', '#fff5de'),
        'op1_wire': ('OP1 lead in the underside groove', '#a3b8c5'),
        'housing': ('Fixed white socket beneath the board', '#eae8df'),
        'terminals': ('Three switch terminals', '#d5b68c'),
        'fasteners': ('Two OP1 PCB screws', '#8294a3'),
    }
    for name, shape in d.hardware().items():
        label, color = labels[name]
        actors[name] = {'file': A.guide_mesh('op1-' + name, shape), 'label': label, 'color': color}
    r = d.r
    touch = {
        'cap': ('Orange hinged bracket: two posts through the board holes, two flexible arms', '#e19753', None),
        'sensor': ('DFRobot DFR0030 V2 board (22 × 35 mm, two holes)', '#303e39', r.sensor()),
        'electrode': ('Gold touch pad', '#ddba59', r.electrode()),
        'connector': ('Gravity socket and plug (estimate)', '#e9e1d2', r.connector()),
        'gravity_pins': ('Gravity socket pin tails (2 mm envelope)', '#b8bcc2', d.gravity_pins()),
        'sensor_lead': ('Gravity lead slack', '#a7777a', r.gravity_lead()),
        'clip_left': ('Left post clip (printed)', '#ffdd68', r.clip(-1)),
        'clip_right': ('Right post clip (printed)', '#ffdd68', r.clip(1)),
        'adjustment_screw': ('M2 × 4 stop screw', '#aeb4c1', d.base.stop_screw(0.)),
    }
    for name, (label, color, shape) in touch.items():
        if shape is not None:
            actors[name] = {'file': A.guide_mesh('dfr-' + name.replace('_', '-'), shape), 'label': label, 'color': color}
    actors['cap'] = {'label': touch['cap'][0], 'file': f'{d.BRACKET}-assembly.stl', 'color': touch['cap'][1]}
    actors['sensor_lead']['frame'] = False
    return actors


def keys_guide(module, checks):
    """Every step is built explicitly from the checked poses."""
    seated = deepcopy(module['steps'][CLICK_STEP]['samples'][-1])
    rest = at()
    setting = checks['stop_settings'][len(checks['stop_settings']) // 2]
    turns = setting['turns_out']

    def screw_pose(angle=None, extra=0., turns_out=turns):
        return at((0., 0., -turns_out * d.PITCH + extra), angle)

    final = {name: seated[name] for name in KEPT}
    final['rod'] = I.copy()
    for name in (*OP1_BOARD, *OP1_PLUG, *MOUSE, 'fasteners'):
        final[name] = I.copy()
    for name in MOVING:
        final[name] = rest.copy()
    final['adjustment_screw'] = screw_pose()
    raised = lifted(rest, 8.)
    board_up = at((0., 0., BOARD_LIFT))
    clips_off = at((0., -CLIP_SLIDE, 0.))

    state = deepcopy(final)
    state['rod'] = A.move(I, (0., ROD_OFF, 0.))
    for name in OP1_BOARD:
        state[name] = lifted(I, d.h32.BOARD_RISE)
    for name in OP1_PLUG:
        state[name] = lifted(I, -9.)
    state['fasteners'] = lifted(I, d.h32.BOARD_RISE + 6.)
    for name in MOUSE:
        state[name] = lifted(I, 8.)
    state['cap'] = A.move(rest, (-36., 0., 8.))
    state['adjustment_screw'] = A.move(screw_pose(extra=-6.), (-36., 0., 8.))
    for name in BOARD_GROUP:
        state[name] = A.move(board_up, (36., 0., 0.))
    for name in CLIPS:
        state[name] = A.move(clips_off, (36., 0., BOARD_LIFT))
    state['morphs'] = {'cap': 0.}
    steps = [previous.stage(
        'Remove Print Supports',
        'Cut the pad ties. Clear supports from the OP1 board slot, the plug opening and lead groove underneath, '
        'and both hinge holes. Check that the bracket arms flex freely and both post clips are clean.',
        [deepcopy(state)])]

    def move(title, caption, changes, morph=None, duration=3, via=None):
        """Straight moves; a `via` pose makes a two-leg route (across, then the checked straight entry)."""
        start = deepcopy(state)
        via = via or {}
        frames = []
        for t in np.linspace(0., 1., 33):
            f = deepcopy(start)
            for name, target in changes.items():
                if name in via:
                    f[name] = (previous.old.lerp(start[name], via[name], 2 * float(t)) if t < .5 else
                               previous.old.lerp(via[name], target, 2 * float(t) - 1.))
                else:
                    f[name] = previous.old.lerp(start[name], target, float(t))
            if morph is not None:
                before = start['morphs']['cap']
                f['morphs'] = {'cap': before + (morph - before) * float(t)}
            frames.append(f)
        state.update(deepcopy(frames[-1]))
        steps.append(previous.stage(title, caption, frames, duration))

    def click(title, caption):
        frames = []
        for angle in [*np.linspace(-d.REST, setting['angle_deg'], 25), *np.linspace(setting['angle_deg'], -d.REST, 25)]:
            f = deepcopy(state)
            for name in MOVING:
                f[name] = at(angle=float(angle))
            f['adjustment_screw'] = screw_pose(float(angle))
            f['plunger'] = lifted(I, -d.base.actuator_travel(float(angle)))
            frames.append(f)
        state.update(deepcopy(frames[-1]))
        steps.append(previous.stage(title, caption, frames, 5))

    move('Lower the OP1 Board',
         'With the holder off the rod, lower the board onto its two seats at its 25° angle. '
         'Its switch end sits under the three-key row; the keys can stay fitted.',
         {n: final[n] for n in OP1_BOARD})
    move('Secure the Board', 'Fit the two kit screws through the eyelets. Tighten gently until the board stops moving.',
         {'fasteners': final['fasteners']})
    move('Connect the Harness Underneath',
         'From below, push the plug up into the white socket. Press its lead into the open groove beside the rod channel '
         'so it leaves at the two-key end. Do this before the holder goes on the rod.',
         {n: final[n] for n in OP1_PLUG})
    move('Seat the Mouse Switch', 'Seat the mouse switch in its three socket barrels. Keep all three pins straight.',
         {n: final[n] for n in MOUSE})
    move('Slide the Holder onto the Rod',
         'Slide the wired holder onto the rod. The plug and lead stay beside the rod channel; do not pull on the lead.',
         {'rod': final['rod']})
    move('Bring the Bracket Over the Supports',
         'Bring the orange bracket above the two fixed supports. The side arms and their pins are part of the bracket.',
         {'cap': raised, 'adjustment_screw': lifted(screw_pose(extra=-6.), 8.)})
    move('Set the OP1 Stop Screw',
         'Fit the M2 × 4 stop screw head-down into the bracket boss. Screw it fully in, then back it out about one turn.',
         {'adjustment_screw': lifted(screw_pose(), 8.)})
    move('Pinch the Bracket Arms', 'Pinch the side arms just enough for their pins to clear the supports. '
         'Do not force them past the centre stop.', {}, 1., 2)
    move('Lower Between the Supports', 'Keep the arms pinched and lower the bracket between the supports.',
         {'cap': rest, 'adjustment_screw': screw_pose()})
    move('Let the Tabs Snap Into the Holes', 'Release the arms so both pins enter the support holes. '
         'Check both sides are retained.', {}, 0., 2)
    move('Plug In and Fit the Board',
         'Plug the Gravity lead into the board, then lower the board over both posts with the gold pad at the three-key end.',
         {n: rest for n in BOARD_GROUP}, via={n: board_up for n in BOARD_GROUP})
    move('Clip the Posts', 'Slide each printed clip onto its post neck from the three-key end until it snaps. '
         'The clips hold the board down.', {n: rest for n in CLIPS}, via={n: clips_off for n in CLIPS})
    click('Touch, Click and Release',
          'Press the gold pad. The bracket pivots onto the OP1 switch under the three-key row. Check that it clicks, '
          'stops on the screw and returns freely. This is a nominal CAD stop, not a promised click.')
    assert steps[CLICK_STEP]['title'] == 'Touch, Click and Release'
    move('Pull Off the Clips', 'To adjust or remove the board, slide both clips off towards the three-key end.',
         {n: clips_off for n in CLIPS})
    move('Lift the Board Off the Posts', 'Lift the board straight up off the posts with its lead attached.',
         {n: board_up for n in BOARD_GROUP})
    move('Pinch to Release the Tabs', 'Pinch the side arms until both pins leave the support holes.', {}, 1., 2)
    move('Lift Off the Bracket', 'Lift the bracket out with the stop screw.',
         {'cap': raised, 'adjustment_screw': lifted(screw_pose(), 8.)})
    move('Adjust the Stop Screw',
         'If it did not click, turn the screw in a quarter turn for more travel. '
         'If it pressed hard after the click, turn it out a quarter turn.',
         {'adjustment_screw': lifted(screw_pose(turns_out=turns - .25), 8.)})
    move('Pinch and Lower It Back', 'Keep the arms pinched and lower the bracket between the supports.',
         {'cap': rest, 'adjustment_screw': screw_pose(turns_out=turns - .25)})
    move('Let the Tabs Snap Back In', 'Release the arms so both pins snap back into the holes.', {}, 0., 2)
    move('Fit the Board Back on the Posts', 'Lower the board over both posts without trapping its lead.',
         {n: rest for n in BOARD_GROUP})
    move('Refit the Clips', 'Slide both clips back onto the post necks until they snap.', {n: rest for n in CLIPS})
    state['adjustment_screw'] = screw_pose()   # the checked click below uses the middle stop setting
    click('Check the Click Again', 'Press the pad again. It should click before the stop and spring back fully.')

    module.update(
        actors=module['actors'], steps=steps, openSeated=False,
        label='DFRobot touch board and diagonal OP1 click', keysLabel='Keys · full assembly',
        status='Fit-trial candidate · not physically tested',
        note=('DFRobot DFR0030 V2 on the R35 two-post bracket with R39 arm roots, squeeze stop and the '
              'adjustable stop. The OP1 board is turned 25° so its switch sits under the three-key row. '
              'Choc keys and heights match R39. Bought board, pin and cable sizes still need a physical fit trial.'))
    pins = d.gravity_pins().bounding_box()
    eyelet = d.board_point(0., d.h32.EYELETS[0])
    plug = d.hardware()['plug'].bounding_box()
    screw = d.base.stop_screw(0.).bounding_box()
    electrode = d.r.electrode().bounding_box()
    module['annotations'] = [
        {'side': 'left', 'actor': 'cap', 'point': [-d.r.POST_X, d.r.hole_y(), d.r.NECK[1]],
         'step': 'Plug In and Fit the Board', 'title': 'Post through the left board hole'},
        {'side': 'right', 'actor': 'clip_right', 'point': [d.r.POST_X + 1.8, d.r.hole_y(), d.r.NECK[0] + d.r.CLIP_T],
         'step': 'Clip the Posts', 'title': 'Clip on the post neck holds the board down'},
        {'side': 'left', 'actor': 'cap', 'point': [-4.1, d.r.AXIS_Y, d.r.h29.AXIS_Z],
         'step': 'Let the Tabs Snap Into the Holes', 'title': 'Tab in the fixed support hole'},
        {'side': 'right', 'actor': 'gravity_pins', 'point': [pins[3], (pins[1] + pins[4]) / 2, pins[2]],
         'step': 'Plug In and Fit the Board', 'title': 'Pocket under the Gravity socket pins'},
        {'side': 'left', 'actor': 'board', 'point': [eyelet[0], eyelet[1], d.PCB_TOP],
         'step': 'Lower the OP1 Board', 'title': 'OP1 board mounting eyelet'},
        {'side': 'right', 'actor': 'plug', 'point': [(plug[0] + plug[3]) / 2, (plug[1] + plug[4]) / 2, plug[2]],
         'step': 'Connect the Harness Underneath', 'title': 'Plug enters from below, beside the rod'},
        {'side': 'right', 'actor': 'adjustment_screw', 'point': [d.base.STOP_X, d.base.STOP_Y, screw[2] + .1],
         'step': 'Set the OP1 Stop Screw', 'title': 'Adjustable hard stop'},
        {'side': 'left', 'actor': 'electrode', 'point': [d.PLUNGER_XY[0], d.PUSH_Y, electrode[5]],
         'step': 'Touch, Click and Release', 'title': 'Pad above the switch plunger'},
    ]


def guide_checks(guide):
    """Structural checks on the written guide: every actor posed in every
    frame, files present, opens on step 1 (not seated), no Grove actors."""
    report = {}
    for name, module in guide['modules'].items():
        actors = set(module['actors'])
        for actor in module['actors'].values():
            for key in ('file', 'morphFile'):
                if key in actor:
                    assert (OUT / actor[key]).resolve().is_file(), (name, actor[key])
        frames = 0
        for step in module['steps']:
            assert step['samples'], (name, step['title'])
            for sample in step['samples']:
                missing = actors - set(sample)
                assert not missing, (name, step['title'], missing)
                frames += 1
        report[name] = {'steps': len(module['steps']), 'frames': frames}
    dfr = guide['modules']['dfr']
    assert dfr['openSeated'] is False and dfr['steps'][0]['title'] == 'Remove Print Supports'
    assert not any('grove' in n for n in dfr['actors']), 'Grove actor left in the DFRobot guide'
    assert dfr['steps'][CLICK_STEP]['title'] == 'Touch, Click and Release'
    morphs = [s.get('morphs', {}).get('cap', 0.) for st in dfr['steps'] for s in st['samples']]
    assert max(morphs) == 1. and morphs[-1] == 0.
    bom = {p for g in guide['print_components'].values() for p in g}
    assert bom == {d.CARRIER, d.BRACKET, d.CLIP, CLIP2, 'Battery_Holder', 'Battery_End_Door',
                   'XIAO_Rod_Holder', 'XIAO_Near_Keeper', 'Cable_Clip_12_Wire'}, bom
    report['print_parts'] = sorted(bom)
    return report


def write_guide(checks, battery, door):
    guide = previous.old.read(SOURCE / 'assembly-guide.json')
    modules = guide['modules']
    modules.pop('whole', None)
    r39_rest = np.asarray(modules['dfr']['steps'][CLICK_STEP]['samples'][-1]['cap']).reshape(3, 4)
    for module in modules.values():
        module['actors'] = {n: A.relative_actor(v, SOURCE, OUT) for n, v in module['actors'].items()}
    for name in ('key', 'finger_rest'):
        modules[name]['actors']['carrier']['file'] = 'Key_Carrier-assembly.stl'
    morph, _ = A.pinched(f'{d.BRACKET}-assembly.stl', 'guide/dfrobot-bracket-pinched.stl')
    modules['dfr']['actors'] = dfr_actors(modules['dfr'])
    modules['dfr']['actors']['cap']['morphFile'] = morph
    keys_guide(modules['dfr'], checks)
    hinge = modules['snap_hinge']
    hinge['actors']['cap'].update(file=f'{d.BRACKET}-assembly.stl', morphFile=morph,
                                  label='Orange DFRobot bracket and flexible hinge arms')
    pivot = d.r.AXIS_Y + d.r.CLICK_SHIFT
    detail = d.carrier() ^ d.box(-7.6, 7.6, pivot - 3.1, pivot + 9., 10.9, 21.)
    hinge['actors']['carrier']['file'] = A.guide_mesh('dfrobot-hinge-detail', detail)
    # Same rigid/spring mechanism; move R39's checked squeeze/lift frames to this rest pose.
    old4 = np.eye(4); old4[:3] = r39_rest
    new4 = np.eye(4); new4[:3] = d.r.placement()
    delta = new4 @ np.linalg.inv(old4)
    for step in hinge['steps']:
        for sample in step['samples']:
            matrix = np.eye(4); matrix[:3] = np.asarray(sample['cap']).reshape(3, 4)
            sample['cap'] = (delta @ matrix)[:3].ravel().tolist()
    previous.OUT = OUT
    previous.d = d
    modules['battery_latch'] = previous.battery_guide(modules['battery'], battery, door)
    modules['whole'] = previous.overview(modules)
    modules['whole']['note'] = ('Same R41 parts, grouped on one rod. Adjustable spacing; '
                                'external wiring lengths are not dimensioned.')
    guide['print_components'] = {n: g['parts'] for n, g in
                                 previous.old.read(HERE / 'complete-assembly.json')['groups'].items()}
    files = {a[k] for m in modules.values() for a in m['actors'].values() for k in ('file', 'morphFile') if k in a}
    guide.update(revision=HERE.name, physical_fit_verified=False, sources={
        'r39_guide_sha256': H.sha(SOURCE / 'assembly-guide.json'), 'generator_sha256': H.sha(__file__),
        'manifest_sha256': H.sha(OUT / 'manifest.json'), 'meshes_sha256': {n: H.sha(OUT / n) for n in sorted(files)}})
    report = guide_checks(guide)
    A.write_json(OUT / 'assembly-guide.json', guide)
    return report


def export():
    (OUT / 'guide').mkdir(parents=True, exist_ok=True)
    A.OUT = H.OUT = OUT
    checks = d.checks()
    assert checks['passed'], 'R41 geometry checks failed'
    flat = np.eye(4)
    H.PRINT_ROT[d.BRACKET] = A.trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0])
    H.PRINT_ROT['Battery_End_Door'] = H.PRINT_ROT[d.BRACKET]
    H.PRINT_ROT[d.CLIP] = H.PRINT_ROT[CLIP2] = flat
    shapes = ((d.CARRIER, d.carrier()), (d.BRACKET, d.bracket()), (d.CLIP, d.clip_part()),
              (CLIP2, d.clip_part()), ('Battery_End_Door', d.battery_door()))
    parts = {n: H.export_part(n, s, n) for n, s in shapes}
    parts['Battery_Holder'] = d.BATTERY.copy_part('Battery_Holder', d.BATTERY.HERE, OUT, anchored=True)
    A.write_json(OUT / 'anchors.json', {'parts': {'Battery_Holder': previous.old.read(
        d.BATTERY.HERE / 'exports/anchors.json')['parts']['Battery_Holder']}})
    battery = d.BATTERY.read(OUT / 'Battery_Holder-assembly.stl')
    door = d.BATTERY.read(OUT / 'Battery_End_Door-assembly.stl')
    checks['battery_door'] = previous.battery_checks(battery, door)
    A.write_json(OUT / 'geometry-checks.json',
                 {'revision': HERE.name, 'physical_fit_verified': False, 'sliced': False, 'checks': checks})
    A.write_json(OUT / 'manifest.json', {
        'revision': HERE.name, 'units': 'mm', 'parts': parts, 'physical_fit_verified': False, 'print_cleared': False,
        'source_sha256': {p.name: H.sha(p) for p in (HERE / 'holder41.py', Path(__file__), HERE / 'complete-assembly.json')}})
    report = write_guide(checks, battery, door)
    print(json.dumps({'geometry_passed': True, 'parts': list(parts), 'guide': report}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--register', action='store_true')
    parser.add_argument('--guide-only', action='store_true')
    args = parser.parse_args()
    if args.register:
        guide = previous.old.read(OUT / 'assembly-guide.json')
        guide_checks(guide)
        A.register_assembly(OUT / 'assembly-guide.json', 'r41', LABEL, make_current=True, group_keys=True)
    elif args.guide_only:
        A.OUT = H.OUT = OUT
        manifest = previous.old.read(OUT / 'manifest.json')
        manifest['source_sha256']['assembly41.py'] = H.sha(__file__)
        A.write_json(OUT / 'manifest.json', manifest)
        print(json.dumps(write_guide(previous.old.read(OUT / 'geometry-checks.json')['checks'],
                                     d.BATTERY.read(OUT / 'Battery_Holder-assembly.stl'),
                                     d.BATTERY.read(OUT / 'Battery_End_Door-assembly.stl'))))
    else:
        export()
