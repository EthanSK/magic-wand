"""Export the crosswise OP1 candidate and its actual assembly motion.

Run through geometry_budget.py. This composes R39's unchanged battery, XIAO
and cable guides; only the OP1, upper keys and touch-bracket poses change.
It creates no printer connection or print command.
"""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path

import numpy as np

import holder40 as d
import assembly39 as previous

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
SOURCE = d.R39 / 'exports'
A, H, I = previous.A, d.H, previous.I
MOVING = previous.old.MOVING
OP1_BOARD = previous.old.OP1_BOARD
OP1_PLUG = previous.old.OP1_PLUG
MOUSE = ('switch', 'terminals', 'plunger')
LABEL = 'R40 Crosswise OP1 click'


def lifted(matrix: list, z: float) -> list:
    return A.move(matrix, (0., 0., z))


def keys_guide(module: dict, checks: dict) -> None:
    """Use a seated R39 frame only as the unchanged actor roster. Build every
    changed R40 pose explicitly, including the below-board plug approach."""
    final = deepcopy(next(s for s in module['steps'] if s['title'] == 'Touch, Click and Release')['samples'][-1])
    for name in (*OP1_BOARD, *OP1_PLUG, *MOUSE, 'fasteners'):
        final[name] = I.copy()
    rest = d.r.placement().ravel().tolist()
    for name in MOVING:
        final[name] = rest.copy()
    # OP1 screw mesh is generated at zero turns. Its pose carries the checked
    # adjustment height; the physical screw remains M2 x 4.
    setting = checks['stop_settings'][len(checks['stop_settings']) // 2]
    screw_raise = setting['turns_out'] * d.PITCH
    def screw_pose(angle=None, extra=0.):
        return d.r.placement(angle, local=(0., 0., -screw_raise + extra)).ravel().tolist()
    final['adjustment_screw'] = screw_pose()
    for name, matrix in list(final.items()):
        if name.rsplit('_', 1)[0] in ('socket', 'switch', 'keycap') and name[-1] in '34':
            final[name] = A.move(matrix, (-d.UPPER_KEY_SHIFT if name[-1] == '3' else d.UPPER_KEY_SHIFT, 0., 0.))
    state = deepcopy(final)
    for name in OP1_BOARD:
        state[name] = lifted(I, d.h32.BOARD_RISE)
    for name in OP1_PLUG:
        state[name] = lifted(I, -9.)
    state['fasteners'] = lifted(I, d.h32.BOARD_RISE + 6.)
    for name in MOUSE:
        state[name] = lifted(I, 8.)
    for name in ('keycap_3', 'keycap_4'):
        if name in state:
            state[name] = lifted(final[name], 12.)
    state['cap'] = A.move(rest, (-36., 0., 8.))
    for name in MOVING:
        if name not in ('cap', 'adjustment_screw'):
            state[name] = d.r.placement(local=(0., 0., d.SERVICE_LIFT), lift=8.).ravel().tolist()
    state['adjustment_screw'] = lifted(screw_pose(extra=-8.), 8.)
    state['sensor_lead'] = lifted(rest, 8.)
    state['morphs'] = {'cap': 0., 'sensor_lead': 1.}
    steps = [previous.stage('Remove Print Supports',
        'Cut the pad ties. Remove supports from the rod bore, board slot and cable passage before fitting electronics. Clear each screw hole and check the flexible arms move freely.', [deepcopy(state)])]

    def move(title, caption, changes, morph=None, duration=3):
        start = deepcopy(state)
        frames = []
        for t in np.linspace(0., 1., 33):
            f = deepcopy(start)
            for name, target in changes.items():
                f[name] = previous.old.lerp(start[name], target, float(t))
            if morph is not None:
                targets = morph if isinstance(morph, dict) else {'cap': morph}
                f['morphs'] = deepcopy(start.get('morphs', {}))
                for name, target in targets.items():
                    before = start.get('morphs', {}).get(name, 0.)
                    f['morphs'][name] = before + (target - before) * float(t)
            frames.append(f)
        state.update(deepcopy(frames[-1]))
        steps.append(previous.stage(title, caption, frames, duration))

    move('Lower the OP1 Board', 'Lower the crosswise board onto its two seats. Keep the plug below the board; the upper keycaps stay off.', {n: final[n] for n in OP1_BOARD})
    move('Secure the Board', 'Fit the two kit screws through the eyelets. Tighten gently until the board stops moving.', {'fasteners': final['fasteners']})
    move('Connect the Cable Underneath', 'Push the harness plug up into the white socket from below. Feed its lead towards the two-key end without pinching it.', {n: final[n] for n in OP1_PLUG})
    move('Seat the Mouse Switch', 'Seat the mouse switch in its three socket barrels. Keep all three pins straight.', {n: final[n] for n in MOUSE})
    move('Refit the Upper Keycaps', 'Fit the two upper keycaps after the OP1 board and harness are seated.', {n: final[n] for n in ('keycap_3', 'keycap_4') if n in final})
    raised = lifted(rest, 8.)
    move('Bring the Bracket Over the Supports', 'Bring the bracket above the two fixed supports. The side arms and their pins stay part of the bracket.', {'cap': raised})
    move('Set the OP1 Stop Screw', 'Fit the M2 × 4 stop screw. Adjust it on the real switch so the switch clicks before the stop touches, then releases freely.', {'adjustment_screw': lifted(screw_pose(), 8.)})
    move('Pinch the Bracket Arms', 'Pinch the side arms just enough for their pins to clear the supports. Do not force them past the centre stop.', {}, 1.)
    move('Lower Between the Supports', 'Keep the arms pinched and lower the bracket between the supports.', {'cap': rest, 'adjustment_screw': screw_pose(), 'sensor_lead': rest})
    move('Let the Tabs Snap Into the Holes', 'Release the arms so both pins enter the support holes. Check both sides are retained.', {}, 0.)
    board_names = ('sensor', 'electrode', 'connector', 'sensor_parts', 'sensor_plug', 'sensor_lead')
    move('Seat the Grove Board', 'Lower the connected Grove board into its bracket. Keep its underside plug and lead clear of the OP1 board.', {n: rest for n in board_names}, {'sensor_lead': 0.})
    move('Fit the Two M2 Screws', 'Fit the two Grove mounting screws. These are separate from the OP1 kit screws and adjustable stop.', {n: rest for n in ('grove_screw_front', 'grove_screw_rear')})
    click_frames = []
    for angle in [*np.linspace(-d.REST, setting['angle_deg'], 25), *np.linspace(setting['angle_deg'], -d.REST, 25)]:
        f = deepcopy(state)
        for name in MOVING:
            f[name] = d.r.placement(float(angle)).ravel().tolist()
        f['adjustment_screw'] = screw_pose(float(angle))
        f['plunger'] = lifted(I, -d.plunger_travel(float(angle)))
        click_frames.append(f)
    state.update(deepcopy(click_frames[-1]))
    steps.append(previous.stage('Touch, Click and Release', 'The touch board pivots onto the crosswise switch. Check click, stop contact and full release on the actual switch before use.', click_frames, 5))
    move('Undo the Two Screws', 'Remove the two Grove screws to lift the board.', {n: lifted(rest, 10.) for n in ('grove_screw_front', 'grove_screw_rear')})
    up = d.r.placement(local=(0., 0., d.SERVICE_LIFT)).ravel().tolist()
    move('Lift the Grove Board', 'Lift the Grove board with its lead clear. Do not pull on solder joints.', {n: up for n in board_names if n != 'sensor_lead'}, {'sensor_lead': 1.})
    move('Unplug the Grove Lead', 'With the board lifted, ease the plug out by its housing.', {'sensor_plug': A.move(up, (-8., 0., 0.)), 'sensor_lead': A.move(rest, (-8., 0., 0.))})
    move('Reconnect the Grove Lead', 'Reconnect the lead by its plug, leaving the wires loose.', {'sensor_plug': up, 'sensor_lead': rest})
    move('Put the Grove Board Back', 'Lower the board without trapping its lead beneath the bracket.', {n: rest for n in board_names}, {'sensor_lead': 0.})
    move('Fasten the Grove Board', 'Refit the two Grove screws, then check that the touch board clicks and returns freely.', {n: rest for n in ('grove_screw_front', 'grove_screw_rear')})
    module.update(steps=steps, label='Grove touch board and crosswise OP1 click',
        status='Slice checked · physical fit untested',
        note='OP1 board turned 90°. The two upper keys move 3.2 mm outwards on each side; the three lower controls stay in place. Bought-board and cable sizes still need a physical fit trial.')
    for note in module.get('annotations', []):
        if note.get('actor') == 'board':
            note.update(point=[-5.7, d.PLUNGER_XY[1], d.PCB_TOP], step='Lower the OP1 Board')
        elif note.get('title') == 'Adjustable hard stop':
            note['step'] = 'Set the OP1 Stop Screw'


def write_guide(checks, battery, door):
    guide = previous.old.read(SOURCE / 'assembly-guide.json')
    modules = guide['modules']
    modules.pop('whole', None)
    for module in modules.values():
        module['actors'] = {n: A.relative_actor(v, SOURCE, OUT) for n, v in module['actors'].items()}
    for name in ('key', 'dfr', 'finger_rest'):
        modules[name]['actors']['carrier']['file'] = 'Key_Carrier-assembly.stl'
    morph, _ = A.pinched('Grove_Touch_Bracket-assembly.stl', 'guide/grove-bracket-pinched.stl')
    for name in ('dfr', 'snap_hinge'):
        modules[name]['actors']['cap'].update(file='Grove_Touch_Bracket-assembly.stl', morphFile=morph)
    for name, shape in d.hardware().items():
        modules['dfr']['actors'][name]['file'] = A.guide_mesh('op1-' + name, shape)
    modules['dfr']['actors']['op1_wire']['label'] = 'OP1 harness towards the two-key end'
    modules['dfr']['actors']['adjustment_screw']['file'] = A.guide_mesh('op1-adjustment-screw', d.base.stop_screw(0.))
    keys_guide(modules['dfr'], checks)
    for step in modules['key']['steps']:
        for sample in step['samples']:
            for name, matrix in list(sample.items()):
                if name.rsplit('_', 1)[0] in ('socket', 'switch', 'keycap') and name[-1] in '34':
                    sample[name] = A.move(matrix, (-d.UPPER_KEY_SHIFT if name[-1] == '3' else d.UPPER_KEY_SHIFT, 0., 0.))
    pivot = d.r.AXIS_Y + d.r.CLICK_SHIFT
    detail = d.carrier() ^ d.box(-7.6, 7.6, pivot - 3.1, pivot + 9., 10.9, 21.)
    modules['snap_hinge']['actors']['carrier']['file'] = A.guide_mesh('grove-hinge-detail', detail)
    # Hinge detail is the same rigid/spring mechanism. Correct its resting
    # transform while retaining each checked squeeze/lift in its local frame.
    old_rest = np.asarray(previous.old.read(SOURCE/'assembly-guide.json')['modules']['dfr']['steps'][13]['samples'][-1]['cap']).reshape(3, 4)
    old4 = np.eye(4); old4[:3] = old_rest
    new4 = np.eye(4); new4[:3] = d.r.placement()
    delta = new4 @ np.linalg.inv(old4)
    for step in modules['snap_hinge']['steps']:
        for sample in step['samples']:
            for name in ('cap',):
                if name in sample:
                    matrix=np.eye(4);matrix[:3]=np.asarray(sample[name]).reshape(3,4)
                    sample[name]=(delta @ matrix)[:3].ravel().tolist()
    previous.OUT = OUT
    previous.d = d
    modules['battery_latch'] = previous.battery_guide(modules['battery'], battery, door)
    modules['whole'] = previous.overview(modules)
    modules['whole']['note']='Same R40 parts, grouped on one rod. Adjustable spacing; external wiring lengths are not dimensioned.'
    guide['print_components'] = {n:g['parts'] for n,g in previous.old.read(HERE/'complete-assembly.json')['groups'].items()}
    files={a[k] for m in modules.values() for a in m['actors'].values() for k in ('file','morphFile') if k in a}
    guide.update(revision=HERE.name, physical_fit_verified=False, sources={
        'r39_guide_sha256':H.sha(SOURCE/'assembly-guide.json'), 'generator_sha256':H.sha(__file__),
        'manifest_sha256':H.sha(OUT/'manifest.json'), 'meshes_sha256':{n:H.sha(OUT/n) for n in sorted(files)}})
    A.write_json(OUT/'assembly-guide.json', guide)


def export():
    (OUT/'guide').mkdir(parents=True, exist_ok=True)
    A.OUT = H.OUT = OUT
    checks = d.checks()
    assert checks['passed'], 'R40 geometry checks failed'
    H.PRINT_ROT[d.BRACKET] = A.trimesh.transformations.rotation_matrix(math.pi/2, [1,0,0])
    H.PRINT_ROT['Battery_End_Door'] = H.PRINT_ROT[d.BRACKET]
    parts={n:H.export_part(n,s,n) for n,s in ((d.CARRIER,d.carrier()),(d.BRACKET,d.bracket()),('Battery_End_Door',d.battery_door()))}
    parts['Battery_Holder']=d.BATTERY.copy_part('Battery_Holder', d.BATTERY.HERE, OUT, anchored=True)
    A.write_json(OUT/'anchors.json', {'parts':{'Battery_Holder':previous.old.read(d.BATTERY.HERE/'exports/anchors.json')['parts']['Battery_Holder']}})
    battery=d.BATTERY.read(OUT/'Battery_Holder-assembly.stl');door=d.BATTERY.read(OUT/'Battery_End_Door-assembly.stl')
    checks['battery_door']=previous.battery_checks(battery,door)
    A.write_json(OUT/'geometry-checks.json',{'revision':HERE.name,'physical_fit_verified':False,'sliced':False,'checks':checks})
    A.write_json(OUT/'manifest.json',{'revision':HERE.name,'units':'mm','parts':parts,'physical_fit_verified':False,'print_cleared':False,
        'source_sha256':{p.name:H.sha(p) for p in (HERE/'holder40.py',Path(__file__),HERE/'complete-assembly.json')}})
    write_guide(checks,battery,door)
    print(json.dumps({'geometry_passed':True,'parts':list(parts),'guide':str(OUT/'assembly-guide.json')}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--register',action='store_true')
    parser.add_argument('--guide-only',action='store_true')
    args=parser.parse_args()
    if args.register:
        A.register_assembly(OUT/'assembly-guide.json','r40',LABEL,make_current=True,group_keys=True)
    elif args.guide_only:
        A.OUT = H.OUT = OUT
        manifest=previous.old.read(OUT/'manifest.json')
        manifest['source_sha256']['assembly40.py']=H.sha(__file__)
        A.write_json(OUT/'manifest.json',manifest)
        write_guide(previous.old.read(OUT/'geometry-checks.json')['checks'],
            d.BATTERY.read(OUT/'Battery_Holder-assembly.stl'), d.BATTERY.read(OUT/'Battery_End_Door-assembly.stl'))
    else:
        export()
