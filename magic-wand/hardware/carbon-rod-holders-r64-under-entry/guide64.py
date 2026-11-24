"""Generate every R64 assembly view from the kit meshes and verified entry/hinge motion."""
import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

import design64 as entry
import hinge64 as hinge
import kit64

OUT = entry.OUT
SOURCE = entry.old.OUT / 'assembly-guide.json'
MOVING = ('cap','post_bar','clip_left','clip_right','sensor','electrode',
          'connector','sensor_lead','gravity_plug','flat_electrode')
IDENTITY = np.eye(4)


def matrix(values):
    return np.vstack([np.reshape(values,(3,4)), [0,0,0,1]])


def shift(xyz):
    pose = IDENTITY.copy()
    pose[:3,3] = xyz
    return pose


def pivot(degrees):
    angle = math.radians(degrees)
    cs, sn = math.cos(angle), math.sin(angle)
    rotate = IDENTITY.copy()
    rotate[1:3,1:3] = [[cs,-sn],[sn,cs]]
    return shift(hinge.PIVOT) @ rotate @ shift(-hinge.PIVOT)


def flat(pose):
    return pose[:3].ravel().tolist()


def stage_parts(module, rod):
    """Show each loose part when the assembly reaches it. Keep installed groups rigid."""
    arrival = {
        'Seat the OP1 board': entry.ACTORS, 'Fit the mouse switch': ('switch','terminals','plunger'),
        'Insert the two-post bar': ('cap','post_bar'),
        'Connect the Gravity lead': ('sensor','electrode','connector','flat_electrode','gravity_plug','sensor_lead'),
        'Slide on the two small clips': ('clip_left','clip_right'),
        'Slide in the hinge pin': ('hinge_pin',), 'Press in the pin clip': ('pin_clip',),
        'Fit the OP1 retainer': ('lid',),
    }
    departure = {
        'Remove the OP1 retainer': ('lid',), 'Pull out the pin clip': ('pin_clip',),
        'Withdraw the hinge pin': ('hinge_pin',), 'Remove the two clips': ('clip_left','clip_right'),
        'Lift the touch board': arrival['Connect the Gravity lead'],
        'Withdraw the post bar': ('cap','post_bar'), 'Lift out the mouse switch': arrival['Fit the mouse switch'],
    }
    visible = {'carrier','rod'}
    module['stagedActors'] = True
    module['frameBounds'] = [[-38,-28,-10],[64,54,53]]
    module['annotationsByStep'] = True
    module['rotation'] = [1.12, .32, .15] if 'cap' in module['actors'] else [2.08, .28, .13]
    module['actors'].setdefault('rod',dict(rod['actors']['rod']))
    rod_pose = rod['steps'][0]['samples'][0]['rod']
    for step in module['steps']:
        title = step['title']
        visible.update(arrival.get(title, ()))
        if title in ('Seat the OP1 board','Lift the OP1 board'):
            step['frameBounds'] = [[-32,-84,-25],[36,48,23]]
        for sample in step['samples']:
            sample.setdefault('rod',list(rod_pose))
            for key in set(sample)-visible-{'morphs'}:
                del sample[key]
            if 'morphs' in sample:
                sample['morphs'] = {k:v for k,v in sample['morphs'].items() if k in visible}
        visible.difference_update(departure.get(title, ()))


