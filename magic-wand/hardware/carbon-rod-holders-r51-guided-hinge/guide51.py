"""Assemble the review viewer from R51 geometry and the unchanged R48 interfaces."""
import hashlib
import json
import os
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
OLD = HERE.parent / 'carbon-rod-holders-r48-edge-click/exports'
OP1 = 'board sockets housing plug switch terminals plunger fasteners op1_wire'.split()
SENSOR = 'sensor electrode connector gravity_pins sensor_lead'.split()
CLIPS = ['clip_left', 'clip_right']
MOVING = ['cap', *SENSOR, *CLIPS]
IDENTITY = [1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0.]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def offset(pose, x=0., y=0., z=0.):
    pose = pose.copy()
    for i, delta in zip((3, 7, 11), (x, y, z)):
        pose[i] += delta
    return pose


def matrix(pose):
    return np.vstack((np.asarray(pose).reshape(3, 4), [0, 0, 0, 1]))


def refit(pose, old, new):
    return (matrix(new) @ np.linalg.inv(matrix(old)) @ matrix(pose))[:3].flatten().tolist()


def step(title, caption, samples, duration=2.5):
    return dict(title=title, caption=caption, duration=duration, samples=samples)


def move(title, caption, start, actors, vector):
    samples = []
    for fraction in np.linspace(0, 1, 26):
        pose = start.copy()
        for key in actors:
            pose[key] = offset(start[key], *(fraction * x for x in vector))
        samples.append(pose)
    return step(title, caption, samples)


def trim_legacy(modules):
    del modules['print_cleanup'], modules['snap_hinge']
    for name, module in modules.items():
        for actor in module['actors'].values():
            for attr in ('file', 'morphFile'):
                if attr in actor:
                    path = actor[attr]
                    if path == 'Key_Carrier-assembly.stl' or path == 'Battery_End_Door-assembly.stl':
                        continue
                    if path.endswith('/Cable_Clip_12_Wire-assembly.stl'):
                        actor[attr] = 'Cable_Clip_12_Wire-reference.stl'
                    elif path == 'guide/micron-tab-pressed.stl':
                        actor[attr] = 'Battery_End_Door-released.stl'
                    else:
                        actor[attr] = os.path.relpath(OLD/path, OUT)
        if name in ('whole', 'dfr'):
            continue
        module['steps'] = [s for s in module['steps'] if 'rod' not in s['title'].lower()
                           and s['title'] not in ('Slide the Clip Off', 'Remove Print Supports', 'Seated',
                                                  'Snip Off the Print Pads', 'Remove the cradle’s print tabs')]
        for s in module['steps']:
            for p in s['samples']:
                if 'rod' in p:
                    p['rod'] = IDENTITY