def configure_motion(module, fit):
    steps = module['steps']
    clicked = next((step for step in steps if step['title']=='Press the lower half of the pad'),None)
    old_neutral = {n:matrix(v) for n,v in clicked['samples'][0].items()} if clicked else {}
    if clicked:
        lead_from_world = np.linalg.inv(old_neutral['sensor_lead'])
        old_peak = max(math.asin(p['cap'][9]) for p in clicked['samples'])
        new_peak = fit['case_stop_deg']-.035
        # Only plunge after the CAD contact angle. Stop short of the case hard stop.
        trigger = fit['button_contact_deg']
        travel_per_degree = fit['plunger_travel_at_case_mm'] / (fit['case_stop_deg'] - trigger)
    for step in steps:
        title = step['title']
        if title in ('Seat the OP1 board','Lift the OP1 board'):
            positions = entry.entry_samples()
            if title == 'Lift the OP1 board':
                positions = positions[::-1]
            # Other components are stationary during this stage. Use upstream poses
            # for the switch and retainer, which are deliberately removed for entry.
            step['samples'] = [dict(step['samples'][0], **position) for position in positions]
            step['duration'] = 4.2
            step['caption'] = ('Leave the mouse switch out. Raise the bare board beside the rod at the open end, '
                               'then feed it along the underside, white connector first. Lower it onto its seat.'
                               if title=='Seat the OP1 board' else
                               'With the retainer and switch removed, lift the board off its seat, slide it towards the open end and lower it beside the rod.')
        elif title in ('Press in the pin clip','Pull out the pin clip'):
            step['caption'] = ('Slide one small clip in from behind until it grips the middle groove of the pin. Keep the second clip as a spare.'
                               if title=='Press in the pin clip' else 'Pull the clip straight out towards the rear, then withdraw the pin.')
        elif title == 'Slide in the hinge pin':
            step['caption'] = 'Lower the paddle onto both seats. Slide the standard pin through the three holes. The second pin gives a slightly snugger fit.'
        for sample in step['samples']:
            if 'pin_clip' not in sample:
                continue
            old_clip = matrix(sample['pin_clip'])
            # The old clip approached vertically. Rotate the entire approach about
            # its new centre so the handle and the free staging pose both face rear.
            sample['pin_clip'] = flat(pivot(hinge.CLIP_ANGLE) @ shift(hinge.MOVE) @ old_clip)
            sample['hinge_pin'] = flat(shift(hinge.MOVE) @ matrix(sample['hinge_pin']))
            if title=='Press the lower half of the pad':
                fraction = math.asin(sample['cap'][9]) / old_peak
                moving = pivot(new_peak * fraction)
                for name in MOVING:
                    local = old_neutral[name]
                    if name=='sensor_lead':
                        local = local @ lead_from_world
                    sample[name] = flat(moving @ local)
                sample['plunger'][11] = old_neutral['plunger'][2,3] - max(0., new_peak*fraction-trigger) * travel_per_degree
            else:
                # R61 guide lead STL is pre-shifted; R64 wire STL is assembled in world coordinates.
                sample['sensor_lead'] = flat(matrix(sample['sensor_lead']) @ lead_from_world)
    # Annotation anchors are mesh-local points. A point in the installed
    # assembly would be translated and rotated a second time by the viewer.
    clip_fit = next((s for s in steps if s['title']=='Press in the pin clip'), None)
    if clip_fit:
        seated_clip = matrix(clip_fit['samples'][-1]['pin_clip'])
        clip_anchor = np.linalg.solve(seated_clip,[0,hinge.AXIS+2.2,hinge.KEEPER_Z,1])[:3].tolist()
    module['annotations'] = [n for n in module.get('annotations',[]) if 'Printed finger under' not in n.get('title','')]
    for note in module.get('annotations',[]):
        if note.get('step')=='Seat the OP1 board':
            if note['actor']=='board':
                note['title']='The board settles on its lower ledge before the black switch is inserted.'
            elif note['actor']=='carrier':
                note['title']='Guide the bare board into the open end beside the rod. The retainer slides in above it.'
        if note.get('actor')=='pin_clip':
            note.update(point=clip_anchor,title='Slide the centre clip in from behind the hinge pin.')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(register=False, make_current=False):
    recipe = json.loads(SOURCE.read_text())
    hashes = {}
    fit = json.loads((OUT/'click-fit.json').read_text())
    for name, module in recipe['modules'].items():
        if name in ('dfr','pin_hinge','op1_clips'):
            configure_motion(module, fit)
            stage_parts(module, recipe['modules']['dfr'])
            module['actors']['housing']['label'] = 'Fixed white connector on the underside of the OP1 board'
            module['actors']['plug']['label'] = 'Harness plug fitted before the board slides in'
            module['actors']['board']['label'] = 'OP1 board with two mounting holes'
            module['note'] = ('Fit the OP1 board and its mouse switch first. On the movable paddle, fit the touch board '
                              'with the gold face up and leave its three wires free to bend beside the hinge.')
            if name=='op1_clips':
                module['note'] = 'The white connector and its plug pass along the underside of the holder. Fit the mouse switch after seating the board.'
        if name=='finger_rest':
            module['note'] = 'Both rounded supports curve into the lower edge of the holder. The outside paths stay open for the lower sockets.'
        for actor, spec in module['actors'].items():
            for field in ('file','morphFile'):
                if field not in spec:
                    continue
                src = (SOURCE.parent/spec[field]).resolve(strict=True)
                if field=='file':
                    src = {'carrier':OUT/entry.HOLDER, 'rod_collet':OUT/entry.COLLET_FILE,
                           'cap':OUT/'Touch_Paddle-assembly.stl','sensor_lead':OUT/'Gravity_Wires-assembly.stl'}.get(actor, src)
                key = os.path.relpath(src,OUT)
                spec[field] = key
                if key not in hashes:
                    hashes[key] = digest(src)
            if actor=='hinge_pin':
                spec['label'] = 'Separate hinge pin'
        if 'status' in module:
            module['status'] = 'R64 design · physical fit untested'
    recipe.pop('reuse_components',None)
    recipe['print_components']['keys'] = sorted(kit64.COMPLETE)
    recipe['revision'] = 'R64'
    recipe['physical_fit_verified'] = False
    recipe['sources'] = dict(generator_sha256=digest(Path(__file__)),upstream_guide_sha256=digest(SOURCE),
                             meshes_sha256=hashes)
    file = OUT/'assembly-guide.json'
    file.write_text(json.dumps(recipe,separators=(',',':'),allow_nan=False)+'\n')
    if register or make_current:
        sys.path.insert(0,str(entry.HERE.parent/'carbon-rod-holders/assembly'))
        from register_assembly import register_assembly
        register_assembly(file,'r64','R64 · Under-entry OP1 and compact hinge',
                          group_keys=True,make_current=make_current)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--register',action='store_true')
    parser.add_argument('--current', action='store_true', help='Register R64 as the default revision')
    args=parser.parse_args()
    write(args.register, args.current)