def hinge_module(module, spec):
    actors = module['actors']
    board_notes = [a for a in module.get('annotations', []) if a.get('step') in ('Plug In and Fit the Board','Clip the Posts') and a['actor'] in ('cap','gravity_pins','clip_right')]
    old_steps = {s['title']: s for s in module['steps']}
    old_rest = old_steps['Clip the Posts']['samples'][-1]['cap']
    rest = spec['rest']
    hw = spec['hardware']
    op_shift = spec['op1_shift']
    del actors['adjustment_screw']
    for k in list(actors):
        if k.startswith('switch_'):
            del actors[k]
    actors['op1_wire'].update(file='op1_wire.stl',morphFile='op1-wire-hanging.stl')
    actors['cap'] = dict(label='DFRobot bracket with reinforced centre bearing', file='DFRobot_Hole_Bracket-assembly.stl', color='#d9822b')
    actors['carrier'].update(label='Key holder with two fixed hinge cheeks')
    for key, part in hw.items():
        actors[key] = dict(label=part['label'], file=part['file'], color=part['color'])
    screw, sleeve, nut = 'axle_screw', 'bearing_sleeve', 'locknut'
    # Insert the sleeve into the loose bracket first. Both ends fit between the cheeks.
    def stage(p):
        state = {k:v for k,v in p.items() if k in actors}
        for k in OP1:
            state[k] = offset(state[k], *op_shift)
        # The R51 harness is already exported in the revised world frame.
        state['op1_wire'] = p['op1_wire']
        state['rod'] = IDENTITY
        state['cap'] = offset(rest, z=14.)
        for k in SENSOR + CLIPS:
            state[k] = offset(refit(old_steps['Plug In and Fit the Board']['samples'][0][k], old_rest, rest), z=14.)
        for k, disp in ((screw, (-21.,0.,0.)), (sleeve, (-13.,0.,14.)), (nut, (11.,0.,0.))):
            state[k] = offset(IDENTITY, *disp)
        state['morphs'] = {'op1_wire': p.get('morphs', {}).get('op1_wire', 0.)}
        return state
    steps = []
    for title in ('Feed the lead through the slot','Lower the OP1 Board','Secure the Board','Press the Lead into the Groove','Seat the Mouse Switch'):
        before = old_steps[title]
        descriptions = {
            'Lower the OP1 Board': 'Lower the plugged-in OP1 board onto its two seats while feeding the lead through the slot.',
            'Press the Lead into the Groove': 'From the underside, guide the lead toward the two-key end and into its groove.',
        }
        steps.append(step(title, descriptions.get(title,before['caption']), [stage(p) for p in before['samples']],before['duration']))
    def advance(title, caption, targets, vector):
        steps.append(move(title, caption, steps[-1]['samples'][-1], targets, vector))
    advance('Slide the sleeve into the bracket', 'Slide the smooth metal sleeve through the orange centre bearing while the bracket is loose.', [sleeve], (13.,0.,0.))
    advance('Lower the bracket between the cheeks', 'Lower the bracket and sleeve together until the three holes line up.', ['cap',sleeve], (0.,0.,-14.))
    advance('Insert the axle screw', 'Pass the M2 screw through the first cheek, the sleeve and the opposite cheek.', [screw], (21.,0.,0.))
    advance('Fit the locknut', 'Fit the locknut on the screw. Check that the bracket swings freely when the axle is secured.', [nut], (-11.,0.,0.))
    # Board and post clips keep their physical interfaces with the bracket. Reuse
    # their checked installation in the new hinge frame, including plug orientation.
    for title in ('Plug In and Fit the Board','Clip the Posts'):
        fixed = steps[-1]['samples'][-1].copy()
        frames = []
        for i,p in enumerate(old_steps[title]['samples']):
            frame = fixed.copy()
            for k in SENSOR+CLIPS:
                frame[k] = refit(p[k], old_rest, rest)
                if title == 'Plug In and Fit the Board':
                    t = i / max(1,len(old_steps[title]['samples'])-1)
                    frame[k] = offset(frame[k], z=14.*(1.-t))
            frames.append(frame)
        steps.append(step(title, old_steps[title]['caption'], frames))
    seated = steps[-1]['samples'][-1]
    frames = []
    for item in spec['press_cycle']:
        p = seated.copy()
        for k in MOVING:
            p[k] = item['pose']
        p['plunger'] = offset(seated['plunger'], z=-item['plunger_drop'])
        frames.append(p)
    steps.append(step('Press the lower half of the pad', 'Press toward the three-key end. The touch board and bracket pivot together above the OP1 button. Check click and return on the assembled parts.',frames,3.))
    module.update(steps=steps, label='Fit the DFRobot touchpad', keysLabel='Keys', note=spec['note'],
                  openSeated=False, fitOuterKeysSeparately=True, status='Design review · physical fit pending',annotations=board_notes)
    return seated


def pivot_detail(module):
    keys = ['carrier','cap','axle_screw','bearing_sleeve','locknut']
    titles = ['Slide the sleeve into the bracket','Lower the bracket between the cheeks',
              'Insert the axle screw','Fit the locknut','Press the lower half of the pad']
    steps = [step(s['title'],s['caption'],[{k:p[k] for k in keys} for p in s['samples']],s['duration'])
             for s in module['steps'] if s['title'] in titles]
    for index,title,caption in [(3,'Remove the locknut','Hold the screw head and undo the locknut.'),
                                (2,'Withdraw the axle','Pull the screw out sideways while supporting the bracket.'),
                                (1,'Lift out the bracket','Lift the orange bracket and sleeve clear of the fixed cheeks.')]:
        steps.append(step(title,caption,list(reversed(steps[index]['samples']))))
    return dict(label='Axle assembly',rotation=[.98,0.,-.5],actors={k:module['actors'][k] for k in keys},
                steps=steps,annotations=[dict(actor='bearing_sleeve',point=[0.,30.1,19.9],step='Slide the sleeve into the bracket',title='Sleeve inside the moving bearing'),
                dict(actor='locknut',point=[9.6,30.1,20.],step='Fit the locknut',title='Locknut retains the axle')],
                note='The sleeve stays inside the orange bearing. Both fixed cheeks are part of the key holder.')


def generate(spec):
    guide = json.loads((OLD/'assembly-guide.json').read_text())
    modules = guide['modules']
    trim_legacy(modules)
    seated = hinge_module(modules['dfr'], spec)
    modules['pin_hinge'] = pivot_detail(modules['dfr'])
    whole = modules['whole']
    old_pose = next(s for s in whole['steps'] if s['title']=='Check the Complete Arrangement')['samples'][-1]
    old_pose.pop('keys_adjustment_screw',None)
    del whole['actors']['keys_adjustment_screw']
    for key, actor in modules['dfr']['actors'].items():
        if key == 'rod':
            continue
        whole['actors']['keys_'+key] = actor
        old_pose['keys_'+key] = seated[key]
    if 'morphs' in old_pose:
        old_pose['morphs'] = {k:v for k,v in old_pose['morphs'].items() if k!='keys_cap'}
    whole['steps'] = [step('Inspect the assembled wand', 'Choose a component to see how its parts fit together.',[old_pose])]

    guide.update(revision='R51',physical_fit_verified=False,
                 print_components={'keys':['Key_Carrier','DFRobot_Hole_Bracket'], 'battery':['Battery_End_Door']})
    names = {a[key] for m in modules.values() for a in m['actors'].values()
             for key in ('file','morphFile') if key in a}
    guide['sources'] = dict(upstream_guide_sha256=digest(OLD/'assembly-guide.json'),
                            mechanism_sha256=digest(OUT/'mechanical-fit.json'),
                            generator_sha256=digest(Path(__file__)),
                            meshes_sha256={name:digest(OUT/name) for name in sorted(names)})
    out = OUT/'assembly-guide.json'
    out.write_text(json.dumps(guide,separators=(',',':'),allow_nan=False)+'\n')
    return out


def review_spec():
    import build51 as cad
    dimensions = json.loads((OUT/'dimensions.json').read_text())
    # Exact paddle placement is regenerated from the same pivot as the CAD.
    raw = json.loads((OUT/'mechanical-fit.json').read_text())
    parameters = raw['viewer']
    rest = np.asarray(parameters['paddle_rest_matrix']).flatten().tolist()
    poses = [dict(pose=cad.placement(item['angle_deg']).flatten().tolist(),
                  plunger_drop=item['plunger_drop_mm']) for item in parameters['click_path']]
    assert np.allclose(poses[0]['pose'],rest) and poses[0]['plunger_drop']<.01
    assert np.allclose(poses[-1]['pose'],rest) and poses[-1]['plunger_drop']<.01
    return dict(rest=rest, press_cycle=poses,op1_shift=dimensions['op1_world_translation_from_r48_mm'],
                hardware={
                    'axle_screw':dict(label='M2 × 20 mm axle screw',file='pivot-screw.stl',color='#98a4b2'),
                    'bearing_sleeve':dict(label='12 mm metal sleeve · 3 mm outside, 2.1 mm inside',file='pivot-sleeve.stl',color='#d8ba75'),
                    'locknut':dict(label='M2 nylon-insert locknut',file='pivot-locknut.stl',color='#738aa4'),
                },
                note='Fit the hinge before installing the four outer Choc switches. Press the lower half of the gold pad toward the three-key end. The two clips retain the touch board.')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--register', action='store_true')
    args=parser.parse_args()
    guide = generate(review_spec())
    if args.register:
        sys.path.insert(0,str(HERE.parent/'carbon-rod-holders/assembly'))
        from register_assembly import register_assembly
        register_assembly(guide,'r51','R51 · Reinforced touchpad hinge and lighter battery lid',make_current=True,group_keys=True)
